from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api import (
    activity,
    advisor,
    analytics,
    audit,
    auth,
    auth_extended,
    comments,
    compliance,
    esg,
    exports,
    market_data,
    maturity,
    mfa,
    narrative,
    notifications,
    optimizations,
    portfolio_access,
    portfolios,
    preferences,
    progress,
    ratings,
    risk,
    risk_intel,
    scheduled,
    security_audit,
    tags,
    watchlists,
    webhooks,
)
from app.database import get_db
from app.security.threats import router as threats_router

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
router.include_router(exports.router)
router.include_router(threats_router)
router.include_router(security_audit.router)
router.include_router(narrative.router)
router.include_router(narrative.country_router)
router.include_router(narrative.whatif_router)
router.include_router(advisor.router)
router.include_router(scheduled.router)
router.include_router(scheduled.notification_router)
router.include_router(compliance.router)
router.include_router(compliance.explain_router)
router.include_router(risk_intel.router)
router.include_router(maturity.router)
router.include_router(esg.router)
router.include_router(ratings.router)


@router.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    return {"status": "healthy", "version": "1.0.0", "database": db_status}
