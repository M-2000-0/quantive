"""add tasks, task comments, meetings, meeting attendees tables

Revision ID: 006_tasks
Revises: 005_news
Create Date: 2026-09-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006_tasks"
down_revision: Union[str, None] = "005_news"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Tasks ───────────────────────────────────────────────────────────────
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("status", sa.String(50), server_default="todo"),
        sa.Column("priority", sa.String(20), server_default="medium"),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("assigned_to", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("due_date", sa.String(30), nullable=True),
        sa.Column("tags_json", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_tasks_org_id", "tasks", ["org_id"])

    # ── Task Comments ───────────────────────────────────────────────────────
    op.create_table(
        "task_comments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_task_comments_task_id", "task_comments", ["task_id"])

    # ── Meetings ────────────────────────────────────────────────────────────
    op.create_table(
        "meetings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("start_time", sa.String(30), nullable=False),
        sa.Column("end_time", sa.String(30), nullable=False),
        sa.Column("location", sa.String(500), server_default=""),
        sa.Column("meeting_url", sa.String(2000), server_default=""),
        sa.Column("recurrence_json", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_meetings_org_id", "meetings", ["org_id"])

    # ── Meeting Attendees ───────────────────────────────────────────────────
    op.create_table(
        "meeting_attendees",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("meeting_id", sa.String(36), sa.ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_meeting_attendees_meeting_id", "meeting_attendees", ["meeting_id"])


def downgrade() -> None:
    op.drop_table("meeting_attendees")
    op.drop_table("meetings")
    op.drop_table("task_comments")
    op.drop_table("tasks")
