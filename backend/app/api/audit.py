from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditEvent, User, UserRole
from app.schemas import AuditEventResponse
from app.security import require_role

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("", response_model=list[AuditEventResponse])
def list_audit_events(
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    action: str = Query(default=None),
    resource_type: str = Query(default=None),
):
    query = db.query(AuditEvent).filter(AuditEvent.org_id == user.org_id)

    if action:
        query = query.filter(AuditEvent.action == action)
    if resource_type:
        query = query.filter(AuditEvent.resource_type == resource_type)

    events = query.order_by(AuditEvent.created_at.desc()).offset(offset).limit(limit).all()
    return [AuditEventResponse.model_validate(e) for e in events]
