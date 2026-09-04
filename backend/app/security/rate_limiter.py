"""In-Memory Rate Limiter — Per-IP Request Throttling.

Middleware that tracks request counts per IP address and blocks
excessive requests with HTTP 429 Too Many Requests.

Usage in main.py:
    from app.security.rate_limiter import RateLimiterMiddleware
    app.add_middleware(RateLimiterMiddleware, max_requests=100, window_seconds=60)
"""

import time
from collections import defaultdict
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Simple sliding-window rate limiter per IP address."""

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._last_cleanup = time.time()

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP, respecting X-Forwarded-For."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    def _cleanup_old_entries(self):
        """Periodically remove old entries to prevent memory leak."""
        now = time.time()
        if now - self._last_cleanup < self.window_seconds * 2:
            return
        self._last_cleanup = now
        cutoff = now - self.window_seconds
        stale_ips = [
            ip for ip, timestamps in self._requests.items()
            if not timestamps or timestamps[-1] < cutoff
        ]
        for ip in stale_ips:
            del self._requests[ip]

    async def dispatch(self, request: Request, call_next: Callable):
        # Skip rate limiting for health checks
        if request.url.path in ("/api/health", "/api/v1/status"):
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        now = time.time()
        cutoff = now - self.window_seconds

        # Cleanup periodically
        self._cleanup_old_entries()

        # Get and prune timestamps for this IP
        timestamps = self._requests[client_ip]
        self._requests[client_ip] = [
            t for t in timestamps if t > cutoff
        ]

        if len(self._requests[client_ip]) >= self.max_requests:
            retry_after = int(self._requests[client_ip][0] + self.window_seconds - now) + 1
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "max_requests": self.max_requests,
                    "window_seconds": self.window_seconds,
                    "retry_after_seconds": max(retry_after, 1),
                },
                headers={"Retry-After": str(max(retry_after, 1))},
            )

        self._requests[client_ip].append(now)
        return await call_next(request)
