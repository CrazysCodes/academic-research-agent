"""
报告导出路由：Markdown 文件下载。
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.repositories import analysis_repo, paper_repo

router = APIRouter()


def _build_markdown(analysis, paper_titles: list[str]) -> str:
    """组装完整 Markdown 报告文档。"""
    lines: list[str] = []

    # 标题 + 元信息
    title = analysis.query[:60] + ("…" if len(analysis.query) > 60 else "")
    lines.append(f"# {title}\n")
    lines.append(f"> 生成时间：{analysis.created_at}\n")

    # 研究问题
    lines.append("## 研究问题\n")
    lines.append(f"{analysis.query}\n")

    # 选中文献
    if paper_titles:
        lines.append("## 参考文献\n")
        for i, t in enumerate(paper_titles, 1):
            lines.append(f"{i}. {t}")
        lines.append("")

    # Agent 执行摘要
    lines.append("## Agent 执行摘要\n")
    lines.append(f"- 分析模式：{analysis.mode}")
    lines.append(f"- 质量评分：{analysis.score}/10")
    lines.append(f"- 撰写轮次：{analysis.iterations}")
    if analysis.node_outputs:
        planner = analysis.node_outputs.get("planner", {})
        sub_queries = planner.get("sub_queries", [])
        if sub_queries:
            lines.append(f"- 子查询：")
            for sq in sub_queries:
                lines.append(f"  - {sq}")
    lines.append("")

    # 正文
    lines.append("## 分析报告\n")
    lines.append(analysis.result or "（无内容）")
    lines.append("")

    # 优化历史
    refinements = analysis.refinements or []
    if refinements:
        lines.append("## 优化历史\n")
        for r in refinements:
            role_label = "用户" if r.get("role") == "user" else "AI"
            lines.append(f"**{role_label}**：{r.get('content', '')}\n")

    return "\n".join(lines)


@router.get("/{analysis_id}/export/markdown")
async def export_markdown(
    analysis_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    """导出分析报告为 Markdown 文件。"""
    analysis = await analysis_repo.get(db, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    # 获取关联论文标题
    paper_titles: list[str] = []
    for link in analysis.paper_links:
        paper = await paper_repo.get(db, link.paper_id)
        if paper:
            paper_titles.append(paper.title)

    md_content = _build_markdown(analysis, paper_titles)
    filename = f"analysis-{analysis_id[:8]}.md"

    return Response(
        content=md_content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
