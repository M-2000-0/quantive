"""Portfolio-level access control model.

Defines which users can access specific portfolios and with what role,
enabling fine-grained RBAC beyond organization-level permissions.
"""
import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models import Portfolio, User


def gen_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PortfolioRole(str, enum.Enum):
    """Roles for portfolio-level access."""
    OWNER = "owner"       # Full control: edit, delete, share, optimize
    EDITOR = "editor"     # Can edit instruments and run optimizations
    ANALYST = "analyst"   # Can view and run optimizations, cannot edit
    VIEWER = "viewer"     # Read-only access


class PortfolioAccess(Base):
    """Maps users to portfolios with specific roles.

    When a PortfolioAccess row exists for a user+portfolio pair,
    it overrides the default org-level access. If no row exists,
    the user's org role determines access (backwards compatible).
    """
    __tablename__ = "portfolio_access"
    __table_args__ = (
        UniqueConstraint("user_id", "portfolio_id", name="uq_portfolio_access_user_portfolio"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    portfolio_id: Mapped[str] = mapped_column(String(36), ForeignKey("portfolios.id"), nullable=False, index=True)
    role: Mapped[PortfolioRole] = mapped_column(String(20), nullable=False, default=PortfolioRole.VIEWER)
    granted_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    user: Mapped["User"] = relationship(foreign_keys=[user_id], back_populates="portfolio_accesses")
    portfolio: Mapped["Portfolio"] = relationship(back_populates="access_grants")
    granter: Mapped["User | None"] = relationship(foreign_keys=[granted_by])
