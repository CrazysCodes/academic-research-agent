import asyncio
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile

from app.api.deps import get_paper_store
from app.models.paper import Paper
from app.models.response import PaperListResponse, PaperStatusResponse, UploadResponse
from app.repositories.paper_store import PaperStore
from app.repositories import vector_repo
from app.services import doc_service, rag_service

router = APIRouter()

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


async def _process_paper(paper: Paper, content: bytes, store: PaperStore) -> None:
    """Background task: parse → chunk → embed → index."""
    try:
        markdown = await asyncio.to_thread(doc_service.parse_document, paper.filename, content)
        chunk_count = await rag_service.index_paper(paper.id, markdown)
        paper.status = "ready"
        paper.chunk_count = chunk_count
    except Exception as exc:
        paper.status = "failed"
        paper.error = str(exc)
    finally:
        store.update(paper)


@router.post("/upload", response_model=UploadResponse)
async def upload_paper(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    store: PaperStore = Depends(get_paper_store),
) -> UploadResponse:
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 50 MB)")

    paper = Paper(title=title, filename=file.filename or "unknown")
    store.add(paper)
    background_tasks.add_task(_process_paper, paper, content, store)
    return UploadResponse(paper=paper)


@router.get("", response_model=PaperListResponse)
async def list_papers(store: PaperStore = Depends(get_paper_store)) -> PaperListResponse:
    return PaperListResponse(papers=store.list())


@router.get("/{paper_id}/status", response_model=PaperStatusResponse)
async def get_paper_status(
    paper_id: str,
    store: PaperStore = Depends(get_paper_store),
) -> PaperStatusResponse:
    paper = store.get(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return PaperStatusResponse(
        paper_id=paper.id,
        status=paper.status,
        chunk_count=paper.chunk_count,
        error=paper.error,
    )


@router.delete("/{paper_id}")
async def delete_paper(
    paper_id: str,
    store: PaperStore = Depends(get_paper_store),
) -> dict:
    paper = store.get(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    vector_repo.delete_collection(paper_id)
    store.delete(paper_id)
    return {"message": "Deleted"}
