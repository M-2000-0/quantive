"""SSO/SAML database models for government identity provider integration."""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SSOProviderType(str, enum.Enum):
    SAML = "saml"
    OIDC = "oidc"


class SSOProviderStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class SSOProvider(Base):
    """Configured identity provider (Okta, Azure AD, PingFederate, etc.)."""
    __tablename__ = "sso_providers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_type: Mapped[SSOProviderType] = mapped_column(SAEnum(SSOProviderType), default=SSOProviderType.SAML)
    status: Mapped[SSOProviderStatus] = mapped_column(SAEnum(SSOProviderStatus), default=SSOProviderStatus.PENDING)

    # SAML configuration
    entity_id: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sso_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    slo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    x509_cert: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Attribute mapping (JSON: {"email": "user.email", "name": "user.displayName", ...})
    attribute_mapping: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Which SAML attribute to use as the unique identifier
    name_id_format: Mapped[str] = mapped_column(String(255), default="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress")

    # Settings
    enforce_sso: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_provision_users: Mapped[bool] = mapped_column(Boolean, default=True)
    default_role: Mapped[str] = mapped_column(String(50), default="analyst")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    links: Mapped[list["SSOUserLink"]] = relationship(back_populates="provider", cascade="all, delete-orphan")


class SSOUserLink(Base):
    """Maps a local user to an external SSO identity."""
    __tablename__ = "sso_user_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    provider_id: Mapped[str] = mapped_column(String(36), ForeignKey("sso_providers.id"), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    external_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Relationships
    provider: Mapped["SSOProvider"] = relationship(back_populates="links")


class SSOSession(Base):
    """Tracks active SSO sessions for logout propagation."""
    __tablename__ = "sso_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    provider_id: Mapped[str] = mapped_column(String(36), ForeignKey("sso_providers.id"), nullable=False)
    session_index: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
