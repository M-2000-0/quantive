"""CSRF Protection Middleware.

Generates and validates CSRF tokens for state-changing operations.
Uses double-submit cookie pattern (no server-side session needed).
"""
import hashlib
import hmac
import os
import secrets
import time
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


# CSRF token lifetime (in seconds)
CSRF_TOKEN_LIFETIME = 3600  # 1 hour

# Paths that require CSRF protection (state-changing methods)
CSRF_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Paths exempt from CSRF (public endpoints, webhooks, health)
CSRF_EXEMPT_PATHS = {"/api/health", "/api/auth/login", "/api/auth/register", "/webhooks", "/api/", "/docs", "/redoc", "/openapi.json", "/login", "/register", "/forgot-password", "/reset-password"}


def generate_csrf_token(secret: str) -> str:
    """Generate a CSRF token with timestamp."""
    timestamp = str(int(time.time()))
    payload = f"{timestamp}:{secrets.token_hex(16)}"
    signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{signature}"


def validate_csrf_token(token: str, secret: str) -> bool:
    """Validate a CSRF token."""
    try:
        parts = token.split(":")
        if len(parts) != 3:
            return False
        
        timestamp_str, payload, signature = parts
        
        # Verify signature
        expected_sig = hmac.new(secret.encode(), f"{timestamp_str}:{payload}".encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return False
        
        # Check expiry
        token_time = int(timestamp_str)
        if time.time() - token_time > CSRF_TOKEN_LIFETIME:
            return False
        
        return True
    except (ValueError, TypeError):
        return False


class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware using double-submit cookie pattern."""
    
    def __init__(self, app, secret: str = "csrf-secret-change-in-production"):
        super().__init__(app)
        self.secret = secret
    
    async def dispatch(self, request: Request, call_next):
        # Skip CSRF for exempt paths
        path = request.url.path
        exempt = any(path.startswith(p) for p in CSRF_EXEMPT_PATHS)
        if exempt:
            return await call_next(request)
        # Skip CSRF for non-state-changing methods
        if request.method not in CSRF_METHODS:
            response = await call_next(request)
            # Set CSRF token cookie on GET requests
            if request.method == "GET" and "csrf_token" not in request.cookies:
                token = generate_csrf_token(self.secret)
                response.set_cookie(
                    key="csrf_token",
                    value=token,
                    httponly=False,  # JavaScript needs to read this
                    secure=True,
                    samesite="strict",
                    max_age=CSRF_TOKEN_LIFETIME,
                )
            return response
        
        # Validate CSRF for state-changing methods
        # Check header first (for AJAX requests)
        header_token = request.headers.get("X-CSRF-Token")
        # Check cookie second
        cookie_token = request.cookies.get("csrf_token")
        
        # Both must be present and match
        if not header_token or not cookie_token:
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token missing. Include X-CSRF-Token header and csrf_token cookie."},
            )
        
        if header_token != cookie_token:
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token mismatch."},
            )
        
        if not validate_csrf_token(header_token, self.secret):
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token expired or invalid."},
            )
        
        return await call_next(request)
