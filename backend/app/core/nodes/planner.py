"""
PlannerNode：将研究问题拆解为 3~5 个子查询。

解析策略（三层）：
1. with_structured_output (Function Calling) —— 代理层强约束，最可靠
2. parse_json_markdown + retry               —— 自动剥除 ```json 围栏，retry 带错误反馈
3. 最终回退                                  —— 将原始查询作为唯一子查询
"""
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.utils.json import parse_json_markdown
from pydantic import BaseModel

from app.core.llm import create_chat_llm, create_structured_llm
from app.core.state import ResearchState

logger = logging.getLogger(__name__)

_SYSTEM = """You are a research planning assistant. The user has already uploaded their papers — you do NOT need to ask for any documents or information.

Your ONLY task: decompose the given research question into 3 to 5 focused sub-queries that will be used to search within the uploaded papers.

Output format: a JSON array of strings, nothing else — no explanation, no markdown fences, no preamble.

Example output:
["What methods are proposed in the papers?", "What datasets and metrics are used for evaluation?", "What are the key findings and conclusions?"]"""

_RETRY_TEMPLATE = """Your previous response was not a valid JSON array. Here is what you returned:

{prev_output}

Research question: {query}

You MUST output ONLY a JSON array of 3 to 5 sub-query strings. No other text, no markdown, no explanation.
Output the JSON array now:"""


# ── 方案一：Structured Output Schema ──
class _PlannerOutput(BaseModel):
    sub_queries: list[str]


def _try_parse_sub_queries(content: str) -> list[str] | None:
    """从 LLM 响应中提取子查询数组，使用 parse_json_markdown 自动处理围栏。"""
    try:
        parsed = parse_json_markdown(content)
        if isinstance(parsed, list) and parsed:
            return [str(q) for q in parsed]
    except Exception:
        pass
    return None


async def planner_node(state: ResearchState) -> dict:
    """
    调用 LLM 将用户问题拆解为多个子查询。

    优先使用 Function Calling 强约束（方案一），失败时降级到
    parse_json_markdown + retry（方案二），最终兜底回退到原始查询。
    """
    logger.info("PlannerNode 开始，原始问题: %s", state["query"][:80])

    messages = [
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=f"Research question: {state['query']}"),
    ]

    # ── 方案一：Function Calling 强约束 ──
    try:
        structured_llm = create_structured_llm(_PlannerOutput)
        result: _PlannerOutput = await structured_llm.ainvoke(messages)
        sub_queries = [str(q) for q in result.sub_queries if q][:5]
        if sub_queries:
            logger.info("PlannerNode [structured] 成功，生成 %d 个子查询: %s", len(sub_queries), sub_queries)
            return {"sub_queries": sub_queries}
    except Exception as e:
        logger.warning("PlannerNode [structured] 失败，降级到 parse_json_markdown 方案: %s", e)

    # ── 方案二：普通调用 + parse_json_markdown + retry ──
    llm = create_chat_llm(streaming=False)
    response = await llm.ainvoke(messages)
    logger.info("[DEBUG][Planner] 第1次 LLM 返回: %r", response.content[:300])

    sub_queries = _try_parse_sub_queries(response.content)

    if not sub_queries:
        logger.warning(
            "PlannerNode 首次解析失败，触发 retry。原始返回(前200字符)=%r",
            response.content[:200],
        )
        retry_messages = [
            SystemMessage(content=_SYSTEM),
            HumanMessage(
                content=_RETRY_TEMPLATE.format(
                    prev_output=response.content[:500],
                    query=state["query"],
                )
            ),
        ]
        retry_response = await llm.ainvoke(retry_messages)
        logger.info("[DEBUG][Planner] Retry LLM 返回: %r", retry_response.content[:300])
        sub_queries = _try_parse_sub_queries(retry_response.content)

    # ── 最终回退 ──
    if not sub_queries:
        logger.warning("PlannerNode retry 后仍失败，回退到原始查询作为单一子查询")
        sub_queries = [state["query"]]

    logger.info("PlannerNode 完成，生成 %d 个子查询: %s", len(sub_queries[:5]), sub_queries[:5])
    return {"sub_queries": sub_queries[:5]}
