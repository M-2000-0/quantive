"""Qubo Tax models — business deduction findings and tax documents.

These models are logically separate from Banking but reference Banking
data (BankAccount, BankTransaction) via foreign keys, representing a
legitimate cross-product data dependency.
"""
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy import JSON as SAJSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class QuboFinding(Base):
    """Business deduction finding from a Qubo ledger scan.

    Honesty contract (mirrors personal tax_packs): relevance + requirements
    only. ``amount_cents`` is the outflow that *may* qualify — never a
    promised saving, never an eligibility guarantee. Every finding traces
    to a versioned rule (jurisdiction x tax year) or it does not exist."""

    __tablename__ = "qubo_findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    account_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("bank_accounts.id"), nullable=True)
    txn_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("bank_transactions.id"), nullable=True)
    rule_id: Mapped[str] = mapped_column(String(64), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(8), default="US", nullable=False)
    tax_year: Mapped[int] = mapped_column(Integer, default=2026, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="", nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    requirements: Mapped[dict] = mapped_column(SAJSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="new", nullable=False)
    # new | accepted | dismissed
    created_at: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=_utcnow, onupdate=_utcnow, nullable=False)


Index("ix_qubo_findings_org_txn_rule", QuboFinding.org_id, QuboFinding.txn_id, QuboFinding.rule_id)


class TaxDocument(Base):
    """Uploaded tax document linked to a Qubo finding.

    File bytes stored on disk; metadata indexed for search.
    """

    __tablename__ = "banking_tax_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    finding_id: Mapped[str] = mapped_column(String(36), ForeignKey("qubo_findings.id"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), default="application/octet-stream", nullable=False)
    size_bytes: Mapped[int] = mapped_column(default=0, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    category: Mapped[str] = mapped_column(String(64), default="other", nullable=False)
    # payroll_register, w2, invoice, receipt, utility_bill, travel_record, other
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    extracted: Mapped[dict] = mapped_column(SAJSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="uploaded", nullable=False)
    # uploaded | reviewed | rejected
    created_at: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=_utcnow, onupdate=_utcnow, nullable=False)


Index("ix_tax_docs_org_finding", TaxDocument.org_id, TaxDocument.finding_id)
