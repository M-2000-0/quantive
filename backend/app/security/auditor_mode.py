"""Auditor Mode - Read-Only External Access."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session


class AuditorAccess:

    def __init__(self, db: Session, auditor_id: str, auditor_email: str):
        self.db = db
        self.auditor_id = auditor_id
        self.auditor_email = auditor_email

    def generate_audit_token(self, org_id: str, expires_hours: int = 24):
        from datetime import timedelta
        payload = {"auditor_id": self.auditor_id, "org_id": org_id, "type": "auditor_readonly",
            "expires": (datetime.now(timezone.utc) + timedelta(hours=expires_hours)).isoformat(),
            "permissions": ["read:audit_log", "read:approvals", "read:decisions", "read:assumptions", "read:portfolios", "read:optimizations"]}
        token_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        from app.audit.database_audit import append_audit_entry
        append_audit_entry(db=self.db, event_type="auditor.token_generated", resource_type="auditor",
            resource_id=self.auditor_id, action="generate_token",
            details={"org_id": org_id, "expires_hours": expires_hours, "token_hash": token_hash})
        return {"token_hash": token_hash, "permissions": payload["permissions"], "expires": payload["expires"]}

    def get_audit_summary(self, org_id: str, days: int = 365):
        from app.models import DatabaseAuditEntry, AuditEvent
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        entries = self.db.query(DatabaseAuditEntry).filter(DatabaseAuditEntry.org_id == org_id, DatabaseAuditEntry.created_at >= cutoff).all()
        event_types = {}
        actors = {}
        for e in entries:
            event_types[e.event_type] = event_types.get(e.event_type, 0) + 1
            actors[e.actor_id] = actors.get(e.actor_id, 0) + 1
        from app.audit.database_audit import verify_chain
        is_valid, broken_at = verify_chain(self.db, org_id)
        return {
            "org_id": org_id,
            "period_days": days,
            "total_events": len(entries),
            "event_types": event_types,
            "unique_actors": len(actors),
            "chain_integrity": "VALID" if is_valid else f"BROKEN at {broken_at}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }