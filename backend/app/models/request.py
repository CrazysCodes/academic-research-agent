from typing import Literal
from pydantic import BaseModel


class ChatRequest(BaseModel):
    paper_ids: list[str]
    query: str


class AnalyzeRequest(BaseModel):
    paper_ids: list[str]
    query: str
    mode: Literal["single", "compare"] = "single"
