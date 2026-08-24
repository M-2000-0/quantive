from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import AuditEvent, User, UserRole

settings = get_settings()
security_scheme = HTTPBearer()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


def get_token_jti(token: str) -> Optional[str]:
    """Extract jti from a JWT without validation (for blacklisting)."""
    try:
        payload = jwt.get_unverified_claims(token)
        return payload.get("jti")
    except Exception:
        return None


def is_token_revoked(jti: str, db: Session) -> bool:
    """Check if a token has been revoked (blacklisted)."""
    from app.models.password_reset import RevokedToken
    return db.query(RevokedToken).filter(RevokedToken.jti == jti).first() is not None


def revoke_token(token: str, db: Session) -> None:
    """Add a token to the revocation list."""
    from app.models.password_reset import RevokedToken
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM], options={"verify_exp": False})
        jti = payload.get("jti")
        user_id = payload.get("sub")
        exp = payload.get("exp")
        if jti and user_id:
            # Check if already revoked
            existing = db.query(RevokedToken).filter(RevokedToken.jti == jti).first()
            if not existing:
                revoked = RevokedToken(
                    jti=jti,
                    user_id=user_id,
                    expires_at=datetime.fromtimestamp(exp, tz=timezone.utc) if exp else datetime.now(timezone.utc) + timedelta(days=7),
                )
                db.add(revoked)
                db.commit()
    except JWTError:
        pass


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    # Check if token is revoked
    jti = payload.get("jti")
    if jti and is_token_revoked(jti, db):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


def require_role(*roles: UserRole):
    def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user
    return role_checker


def log_audit_event(
    db: Session,
    user: Optional[User],
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    org_id: Optional[str] = None,
    metadata: Optional[dict] = None,
    ip_address: Optional[str] = None,
):
    event = AuditEvent(
        actor_id=user.id if user else None,
        actor_email=user.email if user else None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        org_id=org_id or (user.org_id if user else None),
        metadata_json=metadata,
        ip_address=ip_address,
    )
    db.add(event)
    db.commit()
