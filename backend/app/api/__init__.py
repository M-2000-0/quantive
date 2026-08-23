from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api import audit, auth, optimizations, portfolios
from app.database import get_db

router = APIRouter()
router.include_router(auth.router)
router.include_router(portfolios.router)
router.include_router(optimizations.router)
router.include_router(audit.router)


@router.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    return {"status": "healthy", "version": "1.0.0", "database": db_status}
