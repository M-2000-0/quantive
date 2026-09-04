"""Database-backed Immutable Audit Trail.

Unlike the in-memory version, this persists to PostgreSQL and survives restarts.
Each entry is hash-chained. The database enforces append-only via:
1. No UPDATE or DELETE permissions for the application role
2. Hash chain verification on read
3. Exportable for SOC 2, ISO 27001, IMF compliance audits
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.database import get_org_id, get_user_id
from app.models import DatabaseAuditEntry


_GENESIS_HASH = "0" * 64


def _compute_data_hash(data: dict) -> str:
    data_str = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(data_str.encode()).hexdigest()


def _compute_chain_hash(data_hash: str, previous_hash: str) -> str:
    return hashlib.sha256(f"{data_hash}{previous_hash}".encode()).hexdigest()


def append_audit_entry(
    db: Session,
    event_type: str,
    resource_type: str,
    resource_id: str,
    action: str,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
) -> DatabaseAuditEntry:
    """Append an immutable audit entry to the database."""
    # Get next index
    last_entry = (
        db.query(DatabaseAuditEntry)
        .order_by(DatabaseAuditEntry.index.desc())
        .first()
    )
    next_index = (last_entry.index + 1) if last_entry else 0
    previous_hash = last_entry.chain_hash if last_entry else _GENESIS_HASH

    # Build data payload
    data_payload = {
        "index": next_index,
        "event_type": event_type,
        "actor_id": get_user_id(),
        "actor_email": None,
        "org_id": get_org_id(),
        "resource_type": resource_type,
        "resource_id": resource_id,
        "action": action,
        "details": details or {},
        "ip_address": ip_address,
        "previous_hash": previous_hash,
    }

    data_hash = _compute_data_hash(data_payload)
    chain_hash = _compute_chain_hash(data_hash, previous_hash)

    entry = DatabaseAuditEntry(
        index=next_index,
        timestamp=datetime.now(timezone.utc),
        event_type=event_type,
        actor_id=get_user_id(),
        org_id=get_org_id(),
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        details=details or {},
        ip_address=ip_address,
        previous_hash=previous_hash,
        data_hash=data_hash,
        chain_hash=chain_hash,
    )
    db.add(entry)
    # Note: DO NOT commit here — let the caller commit as part of their transaction
    return entry


def verify_chain(db: Session, org_id: Optional[str] = None) -> tuple[bool, Optional[int]]:
    """Verify the entire audit chain integrity."""
    query = db.query(DatabaseAuditEntry).order_by(DatabaseAuditEntry.index.asc())
    if org_id:
        query = query.filter(DatabaseAuditEntry.org_id == org_id)
    entries = query.all()

    prev_hash = _GENESIS_HASH
    for i, entry in enumerate(entries):
        if entry.previous_hash != prev_hash:
            return False, entry.index

        # Recompute data hash
        data_payload = {
            "index": entry.index,
            "event_type": entry.event_type,
            "actor_id": entry.actor_id,
            "actor_email": entry.actor_email,
            "org_id": entry.org_id,
            "resource_type": entry.resource_type,
            "resource_id": entry.resource_id,
            "action": entry.action,
            "details": entry.details,
            "ip_address": entry.ip_address,
            "previous_hash": entry.previous_hash,
        }
        expected_data_hash = _compute_data_hash(data_payload)
        if entry.data_hash != expected_data_hash:
            return False, entry.index

        expected_chain_hash = _compute_chain_hash(entry.data_hash, entry.previous_hash)
        if entry.chain_hash != expected_chain_hash:
            return False, entry.index

        prev_hash = entry.chain_hash

    return True, None


def export_for_audit(db: Session, org_id: Optional[str] = None) -> dict:
    """Export full chain for external auditors."""
    query = db.query(DatabaseAuditEntry).order_by(DatabaseAuditEntry.index.asc())
    if org_id:
        query = query.filter(DatabaseAuditEntry.org_id == org_id)
    entries = query.all()

    is_valid, broken_at = verify_chain(db, org_id)

    return {
        "export_timestamp": datetime.now(timezone.utc).isoformat(),
        "chain_status": "VALID" if is_valid else f"BROKEN at index {broken_at}",
        "total_entries": len(entries),
        "entries": [
            {
                "index": e.index,
                "timestamp": e.timestamp.isoformat(),
                "event_type": e.event_type,
                "actor_id": e.actor_id,
                "resource_type": e.resource_type,
                "resource_id": e.resource_id,
                "action": e.action,
                "details": e.details,
                "chain_hash": e.chain_hash,
            }
            for e in entries
        ],
        "verification_instructions": (
            "Verify: 1) Rebuild data_hash from fields. "
            "2) Verify chain_hash = SHA256(data_hash + previous_hash). "
            "3) Check each previous_hash matches prior chain_hash. "
            "4) Genesis hash is '0' * 64."
        ),
    }
