"""Disaster Recovery API endpoints.

Exposes DR status, backup management, and recovery testing.
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.models import User
from app.security import get_current_user

router = APIRouter(prefix="/api/disaster-recovery", tags=["disaster-recovery"])


class BackupRequest(BaseModel):
    backup_type: str = Field(default="full", description="Backup type: full, incremental, differential")
    location: str = Field(default="primary", description="Backup location")


class DRTestRequest(BaseModel):
    test_type: str = Field(default="full_recovery", description="Test type")


@router.get("/status")
def get_dr_status(user: User = Depends(get_current_user)):
    """Get current DR status."""
    from quantive.government.disaster_recovery import get_dr_engine

    engine = get_dr_engine()
    return engine.get_dr_status()


@router.post("/backup")
def create_backup(
    request: BackupRequest,
    user: User = Depends(get_current_user),
):
    """Create a new backup."""
    from quantive.government.disaster_recovery import BackupType, get_dr_engine

    engine = get_dr_engine()

    type_map = {"full": BackupType.FULL, "incremental": BackupType.INCREMENTAL,
                "differential": BackupType.DIFFERENTIAL}
    backup_type = type_map.get(request.backup_type, BackupType.FULL)

    backup = engine.create_backup(backup_type=backup_type, location=request.location)

    return {
        "backup_id": backup.backup_id,
        "type": backup.backup_type.value,
        "timestamp": backup.timestamp.isoformat(),
        "location": backup.location,
        "encrypted": backup.encrypted,
        "message": "Backup created successfully",
    }


@router.post("/backup/{backup_id}/verify")
def verify_backup(
    backup_id: str,
    user: User = Depends(get_current_user),
):
    """Verify a backup is intact."""
    from quantive.government.disaster_recovery import get_dr_engine

    engine = get_dr_engine()
    verified = engine.verify_backup(backup_id)

    return {
        "backup_id": backup_id,
        "verified": verified,
        "message": "Backup verified" if verified else "Backup not found",
    }


@router.get("/backups")
def list_backups(
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
):
    """List backup history."""
    from quantive.government.disaster_recovery import get_dr_engine

    engine = get_dr_engine()
    backups = engine.get_backup_history(limit=limit)

    return {"backups": backups, "total": len(backups)}


@router.post("/test")
def run_dr_test(
    request: DRTestRequest,
    user: User = Depends(get_current_user),
):
    """Run a DR test."""
    from quantive.government.disaster_recovery import get_dr_engine

    engine = get_dr_engine()
    test = engine.run_dr_test(test_type=request.test_type)

    return {
        "test_id": test.test_id,
        "test_type": test.test_type,
        "status": test.status.value,
        "rto_achieved_minutes": test.rto_achieved_minutes,
        "rpo_achieved_minutes": test.rpo_achieved_minutes,
        "started_at": test.start_time.isoformat(),
        "completed_at": test.end_time.isoformat() if test.end_time else None,
    }


@router.get("/plan")
def get_dr_plan(user: User = Depends(get_current_user)):
    """Get DR plan documentation."""
    from quantive.government.disaster_recovery import get_dr_engine

    engine = get_dr_engine()
    return engine.get_dr_plan()


@router.get("/compliance")
def get_compliance_checklist(user: User = Depends(get_current_user)):
    """Get DR compliance checklist."""
    from quantive.government.disaster_recovery import get_dr_engine

    engine = get_dr_engine()
    checklist = engine.get_compliance_checklist()

    met = sum(1 for item in checklist if item["status"] == "met")
    total = len(checklist)

    return {
        "checklist": checklist,
        "total_items": total,
        "items_met": met,
        "compliance_score": round(met / total * 100, 1) if total > 0 else 0,
    }
