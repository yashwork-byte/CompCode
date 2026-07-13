"""Shared state for the CodeComp LangGraph workflow.

One request flows through the graph as this dict. Nodes return partial
updates that LangGraph merges in. `total=False` so nodes only set what they
touch.
"""

from typing import Any, TypedDict


class GraphState(TypedDict, total=False):
    # ---- inputs (set by the API before invoking) ----
    query: str
    repo: str                 # local path or GitHub URL
    token: str | None         # GitHub token, remote repos only
    memory_ctx: str           # conversational memory, injected by the API

    # ---- routing ----
    route: str                # "qa" | "edit"
    is_remote: bool           # GitHub/remote vs local checkout
    repo_path: str            # resolved local path (edit path only)

    # ---- retrieval ----
    # NB: we deliberately do NOT store raw Documents in state — the checkpointer
    # must serialize state, so we keep only plain, serializable data.
    expanded: list[str]       # graph-expanded uids (list, not a set)
    context: str              # compressed context for the LLM
    functions: list[dict]     # serialized hits for the UI

    # ---- edit workflow ----
    plan: dict                # {file, new_content, diff, rationale}
    feedback: str             # reviewer feedback on reject
    decision: str             # "approve" | "reject"
    verify: dict              # {passed, output, checks}
    retries: int              # verify-loop attempts so far

    # ---- output ----
    answer: str
    status: str               # qa_answer | edit_applied | edit_unavailable | edit_failed
