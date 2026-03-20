"""
SQLAlchemy ORM 模型。
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uuid() -> str:
    return str(uuid.uuid4())


class PaperORM(Base):
    __tablename__ = "papers"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String, nullable=False)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="processing")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[str] = mapped_column(String, default=_now)

    conversations: Mapped[list["ConversationPaperORM"]] = relationship(
        back_populates="paper", cascade="all, delete-orphan"
    )


class ConversationORM(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String, default="新对话")
    created_at: Mapped[str] = mapped_column(String, default=_now)
    updated_at: Mapped[str] = mapped_column(String, default=_now)

    messages: Mapped[list["MessageORM"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="MessageORM.created_at"
    )
    paper_links: Mapped[list["ConversationPaperORM"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class ConversationPaperORM(Base):
    """多对多：对话 ↔ 论文（关联表）。"""
    __tablename__ = "conversation_papers"

    conversation_id: Mapped[str] = mapped_column(
        String, ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True
    )
    paper_id: Mapped[str] = mapped_column(
        String, ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True
    )

    conversation: Mapped["ConversationORM"] = relationship(back_populates="paper_links")
    paper: Mapped["PaperORM"] = relationship(back_populates="conversations")


class MessageORM(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(
        String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String, nullable=False)  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String, default=_now)

    conversation: Mapped["ConversationORM"] = relationship(back_populates="messages")


class AnalysisORM(Base):
    """多文档分析历史记录。"""
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(String, default="compare")
    result: Mapped[str] = mapped_column(Text, default="")
    score: Mapped[int] = mapped_column(Integer, default=0)
    iterations: Mapped[int] = mapped_column(Integer, default=0)
    node_outputs: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    refinements: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[str] = mapped_column(String, default=_now)

    paper_links: Mapped[list["AnalysisPaperORM"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )


class AnalysisPaperORM(Base):
    """多对多：分析 ↔ 论文（关联表）。"""
    __tablename__ = "analysis_papers"

    analysis_id: Mapped[str] = mapped_column(
        String, ForeignKey("analyses.id", ondelete="CASCADE"), primary_key=True
    )
    paper_id: Mapped[str] = mapped_column(
        String, ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True
    )

    analysis: Mapped["AnalysisORM"] = relationship(back_populates="paper_links")
    paper: Mapped["PaperORM"] = relationship()
