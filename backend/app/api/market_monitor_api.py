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
import asyncio
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
    notify_email: bool = True
    notify_sms: bool = False


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

        # Enrich crypto assets with DeFi Llama TVL metrics (growth, category, chains)
        try:
            from app.services.defi_tvl import enrich_crypto_assets
            enriched = enrich_crypto_assets(_asset_store)
            results["tvl_enriched"] = enriched
        except Exception as e:
            results["errors"].append(f"TVL enrich: {str(e)[:50]}")

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


@router.get("/defi-tvl")
def get_defi_tvl(
    request: Request,
    limit: int = 15,
    min_tvl: float = 50e6,
    category: Optional[str] = None,
):
    """Top DeFi protocols by 7-day TVL growth (from DeFi Llama).

    Surfaces where capital is flowing now — the input to crypto discovery's
    protocol-growth signal.
    """
    from app.services.defi_tvl import get_top_tvl_movers, _get_protocol_data

    movers = get_top_tvl_movers(limit=limit, min_tvl=min_tvl, category=category)
    data = _get_protocol_data()
    total_protocols = len(data)
    total_tvl = sum(p["tvl"] for p in data.values())

    return {
        "movers": movers,
        "total": len(movers),
        "stats": {
            "protocols_tracked": total_protocols,
            "total_tvl_usd": round(total_tvl, 0),
            "source": "DeFi Llama",
        },
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
        "asset_class": getattr(data, "asset_class", "stock"),
        "alert_type": data.alert_type,
        "condition": data.condition,
        "threshold": data.threshold,
        "delivery_channels": data.delivery_channels,
        "repeat": data.repeat,
        "notify_email": data.notify_email,
        "notify_sms": data.notify_sms,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _alert_store.append(alert)

    # Persist to DB so alert history survives restarts and the bubble
    # dispatcher can find opted-in users by delivery channel.
    try:
        import uuid as _uuid

        from app.models.market_monitor import UserAlert

        db.add(UserAlert(
            id=str(_uuid.uuid4()),
            user_id=user_id,
            alert_type=data.alert_type,
            condition=data.condition,
            threshold=data.threshold,
            is_active=True,
            delivery_channels=data.delivery_channels,
            repeat=data.repeat,
            metadata_json={"symbol": data.symbol.upper()},
        ))
        db.commit()
        alert["persisted"] = True
    except Exception as e:
        logger.debug("Alert persistence failed: %s", e)
        try:
            db.rollback()
        except Exception:
            pass

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
    """Get alert trigger history (in-memory + persisted)."""
    user = _get_user(request, db)
    user_id = str(user.id) if user else "anonymous"
    history = [h for h in _alert_history if h.get("user_id") == user_id]
    return {"history": history[-50:][::-1], "total": len(history)}


# ── Background Alert Checker ─────────────────────────────────────────

_alert_history: list[dict] = []
_bg_task = None


def _evaluate_mm_alert(alert: dict) -> dict | None:
    """Evaluate a market-monitor alert against live store data."""
    symbol = alert.get("symbol", "")
    asset = (
        _asset_store.get(symbol)
        or _asset_store.get(f"CRYPTO:{symbol}")
        or _asset_store.get(f"FX:{symbol}")
        or _asset_store.get(f"BOND:US-{symbol}")
    )
    if not asset:
        return None

    price = asset.get("current_price") or 0
    change = asset.get("day_change_pct") or 0
    atype = alert.get("alert_type", "")
    cond = alert.get("condition", "above")
    threshold = alert.get("threshold", 0)

    fired = False
    value = None
    reason = ""

    if atype == "price_above" and price and price > threshold:
        fired, value = True, price
        reason = f"Price ${price:,.2f} crossed above ${threshold:,.2f}"
    elif atype == "price_below" and price and price < threshold:
        fired, value = True, price
        reason = f"Price ${price:,.2f} dropped below ${threshold:,.2f}"
    elif atype == "price_change_pct" and abs(change) > threshold:
        fired, value = True, change
        reason = f"Price moved {change:+.1f}% (threshold ±{threshold}%)"
    elif atype == "volume_spike" and price and alert.get("_volume_ratio"):
        pass  # volume ratio requires history; handled in service module

    if not fired:
        return None
    return {
        "alert_id": alert.get("id"),
        "user_id": alert.get("user_id"),
        "symbol": symbol,
        "alert_type": atype,
        "trigger_value": value,
        "threshold": threshold,
        "reason": reason,
        "delivery_channels": alert.get("delivery_channels", ["in_app"]),
        "triggered_at": datetime.now(timezone.utc).isoformat(),
    }


async def _mm_alert_check_loop():
    """Evaluate market-monitor alerts every 60s; dispatch via notification service."""
    while True:
        try:
            await asyncio.sleep(60)
            if not _alert_store:
                continue

            for alert in list(_alert_store):
                if not alert.get("is_active"):
                    continue
                if alert.get("triggered") and alert.get("repeat", "once") == "once":
                    continue
                if alert.get("_last_check") and (datetime.now(timezone.utc) - alert["_last_check"]).total_seconds() < 55:
                    continue

                alert["_last_check"] = datetime.now(timezone.utc)
                triggered = _evaluate_mm_alert(alert)
                if not triggered:
                    continue

                alert["triggered"] = True
                alert["triggered_at"] = triggered["triggered_at"]
                _alert_history.append({**triggered, "checked_at": triggered["triggered_at"]})

                # Multi-channel dispatch (WebSocket + email + SMS)
                try:
                    from app.services.notification_dispatcher import send_price_alert, should_notify

                    channels = alert.get("delivery_channels") or ["in_app"]
                    wants_email = "email" in channels or alert.get("notify_email", True)
                    wants_sms = "sms" in channels or alert.get("notify_sms", False)

                    if should_notify(alert.get("user_id", "anon"), f"mm:{alert.get('id')}"):
                        user = _get_user_by_id(alert.get("user_id"))
                        await send_price_alert(
                            user_id=alert.get("user_id", "anon"),
                            user_email=(user.email if user else "") if wants_email else "",
                            symbol=triggered["symbol"],
                            alert_type=triggered["alert_type"],
                            message=triggered["reason"],
                            current_price=triggered.get("trigger_value"),
                            threshold=triggered.get("threshold"),
                            user_phone=(getattr(user, "phone", None) if user else None) if wants_sms else None,
                            notify_email=wants_email,
                            notify_sms=wants_sms,
                        )
                except Exception as e:
                    logger.debug("MM alert dispatch failed: %s", e)
        except Exception as e:
            logger.error(f"MM alert check error: {e}")


def _get_user_by_id(user_id: str):
    if not user_id or user_id == "anonymous":
        return None
    try:
        from app.database import SessionLocal
        from app.models import User

        db = SessionLocal()
        try:
            return db.query(User).filter(User.id == user_id).first()
        finally:
            db.close()
    except Exception:
        return None


def start_mm_alert_checker():
    """Start the market-monitor background alert checker."""
    global _bg_task
    if _bg_task is None:
        try:
            loop = asyncio.get_running_loop()
            _bg_task = loop.create_task(_mm_alert_check_loop())
            logger.info("Market-monitor alert checker started")
        except RuntimeError:
            logger.warning("No running event loop; MM alert checker not started")


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

            # DeFi protocol growth scoring (0-20 pts) — real TVL trends from DeFi Llama
            tvl_score = 0
            try:
                from app.services.defi_tvl import get_tvl_growth_score
                growth = get_tvl_growth_score(symbol.split(":")[-1])
                if growth.get("has_data"):
                    tvl_score = growth["score"]
                    asset["tvl"] = growth.get("tvl")
                    asset["tvl_change_7d"] = growth.get("tvl_change_7d")
                    asset["tvl_category"] = growth.get("category")
                    asset["tvl_chains"] = growth.get("chains", [])
            except Exception:
                pass

            score = min(100, score + tvl_score)
            asset["tvl_growth_score"] = tvl_score

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
