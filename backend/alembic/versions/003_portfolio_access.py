"""add portfolio_access table for per-portfolio RBAC

Revision ID: 003_portfolio_access
Revises: 002_extended
Create Date: 2026-08-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003_portfolio_access"
down_revision: Union[str, None] = "002_extended"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "portfolio_access",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("portfolio_id", sa.String(36), sa.ForeignKey("portfolios.id"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="viewer"),
        sa.Column("granted_by", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "portfolio_id", name="uq_portfolio_access_user_portfolio"),
    )
    op.create_index("ix_portfolio_access_user_id", "portfolio_access", ["user_id"])
    op.create_index("ix_portfolio_access_portfolio_id", "portfolio_access", ["portfolio_id"])


def downgrade() -> None:
    op.drop_table("portfolio_access")
