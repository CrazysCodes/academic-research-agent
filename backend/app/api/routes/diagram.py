"""
图表生成路由：LLM → Mermaid 代码。
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from langchain_core.messages import HumanMessage, SystemMessage

from app.api.deps import get_db_session
from app.core.llm import create_chat_llm
from app.models.request import DiagramRequest
from app.repositories import analysis_repo

logger = logging.getLogger(__name__)

router = APIRouter()

_DIAGRAM_PROMPTS: dict[str, str] = {
    "relationship": (
        "根据以下学术分析报告，生成一个 Mermaid 关系图（graph LR），展示论文/概念之间的关系。\n"
        "只输出 Mermaid 代码，不要加 ```mermaid 围栏，不要加任何解释文字。"
    ),
    "flowchart": (
        "根据以下学术分析报告，生成一个 Mermaid 流程图（flowchart TD），展示研究方法或论证逻辑的流程。\n"
        "只输出 Mermaid 代码，不要加 ```mermaid 围栏，不要加任何解释文字。"
    ),
    "timeline": (
        "根据以下学术分析报告，生成一个 Mermaid 时间线图（timeline），展示研究发展脉络或关键节点。\n"
        "只输出 Mermaid 代码，不要加 ```mermaid 围栏，不要加任何解释文字。"
    ),
}


@router.post("/{analysis_id}/diagram")
async def generate_diagram(
    analysis_id: str,
    req: DiagramRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """从分析报告生成 Mermaid 图表代码。"""
    analysis = await analysis_repo.get(db, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    system_prompt = _DIAGRAM_PROMPTS.get(req.diagram_type)
    if not system_prompt:
        raise HTTPException(status_code=400, detail=f"Unsupported diagram type: {req.diagram_type}")

    llm = create_chat_llm(streaming=False)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=analysis.result or "（无报告内容）"),
    ]

    logger.info("生成 Mermaid 图表，analysis_id=%s，type=%s", analysis_id, req.diagram_type)
    response = await llm.ainvoke(messages)
    mermaid_code = response.content.strip()

    # 清理可能残留的 markdown 围栏
    if mermaid_code.startswith("```"):
        lines = mermaid_code.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        mermaid_code = "\n".join(lines).strip()

    return {"mermaid_code": mermaid_code}
