"""Idempotency Key Middleware.

Ensures that retried POST requests don't create duplicate records.
Uses an in-memory store (swap for Redis in production).

Usage:
    Include the X-Idempotency-Key header on POST requests.
    The middleware caches the response for 24 hours.
    If the same key is seen again, the cached response is returned.
"""

import hashlib
import json
import time
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


# In-memory idempotency store (use Redis in production)
_idempotency_store: dict[str, dict] = {}
_MAX_STORE_SIZE = 10000
_STORE_TTL_SECONDS = 86400  # 24 hours


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Cache POST responses keyed by X-Idempotency-Key header."""

    async def dispatch(self, request: Request, call_next):
        # Only apply to POST requests with an idempotency key
        if request.method != "POST":
            return await call_next(request)

        idem_key = request.headers.get("X-Idempotency-Key")
        if not idem_key:
            return await call_next(request)

        # Build a cache key from method + path + body hash + idempotency key
        body = await request.body()
        body_hash = hashlib.sha256(body).hexdigest()[:16]
        cache_key = f"{idem_key}:{request.url.path}:{body_hash}"

        # Check if we have a cached response
        now = time.time()
        if cache_key in _idempotency_store:
            cached = _idempotency_store[cache_key]
            if now - cached["ts"] < _STORE_TTL_SECONDS:
                return JSONResponse(
                    status_code=cached["status"],
                    content=cached["body"],
                    headers={"X-Idempotent-Replayed": "true"},
                )
            else:
                del _idempotency_store[cache_key]

        # Execute the request
        response = await call_next(request)

        # Cache successful responses (2xx)
        if 200 <= response.status_code < 300:
            try:
                body_bytes = b""
                async for chunk in response.body_iterator:
                    if isinstance(chunk, str):
                        body_bytes += chunk.encode()
                    else:
                        body_bytes += chunk

                body_json = json.loads(body_bytes)
                # Evict old entries if store is too large
                if len(_idempotency_store) > _MAX_STORE_SIZE:
                    oldest_keys = sorted(_idempotency_store.keys(), key=lambda k: _idempotency_store[k]["ts"])[:1000]
                    for k in oldest_keys:
                        del _idempotency_store[k]

                _idempotency_store[cache_key] = {
                    "status": response.status_code,
                    "body": body_json,
                    "ts": now,
                }

                return JSONResponse(
                    status_code=response.status_code,
                    content=body_json,
                    headers={"X-Idempotent-Cached": "true"},
                )
            except Exception:
                pass  # Non-JSON response, don't cache

        return response



