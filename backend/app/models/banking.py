"""Quantive Banking ledger models (sandbox ledger; partner-bank rail simulated).

Design notes:
- All money is stored as integer minor units (``*_cents``) — never floats.
- ``fee_cents`` columns exist for audit transparency, but the API layer
  enforces ``0`` on every movement. Quantive Banking charges no
  per-transaction fees; revenue comes from deposit spread, subscriptions,
  lending and treasury products — never from hidden fees.
- Every row is org-scoped (``org_id``) so business data never leaks
  across organizations.
"""
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy import JSON as SAJSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BankAccount(Base):
    """Free business account. Funds are notionally held with a regulated
    partner bank (``partner_ref``); this ledger is the system of record
    for the sandbox."""

    __tablename__ = "bank_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    owner_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False, default="Operating")
    account_type: Mapped[str] = mapped_column(String(32), default="operating", nullable=False)
    # operating | reserve | yield
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    balance_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    # active | frozen | closed
    partner_ref: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=_utcnow, onupdate=_utcnow, nullable=False)


class BankTransaction(Base):
    """Single posted/pending ledger movement. ``amount_cents`` is always
    positive; ``direction`` gives the sign. ``fee_cents`` must be 0."""

    __tablename__ = "bank_transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("bank_accounts.id"), index=True, nullable=False
    )
    direction: Mapped[str] = mapped_column(String(8), nullable=False)  # in | out
    txn_type: Mapped[str] = mapped_column(String(32), nullable=False)
    # ach_in | ach_out | transfer_in | transfer_out | payroll | invoice |
    # payout | adjustment | opening_balance
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    fee_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    counterparty: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    memo: Mapped[str] = mapped_column(Text, default="", nullable=False)
    category: Mapped[str] = mapped_column(String(64), default="Uncategorized", nullable=False)
    tax_tag: Mapped[str] = mapped_column(String(64), default="review", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="posted", nullable=False)
    # posted | pending
    transfer_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)


Index("ix_bank_txns_org_idem", BankTransaction.org_id, BankTransaction.idempotency_key)


class BankTransfer(Base):
    """Double-entry movement between two org accounts (or out to an
    external counterparty when ``to_account_id`` is null). Settles
    instantly in the sandbox; a partner rail would settle async."""

    __tablename__ = "bank_transfers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    from_account_id: Mapped[str] = mapped_column(String(36), ForeignKey("bank_accounts.id"), nullable=False)
    to_account_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("bank_accounts.id"), nullable=True)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    fee_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="posted", nullable=False)
    counterparty: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    memo: Mapped[str] = mapped_column(Text, default="", nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)


Index("ix_bank_transfers_org_idem", BankTransfer.org_id, BankTransfer.idempotency_key)


class BusinessProfile(Base):
    """KYB / onboarding profile. One per org. Status machine:
    draft -> pending -> verified | rejected. Only admins can decide."""

    __tablename__ = "banking_business_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    legal_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    dba: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    country: Mapped[str] = mapped_column(String(2), default="US", nullable=False)
    industry: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    tax_id_last4: Mapped[str] = mapped_column(String(4), default="", nullable=False)
    kyb_status: Mapped[str] = mapped_column(String(16), default="draft", nullable=False)
    kyb_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    details: Mapped[dict] = mapped_column(SAJSON, default=dict, nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=_utcnow, onupdate=_utcnow, nullable=False)
