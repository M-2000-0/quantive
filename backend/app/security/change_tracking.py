"""Change Tracking - Before/After Diff for Every Edit."""

import json
from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy.orm import Session


def compute_diff(old_values: dict, new_values: dict) -> dict:
    changes = {}
    all_keys = set(list(old_values.keys()) + list(new_values.keys()))
    for key in all_keys:
        old = old_values.get(key)
        new = new_values.get(key)
        if old != new:
            changes[key] = {"before": old, "after": new}
    return changes


def record_change(db: Session, resource_type: str, resource_id: str, old_values: dict, new_values: dict, user_id: str, reason: Optional[str] = None):
    from app.audit.database_audit import append_audit_entry
    diff = compute_diff(old_values, new_values)
    if not diff:
        return None
    return append_audit_entry(db=db, event_type="data.update", resource_type=resource_type, resource_id=resource_id, action="update",
        details={"changes": diff, "changed_by": user_id, "reason": reason, "field_count": len(diff)})


def record_create(db: Session, resource_type: str, resource_id: str, values: dict, user_id: str):
    from app.audit.database_audit import append_audit_entry
    return append_audit_entry(db=db, event_type="data.create", resource_type=resource_type, resource_id=resource_id, action="create",
        details={"values": {k: str(v)[:200] for k, v in values.items()}, "created_by": user_id})


def record_delete(db: Session, resource_type: str, resource_id: str, values: dict, user_id: str, reason: str):
    from app.audit.database_audit import append_audit_entry
    return append_audit_entry(db=db, event_type="data.delete", resource_type=resource_type, resource_id=resource_id, action="delete",
        details={"deleted_values": {k: str(v)[:200] for k, v in values.items()}, "deleted_by": user_id, "reason": reason})