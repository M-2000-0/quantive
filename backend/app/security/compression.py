"""
GZip Compression Middleware
===========================
Compresses responses for faster page loads.
Handles HTML, CSS, JS, JSON, and SVG content types.
"""

import gzip

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

        # Compress
        compressed = gzip.compress(body, compresslevel=6)

        # Only use if actually smaller
        if len(body) >= MIN_SIZE and len(compressed) < len(body):
            return self._rebuild(response, compressed, gzipped=True)

        # Too small or not worth compressing — re-emit the original body,
        # preserving the original headers EXACTLY (including duplicate
        # Set-Cookie headers). A plain dict(response.headers) collapse would
        # silently drop the refresh_token cookie from login/register responses.
        return self._rebuild(response, body, gzipped=False)

    @staticmethod
    def _rebuild(response: Response, body: bytes, gzipped: bool) -> Response:
        raw = [(k, v) for k, v in response.raw_headers]
        if gzipped:
            raw = [
                (k, v)
                for (k, v) in raw
                if k not in (b"content-length", b"content-encoding", b"vary")
            ]
            raw.append((b"content-encoding", b"gzip"))
            raw.append((b"content-length", str(len(body)).encode("latin-1")))
            raw.append((b"vary", b"Accept-Encoding"))
        else:
            raw = [(k, v) for (k, v) in raw if k != b"content-length"]
            raw.append((b"content-length", str(len(body)).encode("latin-1")))

        new = Response(content=body, status_code=response.status_code)
        new.raw_headers = raw
        return new