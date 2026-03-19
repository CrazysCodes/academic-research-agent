"""
会话历史 CRUD 路由。
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.repositories import conversation_repo

router = APIRouter()


# ──────────────────────────── 请求 / 响应 Schema ────────────────────────────


class ConversationCreate(BaseModel):
    title: str = "新对话"
    paper_ids: list[str] = []


class MessageSchema(BaseModel):
    id: str
    role: str
    content: str
    created_at: str


class ConversationSchema(BaseModel):
    id: str
    title: str
    paper_ids: list[str]
    created_at: str
    updated_at: str
    messages: list[MessageSchema] = []


def _to_schema(conv, include_messages: bool = False) -> ConversationSchema:
    paper_ids = [link.paper_id for link in conv.paper_links]
    messages = (
        [MessageSchema(id=m.id, role=m.role, content=m.content, created_at=m.created_at)
         for m in conv.messages]
        if include_messages
        else []
    )
    return ConversationSchema(
        id=conv.id,
        title=conv.title,
        paper_ids=paper_ids,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=messages,
    )


# ──────────────────────────── 路由 ──────────────────────────────────────────


@router.post("", response_model=ConversationSchema, status_code=201)
async def create_conversation(
    body: ConversationCreate,
    db: AsyncSession = Depends(get_db_session),
):
    conv = await conversation_repo.create_conversation(db, body.title, body.paper_ids)
    # 重新加载带关联数据的版本
    conv = await conversation_repo.get_conversation(db, conv.id)
    return _to_schema(conv)  # type: ignore[arg-type]


@router.get("", response_model=list[ConversationSchema])
async def list_conversations(db: AsyncSession = Depends(get_db_session)):
    convs = await conversation_repo.list_conversations(db)
    return [_to_schema(c) for c in convs]


@router.get("/{conv_id}", response_model=ConversationSchema)
async def get_conversation(
    conv_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    conv = await conversation_repo.get_conversation(db, conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return _to_schema(conv, include_messages=True)


@router.patch("/{conv_id}/title")
async def rename_conversation(
    conv_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db_session),
):
    conv = await conversation_repo.update_conversation_title(db, conv_id, body.get("title", ""))
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"id": conv.id, "title": conv.title}


@router.delete("/{conv_id}", status_code=204)
async def delete_conversation(
    conv_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    deleted = await conversation_repo.delete_conversation(db, conv_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")


class AddMessageBody(BaseModel):
    role: str
    content: str


@router.post("/{conv_id}/messages", response_model=MessageSchema, status_code=201)
async def add_message(
    conv_id: str,
    body: AddMessageBody,
    db: AsyncSession = Depends(get_db_session),
):
    conv = await conversation_repo.get_conversation(db, conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    msg = await conversation_repo.add_message(db, conv_id, body.role, body.content)
    return MessageSchema(id=msg.id, role=msg.role, content=msg.content, created_at=msg.created_at)
