"""add deals, email campaigns tables

Revision ID: 008_management
Revises: 007_support
Create Date: 2026-09-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "008_management"
down_revision: Union[str, None] = "007_support"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Deals (Sales Pipeline) ──────────────────────────────────────────────
    op.create_table(
        "deals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("company", sa.String(255), server_default=""),
        sa.Column("contact_email", sa.String(255), server_default=""),
        sa.Column("value", sa.Float, server_default=sa.text("0")),
        sa.Column("currency", sa.String(3), server_default="USD"),
        sa.Column("stage", sa.String(50), server_default="lead"),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("probability", sa.Integer, server_default=sa.text("10")),
        sa.Column("expected_close_date", sa.String(30), nullable=True),
        sa.Column("notes", sa.Text, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_deals_org_id", "deals", ["org_id"])

    # ── Email Campaigns ─────────────────────────────────────────────────────
    op.create_table(
        "email_campaigns",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("status", sa.String(50), server_default="draft"),
        sa.Column("total_recipients", sa.Integer, server_default=sa.text("0")),
        sa.Column("sent_count", sa.Integer, server_default=sa.text("0")),
        sa.Column("open_count", sa.Integer, server_default=sa.text("0")),
        sa.Column("click_count", sa.Integer, server_default=sa.text("0")),
        sa.Column("scheduled_at", sa.String(30), nullable=True),
        sa.Column("sent_at", sa.String(30), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_email_campaigns_org_id", "email_campaigns", ["org_id"])


def downgrade() -> None:
    op.drop_table("email_campaigns")
    op.drop_table("deals")
