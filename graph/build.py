"""Assemble the CodeComp workflow as a LangGraph StateGraph.

Topology:

    route -> retrieve -> {qa | edit_remote | edit_local}
      qa           -> answer -> END
      edit_remote  -> edit_unavailable -> END
      edit_local   -> plan_edit -> human_gate* (interrupt)
                        approve -> apply_edit -> verify
                                     pass  -> reindex -> summary -> END
                                     retry -> plan_edit           (self-correction cycle)
                                     fail  -> report_failure -> END
                        reject  -> plan_edit                      (feedback cycle)

The human gate uses interrupt(); a checkpointer persists state across the
pause so the API can resume with the reviewer's decision.
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from graph.state import GraphState
from graph import nodes as n


def build_graph(checkpointer=None):
    g = StateGraph(GraphState)

    g.add_node("route", n.node_route)
    g.add_node("retrieve", n.node_retrieve)
    g.add_node("answer", n.node_answer)
    g.add_node("edit_unavailable", n.node_edit_unavailable)
    g.add_node("plan_edit", n.node_plan_edit)
    g.add_node("human_gate", n.node_human_gate)
    g.add_node("apply_edit", n.node_apply_edit)
    g.add_node("verify", n.node_verify)
    g.add_node("reindex", n.node_reindex)
    g.add_node("summary", n.node_summary)
    g.add_node("report_failure", n.node_report_failure)

    g.add_edge(START, "route")
    g.add_edge("route", "retrieve")

    g.add_conditional_edges(
        "retrieve",
        n.decide_route,
        {"qa": "answer", "edit_remote": "edit_unavailable", "edit_local": "plan_edit"},
    )
    g.add_edge("answer", END)
    g.add_edge("edit_unavailable", END)

    g.add_edge("plan_edit", "human_gate")
    g.add_conditional_edges(
        "human_gate",
        n.decide_gate,
        {"approve": "apply_edit", "reject": "plan_edit"},
    )
    g.add_edge("apply_edit", "verify")
    g.add_conditional_edges(
        "verify",
        n.decide_verify,
        {"pass": "reindex", "retry": "plan_edit", "fail": "report_failure"},
    )
    g.add_edge("reindex", "summary")
    g.add_edge("summary", END)
    g.add_edge("report_failure", END)

    return g.compile(checkpointer=checkpointer or MemorySaver())
