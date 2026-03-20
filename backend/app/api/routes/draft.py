"""
写作草稿辅助路由：基于分析报告 + 论文全文生成章节草稿（SSE 流式）。
"""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from langchain_core.messages import HumanMessage, SystemMessage

from app.api.deps import get_db_session
from app.core.llm import create_chat_llm
from app.models.request import DraftSectionRequest
from app.repositories import analysis_repo, vector_repo

logger = logging.getLogger(__name__)

router = APIRouter()

_MAX_DRAFT_CONTEXT_CHARS = 40_000

_SECTION_PROMPTS: dict[str, str] = {
    "abstract": (
        "你是一位学术论文写作助手。请基于以下分析报告和论文原文，撰写一份学术论文摘要（Abstract）。\n"
        "要求：\n"
        "- 包含研究背景、目的、方法、主要发现和结论\n"
        "- 语言简洁、学术化\n"
        "- 目标字数：{target_length} 字左右\n"
        "- 使用与分析报告相同的语言"
    ),
    "introduction": (
        "你是一位学术论文写作助手。请基于以下分析报告和论文原文，撰写一份学术论文引言（Introduction）。\n"
        "要求：\n"
        "- 介绍研究背景和动机\n"
        "- 指出研究空白或问题\n"
        "- 说明本研究的目的和贡献\n"
        "- 简要概述文章结构\n"
        "- 目标字数：{target_length} 字左右\n"
        "- 使用与分析报告相同的语言"
    ),
    "related_work": (
        "你是一位学术论文写作助手。请基于以下分析报告和论文原文，撰写一份相关工作综述（Related Work）。\n"
        "要求：\n"
        "- 按主题或方法分类组织文献\n"
        "- 总结每类工作的核心思想和局限性\n"
        "- 指出与本研究的关系和区别\n"
        "- 目标字数：{target_length} 字左右\n"
        "- 使用与分析报告相同的语言"
    ),
}


async def _stream_draft(analysis_id: str, section_type: str, target_length: int, db: AsyncSession):
    """流式生成章节草稿。"""
    analysis = await analysis_repo.get(db, analysis_id)
    if not analysis:
        yield f"data: {json.dumps({'error': 'Analysis not found'})}\n\n"
        return

    # 加载论文全文上下文
    paper_ids = [link.paper_id for link in analysis.paper_links]
    context_chunks: list[str] = []
    total_chars = 0
    for paper_id in paper_ids:
        try:
            chunks = vector_repo.get_all_chunks(paper_id)
            for c in chunks:
                if total_chars + len(c["text"]) > _MAX_DRAFT_CONTEXT_CHARS:
                    break
                context_chunks.append(c["text"])
                total_chars += len(c["text"])
            if total_chars >= _MAX_DRAFT_CONTEXT_CHARS:
                break
        except Exception as e:
            logger.warning("加载论文 %s 失败: %s", paper_id, e)

    context_text = "\n\n---\n\n".join(context_chunks) if context_chunks else "（未获取到论文内容）"

    system_prompt = _SECTION_PROMPTS[section_type].format(target_length=target_length)
    system_prompt += f"\n\n## 分析报告\n{analysis.result}\n\n## 论文原文片段\n{context_text}"

    llm = create_chat_llm(streaming=True)
    section_name = {"abstract": "摘要", "introduction": "引言", "related_work": "相关工作"}[section_type]
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"请撰写{section_name}章节。"),
    ]

    logger.info("生成章节草稿，analysis_id=%s，section=%s", analysis_id, section_type)

    async for chunk in llm.astream(messages):
        if chunk.content:
            yield f"data: {json.dumps({'delta': chunk.content})}\n\n"

    yield "data: [DONE]\n\n"


@router.post("/{analysis_id}/draft-section")
async def draft_section(
    analysis_id: str,
    req: DraftSectionRequest,
    db: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    """基于分析报告生成指定章节草稿（SSE 流式输出）。"""
    if req.section_type not in _SECTION_PROMPTS:
        raise HTTPException(status_code=400, detail=f"Unsupported section type: {req.section_type}")

    analysis = await analysis_repo.get(db, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return StreamingResponse(
        _stream_draft(analysis_id, req.section_type, req.target_length, db),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
