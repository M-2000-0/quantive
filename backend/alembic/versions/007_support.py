"""add support tickets, FAQ, bug reports tables

Revision ID: 007_support
Revises: 006_tasks
Create Date: 2026-09-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "007_support"
down_revision: Union[str, None] = "006_tasks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Support Tickets ─────────────────────────────────────────────────────
    op.create_table(
        "support_tickets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("status", sa.String(50), server_default="open"),
        sa.Column("priority", sa.String(20), server_default="medium"),
        sa.Column("category", sa.String(100), server_default="general"),
        sa.Column("assigned_to", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("sla_deadline", sa.String(30), nullable=True),
        sa.Column("escalated", sa.Boolean, server_default=sa.text("0")),
        sa.Column("escalation_level", sa.Integer, server_default=sa.text("0")),
        sa.Column("resolution_notes", sa.Text, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_support_tickets_org_id", "support_tickets", ["org_id"])
    op.create_index("ix_support_tickets_user_id", "support_tickets", ["user_id"])

    # ── Support Messages ────────────────────────────────────────────────────
    op.create_table(
        "support_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ticket_id", sa.String(36), sa.ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("is_internal", sa.Boolean, server_default=sa.text("0")),
        sa.Column("is_ai_generated", sa.Boolean, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_support_messages_ticket_id", "support_messages", ["ticket_id"])

    # ── FAQ Categories ──────────────────────────────────────────────────────
    op.create_table(
        "faq_categories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("sort_order", sa.Integer, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_faq_categories_org_id", "faq_categories", ["org_id"])

    # ── FAQ Items ───────────────────────────────────────────────────────────
    op.create_table(
        "faq_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("category_id", sa.String(36), sa.ForeignKey("faq_categories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question", sa.String(1000), nullable=False),
        sa.Column("answer", sa.Text, nullable=False),
        sa.Column("helpful_count", sa.Integer, server_default=sa.text("0")),
        sa.Column("is_published", sa.Boolean, server_default=sa.text("1")),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_faq_items_category_id", "faq_items", ["category_id"])

    # ── Bug Reports ─────────────────────────────────────────────────────────
    op.create_table(
        "bug_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("reported_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("severity", sa.String(20), server_default="medium"),
        sa.Column("status", sa.String(50), server_default="open"),
        sa.Column("assigned_to", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("steps_to_reproduce", sa.Text, server_default=""),
        sa.Column("expected_behavior", sa.Text, server_default=""),
        sa.Column("actual_behavior", sa.Text, server_default=""),
        sa.Column("environment", sa.String(200), server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_bug_reports_org_id", "bug_reports", ["org_id"])


def downgrade() -> None:
    op.drop_table("bug_reports")
    op.drop_table("faq_items")
    op.drop_table("faq_categories")
    op.drop_table("support_messages")
    op.drop_table("support_tickets")
