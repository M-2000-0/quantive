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


class BearerPromotionMiddleware(BaseHTTPMiddleware):
    """Promote the httpOnly access-token cookie to an Authorization header.

    Problem: pages authenticate with an httpOnly session cookie (set by the
    HTML login), which JavaScript cannot read — so same-origin fetch() calls
    to /api/ endpoints cannot attach a Bearer token themselves, while API
    auth dependencies (app.security.get_current_user) read ONLY the
    Authorization header. Result: every logged-in page's fetch() would 401.

    Fix: for API paths carrying an access_token cookie and no explicit
    Authorization header, promote cookie → Bearer header in-place. Adds no
    new trust — the same JWT flows through the exact same signature/revocation
    verification as a header token.
    """

    def __init__(self, app, api_prefixes: tuple[str, ...] = ("/api/",)):
        super().__init__(app)
        self.api_prefixes = api_prefixes

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith(self.api_prefixes):
            token = request.cookies.get("access_token", "")
            if token and not request.headers.get("authorization"):
                headers = [
                    (k, v) for (k, v) in request.scope["headers"]
                    if k.lower() != b"authorization"
                ]
                headers.append((b"authorization", b"Bearer " + token.encode("utf-8")))
                request.scope["headers"] = headers
        return await call_next(request)


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


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject request bodies larger than a configurable threshold (default 10MB).
    
    Upload endpoints (/import, /upload) are exempt — they handle their own limits.
    """

    # Paths that handle their own upload limits
    UPLOAD_PATHS = {"/api/portfolios/upload", "/api/v1/portfolios/upload"}

    def __init__(self, app, max_body_bytes: int = 10 * 1024 * 1024):
        super().__init__(app)
        self.max_body_bytes = max_body_bytes

    async def dispatch(self, request: Request, call_next):
        if request.method in ("GET", "HEAD", "DELETE", "OPTIONS"):
            return await call_next(request)
        if request.url.path in self.UPLOAD_PATHS:
            return await call_next(request)
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_body_bytes:
            return JSONResponse(
                status_code=413,
                content={"detail": f"Request body too large. Maximum size: {self.max_body_bytes // (1024 * 1024)}MB"},
            )
        return await call_next(request)
