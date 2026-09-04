"""add news sources and articles tables

Revision ID: 005_news
Revises: 004_social
Create Date: 2026-09-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005_news"
down_revision: Union[str, None] = "004_social"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── News Sources ────────────────────────────────────────────────────────
    op.create_table(
        "news_sources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("url", sa.String(2000), nullable=False),
        sa.Column("config_json", sa.JSON, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("1")),
        sa.Column("last_fetched_at", sa.String(30), nullable=True),
        sa.Column("fetch_error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_news_sources_org_id", "news_sources", ["org_id"])

    # ── News Articles ───────────────────────────────────────────────────────
    op.create_table(
        "news_articles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_id", sa.String(36), sa.ForeignKey("news_sources.id"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text, server_default=""),
        sa.Column("content", sa.Text, server_default=""),
        sa.Column("url", sa.String(2000), nullable=False),
        sa.Column("author", sa.String(255), nullable=True),
        sa.Column("published_at", sa.String(30), nullable=True),
        sa.Column("tickers_json", sa.JSON, nullable=True),
        sa.Column("sentiment_score", sa.Float, nullable=True),
        sa.Column("category", sa.String(100), server_default="general"),
        sa.Column("tags_json", sa.JSON, nullable=True),
        sa.Column("ingestion_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("is_read", sa.Boolean, server_default=sa.text("0")),
        sa.Column("is_starred", sa.Boolean, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_news_articles_published", "news_articles", ["published_at"])
    op.create_index("ix_news_articles_source", "news_articles", ["source_id"])


def downgrade() -> None:
    op.drop_table("news_articles")
    op.drop_table("news_sources")
