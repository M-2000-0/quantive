"""
Global Market & Bubble Detector API

Endpoints:
  GET  /api/v1/global-market/universe       — Full global stock/crypto universe
  GET  /api/v1/global-market/stats          — Universe statistics
  GET  /api/v1/global-market/exchanges      — List all exchanges
  POST /api/v1/global-market/ingest-global   — Ingest from all global exchanges
  POST /api/v1/bubble-detector/scan          — Scan assets for bubble risk
  POST /api/v1/bubble-detector/single       — Check single asset
  GET  /api/v1/bubble-detector/portfolio    — Scan full portfolio
"""
from datetime import datetime, timezone
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

router = APIRouter(prefix="/global-market", tags=["global-market"])


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


# ── In-memory store ─────────────────────────────────────────────────

_global_asset_store = {}


# ── Universe Endpoints ──────────────────────────────────────────────

@router.get("/universe")
def get_universe(request: Request, exchange: Optional[str] = None):
    """Get the full global market universe."""
    from app.services.global_market_universe import get_global_stock_universe, get_crypto_universe

    stock_universe = get_global_stock_universe()
    crypto_universe = get_crypto_universe()

    if exchange:
        filtered = {}
        for k, v in stock_universe.items():
            if exchange.lower() in k.lower():
                filtered[k] = v
        return {"exchanges": filtered, "crypto": crypto_universe}

    return {"exchanges": stock_universe, "crypto": crypto_universe}


@router.get("/stats")
def get_stats(request: Request):
    """Get universe statistics."""
    from app.services.global_market_universe import get_universe_stats
    return get_universe_stats()


@router.get("/exchanges")
def list_exchanges(request: Request):
    """List all tracked exchanges."""
    from app.services.global_market_universe import get_global_stock_universe
    universe = get_global_stock_universe()
    return {
        "exchanges": [
            {
                "name": name,
                "symbol_count": len(symbols),
                "sample_symbols": symbols[:5],
            }
            for name, symbols in universe.items()
        ]
    }


@router.post("/ingest-global")
def ingest_global(
    request: Request,
    exchanges: Optional[list] = None,
    max_per_exchange: int = 10,
):
    """Ingest data from global exchanges (respecting rate limits)."""
    from app.services.global_market_universe import get_global_stock_universe, get_crypto_universe
    from app.services.market_monitor_ingest import fetch_yahoo_quote, fetch_coingecko_top

    universe = get_global_stock_universe()
    results = {"exchanges": {}, "crypto": 0, "total": 0, "errors": []}

    # Ingest stocks by exchange
    for exchange_name, symbols in universe.items():
        if exchanges and not any(e.lower() in exchange_name.lower() for e in exchanges):
            continue

        count = 0
        for symbol in symbols[:max_per_exchange]:
            try:
                quote = fetch_yahoo_quote(symbol)
                if quote and quote.get("price", 0) > 0:
                    _global_asset_store[symbol] = {
                        "symbol": symbol,
                        "name": quote.get("name", symbol),
                        "asset_class": "stock",
                        "exchange": exchange_name,
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
                    count += 1
            except Exception as e:
                results["errors"].append(f"{symbol}: {str(e)[:50]}")

        results["exchanges"][exchange_name] = count
        results["total"] += count

    # Ingest crypto
    try:
        coins = fetch_coingecko_top(30)
        for coin in coins:
            sym = coin["symbol"].upper()
            _global_asset_store[f"CRYPTO:{sym}"] = {
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

    results["total"] += results["crypto"]

    return {
        "status": "completed",
        "results": results,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── Bubble Detector Endpoints ───────────────────────────────────────

bubble_router = APIRouter(prefix="/bubble-detector", tags=["bubble-detector"])


class ScanRequest(BaseModel):
    symbols: Optional[list] = None
    asset_class: Optional[str] = None


class SingleScanRequest(BaseModel):
    symbol: str
    asset_class: str = "stock"
    current_price: float = 0
    previous_close: float = 0
    volume_24h: float = 0
    market_cap: float = 0
    high_52w: float = 0
    low_52w: float = 0
    ath: float = 0
    day_change_pct: float = 0


@bubble_router.post("/scan")
def scan_assets(data: ScanRequest, request: Request):
    """Scan multiple assets for bubble risk."""
    from app.services.bubble_detector import calculate_bubble_risk_score, scan_portfolio_for_bubbles

    # Merge both stores (market_monitor + global_market)
    from app.api.market_monitor_api import _asset_store as monitor_store
    assets = list({**monitor_store, **_global_asset_store}.values())

    if data.symbols:
        assets = [a for a in assets if a.get("symbol") in data.symbols]
    if data.asset_class:
        assets = [a for a in assets if a.get("asset_class") == data.asset_class]

    if not assets:
        return {"error": "No assets found. Run ingestion first.", "total": 0}

    scan = scan_portfolio_for_bubbles(assets)

    # Record high/critical bubble flags in the outcome tracker (bearish claims)
    try:
        from app.services.signal_outcome_tracker import record_batch

        flagged = [
            a for a in (scan.get("results") or [])
            if (a.get("risk_level") or "").lower() in ("high", "critical")
            and (a.get("bubble_score") or 0) >= 50
        ]
        if flagged:
            record_batch([
                {
                    "signal_type": "bubble_flag",
                    "symbol": f.get("symbol", ""),
                    "direction": "bearish",
                    "claim": (
                        f"{f.get('symbol')} flagged {f.get('risk_level')} bubble risk "
                        f"({f.get('bubble_score')}/100) — expects meaningful decline within 20 days"
                    ),
                    "strength": int(f.get("bubble_score") or 0),
                    "asset_class": f.get("asset_class", "stock"),
                    "recorded_price": f.get("current_price") or f.get("price"),
                    "metadata": {"patterns": f.get("patterns_detected", [])[:3]},
                }
                for f in flagged
                if f.get("symbol")
            ])
    except Exception:
        pass

    # Notify subscribed users about high/critical bubble risks (background-safe)
    if request.method == "POST":
        try:
            import asyncio

            flagged = [
                a for a in (scan.get("scan_results") or [])
                if (a.get("risk_level") or "").upper() in ("HIGH", "EXTREME")
                and (a.get("bubble_score") or 0) >= 50
            ]
            if flagged:
                _dispatch_bubble_notifications(flagged)
        except Exception:
            pass

    return scan


def _dispatch_bubble_notifications(flagged: list[dict]):
    """Fire-and-forget bubble notifications to users with alerts enabled."""
    try:
        import asyncio

        from app.services.notification_dispatcher import send_bubble_alert, should_notify

        async def _run():
            from app.database import SessionLocal
            from app.models import User
            from app.models.market_monitor import UserAlert

            db = SessionLocal()
            try:
                # Users who opted into bubble/market alert emails via delivery
                # channels OR their notification settings
                subs = (
                    db.query(User, UserAlert)
                    .join(UserAlert, UserAlert.user_id == User.id)
                    .filter(UserAlert.is_active == True)  # noqa: E712
                    .all()
                )
                notified_users = set()
                for user, alert in subs:
                    if user.id in notified_users:
                        continue
                    channels = (alert.delivery_channels or ["in_app"]) if isinstance(alert.delivery_channels, list) else ["in_app"]

                    # Also honor the user-level notification settings
                    # (email_alerts / sms_alerts / bubble_alerts toggles)
                    settings = {}
                    try:
                        from app.models.user_profile import UserProfile
                        prof = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
                        if prof and isinstance(prof.compliance_constraints, dict):
                            settings = prof.compliance_constraints.get("notification_settings") or {}
                    except Exception:
                        settings = {}

                    bubble_enabled = settings.get("bubble_alerts", True)
                    wants_email = ("email" in channels or settings.get("email_alerts", True)) and bubble_enabled
                    wants_sms = ("sms" in channels or settings.get("sms_alerts", False)) and bubble_enabled

                    notified_users.add(user.id)
                    if not (wants_email or wants_sms):
                        continue

                    for f in flagged[:5]:  # Cap at 5 assets per notification wave
                        if not should_notify(user.id, f"bubble:{f.get('symbol')}"):
                            continue
                        try:
                            await send_bubble_alert(
                                user_id=user.id,
                                user_email=user.email if wants_email else "",
                                symbol=f.get("symbol", ""),
                                asset_name=f.get("name") or f.get("symbol", ""),
                                risk_score=int(f.get("bubble_score") or 0),
                                risk_level=(f.get("risk_level") or "HIGH").lower(),
                                patterns=[
                                    (p.get("name") if isinstance(p, dict) else str(p))
                                    for p in (f.get("pattern_details") or f.get("patterns") or [])[:3]
                                ],
                                indicators=f.get("indicators") or [],
                                user_phone=settings.get("phone_number") or getattr(user, "phone", None),
                                notify_email=wants_email,
                                notify_sms=wants_sms,
                            )
                        except Exception:
                            pass
            finally:
                db.close()

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_run())
        except RuntimeError:
            # No running loop (e.g. sync context) — run a fresh loop in a thread
            import threading

            def _bg():
                asyncio.run(_run())

            threading.Thread(target=_bg, daemon=True).start()
    except Exception as e:
        logging.getLogger("quantive.notifications").debug("Bubble dispatch error: %s", e)


@bubble_router.post("/single")
def scan_single(data: SingleScanRequest, request: Request):
    """Scan a single asset for bubble risk."""
    from app.services.bubble_detector import calculate_bubble_risk_score, get_sentiment_for_symbols

    sentiment = (get_sentiment_for_symbols([data.symbol]) or {}).get(data.symbol.upper())
    result = calculate_bubble_risk_score(
        symbol=data.symbol,
        asset_class=data.asset_class,
        current_price=data.current_price,
        previous_close=data.previous_close,
        volume_24h=data.volume_24h,
        market_cap=data.market_cap,
        high_52w=data.high_52w,
        low_52w=data.low_52w,
        ath=data.ath,
        day_change_pct=data.day_change_pct,
        news_sentiment=sentiment,
    )
    return result


@bubble_router.get("/portfolio")
def scan_portfolio(request: Request, db: Session = Depends(get_db)):
    """Scan user's portfolio for bubble risks."""
    from app.services.bubble_detector import scan_portfolio_for_bubbles

    user = _get_user(request, db)
    if not user:
        return {"error": "Not authenticated"}

    # Get user's instruments
    try:
        from app.models import Portfolio, DebtInstrument
        portfolios = db.query(Portfolio).filter(Portfolio.created_by == user.id).all()
        instruments = []
        for p in portfolios:
            insts = db.query(DebtInstrument).filter(DebtInstrument.portfolio_id == p.id).all()
            for i in insts:
                instruments.append({
                    "symbol": i.name,
                    "asset_class": i.instrument_type or "bond",
                    "current_price": float(i.principal_outstanding),
                    "previous_close": float(i.principal_outstanding) * 0.98,
                    "market_cap": float(i.principal_outstanding),
                    "day_change_pct": -2.0,
                })

        if instruments:
            return scan_portfolio_for_bubbles(instruments)
        return {"message": "No instruments in portfolio", "total": 0}
    except Exception as e:
        return {"error": str(e)}
