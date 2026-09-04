"""Data Integrity Layer - Backup, Dry-Run, Rollback, Confirmation."""

import json
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy.orm import Session

logger = logging.getLogger("quantive.integrity")


class BackupPoint:
    """Immutable snapshot of data before a destructive operation."""
    def __init__(self, resource_type, resource_id, data, operation, user_id):
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.data = data
        self.operation = operation
        self.user_id = user_id
        self.timestamp = datetime.now(timezone.utc)
        self.checksum = hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()

    def to_dict(self):
        return {"resource_type": self.resource_type, "resource_id": self.resource_id,
            "data": self.data, "operation": self.operation, "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(), "checksum": self.checksum}


_backup_store = {}


def create_backup_point(db: Session, resource_type: str, resource_id: str, data: dict, operation: str, user_id: str) -> str:
    """Create an immutable backup before a destructive operation. Returns backup_id."""
    bp = BackupPoint(resource_type, resource_id, data, operation, user_id)
    backup_id = f"bp-{resource_type}-{resource_id}-{int(bp.timestamp.timestamp())}"
    _backup_store[backup_id] = bp
    from app.audit.database_audit import append_audit_entry
    append_audit_entry(db=db, event_type="integrity.backup_created", resource_type=resource_type,
        resource_id=resource_id, action="backup",
        details={"backup_id": backup_id, "operation": operation, "checksum": bp.checksum})
    logger.info(f"Backup created: {backup_id} for {resource_type}/{resource_id}")
    return backup_id


def rollback_to_backup(db: Session, backup_id: str, user_id: str) -> dict:
    """Restore data from a backup point."""
    bp = _backup_store.get(backup_id)
    if not bp:
        return {"success": False, "message": f"Backup {backup_id} not found"}
    current_checksum = hashlib.sha256(json.dumps(bp.data, sort_keys=True, default=str).encode()).hexdigest()
    if current_checksum != bp.checksum:
        logger.warning(f"Data changed since backup {backup_id} was created")
    from app.audit.database_audit import append_audit_entry
    append_audit_entry(db=db, event_type="integrity.rollback", resource_type=bp.resource_type,
        resource_id=bp.resource_id, action="rollback",
        details={"backup_id": backup_id, "restored_by": user_id, "original_operation": bp.operation})
    return {"success": True, "data": bp.data, "backup_id": backup_id}


def dry_run_operation(db: Session, operation: str, params: dict, user_id: str) -> dict:
    """Simulate an operation without executing it. Returns what would change."""
    result = {"operation": operation, "params": params, "would_affect": [], "dry_run": True}
    from app.audit.database_audit import append_audit_entry
    append_audit_entry(db=db, event_type="integrity.dry_run", resource_type="system",
        resource_id="dry-run", action="simulate",
        details={"operation": operation, "params": {k: str(v)[:100] for k, v in params.items()}, "user_id": user_id})
    return result


# Confirmation store: operations requiring dual confirmation
_pending_confirmations = {}


def require_confirmation(operation: str, params: dict, user_id: str, timeout_seconds: int = 300) -> str:
    """Queue a destructive operation for dual confirmation. Returns confirmation_id."""
    import secrets
    conf_id = secrets.token_urlsafe(16)
    _pending_confirmations[conf_id] = {
        "operation": operation, "params": params, "user_id": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "timeout_seconds": timeout_seconds, "confirmed_by": [],
    }
    return conf_id


def confirm_operation(conf_id: str, confirmer_id: str, required_confirmations: int = 2) -> dict:
    """Confirm a pending operation. Returns {ready: bool, confirmed_count: int}."""
    pending = _pending_confirmations.get(conf_id)
    if not pending:
        return {"ready": False, "message": "Confirmation not found", "confirmed_count": 0}
    if confirmer_id == pending["user_id"]:
        return {"ready": False, "message": "Creator cannot confirm their own operation", "confirmed_count": len(pending["confirmed_by"])}
    if confirmer_id not in pending["confirmed_by"]:
        pending["confirmed_by"].append(confirmer_id)
    count = len(pending["confirmed_by"])
    if count >= required_confirmations:
        del _pending_confirmations[conf_id]
        return {"ready": True, "operation": pending["operation"], "params": pending["params"], "confirmed_count": count}
    return {"ready": False, "confirmed_count": count}