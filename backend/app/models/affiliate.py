"""Affiliate program models — referral tracking and commission management for Qubo Tax.

Commission structure: recurring % of referred user's Qubo subscription.
Manual payouts tracked in the dashboard."""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy import JSON as SAJSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uid() -> str:
    import uuid
    return str(uuid.uuid4())


class AffiliateProgram(Base):
    """Affiliate account — one per user who joins the program.

    Each affiliate gets a unique referral code and tracks their own
    referral stats and earnings."""
    __tablename__ = "affiliate_programs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    referral_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    commission_rate: Mapped[float] = mapped_column(Float, default=0.20, nullable=False)  # 20% recurring
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    payout_email: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)


class Referral(Base):
    """A referred user — tracks who was referred by whom and when.

    When a new user signs up with a referral code, a Referral is created.
    The referred_user_id is set after they complete registration."""
    __tablename__ = "affiliate_referrals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    affiliate_id: Mapped[str] = mapped_column(String(36), ForeignKey("affiliate_programs.id"), nullable=False, index=True)
    referred_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    referred_org_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=True)
    referral_code: Mapped[str] = mapped_column(String(32), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    landing_page: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    # pending | registered | converted | churned
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    registered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    converted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)


Index("ix_referral_code", Referral.referral_code)


class Commission(Base):
    """Commission record — tracks earnings per referred user per billing period.

    Created when a referred user pays for Qubo Tax. The affiliate earns
    commission_rate % of the payment amount. Manual payouts are tracked
    via the payout fields."""
    __tablename__ = "affiliate_commissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    affiliate_id: Mapped[str] = mapped_column(String(36), ForeignKey("affiliate_programs.id"), nullable=False, index=True)
    referral_id: Mapped[str] = mapped_column(String(36), ForeignKey("affiliate_referrals.id"), nullable=False, index=True)
    referred_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    billing_period: Mapped[str] = mapped_column(String(32), nullable=False)  # e.g. "2026-01"
    subscription_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    commission_rate: Mapped[float] = mapped_column(Float, nullable=False)
    commission_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    # pending | approved | paid | cancelled
    payout_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)


class Payout(Base):
    """Manual payout record — admin marks commissions as paid."""
    __tablename__ = "affiliate_payouts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    affiliate_id: Mapped[str] = mapped_column(String(36), ForeignKey("affiliate_programs.id"), nullable=False, index=True)
    commission_ids: Mapped[list] = mapped_column(SAJSON, nullable=False, default=list)  # list of commission IDs included
    total_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    method: Mapped[str] = mapped_column(String(32), default="manual", nullable=False)
    # manual | stripe | bank_transfer | crypto
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    # pending | completed | failed
    admin_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)


class ReferralClick(Base):
    """Tracks referral link clicks for analytics."""
    __tablename__ = "affiliate_clicks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    referral_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    landing_page: Mapped[str | None] = mapped_column(String(512), nullable=True)
    referrer: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
