"""project workspaces + documents, link agent runs to projects

Revision ID: 014_projects
Revises: 013_agent_step_approver
Create Date: 2026-09-12
"""
import sqlalchemy as sa
from alembic import op

revision = "014_projects"
down_revision = "013_agent_step_approver"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="active", index=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "project_documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("org_id", sa.String(36), nullable=False, index=True),
        sa.Column("folder", sa.String(30), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("uploaded_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.add_column("agent_runs", sa.Column("project_id", sa.String(36),
                                          sa.ForeignKey("projects.id", ondelete="SET NULL"),
                                          nullable=True, index=True))


def downgrade() -> None:
    op.drop_column("agent_runs", "project_id")
    op.drop_table("project_documents")
    op.drop_table("projects")
