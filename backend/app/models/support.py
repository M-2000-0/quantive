"""Customer support models — tickets, FAQ, bug reports."""
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


# ── Support Tickets ────────────────────────────────────────────────


class SupportTicket(Base):
    """Customer support ticket with classification and escalation."""
    __tablename__ = "support_tickets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="open")  # open, in_progress, waiting, resolved, closed
    priority: Mapped[str] = mapped_column(String(20), default="medium")  # low, medium, high, urgent
    category: Mapped[str] = mapped_column(String(100), default="general")  # billing, technical, feature_request, bug, general
    assigned_to: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    sla_deadline: Mapped[str | None] = mapped_column(String(30), nullable=True)
    escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    escalation_level: Mapped[int] = mapped_column(Integer, default=0)
    resolution_notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    messages: Mapped[list["SupportMessage"]] = relationship(back_populates="ticket", cascade="all, delete-orphan")


class SupportMessage(Base):
    """Messages within a support ticket."""
    __tablename__ = "support_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    ticket_id: Mapped[str] = mapped_column(String(36), ForeignKey("support_tickets.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False)  # internal notes
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    ticket: Mapped["SupportTicket"] = relationship(back_populates="messages")


# ── FAQ ────────────────────────────────────────────────────────────


class FAQCategory(Base):
    """FAQ category for organization."""
    __tablename__ = "faq_categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    items: Mapped[list["FAQItem"]] = relationship(back_populates="category", cascade="all, delete-orphan")


class FAQItem(Base):
    """Individual FAQ entry."""
    __tablename__ = "faq_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    category_id: Mapped[str] = mapped_column(String(36), ForeignKey("faq_categories.id"), nullable=False, index=True)
    question: Mapped[str] = mapped_column(String(1000), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    helpful_count: Mapped[int] = mapped_column(Integer, default=0)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    category: Mapped["FAQCategory"] = relationship(back_populates="items")


# ── Bug Reports ───────────────────────────────────────────────────


class BugReport(Base):
    """Bug report with lifecycle tracking."""
    __tablename__ = "bug_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    reported_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="medium")  # low, medium, high, critical
    status: Mapped[str] = mapped_column(String(50), default="open")  # open, confirmed, in_progress, fixed, wont_fix, closed
    assigned_to: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    steps_to_reproduce: Mapped[str] = mapped_column(Text, default="")
    expected_behavior: Mapped[str] = mapped_column(Text, default="")
    actual_behavior: Mapped[str] = mapped_column(Text, default="")
    environment: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
