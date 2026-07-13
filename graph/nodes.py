"""Graph nodes. Each wraps existing CodeComp logic and returns a partial
state update. Streaming (QA tokens + a `meta` event) is pushed through the
LangGraph custom stream writer so the API can forward it as SSE.
"""

from langgraph.types import interrupt

from router import route_query
from retrieval.query import search_code
from agents.context_extender import build_compressed_context
from agents.reasoner import stream_answer
from agents.editor import propose_edit, apply_edit_to_disk, verify_repo
from ingestion.index import sync_index
from ingestion.repo_source import is_remote, resolve_repo

from graph.state import GraphState

MAX_RETRIES = 2  # extra plan attempts after the first failed verify


def _writer():
    """Custom stream writer, or a no-op when not streaming (plain invoke)."""
    try:
        from langgraph.config import get_stream_writer

        return get_stream_writer()
    except Exception:  # noqa: BLE001
        return lambda *_a, **_k: None


def _serialize(docs) -> list[dict]:
    return [
        {
            "function": d.metadata.get("function", "unknown"),
            "file": d.metadata.get("file", "unknown"),
            "language": d.metadata.get("language", ""),
            "code": d.metadata.get("code") or d.page_content,
        }
        for d in docs
    ]


# --------------------------------------------------------------------------- #
# Routing + retrieval (shared by both branches)
# --------------------------------------------------------------------------- #

def node_route(state: GraphState) -> GraphState:
    raw = route_query(state["query"])           # "codebase" | "debugger"
    return {
        "route": "edit" if raw == "debugger" else "qa",
        "is_remote": is_remote(state["repo"]),
    }


def node_retrieve(state: GraphState) -> GraphState:
    docs, expanded = search_code(state["query"], state["repo"], token=state.get("token"))
    functions = _serialize(docs)
    _writer()({"type": "meta", "data": {"route": state["route"], "functions": functions}})
    # Keep only serializable data in state (the checkpointer persists it).
    return {
        "expanded": list(expanded) if expanded else [],
        "context": build_compressed_context(docs),
        "functions": functions,
    }


# --------------------------------------------------------------------------- #
# QA branch
# --------------------------------------------------------------------------- #

def node_answer(state: GraphState) -> GraphState:
    write = _writer()
    parts: list[str] = []
    for delta in stream_answer(
        state["query"], state["context"], state.get("expanded"), state.get("memory_ctx", "")
    ):
        parts.append(delta)
        write({"type": "token", "text": delta})
    return {"answer": "".join(parts), "status": "qa_answer"}


# --------------------------------------------------------------------------- #
# Edit branch
# --------------------------------------------------------------------------- #

def node_edit_unavailable(state: GraphState) -> GraphState:
    msg = (
        "Editing is only supported on local repositories, because the "
        "verify step (compile / lint / tests) needs to run against a real "
        "checkout with its dependencies installed. This repo was cloned from "
        "a remote URL. Clone it locally and pass the local path to enable "
        "the edit workflow."
    )
    _writer()({"type": "token", "text": msg})
    return {"answer": msg, "status": "edit_unavailable"}


def node_plan_edit(state: GraphState) -> GraphState:
    repo_path = state.get("repo_path") or resolve_repo(state["repo"], update=False)
    plan = propose_edit(
        state["query"],
        state["context"],
        repo_path,
        feedback=state.get("feedback", ""),
        prior_error=(state.get("verify") or {}).get("output", ""),
    )
    # Clear consumed feedback so a later approve doesn't re-trigger it.
    return {"plan": plan, "repo_path": repo_path, "feedback": ""}


def node_human_gate(state: GraphState) -> GraphState:
    """Pause for human review of the proposed diff.

    Resumes with {"decision": "approve"} or
    {"decision": "reject", "feedback": "..."}.
    """
    decision = interrupt({"type": "review", "plan": state["plan"]})
    if isinstance(decision, dict):
        if decision.get("decision") == "approve":
            return {"decision": "approve"}
        return {"decision": "reject", "feedback": decision.get("feedback", "")}
    return {"decision": str(decision)}


def node_apply_edit(state: GraphState) -> GraphState:
    apply_edit_to_disk(state["repo_path"], state["plan"])
    return {}


def node_verify(state: GraphState) -> GraphState:
    result = verify_repo(state["repo_path"], state["plan"]["file"])
    retries = state.get("retries", 0)
    return {"verify": result, "retries": retries + (0 if result["passed"] else 1)}


def node_reindex(state: GraphState) -> GraphState:
    # Refresh the vector index so subsequent questions see the edited code.
    try:
        sync_index(state["repo_path"])
    except Exception:  # noqa: BLE001 -- reindex is best-effort
        pass
    return {}


def node_summary(state: GraphState) -> GraphState:
    plan = state["plan"]
    answer = (
        f"Applied edit to `{plan['file']}` and it passed verification.\n\n"
        f"{plan['rationale']}\n\n"
        f"Verification:\n{state['verify']['output']}"
    )
    _writer()({"type": "token", "text": answer})
    return {"answer": answer, "status": "edit_applied"}


def node_report_failure(state: GraphState) -> GraphState:
    plan = state.get("plan", {})
    answer = (
        f"Couldn't get `{plan.get('file', '?')}` to pass verification after "
        f"{state.get('retries', 0)} attempts. The change was written to disk; "
        "review it manually.\n\nLast verification output:\n"
        f"{(state.get('verify') or {}).get('output', 'n/a')}"
    )
    _writer()({"type": "token", "text": answer})
    return {"answer": answer, "status": "edit_failed"}


# --------------------------------------------------------------------------- #
# Conditional edges
# --------------------------------------------------------------------------- #

def decide_route(state: GraphState) -> str:
    if state["route"] == "qa":
        return "qa"
    return "edit_remote" if state["is_remote"] else "edit_local"


def decide_gate(state: GraphState) -> str:
    return "approve" if state["decision"] == "approve" else "reject"


def decide_verify(state: GraphState) -> str:
    if state["verify"]["passed"]:
        return "pass"
    if state.get("retries", 0) > MAX_RETRIES:
        return "fail"
    return "retry"
