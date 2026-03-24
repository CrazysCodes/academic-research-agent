"""
LangGraph StateGraph 编排：多 Agent 研究分析管线。

流程：Planner → Retriever → Writer → Reviewer → (打回修订 or 完成)

条件边逻辑：
  - Reviewer 评分 < 7 且修订轮次 < 2 → 打回 Writer 重写
  - 否则 → 结束，输出最终报告
"""
from langgraph.graph import END, StateGraph

from app.core.nodes.planner import planner_node
from app.core.nodes.retriever import retriever_node
from app.core.nodes.reviewer import reviewer_node
from app.core.nodes.writer import writer_node
from app.core.state import ResearchState

_MAX_ITERATIONS = 2  # Writer 最多执行次数（含首次）
_PASS_SCORE = 7      # Reviewer 评分及格线


def _should_revise(state: ResearchState) -> str:
    """条件边：决定是打回 Writer 修订还是结束。"""
    if state.get("score", 10) < _PASS_SCORE and state.get("iterations", 0) < _MAX_ITERATIONS:
        return "writer"
    return "end"


def build_research_graph():
    """构建并编译研究分析 StateGraph。"""
    g = StateGraph(ResearchState)

    # 注册 4 个 Agent 节点
    g.add_node("planner", planner_node)
    g.add_node("retriever", retriever_node)
    g.add_node("writer", writer_node)
    g.add_node("reviewer", reviewer_node)

    # 线性流水线：planner → retriever → writer → reviewer
    g.set_entry_point("planner")
    g.add_edge("planner", "retriever")
    g.add_edge("retriever", "writer")
    g.add_edge("writer", "reviewer")

    # 条件边：reviewer 评分不及格则打回 writer 修订
    g.add_conditional_edges(
        "reviewer",
        _should_revise,
        {"writer": "writer", "end": END},
    )

    return g.compile()


# 模块级单例，全局复用
research_graph = build_research_graph()
