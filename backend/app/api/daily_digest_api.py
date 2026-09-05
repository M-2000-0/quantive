"""Daily Morning Digest API.

Endpoints:
  GET  /api/v1/digest          — Today's briefing (auto-generated, cached per day)
  POST /api/v1/digest/refresh  — Force regeneration
"""
import logging

from fastapi import APIRouter

logger = logging.getLogger("quantive.digest_api")

router = APIRouter(prefix="/digest", tags=["daily-digest"])


@router.get("")
@router.get("/")
def get_digest():
    """Today's morning digest. Generated on first access each day, cached after."""
    from app.services.daily_digest import generate_digest
    digest = generate_digest()
    return {
        **digest,
        "cached": True,
    }


@router.post("/refresh")
def refresh_digest():
    """Force regeneration of today's digest with fresh data."""
    from app.services.daily_digest import generate_digest
    digest = generate_digest(force=True)
    return {**digest, "cached": False}
