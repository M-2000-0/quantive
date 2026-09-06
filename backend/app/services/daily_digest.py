"""Daily Morning Digest — a single briefing card combining the day's key intel.

Sections:
  1. Market Pulse      — one-paragraph equities/crypto/yields summary
  2. Top Movers        — biggest gainers and losers with context
  3. Volatility Regime — calm/normal/elevated/stressed/panic classification
  4. Bubble Alerts     — high/critical bubble-risk flags from the detector
  5. News Sentiment    — strongest news tone among tracked assets (if available)

The digest is generated once per day (cached in memory + persisted as JSON in
.freebuff/ or data dir) and refreshed on demand or hourly by the scheduler.
Generation is fully
fire-safe: a failing section degrades to null instead of breaking the card.
"""
import json
import logging
import os
import time
from datetime import datetime, timezone

logger = logging.getLogger("quantive.daily_digest")

_digest_cache: dict | None = None
_digest_date: str | None = None

# Persisted so a server restart doesn't regenerate a different morning brief
_DIGEST_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".freebuff")
_DIGEST_FILE = os.path.join(_DIGEST_DIR, "daily-digest.json")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load_persisted() -> tuple[dict | None, str | None]:
    try:
        if os.path.exists(_DIGEST_FILE):
            with open(_DIGEST_FILE, encoding="utf-8") as f:
                data = json.load(f)
            return data, data.get("date")
    except Exception:
        pass
    return None, None


def _persist(digest: dict):
    try:
        os.makedirs(_DIGEST_DIR, exist_ok=True)
        with open(_DIGEST_FILE, "w", encoding="utf-8") as f:
            json.dump(digest, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.debug("Could not persist digest: %s", e)


def _get_asset_stores() -> list[dict]:
    assets: list[dict] = []
    try:
        from app.api.market_monitor_api import _asset_store
        assets.extend(_asset_store.values())
    except Exception:
        pass
    try:
        from app.api.global_market_api import _global_asset_store
        assets.extend(_global_asset_store.values())
    except Exception:
        pass
    return assets


def _collect_stores() -> dict:
    """Collect all inputs the digest needs. Returns dict of raw inputs."""
    inputs: dict = {"assets": _get_asset_stores()}

    # Prices for volatility regime (use any asset with history)
    try:
        from app.api.market_monitor_api import _price_store
        inputs["price_store"] = _price_store
    except Exception:
        inputs["price_store"] = {}

    # Yields for the pulse line
    try:
        from app.services.market_monitor_ingest import fetch_treasury_yields
        inputs["yields"] = fetch_treasury_yields() or {}
    except Exception:
        inputs["yields"] = {}

    return inputs


def _section_pulse(assets: list[dict], yields: dict) -> dict | None:
    try:
        from app.services.market_monitor_alerts import generate_market_pulse_summary
        summary = generate_market_pulse_summary(assets, yields=yields)
        stocks = [a for a in assets if a.get("asset_class") == "stock"]
        crypto = [a for a in assets if a.get("asset_class") == "crypto"]

        def _avg(lst):
            vals = [a.get("day_change_pct", 0) or 0 for a in lst]
            return round(sum(vals) / len(vals), 2) if vals else 0

        return {
            "summary": summary,
            "stocks_avg": _avg(stocks),
            "crypto_avg": _avg(crypto),
            "stock_count": len(stocks),
            "crypto_count": len(crypto),
            "total_tracked": len(assets),
        }
    except Exception as e:
        logger.warning("pulse section failed: %s", e)
        return None


def _section_movers(assets: list[dict], top_n: int = 5) -> dict | None:
    try:
        movers = [a for a in assets if a.get("asset_class") in ("stock", "crypto") and a.get("day_change_pct") is not None]
        gainers = sorted(movers, key=lambda x: x.get("day_change_pct", 0), reverse=True)[:top_n]
        losers = sorted(movers, key=lambda x: x.get("day_change_pct", 0))[:top_n]

        def _fmt(a):
            return {
                "symbol": (a.get("symbol") or "").split(":")[-1],
                "name": (a.get("name") or "")[:30],
                "price": a.get("current_price"),
                "change_pct": a.get("day_change_pct"),
            }

        return {"gainers": [_fmt(a) for a in gainers], "losers": [_fmt(a) for a in losers]}
    except Exception as e:
        logger.warning("movers section failed: %s", e)
        return None


def _section_volatility(price_store: dict) -> dict | None:
    try:
        from app.services.market_monitor_algo import detect_volatility_regime

        closes: list[float] = []

        # Prefer cached SPY series if present
        spy = price_store.get("SPY") or []
        if isinstance(spy, list) and len(spy) >= 10:
            for p in spy:
                closes.append(p["close"] if isinstance(p, dict) else float(p))

        # Otherwise fetch SPY history directly (bounded, one call)
        if len(closes) < 10:
            try:
                from app.services.market_monitor_ingest import fetch_yahoo_history
                hist = fetch_yahoo_history("SPY", days=90)
                closes = [h["close"] for h in hist if h.get("close")]
            except Exception:
                pass

        if len(closes) < 10:
            return {"regime": "unknown", "description": "Insufficient price history", "color": "#9ca3af"}

        return detect_volatility_regime(spy_prices=closes)
    except Exception as e:
        logger.warning("volatility section failed: %s", e)
        return None


def _section_bubble(assets: list[dict]) -> dict | None:
    try:
        from app.services.bubble_detector import scan_portfolio_for_bubbles

        scan = scan_portfolio_for_bubbles(assets)
        results = scan.get("scan_results") or []
        flagged = [
            {
                "symbol": (r.get("symbol") or "").split(":")[-1],
                "score": r.get("bubble_score"),
                "level": r.get("risk_level"),
                "patterns": [
                    (p.get("name") if isinstance(p, dict) else str(p))
                    for p in (r.get("pattern_details") or [])[:2]
                ],
            }
            for r in results
            if r.get("bubble_score", 0) >= 60 and r.get("risk_level") in ("HIGH", "EXTREME")
        ][:5]
        return {
            "flagged": flagged,
            "extreme_count": scan.get("extreme_count", 0),
            "high_count": scan.get("high_count", 0),
            "total_scanned": scan.get("total_scanned", len(assets)),
            "overall_risk": scan.get("overall_risk_score", 0),
        }
    except Exception as e:
        logger.warning("bubble section failed: %s", e)
        return None


def _section_sentiment() -> dict | None:
    """Strongest news-sentiment assets (positive AND negative conviction)."""
    try:
        from app.database import SessionLocal
        from app.api.sentiment_api import _recent_scores_by_ticker
        from app.services.sentiment_analyzer import aggregate_sentiment

        db = SessionLocal()
        try:
            by_ticker = _recent_scores_by_ticker(db, days=2)
        finally:
            db.close()

        aggs = []
        for sym, scores in by_ticker.items():
            if len(scores) < 2:
                continue
            agg = aggregate_sentiment(scores)
            if agg["count"] >= 2:
                aggs.append({"symbol": sym, **agg})

        aggs.sort(key=lambda a: abs(a.get("mean") or 0), reverse=True)
        most_positive = [a for a in aggs if (a.get("mean") or 0) > 0.15][:3]
        most_negative = [a for a in aggs if (a.get("mean") or 0) < -0.15][:3]
        return {"most_positive": most_positive, "most_negative": most_negative}
    except Exception as e:
        logger.debug("sentiment section failed: %s", e)
        return None


def generate_digest(force: bool = False) -> dict:
    """Generate (or return cached) today's morning digest."""
    global _digest_cache, _digest_date

    today = _today()

    if not force and _digest_cache and _digest_date == today:
        return _digest_cache

    # Try persisted version from an earlier run today
    if not force:
        cached, cached_date = _load_persisted()
        if cached and cached_date == today:
            _digest_cache = cached
            _digest_date = cached_date
            return cached

    inputs = _collect_stores()
    assets = inputs["assets"]

    # If stores are cold, warm them via the ingestion logic. The API endpoint
    # requires a Request/DB, so extract the store-filling loop directly by
    # reusing its internals through a lightweight shim.
    # Time-budgeted: a cold full ingestion touches 200+ upstream endpoints and
    # can run for many minutes; the digest must never block that long. The
    # warm-up runs in a daemon thread and is abandoned at the budget — it keeps
    # filling the shared store in the background, so a later refresh picks up
    # whatever landed.
    if len(assets) < 20:
        _WARMUP_BUDGET_S = float(os.environ.get("DIGEST_WARMUP_BUDGET_S", "60"))
        import threading

        _warm_error: list = []

        def _warm():
            try:
                from app.api.market_monitor_api import run_ingestion

                class _ShimRequest:
                    pass

                try:
                    run_ingestion(request=_ShimRequest(), asset_class=None, db=None)
                except TypeError:
                    # Different signature — try positional-free variant
                    run_ingestion(_ShimRequest(), None, None)
            except Exception as e:  # pragma: no cover - defensive
                _warm_error.append(e)

        _t = threading.Thread(target=_warm, name="digest-warmup", daemon=True)
        _t.start()
        _t.join(timeout=max(1.0, _WARMUP_BUDGET_S))
        if _t.is_alive():
            logger.warning(
                "digest store warm-up still running after %.0fs budget; "
                "generating from available data (warm-up continues in background)",
                _WARMUP_BUDGET_S,
            )
        if _warm_error:
            logger.warning("digest store warm-up failed: %s", _warm_error[0])
        assets = _get_asset_stores()

    digest = {
        "date": today,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "refresh_count": 0,
        "headline": None,
        "pulse": _section_pulse(assets, inputs["yields"]),
        "movers": _section_movers(assets),
        "volatility": _section_volatility(inputs.get("price_store", {})),
        "bubble": _section_bubble(assets),
        "sentiment": _section_sentiment(),
        "disclaimer": (
            "Automated analytical output for decision-support purposes only. "
            "Does not constitute financial advice."
        ),
    }

    # One-line headline for the card top
    parts = []
    if digest["pulse"]:
        parts.append(digest["pulse"]["summary"].rstrip("."))
    if digest["volatility"] and digest["volatility"].get("regime") not in (None, "unknown"):
        parts.append(f"{digest['volatility']['regime'].title()} volatility")
    if digest["bubble"] and digest["bubble"]["flagged"]:
        parts.append(f"{len(digest['bubble']['flagged'])} bubble alert{'s' if len(digest['bubble']['flagged']) != 1 else ''}")
    digest["headline"] = " — ".join(parts) + "." if parts else "Market data unavailable — run ingestion to populate the briefing."

    _digest_cache = digest
    _digest_date = today
    _persist(digest)
    return digest


def get_digest_if_stale() -> tuple[dict, bool]:
    """Return (digest, was_regenerated). Used by background refresh."""
    global _digest_cache, _digest_date
    today = _today()
    if _digest_cache and _digest_date == today:
        return _digest_cache, False
    return generate_digest(), True


def refresh_digest_data() -> dict:
    """Regenerate today's digest from current live stores, keeping caches
    coherent. Used by the hourly scheduler so the briefing tracks the
    trading day instead of freezing at the first access each morning.

    Keeps the original date; bumps generated_at and refresh_count.
    """
    global _digest_cache, _digest_date
    prior_count = int((_digest_cache or {}).get("refresh_count") or 0)
    fresh = generate_digest(force=True)
    fresh["date"] = _today()
    # generate_digest resets the count; accumulate across the day instead
    fresh["refresh_count"] = prior_count + 1
    fresh["generated_at"] = datetime.now(timezone.utc).isoformat()
    _digest_cache = fresh
    _digest_date = fresh["date"]
    _persist(fresh)
    return fresh
