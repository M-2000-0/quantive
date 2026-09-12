"""persisted market snapshots

Revision ID: 015_market_snapshots
Revises: 014_projects
Create Date: 2026-09-12
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON

revision = "015_market_snapshots"
down_revision = "014_projects"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source", sa.String(50), nullable=False, index=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="ok", index=True),
        sa.Column("payload", sa.JSON().with_variant(SQLiteJSON(), "sqlite"),
                  nullable=False, server_default="{}"),
        sa.Column("record_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=False, server_default=""),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("market_snapshots")
