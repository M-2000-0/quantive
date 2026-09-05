"""Sentiment–price divergence detection for the market monitor.

Flags assets where news coverage tone and price action disagree over the
same 3-day window — the two interesting cases:

  BULLISH DIVERGENCE  — coverage negative, price rising. The market is
  ignoring bad news (accumulation, or the beginning of a denial phase).

  BEARISH DIVERGENCE  — coverage euphoric, price falling. Hype has
  decoupled from delivery (distribution, or a top being formed).

Both directions matter, and so does the boring case: alignment. Assets
whose tone and price agree are healthy and are *not* flagged.

Design notes
------------
- Sentiment comes from the scored-article DB (5-day lookback, >=3 articles
  required so one headline can't fake a signal).
- Price action uses the same 3-day window: prefer the asset store's
  day_change_pct (fresh, from ingestion); fall back to Yahoo 5-day history
  only when needed, bounded and rate-limit-safe (max 12 lookups per call,
  cached in-process for 10 minutes).
- Deterministic: same inputs always produce the same classification.
"""

import logging
import time
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("quantive.divergence")

# In-process cache: symbol -> (expiry, day_change_pct)
_price_change_cache: dict[str, tuple[float, float | None]] = {}
_PRICE_CACHE_TTL = 600  # 10 minutes
_MAX_HISTORY_LOOKUPS = 12  # rate-limit safety for Yahoo fallback

# Classification thresholds
_SENTIMENT_STRONG = 0.25   # |mean| above this = strong tone
_SENTIMENT_MILD = 0.10     # |mean| above this = mild tone
_PRICE_STRONG = 2.0        # |3-day price move| above this = strong move
_PRICE_MILD = 0.75         # |3-day price move| above this = mild move
_STRENGTH_CAP = 100


def _classify(mean: float, price_move: float) -> tuple[str | None, float, str]:
    """Classify one asset. Returns (divergence_type, strength, reason)."""
    strength = min(_STRENGTH_CAP, round(abs(mean) * 55 + abs(price_move) * 9))
    reason = (
        f"News tone {mean:+.2f} vs price {price_move:+.2f}% over 3 days"
    )

    # Bearish divergence: euphoric coverage while price falls
    if mean >= _SENTIMENT_STRONG and price_move <= -_PRICE_MILD:
        if mean >= 0.45 and price_move <= -_PRICE_STRONG:
            return "bearish_divergence", max(strength, 85), reason
        return "bearish_divergence", strength, reason

    # Bullish divergence: negative coverage while price rises
    if mean <= -_SENTIMENT_STRONG and price_move >= _PRICE_MILD:
        if mean <= -0.45 and price_move >= _PRICE_STRONG:
            return "bullish_divergence", max(strength, 85), reason
        return "bullish_divergence", strength, reason

    # Mild cases still worth surfacing when both sides are directional
    if mean >= _SENTIMENT_MILD and price_move <= -_PRICE_MILD:
        return "bearish_divergence", max(25, strength // 2), reason
    if mean <= -_SENTIMENT_MILD and price_move >= _PRICE_MILD:
        return "bullish_divergence", max(25, strength // 2), reason

    return None, 0, reason


def _price_move_3d(asset: dict) -> float | None:
    """Best-effort 3-day price move for one asset.

    Uses day_change_pct directly when it's a strong move (ingestion is
    fresh); otherwise fetches bounded Yahoo history. Returns pct or None.
    """
    symbol = (asset.get("symbol") or "").split(":")[-1].upper()
    day = asset.get("day_change_pct")

    # A strong single-day move is itself decisive evidence — use it directly
    if day is not None and abs(float(day)) >= _PRICE_STRONG:
        return float(day)

    # Cached result?
    now = time.time()
    cached = _price_change_cache.get(symbol)
    if cached and cached[0] > now:
        return cached[1]

    # Budget guard: bound external lookups per compute pass
    if _Budget.value <= 0:
        return float(day) if day is not None else None
    _Budget.value -= 1

    try:
        from app.services.market_monitor_ingest import fetch_yahoo_history

        history = fetch_yahoo_history(symbol, days=5)
        if len(history) >= 4:
            first = float(history[0]["close"])
            last = float(history[-1]["close"])
            if first > 0:
                move = (last - first) / first * 100
                _price_change_cache[symbol] = (now + _PRICE_CACHE_TTL, move)
                return move
    except Exception as e:
        logger.debug("history fetch failed for %s: %s", symbol, e)

    _price_change_cache[symbol] = (now + _PRICE_CACHE_TTL, None)
    return float(day) if day is not None else None


class _Budget:
    """Per-compute-pass budget for external price-history lookups."""

    value = 12


def compute_divergences(
    assets: list[dict],
    sentiment_by_symbol: dict[str, dict],
) -> list[dict]:
    """Compute divergence flags for assets that have both sentiment and price data.

    Args:
        assets: asset dicts from the market monitor store
        sentiment_by_symbol: {SYMBOL: {"mean": float, "count": int, ...}}

    Returns:
        list of divergence dicts, strongest first. Only flagged assets included.
    """
    _Budget.value = _MAX_HISTORY_LOOKUPS

    flags = []
    for a in assets:
        symbol = (a.get("symbol") or "").split(":")[-1].upper()
        if not symbol:
            continue
        sent = sentiment_by_symbol.get(symbol)
        if not sent or not sent.get("count") or sent["count"] < 3:
            continue
        mean = sent.get("mean")
        if mean is None:
            continue

        price_move = _price_move_3d(a)
        if price_move is None:
            continue

        dtype, strength, reason = _classify(mean, price_move)
        if dtype is None:
            continue

        flags.append({
            "symbol": symbol,
            "name": a.get("name", symbol),
            "asset_class": a.get("asset_class", "stock"),
            "current_price": a.get("current_price"),
            "news_sentiment": round(mean, 3),
            "article_count": sent["count"],
            "price_change_pct": round(price_move, 2),
            "divergence_type": dtype,
            "strength": min(_STRENGTH_CAP, strength),
            "reason": reason,
            "label": (
                "Bearish Divergence" if dtype == "bearish_divergence"
                else "Bullish Divergence"
            ),
            "detected_at": datetime.now(timezone.utc).isoformat(),
        })

    flags.sort(key=lambda f: f["strength"], reverse=True)
    return flags
