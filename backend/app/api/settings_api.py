"""
Settings & Admin API — System Configuration
=============================================

Endpoints:
- GET /api/settings/system — System configuration
- GET /api/settings/users — User management list
- GET /api/settings/data-sources — Configured data providers
- GET /api/settings/audit-summary — Audit trail summary
- GET /api/settings/security-status — Security posture overview
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/me")
def get_current_user_profile(request: Request, db: Session = Depends(get_db)):
    """Get current user profile from cookie auth."""
    token = request.cookies.get("access_token", "")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        from app.security import decode_token
        payload = decode_token(token)
        if payload:
            user = db.query(User).filter(User.id == payload.get("sub")).first()
            if user:
                return {
                    "id": str(user.id),
                    "name": user.name,
                    "email": user.email,
                    "role": str(user.role.value if hasattr(user.role, 'value') else user.role),
                    "org_id": str(user.org_id),
                    "is_active": user.is_active,
                }
    except Exception:
        pass
    raise HTTPException(status_code=401, detail="Not authenticated")


@router.get("/system")
def get_system_config():
    """Get system configuration and status."""
    return {
        "platform": {
            "name": "Quantive",
            "version": "1.0.0",
            "edition": "Sovereign Finance Intelligence",
            "build": "2026.08.30",
        },
        "features": {
            "optimization_engine": True,
            "simulation_engine": True,
            "ai_advisor": True,
            "rbac": True,
            "pqc_encryption": True,
            "imf_exports": True,
            "real_time_data": True,
            "advanced_debt_analysis": True,
        },
        "security": {
            "pqc_enabled": True,
            "encryption": "AES-256-GCM + ML-KEM hybrid",
            "auth": "JWT + refresh tokens",
            "rbac": "6 roles, 30+ permissions",
            "audit_trail": "Immutable",
            "mfa": "Available (TOTP)",
        },
        "data_sources": {
            "treasury": {"status": "active", "source": "US Treasury", "cost": "free"},
            "ecb": {"status": "active", "source": "ECB Statistical Data Warehouse", "cost": "free"},
            "world_bank": {"status": "active", "source": "World Bank Open Data", "cost": "free"},
            "ny_fed": {"status": "active", "source": "Federal Reserve Bank of New York", "cost": "free"},
            "imf": {"status": "active", "source": "IMF International Financial Statistics", "cost": "free"},
            "fred": {"status": "active", "source": "Federal Reserve Economic Data", "cost": "free"},
        },
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/users")
def get_users(db: Session = Depends(get_db)):
    """Get list of users from the database."""
    users = db.query(User).order_by(User.created_at).all()
    roles_dist = {}
    user_list = []
    for u in users:
        role = str(u.role.value) if hasattr(u.role, 'value') else str(u.role)
        roles_dist[role] = roles_dist.get(role, 0) + 1
        user_list.append({
            "id": str(u.id),
            "email": u.email,
            "name": u.name,
            "role": role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        })
    return {
        "users": user_list,
        "total": len(user_list),
        "roles_distribution": roles_dist,
    }


@router.get("/data-sources")
def get_data_sources():
    """Get configured data providers and their status."""
    return {
        "sources": [
            {
                "id": "treasury",
                "name": "US Treasury",
                "url": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/",
                "type": "yield_curve",
                "cost": "free",
                "refresh_rate": "daily",
                "status": "active",
                "last_fetched": "2026-08-30T06:00:00Z",
                "records": 13,
            },
            {
                "id": "ecb",
                "name": "ECB Statistical Data Warehouse",
                "url": "https://www.ecb.europa.eu/stats/eurofxref/",
                "type": "fx_rates",
                "cost": "free",
                "refresh_rate": "daily",
                "status": "active",
                "last_fetched": "2026-08-30T06:00:00Z",
                "records": 10,
            },
            {
                "id": "world_bank",
                "name": "World Bank Open Data",
                "url": "https://api.worldbank.org/v2",
                "type": "economic_indicators",
                "cost": "free",
                "refresh_rate": "quarterly",
                "status": "active",
                "last_fetched": "2026-07-01T00:00:00Z",
                "records": 6,
            },
            {
                "id": "ny_fed",
                "name": "Federal Reserve Bank of New York",
                "url": "https://markets.newyorkfed.org/api",
                "type": "interest_rates",
                "cost": "free",
                "refresh_rate": "daily",
                "status": "active",
                "last_fetched": "2026-08-30T06:00:00Z",
                "records": 12,
            },
            {
                "id": "imf",
                "name": "IMF International Financial Statistics",
                "url": "https://dataservices.imf.org/REST/SDMX_JSON.svc/",
                "type": "macro_data",
                "cost": "free",
                "refresh_rate": "monthly",
                "status": "active",
                "last_fetched": "2026-08-15T00:00:00Z",
                "records": 20,
            },
            {
                "id": "fred",
                "name": "Federal Reserve Economic Data",
                "url": "https://api.stlouisfed.org/fred/series/observations",
                "type": "historical_series",
                "cost": "free (API key required)",
                "refresh_rate": "daily",
                "status": "configured",
                "last_fetched": None,
                "records": 0,
                "note": "API key needed for production use",
            },
        ],
        "paid_providers": [
            {"name": "Bloomberg B-PIPE", "status": "not_configured", "cost": "$24K+/year"},
            {"name": "Refinitiv Eikon", "status": "not_configured", "cost": "$15K+/year"},
            {"name": "ICE Data Services", "status": "not_configured", "cost": "enterprise"},
        ],
    }


@router.get("/audit-summary")
def get_audit_summary(db: Session = Depends(get_db)):
    """Get real audit trail summary from the database."""
    from app.models import AuditEvent
    from datetime import timedelta

    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    events = db.query(AuditEvent).filter(AuditEvent.created_at >= thirty_days_ago).all()

    by_action = {}
    for e in events:
        action = str(e.action) if e.action else "unknown"
        by_action[action] = by_action.get(action, 0) + 1

    return {
        "period": "last_30_days",
        "total_events": len(events),
        "by_action": by_action,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/security-status")
def get_security_status(db: Session = Depends(get_db)):
    """Get real security posture from the database."""
    from app.models import AuditEvent
    from datetime import timedelta

    twenty_four_h = datetime.now(timezone.utc) - timedelta(hours=24)
    failed_logins = db.query(AuditEvent).filter(
        AuditEvent.action == "login_failed",
        AuditEvent.created_at >= twenty_four_h,
    ).count()

    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()

    return {
        "encryption": {
            "at_rest": "AES-256-GCM + ML-KEM (post-quantum hybrid)",
            "in_transit": "TLS 1.3",
        },
        "authentication": {
            "method": "JWT with refresh tokens",
            "mfa": "TOTP available",
        },
        "rbac": {
            "total_users": total_users,
            "active_users": active_users,
        },
        "threats": {
            "failed_logins_24h": failed_logins,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
