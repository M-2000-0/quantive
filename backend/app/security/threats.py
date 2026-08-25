"""IP-based threat detection and blocking middleware.

Tracks failed login attempts per IP, blocks IPs with excessive failures,
and provides an admin endpoint to view/manage blocked IPs.
"""

import threading
import time
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.models import User, UserRole
from app.security import require_role

router = APIRouter(prefix="/api/security", tags=["security"])

# In-memory threat store (swap for Redis in production)
_failed_attempts: dict[str, list[dict]] = defaultdict(list)
_blocked_ips: dict[str, float] = {}  # ip -> unblock_time
_lock = threading.Lock()

# Thresholds
FAILED_LOGIN_THRESHOLD = 10        # failures before IP block
FAILED_LOGIN_WINDOW = 3600         # 1 hour window
IP_BLOCK_DURATION = 3600           # 1 hour block
FAILED_ENDPOINT_THRESHOLD = 50     # 4xx/5xx hits before block
FAILED_ENDPOINT_WINDOW = 300       # 5 minute window
ENDPOINT_BLOCK_DURATION = 900      # 15 minute block

# Exempt paths (health checks, docs)
EXEMPT_PATHS = {"/api/health", "/docs", "/redoc", "/openapi.json"}


class ThreatDetectionMiddleware(BaseHTTPMiddleware):
    """Middleware that tracks failed requests per IP and blocks malicious IPs."""

    async def dispatch(self, request: Request, call_next):
        client_ip = _get_client_ip(request)

        # Skip exempt paths
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        # Check if IP is blocked
        with _lock:
            if client_ip in _blocked_ips:
                if time.time() < _blocked_ips[client_ip]:
                    remaining = int(_blocked_ips[client_ip] - time.time())
                    return JSONResponse(
                        status_code=403,
                        content={
                            "detail": "IP address temporarily blocked due to suspicious activity",
                            "retry_after": remaining,
                            "code": "ip_blocked",
                        },
                        headers={"Retry-After": str(remaining)},
                    )
                else:
                    # Block expired
                    del _blocked_ips[client_ip]

        response = await call_next(request)

        # Track failed responses (4xx and 5xx, excluding 404)
        if response.status_code >= 400 and response.status_code != 404:
            now = time.time()
            with _lock:
                _failed_attempts[client_ip].append({
                    "time": now,
                    "path": request.url.path,
                    "status": response.status_code,
                    "method": request.method,
                })
                # Prune old entries
                _failed_attempts[client_ip] = [
                    e for e in _failed_attempts[client_ip]
                    if now - e["time"] < FAILED_ENDPOINT_WINDOW
                ]
                # Check threshold
                if len(_failed_attempts[client_ip]) >= FAILED_ENDPOINT_THRESHOLD:
                    _blocked_ips[client_ip] = time.time() + ENDPOINT_BLOCK_DURATION
                    _failed_attempts[client_ip] = []

        return response


def track_failed_login(email: str, ip: str):
    """Track a failed login attempt for an IP."""
    now = time.time()
    with _lock:
        key = f"login:{ip}"
        _failed_attempts[key].append({"time": now, "email": email})
        _failed_attempts[key] = [
            e for e in _failed_attempts[key]
            if now - e["time"] < FAILED_LOGIN_WINDOW
        ]
        if len(_failed_attempts[key]) >= FAILED_LOGIN_THRESHOLD:
            _blocked_ips[ip] = time.time() + IP_BLOCK_DURATION
            _failed_attempts[key] = []


def is_ip_blocked(ip: str) -> bool:
    """Check if an IP is currently blocked."""
    with _lock:
        if ip in _blocked_ips:
            if time.time() < _blocked_ips[ip]:
                return True
            del _blocked_ips[ip]
    return False


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request, respecting X-Forwarded-For."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ── Admin Security Endpoints ───────────────────────────────────────────

@router.get("/threats/blocked-ips")
def get_blocked_ips(user: User = Depends(require_role(UserRole.ADMIN))):
    """List currently blocked IPs. Admin only."""
    now = time.time()
    with _lock:
        blocked = [
            {"ip": ip, "unblocks_at": datetime.fromtimestamp(t, tz=timezone.utc).isoformat(),
             "remaining_seconds": int(t - now)}
            for ip, t in _blocked_ips.items()
            if t > now
        ]
    return {"blocked_ips": blocked, "count": len(blocked)}


@router.post("/threats/unblock/{ip}")
def unblock_ip(ip: str, user: User = Depends(require_role(UserRole.ADMIN))):
    """Manually unblock an IP address. Admin only."""
    with _lock:
        if ip in _blocked_ips:
            del _blocked_ips[ip]
            return {"detail": f"IP {ip} has been unblocked"}
    return {"detail": f"IP {ip} was not blocked"}


@router.get("/threats/failed-logins")
def get_failed_logins(
    hours: int = 24,
    user: User = Depends(require_role(UserRole.ADMIN)),
):
    """View failed login attempts in the last N hours. Admin only."""
    cutoff = time.time() - (hours * 3600)
    with _lock:
        results = []
        for key, attempts in _failed_attempts.items():
            if key.startswith("login:"):
                ip = key.replace("login:", "")
                recent = [a for a in attempts if a["time"] > cutoff]
                if recent:
                    results.append({
                        "ip": ip,
                        "attempts": len(recent),
                        "emails_targeted": list(set(a.get("email", "") for a in recent)),
                        "last_attempt": datetime.fromtimestamp(
                            max(a["time"] for a in recent), tz=timezone.utc
                        ).isoformat(),
                    })
    results.sort(key=lambda x: x["attempts"], reverse=True)
    return {"failed_logins": results, "period_hours": hours}


@router.get("/threats/summary")
def get_threat_summary(user: User = Depends(require_role(UserRole.ADMIN))):
    """Get a summary of current security threats. Admin only."""
    now = time.time()
    with _lock:
        blocked_count = len([t for t in _blocked_ips.values() if t > now])
        failed_login_count = sum(
            len(attempts) for key, attempts in _failed_attempts.items()
            if key.startswith("login:")
        )
        failed_endpoint_count = sum(
            len(attempts) for key, attempts in _failed_attempts.items()
            if not key.startswith("login:")
        )
    return {
        "blocked_ips": blocked_count,
        "failed_logins_recent": failed_login_count,
        "failed_endpoints_recent": failed_endpoint_count,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
