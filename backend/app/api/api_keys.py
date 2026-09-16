"""API Key management — create, list, revoke, rotate, authenticate.

API keys allow programmatic access to Quantive endpoints without browser sessions.
Keys are HMAC-SHA256 hashed at rest. Only the prefix + hash are stored.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.models.extended import ApiKey
from app.security import get_current_user

router = APIRouter(prefix="/api/keys", tags=["api-keys"])

KEY_PREFIX = "qtv_"
KEY_BYTES = 32  # 256-bit keys


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _generate_key() -> tuple[str, str, str]:
    """Returns (full_key, key_hash, key_prefix)."""
    raw = KEY_PREFIX + secrets.token_hex(KEY_BYTES)
    return raw, _hash_key(raw), raw[:12] + "..."


class CreateKeyBody(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    scopes: list[str] = Field(default_factory=lambda: ["read"])
    expires_in_days: int | None = Field(default=None, ge=1, le=365)


@router.post("")
def create_key(body: CreateKeyBody, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new API key. Returns the full key ONCE — store it securely."""
    full_key, key_hash, key_prefix = _generate_key()
    expires_at = datetime.now(timezone.utc) + timedelta(days=body.expires_in_days) if body.expires_in_days else None

    api_key = ApiKey(
        id=str(uuid.uuid4()),
        user_id=user.id,
        name=body.name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        scopes=body.scopes,
        expires_at=expires_at,
        is_active=True,
    )
    db.add(api_key)
    db.commit()

    return {
        "id": api_key.id,
        "name": api_key.name,
        "key": full_key,
        "key_prefix": key_prefix,
        "scopes": api_key.scopes,
        "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
        "created_at": api_key.created_at.isoformat(),
        "warning": "Store this key securely — it will not be shown again.",
    }


@router.get("")
def list_keys(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List all API keys for the current user."""
    keys = (
        db.query(ApiKey)
        .filter(ApiKey.user_id == user.id)
        .order_by(ApiKey.created_at.desc())
        .all()
    )
    return {
        "keys": [
            {
                "id": k.id,
                "name": k.name,
                "key_prefix": k.key_prefix,
                "scopes": k.scopes,
                "is_active": k.is_active,
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
                "expires_at": k.expires_at.isoformat() if k.expires_at else None,
                "created_at": k.created_at.isoformat(),
            }
            for k in keys
        ]
    }


class RotateKeyBody(BaseModel):
    key_id: str
    expires_in_days: int | None = Field(default=None, ge=1, le=365)


@router.post("/rotate")
def rotate_key(body: RotateKeyBody, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Rotate an API key — invalidates the old one, returns a new one."""
    old = db.query(ApiKey).filter(ApiKey.id == body.key_id, ApiKey.user_id == user.id).first()
    if not old:
        raise HTTPException(status_code=404, detail="Key not found")

    old.is_active = False
    full_key, key_hash, key_prefix = _generate_key()
    expires_at = datetime.now(timezone.utc) + timedelta(days=body.expires_in_days) if body.expires_in_days else None

    new_key = ApiKey(
        id=str(uuid.uuid4()),
        user_id=user.id,
        name=old.name + " (rotated)",
        key_hash=key_hash,
        key_prefix=key_prefix,
        scopes=old.scopes,
        expires_at=expires_at,
        is_active=True,
    )
    db.add(new_key)
    db.commit()

    return {
        "id": new_key.id,
        "name": new_key.name,
        "key": full_key,
        "key_prefix": key_prefix,
        "old_key_id": old.id,
        "warning": "Store this key securely — it will not be shown again.",
    }


@router.delete("/{key_id}")
def revoke_key(key_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Revoke (deactivate) an API key."""
    key = db.query(ApiKey).filter(ApiKey.id == key_id, ApiKey.user_id == user.id).first()
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    key.is_active = False
    db.commit()
    return {"revoked": True, "key_id": key_id}


def authenticate_by_api_key(x_api_key: str | None = Header(default=None), db: Session = Depends(get_db)) -> User | None:
    """Try to authenticate via X-API-Key header. Returns User or None."""
    if not x_api_key or not x_api_key.startswith(KEY_PREFIX):
        return None
    key_hash = _hash_key(x_api_key)
    api_key = db.query(ApiKey).filter(
        ApiKey.key_hash == key_hash,
        ApiKey.is_active.is_(True),
    ).first()
    if not api_key:
        return None
    if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
        return None
    # Update last_used_at
    api_key.last_used_at = datetime.now(timezone.utc)
    db.commit()
    user = db.query(User).filter(User.id == api_key.user_id, User.is_active.is_(True)).first()
    return user
