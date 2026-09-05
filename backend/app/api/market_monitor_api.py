"""
Market Monitor API — Real-time market tracking, discovery, alerts, and insights.

Endpoints:
  GET  /api/market-monitor/assets          — List all tracked assets
  POST /api/market-monitor/ingest          — Run data ingestion
  GET  /api/market-monitor/discovery       — Get discovery scores (stocks + crypto)
  GET  /api/market-monitor/signals         — Get active trading signals
  GET  /api/market-monitor/insights        — Get daily insights
  GET  /api/market-monitor/pulse           — Get market pulse summary
  GET  /api/market-monitor/volatility      — Get volatility regime
  POST /api/market-monitor/alerts/create   — Create custom alert
  GET  /api/market-monitor/alerts          — List user alerts
  GET  /api/market-monitor/alerts/history  — Alert trigger history
  GET  /api/market-monitor/watchlist       — Get user watchlist
  POST /api/market-monitor/watchlist/add   — Add to watchlist
"""
from datetime import datetime, timezone
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

logger = logging.getLogger("quantive.market_monitor")

router = APIRouter(prefix="/market-monitor", tags=["market-monitor"])


def _get_user(request: Request, db: Session):
    token = request.cookies.get("access_token", "")
    if not token:
        return None
    try:
        from app.security import decode_token
        payload = decode_token(token)
        if payload:
            return db.query(User).filter(User.id == payload.get("sub")).first()
    except Exception:
        pass
    return None


class AlertCreateRequest(BaseModel):
    symbol: str
    alert_type: str
    condition: str = "above"
    threshold: float = 0
    delivery_channels: list = ["in_app"]
    repeat: str = "once"


class WatchlistAddRequest(BaseModel):
    symbol: str
    asset_class: str = "stock"
    name: str = ""


# ── In-memory store (upgrade to DB for production) ──────────────────

_asset_store = {}  # symbol -> asset data
_price_store = {}  # symbol -> list of prices
_alert_store = []  # user alerts
_watchlist = []    # user watchlist
_insight_cache = [] # cached insights
_signal_cache = []  # cached signals


# ── Asset Endpoints ─────────────────────────────────────────────────

@router.get("/assets")
def list_assets(
    request: Request,
    asset_class: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List all tracked market assets."""
    assets = list(_asset_store.values())
    if asset_class:
        assets = [a for a in assets if a.get("asset_class") == asset_class]
    assets.sort(key=lambda x: abs(x.get("day_change_pct", 0)), reverse=True)
    return {"assets": assets[:limit], "total": len(assets)}


@router.post("/ingest")
def run_ingestion(
    request: Request,
    asset_class: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Run data ingestion pipeline to fetch latest market data."""
    from app.services.market_monitor_ingest import (
        fetch_yahoo_quote, fetch_coingecko_top, fetch_ecb_fx,
        fetch_treasury_yields,
    )
    from app.services.global_market_universe import get_global_stock_universe, get_crypto_universe

    results = {"stocks": 0, "crypto": 0, "fx": 0, "yields": 0, "errors": []}

    # Fetch stocks from all exchanges
    universe = get_global_stock_universe()
    all_symbols = []
    for exchange, symbols in universe.items():
        all_symbols.extend(symbols[:15])  # 15 per exchange

    if not asset_class or asset_class == "stock":
        for symbol in all_symbols[:200]:  # Cap at 200 for rate limits
            try:
                quote = fetch_yahoo_quote(symbol)
                if quote and quote.get("price", 0) > 0:
                    _asset_store[symbol] = {
                        "symbol": symbol,
                        "name": quote.get("name", symbol),
                        "asset_class": "stock",
                        "exchange": quote.get("exchange", ""),
                        "current_price": quote["price"],
                        "previous_close": quote.get("previous_close", 0),
                        "day_change_pct": quote.get("day_change_pct", 0),
                        "market_cap": quote.get("market_cap", 0),
                        "volume_24h": quote.get("volume", 0),
                        "high_52w": quote.get("fifty_two_week_high", 0),
                        "low_52w": quote.get("fifty_two_week_low", 0),
                        "currency": quote.get("currency", "USD"),
                        "last_updated": datetime.now(timezone.utc).isoformat(),
                    }
                    results["stocks"] += 1
            except Exception as e:
                results["errors"].append(f"{symbol}: {str(e)[:50]}")

    # Fetch crypto from all categories
    if not asset_class or asset_class == "crypto":
        try:
            crypto_universe = get_crypto_universe()
            all_crypto_ids = []
            for cat, ids in crypto_universe.items():
                all_crypto_ids.extend(ids)
            coins = fetch_coingecko_top(30)  # Get top 30
            for coin in coins:
                sym = coin["symbol"]
                _asset_store[f"CRYPTO:{sym}"] = {
                    "symbol": sym,
                    "name": coin.get("name", sym),
                    "asset_class": "crypto",
                    "current_price": coin.get("price", 0),
                    "day_change_pct": coin.get("day_change_pct", 0),
                    "market_cap": coin.get("market_cap", 0),
                    "volume_24h": coin.get("volume_24h", 0),
                    "ath": coin.get("ath", 0),
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                }
                results["crypto"] += 1
        except Exception as e:
            results["errors"].append(f"Crypto: {str(e)[:50]}")

    # Fetch FX
    if not asset_class or asset_class == "fx":
        try:
            fx_rates = fetch_ecb_fx()
            for pair, rate in fx_rates.items():
                _asset_store[f"FX:{pair}"] = {
                    "symbol": pair,
                    "name": pair,
                    "asset_class": "fx",
                    "current_price": rate,
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                }
                results["fx"] += 1
        except Exception as e:
            results["errors"].append(f"FX: {str(e)[:50]}")

    # Fetch yields
    if not asset_class or asset_class == "bond":
        try:
            yields = fetch_treasury_yields()
            for maturity, rate in yields.items():
                _asset_store[f"BOND:US-{maturity}Y"] = {
                    "symbol": f"US-{maturity}Y",
                    "name": f"US Treasury {maturity}Y",
                    "asset_class": "bond",
                    "current_price": rate,
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                }
                results["yields"] += 1
        except Exception as e:
            results["errors"].append(f"Yields: {str(e)[:50]}")

    # Run discovery scoring after ingestion
    _run_discovery_scoring()

    return {
        "status": "completed",
        "results": results,
        "total_assets": len(_asset_store),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── Discovery Endpoints ─────────────────────────────────────────────

@router.get("/discovery")
def get_discovery_scores(
    request: Request,
    asset_class: Optional[str] = None,
    limit: int = 20,
):
    """Get discovery scores for all assets (stocks and crypto)."""
    assets = list(_asset_store.values())
    if asset_class:
        assets = [a for a in assets if a.get("asset_class") == asset_class]

    scored = [a for a in assets if a.get("discovery_score", 0) > 0]
    scored.sort(key=lambda x: x.get("discovery_score", 0), reverse=True)

    return {
        "assets": scored[:limit],
        "rising_stars": [a for a in scored if a.get("classification") == "rising_star"],
        "watch_list": [a for a in scored if a.get("classification") == "watch"],
        "total_scored": len(scored),
    }


@router.get("/signals")
def get_trading_signals(
    request: Request,
    asset_class: Optional[str] = None,
):
    """Get active trading signals across all assets."""
    return {"signals": _signal_cache[:20], "total": len(_signal_cache)}


# ── Insights Endpoints ──────────────────────────────────────────────

@router.get("/insights")
def get_insights(
    request: Request,
    insight_type: Optional[str] = None,
    limit: int = 10,
):
    """Get daily market insights."""
    insights = _insight_cache
    if insight_type:
        insights = [i for i in insights if i.get("insight_type") == insight_type]
    return {"insights": insights[:limit], "total": len(insights)}


@router.get("/pulse")
def get_market_pulse(request: Request):
    """Get market pulse summary."""
    from app.services.market_monitor_alerts import generate_market_pulse_summary

    assets = list(_asset_store.values())
    summary = generate_market_pulse_summary(assets)

    stocks = [a for a in assets if a.get("asset_class") == "stock"]
    crypto = [a for a in assets if a.get("asset_class") == "crypto"]
    fx = [a for a in assets if a.get("asset_class") == "fx"]
    bonds = [a for a in assets if a.get("asset_class") == "bond"]

    stock_avg = sum(a.get("day_change_pct", 0) for a in stocks) / len(stocks) if stocks else 0
    crypto_avg = sum(a.get("day_change_pct", 0) for a in crypto) / len(crypto) if crypto else 0

    return {
        "summary": summary,
        "stock_avg_change": round(stock_avg, 2),
        "crypto_avg_change": round(crypto_avg, 2),
        "asset_counts": {
            "stocks": len(stocks),
            "crypto": len(crypto),
            "fx": len(fx),
            "bonds": len(bonds),
        },
        "top_gainers": sorted(assets, key=lambda x: x.get("day_change_pct", 0), reverse=True)[:3],
        "top_losers": sorted(assets, key=lambda x: x.get("day_change_pct", 0))[:3],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/volatility")
def get_volatility_regime(request: Request):
    """Get current market volatility regime."""
    from app.services.market_monitor_algo import detect_volatility_regime
    return detect_volatility_regime()


# ── Alert Endpoints ─────────────────────────────────────────────────

@router.post("/alerts/create")
def create_alert(
    request: Request,
    data: AlertCreateRequest,
    db: Session = Depends(get_db),
):
    """Create a new market alert."""
    user = _get_user(request, db)
    user_id = str(user.id) if user else "anonymous"

    alert = {
        "id": str(__import__("uuid").uuid4()),
        "user_id": user_id,
        "symbol": data.symbol.upper(),
        "alert_type": data.alert_type,
        "condition": data.condition,
        "threshold": data.threshold,
        "delivery_channels": data.delivery_channels,
        "repeat": data.repeat,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _alert_store.append(alert)

    return {"status": "created", "alert": alert}


@router.get("/alerts")
def list_alerts(
    request: Request,
    db: Session = Depends(get_db),
):
    """List user's active alerts."""
    user = _get_user(request, db)
    user_id = str(user.id) if user else "anonymous"

    user_alerts = [a for a in _alert_store if a.get("user_id") == user_id]
    return {"alerts": user_alerts, "total": len(user_alerts)}


@router.delete("/alerts/{alert_id}")
def delete_alert(
    request: Request,
    alert_id: str,
    db: Session = Depends(get_db),
):
    """Delete an alert."""
    global _alert_store
    _alert_store = [a for a in _alert_store if a.get("id") != alert_id]
    return {"status": "deleted"}


@router.get("/alerts/history")
def alert_history(
    request: Request,
    db: Session = Depends(get_db),
):
    """Get alert trigger history."""
    return {"history": [], "total": 0}


# ── Watchlist Endpoints ─────────────────────────────────────────────

@router.get("/watchlist")
def get_watchlist(
    request: Request,
    db: Session = Depends(get_db),
):
    """Get user's watchlist with current prices."""
    watchlist_assets = []
    for item in _watchlist:
        asset = _asset_store.get(item["symbol"]) or _asset_store.get(f"CRYPTO:{item['symbol']}") or _asset_store.get(f"FX:{item['symbol']}")
        if asset:
            watchlist_assets.append(asset)
        else:
            watchlist_assets.append({**item, "current_price": 0, "day_change_pct": 0})

    return {"watchlist": watchlist_assets, "total": len(watchlist_assets)}


@router.post("/watchlist/add")
def add_to_watchlist(
    request: Request,
    data: WatchlistAddRequest,
    db: Session = Depends(get_db),
):
    """Add an asset to the watchlist."""
    symbol = data.symbol.upper()
    if not any(w["symbol"] == symbol for w in _watchlist):
        _watchlist.append({
            "symbol": symbol,
            "asset_class": data.asset_class,
            "name": data.name or symbol,
            "added_at": datetime.now(timezone.utc).isoformat(),
        })
    return {"status": "added", "symbol": symbol}


@router.delete("/watchlist/{symbol}")
def remove_from_watchlist(
    request: Request,
    symbol: str,
    db: Session = Depends(get_db),
):
    """Remove an asset from the watchlist."""
    global _watchlist
    _watchlist = [w for w in _watchlist if w["symbol"] != symbol.upper()]
    return {"status": "removed"}


# ── Internal Functions ──────────────────────────────────────────────

def _run_discovery_scoring():
    """Run discovery scoring on all assets."""
    from app.services.market_monitor_algo import score_stock_discovery, score_crypto_discovery

    for symbol, asset in _asset_store.items():
        if asset.get("asset_class") == "stock" and asset.get("current_price", 0) > 0:
            # Simulate discovery scoring with available data
            score = min(100, int(
                (50 if asset.get("day_change_pct", 0) > 3 else 0) +
                (20 if asset.get("volume_24h", 0) > 50_000_000 else 0) +
                (15 if asset.get("market_cap", 0) > 100_000_000_000 else 0) +
                (15 if asset.get("day_change_pct", 0) > 5 else 0)
            ))
            asset["discovery_score"] = score
            asset["classification"] = (
                "rising_star" if score >= 80 else
                "watch" if score >= 60 else
                "monitor" if score >= 40 else
                "quiet"
            )

        elif asset.get("asset_class") == "crypto" and asset.get("current_price", 0) > 0:
            score = min(100, int(
                (30 if abs(asset.get("day_change_pct", 0)) > 5 else 0) +
                (25 if asset.get("volume_24h", 0) > asset.get("market_cap", 1) * 0.1 else 0) +
                (20 if asset.get("day_change_pct", 0) > 10 else 0) +
                (15 if asset.get("market_cap", 0) > 10_000_000_000 else 0) +
                (10 if asset.get("ath", 0) > 0 and asset["current_price"] > asset["ath"] * 0.7 else 0)
            ))
            asset["discovery_score"] = score
            asset["classification"] = (
                "emerging_token" if score >= 70 else
                "watch" if score >= 50 else
                "monitor" if score >= 30 else
                "quiet"
            )

    # Generate insights
    from app.services.market_monitor_alerts import generate_daily_insights
    global _insight_cache
    _insight_cache = generate_daily_insights(list(_asset_store.values()))

    # Generate signals
    global _signal_cache
    _signal_cache = []
    _outcome_signals = []
    for symbol, asset in _asset_store.items():
        change = asset.get("day_change_pct", 0)
        if abs(change) > 5:
            _signal_cache.append({
                "symbol": asset.get("symbol", symbol),
                "signal": "strong_move",
                "direction": "bullish" if change > 0 else "bearish",
                "strength": min(100, int(abs(change) * 10)),
                "detail": f"{'+' if change > 0 else ''}{change:.1f}% today",
            })
            _outcome_signals.append({
                "signal_type": "strong_move",
                "symbol": asset.get("symbol", symbol),
                "direction": "bullish" if change > 0 else "bearish",
                "claim": f"{asset.get('symbol', symbol)} moved {'+' if change > 0 else ''}{change:.1f}% today — momentum continues over 5 days",
                "strength": min(100, int(abs(change) * 10)),
                "asset_class": asset.get("asset_class", "stock"),
                "recorded_price": asset.get("current_price"),
                "metadata": {"detail": f"{change:+.1f}% today"},
            })

    # Record discovery classifications as evaluable signals
    for symbol, asset in _asset_store.items():
        classification = asset.get("classification")
        score = asset.get("discovery_score", 0)
        if not classification or classification in ("quiet", "monitor"):
            continue
        is_crypto = asset.get("asset_class") == "crypto"
        stype = "discovery_crypto" if is_crypto else "discovery_stock"
        claim = (
            f"{asset.get('symbol', symbol)} flagged '{classification}' (score {score}/100) — "
            f"expects meaningful upward movement within 5 days"
        )
        _outcome_signals.append({
            "signal_type": stype,
            "symbol": asset.get("symbol", symbol),
            "direction": "bullish",
            "claim": claim,
            "strength": score,
            "asset_class": asset.get("asset_class", "stock"),
            "recorded_price": asset.get("current_price"),
            "metadata": {"classification": classification, "score": score},
        })

    # Persist to the outcome tracker (dedupes per day internally)
    try:
        from app.services.signal_outcome_tracker import record_batch
        _recorded = record_batch(_outcome_signals)
        if _recorded:
            logger.info("Signal tracker: recorded %d new signals", _recorded)
    except Exception as e:
        logger.debug("Signal tracker recording failed: %s", e)
