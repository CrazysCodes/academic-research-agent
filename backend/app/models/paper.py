from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field
import uuid


class Paper(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    filename: str
    status: Literal["processing", "ready", "failed"] = "processing"
    error: str | None = None
    chunk_count: int = 0
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
