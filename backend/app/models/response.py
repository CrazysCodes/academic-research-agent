from pydantic import BaseModel
from app.models.paper import Paper


class UploadResponse(BaseModel):
    paper: Paper
    message: str = "Processing started"


class PaperListResponse(BaseModel):
    papers: list[Paper]


class PaperStatusResponse(BaseModel):
    paper_id: str
    status: str
    chunk_count: int
    error: str | None = None
