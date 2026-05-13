"""
ReviewerNode：质量评审 + 可选 Tavily 外部搜索补充。
评分 0-10，score < 7 且未超轮数时打回 WriterNode 重写。
评分维度：准确性(0-3) + 结构清晰度(0-3) + 分析深度(0-4)

解析策略（三层）：
1. with_structured_output (Function Calling) —— 代理层强约束，最可靠
2. parse_json_markdown + retry               —— 自动剥除 ```json 围栏，retry 带错误反馈
3. 最终回退                                  —— 默认评分 7（通过），空 feedback
"""
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.utils.json import parse_json_markdown
from pydantic import BaseModel

from app.core.llm import create_chat_llm, create_structured_llm, supports_structured_output
from app.core.state import ResearchState
from app.core.tools.web_search import search_web

logger = logging.getLogger(__name__)

_SYSTEM = """You are a strict JSON-output grader for academic reports.

Your ONLY task: read the report inside <report> tags and output a score.

Output format — JSON object, nothing else, no markdown fences, no explanation:
{"score": <integer 0-10>, "feedback": "<improvement suggestions, or empty string if score >= 7>"}

Scoring:
- Accuracy and citation of sources: 0-3
- Structure and clarity: 0-3
- Depth and completeness: 0-4

CRITICAL: Your entire response must be a single JSON object. Do not write any text outside the JSON."""

_RETRY_TEMPLATE = """Your previous response was not a valid JSON object. Here is what you returned:

{prev_output}

You MUST output ONLY this JSON object — no markdown, no explanation, no other text:
{{"score": <integer 0-10>, "feedback": "<suggestions or empty string>"}}

Output the JSON now:"""


# ── 方案一：Structured Output Schema ──
class _ReviewerOutput(BaseModel):
    score: int
    feedback: str


def _try_parse_reviewer_output(content: str) -> dict | None:
    """从 LLM 响应中提取评审结果，使用 parse_json_markdown 自动处理围栏。"""
    try:
        parsed = parse_json_markdown(content)
        if isinstance(parsed, dict) and "score" in parsed:
            return {
                "score": max(0, min(10, int(parsed["score"]))),
                "feedback": str(parsed.get("feedback", "")),
            }
    except Exception:
        pass
    return None


async def reviewer_node(state: ResearchState) -> dict:
    """
    评审报告质量，返回评分和改进建议。

    优先使用 Function Calling 强约束（方案一），失败时降级到
    parse_json_markdown + retry（方案二），最终兜底默认评分 7。
    """
    logger.info("ReviewerNode 开始，报告长度=%d", len(state.get("draft", "")))
    llm = create_chat_llm(streaming=False)

    # 可选：Tavily 外部搜索补充评审上下文
    web_context = ""
    if state.get("query"):
        web_context_raw = await search_web(state["query"])
        if web_context_raw:
            web_context = f"\n\n<web_context>{web_context_raw}</web_context>"
            logger.info("ReviewerNode 获取到 Tavily 外部搜索结果")

    # 用 XML 标签明确包裹报告内容，避免 LLM 将报告内容误解为指令
    report_block = f"<report>\n{state['draft']}\n</report>{web_context}"
    messages = [
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=f"Grade this report and return JSON only:\n\n{report_block}"),
    ]

    # ── 方案一：Function Calling 强约束 ──
    if supports_structured_output():
        try:
            structured_llm = create_structured_llm(_ReviewerOutput)
            result_obj: _ReviewerOutput = await structured_llm.ainvoke(messages)
            score = max(0, min(10, result_obj.score))
            logger.info("ReviewerNode [structured] 成功，评分=%d", score)
            return {"score": score, "feedback": result_obj.feedback}
        except Exception as e:
            logger.warning("ReviewerNode [structured] 失败，降级到 parse_json_markdown 方案: %s", e)
    else:
        logger.info("ReviewerNode 跳过 structured 输出，使用 parse_json_markdown 方案")

    # ── 方案二：普通调用 + parse_json_markdown + retry ──
    response = await llm.ainvoke(messages)
    logger.info("[DEBUG][Reviewer] 第1次 LLM 返回: %r", response.content[:300])

    result = _try_parse_reviewer_output(response.content)

    if result is None:
        logger.warning(
            "ReviewerNode 首次解析失败，触发 retry。原始返回(前200字符)=%r",
            response.content[:200],
        )
        retry_messages = [
            SystemMessage(content=_SYSTEM),
            HumanMessage(content=_RETRY_TEMPLATE.format(prev_output=response.content[:500])),
        ]
        retry_response = await llm.ainvoke(retry_messages)
        logger.info("[DEBUG][Reviewer] Retry LLM 返回: %r", retry_response.content[:300])
        result = _try_parse_reviewer_output(retry_response.content)

    # ── 最终回退 ──
    if result is None:
        logger.warning("ReviewerNode retry 后仍失败，默认评分 7 通过")
        result = {"score": 7, "feedback": ""}

    logger.info("ReviewerNode 完成，评分=%d，是否需要修订=%s", result["score"], result["score"] < 7)
    return result
