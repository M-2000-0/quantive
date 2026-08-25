"""Server-Sent Events (SSE) endpoint for real-time optimization progress."""
import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import JobStatus, OptimizationJob, User
from app.security import get_current_user

router = APIRouter(prefix="/api/optimizations", tags=["progress"])


async def _progress_generator(job_id: str, user_id: str, db_factory):
    """Generate SSE events for optimization progress."""
    last_status = None
    last_progress = -1

    while True:
        db = db_factory()
        try:
            job = db.query(OptimizationJob).filter(
                OptimizationJob.id == job_id,
                OptimizationJob.org_id == db.query(User).filter(User.id == user_id).first().org_id if db.query(User).filter(User.id == user_id).first() else None,
            ).first()

            if not job:
                yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
                break

            # Only send updates when status or progress changes
            if job.status != last_status or abs(job.progress - last_progress) > 0.01:
                event_data = {
                    "job_id": job.id,
                    "status": job.status.value if hasattr(job.status, 'value') else job.status,
                    "progress": job.progress,
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                    "error_message": job.error_message,
                }
                yield f"data: {json.dumps(event_data)}\n\n"
                last_status = job.status
                last_progress = job.progress

            # If job is terminal, close the stream
            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                yield f"data: {json.dumps({'event': 'done', 'status': job.status.value if hasattr(job.status, 'value') else job.status})}\n\n"
                break
        except Exception:
            yield f"data: {json.dumps({'error': 'Failed to fetch progress'})}\n\n"
            break
        finally:
            db.close()

        # Check if client disconnected
        await asyncio.sleep(1.0)


@router.get("/{job_id}/progress")
async def get_optimization_progress(
    job_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Stream real-time optimization progress via Server-Sent Events.

    Returns an SSE stream that sends events when the job status or
    progress changes. The client can use EventSource to consume these.
    """
    # Verify the job exists and user has access
    job = db.query(OptimizationJob).filter(
        OptimizationJob.id == job_id,
        OptimizationJob.org_id == user.org_id,
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Optimization job not found")

    # If already complete, return final state immediately
    if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
        event_data = {
            "job_id": job.id,
            "status": job.status.value if hasattr(job.status, 'value') else job.status,
            "progress": job.progress,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error_message": job.error_message,
        }

        async def immediate_response():
            yield f"data: {json.dumps(event_data)}\n\n"
            yield f"data: {json.dumps({'event': 'done'})}\n\n"

        return StreamingResponse(
            immediate_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    import app.database as database_module

    def factory():
        return database_module.SessionLocal()

    return StreamingResponse(
        _progress_generator(job_id, user.id, factory),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{job_id}/progress/poll")
async def poll_optimization_progress(
    job_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Poll optimization progress (non-streaming alternative to SSE)."""
    job = db.query(OptimizationJob).filter(
        OptimizationJob.id == job_id,
        OptimizationJob.org_id == user.org_id,
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Optimization job not found")

    return {
        "job_id": job.id,
        "status": job.status.value if hasattr(job.status, 'value') else job.status,
        "progress": job.progress,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "error_message": job.error_message,
    }
