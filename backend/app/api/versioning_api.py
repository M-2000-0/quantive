"""Portfolio Versioning API — Snapshot and diff endpoints.

- POST /api/versions/{portfolio_id}/snapshot — Create snapshot
- GET /api/versions/{portfolio_id} — Get version history
- GET /api/versions/{portfolio_id}/diff?v1=X&v2=Y — Compare versions
- GET /api/versions/{portfolio_id}/{version} — Get full snapshot
"""

from fastapi import APIRouter, Depends, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models import User

_optional_bearer = HTTPBearer(auto_error=False)

router = APIRouter(prefix="/api/versions", tags=["versioning"])


async def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(_optional_bearer),
    db: Session = Depends(get_db),
) -> Optional[User]:
    token = None
    if credentials:
        token = credentials.credentials
    else:
        token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        from app.security import decode_token
        payload = decode_token(token)
        if payload:
            uid = payload.get("sub")
            return db.query(User).filter(User.id == uid).first()
    except Exception:
        pass
    return None


class SnapshotRequest(BaseModel):
    trigger: str = "manual"
    description: Optional[str] = None


@router.post("/{portfolio_id}/snapshot")
def create_snapshot(
    portfolio_id: str,
    data: SnapshotRequest,
    user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Create a point-in-time snapshot of a portfolio."""
    from app.services.portfolio_versioning import PortfolioVersioning
    versioning = PortfolioVersioning(db)
    return versioning.create_snapshot(
        portfolio_id=portfolio_id,
        trigger=data.trigger,
        created_by=str(user.id) if user else None,
        description=data.description,
    )


@router.get("/{portfolio_id}")
def get_version_history(
    portfolio_id: str,
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Get version history for a portfolio."""
    from app.services.portfolio_versioning import PortfolioVersioning
    versioning = PortfolioVersioning(db)
    return {"versions": versioning.get_versions(portfolio_id, limit=limit)}


@router.get("/{portfolio_id}/diff")
def diff_versions(
    portfolio_id: str,
    v1: int = Query(..., ge=1),
    v2: int = Query(..., ge=1),
    user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Compare two versions and return the diff."""
    from app.services.portfolio_versioning import PortfolioVersioning
    versioning = PortfolioVersioning(db)
    return versioning.diff_versions(portfolio_id, v1, v2)


@router.get("/{portfolio_id}/{version}")
def get_version_snapshot(
    portfolio_id: str,
    version: int,
    user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Get the full snapshot for a specific version."""
    from app.services.portfolio_versioning import PortfolioVersioning
    versioning = PortfolioVersioning(db)
    return versioning.get_version_snapshot(portfolio_id, version)
