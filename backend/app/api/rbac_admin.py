"""
RBAC Administration API
========================
Endpoints for managing roles, permissions, and user role assignments.
Only system_admin and minister roles can access these.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import get_current_user
from app.security.rbac import (
    ROLE_PERMISSIONS,
    ROLE_DISPLAY_NAMES,
    ROLE_DESCRIPTIONS,
    ROLE_HIERARCHY,
    get_user_permissions,
    has_permission,
    log_rbac_event,
    require_role,
    require_permissions,
)
from app.security.rbac_middleware import map_db_role

router = APIRouter(prefix="/api/rbac", tags=["rbac"])


# ── Response Models ───────────────────────────────────────────────────

class RoleInfo(BaseModel):
    name: str
    display_name: str
    description: str
    level: int
    permissions: list[str]
    permission_count: int


class PermissionCheck(BaseModel):
    role: str
    permission: str
    has_permission: bool


class UserRoleAssign(BaseModel):
    user_id: str
    new_role: str


class RBACAuditEntry(BaseModel):
    timestamp: str
    user_id: str
    user_email: str
    role: str
    action: str
    resource: str
    granted: bool
    reason: str = ""


class RBACStatus(BaseModel):
    total_roles: int
    total_permissions: int
    current_user_role: str
    current_user_permissions: list[str]
    role_hierarchy: list[str]


# ── Endpoints ────────────────────────────────────────────────────────

@router.get("/roles", response_model=list[RoleInfo])
def list_roles(user: User = Depends(require_role("system_admin", "minister"))):
    """List all roles with their permissions and hierarchy level."""
    roles = []
    for i, role_name in enumerate(ROLE_HIERARCHY):
        perms = ROLE_PERMISSIONS.get(role_name, set())
        roles.append(RoleInfo(
            name=role_name,
            display_name=ROLE_DISPLAY_NAMES.get(role_name, role_name),
            description=ROLE_DESCRIPTIONS.get(role_name, ""),
            level=i,
            permissions=sorted(perms),
            permission_count=len(perms),
        ))
    return roles


@router.get("/permissions")
def list_all_permissions(user: User = Depends(require_role("system_admin", "minister"))):
    """List all defined permissions and which roles have them."""
    all_perms = set()
    for perms in ROLE_PERMISSIONS.values():
        all_perms.update(perms)

    perm_matrix = {}
    for perm in sorted(all_perms):
        perm_matrix[perm] = {
            "roles": sorted([
                role for role, perms in ROLE_PERMISSIONS.items()
                if perm in perms
            ]),
            "role_count": sum(1 for perms in ROLE_PERMISSIONS.values() if perm in perms),
        }

    return {
        "total_permissions": len(all_perms),
        "permissions": perm_matrix,
    }


@router.get("/check")
def check_permission(
    role: str,
    permission: str,
    user: User = Depends(require_role("system_admin", "minister")),
):
    """Check if a role has a specific permission."""
    return PermissionCheck(
        role=role,
        permission=permission,
        has_permission=has_permission(role, permission),
    )


@router.get("/hierarchy")
def get_hierarchy(user: User = Depends(require_role("system_admin", "minister"))):
    """Get the role hierarchy with levels."""
    return {
        "hierarchy": [
            {
                "role": role,
                "level": i,
                "display_name": ROLE_DISPLAY_NAMES.get(role, role),
                "permission_count": len(ROLE_PERMISSIONS.get(role, set())),
            }
            for i, role in enumerate(ROLE_HIERARCHY)
        ]
    }


@router.get("/users")
def list_users_with_roles(
    user: User = Depends(require_role("system_admin", "minister")),
    db: Session = Depends(get_db),
):
    """List all users with their current roles and permission counts."""
    users = db.query(User).filter(User.is_active.is_(True)).all()
    result = []
    for u in users:
        rbac_role = map_db_role(str(u.role))
        perms = get_user_permissions(rbac_role)
        result.append({
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "db_role": str(u.role),
            "rbac_role": rbac_role,
            "permission_count": len(perms),
            "permissions": sorted(perms),
        })
    return result


@router.put("/users/role")
def assign_user_role(
    data: UserRoleAssign,
    user: User = Depends(require_role("system_admin")),
    db: Session = Depends(get_db),
):
    """
    Assign a new RBAC role to a user.
    Only system_admin can change roles.
    """
    # Validate the target role exists in RBAC
    valid_rbac_roles = set(ROLE_PERMISSIONS.keys())
    # Map from RBAC role back to DB role
    rbac_to_db = {
        "system_admin": "admin",
        "minister": "admin",
        "treasury_officer": "analyst",
        "analyst": "analyst",
        "auditor": "viewer",
        "public_view": "viewer",
    }

    if data.new_role not in valid_rbac_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role: {data.new_role}. Valid roles: {sorted(valid_rbac_roles)}",
        )

    target = db.query(User).filter(User.id == data.user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    old_role = str(target.role)
    new_db_role = rbac_to_db.get(data.new_role, "viewer")
    target.role = new_db_role
    db.commit()

    log_rbac_event(
        db=db,
        user=user,
        action="role_changed",
        resource="user",
        resource_id=target.id,
        metadata={
            "old_role": old_role,
            "new_db_role": new_db_role,
            "rbac_role": data.new_role,
            "changed_by": user.id,
        },
    )

    return {
        "user_id": target.id,
        "old_role": old_role,
        "new_db_role": new_db_role,
        "rbac_role": data.new_role,
        "permissions": sorted(get_user_permissions(data.new_role)),
    }


@router.get("/status")
def rbac_status(user: User = Depends(get_current_user)):
    """Get current user's RBAC status."""
    rbac_role = map_db_role(str(user.role))
    perms = get_user_permissions(rbac_role)

    return RBACStatus(
        total_roles=len(ROLE_HIERARCHY),
        total_permissions=sum(len(p) for p in ROLE_PERMISSIONS.values()),
        current_user_role=rbac_role,
        current_user_permissions=sorted(perms),
        role_hierarchy=ROLE_HIERARCHY,
    )


@router.get("/audit")
def rbac_audit_log(
    user: User = Depends(require_role("system_admin", "auditor")),
    db: Session = Depends(get_db),
    limit: int = 50,
):
    """View RBAC access audit trail."""
    from app.models import AuditEvent
    events = (
        db.query(AuditEvent)
        .filter(AuditEvent.action.like("rbac.%"))
        .order_by(AuditEvent.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": e.id,
            "timestamp": e.created_at.isoformat() if e.created_at else None,
            "user_id": e.actor_id,
            "user_email": e.actor_email,
            "action": e.action,
            "resource": e.resource_type,
            "resource_id": e.resource_id,
            "metadata": e.metadata_json,
        }
        for e in events
    ]
