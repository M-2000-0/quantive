"""
Live Price Streaming API — Real-time price updates via Server-Sent Events and polling.

Provides:
- SSE endpoint for streaming price updates
- Batch price endpoint for polling (fallback for clients without SSE)
- Watchlist streaming (user-defined symbol lists)
- Price snapshot endpoint
"""
from datetime import datetime, timezone
from typing import Optional

import asyncio
import json
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.market_data.cache import get_cache
from app.api.trading_intelligence import (
    _fetch_yahoo_quote,
    SP500_TOP50,
    NASDAQ100_EXTRA,
    SECTOR_ETFS,
    MAJOR_ETFS,
    TTL_STOCK_PRICES,
)
from app.security import get_current_user
from typing import Optional
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User

_optional_bearer = HTTPBearer(auto_error=False)


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(_optional_bearer),
    db: Session = Depends(get_db),
) -> Optional[User]:
    if credentials is None:
        return None
    try:
        from app.security import decode_token
        payload = decode_token(credentials.credentials)
        if payload:
            uid = payload.get("sub")
            return db.query(User).filter(User.id == uid).first()
    except Exception:
        pass
    return None


router = APIRouter(prefix="/api/streaming", tags=["live-prices"])

# Default watchlist for streaming
DEFAULT_STREAM_SYMBOLS = ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "JNJ"]


@router.get("/prices")
def get_live_prices(
    symbols: str = Query(default=",".join(DEFAULT_STREAM_SYMBOLS), description="Comma-separated symbols"),
    user=Depends(get_optional_user),
):
    """Get current prices for multiple symbols. Use this for polling-based updates."""
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()][:30]
    results = []
    import time
    for sym in symbol_list:
        try:
            time.sleep(0.1)
            quote = _fetch_yahoo_quote(sym)
            if not quote.get("error") and quote.get("price"):
                results.append({
                    "symbol": sym,
                    "price": round(quote["price"], 2),
                    "change": round(quote.get("change", 0) or 0, 2),
                    "change_pct": round(quote.get("change_pct", 0) or 0, 2),
                    "volume": quote.get("volume", 0),
                    "previous_close": quote.get("previous_close", 0),
                })
        except Exception:
            continue

    return {
        "prices": results,
        "count": len(results),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/prices/batch")
def get_batch_prices(
    symbols: str = Query(default=",".join(DEFAULT_STREAM_SYMBOLS), description="Comma-separated symbols"),
    user=Depends(get_optional_user),
):
    """Batch price endpoint optimized for speed — returns cached prices when available."""
    cache = get_cache()
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()][:30]

    cached_key = f"batch_prices_{','.join(sorted(symbol_list))}"
    cached = cache.get(cached_key)
    if cached:
        return cached

    results = []
    import time
    for sym in symbol_list:
        try:
            time.sleep(0.08)
            quote = _fetch_yahoo_quote(sym)
            if not quote.get("error") and quote.get("price"):
                results.append({
                    "symbol": sym,
                    "price": round(quote["price"], 2),
                    "change_pct": round(quote.get("change_pct", 0) or 0, 2),
                })
        except Exception:
            continue

    resp = {
        "prices": results,
        "count": len(results),
        "cached": False,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    cache.set(cached_key, resp, 30)  # Cache for 30 seconds
    return resp


@router.get("/market-snapshot")
def get_market_snapshot(user=Depends(get_optional_user)):
    """Quick market snapshot with key indices and movers."""
    cache = get_cache()
    cached = cache.get("market_snapshot")
    if cached:
        return cached

    from app.api.trading_intelligence import _fetch_yahoo_quote
    import time

    indices = {}
    for sym, name in [("SPY", "S&P 500"), ("QQQ", "NASDAQ 100"), ("IWM", "Russell 2000")]:
        time.sleep(0.1)
        quote = _fetch_yahoo_quote(sym)
        if not quote.get("error") and quote.get("price"):
            indices[sym] = {
                "name": name,
                "price": round(quote["price"], 2),
                "change_pct": round(quote.get("change_pct", 0) or 0, 2),
            }

    resp = {
        "indices": indices,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    cache.set("market_snapshot", resp, 60)
    return resp


@router.get("/sector-snapshot")
def get_sector_snapshot(user=Depends(get_optional_user)):
    """Quick sector rotation snapshot."""
    cache = get_cache()
    cached = cache.get("sector_snapshot")
    if cached:
        return cached

    from app.api.trading_intelligence import _fetch_yahoo_quote
    import time

    sectors = []
    for sym, info in SECTOR_ETFS.items():
        time.sleep(0.1)
        quote = _fetch_yahoo_quote(sym)
        if not quote.get("error") and quote.get("price"):
            change = round(quote.get("change_pct", 0) or 0, 2)
            sectors.append({
                "symbol": sym,
                "name": info["name"],
                "price": round(quote["price"], 2),
                "change_pct": change,
                "signal": "BUY" if change > 0.5 else "SELL" if change < -0.5 else "HOLD",
            })

    sectors.sort(key=lambda s: s["change_pct"], reverse=True)

    resp = {
        "sectors": sectors,
        "leaders": [s["symbol"] for s in sectors[:3]],
        "laggards": [s["symbol"] for s in sectors[-3:]],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    cache.set("sector_snapshot", resp, 120)
    return resp
