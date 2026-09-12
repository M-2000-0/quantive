"""add sso tables

Revision ID: 010_sso
Revises: 009_government_models
Create Date: 2026-09-11
"""
from alembic import op
import sqlalchemy as sa

revision = "010_sso"
down_revision = "009_government_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sso_providers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("provider_type", sa.Enum("saml", "oidc", name="ssoprovidertype"), nullable=False, server_default="saml"),
        sa.Column("status", sa.Enum("active", "inactive", "pending", name="ssoproviderstatus"), nullable=False, server_default="pending"),
        sa.Column("entity_id", sa.String(500), nullable=True),
        sa.Column("sso_url", sa.String(500), nullable=True),
        sa.Column("slo_url", sa.String(500), nullable=True),
        sa.Column("x509_cert", sa.Text, nullable=True),
        sa.Column("metadata_url", sa.String(500), nullable=True),
        sa.Column("attribute_mapping", sa.JSON, nullable=True),
        sa.Column("name_id_format", sa.String(255), nullable=False, server_default="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"),
        sa.Column("enforce_sso", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("auto_provision_users", sa.Boolean, nullable=False, server_default=sa.text("1")),
        sa.Column("default_role", sa.String(50), nullable=False, server_default="analyst"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "sso_user_links",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("provider_id", sa.String(36), sa.ForeignKey("sso_providers.id"), nullable=False, index=True),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("external_email", sa.String(255), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "sso_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("provider_id", sa.String(36), sa.ForeignKey("sso_providers.id"), nullable=False),
        sa.Column("session_index", sa.String(255), nullable=True),
        sa.Column("name_id", sa.String(255), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("sso_sessions")
    op.drop_table("sso_user_links")
    op.drop_table("sso_providers")
    op.execute("DROP TYPE IF EXISTS ssoproviderstatus")
    op.execute("DROP TYPE IF EXISTS ssoprovidertype")
