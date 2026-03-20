"""
引用格式化路由：从论文元数据 + LLM 生成格式化引用。
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from langchain_core.messages import HumanMessage, SystemMessage

from app.api.deps import get_db_session
from app.core.llm import create_chat_llm
from app.models.request import CitationRequest
from app.repositories import paper_repo, vector_repo

logger = logging.getLogger(__name__)

router = APIRouter()

_CITATION_SYSTEM_PROMPT = """你是一位学术引用格式化专家。

根据以下论文信息，生成 {format} 格式的引用。如果信息不完整，请根据已有信息合理推断。

## 论文标题
{title}

## 论文文件名
{filename}

## 论文首页内容
{first_chunk}

请直接输出格式化后的引用文本，不要加任何解释或前缀。"""


@router.post("/{paper_id}/citation")
async def generate_citation(
    paper_id: str,
    req: CitationRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """生成指定格式的论文引用。"""
    paper = await paper_repo.get(db, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    # 从 Qdrant 获取论文首页内容（第一个 chunk 通常包含标题、作者等元信息）
    first_chunk = ""
    try:
        chunks = vector_repo.get_all_chunks(paper_id)
        if chunks:
            # 取前 3 个 chunk 以获取足够的元信息
            first_chunk = "\n\n".join(c["text"] for c in chunks[:3])
    except Exception as e:
        logger.warning("获取论文 chunk 失败: %s", e)

    format_labels = {
        "apa": "APA (7th edition)",
        "mla": "MLA (9th edition)",
        "ieee": "IEEE",
        "bibtex": "BibTeX",
    }
    format_label = format_labels.get(req.format, req.format.upper())

    llm = create_chat_llm(streaming=False)
    prompt = _CITATION_SYSTEM_PROMPT.format(
        format=format_label,
        title=paper.title,
        filename=paper.filename,
        first_chunk=first_chunk[:3000] if first_chunk else "（无法获取论文内容）",
    )

    logger.info("生成引用，paper_id=%s，format=%s", paper_id, req.format)
    response = await llm.ainvoke([
        SystemMessage(content=prompt),
        HumanMessage(content=f"请生成 {format_label} 格式的引用。"),
    ])

    return {"citation": response.content.strip()}
