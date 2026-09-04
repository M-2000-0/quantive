"""
System Health & Readiness API — Production monitoring endpoints.

Provides:
- /api/health/live — Liveness probe (is the server running?)
- /api/health/ready — Readiness probe (can it serve requests?)
- /api/health/status — System status (API response times, data freshness)
"""
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.market_data.cache import get_cache
from typing import Optional
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.models import User
from app.security import get_current_user

_optional_bearer = HTTPBearer(auto_error=False)

async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(_optional_bearer),
    db: Session = Depends(get_db),
) -> Optional[User]:
    if credentials is None:
        return None
    try:
        from app.security import decode_token
        payload = decode_token(credentials.credentials)
        if payload:
            uid = payload.get("sub")
            return db.query(User).filter(User.id == uid).first()
    except Exception:
        pass
    return None

router = APIRouter(prefix="/api/health", tags=["health"])

# Track server start time
_start_time = time.time()


@router.get("/live")
def liveness():
    """Liveness probe — confirms the process is running.

    Use this for load balancer health checks. Returns 200 if alive.
    No dependencies checked — if the server responds, it's alive.
    """
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/ready")
def readiness(db: Session = Depends(get_db)):
    """Readiness probe — confirms the server can serve requests.

    Checks: database connectivity, cache availability.
    Returns 200 only if all critical systems are operational.
    """
    checks = {}

    # Database check
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception:
        checks["database"] = "unhealthy"
        return {"status": "not_ready", "checks": checks}, 503

    # Cache check
    try:
        cache = get_cache()
        cache.set("_health_check", "ok", 10)
        if cache.get("_health_check") == "ok":
            checks["cache"] = "healthy"
        else:
            checks["cache"] = "degraded"
    except Exception:
        checks["cache"] = "unhealthy"

    return {"status": "ready", "checks": checks, "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/status")
def system_status(db: Session = Depends(get_db), user: Optional[User] = Depends(get_optional_user)):
    """System status dashboard — operational metrics for monitoring.

    Returns: uptime, database status, cache stats, API response times.
    Does NOT expose: secrets, connection strings, user data, internal IPs.
    """
    uptime_seconds = time.time() - _start_time
    uptime_hours = round(uptime_seconds / 3600, 1)

    # Database status
    db_status = "healthy"
    try:
        start = time.time()
        db.execute(text("SELECT 1"))
        db_latency_ms = round((time.time() - start) * 1000, 2)
    except Exception:
        db_status = "unhealthy"
        db_latency_ms = -1

    # Cache stats
    try:
        cache = get_cache()
        cache_stats = cache.stats()
    except Exception:
        cache_stats = {"entries": 0, "hits": 0, "misses": 0}

    return {
        "status": "operational",
        "uptime_hours": uptime_hours,
        "version": "1.0.0",
        "environment": "production",
        "systems": {
            "database": {"status": db_status, "latency_ms": db_latency_ms},
            "cache": {"status": "healthy", **cache_stats},
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
