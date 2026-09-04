"""Emergency Halt - Circuit Breaker for Safety-Critical Operations."""

import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

logger = logging.getLogger("quantive.emergency")


_halt_active = False
_halt_reason = None
_halt_initiated_by = None
_halt_timestamp = None


def is_halted():
    return {"halted": _halt_active, "reason": _halt_reason, "initiated_by": _halt_initiated_by, "timestamp": _halt_timestamp}


def emergency_halt(reason, user_id, db=None):
    global _halt_active, _halt_reason, _halt_initiated_by, _halt_timestamp
    _halt_active = True
    _halt_reason = reason
    _halt_initiated_by = user_id
    _halt_timestamp = datetime.now(timezone.utc).isoformat()
    logger.critical("EMERGENCY HALT activated by %s: %s", user_id, reason)
    if db:
        from app.audit.database_audit import append_audit_entry
        append_audit_entry(db=db, event_type="emergency.halt", resource_type="system",
            resource_id="global", action="halt",
            details={"reason": reason, "initiated_by": user_id})
    return {"halted": True, "reason": reason}


def resume_operations(user_id, db=None):
    global _halt_active, _halt_reason, _halt_initiated_by, _halt_timestamp
    if not _halt_active:
        return {"success": False, "message": "No active halt to resume"}
    prev_reason = _halt_reason
    _halt_active = False
    _halt_reason = None
    _halt_initiated_by = None
    _halt_timestamp = None
    logger.info("Operations resumed by %s (was halted for: %s)", user_id, prev_reason)
    if db:
        from app.audit.database_audit import append_audit_entry
        append_audit_entry(db=db, event_type="emergency.resume", resource_type="system",
            resource_id="global", action="resume",
            details={"resumed_by": user_id, "previous_reason": prev_reason})
    return {"success": True, "message": "Operations resumed"}


HALT_REASONS = {
    "data_breach": "Suspected data breach detected. All operations halted pending investigation.",
    "integrity_failure": "Data integrity check failed. Operations halted to prevent corruption.",
    "unauthorized_access": "Unauthorized access attempt detected. Operations halted.",
    "system_compromise": "System compromise suspected. All operations halted.",
    "safety_critical": "Safety-critical issue detected. Human-in-the-loop review required.",
    "manual": "Manual emergency halt by authorized administrator.",
}


def get_halt_status():
    status = is_halted()
    status["available_reasons"] = list(HALT_REASONS.keys())
    return status