"""
RBAC Middleware for FastAPI
============================
Intercepts all /api/ requests and enforces role-based permissions.
Maps route patterns + HTTP methods to required permissions.

Usage in main.py:
    from app.security.rbac_middleware import RBACMiddleware
    app.add_middleware(RBACMiddleware)
"""

import re
import time
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.security import decode_token
from app.security.rbac import (
    Permission,
    ROLE_PERMISSIONS,
    get_user_permissions,
    has_permission,
    log_rbac_event,
)


# ── Role mapping from DB UserRole enum to RBAC role strings ──────────
# The User model stores role as ADMIN/ANALYST/VIEWER.
# Map these to the granular RBAC roles.
DB_ROLE_TO_RBAC: dict[str, str] = {
    "admin": "system_admin",
    "treasury_officer": "treasury_officer",
    "minister": "minister",
    "analyst": "analyst",
    "auditor": "auditor",
    "public_view": "public_view",
    # Default viewers get the least-privilege role
    "viewer": "public_view",
}


def map_db_role(db_role) -> str:
    """Map a DB UserRole value to its RBAC role string.

    Handles both string values ('admin') and enum types (UserRole.ADMIN).
    """
    raw = str(db_role)
    # Handle enum repr like 'UserRole.ADMIN' -> 'admin'
    if "." in raw:
        raw = raw.rsplit(".", 1)[-1]
    return DB_ROLE_TO_RBAC.get(raw.lower(), "public_view")


# ── Route → Permission Mapping ───────────────────────────────────────
# Pattern: (regex for path, HTTP method or "*" for any, required permission)
# First match wins. Order matters — more specific patterns first.

ROUTE_PERMISSIONS: list[tuple[str, str, str]] = [
    # ── Auth (self-service — no special permissions beyond being logged in) ──
    # Auth endpoints are excluded from RBAC checks (handled by auth.py itself).

    # ── User management ───────────────────────────────────────────────
    (r"/api/.*users?", "GET", Permission.USER_READ),
    (r"/api/.*users?", "POST", Permission.USER_WRITE),
    (r"/api/.*users?/.*", "PUT", Permission.USER_WRITE),
    (r"/api/.*users?/.*", "DELETE", Permission.USER_DELETE),

    # ── Portfolios ────────────────────────────────────────────────────
    (r"/api/.*portfolio.*", "POST", Permission.PORTFOLIO_WRITE),
    (r"/api/.*portfolio.*", "PUT", Permission.PORTFOLIO_WRITE),
    (r"/api/.*portfolio.*", "DELETE", Permission.PORTFOLIO_DELETE),
    (r"/api/.*portfolio.*", "GET", Permission.PORTFOLIO_READ),

    # ── Instruments ───────────────────────────────────────────────────
    (r"/api/.*instrument.*", "POST", Permission.INSTRUMENT_WRITE),
    (r"/api/.*instrument.*", "PUT", Permission.INSTRUMENT_WRITE),
    (r"/api/.*instrument.*", "DELETE", Permission.INSTRUMENT_DELETE),
    (r"/api/.*instrument.*", "GET", Permission.INSTRUMENT_READ),

    # ── Optimizations ─────────────────────────────────────────────────
    (r"/api/.*optimi[sz]ation.*", "POST", Permission.OPTIMIZATION_CREATE),
    (r"/api/.*optimi[sz]ation.*execute.*", "POST", Permission.OPTIMIZATION_EXECUTE),
    (r"/api/.*optimi[sz]ation.*", "PUT", Permission.OPTIMIZATION_CREATE),
    (r"/api/.*optimi[sz]ation.*", "DELETE", Permission.OPTIMIZATION_CREATE),
    (r"/api/.*optimi[sz]ation.*", "GET", Permission.OPTIMIZATION_READ),

    # ── Market Data ───────────────────────────────────────────────────
    (r"/api/.*market.*", "POST", Permission.MARKET_WRITE),
    (r"/api/.*market.*", "PUT", Permission.MARKET_WRITE),
    (r"/api/.*market.*", "DELETE", Permission.MARKET_WRITE),
    (r"/api/.*market.*", "GET", Permission.MARKET_READ),

    # ── Risk ──────────────────────────────────────────────────────────
    (r"/api/.*risk.*", "POST", Permission.RISK_WRITE),
    (r"/api/.*risk.*", "PUT", Permission.RISK_WRITE),
    (r"/api/.*risk.*", "DELETE", Permission.RISK_WRITE),
    (r"/api/.*risk.*", "GET", Permission.RISK_READ),

    # ── Simulation ────────────────────────────────────────────────────
    (r"/api/sim/.*monte-carlo.*", "POST", Permission.SIMULATION_RUN),
    (r"/api/.*simulat.*", "POST", Permission.SIMULATION_RUN),
    (r"/api/sim/.*", "GET", Permission.SIMULATION_READ),
    (r"/api/.*simulat.*", "GET", Permission.SIMULATION_READ),

    # ── Compliance ────────────────────────────────────────────────────
    (r"/api/.*compliance.*", "POST", Permission.COMPLIANCE_WRITE),
    (r"/api/.*compliance.*", "PUT", Permission.COMPLIANCE_WRITE),
    (r"/api/.*compliance.*", "DELETE", Permission.COMPLIANCE_WRITE),
    (r"/api/.*compliance.*", "GET", Permission.COMPLIANCE_READ),
    (r"/api/.*fiscal.*rule.*", "GET", Permission.COMPLIANCE_READ),
    (r"/api/.*fiscal.*rule.*", "POST", Permission.COMPLIANCE_WRITE),

    # ── Audit ─────────────────────────────────────────────────────────
    (r"/api/.*audit.*", "POST", Permission.AUDIT_EXPORT),
    (r"/api/.*audit.*", "PUT", Permission.AUDIT_EXPORT),
    (r"/api/.*audit.*", "DELETE", Permission.AUDIT_EXPORT),
    (r"/api/.*audit.*", "GET", Permission.AUDIT_READ),

    # ── Approvals ─────────────────────────────────────────────────────
    (r"/api/.*approv.*", "POST", Permission.APPROVAL_APPROVE),
    (r"/api/.*approv.*", "PUT", Permission.APPROVAL_APPROVE),
    (r"/api/.*approv.*", "DELETE", Permission.APPROVAL_REJECT),
    (r"/api/.*approv.*", "GET", Permission.APPROVAL_READ),

    # ── Reports ───────────────────────────────────────────────────────
    (r"/api/.*report.*", "POST", Permission.REPORT_CREATE),
    (r"/api/.*report.*", "PUT", Permission.REPORT_CREATE),
    (r"/api/.*report.*", "DELETE", Permission.REPORT_CREATE),
    (r"/api/.*report.*", "GET", Permission.REPORT_READ),
    (r"/api/.*export.*", "POST", Permission.REPORT_EXPORT),
    (r"/api/.*export.*", "GET", Permission.REPORT_EXPORT),

    # ── Settings / System ─────────────────────────────────────────────
    (r"/api/.*setting.*", "POST", Permission.SETTINGS_WRITE),
    (r"/api/.*setting.*", "PUT", Permission.SETTINGS_WRITE),
    (r"/api/.*setting.*", "DELETE", Permission.SETTINGS_WRITE),
    (r"/api/.*setting.*", "GET", Permission.SETTINGS_READ),
    (r"/api/.*system.*", "POST", Permission.SYSTEM_CONFIG),
    (r"/api/.*system.*", "PUT", Permission.SYSTEM_CONFIG),
    (r"/api/.*system.*", "DELETE", Permission.SYSTEM_ADMIN),
    (r"/api/.*system.*", "GET", Permission.SETTINGS_READ),

    # ── Advanced Debt ─────────────────────────────────────────────────
    (r"/api/advanced-debt.*", "POST", Permission.RISK_WRITE),
    (r"/api/advanced-debt.*", "GET", Permission.RISK_READ),

    # ── Scenarios ─────────────────────────────────────────────────────
    (r"/api/.*scenari.*", "POST", Permission.SIMULATION_RUN),
    (r"/api/.*scenari.*", "GET", Permission.SIMULATION_READ),

    # ── PQC / Security ───────────────────────────────────────────────
    (r"/api/pqc.*", "POST", Permission.SYSTEM_CONFIG),
    (r"/api/pqc.*", "GET", Permission.SYSTEM_CONFIG),
    (r"/api/.*secur.*", "POST", Permission.SYSTEM_CONFIG),
    (r"/api/.*secur.*", "GET", Permission.AUDIT_READ),

    # ── Notifications ─────────────────────────────────────────────────
    (r"/api/.*notif.*", "GET", Permission.REPORT_READ),
    (r"/api/.*notif.*", "PUT", Permission.REPORT_READ),
    (r"/api/.*notif.*", "DELETE", Permission.REPORT_READ),

    # ── Comments ──────────────────────────────────────────────────────
    (r"/api/.*comment.*", "POST", Permission.REPORT_CREATE),
    (r"/api/.*comment.*", "PUT", Permission.REPORT_CREATE),
    (r"/api/.*comment.*", "DELETE", Permission.REPORT_CREATE),
    (r"/api/.*comment.*", "GET", Permission.REPORT_READ),

    # ── Tags ──────────────────────────────────────────────────────────
    (r"/api/.*tag.*", "POST", Permission.PORTFOLIO_WRITE),
    (r"/api/.*tag.*", "PUT", Permission.PORTFOLIO_WRITE),
    (r"/api/.*tag.*", "DELETE", Permission.PORTFOLIO_WRITE),
    (r"/api/.*tag.*", "GET", Permission.PORTFOLIO_READ),

    # ── Watchlists ────────────────────────────────────────────────────
    (r"/api/.*watchlist.*", "POST", Permission.PORTFOLIO_WRITE),
    (r"/api/.*watchlist.*", "PUT", Permission.PORTFOLIO_WRITE),
    (r"/api/.*watchlist.*", "DELETE", Permission.PORTFOLIO_WRITE),
    (r"/api/.*watchlist.*", "GET", Permission.PORTFOLIO_READ),

    # ── Payments / Billing ────────────────────────────────────────────
    (r"/api/.*billing.*", "POST", Permission.SETTINGS_WRITE),
    (r"/api/.*billing.*", "PUT", Permission.SETTINGS_WRITE),
    (r"/api/.*billing.*", "GET", Permission.SETTINGS_READ),

    # ── Webhooks ──────────────────────────────────────────────────────
    (r"/api/.*webhook.*", "POST", Permission.SYSTEM_CONFIG),
    (r"/api/.*webhook.*", "PUT", Permission.SYSTEM_CONFIG),
    (r"/api/.*webhook.*", "DELETE", Permission.SYSTEM_CONFIG),
    (r"/api/.*webhook.*", "GET", Permission.SETTINGS_READ),

    # ── Analytics ─────────────────────────────────────────────────────
    (r"/api/.*analyt.*", "GET", Permission.RISK_READ),
    (r"/api/.*analyt.*", "POST", Permission.RISK_WRITE),

    # ── Narrative / Advisor / Copilot ─────────────────────────────────
    (r"/api/.*narrative.*", "GET", Permission.REPORT_READ),
    (r"/api/.*narrative.*", "POST", Permission.REPORT_CREATE),
    (r"/api/.*advisor.*", "GET", Permission.REPORT_READ),
    (r"/api/.*advisor.*", "POST", Permission.REPORT_CREATE),

    # ── Government / Subnational ──────────────────────────────────────
    (r"/api/.*government.*", "POST", Permission.COMPLIANCE_WRITE),
    (r"/api/.*government.*", "PUT", Permission.COMPLIANCE_WRITE),
    (r"/api/.*government.*", "DELETE", Permission.COMPLIANCE_WRITE),
    (r"/api/.*government.*", "GET", Permission.COMPLIANCE_READ),

    # ── Progress / Activity ───────────────────────────────────────────
    (r"/api/.*progress.*", "GET", Permission.PORTFOLIO_READ),
    (r"/api/.*activity.*", "GET", Permission.AUDIT_READ),
    (r"/api/.*activity.*export.*", "GET", Permission.AUDIT_EXPORT),

    # ── Preferences ───────────────────────────────────────────────────
    (r"/api/.*preference.*", "POST", Permission.PORTFOLIO_WRITE),
    (r"/api/.*preference.*", "PUT", Permission.PORTFOLIO_WRITE),
    (r"/api/.*preference.*", "DELETE", Permission.PORTFOLIO_WRITE),
    (r"/api/.*preference.*", "GET", Permission.PORTFOLIO_READ),

    # ── Scheduled / Email ─────────────────────────────────────────────
    (r"/api/.*schedul.*", "POST", Permission.REPORT_CREATE),
    (r"/api/.*schedul.*", "PUT", Permission.REPORT_CREATE),
    (r"/api/.*schedul.*", "DELETE", Permission.REPORT_CREATE),
    (r"/api/.*schedul.*", "GET", Permission.REPORT_READ),

    # ── PDF Reports ───────────────────────────────────────────────────
    (r"/api/.*pdf.*", "POST", Permission.REPORT_CREATE),
    (r"/api/.*pdf.*", "GET", Permission.REPORT_READ),

    # ── Ratings ───────────────────────────────────────────────────────
    (r"/api/.*rating.*", "POST", Permission.RISK_WRITE),
    (r"/api/.*rating.*", "PUT", Permission.RISK_WRITE),
    (r"/api/.*rating.*", "GET", Permission.RISK_READ),

    # ── ESG ───────────────────────────────────────────────────────────
    (r"/api/.*esg.*", "POST", Permission.RISK_WRITE),
    (r"/api/.*esg.*", "PUT", Permission.RISK_WRITE),
    (r"/api/.*esg.*", "GET", Permission.RISK_READ),

    # ── Maturity ──────────────────────────────────────────────────────
    (r"/api/.*maturity.*", "POST", Permission.RISK_WRITE),
    (r"/api/.*maturity.*", "PUT", Permission.RISK_WRITE),
    (r"/api/.*maturity.*", "DELETE", Permission.RISK_WRITE),
    (r"/api/.*maturity.*", "GET", Permission.RISK_READ),

    # ── Data Quality ──────────────────────────────────────────────────
    (r"/api/.*data.quality.*", "POST", Permission.MARKET_WRITE),
    (r"/api/.*data.quality.*", "PUT", Permission.MARKET_WRITE),
    (r"/api/.*data.quality.*", "DELETE", Permission.MARKET_WRITE),
    (r"/api/.*data.quality.*", "GET", Permission.MARKET_READ),

    # ── Threat Detection ──────────────────────────────────────────────
    (r"/api/.*threat.*", "GET", Permission.AUDIT_READ),
    (r"/api/.*threat.*", "POST", Permission.AUDIT_EXPORT),

    # ── Security Audit ────────────────────────────────────────────────
    (r"/api/.*security.audit.*", "GET", Permission.AUDIT_READ),
    (r"/api/.*security.audit.*", "POST", Permission.AUDIT_EXPORT),

    # ── Immutable Audit ───────────────────────────────────────────────
    (r"/api/.*immutable.audit.*", "GET", Permission.AUDIT_READ),
    (r"/api/.*immutable.audit.*", "POST", Permission.AUDIT_EXPORT),

    # ── Quantum / PQC ─────────────────────────────────────────────────
    (r"/api/.*quantum.*", "GET", Permission.SYSTEM_CONFIG),
    (r"/api/.*quantum.*", "POST", Permission.SYSTEM_CONFIG),
    (r"/api/.*pqc.*", "GET", Permission.SYSTEM_CONFIG),
    (r"/api/.*pqc.*", "POST", Permission.SYSTEM_CONFIG),

    # ── SOC2 ──────────────────────────────────────────────────────────
    (r"/api/.*soc2.*", "GET", Permission.AUDIT_READ),
    (r"/api/.*soc2.*", "POST", Permission.AUDIT_EXPORT),

    # ── WebSocket ─────────────────────────────────────────────────────
    (r"/ws/.*", "GET", Permission.PORTFOLIO_READ),
]

# Compile regex patterns once for performance
COMPILED_ROUTES: list[tuple[re.Pattern, str, str]] = []
for pattern, method, perm in ROUTE_PERMISSIONS:
    if isinstance(pattern, tuple):
        # Handle malformed tuple entry
        continue
    COMPILED_ROUTES.append((re.compile(pattern, re.IGNORECASE), method.upper(), perm))


# ── Paths that bypass RBAC (always allowed) ──────────────────────────
RBAC_BYPASS_PATHS: set[str] = {
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/refresh",
    "/api/auth/logout",
    "/api/health",
    "/docs",
    "/redoc",
    "/openapi.json",
}

# Prefix patterns that bypass RBAC
RBAC_BYPASS_PREFIXES: list[str] = [
    "/api/auth/",
    "/api/exports/",  # Read-only data generation
    "/api/ai-advisor/",  # Read-only intelligence
    "/api/simulation/",  # Read-only simulation
    "/api/optimizer/",  # Read-only optimization
    "/api/realtime/",  # Market data snapshot
    "/api/advanced-analysis/",  # Read-only analysis
    "/api/settings/",  # System config (read-only)
    "/api/ui/",  # Browser UI bridge (read/create for Jinja2 pages)
    "/api/external-factors/",  # Read-only external factors analysis
    "/api/first-run/",  # Onboarding flow
    "/api/savings/",  # Read-only savings dashboard
    "/api/market-pulse/",
    "/api/market/",  # Market data endpoints
    "/api/briefing/",  # Read-only daily briefing
    "/api/assets/",  # Read-only asset tracker
    "/api/hybrid/",  # Hybrid workflow engine
    "/api/optimize-debt/",  # Quantum debt optimizer
    "/api/v1/",  # Enterprise sovereign debt engine
    "/api/circuit-designer/",  # Visual circuit designer
    "/api/algorithm-marketplace/",  # Algorithm marketplace
    "/api/error-correction/",  # Error correction layer
    "/api/quantum-simulator/",  # Quantum simulator
    "/api/trading/",  # Trading intelligence (stocks, ETFs, sectors, technicals)
    "/api/market-intelligence/",  # Market launch intelligence
    "/api/fintech-tracker/",  # FinTech competitive intelligence
    "/api/crypto/",  # Crypto market data
    "/api/recommendations/",  # Personalized recommendations
    "/api/health",  # Health checks
    "/api/alerts",  # Price alerts
    "/api/backtest",  # Backtesting engine
    "/api/earnings",  # Earnings calendar
    "/api/screener",  # Stock screener & watchlists
    "/api/rebalancing/",  # Portfolio rebalancing engine
    "/api/streaming/",  # Live price streaming
    "/api/portfolio-agg/",  # Portfolio aggregator
    "/api/performance/",  # Advanced analytics
    "/api/risk-parity/",  # Advanced analytics
    "/api/tax-harvest/",  # Advanced analytics
]


def should_bypass_rbac(path: str) -> bool:
    """Check if this path should skip RBAC checks."""
    if path in RBAC_BYPASS_PATHS:
        return True
    for prefix in RBAC_BYPASS_PREFIXES:
        if path.startswith(prefix):
            return True
    # Page routes (HTML) don't go through API RBAC
    if not path.startswith("/api/"):
        return True
    return False


def match_route_permission(path: str, method: str) -> Optional[str]:
    """Find the required permission for a given path + method."""
    method_upper = method.upper()
    for compiled_pattern, route_method, permission in COMPILED_ROUTES:
        if route_method != "*" and route_method != method_upper:
            continue
        if compiled_pattern.search(path):
            return permission
    return None


# ── Middleware ────────────────────────────────────────────────────────

class RBACMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that enforces RBAC on all /api/ requests.

    Flow:
    1. Skip auth pages, health check, docs
    2. Extract JWT from Authorization header or cookie
    3. Decode token, get user role
    4. Map DB role to RBAC role
    5. Match route to required permission
    6. Check if role has that permission
    7. Log the decision for audit trail
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        # Skip RBAC for bypass paths
        if should_bypass_rbac(path):
            return await call_next(request)

        # Extract token
        token = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        if not token:
            token = request.cookies.get("access_token", "")

        if not token:
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required"},
            )

        # Decode JWT
        payload = decode_token(token)
        if not payload:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token"},
            )

        # Get user role from token
        db_role = payload.get("role", "viewer")
        rbac_role = map_db_role(db_role)

        # Match route to required permission
        required_permission = match_route_permission(path, method)

        if required_permission is None:
            # No specific permission mapped — allow authenticated users
            # This is the default: if we haven't mapped a route, it's read-only
            # and any authenticated user can access it.
            # Log for audit so we can tighten this over time.
            return await call_next(request)

        # Check permission
        if not has_permission(rbac_role, required_permission):
            # Log the denied access
            try:
                # We don't have db access here easily, but we can log to a file or
                # pass the info through request state
                request.state.rbac_denied = {
                    "role": rbac_role,
                    "permission": required_permission,
                    "path": path,
                    "method": method,
                }
            except Exception:
                pass

            return JSONResponse(
                status_code=403,
                content={
                    "detail": f"Insufficient permissions",
                    "required": required_permission,
                    "your_role": rbac_role,
                    "endpoint": f"{method} {path}",
                },
            )

        # Permission granted — attach user info to request state for downstream use
        request.state.rbac_user_id = payload.get("sub")
        request.state.rbac_role = rbac_role
        request.state.rbac_permission = required_permission

        return await call_next(request)


# ── FastAPI Dependency (alternative to middleware) ────────────────────
# Use this when you want per-route RBAC instead of blanket middleware.

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User


def require_rbac(permission: str):
    """
    FastAPI dependency factory for per-route permission checks.

    Usage:
        @router.post("/optimize")
        def run_optimization(
            user: User = Depends(get_current_user),
            _=Depends(require_rbac(Permission.OPTIMIZATION_EXECUTE)),
        ):
            ...
    """
    def checker(
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        rbac_role = map_db_role(str(user.role))
        if not has_permission(rbac_role, permission):
            log_rbac_event(
                db=db,
                user=user,
                action="denied",
                resource=permission,
                granted=False,
                reason=f"Role {rbac_role} lacks {permission}",
            )
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required: {permission}, your role: {rbac_role}",
            )
        log_rbac_event(
            db=db,
            user=user,
            action="granted",
            resource=permission,
            granted=True,
        )
        return user
    return checker
