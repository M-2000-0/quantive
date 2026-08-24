from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditEvent, User, UserRole
from app.pagination import (
    PaginationQuery,
    create_paginated_response,
    paginate_query,
)
from app.schemas import AuditEventResponse
from app.security import require_role

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("")
def list_audit_events(
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
    pagination: PaginationQuery = Depends(),
    action: Optional[str] = Query(default=None, description="Filter by action type"),
    resource_type: Optional[str] = Query(default=None, description="Filter by resource type"),
    actor_email: Optional[str] = Query(default=None, description="Filter by actor email"),
):
    query = db.query(AuditEvent).filter(AuditEvent.org_id == user.org_id)

    # Apply specific filters
    if action:
        query = query.filter(AuditEvent.action == action)
    if resource_type:
        query = query.filter(AuditEvent.resource_type == resource_type)
    if actor_email:
        query = query.filter(AuditEvent.actor_email.ilike(f"%{actor_email}%"))

    # Search in action and actor_email
    items, total = paginate_query(
        query,
        limit=pagination.limit,
        offset=pagination.offset,
        cursor=pagination.cursor,
        search=pagination.search,
        search_fields=["action", "actor_email", "resource_type"],
        sort_by=pagination.sort_by or "created_at",
        sort_order=pagination.sort_order,
        model=AuditEvent,
    )

    return create_paginated_response(
        items=items,
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
        serializer=lambda e: AuditEventResponse.model_validate(e).model_dump(mode="json"),
    )
