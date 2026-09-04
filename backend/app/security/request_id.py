"""Request ID tracking middleware.

Adds a unique correlation ID to every request for tracing.
"""
import uuid
from contextvars import ContextVar
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# Context variable for current request ID (accessible anywhere in the request)
current_request_id: ContextVar[str] = ContextVar("request_id", default="")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Adds X-Request-ID to every request and response."""

    async def dispatch(self, request: Request, call_next):
        # Use client-provided ID if present, otherwise generate one
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Set in context for logging
        current_request_id.set(request_id)

        # Process request
        response = await call_next(request)

        # Add to response headers
        response.headers["X-Request-ID"] = request_id

        return response
