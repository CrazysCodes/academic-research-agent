"""
RetrieverNode：并发 RAG 检索，聚合并去重 context chunks。
"""
import asyncio

from app.core.state import ResearchState
from app.services import rag_service

_MAX_CHUNKS = 20


async def retriever_node(state: ResearchState) -> dict:
    tasks = [
        rag_service.retrieve(state["paper_ids"], sq, top_k=5)
        for sq in state["sub_queries"]
    ]
    results = await asyncio.gather(*tasks)

    seen: set[str] = set()
    chunks: list[str] = []
    for batch in results:
        for chunk in batch:
            if chunk not in seen:
                seen.add(chunk)
                chunks.append(chunk)

    return {"context_chunks": chunks[:_MAX_CHUNKS]}
