import logging
import threading
import time
import uuid
from collections import defaultdict

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("quantive.security")


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; img-src 'self' data:; font-src 'self' data: https://fonts.gstatic.com"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP rate limiter with endpoint-specific overrides.

    Endpoint-specific limits (stricter for auth/expensive operations):
      - /login, /register, /forgot-password: 10 req/min (brute-force protection)
      - /optimize: 5 req/min (computationally expensive)
      - /api/health: unlimited (monitoring)
      - Default: 60 req/min
    """

    # Per-endpoint limits: (max_requests, window_seconds)
    ENDPOINT_LIMITS: dict[str, tuple[int, int]] = {
        "/login": (10, 60),
        "/register": (10, 60),
        "/api/auth/login": (10, 60),
        "/api/auth/register": (10, 60),
        "/api/auth/forgot-password": (5, 60),
        "/api/v1/optimize": (5, 60),
        "/api/v1/optimize/background": (5, 60),
    }

    # Paths that bypass rate limiting entirely
    EXEMPT_PATHS: set[str] = {
        "/docs", "/redoc", "/openapi.json", "/api/health", "/status",
    }

    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.default_max = max_requests
        self.default_window = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _get_limit(self, path: str) -> tuple[int, int]:
        for pattern, limit in self.ENDPOINT_LIMITS.items():
            if path.startswith(pattern) or path == pattern:
                return limit
        return (self.default_max, self.default_window)

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        max_req, window = self._get_limit(request.url.path)
        now = time.time()

        with self._lock:
            # Cleanup old entries for this IP (sliding window)
            bucket_key = f"{client_ip}:{request.url.path}"
            self._requests[bucket_key] = [
                t for t in self._requests[bucket_key] if now - t < window
            ]
            if len(self._requests[bucket_key]) >= max_req:
                retry_after = int(window - (now - self._requests[bucket_key][0]))
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded", "retry_after": retry_after, "limit": max_req},
                    headers={"Retry-After": str(retry_after), "X-RateLimit-Limit": str(max_req)},
                )
            self._requests[bucket_key].append(now)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(max_req)
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        request_id = getattr(request.state, "request_id", "unknown")
        response = await call_next(request)
        duration = time.time() - start
        logger.info(
            "api_request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round(duration * 1000, 2),
                "client_ip": request.client.host if request.client else "unknown",
            },
        )
        return response


class GlobalExceptionHandler(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception:
            logger.exception("unhandled_exception", extra={"path": request.url.path})
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error",
                    "code": "internal_error",
                    "request_id": getattr(request.state, "request_id", "unknown"),
                },
            )
