import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.llm import create_chat_llm
from app.core.nodes.query_rewrite import retrieval_texts, rewrite_chat_query
from app.models.request import ChatRequest
from app.repositories import paper_repo
from app.services import rag_service

router = APIRouter()
logger = logging.getLogger(__name__)

RAG_SYSTEM_PROMPT = """You are an academic research assistant.
Answer the user's question based ONLY on the provided context from research papers.
If the context does not contain enough information, say so clearly.
Cite relevant parts of the context when answering.
Respond in the same language as the user's question."""

GENERAL_SYSTEM_PROMPT = """You are a helpful academic research assistant.
Answer the user's question thoroughly and accurately.
Respond in the same language as the user's question."""


async def _stream_rag(query: str, context_chunks: list[str]):
    llm = create_chat_llm()
    context = "\n\n---\n\n".join(context_chunks)
    logger.info(
        "Chat RAG LLM call: query=%r context_chunks=%d context_chars=%d previews=%s",
        query,
        len(context_chunks),
        len(context),
        [" ".join(chunk.split())[:120] for chunk in context_chunks],
    )
    messages = [
        SystemMessage(content=RAG_SYSTEM_PROMPT),
        HumanMessage(content=f"Context:\n{context}\n\nQuestion: {query}"),
    ]
    async for chunk in llm.astream(messages):
        if chunk.content:
            yield f"data: {json.dumps({'delta': chunk.content})}\n\n"
    yield "data: [DONE]\n\n"


async def _stream_general(query: str):
    llm = create_chat_llm()
    logger.info("Chat general LLM call: query=%r", query)
    messages = [
        SystemMessage(content=GENERAL_SYSTEM_PROMPT),
        HumanMessage(content=query),
    ]
    async for chunk in llm.astream(messages):
        if chunk.content:
            yield f"data: {json.dumps({'delta': chunk.content})}\n\n"
    yield "data: [DONE]\n\n"


@router.post("")
async def chat_stream(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    # 通用 LLM 模式（未选论文）
    if not req.paper_ids:
        logger.info("Chat request: mode=general query=%r", req.query)
        return StreamingResponse(
            _stream_general(req.query),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # RAG 模式 — 从 DB 验证论文状态
    for paper_id in req.paper_ids:
        paper = await paper_repo.get(db, paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail=f"Paper {paper_id} not found")
        if paper.status != "ready":
            raise HTTPException(
                status_code=400,
                detail=f"Paper '{paper.title}' is not ready (status: {paper.status})",
            )

    logger.info("Chat request: mode=rag query=%r paper_ids=%s", req.query, req.paper_ids)
    rewrite = await rewrite_chat_query(req.query)
    texts = retrieval_texts(rewrite)
    logger.info(
        "Chat intent/rewrite: rewritten=%r retrieval_texts=%s",
        rewrite.rewritten_query,
        texts,
    )
    context_chunks = await rag_service.retrieve_multi(req.paper_ids, texts, top_k=8)
    if not context_chunks:
        raise HTTPException(status_code=404, detail="No relevant content found in selected papers")
    logger.info("Chat retrieved context: chunks=%d", len(context_chunks))

    return StreamingResponse(
        _stream_rag(req.query, context_chunks),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
