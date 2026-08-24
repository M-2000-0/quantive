from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api import (
    activity, analytics, audit, auth, auth_extended,
    comments, market_data, mfa, notifications, optimizations,
    portfolio_access, portfolios, preferences, progress,
    risk, tags, webhooks, watchlists,
)
from app.database import get_db

router = APIRouter()
router.include_router(auth.router)
router.include_router(auth_extended.router)
router.include_router(mfa.router)
router.include_router(portfolios.router)
router.include_router(portfolio_access.router)
router.include_router(optimizations.router)
router.include_router(audit.router)
router.include_router(analytics.router)
router.include_router(progress.router)
router.include_router(risk.router)
router.include_router(comments.router)
router.include_router(tags.router)
router.include_router(watchlists.router)
router.include_router(activity.activity_router)
router.include_router(activity.export_router)
router.include_router(notifications.notif_router)
router.include_router(notifications.dashboard_router)
router.include_router(preferences.pref_router)
router.include_router(preferences.org_router)
router.include_router(preferences.views_router)
router.include_router(preferences.filters_router)
router.include_router(webhooks.router)
router.include_router(market_data.router)


@router.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    return {"status": "healthy", "version": "1.0.0", "database": db_status}
