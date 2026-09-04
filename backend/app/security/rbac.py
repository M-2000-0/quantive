"""
Role-Based Access Control (RBAC) for Government DMO
=====================================================
Government-grade RBAC with hierarchical roles matching
typical Debt Management Office organizational structures.

Roles (hierarchical, highest to lowest):
  1. system_admin  — Full access, user management, system config
  2. minister      — Read-all + approve proposals, no direct edits
  3. treasury_officer — Full CRUD on debt instruments, portfolios, optimizations
  4. analyst       — Read + create drafts, no execute/approve
  5. auditor       — Read-only + export, audit trail access
  6. public_view   — Read-only on public-facing dashboards only
"""

from functools import wraps
from typing import Callable

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.security import decode_token, get_current_user


# ── Permission Definitions ─────────────────────────────────────────────

class Permission:
    """Granular permissions."""
    # Portfolio
    PORTFOLIO_READ = "portfolio:read"
    PORTFOLIO_WRITE = "portfolio:write"
    PORTFOLIO_DELETE = "portfolio:delete"

    # Instruments
    INSTRUMENT_READ = "instrument:read"
    INSTRUMENT_WRITE = "instrument:write"
    INSTRUMENT_DELETE = "instrument:delete"

    # Optimizations
    OPTIMIZATION_READ = "optimization:read"
    OPTIMIZATION_CREATE = "optimization:create"
    OPTIMIZATION_EXECUTE = "optimization:execute"

    # Market Data
    MARKET_READ = "market:read"
    MARKET_WRITE = "market:write"

    # Risk
    RISK_READ = "risk:read"
    RISK_WRITE = "risk:write"

    # Simulation
    SIMULATION_READ = "simulation:read"
    SIMULATION_RUN = "simulation:run"

    # Compliance
    COMPLIANCE_READ = "compliance:read"
    COMPLIANCE_WRITE = "compliance:write"

    # Audit
    AUDIT_READ = "audit:read"
    AUDIT_EXPORT = "audit:export"

    # Approvals
    APPROVAL_READ = "approval:read"
    APPROVAL_APPROVE = "approval:approve"
    APPROVAL_REJECT = "approval:reject"

    # Reports
    REPORT_READ = "report:read"
    REPORT_CREATE = "report:create"
    REPORT_EXPORT = "report:export"

    # Settings
    SETTINGS_READ = "settings:read"
    SETTINGS_WRITE = "settings:write"

    # Users
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"

    # System
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_CONFIG = "system:config"


# ── Role → Permission Matrix ───────────────────────────────────────────

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "system_admin": {
        Permission.PORTFOLIO_READ, Permission.PORTFOLIO_WRITE, Permission.PORTFOLIO_DELETE,
        Permission.INSTRUMENT_READ, Permission.INSTRUMENT_WRITE, Permission.INSTRUMENT_DELETE,
        Permission.OPTIMIZATION_READ, Permission.OPTIMIZATION_CREATE, Permission.OPTIMIZATION_EXECUTE,
        Permission.MARKET_READ, Permission.MARKET_WRITE,
        Permission.RISK_READ, Permission.RISK_WRITE,
        Permission.SIMULATION_READ, Permission.SIMULATION_RUN,
        Permission.COMPLIANCE_READ, Permission.COMPLIANCE_WRITE,
        Permission.AUDIT_READ, Permission.AUDIT_EXPORT,
        Permission.APPROVAL_READ, Permission.APPROVAL_APPROVE, Permission.APPROVAL_REJECT,
        Permission.REPORT_READ, Permission.REPORT_CREATE, Permission.REPORT_EXPORT,
        Permission.SETTINGS_READ, Permission.SETTINGS_WRITE,
        Permission.USER_READ, Permission.USER_WRITE, Permission.USER_DELETE,
        Permission.SYSTEM_ADMIN, Permission.SYSTEM_CONFIG,
    },
    "minister": {
        Permission.PORTFOLIO_READ,
        Permission.INSTRUMENT_READ,
        Permission.OPTIMIZATION_READ,
        Permission.MARKET_READ,
        Permission.RISK_READ,
        Permission.SIMULATION_READ,
        Permission.COMPLIANCE_READ,
        Permission.AUDIT_READ, Permission.AUDIT_EXPORT,
        Permission.APPROVAL_READ, Permission.APPROVAL_APPROVE, Permission.APPROVAL_REJECT,
        Permission.REPORT_READ, Permission.REPORT_EXPORT,
        Permission.SETTINGS_READ,
        Permission.USER_READ,
    },
    "treasury_officer": {
        Permission.PORTFOLIO_READ, Permission.PORTFOLIO_WRITE,
        Permission.INSTRUMENT_READ, Permission.INSTRUMENT_WRITE,
        Permission.OPTIMIZATION_READ, Permission.OPTIMIZATION_CREATE, Permission.OPTIMIZATION_EXECUTE,
        Permission.MARKET_READ, Permission.MARKET_WRITE,
        Permission.RISK_READ, Permission.RISK_WRITE,
        Permission.SIMULATION_READ, Permission.SIMULATION_RUN,
        Permission.COMPLIANCE_READ, Permission.COMPLIANCE_WRITE,
        Permission.AUDIT_READ,
        Permission.APPROVAL_READ,
        Permission.REPORT_READ, Permission.REPORT_CREATE, Permission.REPORT_EXPORT,
        Permission.SETTINGS_READ,
    },
    "analyst": {
        Permission.PORTFOLIO_READ,
        Permission.INSTRUMENT_READ,
        Permission.OPTIMIZATION_READ, Permission.OPTIMIZATION_CREATE,  # Can create, not execute
        Permission.MARKET_READ,
        Permission.RISK_READ,
        Permission.SIMULATION_READ, Permission.SIMULATION_RUN,
        Permission.COMPLIANCE_READ,
        Permission.AUDIT_READ,
        Permission.REPORT_READ, Permission.REPORT_CREATE,
    },
    "auditor": {
        Permission.PORTFOLIO_READ,
        Permission.INSTRUMENT_READ,
        Permission.OPTIMIZATION_READ,
        Permission.MARKET_READ,
        Permission.RISK_READ,
        Permission.SIMULATION_READ,
        Permission.COMPLIANCE_READ,
        Permission.AUDIT_READ, Permission.AUDIT_EXPORT,
        Permission.REPORT_READ, Permission.REPORT_EXPORT,
        Permission.USER_READ,
    },
    "public_view": {
        Permission.PORTFOLIO_READ,
        Permission.INSTRUMENT_READ,
        Permission.MARKET_READ,
        Permission.RISK_READ,
        Permission.REPORT_READ,
    },
}


# ── Role Hierarchy ─────────────────────────────────────────────────────

ROLE_HIERARCHY: list[str] = [
    "system_admin",
    "minister",
    "treasury_officer",
    "analyst",
    "auditor",
    "public_view",
]


def role_level(role: str) -> int:
    """Return numeric level (higher = more power). -1 if unknown."""
    try:
        return ROLE_HIERARCHY.index(role)
    except ValueError:
        return -1


# ── Core RBAC Functions ────────────────────────────────────────────────

def get_user_permissions(role: str) -> set[str]:
    """Get all permissions for a role — no inheritance, each role is explicit."""
    return set(ROLE_PERMISSIONS.get(role, set()))


def has_permission(role: str, permission: str) -> bool:
    """Check if a role has a specific permission."""
    return permission in get_user_permissions(role)


def require_permission(role: str, permission: str):
    """Raise 403 if role lacks permission."""
    if not has_permission(role, permission):
        raise HTTPException(
            status_code=403,
            detail=f"Insufficient permissions. Required: {permission}, your role: {role}",
        )


# ── FastAPI Dependencies ───────────────────────────────────────────────

def require_role(*allowed_roles: str):
    """
    Dependency factory that checks the current user has one of the allowed roles.

    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_role("system_admin", "minister"))])
        def admin_view(): ...
    """
    def checker(request: Request, db: Session = Depends(get_db)):
        user = get_current_user_from_request(request, db)
        # Map DB role (UserRole.ADMIN) to RBAC role string (system_admin)
        from app.security.rbac_middleware import map_db_role
        rbac_role = map_db_role(user.role)
        if rbac_role not in allowed_roles:
            # Check hierarchy: higher roles can access lower role endpoints
            user_level = role_level(rbac_role)
            min_required = min(role_level(r) for r in allowed_roles if role_level(r) >= 0)
            if user_level < 0 or user_level > min_required:
                raise HTTPException(
                    status_code=403,
                    detail=f"This action requires one of: {', '.join(allowed_roles)}. Your role: {rbac_role}",
                )
        return user
    return checker


def require_permissions(*required_perms: str):
    """
    Dependency factory that checks the current user has ALL specified permissions.

    Usage:
        @router.post("/optimize", dependencies=[Depends(require_permissions(Permission.OPTIMIZATION_EXECUTE))])
        def run_optimization(): ...
    """
    def checker(request: Request, db: Session = Depends(get_db)):
        user = get_current_user_from_request(request, db)
        from app.security.rbac_middleware import map_db_role
        rbac_role = map_db_role(user.role)
        user_perms = get_user_permissions(rbac_role)
        missing = [p for p in required_perms if p not in user_perms]
        if missing:
            raise HTTPException(
                status_code=403,
                detail=f"Missing permissions: {', '.join(missing)}",
            )
        return user
    return checker


def get_current_user_from_request(request: Request, db: Session):
    """Extract user from request token with RBAC context."""
    from app.models import User

    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")

    if not token:
        # Try cookies
        token = request.cookies.get("access_token", "")

    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or deactivated")

    return user


# ── Audit Trail for RBAC Events ────────────────────────────────────────

def log_rbac_event(db: Session, user, action: str, resource: str, resource_id: str = None,
                   granted: bool = True, reason: str = ""):
    """Log an RBAC access decision for audit trail."""
    from app.audit.logger import AuditLogger
    try:
        AuditLogger.log_event(
            db=db,
            user=user,
            event_type=f"rbac.{action}",
            resource_type=resource,
            resource_id=resource_id,
            metadata={
                "granted": granted,
                "role": user.role if user else "anonymous",
                "reason": reason,
            },
        )
    except (ImportError, Exception):
        pass  # Don't fail the request if audit logging fails


# ── RBAC Enforcement Decorator ─────────────────────────────────────────

def rbac(permission: str, resource_type: str = ""):
    """
    Decorator for route handlers that enforces a single permission.

    Usage:
        @router.delete("/portfolios/{id}")
        @rbac(Permission.PORTFOLIO_DELETE, "portfolio")
        def delete_portfolio(id: str, user = Depends(get_current_user)): ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find the user in kwargs (injected by Depends)
            user = kwargs.get("user")
            if user and hasattr(user, "role"):
                require_permission(user.role, permission)
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# ── Utility: Get DMO Role Display Name ─────────────────────────────────

ROLE_DISPLAY_NAMES = {
    "system_admin": "System Administrator",
    "minister": "Minister / Senior Official",
    "treasury_officer": "Treasury Officer",
    "analyst": "Financial Analyst",
    "auditor": "Auditor",
    "public_view": "Public Viewer",
}

ROLE_DESCRIPTIONS = {
    "system_admin": "Full system access including user management and configuration",
    "minister": "Read-only oversight with authority to approve/reject proposals",
    "treasury_officer": "Full operational access to debt instruments, portfolios, and optimizations",
    "analyst": "Can create drafts and run simulations, cannot execute or approve",
    "auditor": "Read-only access with export capability for audit trail review",
    "public_view": "Read-only access to public-facing dashboards and reports",
}
