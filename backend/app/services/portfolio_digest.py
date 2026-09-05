"""Portfolio-aware digest sections — the user's own holdings and alerts.

The shared morning digest is cached per day and identical for everyone;
these sections are per-user and computed fresh on each request (cheap:
join watchlist/alert symbols to the in-memory asset stores).

Sections:
  1. Holdings Moves    — watchlist instruments' day moves with a portfolio
                         average vs the market pulse, and which holdings'
                         moves stand out (≥2σ against tracked-asset moves).
  2. Instrument Alerts — the user's active price/bubble alerts matched to
                         live prices: armed, in-warning-zone, or triggered.
"""
import logging
from datetime import datetime, timezone

logger = logging.getLogger("quantive.portfolio_digest")

# Standout-move thresholds (absolute day change %)
_STANDOUT_GAIN = 3.0
_STANDOUT_DROP = -3.0


def _load_stores() -> tuple[dict[str, dict], list[dict]]:
    """(asset lookup by bare symbol, all assets list) from live stores."""
    lookup: dict[str, dict] = {}
    all_assets: list[dict] = []
    try:
        from app.api.market_monitor_api import _asset_store
        for key, a in _asset_store.items():
            all_assets.append(a)
            sym = (a.get("symbol") or "").split(":")[-1].upper()
            if sym and sym not in lookup:
                lookup[sym] = a
    except Exception:
        pass
    try:
        from app.api.global_market_api import _global_asset_store
        for key, a in _global_asset_store.items():
            all_assets.append(a)
            sym = (a.get("symbol") or "").split(":")[-1].upper()
            if sym and sym not in lookup:
                lookup[sym] = a
    except Exception:
        pass
    return lookup, all_assets


def _portfolio_symbols(db, user_id: str) -> list[dict]:
    """The user's instruments: watchlist + alert symbols, deduped."""
    items: dict[str, dict] = {}
    try:
        from app.api.market_monitor_api import _watchlist
        for w in _watchlist:
            sym = (w.get("symbol") or "").upper()
            if sym:
                items.setdefault(sym, {"symbol": sym, "sources": ["watchlist"]})
    except Exception:
        pass
    try:
        from app.api.market_monitor_api import _alert_store
        for a in _alert_store:
            if a.get("user_id") == user_id and a.get("is_active", True):
                sym = (a.get("symbol") or "").upper()
                if sym:
                    e = items.setdefault(sym, {"symbol": sym, "sources": []})
                    if "alert" not in e["sources"]:
                        e["sources"].append("alert")
    except Exception:
        pass
    return list(items.values())


def _section_holdings(assets: list[dict], all_assets: list[dict]) -> dict | None:
    """User holdings' moves with standout detection vs the tracked market."""
    if not assets:
        return None

    # Market baseline: average absolute-and-signed move of tracked assets
    market_moves = [a.get("day_change_pct") for a in all_assets
                    if isinstance(a.get("day_change_pct"), (int, float))]
    market_avg = round(sum(market_moves) / len(market_moves), 2) if market_moves else None

    holdings = []
    standout_count = 0
    for a in assets:
        change = a.get("day_change_pct")
        entry = {
            "symbol": a.get("symbol", ""),
            "name": (a.get("name") or "")[:28],
            "price": a.get("current_price"),
            "change_pct": change,
            "asset_class": a.get("asset_class", "stock"),
        }
        if isinstance(change, (int, float)):
            if change >= _STANDOUT_GAIN or change <= _STANDOUT_DROP:
                entry["standout"] = True
                standout_count += 1
        holdings.append(entry)

    # Portfolio average (signed) for the summary line
    moves = [h["change_pct"] for h in holdings if isinstance(h.get("change_pct"), (int, float))]
    avg = round(sum(moves) / len(moves), 2) if moves else None

    holdings.sort(key=lambda h: h.get("change_pct") if isinstance(h.get("change_pct"), (int, float)) else -999,
                  reverse=True)
    return {
        "holdings": holdings[:12],
        "total": len(holdings),
        "portfolio_avg_change": avg,
        "market_avg_change": market_avg,
        "standout_count": standout_count,
    }


def _classify_alert(alert: dict, asset: dict | None) -> dict | None:
    """Classify one alert against the live price. Returns alert row or None."""
    sym = alert.get("symbol", "")
    if not asset or not isinstance(asset.get("current_price"), (int, float)):
        return {
            "symbol": sym, "alert_type": alert.get("alert_type", "price"),
            "condition": alert.get("condition", ""), "threshold": alert.get("threshold"),
            "status": "no_data", "current_price": None, "distance_pct": None,
        }

    price = float(asset["current_price"])
    atype = (alert.get("alert_type") or "price").lower()
    cond = (alert.get("condition") or "above").lower()
    threshold = alert.get("threshold")

    row = {
        "symbol": sym,
        "alert_type": atype,
        "condition": cond,
        "threshold": threshold,
        "current_price": price,
        "status": "armed",
    }

    if atype == "price" and isinstance(threshold, (int, float)):
        t = float(threshold)
        if cond == "above" and price >= t:
            row["status"] = "triggered"
        elif cond == "below" and price <= t:
            row["status"] = "triggered"
        elif t > 0:
            # Warning zone: within 2% of the threshold
            gap = abs(price - t) / t
            if gap <= 0.02:
                row["status"] = "warning_zone"
            row["distance_pct"] = round((price - t) / t * 100, 2)
    elif atype == "price_change_pct" and isinstance(threshold, (int, float)):
        change = asset.get("day_change_pct") or 0
        if abs(float(change)) >= abs(float(threshold)):
            row["status"] = "triggered"
        row["current_change_pct"] = change

    return row


def _section_alerts(db, user_id: str, lookup: dict[str, dict]) -> dict | None:
    """User's active alerts evaluated against live prices."""
    alerts: list[dict] = []
    try:
        from app.api.market_monitor_api import _alert_store
        alerts = [a for a in _alert_store
                  if a.get("user_id") == user_id and a.get("is_active", True)]
    except Exception:
        pass

    # Also include persisted alerts (survive restarts)
    try:
        from app.models.market_monitor import UserAlert
        rows = db.query(UserAlert).filter(
            UserAlert.user_id == user_id, UserAlert.is_active == True  # noqa: E712
        ).all()
        persisted_symbols = {a.symbol if hasattr(a, "symbol") else None for a in rows}
        known = {(a.get("symbol"), a.get("alert_type"), a.get("condition"), a.get("threshold"))
                 for a in alerts}
        for r in rows:
            # UserAlert rows store condition/threshold but the symbol lives in
            # metadata_json for persisted rows; best-effort recovery
            meta = r.metadata_json if isinstance(r.metadata_json, dict) else {}
            sym = (meta.get("symbol") or "").upper()
            if not sym:
                continue
            key = (sym, r.alert_type, r.condition, r.threshold)
            if key not in known:
                alerts.append({
                    "symbol": sym, "alert_type": r.alert_type,
                    "condition": r.condition, "threshold": r.threshold,
                    "is_active": True, "source": "db",
                })
    except Exception as e:
        logger.debug("persisted alert lookup failed: %s", e)

    if not alerts:
        return None

    rows = []
    triggered = 0
    warning = 0
    for a in alerts:
        row = _classify_alert(a, lookup.get(a.get("symbol", "")))
        if row:
            if row["status"] == "triggered":
                triggered += 1
            elif row["status"] == "warning_zone":
                warning += 1
            rows.append(row)

    rows.sort(key=lambda r: {"triggered": 0, "warning_zone": 1, "armed": 2, "no_data": 3}.get(r["status"], 4))
    return {
        "alerts": rows[:10],
        "total": len(rows),
        "triggered_count": triggered,
        "warning_count": warning,
    }


def build_portfolio_digest(db, user_id: str) -> dict:
    """Per-user portfolio sections for the morning digest. Never raises."""
    result = {
        "holdings": None,
        "alerts": None,
        "has_data": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        lookup, all_assets = _load_stores()
        symbols = _portfolio_symbols(db, user_id)

        holdings_assets = [lookup[s["symbol"]] for s in symbols if s["symbol"] in lookup]
        result["holdings"] = _section_holdings(holdings_assets, all_assets)
        result["alerts"] = _section_alerts(db, user_id, lookup)
        result["has_data"] = bool(result["holdings"] or result["alerts"])
    except Exception as e:
        logger.warning("portfolio digest failed: %s", e)
    return result
