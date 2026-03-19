"""
Paper 数据库 Repository（异步 SQLAlchemy + PostgreSQL）。
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PaperORM
from app.models.paper import Paper


def _to_paper(row: PaperORM) -> Paper:
    return Paper(
        id=row.id,
        title=row.title,
        filename=row.filename,
        status=row.status,  # type: ignore[arg-type]
        error=row.error,
        chunk_count=row.chunk_count,
        created_at=row.created_at,
    )


async def create(db: AsyncSession, paper: Paper) -> Paper:
    row = PaperORM(
        id=paper.id,
        title=paper.title,
        filename=paper.filename,
        status=paper.status,
        error=paper.error,
        chunk_count=paper.chunk_count,
        created_at=paper.created_at,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _to_paper(row)


async def get(db: AsyncSession, paper_id: str) -> Paper | None:
    row = await db.get(PaperORM, paper_id)
    return _to_paper(row) if row else None


async def list_all(db: AsyncSession) -> list[Paper]:
    result = await db.execute(select(PaperORM).order_by(PaperORM.created_at.desc()))
    return [_to_paper(r) for r in result.scalars()]


async def update(db: AsyncSession, paper: Paper) -> Paper:
    row = await db.get(PaperORM, paper.id)
    if not row:
        raise ValueError(f"Paper {paper.id} not found")
    row.status = paper.status
    row.error = paper.error
    row.chunk_count = paper.chunk_count
    await db.commit()
    await db.refresh(row)
    return _to_paper(row)


async def delete(db: AsyncSession, paper_id: str) -> bool:
    row = await db.get(PaperORM, paper_id)
    if not row:
        return False
    await db.delete(row)
    await db.commit()
    return True
