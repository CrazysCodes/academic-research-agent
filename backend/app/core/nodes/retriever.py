"""
RetrieverNode：获取论文全文内容用于深度分析。
若 initial_state 已预填充 context_chunks（全文模式），则跳过 RAG 直接透传。
降级分支（context_chunks 为空时）仍走 RAG 检索，保持向后兼容。
"""
import asyncio
import logging

from app.core.state import ResearchState
from app.services import rag_service

logger = logging.getLogger(__name__)

_MAX_CHUNKS = 20


async def retriever_node(state: ResearchState) -> dict:
    """
    全文模式：若 state 中已有 context_chunks（由 _stream_agent 预填充），直接返回。
    RAG 降级：context_chunks 为空时，才做向量检索（兜底逻辑）。
    """
    existing_chunks = state.get("context_chunks", [])

    # 全文模式：context_chunks 已由外部预填充，直接透传给 WriterNode
    if existing_chunks:
        logger.info(
            "RetrieverNode 全文模式：跳过 RAG，直接使用预填充的 %d 个文本块",
            len(existing_chunks),
        )
        return {"context_chunks": existing_chunks}

    # 降级：RAG 检索（context_chunks 未预填充时的兜底）
    logger.warning(
        "RetrieverNode 降级到 RAG 模式（context_chunks 未预填充），%d 个子查询，%d 篇论文",
        len(state["sub_queries"]), len(state["paper_ids"]),
    )
    tasks = [
        rag_service.retrieve(state["paper_ids"], sq, top_k=5)
        for sq in state["sub_queries"]
    ]
    results = await asyncio.gather(*tasks)

    # 合并去重：保留首次出现的顺序
    seen: set[str] = set()
    chunks: list[str] = []
    for batch in results:
        for chunk in batch:
            if chunk not in seen:
                seen.add(chunk)
                chunks.append(chunk)

    final_chunks = chunks[:_MAX_CHUNKS]
    logger.info("RetrieverNode RAG 完成，去重后 %d 个文本块（上限 %d）", len(final_chunks), _MAX_CHUNKS)
    return {"context_chunks": final_chunks}
