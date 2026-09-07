"""Automation engine models — native workflow features.

Replaces the n8n JSON workflows with in-app automations that run on
real data: CRM leads, onboarding sequences, failed-payment recovery,
MRR tracking, support triage, and system health checks.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Automation(Base):
    """A registered automation (feature job) with schedule + toggle."""
    __tablename__ = "automations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(50), default="ops")  # sales|billing|onboarding|support|ops
    interval_minutes: Mapped[int] = mapped_column(Integer, default=60)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status: Mapped[str] = mapped_column(String(20), default="never")  # never|success|failed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AutomationRun(Base):
    """One execution of an automation, with what it actually did."""
    __tablename__ = "automation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    automation_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="running")  # running|success|failed
    trigger: Mapped[str] = mapped_column(String(20), default="schedule")  # schedule|manual
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    items_scanned: Mapped[int] = mapped_column(Integer, default=0)
    actions_taken: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str] = mapped_column(Text, default="")
    log: Mapped[str] = mapped_column(Text, default="")  # JSON list of action entries
    error: Mapped[str] = mapped_column(Text, default="")


class Lead(Base):
    """CRM lead captured from webhooks, demo requests, or manual entry."""
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(255), default="")
    email: Mapped[str] = mapped_column(String(255), default="", index=True)
    company: Mapped[str] = mapped_column(String(255), default="")
    title: Mapped[str] = mapped_column(String(255), default="")
    source: Mapped[str] = mapped_column(String(50), default="website")  # website|demo|webhook|referral
    stage: Mapped[str] = mapped_column(String(30), default="new")  # new|working|qualified|converted|lost
    score: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    score_reasons: Mapped[str] = mapped_column(Text, default="")  # JSON list
    enriched: Mapped[bool] = mapped_column(Boolean, default=False)
    converted_deal_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class OnboardingSequence(Base):
    """Onboarding progress per organization."""
    __tablename__ = "onboarding_sequences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    user_email: Mapped[str] = mapped_column(String(255), default="")
    step: Mapped[int] = mapped_column(Integer, default=0)  # 0..4 (5 steps)
    emails_sent: Mapped[int] = mapped_column(Integer, default=0)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_email_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DunningCase(Base):
    """Failed-payment recovery for a past_due subscription."""
    __tablename__ = "dunning_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    user_email: Mapped[str] = mapped_column(String(255), default="")
    amount_cents: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="usd")
    attempt: Mapped[int] = mapped_column(Integer, default=0)  # 1..3
    status: Mapped[str] = mapped_column(String(20), default="open")  # open|recovered|canceled
    next_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_email_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MrrEvent(Base):
    """MRR-changing subscription event for revenue tracking/churn."""
    __tablename__ = "mrr_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(30), default="snapshot")  # new|upgrade|downgrade|churn|reactivation|snapshot
    tier: Mapped[str] = mapped_column(String(20), default="free")
    mrr_cents: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
