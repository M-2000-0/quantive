"""Personal-DB models. All rows are keyed by user_id (owner). No sovereign FKs."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.personal.database import PersonalBase


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class PersonalProfile(PersonalBase):
    """One row per user: onboarding state + derived score cache."""

    __tablename__ = "personal_profiles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), default="")
    tax_year: Mapped[int] = mapped_column(default=2026)
    jurisdiction: Mapped[str] = mapped_column(String(16), default="")  # e.g. MX, US
    onboarding_status: Mapped[str] = mapped_column(String(24), default="not_started")
    onboarding_current: Mapped[int] = mapped_column(default=0)
    score: Mapped[int] = mapped_column(default=0)
    score_detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class ProfileFact(PersonalBase):
    """Structured memory: one fact per row, user owns/corrects it."""

    __tablename__ = "personal_profile_facts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: _id("fact"))
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(48), index=True, nullable=False)
    key: Mapped[str] = mapped_column(String(96), index=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, default="")
    value_json: Mapped[dict] = mapped_column(JSON, default=dict)
    source: Mapped[str] = mapped_column(String(32), default="onboarding")
    confidence: Mapped[str] = mapped_column(String(32), default="user_reported")
    status: Mapped[str] = mapped_column(String(32), default="unconfirmed")
    fact_date: Mapped[str] = mapped_column(String(16), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


Index("ix_personal_facts_user_cat_key", ProfileFact.user_id, ProfileFact.category, ProfileFact.key, unique=True)


class PersonalOpportunity(PersonalBase):
    """Detected opportunity. Relevance only — never guaranteed savings."""

    __tablename__ = "personal_opportunities"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: _id("opp"))
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    tax_year: Mapped[int] = mapped_column(default=2026)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(64), default="")
    relevance: Mapped[str] = mapped_column(String(16), default="low")  # high|medium|low
    status: Mapped[str] = mapped_column(String(32), default="potentially_relevant")
    why: Mapped[str] = mapped_column(Text, default="")
    needs_info: Mapped[list] = mapped_column(JSON, default=list)
    needs_docs: Mapped[list] = mapped_column(JSON, default=list)
    rule_refs: Mapped[list] = mapped_column(JSON, default=list)
    next_action: Mapped[str] = mapped_column(Text, default="")
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class PersonalTask(PersonalBase):
    """Unified Action Center tasks."""

    __tablename__ = "personal_tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: _id("task"))
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(16), default="medium")
    status: Mapped[str] = mapped_column(String(24), default="open")
    due: Mapped[str] = mapped_column(String(16), default="")
    link: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class PersonalDocument(PersonalBase):
    """Document metadata only. File bytes stay in existing upload store."""

    __tablename__ = "personal_documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: _id("doc"))
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    tax_year: Mapped[int] = mapped_column(default=2026)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(48), default="other")
    storage_path: Mapped[str] = mapped_column(String(512), default="")
    status: Mapped[str] = mapped_column(String(32), default="uploaded")
    extracted: Mapped[dict] = mapped_column(JSON, default=dict)
    related_opps: Mapped[list] = mapped_column(JSON, default=list)
    review_status: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class TaxRule(PersonalBase):
    """Versioned tax knowledge. No advice text in frontend — everything cites a rule."""

    __tablename__ = "personal_tax_rules"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)  # e.g. MX-2026-mortgage-interest
    jurisdiction: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    tax_year: Mapped[int] = mapped_column(index=True, nullable=False)
    topic: Mapped[str] = mapped_column(String(96), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="")
    requirements: Mapped[list] = mapped_column(JSON, default=list)
    docs_required: Mapped[list] = mapped_column(JSON, default=list)
    limits: Mapped[dict] = mapped_column(JSON, default=dict)
    sources: Mapped[list] = mapped_column(JSON, default=list)
    effective_from: Mapped[str] = mapped_column(String(16), default="")
    effective_to: Mapped[str] = mapped_column(String(16), default="")


class PersonalAudit(PersonalBase):
    """Product-scoped audit log (separate from sovereign AuditEvent on purpose)."""

    __tablename__ = "personal_audit"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: _id("audit"))
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(96), nullable=False)
    entity: Mapped[str] = mapped_column(String(64), default="")
    entity_id: Mapped[str] = mapped_column(String(64), default="")
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
