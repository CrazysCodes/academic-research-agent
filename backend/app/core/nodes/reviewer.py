"""
ReviewerNode：质量评审 + 可选 Tavily 外部搜索补充。
score < 7 且未超轮数时打回 WriterNode 重写。
"""
import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import create_chat_llm
from app.core.state import ResearchState
from app.core.tools.web_search import search_web

_SYSTEM = """You are a critical academic review assistant.
Evaluate the following research analysis report on a scale of 0 to 10.

Scoring criteria:
- Accuracy and use of provided sources (0-3 points)
- Structure and clarity (0-3 points)
- Depth and completeness of analysis (0-4 points)

Respond with a JSON object ONLY — no explanation, no markdown fences:
{"score": <integer 0-10>, "feedback": "<specific improvement suggestions, or empty string if score >= 7>"}"""


async def reviewer_node(state: ResearchState) -> dict:
    llm = create_chat_llm(streaming=False)

    web_context = ""
    if state.get("query"):
        web_context_raw = await search_web(state["query"])
        if web_context_raw:
            web_context = f"\n\nAdditional web context for reference:\n{web_context_raw}"

    messages = [
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=f"Draft report:\n{state['draft']}{web_context}"),
    ]
    response = await llm.ainvoke(messages)

    try:
        result = json.loads(response.content)
        score = max(0, min(10, int(result.get("score", 7))))
        feedback = result.get("feedback", "")
    except Exception:
        score = 7
        feedback = ""

    return {"score": score, "feedback": feedback}
