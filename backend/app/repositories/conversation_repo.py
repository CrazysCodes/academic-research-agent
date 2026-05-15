"""
Conversation + Message 数据库 Repository。
"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import ConversationORM, ConversationPaperORM, MessageORM


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ──────────────────────────── Conversation ──────────────────────────────────


async def create_conversation(
    db: AsyncSession,
    title: str = "新对话",
    paper_ids: list[str] | None = None,
) -> ConversationORM:
    conv = ConversationORM(title=title)
    db.add(conv)
    await db.flush()  # 获取 id
    if paper_ids:
        for pid in paper_ids:
            db.add(ConversationPaperORM(conversation_id=conv.id, paper_id=pid))
    await db.commit()
    await db.refresh(conv)
    return conv


async def get_conversation(db: AsyncSession, conv_id: str) -> ConversationORM | None:
    result = await db.execute(
        select(ConversationORM)
        .where(ConversationORM.id == conv_id)
        .options(
            selectinload(ConversationORM.messages),
            selectinload(ConversationORM.paper_links),
        )
    )
    return result.scalar_one_or_none()


async def list_conversations(db: AsyncSession, *, include_messages: bool = False) -> list[ConversationORM]:
    options = [selectinload(ConversationORM.paper_links)]
    if include_messages:
        # 首屏默认选中最近会话时，列表接口可一次带回消息，避免前端再串行请求详情。
        options.append(selectinload(ConversationORM.messages))

    result = await db.execute(
        select(ConversationORM)
        .options(*options)
        .order_by(ConversationORM.updated_at.desc())
    )
    return list(result.scalars())


async def delete_conversation(db: AsyncSession, conv_id: str) -> bool:
    row = await db.get(ConversationORM, conv_id)
    if not row:
        return False
    await db.delete(row)
    await db.commit()
    return True


async def update_conversation_title(db: AsyncSession, conv_id: str, title: str) -> ConversationORM | None:
    row = await db.get(ConversationORM, conv_id)
    if not row:
        return None
    row.title = title
    row.updated_at = _now()
    await db.commit()
    await db.refresh(row)
    return row


# ──────────────────────────── Messages ──────────────────────────────────────


async def add_message(
    db: AsyncSession,
    conv_id: str,
    role: str,
    content: str,
) -> MessageORM:
    msg = MessageORM(conversation_id=conv_id, role=role, content=content)
    db.add(msg)
    # 同时更新 conversation.updated_at
    conv = await db.get(ConversationORM, conv_id)
    if conv:
        conv.updated_at = _now()
    await db.commit()
    await db.refresh(msg)
    return msg
