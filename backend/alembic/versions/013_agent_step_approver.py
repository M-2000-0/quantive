"""record approver identity on agent_steps (four-eyes)

Revision ID: 013_agent_step_approver
Revises: 012_agent_runs
Create Date: 2026-09-12
"""
import sqlalchemy as sa
from alembic import op

revision = "013_agent_step_approver"
down_revision = "012_agent_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agent_steps", sa.Column("approved_by", sa.String(36), nullable=True))
    op.add_column("agent_steps", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("agent_steps", sa.Column("approve_comment", sa.Text(), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("agent_steps", "approve_comment")
    op.drop_column("agent_steps", "approved_at")
    op.drop_column("agent_steps", "approved_by")
