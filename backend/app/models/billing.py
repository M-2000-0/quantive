"""Persistent billing storage (subscriptions + usage metering).

Replaces the original in-memory dicts in app/billing.py so that:
- paying users keep their plan across server restarts
- daily usage counters survive restarts (no free quota reset per reboot)

Timestamps are stored as ISO strings to preserve the exact lexicographic
comparison semantics the original in-memory implementation used.
"""
from sqlalchemy import String, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SubscriptionRow(Base):
    __tablename__ = "billing_subscriptions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    tier: Mapped[str] = mapped_column(String(32), nullable=False)  # free | pro | enterprise
    billing_cycle: Mapped[str] = mapped_column(String(16), default="monthly", nullable=False)
    stripe_customer_id: Mapped[str] = mapped_column(String(128), default="", index=True)
    stripe_subscription_id: Mapped[str] = mapped_column(String(128), default="", index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    current_period_start: Mapped[str] = mapped_column(String(40), default="")
    current_period_end: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    updated_at: Mapped[str] = mapped_column(String(40), default="", nullable=False)


class UsageRow(Base):
    __tablename__ = "billing_usage"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    resource: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g. optimizations_per_day
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    timestamp: Mapped[str] = mapped_column(String(40), default="", nullable=False)


Index("ix_billing_usage_org_resource_ts", UsageRow.org_id, UsageRow.resource, UsageRow.timestamp)
