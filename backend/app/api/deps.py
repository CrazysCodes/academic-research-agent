from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.repositories.paper_store import paper_store, PaperStore


# ── 旧内存 store（兼容层，已弃用）──────────────────────────────────────────
def get_paper_store() -> PaperStore:
    return paper_store


# ── DB session ─────────────────────────────────────────────────────────────
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """提供异步 DB session，任何异常直接向上传播，不做包装。"""
    async with AsyncSessionLocal() as session:
        yield session
