# CodeComp

> Ask questions about a codebase — or ask it to make a change. Answers and edits
> are grounded in the actual code, reviewed, verified, and re-indexed.

---

##  What is CodeComp?

CodeComp lets you interact with a codebase using natural language.

Instead of:
- opening files  
- tracing function calls  
- building mental maps  

You can:
> provide a repository → ask a question (or request an edit) → get a structured,
> code-grounded result

---

##  What it does

- Extracts function-level chunks using AST (tree-sitter, multi-language)
- Builds relationships between functions (call graph)
- Retrieves relevant code using embeddings, expands context via graph traversal
- Answers questions with an LLM, streamed token-by-token
- Proposes edits as a reviewable diff, applies them only after you approve, then
  verifies (compile + lint + tests) and self-corrects on failure
- Keeps the index in sync automatically as the code changes
- Maintains conversational memory across queries

---

##  System Architecture

    Codebase → AST Chunking → Summaries → Embeddings (Qdrant)
                                          ↓
    User Query → Route → Retrieval → Graph Expansion → Context Compression
                                                  ↓
                                    ┌─────────────┴─────────────┐
                                    │                           │
                              QA (streamed)            Edit (review → apply
                                                        → verify → reindex)

---

##  Example Queries

QA (local *or* GitHub repos):
- "How does this feature work end-to-end?"  
- "Which functions are involved in this flow?"  
- "What calls this function and why?"  

Edit (local repos only):
- "Add a `mul()` to calc.py"  
- "Fix the off-by-one in the pagination helper"  

---

##  Setup

### 1. Clone the repo

    git clone https://github.com/yashwork-byte/CompCode
    cd CompCode

### 2. Install dependencies

    pip install -r requirements.txt

### 3. Start Qdrant (Docker)

    docker run -p 6333:6333 qdrant/qdrant

### 4. Setup environment variables

Create a `.env` file in the root:

    OPENAI_API_KEY=your_key_here

> **Verify safety:** on the edit path, the `verify` step can run the repo's test
> suite (shell execution). This is **disabled by default**. To enable it (and only
> in a throwaway/sandboxed checkout) set `CODECOMP_ALLOW_EXEC=1`. Compile and lint
> checks always run; tests run only when execution is enabled. Obviously
> destructive commands are refused even when enabled.

---

##  Run

The app is a FastAPI backend + a Next.js/shadcn frontend. Both need Qdrant
running and `OPENAI_API_KEY` set.

    # 1. backend API
    uvicorn api:app --reload --port 8000

    # 2. frontend (in another terminal)
    cd frontend
    npm install
    npm run dev            # http://localhost:3000

The frontend talks to the API at `NEXT_PUBLIC_API_URL` (default
`http://localhost:8000`, set in `frontend/.env.local`).

---

##  Agent workflow (LangGraph)

Every request runs through one `StateGraph` (`graph/build.py`):

    route → retrieve → ┬─ qa ───────────────▶ answer (streamed)
                       ├─ edit + remote ────▶ edit_unavailable
                       └─ edit + local ─────▶ plan_edit → human_gate* → apply_edit → verify
                                                              (interrupt)              │
                                     reject+feedback ↺ plan_edit          pass ▶ reindex ▶ summary
                                                                          retry ↺ plan_edit
                                                                          fail  ▶ report

- **Routing** picks QA vs. edit. **QA** works on local *and* GitHub repos; **edit** is
  **local-only** (verify needs a real checkout with deps), so remote edit requests are
  refused via a conditional edge.
- **Human gate:** the graph `interrupt()`s before writing anything — the UI shows the
  proposed **diff**; you Approve (apply) or Reject with feedback (loops back to re-plan). A
  `MemorySaver` checkpointer + `thread_id` persist the pause; the API resumes with
  `Command(resume=...)`.
- **Self-correction:** after applying, `verify` runs compile + lint (and the repo's tests
  when `CODECOMP_ALLOW_EXEC=1`). On failure the error trace feeds back to `plan_edit`, bounded
  by a retry limit. On success the index is refreshed (`reindex`) so the next question sees the
  new code.

Endpoints: `POST /query/stream` (SSE: `meta` → `token` → `interrupt`|`done`) and
`POST /resume` (`{thread_id, decision, feedback}`).

##  Staying in sync with code changes

The index self-heals. Every query first runs an **incremental sync**: it hashes
each function on disk, compares against what's indexed, and re-summarizes only
the functions that changed (deleting ones that were removed). So edits — whether
from the edit agent, your editor, or a `git pull` — are reflected on the next
question, with no manual re-index and no full-repo LLM cost. The call graph is
cached on a file-mtime fingerprint, so it invalidates on any edit too.

##  Repositories & languages

- **Local or GitHub:** pass a local path *or* a GitHub URL
  (`https://github.com/user/repo`). Remote repos are shallow-cloned into
  `~/.codecomp/repos`. Public repos need no auth; private repos take a token
  (`GITHUB_TOKEN` env, or the token field in the UI).
- **Languages:** Python, JavaScript, TypeScript/TSX, Go, Java, Rust, and
  C/C++ — parsed with tree-sitter. Adding a language is a small entry in
  `ingestion/languages.py`.

---

##  Evaluation

`eval/run_eval.py` runs a small QA test set (`eval/test_cases.json`): it scores
retrieval recall against expected functions and uses an LLM judge for relevance,
groundedness, and correctness.

    python -m eval.run_eval

---

##  Limitations

- Function-level granularity  
- Heuristic ranking  
- Name-based call resolution (over-connects; not scope-aware)  
- Not optimized for very large repos  

---

##  Key Design Ideas

- Structure first (AST), semantics later (LLM)  
- Graph-based context over flat retrieval  
- Precompute expensive steps (summaries)  
- Not all context should be treated equally (memory vs code)  
- Never write to disk without human review; never trust an edit until it verifies  

---

##  Future Work

- Scope-aware call resolution (imports, class scope)  
- Better ranking strategies  
- Scalable background processing (RQ)  
- Improved memory isolation  
- Multi-file edits  

---

##  Open to Feedback

If you’ve worked on:
- code search  
- developer tools  
- LLM systems  

I’d really value your feedback.

---

##  Article

Read the full breakdown here:  
 https://medium.com/@tarunyash01/v1-codecomp-building-a-system-to-reason-over-a-codebase-0267ca507b9d
