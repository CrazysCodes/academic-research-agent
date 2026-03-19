import asyncio
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.db.database import AsyncSessionLocal
from app.models.paper import Paper
from app.models.response import PaperListResponse, PaperStatusResponse, UploadResponse
from app.repositories import paper_repo, vector_repo
from app.services import doc_service, rag_service

router = APIRouter()

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


async def _process_paper(paper_id: str, filename: str, content: bytes) -> None:
    """后台任务：解析 → 切块 → 向量化 → 写入 Qdrant，完成后更新 DB。"""
    async with AsyncSessionLocal() as db:
        paper = await paper_repo.get(db, paper_id)
        if not paper:
            return
        try:
            markdown = await asyncio.to_thread(doc_service.parse_document, filename, content)
            chunk_count = await rag_service.index_paper(paper_id, markdown)
            paper.status = "ready"
            paper.chunk_count = chunk_count
        except Exception as exc:
            paper.status = "failed"
            paper.error = str(exc)
        finally:
            await paper_repo.update(db, paper)


@router.post("/upload", response_model=UploadResponse)
async def upload_paper(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    db: AsyncSession = Depends(get_db_session),
) -> UploadResponse:
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 50 MB)")

    paper = Paper(title=title, filename=file.filename or "unknown")
    saved = await paper_repo.create(db, paper)
    background_tasks.add_task(_process_paper, saved.id, saved.filename, content)
    return UploadResponse(paper=saved)


@router.get("", response_model=PaperListResponse)
async def list_papers(db: AsyncSession = Depends(get_db_session)) -> PaperListResponse:
    papers = await paper_repo.list_all(db)
    return PaperListResponse(papers=papers)


@router.get("/{paper_id}")
async def get_paper(
    paper_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    paper = await paper_repo.get(db, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@router.get("/{paper_id}/chunks")
async def get_paper_chunks(
    paper_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    paper = await paper_repo.get(db, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    chunks = vector_repo.get_all_chunks(paper_id)
    return {"paper_id": paper_id, "chunks": chunks}


@router.get("/{paper_id}/status", response_model=PaperStatusResponse)
async def get_paper_status(
    paper_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> PaperStatusResponse:
    paper = await paper_repo.get(db, paper_id)
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
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    paper = await paper_repo.get(db, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    vector_repo.delete_collection(paper_id)
    await paper_repo.delete(db, paper_id)
    return {"message": "Deleted"}
