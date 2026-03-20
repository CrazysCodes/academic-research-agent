"""
LangGraph StateGraph：Research → Retriever → Writer → Reviewer → (retry or done)
"""
from langgraph.graph import END, StateGraph

from app.core.nodes.planner import planner_node
from app.core.nodes.retriever import retriever_node
from app.core.nodes.reviewer import reviewer_node
from app.core.nodes.writer import writer_node
from app.core.state import ResearchState

_MAX_ITERATIONS = 2
_PASS_SCORE = 7


def _should_revise(state: ResearchState) -> str:
    if state.get("score", 10) < _PASS_SCORE and state.get("iterations", 0) < _MAX_ITERATIONS:
        return "writer"
    return "end"


def build_research_graph():
    g = StateGraph(ResearchState)

    g.add_node("planner", planner_node)
    g.add_node("retriever", retriever_node)
    g.add_node("writer", writer_node)
    g.add_node("reviewer", reviewer_node)

    g.set_entry_point("planner")
    g.add_edge("planner", "retriever")
    g.add_edge("retriever", "writer")
    g.add_edge("writer", "reviewer")
    g.add_conditional_edges(
        "reviewer",
        _should_revise,
        {"writer": "writer", "end": END},
    )

    return g.compile()


research_graph = build_research_graph()
