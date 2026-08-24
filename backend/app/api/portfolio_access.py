"""Portfolio access management API endpoints.

Allows owners to grant/revoke access to specific users for their portfolios.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Portfolio, PortfolioAccess, PortfolioRole, User, UserRole
from app.security import get_current_user, log_audit_event
from app.security.portfolio_rbac import require_portfolio_access

router = APIRouter(prefix="/api/portfolios", tags=["portfolio-access"])


class GrantAccessRequest(BaseModel):
    user_id: str
    role: str  # PortfolioRole value
    portfolio_id: str


class UpdateAccessRequest(BaseModel):
    role: str  # PortfolioRole value


class AccessResponse(BaseModel):
    id: str
    user_id: str
    user_email: str
    user_name: str
    portfolio_id: str
    role: str
    granted_by: Optional[str]
    is_active: bool
    created_at: str

    class Config:
        from_attributes = True


def _validate_role(role_str: str) -> PortfolioRole:
    """Validate and convert role string to PortfolioRole."""
    try:
        return PortfolioRole(role_str)
    except ValueError:
        valid_roles = [r.value for r in PortfolioRole]
        raise HTTPException(
            status_code=422,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}",
        )


@router.get("/{portfolio_id}/access", response_model=list[AccessResponse])
def list_portfolio_access(
    portfolio_id: str,
    user: User = Depends(require_portfolio_access(PortfolioRole.OWNER)),
    db: Session = Depends(get_db),
):
    """List all users with access to a portfolio. Requires OWNER role."""
    access_records = db.query(PortfolioAccess).filter(
        PortfolioAccess.portfolio_id == portfolio_id,
        PortfolioAccess.is_active.is_(True),
    ).all()

    result = []
    for access in access_records:
        access_user = db.query(User).filter(User.id == access.user_id).first()
        if access_user:
            result.append(AccessResponse(
                id=access.id,
                user_id=access.user_id,
                user_email=access_user.email,
                user_name=access_user.name,
                portfolio_id=access.portfolio_id,
                role=access.role,
                granted_by=access.granted_by,
                is_active=access.is_active,
                created_at=access.created_at.isoformat() if access.created_at else "",
            ))

    return result


@router.post("/{portfolio_id}/access", response_model=AccessResponse, status_code=201)
def grant_portfolio_access(
    portfolio_id: str,
    data: GrantAccessRequest,
    user: User = Depends(require_portfolio_access(PortfolioRole.OWNER)),
    db: Session = Depends(get_db),
):
    """Grant access to a user for a portfolio. Requires OWNER role."""
    # Verify target user exists and is in the same org
    target_user = db.query(User).filter(User.id == data.user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    if target_user.org_id != portfolio.org_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot grant access to users outside the organization",
        )

    # Cannot grant access to yourself
    if data.user_id == user.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot grant access to yourself",
        )

    role = _validate_role(data.role)

    # Check if access already exists
    existing = db.query(PortfolioAccess).filter(
        PortfolioAccess.user_id == data.user_id,
        PortfolioAccess.portfolio_id == portfolio_id,
    ).first()

    if existing:
        if existing.is_active:
            raise HTTPException(
                status_code=409,
                detail="User already has access to this portfolio",
            )
        # Reactivate and update role
        existing.is_active = True
        existing.role = role
        existing.granted_by = user.id
        db.commit()
        db.refresh(existing)

        log_audit_event(
            db, user, "portfolio.access.granted", "portfolio",
            portfolio_id, metadata={"target_user": data.user_id, "role": role.value},
        )

        return AccessResponse(
            id=existing.id,
            user_id=existing.user_id,
            user_email=target_user.email,
            user_name=target_user.name,
            portfolio_id=existing.portfolio_id,
            role=existing.role,
            granted_by=existing.granted_by,
            is_active=existing.is_active,
            created_at=existing.created_at.isoformat() if existing.created_at else "",
        )

    # Create new access grant
    access = PortfolioAccess(
        user_id=data.user_id,
        portfolio_id=portfolio_id,
        role=role,
        granted_by=user.id,
    )
    db.add(access)
    db.commit()
    db.refresh(access)

    log_audit_event(
        db, user, "portfolio.access.granted", "portfolio",
        portfolio_id, metadata={"target_user": data.user_id, "role": role.value},
    )

    return AccessResponse(
        id=access.id,
        user_id=access.user_id,
        user_email=target_user.email,
        user_name=target_user.name,
        portfolio_id=access.portfolio_id,
        role=access.role,
        granted_by=access.granted_by,
        is_active=access.is_active,
        created_at=access.created_at.isoformat() if access.created_at else "",
    )


@router.put("/{portfolio_id}/access/{access_id}", response_model=AccessResponse)
def update_portfolio_access(
    portfolio_id: str,
    access_id: str,
    data: UpdateAccessRequest,
    user: User = Depends(require_portfolio_access(PortfolioRole.OWNER)),
    db: Session = Depends(get_db),
):
    """Update a user's role on a portfolio. Requires OWNER role."""
    access = db.query(PortfolioAccess).filter(
        PortfolioAccess.id == access_id,
        PortfolioAccess.portfolio_id == portfolio_id,
    ).first()

    if not access:
        raise HTTPException(status_code=404, detail="Access grant not found")

    role = _validate_role(data.role)
    access.role = role
    db.commit()
    db.refresh(access)

    target_user = db.query(User).filter(User.id == access.user_id).first()

    log_audit_event(
        db, user, "portfolio.access.updated", "portfolio",
        portfolio_id, metadata={"target_user": access.user_id, "role": role.value},
    )

    return AccessResponse(
        id=access.id,
        user_id=access.user_id,
        user_email=target_user.email if target_user else "unknown",
        user_name=target_user.name if target_user else "unknown",
        portfolio_id=access.portfolio_id,
        role=access.role,
        granted_by=access.granted_by,
        is_active=access.is_active,
        created_at=access.created_at.isoformat() if access.created_at else "",
    )


@router.delete("/{portfolio_id}/access/{access_id}", status_code=204)
def revoke_portfolio_access(
    portfolio_id: str,
    access_id: str,
    user: User = Depends(require_portfolio_access(PortfolioRole.OWNER)),
    db: Session = Depends(get_db),
):
    """Revoke a user's access to a portfolio. Requires OWNER role."""
    access = db.query(PortfolioAccess).filter(
        PortfolioAccess.id == access_id,
        PortfolioAccess.portfolio_id == portfolio_id,
    ).first()

    if not access:
        raise HTTPException(status_code=404, detail="Access grant not found")

    # Soft delete - mark as inactive
    access.is_active = False
    db.commit()

    log_audit_event(
        db, user, "portfolio.access.revoked", "portfolio",
        portfolio_id, metadata={"target_user": access.user_id},
    )
