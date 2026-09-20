"""Audit Trail & Role-Based Access Control (RBAC) System.

Provides immutable audit logging, role-based permissions,
and user management for government deployments.
"""

import uuid
import time
import hashlib
import threading
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timezone
from functools import wraps


# ── Roles & Permissions ──────────────────────────────────────────────

ROLES = {
    "minister": {
        "description": "Finance Minister / Secretary",
        "permissions": {"read", "write", "approve", "admin", "view_all", "export", "delete"},
    },
    "director_general": {
        "description": "Director General of Debt Management",
        "permissions": {"read", "write", "approve", "view_all", "export"},
    },
    "debt_manager": {
        "description": "Senior Debt Management Officer",
        "permissions": {"read", "write", "view_all", "export"},
    },
    "analyst": {
        "description": "Debt/Government Finance Analyst",
        "permissions": {"read", "write", "export"},
    },
    "fiscal_planner": {
        "description": "Fiscal Planning Officer",
        "permissions": {"read", "write_fiscal", "export"},
    },
    "auditor": {
        "description": "Internal/External Auditor",
        "permissions": {"read", "view_all", "audit_trail"},
    },
    "viewer": {
        "description": "Read-only viewer",
        "permissions": {"read"},
    },
    "system_admin": {
        "description": "System administrator",
        "permissions": {"read", "write", "approve", "admin", "view_all", "export", "delete", "manage_users"},
    },
}

PERMISSION_DESCRIPTIONS = {
    "read": "View dashboards and reports",
    "write": "Create and modify debt instruments, scenarios, budgets",
    "write_fiscal": "Modify fiscal data only",
    "approve": "Approve debt operations and policy changes",
    "admin": "System administration",
    "view_all": "View data across all departments/entities",
    "export": "Export data and generate reports",
    "delete": "Delete records",
    "audit_trail": "Access audit logs",
    "manage_users": "Create and manage user accounts",
}


class AuditLogger:
    """Immutable audit log with integrity verification."""

    def __init__(self):
        self._lock = threading.Lock()
        self._log: List[dict] = []
        self._prev_hash = "genesis"

    def log(self, user_id: str, action: str, resource: str, details: dict = None, ip_address: str = "") -> dict:
        """Record an audit event."""
        entry = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "details": details or {},
            "ip_address": ip_address,
            "prev_hash": self._prev_hash,
        }

        # Compute integrity hash
        hash_input = f"{entry['id']}{entry['timestamp']}{entry['user_id']}{entry['action']}{entry['resource']}{self._prev_hash}"
        entry["hash"] = hashlib.sha256(hash_input.encode()).hexdigest()

        with self._lock:
            self._log.append(entry)
            self._prev_hash = entry["hash"]

        return entry

    def query(
        self,
        user_id: str = None,
        action: str = None,
        resource: str = None,
        start_time: str = None,
        end_time: str = None,
        limit: int = 100,
    ) -> List[dict]:
        """Query audit log with filters."""
        with self._lock:
            results = list(self._log)

        if user_id:
            results = [e for e in results if e["user_id"] == user_id]
        if action:
            results = [e for e in results if e["action"] == action]
        if resource:
            results = [e for e in results if resource in e["resource"]]
        if start_time:
            results = [e for e in results if e["timestamp"] >= start_time]
        if end_time:
            results = [e for e in results if e["timestamp"] <= end_time]

        return list(reversed(results[-limit:]))

    def verify_integrity(self) -> dict:
        """Verify audit log integrity by checking hash chain."""
        with self._lock:
            entries = list(self._log)

        violations = 0
        for i in range(1, len(entries)):
            expected_prev = entries[i - 1]["hash"]
            if entries[i]["prev_hash"] != expected_prev:
                violations += 1

        return {
            "total_entries": len(entries),
            "violations": violations,
            "integrity": "valid" if violations == 0 else "compromised",
            "last_entry_time": entries[-1]["timestamp"] if entries else None,
        }


# ── RBAC Manager ─────────────────────────────────────────────────────

class User:
    def __init__(self, user_id: str, name: str, role: str, department: str = "", active: bool = True):
        self.user_id = user_id
        self.name = name
        self.role = role
        self.department = department
        self.active = active
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.last_login = None
        self.login_count = 0

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "name": self.name,
            "role": self.role,
            "department": self.department,
            "active": self.active,
            "permissions": list(ROLES.get(self.role, {}).get("permissions", set())),
            "created_at": self.created_at,
            "last_login": self.last_login,
            "login_count": self.login_count,
        }


class RBACManager:
    def __init__(self, audit_logger: AuditLogger):
        self._lock = threading.Lock()
        self._users: Dict[str, User] = {}
        self._audit = audit_logger

    def create_user(self, user_id: str, name: str, role: str, department: str = "") -> dict:
        if role not in ROLES:
            return {"error": f"Invalid role: {role}. Valid: {list(ROLES.keys())}"}

        with self._lock:
            if user_id in self._users:
                return {"error": f"User {user_id} already exists"}

            user = User(user_id, name, role, department)
            self._users[user_id] = user

        self._audit.log("system", "user_created", f"users/{user_id}", {"name": name, "role": role})
        return user.to_dict()

    def get_user(self, user_id: str) -> Optional[dict]:
        with self._lock:
            user = self._users.get(user_id)
        return user.to_dict() if user else None

    def list_users(self) -> List[dict]:
        with self._lock:
            return [u.to_dict() for u in self._users.values()]

    def has_permission(self, user_id: str, permission: str) -> bool:
        with self._lock:
            user = self._users.get(user_id)
            if not user or not user.active:
                return False
            return permission in ROLES.get(user.role, {}).get("permissions", set())

    def record_login(self, user_id: str):
        with self._lock:
            user = self._users.get(user_id)
            if user:
                user.last_login = datetime.now(timezone.utc).isoformat()
                user.login_count += 1

        self._audit.log(user_id, "login", "auth")

    def deactivate_user(self, user_id: str) -> bool:
        with self._lock:
            user = self._users.get(user_id)
            if user:
                user.active = False
                self._audit.log("system", "user_deactivated", f"users/{user_id}")
                return True
        return False


# ── Permission Decorator ─────────────────────────────────────────────

def require_permission(permission: str):
    """Decorator to enforce permission on API endpoints."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_id = kwargs.get("user_id") or (args[0] if args else None)
            if user_id:
                manager = get_rbac_manager()
                if not manager.has_permission(user_id, permission):
                    from fastapi import HTTPException
                    raise HTTPException(status_code=403, detail=f"Permission denied: requires '{permission}'")
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ── Singletons ───────────────────────────────────────────────────────

_audit = None
_rbac = None


def get_audit_logger() -> AuditLogger:
    global _audit
    if _audit is None:
        _audit = AuditLogger()
    return _audit


def get_rbac_manager() -> RBACManager:
    global _rbac
    if _rbac is None:
        _rbac = RBACManager(get_audit_logger())
    return _rbac
