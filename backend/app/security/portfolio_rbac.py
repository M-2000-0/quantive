"""Per-portfolio RBAC dependency.

Provides fastapi dependencies for checking portfolio-level access:
- require_portfolio_access: Check if user has specific role on a portfolio
- get_portfolio_role: Get user's effective role on a portfolio
- require_portfolio_write: Require write access (owner/editor)
- require_portfolio_admin: Require admin access (owner only)
"""
from functools import wraps
from typing import Callable, Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Portfolio, PortfolioAccess, PortfolioRole, User, UserRole
from app.security import get_current_user


# Role hierarchy: higher roles include permissions of lower roles
ROLE_HIERARCHY = {
    PortfolioRole.VIEWER: 0,
    PortfolioRole.ANALYST: 1,
    PortfolioRole.EDITOR: 2,
    PortfolioRole.OWNER: 3,
}


def _role_level(role: str) -> int:
    """Get numeric level for role comparison."""
    try:
        return ROLE_HIERARCHY[PortfolioRole(role)]
    except (ValueError, KeyError):
        return 0


def get_portfolio_role(
    user: User,
    portfolio: Portfolio,
    db: Session,
) -> Optional[PortfolioRole]:
    """Get user's effective role on a portfolio.

    Returns:
        PortfolioRole if user has explicit access, None if using org-level default.
    """
    access = db.query(PortfolioAccess).filter(
        PortfolioAccess.user_id == user.id,
        PortfolioAccess.portfolio_id == portfolio.id,
        PortfolioAccess.is_active.is_(True),
    ).first()

    if access:
        return PortfolioRole(access.role)

    # No explicit access - check if user is in same org
    if portfolio.org_id == user.org_id:
        return None  # Signal to use org-level role

    return None


def check_portfolio_access(
    user: User,
    portfolio: Portfolio,
    db: Session,
    required_role: PortfolioRole,
) -> bool:
    """Check if user has required access level on a portfolio.

    Access rules:
    1. If user has explicit PortfolioAccess, use that role
    2. If user is in same org, fall back to org-level role mapping:
       - ADMIN -> OWNER
       - ANALYST -> EDITOR
       - VIEWER -> VIEWER
    3. If user is not in same org, deny access
    """
    # Check explicit portfolio access
    access = db.query(PortfolioAccess).filter(
        PortfolioAccess.user_id == user.id,
        PortfolioAccess.portfolio_id == portfolio.id,
        PortfolioAccess.is_active.is_(True),
    ).first()

    if access:
        user_level = _role_level(access.role)
        required_level = _role_level(required_role)
        return user_level >= required_level

    # Fall back to org-level access
    if portfolio.org_id != user.org_id:
        return False

    # Map org roles to portfolio roles
    org_role_map = {
        UserRole.ADMIN: PortfolioRole.OWNER,
        UserRole.ANALYST: PortfolioRole.EDITOR,
        UserRole.VIEWER: PortfolioRole.VIEWER,
    }

    effective_role = org_role_map.get(user.role, PortfolioRole.VIEWER)
    user_level = _role_level(effective_role)
    required_level = _role_level(required_role)

    return user_level >= required_level


def require_portfolio_access(required_role: PortfolioRole):
    """Dependency factory that checks portfolio access.

    Usage:
        @router.get("/{portfolio_id}")
        def get_portfolio(
            portfolio_id: str,
            user: User = Depends(require_portfolio_access(PortfolioRole.VIEWER)),
            db: Session = Depends(get_db),
        ):
            ...
    """
    async def _check(
        portfolio_id: str,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        portfolio = db.query(Portfolio).filter(
            Portfolio.id == portfolio_id,
        ).first()

        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found",
            )

        if not check_portfolio_access(user, portfolio, db, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {required_role.value}",
            )

        return user

    return _check


def require_portfolio_write(
    portfolio_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Dependency that requires write access (owner/editor) to a portfolio."""
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    if not check_portfolio_access(user, portfolio, db, PortfolioRole.EDITOR):
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions. Write access required.",
        )
    return user


def require_portfolio_admin(
    portfolio_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Dependency that requires admin access (owner) to a portfolio."""
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    if not check_portfolio_access(user, portfolio, db, PortfolioRole.OWNER):
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions. Owner access required.",
        )
    return user
