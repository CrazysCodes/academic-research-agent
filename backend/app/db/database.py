"""
SQLAlchemy 异步数据库连接（PostgreSQL via asyncpg）。
"""
import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


def _make_engine():
    url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return create_async_engine(url, echo=settings.debug, pool_pre_ping=True)


engine = _make_engine()
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncSession:  # type: ignore[misc]
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """启动时创建所有表（如不存在）。连接失败时仅打 WARNING，不阻断启动。"""
    from app.db import models  # noqa: F401 – 确保模型被注册
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("数据库初始化完成")
    except Exception as e:
        logger.warning(
            "数据库连接失败，持久化功能不可用（启动 PostgreSQL 后重启后端即可）: %s",
            e,
        )
