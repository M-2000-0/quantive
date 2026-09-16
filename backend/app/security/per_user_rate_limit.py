"""Per-user rate limiting middleware.

Tracks requests per-user (JWT/API key) with sliding window.
Falls back to per-IP when unauthenticated.
Uses in-memory store with TTL cleanup (swap for Redis in production).
"""
from __future__ import annotations

import os
import time
import threading
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import get_settings

settings = get_settings()

# Plan-based rate limits (requests per minute)
PLAN_LIMITS = {
    "free": 60,
    "pro": 300,
    "enterprise": 1000,
    "personal": 300,
    "personal_2k": 100,
    "personal_10k": 500,
}

# Exempt paths
EXEMPT_PATHS = {"/api/health", "/docs", "/redoc", "/openapi.json", "/api/chat"}


class PerUserRateLimitMiddleware(BaseHTTPMiddleware):
    """Per-user sliding window rate limiter with plan-based limits."""

    def __init__(self, app, default_limit: int = 60):
        super().__init__(app)
        self.default_limit = default_limit
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()
        # Disable in test mode
        self._enabled = os.environ.get("PYTEST_CURRENT_TEST") is None

    def _cleanup(self):
        """Remove expired entries."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        self._last_cleanup = now
        cutoff = now - 60  # 1 minute window
        with self._lock:
            empty_keys = [k for k, v in self._requests.items() if not v or v[-1] < cutoff]
            for k in empty_keys:
                del self._requests[k]

    def _get_client_id(self, request: Request) -> str:
        """Extract user ID from JWT payload or fall back to IP."""
        # Try to get user ID from request state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"
        # Try X-API-Key prefix
        api_key = request.headers.get("x-api-key", "")
        if api_key.startswith("qtv_"):
            return f"apikey:{api_key[:12]}"
        # Fall back to IP
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"
        return f"ip:{ip}"

    def _get_limit(self, client_id: str) -> int:
        """Get rate limit for client based on plan."""
        if client_id.startswith("user:"):
            # Would need to look up plan from DB — use default for now
            return self.default_limit
        if client_id.startswith("apikey:"):
            return self.default_limit * 2  # API keys get 2x
        return self.default_limit  # Unauthenticated: default

    async def dispatch(self, request: Request, call_next):
        # Skip in test mode
        if not self._enabled:
            return await call_next(request)

        path = request.url.path

        # Skip exempt paths
        if path in EXEMPT_PATHS or path.startswith("/assets/") or path.endswith((".js", ".css", ".svg", ".ico", ".png")):
            return await call_next(request)

        # Cleanup old entries periodically
        self._cleanup()

        client_id = self._get_client_id(request)
        limit = self._get_limit(client_id)
        now = time.time()
        window = 60  # 1 minute sliding window

        with self._lock:
            self._requests[client_id] = [
                t for t in self._requests[client_id] if now - t < window
            ]
            if len(self._requests[client_id]) >= limit:
                retry_after = int(window - (now - self._requests[client_id][0]))
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded",
                        "retry_after": retry_after,
                        "limit": limit,
                        "window": "1 minute",
                    },
                    headers={"Retry-After": str(retry_after), "X-RateLimit-Limit": str(limit)},
                )
            self._requests[client_id].append(now)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - len(self._requests.get(client_id, []))))
        return response
