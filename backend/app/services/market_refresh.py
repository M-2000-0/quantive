"""Scheduled market data refresh — fetch, classify, persist, prune.

Fetchers degrade to flagged fallbacks instead of raising; this service turns
each fetch into a persisted MarketSnapshot so freshness is observable and
auditable. Retries once per source; a total failure records an error
snapshot instead of raising (the scheduler must never die on market data).
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.market_data import fx_rates, yield_curve
from app.models.market import SOURCES, MarketSnapshot

logger = logging.getLogger("quantive.market_refresh")


def _fetch(source: str, use_cache: bool) -> dict:
    if source == "treasury_yields":
        return yield_curve.fetch_treasury_yield_curve(use_cache=use_cache)
    if source == "fx_rates":
        return fx_rates.fetch_ecb_rates(use_cache=use_cache)
    raise ValueError(f"unknown source: {source}")


def _classify(payload: dict) -> tuple[str, int]:
    if not isinstance(payload, dict) or not payload:
        return "error", 0
    if payload.get("is_fallback"):
        count = len(payload.get("maturities") or payload.get("rates") or [])
        return "fallback", count
    count = len(payload.get("maturities") or payload.get("rates") or [])
    return "ok", count


def refresh_market_data(db: Session, use_cache: bool = False,
                        retention_days: int = 30) -> dict:
    """Refresh every source; returns per-source outcomes. Never raises."""
    outcomes: dict[str, dict] = {}
    for source in SOURCES:
        payload: dict = {}
        status, count, error = "error", 0, ""
        for attempt in (1, 2):
            try:
                payload = _fetch(source, use_cache=use_cache and attempt == 1)
                status, count = _classify(payload)
                break
            except Exception as e:  # noqa: BLE001 — record, don't crash
                error = f"{type(e).__name__}: {e}"[:1000]
                logger.warning("market refresh %s attempt %d failed: %s", source, attempt, error)
                time.sleep(2 * attempt)
        try:
            db.add(MarketSnapshot(source=source, status=status,
                                  payload=payload if isinstance(payload, dict) else {},
                                  record_count=count, error=error))
            db.commit()
        except Exception as e:  # noqa: BLE001
            db.rollback()
            error = f"persist failed: {e}"[:1000]
            status = "error"
        outcomes[source] = {"status": status, "records": count, "error": error}

    # Prune snapshots older than retention.
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        pruned = (
            db.query(MarketSnapshot)
            .filter(MarketSnapshot.fetched_at < cutoff)
            .delete(synchronize_session=False)
        )
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()
        pruned = 0
    outcomes["_pruned"] = pruned
    return outcomes
