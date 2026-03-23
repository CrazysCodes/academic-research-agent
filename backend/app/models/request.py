from typing import Literal
from pydantic import BaseModel


class ChatRequest(BaseModel):
    paper_ids: list[str]
    query: str


class AnalyzeRequest(BaseModel):
    paper_ids: list[str]
    query: str
    mode: Literal["single", "compare"] = "single"


class RefineRequest(BaseModel):
    instruction: str


class DiagramRequest(BaseModel):
    diagram_type: Literal["relationship", "flowchart", "timeline"]


class CitationRequest(BaseModel):
    format: Literal["apa", "mla", "ieee", "bibtex"]


class DraftSectionRequest(BaseModel):
    section_type: Literal["abstract", "introduction", "related_work"]
    target_length: int = 500
