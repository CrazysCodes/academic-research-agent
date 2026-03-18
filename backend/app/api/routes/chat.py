import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.api.deps import get_paper_store
from app.config import settings
from app.models.request import ChatRequest
from app.repositories.paper_store import PaperStore
from app.services import rag_service

router = APIRouter()

SYSTEM_PROMPT = """You are an academic research assistant.
Answer the user's question based ONLY on the provided context from research papers.
If the context does not contain enough information, say so clearly.
Cite relevant parts of the context when answering.
Respond in the same language as the user's question."""


async def _stream_response(query: str, context_chunks: list[str]):
    llm = ChatOpenAI(
        model=settings.llm_model,
        openai_api_key=settings.openai_api_key,
        streaming=True,
    )

    context = "\n\n---\n\n".join(context_chunks)
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Context:\n{context}\n\nQuestion: {query}"),
    ]

    async for chunk in llm.astream(messages):
        if chunk.content:
            yield f"data: {json.dumps({'delta': chunk.content})}\n\n"

    yield "data: [DONE]\n\n"


@router.post("")
async def chat_stream(
    req: ChatRequest,
    store: PaperStore = Depends(get_paper_store),
) -> StreamingResponse:
    for paper_id in req.paper_ids:
        paper = store.get(paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail=f"Paper {paper_id} not found")
        if paper.status != "ready":
            raise HTTPException(
                status_code=400,
                detail=f"Paper '{paper.title}' is not ready (status: {paper.status})",
            )

    context_chunks = await rag_service.retrieve(req.paper_ids, req.query)
    if not context_chunks:
        raise HTTPException(status_code=404, detail="No relevant content found in selected papers")

    return StreamingResponse(
        _stream_response(req.query, context_chunks),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
