"""Signal Track Record API — the system's public hit/miss record.

Endpoints:
  GET /api/v1/track-record              — Aggregate hit/miss stats
  GET /api/v1/track-record/recent       — Recent evaluated signals (receipts)
  POST /api/v1/track-record/evaluate    — Manually trigger evaluation of due signals
  GET /api/v1/track-record/pending      — Count of signals awaiting evaluation
"""
import logging

from fastapi import APIRouter, Request
from sqlalchemy.orm import Session

from app.database import get_db

logger = logging.getLogger("quantive.track_record")

router = APIRouter(prefix="/track-record", tags=["signal-track-record"])

# Track-record data is public (no user-specific data), but pages require auth.


@router.get("")
@router.get("/")
def get_track_record_summary(signal_type: str | None = None):
    """Aggregate hit/miss statistics for all published signals.

    Query params:
      signal_type — optional filter: discovery_stock, discovery_crypto,
                    strong_move, price_alert, bubble_flag
    """
    # Lazy evaluation pass first so stats are as fresh as possible
    try:
        from app.services.signal_outcome_tracker import evaluate_pending
        evaluate_pending(max_evaluations=100)
    except Exception as e:
        logger.debug("Background evaluation failed: %s", e)

    from app.services.signal_outcome_tracker import get_track_record, get_calibration
    record = get_track_record(signal_type)
    record["calibration"] = get_calibration(signal_type)
    return record


@router.get("/calibration")
def get_calibration_view(signal_type: str | None = None):
    """Hit rate bucketed by signal strength (score at record time).

    Shows which confidence levels are actually reliable, with per-bucket
    sample-size confidence flags.
    """
    from app.services.signal_outcome_tracker import get_calibration
    return get_calibration(signal_type)


@router.get("/recent")
def get_recent_outcomes(limit: int = 20):
    """Recently evaluated signals — the receipt trail."""
    try:
        from app.services.signal_outcome_tracker import evaluate_pending, get_track_record
        evaluate_pending(max_evaluations=50)
        record = get_track_record()
        return {"recent": record.get("recent", [])[:limit], "has_data": record.get("has_data", False)}
    except Exception as e:
        return {"recent": [], "error": str(e)}


@router.post("/evaluate")
def trigger_evaluation():
    """Manually trigger evaluation of all due pending signals."""
    from app.services.signal_outcome_tracker import evaluate_pending
    stats = evaluate_pending(max_evaluations=500)
    return {"triggered": True, "stats": stats}


@router.get("/pending")
def get_pending():
    """Number of signals still inside their evaluation window."""
    from app.services.signal_outcome_tracker import get_pending_count
    return {"pending": get_pending_count()}
