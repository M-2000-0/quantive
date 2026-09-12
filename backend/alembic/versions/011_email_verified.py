"""add email_verified to users

Revision ID: 011_email_verified
Revises: 010_sso
Create Date: 2026-09-12
"""
from alembic import op
import sqlalchemy as sa

revision = "011_email_verified"
down_revision = "010_sso"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    )


def downgrade() -> None:
    op.drop_column("users", "email_verified")