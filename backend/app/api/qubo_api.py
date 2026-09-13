"""Public Qubo trends API — no login required.

Returns age-bracket aggregates only (never individual data). When fewer than
MIN_BUCKET contributors exist per bracket, returns a labeled illustrative
preview so the public Qubo page is useful from day one.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.personal.database import get_personal_db
from app.personal import qubo as qubo_engine

router = APIRouter(prefix="/api/qubo", tags=["qubo"])


@router.get("/trends")
def public_trends(db: Session = Depends(get_personal_db)):
    """Public aggregate trends + contributor count + privacy contract."""
    data = qubo_engine.public_trends(db)
    data["brackets"] = qubo_engine.AGE_BRACKETS
    data["min_bucket"] = qubo_engine.MIN_BUCKET
    return data
