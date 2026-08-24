import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Organization, User
from app.schemas import PasswordChange, TokenRefresh, TokenResponse, UserCreate, UserLogin, UserResponse, UserUpdate
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    log_audit_event,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

_failed_logins: dict[str, list[float]] = defaultdict(list)
_LOCKOUT_THRESHOLD = 5
_LOCKOUT_WINDOW_SECONDS = 900
_LOCKOUT_DURATION_SECONDS = 900


def _check_lockout(email: str):
    now = time.time()
    attempts = [t for t in _failed_logins[email] if now - t < _LOCKOUT_WINDOW_SECONDS]
    _failed_logins[email] = attempts
    if len(attempts) >= _LOCKOUT_THRESHOLD:
        remaining = int(_LOCKOUT_DURATION_SECONDS - (now - attempts[0]))
        if remaining > 0:
            raise HTTPException(
                status_code=429,
                detail=f"Account temporarily locked. Try again in {remaining} seconds.",
                headers={"Retry-After": str(remaining)},
            )
        _failed_logins[email] = []


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(data: UserCreate, request: Request, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == data.email.lower().strip()).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    org = Organization(name=data.org_name or f"{data.name}'s Organization")
    db.add(org)
    db.flush()

    user = User(
        email=data.email.lower().strip(),
        password_hash=hash_password(data.password),
        name=data.name.strip(),
        role="admin",
        org_id=org.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    ip = request.client.host if request.client else None
    log_audit_event(db, user, "user.registered", "user", user.id, ip_address=ip)

    access = create_access_token({"sub": user.id, "org_id": user.org_id, "role": user.role})
    refresh = create_refresh_token({"sub": user.id})

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, request: Request, db: Session = Depends(get_db)):
    email = data.email.lower().strip()
    _check_lockout(email)

    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(data.password, user.password_hash):
        _failed_logins[email].append(time.time())
        ip = request.client.host if request.client else None
        log_audit_event(db, None, "user.login_failed", "user", metadata={"email": email}, ip_address=ip)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    _failed_logins.pop(email, None)

    ip = request.client.host if request.client else None
    log_audit_event(db, user, "user.login", "user", user.id, ip_address=ip)

    access = create_access_token({"sub": user.id, "org_id": user.org_id, "role": user.role})
    refresh = create_refresh_token({"sub": user.id})

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(data: TokenRefresh, db: Session = Depends(get_db)):
    payload = decode_token(data.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user = db.query(User).filter(User.id == payload.get("sub"), User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    access = create_access_token({"sub": user.id, "org_id": user.org_id, "role": user.role})
    refresh = create_refresh_token({"sub": user.id})

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user=UserResponse.model_validate(user),
    )


@router.post("/logout", status_code=204)
def logout(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Revoke the access token
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")
    if token:
        from app.security import revoke_token
        revoke_token(token, db)
    log_audit_event(db, user, "user.logout", "user", user.id)


@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    return UserResponse.model_validate(user)


@router.put("/me", response_model=UserResponse)
def update_me(data: UserUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if data.name is not None:
        user.name = data.name.strip()
    if data.email is not None:
        new_email = data.email.lower().strip()
        existing = db.query(User).filter(User.email == new_email, User.id != user.id).first()
        if existing:
            raise HTTPException(status_code=409, detail="Email already in use")
        user.email = new_email

    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.post("/password/change", status_code=204)
def change_password(data: PasswordChange, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    user.password_hash = hash_password(data.new_password)
    db.commit()

    log_audit_event(db, user, "user.password_changed", "user", user.id)
