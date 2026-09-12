"""add agent_runs + agent_steps tables

Revision ID: 012_agent_runs
Revises: 011_email_verified, 1fd54de1246e
Create Date: 2026-09-12
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON

revision = "012_agent_runs"
down_revision = ("011_email_verified", "1fd54de1246e")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("org_id", sa.String(36), nullable=False, index=True),
        sa.Column("actor_id", sa.String(36), nullable=True),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued", index=True),
        sa.Column("plan", sa.JSON().with_variant(SQLiteJSON(), "sqlite"), nullable=False, server_default="[]"),
        sa.Column("current_step", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "agent_steps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column("args", sa.JSON().with_variant(SQLiteJSON(), "sqlite"), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending", index=True),
        sa.Column("output", sa.JSON().with_variant(SQLiteJSON(), "sqlite"), nullable=True),
        sa.Column("approval_status", sa.String(20), nullable=False, server_default="none"),
        sa.Column("error", sa.Text(), nullable=False, server_default=""),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("agent_steps")
    op.drop_table("agent_runs")
