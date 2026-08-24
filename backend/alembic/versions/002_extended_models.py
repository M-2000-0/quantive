"""add auth security, user preferences, notifications, api keys, constraint templates, portfolio snapshots, scheduled reports

Revision ID: 002_extended
Revises: 001_initial
Create Date: 2026-08-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002_extended"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Password Reset Tokens ──────────────────────────────────────────────
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
    op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"])

    # ── Email Verification Tokens ──────────────────────────────────────────
    op.create_table(
        "email_verification_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_email_verification_tokens_user_id", "email_verification_tokens", ["user_id"])
    op.create_index("ix_email_verification_tokens_token_hash", "email_verification_tokens", ["token_hash"])

    # ── Revoked Tokens (JWT blacklist) ─────────────────────────────────────
    op.create_table(
        "revoked_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("jti", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_revoked_tokens_jti", "revoked_tokens", ["jti"])
    op.create_index("ix_revoked_tokens_user_id", "revoked_tokens", ["user_id"])

    # ── User Preferences ───────────────────────────────────────────────────
    op.create_table(
        "user_preferences",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), unique=True, nullable=False),
        sa.Column("theme", sa.String(20), server_default="light"),
        sa.Column("language", sa.String(10), server_default="en"),
        sa.Column("timezone", sa.String(50), server_default="UTC"),
        sa.Column("date_format", sa.String(20), server_default="YYYY-MM-DD"),
        sa.Column("number_format", sa.String(20), server_default="en-US"),
        sa.Column("currency_display", sa.String(5), server_default="USD"),
        sa.Column("notifications_email", sa.Boolean, server_default=sa.text("1")),
        sa.Column("notifications_in_app", sa.Boolean, server_default=sa.text("1")),
        sa.Column("dashboard_config", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_user_preferences_user_id", "user_preferences", ["user_id"])

    # ── Notifications ──────────────────────────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text, server_default=""),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("resource_id", sa.String(36), nullable=True),
        sa.Column("read", sa.Boolean, server_default=sa.text("0")),
        sa.Column("metadata_json", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])

    # ── API Keys ───────────────────────────────────────────────────────────
    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("key_hash", sa.String(255), nullable=False),
        sa.Column("key_prefix", sa.String(10), nullable=False),
        sa.Column("scopes", sa.JSON, nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"])

    # ── Constraint Templates ───────────────────────────────────────────────
    op.create_table(
        "constraint_templates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("constraints", sa.JSON, nullable=False),
        sa.Column("is_default", sa.Boolean, server_default=sa.text("0")),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_constraint_templates_org_id", "constraint_templates", ["org_id"])

    # ── Portfolio Snapshots ────────────────────────────────────────────────
    op.create_table(
        "portfolio_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("portfolio_id", sa.String(36), sa.ForeignKey("portfolios.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("instruments_snapshot", sa.JSON, nullable=False),
        sa.Column("metadata_json", sa.JSON, nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_portfolio_snapshots_portfolio_id", "portfolio_snapshots", ["portfolio_id"])

    # ── Scheduled Reports ──────────────────────────────────────────────────
    op.create_table(
        "scheduled_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("report_type", sa.String(50), nullable=False),
        sa.Column("config", sa.JSON, nullable=False),
        sa.Column("cron_expression", sa.String(100), nullable=False),
        sa.Column("recipients", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("1")),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_scheduled_reports_org_id", "scheduled_reports", ["org_id"])


def downgrade() -> None:
    op.drop_table("scheduled_reports")
    op.drop_table("portfolio_snapshots")
    op.drop_table("constraint_templates")
    op.drop_table("api_keys")
    op.drop_table("notifications")
    op.drop_table("user_preferences")
    op.drop_table("revoked_tokens")
    op.drop_table("email_verification_tokens")
    op.drop_table("password_reset_tokens")
