"""Automated Backup System — SQLite/DuckDB Database Backups.

Creates timestamped backups of all local databases with rotation
and compression. Backups stored in D:\\QuantiveBackups\\ or configurable path.

Usage:
    from app.backup import run_backup, schedule_backups
    run_backup()  # One-time backup
    schedule_backups(interval_hours=24)  # Background scheduler
"""

import os
import shutil
import gzip
import time
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


BACKUP_DIR = os.environ.get("QUANTIVE_BACKUP_DIR", r"D:\QuantiveBackups")
MAX_BACKUPS = 30  # Keep last 30 backups
DB_PATHS = [
    "app/data/quantive.duckdb",
    "app/data/quantive.db",
]


def _get_backup_path() -> Path:
    """Ensure backup directory exists and return path."""
    path = Path(BACKUP_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _compress_file(src: Path, dst: Path):
    """Gzip compress a file."""
    with open(src, "rb") as f_in:
        with gzip.open(dst, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)


def run_backup(extra_paths: Optional[list[str]] = None) -> dict:
    """Run a full backup of all configured databases.
    
    Returns:
        dict with backup results: files_backed_up, total_size_bytes, errors
    """
    backup_dir = _get_backup_path()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    session_dir = backup_dir / f"backup_{timestamp}"
    session_dir.mkdir(exist_ok=True)
    
    results = {
        "timestamp": timestamp,
        "backup_dir": str(session_dir),
        "files": [],
        "total_size_bytes": 0,
        "errors": [],
    }
    
    all_paths = DB_PATHS + (extra_paths or [])
    
    for db_path_str in all_paths:
        db_path = Path(db_path_str)
        if not db_path.exists():
            continue
        
        try:
            # Create compressed backup
            backup_name = f"{db_path.stem}_{timestamp}{db_path.suffix}.gz"
            backup_path = session_dir / backup_name
            
            _compress_file(db_path, backup_path)
            
            size = backup_path.stat().st_size
            results["files"].append({
                "source": str(db_path),
                "backup": str(backup_path),
                "size_bytes": size,
            })
            results["total_size_bytes"] += size
            
        except Exception as e:
            results["errors"].append({"file": str(db_path), "error": str(e)})
    
    # Rotate old backups
    _rotate_backups(backup_dir)
    
    return results


def _rotate_backups(backup_dir: Path):
    """Keep only the last MAX_BACKUPS backup sessions."""
    sessions = sorted(
        [d for d in backup_dir.iterdir() if d.is_dir() and d.name.startswith("backup_")],
        key=lambda d: d.name,
        reverse=True,
    )
    
    for old_session in sessions[MAX_BACKUPS:]:
        shutil.rmtree(old_session, ignore_errors=True)


def schedule_backups(interval_hours: int = 24):
    """Start a background thread that runs backups periodically."""
    def _loop():
        while True:
            try:
                result = run_backup()
                print(f"[backup] Completed: {len(result['files'])} files, "
                      f"{result['total_size_bytes'] / 1024:.1f} KB")
            except Exception as e:
                print(f"[backup] Error: {e}")
            time.sleep(interval_hours * 3600)
    
    thread = threading.Thread(target=_loop, daemon=True, name="backup-scheduler")
    thread.start()
    print(f"[backup] Scheduled every {interval_hours}h, storing in {BACKUP_DIR}")


def list_backups() -> list[dict]:
    """List all available backup sessions."""
    backup_dir = Path(BACKUP_DIR)
    if not backup_dir.exists():
        return []
    
    backups = []
    for session in sorted(backup_dir.iterdir(), reverse=True):
        if session.is_dir() and session.name.startswith("backup_"):
            files = list(session.glob("*.gz"))
            total_size = sum(f.stat().st_size for f in files)
            backups.append({
                "timestamp": session.name.replace("backup_", ""),
                "path": str(session),
                "files_count": len(files),
                "total_size_bytes": total_size,
            })
    
    return backups


def restore_backup(backup_timestamp: str) -> dict:
    """Restore databases from a specific backup session.
    
    WARNING: This overwrites current databases. Use with caution.
    """
    backup_dir = _get_backup_path()
    session_dir = backup_dir / f"backup_{backup_timestamp}"
    
    if not session_dir.exists():
        return {"error": f"Backup {backup_timestamp} not found"}
    
    restored = []
    errors = []
    
    for gz_file in session_dir.glob("*.gz"):
        try:
            # Determine target path from filename
            stem = gz_file.stem  # e.g., "quantive_20260903_120000.duckdb"
            # Remove timestamp to get original name
            parts = stem.rsplit("_", 1)
            if len(parts) == 2:
                original_name = parts[0] + gz_file.suffix.replace(".gz", "")
            else:
                original_name = stem
            
            # Find matching target path
            for db_path_str in DB_PATHS:
                db_path = Path(db_path_str)
                if db_path.name == original_name:
                    # Decompress
                    with gzip.open(gz_file, "rb") as f_in:
                        with open(db_path, "wb") as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    restored.append(str(db_path))
                    break
        except Exception as e:
            errors.append({"file": str(gz_file), "error": str(e)})
    
    return {"restored": restored, "errors": errors}
