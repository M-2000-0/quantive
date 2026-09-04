"""
GZip Compression Middleware
============================
Compresses responses for faster page loads.
Handles HTML, CSS, JS, JSON, and SVG content types.
"""

import gzip
import io
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


# Content types worth compressing
COMPRESSIBLE_TYPES = {
    "text/html",
    "text/css",
    "text/javascript",
    "text/xml",
    "text/plain",
    "application/json",
    "application/javascript",
    "application/xml",
    "application/xhtml+xml",
    "image/svg+xml",
}

MIN_SIZE = 500  # Don't compress tiny responses


class CompressionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Check if client accepts gzip
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding:
            return response

        # Check content type
        content_type = response.headers.get("content-type", "")
        is_compressible = any(ct in content_type for ct in COMPRESSIBLE_TYPES)

        if not is_compressible:
            return response

        # Read response body
        body = b""
        async for chunk in response.body_iterator:
            if isinstance(chunk, str):
                chunk = chunk.encode("utf-8")
            body += chunk

        # Skip if too small
        if len(body) < MIN_SIZE:
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=content_type,
            )

        # Compress
        compressed = gzip.compress(body, compresslevel=6)

        # Only use if actually smaller
        if len(compressed) >= len(body):
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=content_type,
            )

        # Build new response with compression headers
        headers = dict(response.headers)
        headers["content-encoding"] = "gzip"
        headers["content-length"] = str(len(compressed))
        headers["vary"] = "Accept-Encoding"

        # Remove content-type if not set (it's in the original headers)
        return Response(
            content=compressed,
            status_code=response.status_code,
            headers=headers,
            media_type=content_type,
        )
