"""Social and collaboration models for the platform.

Watchlists, comments, attachments, tags, activity logs, saved views/filters.
"""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Watchlists ──────────────────────────────────────────────────────────────

class Watchlist(Base):
    """User-created watchlist for monitoring portfolios or instruments."""
    __tablename__ = "watchlists"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    items: Mapped[list["WatchlistItem"]] = relationship(back_populates="watchlist", cascade="all, delete-orphan")


class WatchlistItem(Base):
    """Individual item in a watchlist."""
    __tablename__ = "watchlist_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    watchlist_id: Mapped[str] = mapped_column(String(36), ForeignKey("watchlists.id"), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "portfolio" | "instrument"
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False)
    alert_threshold: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    watchlist: Mapped["Watchlist"] = relationship(back_populates="items")


# ── Comments ────────────────────────────────────────────────────────────────

class Comment(Base):
    """Comments on portfolios, instruments, optimizations, etc."""
    __tablename__ = "comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "portfolio" | "instrument" | "optimization"
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    parent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("comments.id"), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    replies: Mapped[list["Comment"]] = relationship(back_populates="parent")
    parent: Mapped["Comment | None"] = relationship(back_populates="replies", remote_side="Comment.id")


# ── Attachments ─────────────────────────────────────────────────────────────

class Attachment(Base):
    """File attachments for portfolios, optimizations, etc."""
    __tablename__ = "attachments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ── Tags ────────────────────────────────────────────────────────────────────

class Tag(Base):
    """Tags for categorization."""
    __tablename__ = "tags"
    __table_args__ = (
        UniqueConstraint("org_id", "name", name="uq_tags_org_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(7), default="#6366f1")  # hex color
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    tagged_items: Mapped[list["TaggedItem"]] = relationship(back_populates="tag", cascade="all, delete-orphan")


class TaggedItem(Base):
    """Many-to-many: tags to resources."""
    __tablename__ = "tagged_items"
    __table_args__ = (
        UniqueConstraint("tag_id", "resource_type", "resource_id", name="uq_tagged_item"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    tag_id: Mapped[str] = mapped_column(String(36), ForeignKey("tags.id"), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    tag: Mapped["Tag"] = relationship(back_populates="tagged_items")


# ── Activity Log ────────────────────────────────────────────────────────────

class ActivityLog(Base):
    """Audit trail for user actions across the platform."""
    __tablename__ = "activity_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)  # "created", "updated", "deleted", "viewed", etc.
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


# ── Saved Views & Filters ──────────────────────────────────────────────────

class SavedView(Base):
    """User-saved dashboard view configurations."""
    __tablename__ = "saved_views"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    view_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "portfolio", "optimization", "analytics"
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class SavedFilter(Base):
    """User-saved filter presets."""
    __tablename__ = "saved_filters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    filter_type: Mapped[str] = mapped_column(String(50), nullable=False)
    filters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
