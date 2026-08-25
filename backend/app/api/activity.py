"""Activity Log and Export Job API endpoints."""
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.activity import get_activity_logger
from app.database import get_db
from app.export_jobs import ExportFormat, ExportStatus, get_export_store, start_export_job
from app.models import User
from app.security import get_current_user

# ── Activity Log Router ─────────────────────────────────────────────────────

activity_router = APIRouter(prefix="/api/activity", tags=["activity"])


class ActivityResponse(BaseModel):
    user_id: str
    org_id: str
    action: str
    resource_type: str
    resource_id: str
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    created_at: str


@activity_router.get("")
def list_activities(
    user: User = Depends(get_current_user),
    action: Optional[str] = Query(None, description="Filter by action type"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    limit: int = Query(50, ge=1, le=500),
):
    """List recent activities for the current user's organization."""
    logger = get_activity_logger()
    activities = logger.get_recent(
        org_id=user.org_id,
        action=action,
        resource_type=resource_type,
        limit=limit,
    )
    return {"activities": list(reversed(activities)), "total": len(activities)}


@activity_router.get("/stats")
def activity_stats(user: User = Depends(get_current_user)):
    """Get activity statistics for the organization."""
    logger = get_activity_logger()
    return logger.get_stats(org_id=user.org_id)


# ── Export Job Router ───────────────────────────────────────────────────────

export_router = APIRouter(prefix="/api/exports", tags=["exports"])


class ExportCreateRequest(BaseModel):
    resource_type: str = Field(..., description="portfolio, optimization, etc.")
    resource_id: str
    output_format: str = Field(default="csv", description="csv, json, xlsx, pdf")
    config: dict = Field(default_factory=dict)


class ExportResponse(BaseModel):
    id: str
    status: str
    progress: int
    output_path: Optional[str]
    error_message: Optional[str]
    created_at: str
    completed_at: Optional[str]


@export_router.post("", response_model=ExportResponse, status_code=201)
def create_export(
    data: ExportCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create an async export job."""
    if data.output_format not in [f.value for f in ExportFormat]:
        raise HTTPException(status_code=422, detail="Invalid format. Use: csv, json, xlsx, pdf")

    store = get_export_store()
    job = store.create_job(
        user_id=user.id,
        org_id=user.org_id,
        export_type=data.resource_type,
        resource_type=data.resource_type,
        resource_id=data.resource_id,
        output_format=data.output_format,
        config=data.config,
    )

    # In a real app, the data fetcher would query the DB
    # For now, use a simple placeholder
    def _fetch_data():
        return [{"placeholder": "data", "resource": data.resource_type, "id": data.resource_id}]

    start_export_job(job["id"], _fetch_data)
    return job


@export_router.get("", response_model=list[ExportResponse])
def list_exports(
    user: User = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
):
    """List export jobs for the current user."""
    store = get_export_store()
    return store.list_jobs(user_id=user.id, limit=limit)


@export_router.get("/{job_id}", response_model=ExportResponse)
def get_export(job_id: str, user: User = Depends(get_current_user)):
    """Get export job status."""
    store = get_export_store()
    job = store.get_job(job_id)
    if not job or job["user_id"] != user.id:
        raise HTTPException(status_code=404, detail="Export job not found")
    return job


@export_router.get("/{job_id}/download")
def download_export(job_id: str, user: User = Depends(get_current_user)):
    """Download the exported file."""
    store = get_export_store()
    job = store.get_job(job_id)
    if not job or job["user_id"] != user.id:
        raise HTTPException(status_code=404, detail="Export job not found")
    if job["status"] != ExportStatus.COMPLETED.value:
        raise HTTPException(status_code=400, detail="Export not ready")
    if not job.get("output_path") or not os.path.exists(job["output_path"]):
        raise HTTPException(status_code=404, detail="Export file not found")

    filename = os.path.basename(job["output_path"])
    return FileResponse(
        job["output_path"],
        filename=filename,
        media_type="application/octet-stream",
    )
