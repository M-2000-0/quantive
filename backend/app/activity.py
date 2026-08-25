"""Activity logging system for automatic user action tracking.

Provides:
- Middleware that logs all API requests with user attribution
- Resource-level activity tracking
- Activity log querying and analytics
"""
import logging
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("quantive.activity")

# ── Activity Logger ─────────────────────────────────────────────────────────

class ActivityLogger:
    """Logs user activities to the database.

    Usage:
        logger = ActivityLogger()
        logger.log(
            user_id="abc",
            org_id="org1",
            action="created",
            resource_type="portfolio",
            resource_id="port123",
        )
    """

    def __init__(self):
        self._log: list[dict] = []

    def log(
        self,
        user_id: str,
        org_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
    ):
        """Record an activity event.

        Args:
            user_id: User who performed the action
            org_id: Organization context
            action: Action performed (created, updated, deleted, viewed, etc.)
            resource_type: Type of resource (portfolio, instrument, optimization, etc.)
            resource_id: ID of the resource
            details: Additional context (optional)
            ip_address: Client IP address (optional)
        """
        entry = {
            "user_id": user_id,
            "org_id": org_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
            "ip_address": ip_address,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._log.append(entry)

        # Also log to Python logger for observability
        logger.info(
            f"activity: {action} {resource_type}/{resource_id} "
            f"by user={user_id} org={org_id}"
        )

    def get_recent(
        self,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """Query recent activities with optional filters."""
        results = self._log.copy()

        if user_id:
            results = [r for r in results if r["user_id"] == user_id]
        if org_id:
            results = [r for r in results if r["org_id"] == org_id]
        if resource_type:
            results = [r for r in results if r["resource_type"] == resource_type]
        if action:
            results = [r for r in results if r["action"] == action]

        return results[-limit:]

    def get_stats(self, org_id: Optional[str] = None) -> dict:
        """Get activity statistics."""
        logs = self._log
        if org_id:
            logs = [entry for entry in logs if entry["org_id"] == org_id]

        if not logs:
            return {"total": 0, "by_action": {}, "by_resource": {}}

        by_action = {}
        by_resource = {}
        for entry in logs:
            by_action[entry["action"]] = by_action.get(entry["action"], 0) + 1
            by_resource[entry["resource_type"]] = by_resource.get(entry["resource_type"], 0) + 1

        return {
            "total": len(logs),
            "by_action": by_action,
            "by_resource": by_resource,
            "earliest": logs[0]["created_at"] if logs else None,
            "latest": logs[-1]["created_at"] if logs else None,
        }


# Singleton
_activity_logger: Optional[ActivityLogger] = None


def get_activity_logger() -> ActivityLogger:
    global _activity_logger
    if _activity_logger is None:
        _activity_logger = ActivityLogger()
    return _activity_logger


# ── FastAPI Middleware ──────────────────────────────────────────────────────

class ActivityMiddleware(BaseHTTPMiddleware):
    """Middleware that automatically logs API requests as activity events.

    Captures:
    - User ID from JWT token
    - Request method and path
    - Response status code
    - Response time
    - IP address
    """

    # Paths to skip (health checks, docs, etc.)
    SKIP_PATHS = {
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/health",
        "/api/auth/login",
        "/api/auth/register",
        "/api/auth/refresh",
        "/favicon.ico",
    }

    # Path patterns that map to resource types
    RESOURCE_PATTERNS = {
        "/api/portfolios": "portfolio",
        "/api/optimizations": "optimization",
        "/api/audit": "audit_event",
        "/api/auth/mfa": "mfa",
    }

    # Method to action mapping
    METHOD_ACTIONS = {
        "GET": "viewed",
        "POST": "created",
        "PUT": "updated",
        "PATCH": "updated",
        "DELETE": "deleted",
    }

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip certain paths
        path = request.url.path
        if any(path.startswith(skip) for skip in self.SKIP_PATHS):
            return await call_next(request)

        # Skip non-API paths
        if not path.startswith("/api/"):
            return await call_next(request)

        start_time = time.time()

        # Extract user info from request state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        org_id = getattr(request.state, "org_id", None)
        ip_address = request.client.host if request.client else None

        # Process request
        response = await call_next(request)
        duration_ms = int((time.time() - start_time) * 1000)

        # Determine resource type and action
        resource_type = self._get_resource_type(path)
        action = self.METHOD_ACTIONS.get(request.method, "unknown")
        resource_id = self._extract_resource_id(path)

        # Only log if we have a user and a meaningful action
        if user_id and org_id and resource_type:
            # Skip logging for list views (GET without specific ID) to reduce noise
            if not (request.method == "GET" and not resource_id):
                activity = get_activity_logger()
                activity.log(
                    user_id=user_id,
                    org_id=org_id,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id or "list",
                    details={
                        "method": request.method,
                        "path": path,
                        "status_code": response.status_code,
                        "duration_ms": duration_ms,
                    },
                    ip_address=ip_address,
                )

        # Log API usage metrics
        logger.info(
            f"api: {request.method} {path} "
            f"status={response.status_code} "
            f"duration={duration_ms}ms"
        )

        return response

    def _get_resource_type(self, path: str) -> Optional[str]:
        """Map URL path to resource type."""
        for pattern, resource_type in self.RESOURCE_PATTERNS.items():
            if path.startswith(pattern):
                return resource_type
        return None

    def _extract_resource_id(self, path: str) -> Optional[str]:
        """Extract resource ID from URL path."""
        parts = path.strip("/").split("/")
        # Pattern: /api/{resource}/{id}
        if len(parts) >= 3 and parts[0] == "api":
            potential_id = parts[2]
            # UUID-like strings or short IDs
            if len(potential_id) >= 8 and ("-" in potential_id or potential_id.isalnum()):
                return potential_id
        return None
