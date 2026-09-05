"""Signal Outcome Tracker — the system's public track record.

Records every published signal (discovery scores, strong-move signals, price
alerts, bubble flags) with its claim and evaluation window, then lazily
evaluates each pending signal once its horizon elapses using live quotes.

Design rules:
- A signal is only counted once per symbol/type/day (dedupe by recorded_date).
- Evaluation is deterministic: bullish wins if price rose >= threshold over the
  horizon, bearish wins if it fell >= threshold, otherwise loss/flat/expired.
- Aggregates are honest: flat outcomes are excluded from hit rate; expired
  (no data) outcomes are shown separately.
"""
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("quantive.signal_tracker")

# Default evaluation horizon per signal type (days)
HORIZONS = {
    "discovery_stock": 5,
    "discovery_crypto": 5,
    "strong_move": 5,
    "price_alert": 10,
    "bubble_flag": 20,
}

# Move needed (in %) for the direction call to count as a win
WIN_THRESHOLD_PCT = {
    "discovery_stock": 2.0,
    "discovery_crypto": 3.0,
    "strong_move": 2.0,
    "price_alert": 1.0,
    "bubble_flag": 5.0,  # bearish claim: price should FALL after a bubble flag
}


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _get_db():
    from app.database import SessionLocal
    return SessionLocal()


def record_signal(
    signal_type: str,
    symbol: str,
    direction: str,
    claim: str,
    strength: int = 0,
    asset_class: str = "stock",
    recorded_price: float | None = None,
    horizon_days: int | None = None,
    win_threshold_pct: float | None = None,
    metadata: dict | None = None,
) -> dict | None:
    """Record a published signal. Idempotent per (type, symbol, day).

    Returns the recorded dict, or None if it was a duplicate or invalid.
    """
    if not symbol or direction not in ("bullish", "bearish"):
        return None

    db = _get_db()
    try:
        from app.models.signal_outcome import SignalOutcome

        today = _today()

        # Dedupe: one record per signal_type+symbol+day
        existing = (
            db.query(SignalOutcome)
            .filter(
                SignalOutcome.signal_type == signal_type,
                SignalOutcome.symbol == symbol,
                SignalOutcome.recorded_date == today,
            )
            .first()
        )
        if existing:
            return None

        rec = SignalOutcome(
            signal_type=signal_type,
            symbol=symbol,
            asset_class=asset_class,
            direction=direction,
            claim=(claim or "")[:500],
            strength=int(strength or 0),
            recorded_price=float(recorded_price) if recorded_price else None,
            recorded_at=datetime.now(timezone.utc),
            recorded_date=today,
            horizon_days=horizon_days or HORIZONS.get(signal_type, 5),
            outcome_threshold_pct=(
                win_threshold_pct
                if win_threshold_pct is not None
                else WIN_THRESHOLD_PCT.get(signal_type, 2.0)
            ),
            outcome_status="pending",
            outcome_metadata=metadata or {},
        )
        db.add(rec)
        db.commit()
        return rec.to_dict()
    except Exception as e:
        logger.debug("record_signal failed for %s/%s: %s", signal_type, symbol, e)
        try:
            db.rollback()
        except Exception:
            pass
        return None
    finally:
        db.close()


def record_batch(signals: list[dict]) -> int:
    """Record multiple signals; returns count actually recorded."""
    n = 0
    for s in signals or []:
        if record_signal(**s) is not None:
            n += 1
    return n


# ── Evaluation ──────────────────────────────────────────────────────

def _fetch_price(symbol: str) -> float | None:
    """Best-effort current price for a symbol, from live stores."""
    try:
        from app.api.market_monitor_api import _asset_store
        a = _asset_store.get(symbol)
        if a and a.get("current_price"):
            return float(a["current_price"])
    except Exception:
        pass
    try:
        from app.api.global_market_api import _global_asset_store
        a = _global_asset_store.get(symbol)
        if a and a.get("current_price"):
            return float(a["current_price"])
    except Exception:
        pass
    # Live quote fallback (works even if stores are cold)
    try:
        from app.api.trading_intelligence import _fetch_yahoo_quote
        q = _fetch_yahoo_quote(symbol)
        if q and q.get("price"):
            return float(q["price"])
    except Exception:
        pass
    return None


def evaluate_pending(max_evaluations: int = 200) -> dict:
    """Evaluate pending signals whose horizon has elapsed.

    Bullish win: price rose >= threshold_pct over the window.
    Bearish win: price fell >= threshold_pct over the window.
    Opposite moves are losses; small moves are flat; unresolvable are expired.
    """
    db = _get_db()
    stats = {"evaluated": 0, "wins": 0, "losses": 0, "flat": 0, "expired": 0}
    try:
        from app.models.signal_outcome import SignalOutcome

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=45)  # hard expiry so nothing lingers forever

        pending = (
            db.query(SignalOutcome)
            .filter(SignalOutcome.outcome_status == "pending")
            .filter(SignalOutcome.recorded_at >= cutoff)
            .limit(max_evaluations)
            .all()
        )

        for rec in pending:
            recorded_at = rec.recorded_at
            if recorded_at is None:
                rec.outcome_status = "expired"
                stats["expired"] += 1
                continue
            # Ensure recorded_at is tz-aware
            if recorded_at.tzinfo is None:
                recorded_at = recorded_at.replace(tzinfo=timezone.utc)

            elapsed = (now - recorded_at).total_seconds() / 86400
            if elapsed < rec.horizon_days:
                continue  # not due yet

            current = _fetch_price(rec.symbol)
            if current is None or not rec.recorded_price:
                if elapsed >= 45:
                    rec.outcome_status = "expired"
                    stats["expired"] += 1
                continue

            change_pct = (current - rec.recorded_price) / rec.recorded_price * 100
            rec.price_change_pct = round(change_pct, 2)
            rec.evaluated_price = current
            rec.evaluated_at = now

            threshold = rec.outcome_threshold_pct or 2.0
            moved = abs(change_pct) >= threshold
            right_direction = (
                (rec.direction == "bullish" and change_pct > 0)
                or (rec.direction == "bearish" and change_pct < 0)
            )

            if moved and right_direction:
                rec.outcome_status = "win"
                stats["wins"] += 1
            elif moved and not right_direction:
                rec.outcome_status = "loss"
                stats["losses"] += 1
            else:
                rec.outcome_status = "flat"
                stats["flat"] += 1
            stats["evaluated"] += 1

        db.commit()
        return stats
    except Exception as e:
        logger.warning("evaluate_pending failed: %s", e)
        try:
            db.rollback()
        except Exception:
            pass
        return stats
    finally:
        db.close()


# ── Aggregation ─────────────────────────────────────────────────────

def get_track_record(signal_type: str | None = None) -> dict:
    """Aggregate hit/miss stats, optionally filtered by signal type."""
    db = _get_db()
    try:
        from app.models.signal_outcome import SignalOutcome
        from sqlalchemy import func

        q = db.query(SignalOutcome).filter(
            SignalOutcome.outcome_status.in_(["win", "loss", "flat", "expired"])
        )
        if signal_type:
            q = q.filter(SignalOutcome.signal_type == signal_type)

        total = q.count()
        if total == 0:
            return {
                "has_data": False,
                "signal_type": signal_type,
                "message": "No evaluated signals yet. The track record builds as signals mature past their evaluation window.",
            }

        wins = q.filter(SignalOutcome.outcome_status == "win").count()
        losses = q.filter(SignalOutcome.outcome_status == "loss").count()
        flat = q.filter(SignalOutcome.outcome_status == "flat").count()
        expired = q.filter(SignalOutcome.outcome_status == "expired").count()

        resolved = wins + losses
        hit_rate = round(wins / resolved * 100, 1) if resolved else None

        # Directional accuracy
        bearish_q = q.filter(SignalOutcome.direction == "bearish")
        b_wins = bearish_q.filter(SignalOutcome.outcome_status == "win").count()
        b_losses = bearish_q.filter(SignalOutcome.outcome_status == "loss").count()
        bullish_wins = wins - b_wins
        bullish_losses = losses - b_losses

        # Average price change captured
        avg_change = q.with_entities(func.avg(SignalOutcome.price_change_pct)).scalar()

        # Per-type breakdown
        by_type = {}
        for t in HORIZONS.keys():
            tq = db.query(SignalOutcome).filter(
                SignalOutcome.signal_type == t,
                SignalOutcome.outcome_status.in_(["win", "loss", "flat", "expired"]),
            )
            tt = tq.count()
            if tt == 0:
                continue
            tw = tq.filter(SignalOutcome.outcome_status == "win").count()
            tl = tq.filter(SignalOutcome.outcome_status == "loss").count()
            t_resolved = tw + tl
            by_type[t] = {
                "total": tt,
                "wins": tw,
                "losses": tl,
                "flat": tt - tw - tl,
                "hit_rate": round(tw / t_resolved * 100, 1) if t_resolved else None,
            }

        # Recent evaluated signals (the receipt trail)
        recent = (
            db.query(SignalOutcome)
            .filter(SignalOutcome.outcome_status.in_(["win", "loss", "flat"]))
            .order_by(SignalOutcome.evaluated_at.desc())
            .limit(20)
            .all()
        )

        return {
            "has_data": True,
            "signal_type": signal_type,
            "total_signals": total,
            "wins": wins,
            "losses": losses,
            "flat": flat,
            "expired": expired,
            "hit_rate": hit_rate,
            "resolved": resolved,
            "by_direction": {
                "bullish": {"wins": bullish_wins, "losses": bullish_losses,
                            "hit_rate": round(bullish_wins / (bullish_wins + bullish_losses) * 100, 1) if (bullish_wins + bullish_losses) else None},
                "bearish": {"wins": b_wins, "losses": b_losses,
                            "hit_rate": round(b_wins / (b_wins + b_losses) * 100, 1) if (b_wins + b_losses) else None},
            },
            "avg_price_change_pct": round(float(avg_change), 2) if avg_change is not None else None,
            "by_type": by_type,
            "recent": [r.to_dict() for r in recent],
            "note": (
                "Hit rate counts only signals that moved beyond their threshold. "
                "Past signal accuracy does not guarantee future results."
            ),
        }
    except Exception as e:
        logger.warning("get_track_record failed: %s", e)
        return {"has_data": False, "error": str(e)}
    finally:
        db.close()


def get_pending_count() -> int:
    db = _get_db()
    try:
        from app.models.signal_outcome import SignalOutcome
        return db.query(SignalOutcome).filter(SignalOutcome.outcome_status == "pending").count()
    except Exception:
        return 0
    finally:
        db.close()
