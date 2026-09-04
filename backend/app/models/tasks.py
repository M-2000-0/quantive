"""Task management and meeting scheduling models."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Tasks ─────────────────────────────────────────────────────────────


class Task(Base):
    """User-created tasks with assignment and tracking."""
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(50), default="todo")  # todo, in_progress, done, cancelled
    priority: Mapped[str] = mapped_column(String(20), default="medium")  # low, medium, high, urgent
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    assigned_to: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    due_date: Mapped[str | None] = mapped_column(String(30), nullable=True)
    tags_json: Mapped[list | None] = mapped_column(Text, nullable=True)  # JSON array
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    comments: Mapped[list["TaskComment"]] = relationship(back_populates="task", cascade="all, delete-orphan")


class TaskComment(Base):
    """Comments on tasks."""
    __tablename__ = "task_comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    task: Mapped["Task"] = relationship(back_populates="comments")


# ── Meetings ──────────────────────────────────────────────────────────


class Meeting(Base):
    """Scheduled meetings with attendees."""
    __tablename__ = "meetings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    start_time: Mapped[str] = mapped_column(String(30), nullable=False)
    end_time: Mapped[str] = mapped_column(String(30), nullable=False)
    location: Mapped[str] = mapped_column(String(500), default="")
    meeting_url: Mapped[str] = mapped_column(String(2000), default="")
    recurrence_json: Mapped[dict | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    attendees: Mapped[list["MeetingAttendee"]] = relationship(back_populates="meeting", cascade="all, delete-orphan")


class MeetingAttendee(Base):
    """Meeting attendee with RSVP status."""
    __tablename__ = "meeting_attendees"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    meeting_id: Mapped[str] = mapped_column(String(36), ForeignKey("meetings.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, accepted, declined, tentative
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    meeting: Mapped["Meeting"] = relationship(back_populates="attendees")
