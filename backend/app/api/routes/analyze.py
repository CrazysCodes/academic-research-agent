import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.llm import create_chat_llm
from app.models.request import AnalyzeRequest
from app.repositories import paper_repo
from app.services import rag_service

router = APIRouter()

SINGLE_PROMPT = """You are an academic research assistant.
Analyze the following research paper excerpts and answer the question thoroughly.
Structure your response with clear sections. Cite sources when possible."""

COMPARE_PROMPT = """You are an academic research assistant.
You are given excerpts from multiple research papers. Compare and contrast them based on the question.
Structure your response as: 1) Key similarities, 2) Key differences, 3) Your synthesis.
Be specific and cite which paper each point comes from when possible."""


async def _stream_analysis(query: str, context_chunks: list[str], mode: str):
    llm = create_chat_llm()
    system = COMPARE_PROMPT if mode == "compare" else SINGLE_PROMPT
    context = "\n\n---\n\n".join(context_chunks)
    messages = [
        SystemMessage(content=system),
        HumanMessage(content=f"Paper excerpts:\n{context}\n\nQuestion: {query}"),
    ]
    async for chunk in llm.astream(messages):
        if chunk.content:
            yield f"data: {json.dumps({'delta': chunk.content})}\n\n"
    yield "data: [DONE]\n\n"


@router.post("")
async def analyze(
    req: AnalyzeRequest,
    db: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    for paper_id in req.paper_ids:
        paper = await paper_repo.get(db, paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail=f"Paper {paper_id} not found")
        if paper.status != "ready":
            raise HTTPException(
                status_code=400,
                detail=f"Paper '{paper.title}' is not ready (status: {paper.status})",
            )

    top_k = 8 if req.mode == "compare" else 5
    context_chunks = await rag_service.retrieve(req.paper_ids, req.query, top_k=top_k)
    if not context_chunks:
        raise HTTPException(status_code=404, detail="No relevant content found")

    return StreamingResponse(
        _stream_analysis(req.query, context_chunks, req.mode),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
