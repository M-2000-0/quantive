"""add social, collaboration, export, webhook, integration, experiment, and API usage models

Revision ID: 004_social
Revises: 003_portfolio_access
Create Date: 2026-08-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004_social"
down_revision: Union[str, None] = "003_portfolio_access"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Watchlists ──────────────────────────────────────────────────────────
    op.create_table(
        "watchlists",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("is_default", sa.Boolean, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_watchlists_user_id", "watchlists", ["user_id"])

    # ── Watchlist Items ─────────────────────────────────────────────────────
    op.create_table(
        "watchlist_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("watchlist_id", sa.String(36), sa.ForeignKey("watchlists.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(36), nullable=False),
        sa.Column("alert_threshold", sa.JSON, nullable=True),
        sa.Column("notes", sa.Text, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_watchlist_items_watchlist_id", "watchlist_items", ["watchlist_id"])

    # ── Comments ────────────────────────────────────────────────────────────
    op.create_table(
        "comments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(36), nullable=False),
        sa.Column("parent_id", sa.String(36), sa.ForeignKey("comments.id"), nullable=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("is_resolved", sa.Boolean, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_comments_user_id", "comments", ["user_id"])
    op.create_index("ix_comments_resource", "comments", ["resource_type", "resource_id"])

    # ── Attachments ─────────────────────────────────────────────────────────
    op.create_table(
        "attachments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(36), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("storage_path", sa.String(1000), nullable=False),
        sa.Column("metadata_json", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_attachments_resource", "attachments", ["resource_type", "resource_id"])

    # ── Tags ────────────────────────────────────────────────────────────────
    op.create_table(
        "tags",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("color", sa.String(7), server_default="#6366f1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("org_id", "name", name="uq_tags_org_name"),
    )
    op.create_index("ix_tags_org_id", "tags", ["org_id"])

    # ── Tagged Items ────────────────────────────────────────────────────────
    op.create_table(
        "tagged_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tag_id", sa.String(36), sa.ForeignKey("tags.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tag_id", "resource_type", "resource_id", name="uq_tagged_item"),
    )
    op.create_index("ix_tagged_items_tag_id", "tagged_items", ["tag_id"])
    op.create_index("ix_tagged_items_resource", "tagged_items", ["resource_type", "resource_id"])

    # ── Activity Log ────────────────────────────────────────────────────────
    op.create_table(
        "activity_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(36), nullable=False),
        sa.Column("details", sa.JSON, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_activity_log_user_id", "activity_log", ["user_id"])
    op.create_index("ix_activity_log_org_id", "activity_log", ["org_id"])
    op.create_index("ix_activity_log_resource_id", "activity_log", ["resource_id"])
    op.create_index("ix_activity_log_created_at", "activity_log", ["created_at"])

    # ── Saved Views ─────────────────────────────────────────────────────────
    op.create_table(
        "saved_views",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("view_type", sa.String(50), nullable=False),
        sa.Column("config", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("is_default", sa.Boolean, server_default=sa.text("0")),
        sa.Column("is_shared", sa.Boolean, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_saved_views_user_id", "saved_views", ["user_id"])

    # ── Saved Filters ───────────────────────────────────────────────────────
    op.create_table(
        "saved_filters",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("filter_type", sa.String(50), nullable=False),
        sa.Column("filters", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("is_default", sa.Boolean, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_saved_filters_user_id", "saved_filters", ["user_id"])

    # ── Export Jobs ─────────────────────────────────────────────────────────
    op.create_table(
        "export_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("export_type", sa.String(50), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(36), nullable=False),
        sa.Column("output_format", sa.String(20), server_default="pdf"),
        sa.Column("status", sa.String(20), server_default="queued"),
        sa.Column("progress", sa.Integer, server_default=sa.text("0")),
        sa.Column("output_path", sa.String(1000), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("config", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_export_jobs_user_id", "export_jobs", ["user_id"])
    op.create_index("ix_export_jobs_org_id", "export_jobs", ["org_id"])

    # ── Webhooks ────────────────────────────────────────────────────────────
    op.create_table(
        "webhooks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("url", sa.String(2000), nullable=False),
        sa.Column("secret", sa.String(255), nullable=False),
        sa.Column("events", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_webhooks_org_id", "webhooks", ["org_id"])

    # ── Webhook Deliveries ──────────────────────────────────────────────────
    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("webhook_id", sa.String(36), sa.ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("status_code", sa.Integer, nullable=True),
        sa.Column("response_body", sa.Text, nullable=True),
        sa.Column("success", sa.Boolean, server_default=sa.text("0")),
        sa.Column("attempts", sa.Integer, server_default=sa.text("0")),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_webhook_deliveries_webhook_id", "webhook_deliveries", ["webhook_id"])

    # ── Integrations ────────────────────────────────────────────────────────
    op.create_table(
        "integrations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("integration_type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("config", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("credentials_encrypted", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("1")),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sync_status", sa.String(20), server_default="idle"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_integrations_org_id", "integrations", ["org_id"])

    # ── Model Experiments ───────────────────────────────────────────────────
    op.create_table(
        "model_experiments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("control_config", sa.JSON, nullable=False),
        sa.Column("treatment_config", sa.JSON, nullable=False),
        sa.Column("traffic_split", sa.Integer, server_default=sa.text("50")),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("results", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_model_experiments_org_id", "model_experiments", ["org_id"])

    # ── API Usage Log ───────────────────────────────────────────────────────
    op.create_table(
        "api_usage_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("endpoint", sa.String(500), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("status_code", sa.Integer, nullable=False),
        sa.Column("response_time_ms", sa.Integer, nullable=False),
        sa.Column("request_size_bytes", sa.Integer, nullable=True),
        sa.Column("response_size_bytes", sa.Integer, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_api_usage_log_user_id", "api_usage_log", ["user_id"])
    op.create_index("ix_api_usage_log_org_id", "api_usage_log", ["org_id"])
    op.create_index("ix_api_usage_log_created_at", "api_usage_log", ["created_at"])


def downgrade() -> None:
    op.drop_table("api_usage_log")
    op.drop_table("model_experiments")
    op.drop_table("integrations")
    op.drop_table("webhook_deliveries")
    op.drop_table("webhooks")
    op.drop_table("export_jobs")
    op.drop_table("saved_filters")
    op.drop_table("saved_views")
    op.drop_table("activity_log")
    op.drop_table("tagged_items")
    op.drop_table("tags")
    op.drop_table("attachments")
    op.drop_table("comments")
    op.drop_table("watchlist_items")
    op.drop_table("watchlists")
