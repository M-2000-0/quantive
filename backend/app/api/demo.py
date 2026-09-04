"""Demo Tracking API — demo requests, pipeline, analytics."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import get_current_user
from app.services.demo_tracker import (
    create_demo_request,
    get_demo_analytics,
    get_demo_pipeline,
    update_demo_status,
)

router = APIRouter(prefix="/api/demos", tags=["demo-tracking"])


class DemoRequestCreate(BaseModel):
    subject: str = Field(..., min_length=1, max_length=500)
    description: str = ""
    preferred_date: Optional[str] = None


class DemoStatusUpdate(BaseModel):
    status: str = Field(..., description="requested, scheduled, completed, converted, lost, no_show")
    notes: Optional[str] = None


@router.get("/pipeline")
def pipeline(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get demo pipeline overview."""
    return get_demo_pipeline(db, user.org_id)


@router.post("/request", status_code=201)
def request_demo(
    data: DemoRequestCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new demo request."""
    return create_demo_request(
        db,
        org_id=user.org_id,
        user_id=user.id,
        subject=data.subject,
        description=data.description,
        preferred_date=data.preferred_date,
    )


@router.put("/{ticket_id}/status")
def set_status(
    ticket_id: str,
    data: DemoStatusUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update demo status."""
    result = update_demo_status(db, ticket_id, user.org_id, data.status, data.notes)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/analytics")
def analytics(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get demo conversion analytics."""
    return get_demo_analytics(db, user.org_id)
