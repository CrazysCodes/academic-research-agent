"""
Analysis 历史记录 Repository。
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer, selectinload

from app.db.models import AnalysisORM, AnalysisPaperORM


async def create(
    db: AsyncSession,
    *,
    query: str,
    mode: str,
    paper_ids: list[str],
    result: str,
    score: int,
    iterations: int,
    node_outputs: dict | None = None,
) -> AnalysisORM:
    analysis = AnalysisORM(
        query=query,
        mode=mode,
        result=result,
        score=score,
        iterations=iterations,
        node_outputs=node_outputs,
    )
    db.add(analysis)
    await db.flush()
    for pid in paper_ids:
        db.add(AnalysisPaperORM(analysis_id=analysis.id, paper_id=pid))
    await db.commit()
    await db.refresh(analysis)
    return analysis


async def list_all(db: AsyncSession, *, include_detail: bool = True) -> list[AnalysisORM]:
    options = [selectinload(AnalysisORM.paper_links)]
    if not include_detail:
        # 历史侧栏只需要摘要字段，跳过报告正文/节点输出等大字段，首屏会更快。
        options.extend([
            defer(AnalysisORM.result),
            defer(AnalysisORM.node_outputs),
            defer(AnalysisORM.refinements),
        ])

    result = await db.execute(
        select(AnalysisORM)
        .options(*options)
        .order_by(AnalysisORM.created_at.desc())
    )
    return list(result.scalars())


async def get(db: AsyncSession, analysis_id: str) -> AnalysisORM | None:
    result = await db.execute(
        select(AnalysisORM)
        .where(AnalysisORM.id == analysis_id)
        .options(selectinload(AnalysisORM.paper_links))
    )
    return result.scalar_one_or_none()


async def append_refinement(
    db: AsyncSession,
    analysis_id: str,
    new_result: str,
    entries: list[dict],
) -> AnalysisORM | None:
    """Update the analysis result and append refinement entries."""
    row = await db.get(AnalysisORM, analysis_id)
    if not row:
        return None
    row.result = new_result
    existing = list(row.refinements or [])
    existing.extend(entries)
    row.refinements = existing
    await db.commit()
    await db.refresh(row)
    return row


async def delete(db: AsyncSession, analysis_id: str) -> bool:
    row = await db.get(AnalysisORM, analysis_id)
    if not row:
        return False
    await db.delete(row)
    await db.commit()
    return True
