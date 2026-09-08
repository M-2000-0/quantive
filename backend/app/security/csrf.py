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

from app.config import get_settings

settings = get_settings()


# CSRF token lifetime (in seconds)
CSRF_TOKEN_LIFETIME = 3600  # 1 hour

# Paths that require CSRF protection (state-changing methods)
CSRF_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Paths exempt from CSRF (public endpoints, webhooks, health)
CSRF_EXEMPT_PATHS = {"/api/health", "/api/auth/login", "/api/auth/register", "/webhooks", "/docs", "/redoc", "/openapi.json", "/login", "/register", "/forgot-password", "/reset-password"}


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


class CSRFMiddleware:
    """CSRF protection middleware using double-submit cookie pattern.

    Raw ASGI middleware (not BaseHTTPMiddleware) so it reliably runs
    in the Starlette/FastAPI middleware stack.
    """
    def __init__(self, app, secret: str = "csrfsecret-change-in-production"):
        self.app = app
        self.secret = secret

    async def __call__(self, scope, receive, send):
        import sys
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        from starlette.requests import Request
        from starlette.responses import JSONResponse, Response
        from starlette.types import Message

        request = Request(scope, receive)
        path = request.url.path
        exempt = any(path.startswith(p) for p in CSRF_EXEMPT_PATHS)

        print(f"CSRF ASGI: {scope['method']} {path} exempt={exempt}", file=sys.stderr, flush=True)

        if request.method == "GET":
            async def get_send(message: Message) -> None:
                if message["type"] == "http.response.start":
                    if "csrf_token" not in request.cookies:
                        token = generate_csrf_token(self.secret)
                        message.setdefault("headers", []).append(
                            (b"set-cookie",
                             f"csrf_token={token}; Path=/; SameSite=strict; Max-Age={CSRF_TOKEN_LIFETIME}; Secure={settings.SECURE_COOKIES}".encode("latin-1"))
                        )
                await send(message)
            await self.app(scope, receive, get_send)
            return

        if exempt:
            return await self.app(scope, receive, send)

        # Validate CSRF for state-changing methods
        async def body_receive() -> Message:
            return await receive()

        header_token = request.headers.get("X-CSRF-Token")
        cookie_token = request.cookies.get("csrf_token")

        if path.startswith("/api/"):
            if not header_token:
                await send({
                    "type": "http.response.start",
                    "status": 403,
                    "headers": [(b"content-type", b"application/json")],
                })
                await send({
                    "type": "http.response.body",
                    "body": b'{"detail":"CSRF token missing. Include X-CSRF-Token header."}',
                })
                return
            if not validate_csrf_token(header_token, self.secret):
                await send({
                    "type": "http.response.start",
                    "status": 403,
                    "headers": [(b"content-type", b"application/json")],
                })
                await send({
                    "type": "http.response.body",
                    "body": b'{"detail":"CSRF token expired or invalid."}',
                })
                return
        else:
            if not header_token or not cookie_token:
                await send({
                    "type": "http.response.start",
                    "status": 403,
                    "headers": [(b"content-type", b"application/json")],
                })
                await send({
                    "type": "http.response.body",
                    "body": b'{"detail":"CSRF token missing. Include X-CSRF-Token header and csrf_token cookie."}',
                })
                return
            if header_token != cookie_token:
                await send({
                    "type": "http.response.start",
                    "status": 403,
                    "headers": [(b"content-type", b"application/json")],
                })
                await send({
                    "type": "http.response.body",
                    "body": b'{"detail":"CSRF token mismatch."}',
                })
                return
            if not validate_csrf_token(header_token, self.secret):
                await send({
                    "type": "http.response.start",
                    "status": 403,
                    "headers": [(b"content-type", b"application/json")],
                })
                await send({
                    "type": "http.response.body",
                    "body": b'{"detail":"CSRF token expired or invalid."}',
                })
                return

        await self.app(scope, receive, send)
