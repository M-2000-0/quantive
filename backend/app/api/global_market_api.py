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
    return scan


@bubble_router.post("/single")
def scan_single(data: SingleScanRequest, request: Request):
    """Scan a single asset for bubble risk."""
    from app.services.bubble_detector import calculate_bubble_risk_score

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
