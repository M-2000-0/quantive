"""Persisted AI chat conversations.

Every conversation is scoped to ``(org_id, user_id)`` so users only ever
see their own threads; messages are stored as rows so the widget can
restore the last conversation after a page reload and switch between
prior conversations.
"""
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ChatConversation(Base):
    """One AI chat thread for a user."""

    __tablename__ = "chat_conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="New conversation", nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=_utcnow, onupdate=_utcnow, nullable=False)


class ChatMessage(Base):
    """A single user/assistant turn inside a conversation."""

    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("chat_conversations.id"), index=True, nullable=False
    )
    org_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # user | assistant
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # Citation snippets shown under the answer (stored so reloads keep them)
    sources: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Suggested follow-up questions offered with this answer (chips in the
    # widget; persisted so restored threads keep their chips).
    suggested_followups: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Per-conversation turn order — timestamps tie within one exchange on
    # Windows (coarse clock), so seq is the authoritative ordering key.
    seq: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)


Index("ix_chat_msgs_conv_seq", ChatMessage.conversation_id, ChatMessage.seq)
