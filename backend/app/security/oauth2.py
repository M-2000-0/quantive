"""OAuth2 authentication with JWT tokens for enterprise government deals."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User  # Assume User model exists with username, password_hash, org_id, role, is_active

# === JWT Configuration ===
JWT_SECRET_KEY = "change-this-in-production"  # Use secrets manager in production
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30000  # 500 hours ≈ 20 days
REFRESH_TOKEN_EXPIRE_DAYS = 30

# OAuth2 password bearer - for login/form auth
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(
    subject: str | Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token."""
    
    if isinstance(subject, str):
        subject = {"sub": subject}
    
    now = datetime.utcnow()
    
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = dict(subject)
    to_encode.update({"exp": expire, "iat": now, "type": "access"})
    
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    subject: str | Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT refresh token."""
    
    if isinstance(subject, str):
        subject = {"sub": subject}
    
    now = datetime.utcnow()
    
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = dict(subject)
    to_encode.update({"exp": expire, "iat": now, "type": "refresh"})
    
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_token(
    token: str,
    key: str = JWT_SECRET_KEY,
    algorithm: str = JWT_ALGORITHM,
) -> Dict[str, Any]:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(token, key, algorithms=[algorithm])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
        )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[dict]:
    """Get current authenticated user from JWT token."""
    
    if not token:
        return None
    
    try:
        payload = decode_token(token)
        token_type: str = payload.get("type")
        
        if token_type != "access":
            return None
        
        subject: str = payload.get("sub")
        if subject is None:
            return None
        
        # Look up user in database
        result = await db.execute(select(User).where(User.username == subject))
        user = result.scalar_one_or_none()
        
        if user is None or not user.is_active:
            return None
        
        return {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "org_id": str(user.org_id) if user.org_id else None,
            "is_superuser": user.is_superuser,
        }
        
    except HTTPException:
        return None


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[dict]:
    """Get current user - optional (works without token for public endpoints)."""
    if not token:
        return None
    return await get_current_user(token=token, db=db)


# Role required dependencies
def get_current_user_with_role(
    required_role: str,
) -> callable:
    """Dependency factory - requires specific user role."""
    
    async def dependency(
        current_user: dict = Depends(get_current_user),
    ) -> dict:
        if not current_user or current_user.get("role") != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User requires role: {required_role}",
            )
        return current_user
    
    return dependency


# Role constants
class UserRole:
    ADMIN = "admin"
    ANALYST = "analyst" 
    VIEWER = "viewer"
    SUPERUSER = "superuser"


# Auth router
# WIP (enterprise OAuth2 flow): kept as a dormant string so the module imports
# cleanly. To enable, move this block into a real module and wire dependencies.
DISABLED_AUTH_ROUTER = """
from fastapi import APIRouter, Request

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=dict)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> dict:
    '''Login with username/password - returns JWT tokens.'''
    
    from sqlalchemy import select
    
    # Query user by username
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password (using passlib context)
    if not pwd_context.verify(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    
    # Create access token
    access_token = create_access_token(
        subject=user.username,
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    
    # Create refresh token
    refresh_token = create_refresh_token(
        subject=user.username,
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "org_id": str(user.org_id) if user.org_id else None,
        },
    }

@router.post("/refresh", response_model=dict)
async def refresh(
    refresh_token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> dict:
    '''Refresh access token using refresh token.'''
    try:
        payload = decode_token(refresh_token)
        
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid refresh token type",
            )
        
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid refresh token payload",
            )
        
        # Check if user still exists and is active
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User no longer active",
            )
        
        new_access_token = create_access_token(
            subject=user.username,
        )
        new_refresh_token = create_refresh_token(
            subject=user.username,
        )
        
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not decode refresh token",
        )

@router.post("/logout")
async def logout(
    current_user: dict = Depends(get_current_user),
) -> dict:
    '''Logout user (invalidate tokens).'''
    # In production, add token to revocation list
    # For JWT with expiry, tokens naturally expire
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=dict)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
) -> dict:
    '''Get current authenticated user information.'''
    return {
        "user": current_user,
    }

@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register_user(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form.default_factory=lambda: UserRole.ANALYST,
    org_id: str = Form(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    '''Register new user (admin-only typically).'''
    
    from passlib.context import CryptContext
    from sqlalchemy.exc import IntegrityError
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    # Hash password
    password_hash = pwd_context.hash(password)
    
    # Create new user
    new_user = User(
        username=username,
        email=email,
        password_hash=password_hash,
        role=role,
        org_id=org_id,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    
    db.add(new_user)
    try:
        await db.commit()
        await db.refresh(new_user)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered",
        )
    
    # Create initial access token
    access_token = create_access_token(
        subject=new_user.username,
    )
    
    return {
        "status": "user_created",
        "user": {
            "id": str(new_user.id),
            "username": new_user.username,
            "email": new_user.email,
            "role": new_user.role,
            "org_id": str(new_user.org_id),
        },
        "access_token": access_token,
        "token_type": "bearer",
    }
"""