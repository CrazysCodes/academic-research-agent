"""
PlannerNode：将研究问题拆解为 3~5 个子查询。
"""
import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import create_chat_llm
from app.core.state import ResearchState

_SYSTEM = """You are a research planning assistant.
Given a research question, decompose it into 3 to 5 specific sub-queries that together cover all aspects needed for a comprehensive answer.
Respond with a JSON array of sub-query strings ONLY — no explanation, no markdown fences.
Example: ["sub-query 1", "sub-query 2", "sub-query 3"]"""


async def planner_node(state: ResearchState) -> dict:
    llm = create_chat_llm(streaming=False)
    messages = [
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=f"Research question: {state['query']}"),
    ]
    response = await llm.ainvoke(messages)
    try:
        sub_queries = json.loads(response.content)
        if not isinstance(sub_queries, list) or not sub_queries:
            raise ValueError
    except Exception:
        sub_queries = [state["query"]]
    return {"sub_queries": sub_queries[:5]}
