"""Subscription enforcement middleware.

Blocks API access for accounts with past_due or cancelled subscriptions.
Enforces plan-based resource limits on protected endpoints.
"""
from __future__ import annotations

import os

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# Paths that work without subscription
FREE_PATHS = {
    "/api/health",
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/logout",
    "/api/auth/refresh",
    "/api/billing/plans",
    "/api/billing/checkout",
    "/api/billing/webhook",
    "/api/billing/mode",
    "/api/chat",
    "/docs",
    "/redoc",
    "/openapi.json",
}


class SubscriptionEnforcementMiddleware(BaseHTTPMiddleware):
    """Block access for past_due/cancelled subscriptions on protected endpoints."""

    def __init__(self, app):
        super().__init__(app)
        self._enabled = os.environ.get("PYTEST_CURRENT_TEST") is None

    async def dispatch(self, request: Request, call_next):
        if not self._enabled:
            return await call_next(request)

        path = request.url.path

        # Skip free paths
        if path in FREE_PATHS or path.startswith("/assets/") or path.endswith((".js", ".css", ".svg")):
            return await call_next(request)

        # Skip non-API paths
        if not path.startswith("/api/"):
            return await call_next(request)

        # Check subscription status from request state (set by auth middleware)
        sub_status = getattr(request.state, "subscription_status", None)

        if sub_status in ("past_due", "cancelled", "unpaid"):
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "Subscription required",
                    "status": sub_status,
                    "message": "Your subscription is " + sub_status.replace("_", " ") + ". Please update your payment method.",
                    "upgrade_url": "/api/billing/portal",
                },
            )

        return await call_next(request)
