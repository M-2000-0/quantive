"""Backup monitoring API — status, verification, alerts."""
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import get_current_user

router = APIRouter(prefix="/api/backup", tags=["backup"])


@router.get("/status")
def backup_status(user: User = Depends(get_current_user)):
    """Get backup system status and recent backups."""
    from app.backup import list_backups, BACKUP_DIR

    backups = list_backups()
    backup_dir_exists = os.path.exists(BACKUP_DIR)

    # Calculate health metrics
    total_backups = len(backups)
    if total_backups > 0:
        latest = backups[0]
        latest_size = latest.get("total_size_bytes", 0)
        latest_time = latest.get("timestamp", "")
    else:
        latest_size = 0
        latest_time = None

    # Determine health
    if total_backups == 0:
        health = "no_backups"
        message = "No backups found. Run a backup to enable monitoring."
    elif total_backups < 3:
        health = "warning"
        message = f"Only {total_backups} backup(s) available. Consider increasing backup frequency."
    else:
        health = "healthy"
        message = f"{total_backups} backups available. System is protected."

    return {
        "health": health,
        "message": message,
        "backup_dir": BACKUP_DIR,
        "backup_dir_exists": backup_dir_exists,
        "total_backups": total_backups,
        "latest_backup": {
            "timestamp": latest_time,
            "size_bytes": latest_size,
            "size_human": f"{latest_size / 1024:.1f} KB" if latest_size else "N/A",
        } if backups else None,
        "recent_backups": backups[:5],
    }


@router.post("/trigger")
def trigger_backup(user: User = Depends(get_current_user)):
    """Manually trigger a backup."""
    from app.backup import run_backup

    result = run_backup()
    return {
        "status": "completed",
        "files_backed_up": len(result.get("files", [])),
        "total_size_bytes": result.get("total_size_bytes", 0),
        "errors": result.get("errors", []),
    }


@router.get("/verify")
def verify_backups(user: User = Depends(get_current_user)):
    """Verify backup integrity."""
    import gzip
    from pathlib import Path
    from app.backup import list_backups, BACKUP_DIR

    backups = list_backups()
    verification_results = []

    for backup in backups[:5]:
        session_path = Path(backup["path"])
        files = list(session_path.glob("*.gz"))
        verified = 0
        failed = 0

        for gz_file in files:
            try:
                with gzip.open(gz_file, "rb") as f:
                    f.read(1024)  # Read first 1KB to verify
                verified += 1
            except Exception:
                failed += 1

        verification_results.append({
            "timestamp": backup["timestamp"],
            "files_total": len(files),
            "files_verified": verified,
            "files_failed": failed,
            "status": "ok" if failed == 0 else "degraded",
        })

    return {
        "total_verified": sum(r["files_verified"] for r in verification_results),
        "total_failed": sum(r["files_failed"] for r in verification_results),
        "results": verification_results,
    }
