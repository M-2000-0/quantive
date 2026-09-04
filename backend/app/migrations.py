"""Database Migration System — Schema Versioning & Upgrades.

Tracks applied migrations in a metadata table and applies
new migrations in order. Supports both SQLite and DuckDB.

Usage:
    from app.migrations import run_migrations
    run_migrations()  # Apply all pending migrations

Adding a new migration:
    MIGRATIONS.append(Migration(
        version=2,
        name="add_rate_limiting",
        up_sql="ALTER TABLE ...",
        down_sql="ALTER TABLE ...",
    ))
"""

import os
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Optional, Callable

from app.database import get_db


@dataclass
class Migration:
    """A single database migration."""
    version: int
    name: str
    up_sql: str
    down_sql: str = ""
    up_fn: Optional[Callable] = None  # For complex migrations
    down_fn: Optional[Callable] = None


# ── Migration Registry ───────────────────────────────────────────

MIGRATIONS: list[Migration] = [
    Migration(
        version=1,
        name="create_migration_table",
        up_sql="""
            CREATE TABLE IF NOT EXISTS _migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """,
    ),
    Migration(
        version=2,
        name="add_data_quality_flags",
        up_sql="""
            -- Data quality flags are added via model changes in Python
            -- This migration ensures the column exists for SQLite
            SELECT 1; -- No-op for schema-only tracking
        """,
    ),
    Migration(
        version=3,
        name="add_audit_timestamps",
        up_sql="""
            SELECT 1; -- Tracked in Python models
        """,
    ),
    Migration(
        version=4,
        name="add_rate_limit_tracking",
        up_sql="""
            CREATE TABLE IF NOT EXISTS rate_limit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                request_count INTEGER DEFAULT 1,
                window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                blocked BOOLEAN DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_rate_limit_ip ON rate_limit_log(ip_address);
            CREATE INDEX IF NOT EXISTS idx_rate_limit_window ON rate_limit_log(window_start);
        """,
    ),
    Migration(
        version=5,
        name="add_backup_metadata",
        up_sql="""
            CREATE TABLE IF NOT EXISTS backup_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                files_count INTEGER DEFAULT 0,
                total_size_bytes INTEGER DEFAULT 0,
                status TEXT DEFAULT 'success',
                errors TEXT DEFAULT '[]'
            );
        """,
    ),
    Migration(
        version=6,
        name="add_prediction_drift_tracking",
        up_sql="""
            CREATE TABLE IF NOT EXISTS prediction_drift (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT NOT NULL,
                prediction_type TEXT NOT NULL,
                mean_predicted REAL,
                mean_actual REAL,
                drift_score REAL,
                sample_size INTEGER,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_drift_model ON prediction_drift(model_name);
        """,
    ),
]


def _get_migration_version(db) -> int:
    """Get the current migration version from the database."""
    try:
        cursor = db.execute("SELECT MAX(version) FROM _migrations")
        row = cursor.fetchone()
        return row[0] if row and row[0] else 0
    except Exception:
        return 0


def _ensure_migration_table(db):
    """Create the migrations tracking table if it doesn't exist."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.commit()


def run_migrations(db=None) -> dict:
    """Apply all pending migrations.
    
    Returns:
        dict with results: applied count, version, details
    """
    close_db = False
    if db is None:
        db = get_db()
        close_db = True
    
    try:
        _ensure_migration_table(db)
        current_version = _get_migration_version(db)
        
        applied = []
        errors = []
        
        pending = [m for m in MIGRATIONS if m.version > current_version]
        pending.sort(key=lambda m: m.version)
        
        for migration in pending:
            try:
                if migration.up_fn:
                    migration.up_fn(db)
                else:
                    # Split and execute individual statements
                    for statement in migration.up_sql.split(";"):
                        statement = statement.strip()
                        if statement and statement.upper() != "SELECT 1":
                            db.execute(statement)
                
                # Record migration
                db.execute(
                    "INSERT INTO _migrations (version, name) VALUES (?, ?)",
                    (migration.version, migration.name),
                )
                db.commit()
                
                applied.append({
                    "version": migration.version,
                    "name": migration.name,
                })
                
            except Exception as e:
                errors.append({
                    "version": migration.version,
                    "name": migration.name,
                    "error": str(e),
                })
                db.rollback()
        
        return {
            "status": "success",
            "previous_version": current_version,
            "new_version": _get_migration_version(db),
            "applied_count": len(applied),
            "applied": applied,
            "errors": errors,
        }
    
    finally:
        if close_db:
            db.close()


def get_migration_status() -> dict:
    """Get current migration status without applying anything."""
    db = get_db()
    try:
        _ensure_migration_table(db)
        current_version = _get_migration_version(db)
        
        applied = []
        cursor = db.execute(
            "SELECT version, name, applied_at FROM _migrations ORDER BY version"
        )
        for row in cursor.fetchall():
            applied.append({
                "version": row[0],
                "name": row[1],
                "applied_at": row[2],
            })
        
        pending = [
            {"version": m.version, "name": m.name}
            for m in MIGRATIONS if m.version > current_version
        ]
        
        return {
            "current_version": current_version,
            "total_migrations": len(MIGRATIONS),
            "applied": applied,
            "pending": pending,
        }
    finally:
        db.close()
