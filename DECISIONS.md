# Decisions — 2026-07-07 shortcomings fix pass

Each entry: options considered → tradeoff → deciding reason → room for improvement.

## 1. Debugger shell execution (security)
- **Options:** (a) keep `os.system`; (b) remove the debugger; (c) capture output via
  `subprocess`, disable execution by default behind `CODECOMP_ALLOW_EXEC`, plus a
  destructive-command denylist.
- **Tradeoff:** (c) keeps the feature usable but adds friction (must opt in).
- **Deciding reason:** running model-generated shell commands unguarded is the worst
  risk in the repo; safe-by-default with real captured output is the right balance.
- **Room for improvement:** true sandbox (container/chroot), per-command human approval,
  an allowlist instead of a denylist.

## 2. Function identity = `file::function` (uid)
- **Options:** (a) keep bare function name; (b) file::function; (c) file::function::lineno.
- **Tradeoff:** (b) fixes cross-file collisions but not two same-named funcs in one file.
- **Deciding reason:** cross-file collision was the actual bug (maps silently overwritten);
  intra-file duplicates are rare. (c) complicates name-based call resolution.
- **Room for improvement:** qualified names including class scope (`Class.method`).

## 3. Call graph: name-based resolution, keyed by uid, cached
- **Options:** (a) keep name-keyed graph; (b) uid nodes, resolve a call to *all* uids of
  that name; (c) full static name resolution (imports/scopes).
- **Tradeoff:** (b) over-connects (a call to `foo` links every `foo`) but never overwrites.
- **Deciding reason:** (c) is a large project on its own; (b) removes the silent data loss
  cheaply. Added `lru_cache(repo_path)` so the graph isn't rebuilt on every query.
- **Room for improvement:** scope-aware resolution; cache invalidation on file mtime.

## 4. Semantic score normalization
- **Options:** (a) keep `1 - score`; (b) use score directly; (c) min-max normalize.
- **Deciding reason:** langchain-qdrant returns cosine *similarity* (higher = better), so
  `1 - score` inverted ranking. Min-max normalizes onto the same [0,1] scale as the graph
  and importance signals regardless of metric.
- **Room for improvement:** confirm metric from collection config rather than assuming cosine.

## 5. Graph-expanded functions now fetch real code
- **Options:** (a) leave expanded funcs as bare names; (b) enlarge top-k pool; (c) fetch by
  uid from Qdrant via `scroll` + `MatchAny` filter.
- **Deciding reason:** (c) guarantees expanded functions contribute actual code/summaries
  (the whole point of graph expansion) without bloating the semantic retrieval.
- **Room for improvement:** batch/limit very large neighborhoods.

## 6. Re-index upserts instead of appends
- **Chose:** deterministic Qdrant point id = `uuid5(namespace, uid)` passed to `from_texts`.
- **Reason:** re-indexing the same repo previously doubled vectors. Stable ids upsert.
- **Room for improvement:** delete points for functions that no longer exist (prune).

## 7. Smaller fixes
- mem0: read `OPENAI_API_KEY` (was `OPEN_API_KEY` → None), port int, dedicated collection,
  parametrized `user_id`.
- debugger: per-call `history` (was a leaking module global); valid-JSON contract +
  `response_format=json_object`.
- reasoner: question no longer duplicated in system and user roles.
- ingestion: shared `ast_utils` (dedup), async-function support, `None`-source guard,
  `SyntaxError`-scoped excepts, single-parse pass.
- index: per-chunk try/except so one summary failure doesn't abort the run.
- app: `@st.cache_resource` for the memory client.
- eval: aggregate summary, robust judge JSON, function-name test keywords.
- docs: README repo name + debugger safety note.

---

# Decisions — 2026-07-07 v2: multi-language, GitHub, web app

## 8. Multi-language extraction: tree-sitter (unified, retire `ast`)
- **Options:** (a) keep Python `ast` and bolt tree-sitter on for others (two paths);
  (b) unify everything on tree-sitter.
- **Deciding reason:** one consistent extractor + call-graph path for all languages;
  tree-sitter's Python grammar is solid, so the old `ast` path bought nothing.
- **Design:** config-driven registry (`ingestion/languages.py`) declaring function/call
  node types per language; generic name extraction via tree-sitter field names with a
  declarator-descent fallback for C/C++. Byte-range slicing gives exact source.
- **Room for improvement:** class-qualified names; arrow/callback coverage in JS.

## 9. GitHub support: clone to a deterministic cache
- **Options:** (a) clone to a temp dir each run; (b) deterministic cache keyed by
  token-free URL, reuse across index+query, best-effort pull on re-index.
- **Deciding reason:** query-time rebuilds the call graph from disk, so the working copy
  must persist and be found again without extra state; (b) gives that and avoids
  re-cloning. Public = no auth; private = PAT (arg or `GITHUB_TOKEN`).
- **Tradeoff / room for improvement:** a tokenized remote URL is written into the cache's
  git config on clone; acceptable for a local dev tool, but could be stripped. `--depth 1`
  means no history-based features.

## 10. Web app: FastAPI + Next.js/shadcn (keep Python pipeline)
- **Options:** (a) rewrite pipeline in TS; (b) Python pipeline behind a FastAPI layer with
  a Next.js/shadcn frontend.
- **Deciding reason:** the whole retrieval/agent stack is Python; (b) reuses it verbatim
  and adds a thin HTTP seam. Frontend is a single client-side page calling `/index` +
  `/query`; memory is optional so the API still serves if Qdrant/memory is down.
- **Room for improvement:** stream answers; per-session repo state; auth on the API.

---

# Decisions — 2026-07-07 v2.1: staleness sync + streaming

## 11. Combat index staleness: auto-sync on query
- **Problem:** after code changed (debugger edits, manual edits, `git pull`) answers
  reflected the *old* code. Two stale layers: the Qdrant vectors/summaries/snippets
  (only written by `index_repo`) and the `@lru_cache`d call graph.
- **Options:** (a) manual "re-index" button; (b) re-index fully on every query;
  (c) incremental sync diffed by per-function content hash, run automatically.
- **Deciding reason:** (a) is a footgun (easy to forget → wrong answers); (b) is correct
  but pays full LLM cost every query. (c) is correct *and* cheap: unchanged repo = parse +
  scroll, no LLM; only changed/new functions get re-summarized, removed ones deleted.
- **Design:** `sync_index(repo)` stores `code_hash` per point, diffs disk vs Qdrant, upserts
  changed (deterministic ids) and deletes removed; called at the top of `search_code` so
  every entry point self-heals. Call-graph cache re-keyed on a file-mtime fingerprint so it
  invalidates on any edit. Verified: edit+add+delete → `2 updated, 1 removed`, fresh code.
- **Room for improvement:** the per-query scroll of all points is O(n); for large repos,
  gate sync behind a cheap dir-fingerprint check, or push it to a background worker.

## 12. Streaming answers (SSE)
- **Options:** (a) WebSocket; (b) Server-Sent Events over a POST body.
- **Deciding reason:** answers are one-way server→client text; SSE is the simplest fit.
  `EventSource` only does GET, so the client POSTs and parses the `text/event-stream` body
  manually. Events: `meta` (route + functions up front) → `token` deltas → `done`/`error`.
- **Debugger route:** agentic + side-effecting, so it runs to completion and is emitted as a
  single block rather than token-streamed. Non-debugger answers stream from the model.
- **Room for improvement:** stream the debugger's intermediate steps; cancel on disconnect.

## 13. Retro pixel-OS UI reskin (dark + shadcn)
- **Options:** (a) install `8bitcn/ui` and swap component set; (b) hand-roll a full custom
  design system; (c) keep shadcn components and reskin them via theme tokens +
  `data-slot` overrides + a few retro-OS wrappers.
- **Tradeoff:** (a) fastest look but forks the component layer and pins us to a third
  party; (b) most control, most work; (c) minimal churn, keeps shadcn a11y/behavior.
- **Deciding reason:** every shadcn primitive carries `data-slot` and derives radius from
  `--radius`, so `--radius:0` + a small `@layer components` override squares and pixel-ifies
  the *whole* UI without editing each component. Reference (simrann_sayss portfolio) is a
  desktop-OS metaphor — so we added `PixelWindow` (title bar + square controls + hard offset
  shadow), a top `MenuBar` (brand/menus/clock), and a bottom `Dock`. Kept the pastel wallpaper
  idea but on a **dark** base with a pixel grid + faint scanlines; neon-lime accent mirrors her
  "Project Overview" highlighter. Fonts: Press Start 2P (chrome), VT323 (readable body), Geist
  Mono (code) via `next/font/google`.
- **Room for improvement:** genuine pixel-art icons (pixelarticons) instead of lucide line
  icons; draggable windows; render "Relevant functions" as a desktop icon grid; a boot/CRT
  power-on animation.

## 14. LangGraph workflow (routing + self-correction + human gate)
- **Options:** (a) keep the router + two agents (no orchestration); (b) add LangGraph only
  around the debugger; (c) model the *whole* request as one StateGraph:
  route → retrieve → {qa answer | edit workflow}.
- **Tradeoff:** (a) honest but doesn't showcase orchestration and the two agents genuinely
  don't need a graph; (b) leaves a graph hanging off the side; (c) more moving parts but the
  graph *is* the app, which is defensible.
- **Deciding reason:** a graph is only justified by things a router can't do — **cycles** and
  **interrupts**. So we expanded the debugger from a single blind write into a verified,
  human-gated, self-correcting edit workflow: `plan_edit → human_gate (interrupt) →
  apply_edit → verify → {pass→reindex→summary | retry→plan_edit | fail→report}`, plus a
  reject→plan_edit feedback cycle. Two real cycles + one interrupt.
- **Edit is local-only:** a conditional edge sends `edit + remote` to `edit_unavailable`.
  This also kills the dependency problem — verify (compile/lint/tests) only runs on a real
  local checkout. QA runs for both local and GitHub repos.
- **Implementation notes:** `MemorySaver` checkpointer + `thread_id` persist the paused
  review; API resumes with `Command(resume=...)`. QA tokens stream from inside the graph via
  `get_stream_writer()` → SSE. State holds only serializable data (no raw Documents — the
  checkpointer must msgpack it). Verify uses `sys.executable -m py_compile` (bare `python`
  isn't always on PATH); missing tools (ruff/eslint/tsc) are skipped, not failed; the repo's
  own test suite runs only under `CODECOMP_ALLOW_EXEC`.
- **Dropped Gemini's standalone security node:** nothing deploys here, so a "deployment
  guardrail" has no target; left a seam to fold bandit/semgrep into `verify` later.
- **Room for improvement:** stream the debugger's intermediate reasoning; revert-on-fail;
  multi-file edits; per-command approval inside verify; migrate the legacy `main.py` CLI onto
  the graph too.
