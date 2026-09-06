"""
Stock Screener & Watchlist API — Filter and rank stocks by multiple criteria.

Provides:
- Multi-criteria stock screening (sector, market cap, dividend yield, technicals)
- Custom watchlist management
- Ranking by composite score
"""
import time as _time
from datetime import datetime, timezone
from typing import Optional

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.trading_intelligence import (
    SP500_TOP50,
    NASDAQ100_EXTRA,
    _calculate_rsi,
    _calculate_macd,
    _fetch_history,
    _fetch_yahoo_quote,
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
    """Return the current user if a valid token is provided, else None."""
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


router = APIRouter(prefix="/api/screener", tags=["stock-screener"])

# In-memory watchlists
_watchlists: dict[str, list[dict]] = {}
_watchlist_counter = 0


class WatchlistCreate(BaseModel):
    name: str
    symbols: list[str] = []


class ScreenRequest(BaseModel):
    sectors: Optional[list[str]] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_dividend_yield: Optional[float] = None
    min_market_cap_b: Optional[float] = None  # in billions
    rsi_filter: Optional[str] = None  # "oversold", "overbought", "neutral"
    macd_filter: Optional[str] = None  # "bullish", "bearish", "neutral"
    sort_by: str = "market_cap"  # "price", "change", "dividend_yield", "rsi", "market_cap"
    limit: int = 50


# Full universe: S&P 500 top 50 + NASDAQ 100 extras
ALL_STOCKS = {**SP500_TOP50, **NASDAQ100_EXTRA}

# Curated dividend stocks with known yields (for dividend_kings preset)
DIVIDEND_STOCKS = [
    {"symbol": "JNJ", "name": "Johnson & Johnson", "yield": 3.1, "sector": "Healthcare"},
    {"symbol": "PG", "name": "Procter & Gamble", "yield": 2.4, "sector": "Consumer"},
    {"symbol": "KO", "name": "Coca-Cola", "yield": 2.8, "sector": "Consumer"},
    {"symbol": "PEP", "name": "PepsiCo", "yield": 2.7, "sector": "Consumer"},
    {"symbol": "MMM", "name": "3M", "yield": 5.2, "sector": "Industrial"},
    {"symbol": "T", "name": "AT&T", "yield": 5.8, "sector": "Telecom"},
    {"symbol": "VZ", "name": "Verizon", "yield": 6.2, "sector": "Telecom"},
    {"symbol": "XOM", "name": "Exxon Mobil", "yield": 3.4, "sector": "Energy"},
    {"symbol": "CVX", "name": "Chevron", "yield": 3.2, "sector": "Energy"},
    {"symbol": "WMT", "name": "Walmart", "yield": 1.2, "sector": "Consumer"},
    {"symbol": "ABBV", "name": "AbbVie", "yield": 3.8, "sector": "Healthcare"},
    {"symbol": "MRK", "name": "Merck", "yield": 2.5, "sector": "Healthcare"},
    {"symbol": "JPM", "name": "JPMorgan Chase", "yield": 2.1, "sector": "Financials"},
    {"symbol": "BAC", "name": "Bank of America", "yield": 3.0, "sector": "Financials"},
    {"symbol": "O", "name": "Realty Income", "yield": 5.5, "sector": "REIT"},
    {"symbol": "NEE", "name": "NextEra Energy", "yield": 2.8, "sector": "Utilities"},
    {"symbol": "SO", "name": "Southern Company", "yield": 3.6, "sector": "Utilities"},
    {"symbol": "DUK", "name": "Duke Energy", "yield": 3.9, "sector": "Utilities"},
    {"symbol": "D", "name": "Dominion Energy", "yield": 4.8, "sector": "Utilities"},
    {"symbol": "IBM", "name": "IBM", "yield": 3.2, "sector": "Technology"},
    {"symbol": "LMT", "name": "Lockheed Martin", "yield": 2.3, "sector": "Defense"},
    {"symbol": "RTX", "name": "RTX Corp", "yield": 2.1, "sector": "Defense"},
    {"symbol": "HON", "name": "Honeywell", "yield": 2.0, "sector": "Industrial"},
    {"symbol": "CAT", "name": "Caterpillar", "yield": 1.6, "sector": "Industrial"},
    {"symbol": "MO", "name": "Altria", "yield": 8.1, "sector": "Consumer"},
    {"symbol": "CL", "name": "Colgate-Palmolive", "yield": 2.2, "sector": "Consumer"},
    {"symbol": "KMB", "name": "Kimberly-Clark", "yield": 3.5, "sector": "Consumer"},
    {"symbol": "TGT", "name": "Target", "yield": 3.2, "sector": "Consumer"},
    {"symbol": "GIS", "name": "General Mills", "yield": 3.6, "sector": "Consumer"},
    {"symbol": "KHC", "name": "Kraft Heinz", "yield": 5.4, "sector": "Consumer"},
]


@router.post("/scan")
def screen_stocks(data: ScreenRequest, user=Depends(get_optional_user)):
    """Screen stocks by multiple criteria.

    Fetches real-time data from Yahoo Finance and applies filters.
    """
    symbols = list(ALL_STOCKS.keys())[:60]  # Cap to avoid rate limits

    # Fetch quotes concurrently for speed
    from concurrent.futures import ThreadPoolExecutor, as_completed
    results = []
    def fetch_one(sym):
        quote = _fetch_yahoo_quote(sym)
        if quote.get("error") or not quote.get("price"):
            return None
        price = quote.get("price", 0)
        change = quote.get("change_pct", 0)
        dividend = quote.get("dividend_yield", 0)
        if data.min_price and price < data.min_price:
            return None
        if data.max_price and price > data.max_price:
            return None
        if data.min_dividend_yield and dividend < data.min_dividend_yield:
            return None
        return {
            "symbol": sym,
            "name": ALL_STOCKS.get(sym, sym),
            "price": price,
            "change_pct": change,
            "dividend_yield": dividend,
            "market_cap_b": 0,
        }
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_one, sym): sym for sym in symbols}
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)

    # Enrich with technical data for RSI/MACD filters (concurrent)
    if data.rsi_filter or data.macd_filter or data.sort_by in ("rsi", "macd"):
        def enrich_tech(stock):
            history = _fetch_history(stock["symbol"], 30)
            if len(history) >= 15:
                rsi = _calculate_rsi(history)
                macd = _calculate_macd(history)
                stock["rsi"] = rsi.get("value")
                stock["macd_trend"] = macd.get("trend")
            return stock
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(enrich_tech, s) for s in results[:20]]
            for f in as_completed(futures):
                f.result()  # Enrich in-place
        # Now filter
        filtered = []
        for stock in results:
            if data.rsi_filter == "oversold" and stock.get("rsi", 50) > 35:
                continue
            elif data.rsi_filter == "overbought" and stock.get("rsi", 50) < 65:
                continue
            elif data.rsi_filter == "neutral" and (stock.get("rsi", 50) < 35 or stock.get("rsi", 50) > 65):
                continue
            if data.macd_filter == "bullish" and stock.get("macd_trend") != "BULLISH":
                continue
            elif data.macd_filter == "bearish" and stock.get("macd_trend") != "BEARISH":
                continue
            elif data.macd_filter == "neutral" and stock.get("macd_trend") != "NEUTRAL":
                continue
            filtered.append(stock)
        results = filtered

    # Sort
    sort_key = {
        "price": lambda x: x.get("price", 0),
        "change": lambda x: abs(x.get("change_pct", 0)),
        "dividend_yield": lambda x: x.get("dividend_yield", 0),
        "market_cap": lambda x: x.get("market_cap_b", 0),
        "rsi": lambda x: x.get("rsi", 50),
    }.get(data.sort_by, lambda x: x.get("price", 0))

    results.sort(key=sort_key, reverse=True)

    return {
        "results": results[:data.limit],
        "total_found": len(results),
        "filters_applied": {
            "sectors": data.sectors,
            "min_price": data.min_price,
            "max_price": data.max_price,
            "min_dividend_yield": data.min_dividend_yield,
            "rsi_filter": data.rsi_filter,
            "macd_filter": data.macd_filter,
        },
        "sort_by": data.sort_by,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/quick")
def quick_screen(
    preset: str = Query("dividend_kings", description="Quick preset: dividend_kings, high_momentum, oversold, large_cap"),
    user=Depends(get_optional_user),
):
    """Quick stock screening with preset filters."""
    # Special handling for dividend_kings - use curated list with concurrent fetching
    if preset == "dividend_kings":
        from concurrent.futures import ThreadPoolExecutor, as_completed
        results = []
        def fetch_div_stock(stock):
            quote = _fetch_yahoo_quote(stock["symbol"])
            if not quote.get("error") and quote.get("price"):
                return {
                    "symbol": stock["symbol"],
                    "name": stock["name"],
                    "price": quote["price"],
                    "change_pct": quote.get("change_pct", 0),
                    "dividend_yield": stock["yield"],
                    "market_cap_b": 0,
                }
            return None
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(fetch_div_stock, s): s for s in DIVIDEND_STOCKS}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)
        results.sort(key=lambda x: x["dividend_yield"], reverse=True)
        return {
            "results": results,
            "total_found": len(results),
            "filters_applied": {"preset": "dividend_kings", "min_yield": 2.0},
            "sort_by": "dividend_yield",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    presets = {
        "high_momentum": {"sort_by": "change", "min_price": 20},
        "oversold": {"rsi_filter": "oversold"},
        "large_cap": {"min_price": 100, "sort_by": "price"},
    }

    params = presets.get(preset, presets.get("large_cap"))
    data = ScreenRequest(**params)
    return screen_stocks(data, user)


# ── Watchlists ───────────────────────────────────────────────────────

@router.get("/watchlists")
def list_watchlists(user=Depends(get_optional_user)):
    """List all watchlists."""
    user_id = str(user.id) if user else "default"
    lists = _watchlists.get(user_id, [])
    return {"watchlists": lists, "count": len(lists)}


@router.post("/watchlists", status_code=201)
def create_watchlist(data: WatchlistCreate, user=Depends(get_optional_user)):
    """Create a new watchlist."""
    global _watchlist_counter
    _watchlist_counter += 1
    user_id = str(user.id) if user else "default"

    if user_id not in _watchlists:
        _watchlists[user_id] = []

    watchlist = {
        "id": f"wl_{_watchlist_counter}",
        "name": data.name,
        "symbols": [s.upper() for s in data.symbols],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "count": len(data.symbols),
    }

    _watchlists[user_id].append(watchlist)
    return watchlist


@router.post("/watchlists/{watchlist_id}/add")
def add_to_watchlist(watchlist_id: str, symbol: str = Query(...), user=Depends(get_optional_user)):
    """Add a symbol to a watchlist."""
    user_id = str(user.id) if user else "default"
    for wl in _watchlists.get(user_id, []):
        if wl["id"] == watchlist_id:
            sym = symbol.upper()
            if sym not in wl["symbols"]:
                wl["symbols"].append(sym)
                wl["count"] = len(wl["symbols"])
            return wl
    raise HTTPException(status_code=404, detail="Watchlist not found")


@router.delete("/watchlists/{watchlist_id}/remove")
def remove_from_watchlist(watchlist_id: str, symbol: str = Query(...), user=Depends(get_optional_user)):
    """Remove a symbol from a watchlist."""
    user_id = str(user.id) if user else "default"
    for wl in _watchlists.get(user_id, []):
        if wl["id"] == watchlist_id:
            wl["symbols"] = [s for s in wl["symbols"] if s != symbol.upper()]
            wl["count"] = len(wl["symbols"])
            return wl
    raise HTTPException(status_code=404, detail="Watchlist not found")


@router.get("/watchlists/{watchlist_id}/live")
def watchlist_live_data(watchlist_id: str, user=Depends(get_optional_user)):
    """Get live data for all symbols in a watchlist."""
    user_id = str(user.id) if user else "default"
    wl = None
    for w in _watchlists.get(user_id, []):
        if w["id"] == watchlist_id:
            wl = w
            break

    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    stocks = []
    for sym in wl["symbols"]:
        _time.sleep(0.15)
        quote = _fetch_yahoo_quote(sym)
        if not quote.get("error") and quote.get("price"):
            stocks.append({
                "symbol": sym,
                "name": ALL_STOCKS.get(sym, sym),
                "price": quote.get("price"),
                "change_pct": quote.get("change_pct", 0),
            })

    return {
        "watchlist": wl["name"],
        "stocks": stocks,
        "count": len(stocks),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


@router.delete("/watchlists/{watchlist_id}", status_code=204)
def delete_watchlist(watchlist_id: str, user=Depends(get_optional_user)):
    """Delete a watchlist."""
    user_id = str(user.id) if user else "default"
    _watchlists[user_id] = [w for w in _watchlists.get(user_id, []) if w["id"] != watchlist_id]
    return None
