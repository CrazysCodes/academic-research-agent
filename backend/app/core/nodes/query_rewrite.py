"""
QueryRewriteNode: rewrite user queries into retrieval-friendly forms.

The node is intentionally fail-open: if the LLM or structured parsing fails,
callers receive the original query so the existing RAG/Agent paths still work.
"""
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.utils.json import parse_json_markdown
from pydantic import BaseModel, Field

from app.core.llm import create_chat_llm, create_structured_llm, supports_structured_output

logger = logging.getLogger(__name__)

_MAX_RETRIEVAL_QUERIES = 5


class QueryRewriteResult(BaseModel):
    rewritten_query: str = Field(description="Self-contained rewritten query")
    retrieval_queries: list[str] = Field(description="Search queries for retrieval")
    hypothetical_answer: str = Field(
        default="",
        description="Short HyDE-style hypothetical answer for embedding retrieval",
    )


_CHAT_SYSTEM = """You rewrite user questions for academic-paper RAG retrieval.

The user has selected uploaded papers. Make the query self-contained and produce several retrieval queries that are likely to match paper chunks.

Output JSON only:
{
  "rewritten_query": "<standalone question>",
  "retrieval_queries": ["<query 1>", "<query 2>", "..."],
  "hypothetical_answer": "<short possible answer containing likely terminology, or empty string>"
}

Rules:
- Keep the user's original intent.
- Use the same language as the user where possible.
- Produce 2 to 4 retrieval queries.
- Expand vague academic terms into concrete searchable terms when helpful.
  For example, "实验参数" should include likely terms such as GPU, hardware,
  learning rate, batch size, epochs, iterations, optimizer, training settings,
  implementation details, parameter settings, and experimental setup.
- If the query asks for a category and likely subfields, include both the broad
  category query and subfield-specific retrieval queries.
- Do not invent paper-specific facts; the hypothetical answer is only a retrieval aid."""

_ANALYZE_SYSTEM = """You rewrite research-analysis requests for multi-paper academic analysis.

The rewritten query will be passed to a planner that decomposes it into sub-queries. Make it explicit, structured, and suitable for comparing uploaded papers.

Output JSON only:
{
  "rewritten_query": "<structured analysis request>",
  "retrieval_queries": ["<optional retrieval focus 1>", "<optional retrieval focus 2>"],
  "hypothetical_answer": ""
}

Rules:
- Preserve the user's original intent.
- Include comparison dimensions if implied, such as method, dataset, metrics, findings, limitations, or future work.
- Use the same language as the user where possible."""


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = " ".join(item.split())
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _fallback(query: str) -> QueryRewriteResult:
    # Query Rewrite 是增强链路，不应阻断主流程；失败时保持原问题继续检索。
    return QueryRewriteResult(
        rewritten_query=query,
        retrieval_queries=[query],
        hypothetical_answer="",
    )


def _normalize(query: str, result: QueryRewriteResult) -> QueryRewriteResult:
    # 统一清洗 LLM 输出：保证 rewritten_query 非空，并限制检索 query 数量，避免一次请求打爆 embedding 成本。
    rewritten = result.rewritten_query.strip() or query
    retrieval_queries = _dedupe([rewritten, *result.retrieval_queries])[:_MAX_RETRIEVAL_QUERIES]
    return QueryRewriteResult(
        rewritten_query=rewritten,
        retrieval_queries=retrieval_queries or [query],
        hypothetical_answer=result.hypothetical_answer.strip(),
    )


def retrieval_texts(result: QueryRewriteResult) -> list[str]:
    """Return query texts to embed for retrieval, including optional HyDE text."""
    # HyDE 文本只作为检索向量，不直接展示给用户；它能帮助短 query 命中更接近答案形态的 chunk。
    texts = [*result.retrieval_queries]
    if result.hypothetical_answer:
        texts.append(result.hypothetical_answer)
    return _dedupe(texts)[:_MAX_RETRIEVAL_QUERIES]


def _parse_result(content: str) -> QueryRewriteResult | None:
    try:
        parsed = parse_json_markdown(content)
        if isinstance(parsed, dict):
            return QueryRewriteResult(
                rewritten_query=str(parsed.get("rewritten_query", "")),
                retrieval_queries=[str(q) for q in parsed.get("retrieval_queries", [])],
                hypothetical_answer=str(parsed.get("hypothetical_answer", "")),
            )
    except Exception:
        pass
    return None


async def _rewrite(query: str, system_prompt: str, mode: str) -> QueryRewriteResult:
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"User query:\n{query}"),
    ]

    if supports_structured_output():
        try:
            # 优先走 function calling，能让支持 tool_choice 的模型直接返回 Pydantic 结构。
            structured_llm = create_structured_llm(QueryRewriteResult)
            result: QueryRewriteResult = await structured_llm.ainvoke(messages)
            normalized = _normalize(query, result)
            logger.info(
                "QueryRewriteNode [%s][structured] 成功: %s -> %s",
                mode,
                query[:80],
                normalized.rewritten_query[:80],
            )
            return normalized
        except Exception as e:
            logger.warning("QueryRewriteNode [%s][structured] 失败，降级普通 JSON 解析: %s", mode, e)
    else:
        logger.info("QueryRewriteNode [%s] 跳过 structured 输出，使用普通 JSON 解析", mode)

    try:
        # 部分 OpenAI 兼容服务不支持强制 tool calling，退回到“提示词 JSON + parse_json_markdown”。
        llm = create_chat_llm(streaming=False)
        response = await llm.ainvoke(messages)
        logger.info("QueryRewriteNode [%s][json] raw: %r", mode, str(response.content)[:1000])
        parsed = _parse_result(str(response.content))
        if parsed:
            normalized = _normalize(query, parsed)
            logger.info(
                "QueryRewriteNode [%s][json] 成功: %s -> %s; retrieval_queries=%s; hyde=%r",
                mode,
                query[:80],
                normalized.rewritten_query[:80],
                normalized.retrieval_queries,
                normalized.hypothetical_answer[:200],
            )
            return normalized
    except Exception as e:
        logger.warning("QueryRewriteNode [%s][json] 失败，回退原始 query: %s", mode, e)

    return _fallback(query)


async def rewrite_chat_query(query: str) -> QueryRewriteResult:
    """Rewrite a chat query for RAG retrieval."""
    return await _rewrite(query, _CHAT_SYSTEM, "chat")


async def rewrite_analyze_query(query: str) -> QueryRewriteResult:
    """Rewrite an analysis query before PlannerNode."""
    return await _rewrite(query, _ANALYZE_SYSTEM, "analyze")
