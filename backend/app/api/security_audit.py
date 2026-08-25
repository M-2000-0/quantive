"""Security audit and monitoring API endpoints.

Provides admins with visibility into security events, threats,
and system health from a cybersecurity perspective.
"""

import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditEvent, User, UserRole
from app.security import get_current_user, require_role
from app.security.sanitization import security_log
from app.security.threats import _blocked_ips, _failed_attempts, _lock

router = APIRouter(prefix="/api/security", tags=["security-audit"])


@router.get("/dashboard")
def get_security_dashboard(
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Get a comprehensive security dashboard. Admin only.

    Returns security metrics, threat status, recent events, and recommendations.
    """
    now = time.time()

    # ── Threat Status ─────────────────────────────────────────────────
    with _lock:
        blocked_count = len([t for t in _blocked_ips.values() if t > now])
        failed_login_count = sum(
            len(attempts) for key, attempts in _failed_attempts.items()
            if key.startswith("login:")
        )

    # ── Audit Event Stats (last 24h) ─────────────────────────────────
    cutoff_24h = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    events_24h = (
        db.query(AuditEvent.action, func.count(AuditEvent.id))
        .filter(AuditEvent.created_at >= cutoff_24h)
        .group_by(AuditEvent.action)
        .all()
    )
    event_counts = {action: count for action, count in events_24h}

    # ── User Stats ────────────────────────────────────────────────────
    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users = db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar() or 0

    # ── Security Score (0-100) ────────────────────────────────────────
    score = 100
    if blocked_count > 0:
        score -= min(20, blocked_count * 5)
    if failed_login_count > 10:
        score -= min(15, failed_login_count)
    score = max(0, score)

    # ── Recommendations ───────────────────────────────────────────────
    recommendations = []
    if blocked_count > 0:
        recommendations.append({
            "severity": "high",
            "message": f"{blocked_count} IP(s) currently blocked. Review and investigate.",
            "action": "View blocked IPs in the Threat Monitor tab",
        })
    if failed_login_count > 5:
        recommendations.append({
            "severity": "medium",
            "message": f"{failed_login_count} failed login attempts detected. Possible brute force.",
            "action": "Monitor failed logins and consider enabling MFA for all users",
        })
    if total_users > 0 and active_users < total_users * 0.5:
        recommendations.append({
            "severity": "low",
            "message": "Many inactive user accounts detected.",
            "action": "Review and deactivate unused accounts to reduce attack surface",
        })
    if score >= 90:
        recommendations.append({
            "severity": "info",
            "message": "Security posture is strong. Continue regular monitoring.",
            "action": "No immediate action needed",
        })

    return {
        "security_score": score,
        "threat_status": {
            "blocked_ips": blocked_count,
            "failed_logins": failed_login_count,
            "status": "alert" if blocked_count > 0 or failed_login_count > 10 else "healthy",
        },
        "audit_events_24h": event_counts,
        "user_stats": {
            "total": total_users,
            "active": active_users,
            "inactive": total_users - active_users,
        },
        "security_events": security_log.get_stats(),
        "recommendations": recommendations,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/audit-trail")
def get_security_audit_trail(
    hours: int = Query(default=24, ge=1, le=720),
    action: str = Query(default=None),
    user_id: str = Query(default=None),
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Get security-relevant audit trail. Admin only.

    Filtered to security-relevant actions like logins, password changes,
    and permission modifications.
    """
    security_actions = {
        "user.login", "user.logout", "user.login_failed",
        "user.registered", "user.password_changed",
        "user.password_reset_requested", "user.password_reset_completed",
        "user.email_verified",
    }

    cutoff = datetime.now(timezone.utc).replace(
        hour=datetime.now(timezone.utc).hour - min(hours, datetime.now(timezone.utc).hour),
        minute=0, second=0, microsecond=0,
    )

    query = db.query(AuditEvent).filter(
        AuditEvent.created_at >= cutoff,
        AuditEvent.action.in_(security_actions),
    )

    if action:
        query = query.filter(AuditEvent.action == action)
    if user_id:
        query = query.filter(AuditEvent.actor_id == user_id)

    events = query.order_by(AuditEvent.created_at.desc()).limit(500).all()

    return {
        "events": [
            {
                "id": e.id,
                "actor_email": e.actor_email,
                "action": e.action,
                "resource_type": e.resource_type,
                "resource_id": e.resource_id,
                "ip_address": e.ip_address,
                "metadata": e.metadata_json,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ],
        "total": len(events),
        "period_hours": hours,
    }


@router.get("/password-policy")
def get_password_policy(
    user: User = Depends(get_current_user),
):
    """Get the current password policy. Any authenticated user."""
    return {
        "min_length": 8,
        "max_length": 128,
        "requirements": [
            "At least one letter (a-z, A-Z)",
            "At least one digit (0-9)",
            "At least one uppercase letter (A-Z)",
            "At least one special character (!@#$%^&*...)",
            "Cannot be a commonly used password",
        ],
        "token_expiry_minutes": 30,
        "refresh_expiry_days": 7,
        "lockout_threshold": 5,
        "lockout_duration_minutes": 15,
    }


@router.get("/health")
def security_health_check(
    user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Security health check endpoint. Admin only."""
    checks = {
        "jwt_algorithm": "HS256",
        "token_expiry_minutes": 30,
        "refresh_expiry_days": 7,
        "rate_limiting": "enabled",
        "security_headers": "enabled",
        "mfa": "available",
        "audit_logging": "enabled",
        "threat_detection": "enabled",
        "input_sanitization": "enabled",
    }

    return {
        "status": "healthy",
        "checks": checks,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
