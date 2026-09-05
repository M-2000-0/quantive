"""Daily Morning Digest API.

Endpoints:
  GET  /api/v1/digest             — Today's briefing (auto-generated, cached per day)
  GET  /api/v1/digest/portfolio   — Per-user holdings moves + instrument alert status
  POST /api/v1/digest/refresh     — Force regeneration
"""
import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db

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


@router.get("/portfolio")
def get_portfolio_digest(request: Request, db: Session = Depends(get_db)):
    """Per-user portfolio sections: holdings moves + instrument alert status.

    Computed fresh per request (cheap joins against the live asset stores);
    the shared digest is cached daily but these sections are personal.
    Unauthenticated callers get empty sections rather than an error.
    """
    from app.services.portfolio_digest import build_portfolio_digest

    try:
        from app.api.market_monitor_api import _get_user
        user = _get_user(request, db)
    except Exception:
        user = None

    if not user:
        return {
            "holdings": None,
            "alerts": None,
            "has_data": False,
            "note": "Sign in to see your holdings and instrument alerts in the digest.",
        }

    return build_portfolio_digest(db, str(user.id))


@router.post("/refresh")
def refresh_digest():
    """Force regeneration of today's digest with fresh data."""
    from app.services.daily_digest import generate_digest
    digest = generate_digest(force=True)
    return {**digest, "cached": False}
