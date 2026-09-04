"""
Earnings Calendar API — Track upcoming earnings dates and historical earnings data.

Provides:
- Upcoming earnings dates for major stocks
- Historical earnings data and EPS estimates
- Earnings impact estimation
"""
from datetime import datetime, timezone, timedelta

import requests
from fastapi import APIRouter, Depends, Query

from app.market_data.cache import get_cache
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


router = APIRouter(prefix="/api/earnings", tags=["earnings-calendar"])

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

# Major earnings dates (curated list of tracked companies)
# In production, fetch from Yahoo Finance calendar or SEC EDGAR
TRACKED_EARNINGS = [
    {"symbol": "AAPL", "name": "Apple", "sector": "Technology", "next_date": "2026-10-28", "estimate_eps": 1.65},
    {"symbol": "MSFT", "name": "Microsoft", "sector": "Technology", "next_date": "2026-10-22", "estimate_eps": 3.12},
    {"symbol": "NVDA", "name": "NVIDIA", "sector": "Technology", "next_date": "2026-11-19", "estimate_eps": 0.82},
    {"symbol": "AMZN", "name": "Amazon", "sector": "Consumer", "next_date": "2026-10-30", "estimate_eps": 1.15},
    {"symbol": "GOOGL", "name": "Alphabet", "sector": "Technology", "next_date": "2026-10-29", "estimate_eps": 1.85},
    {"symbol": "META", "name": "Meta Platforms", "sector": "Technology", "next_date": "2026-10-29", "estimate_eps": 5.30},
    {"symbol": "TSLA", "name": "Tesla", "sector": "Consumer", "next_date": "2026-10-22", "estimate_eps": 0.95},
    {"symbol": "JPM", "name": "JPMorgan Chase", "sector": "Financials", "next_date": "2026-10-14", "estimate_eps": 4.15},
    {"symbol": "V", "name": "Visa", "sector": "Financials", "next_date": "2026-10-28", "estimate_eps": 2.58},
    {"symbol": "JNJ", "name": "Johnson & Johnson", "sector": "Healthcare", "next_date": "2026-10-14", "estimate_eps": 2.62},
    {"symbol": "WMT", "name": "Walmart", "sector": "Consumer", "next_date": "2026-11-20", "estimate_eps": 0.53},
    {"symbol": "UNH", "name": "UnitedHealth", "sector": "Healthcare", "next_date": "2026-10-14", "estimate_eps": 7.25},
    {"symbol": "XOM", "name": "Exxon Mobil", "sector": "Energy", "next_date": "2026-10-31", "estimate_eps": 1.82},
    {"symbol": "BAC", "name": "Bank of America", "sector": "Financials", "next_date": "2026-10-15", "estimate_eps": 0.88},
    {"symbol": "HD", "name": "Home Depot", "sector": "Consumer", "next_date": "2026-11-18", "estimate_eps": 3.78},
    {"symbol": "PFE", "name": "Pfizer", "sector": "Healthcare", "next_date": "2026-10-28", "estimate_eps": 0.63},
    {"symbol": "ABBV", "name": "AbbVie", "sector": "Healthcare", "next_date": "2026-10-31", "estimate_eps": 3.12},
    {"symbol": "KO", "name": "Coca-Cola", "sector": "Consumer", "next_date": "2026-10-21", "estimate_eps": 0.74},
    {"symbol": "CRM", "name": "Salesforce", "sector": "Technology", "next_date": "2026-12-03", "estimate_eps": 1.45},
    {"symbol": "NFLX", "name": "Netflix", "sector": "Technology", "next_date": "2026-10-16", "estimate_eps": 5.40},
]


@router.get("/upcoming")
def get_upcoming_earnings(
    days: int = Query(90, description="How many days ahead to look"),
    sector: str = Query(None, description="Filter by sector"),
    user=Depends(get_optional_user),
):
    """Get upcoming earnings dates for tracked stocks."""
    cache = get_cache()
    cache_key = f"earnings_upcoming_{days}_{sector}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    today = datetime.now().date()
    cutoff = today + timedelta(days=days)

    upcoming = []
    for stock in TRACKED_EARNINGS:
        if sector and stock["sector"].lower() != sector.lower():
            continue
        try:
            earnings_date = datetime.strptime(stock["next_date"], "%Y-%m-%d").date()
            if today <= earnings_date <= cutoff:
                days_until = (earnings_date - today).days
                upcoming.append({
                    **stock,
                    "days_until": days_until,
                    "urgency": "this_week" if days_until <= 7 else "this_month" if days_until <= 30 else "upcoming",
                })
        except ValueError:
            continue

    upcoming.sort(key=lambda x: x["days_until"])

    # Group by week
    this_week = [e for e in upcoming if e["urgency"] == "this_week"]
    this_month = [e for e in upcoming if e["urgency"] == "this_month"]
    later = [e for e in upcoming if e["urgency"] == "upcoming"]

    result = {
        "upcoming": upcoming,
        "summary": {
            "total": len(upcoming),
            "this_week": len(this_week),
            "this_month": len(this_month),
            "later": len(later),
        },
        "this_week": this_week,
        "this_month": this_month,
        "sectors": list(set(e["sector"] for e in upcoming)),
        "look_ahead_days": days,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    cache.set(cache_key, result, 30 * 60)
    return result


@router.get("/{symbol}")
def get_stock_earnings(symbol: str, user=Depends(get_optional_user)):
    """Get earnings data for a specific stock."""
    symbol = symbol.upper()
    stock = next((s for s in TRACKED_EARNINGS if s["symbol"] == symbol), None)

    if not stock:
        return {
            "symbol": symbol,
            "found": False,
            "message": "Earnings data not available for this stock",
        }

    today = datetime.now().date()
    try:
        earnings_date = datetime.strptime(stock["next_date"], "%Y-%m-%d").date()
        days_until = (earnings_date - today).days
    except ValueError:
        days_until = -1

    # Estimate potential impact based on sector and historical patterns
    impact = _estimate_earnings_impact(symbol)

    return {
        "symbol": symbol,
        "name": stock["name"],
        "sector": stock["sector"],
        "next_earnings": stock["next_date"],
        "days_until": days_until,
        "estimated_eps": stock["estimate_eps"],
        "impact_estimate": impact,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def _estimate_earnings_impact(symbol: str) -> dict:
    """Estimate potential earnings impact based on sector and patterns."""
    # Historical average moves by sector (simplified model)
    sector_moves = {
        "Technology": {"avg_move": 4.5, "volatility": "high"},
        "Consumer": {"avg_move": 3.2, "volatility": "medium"},
        "Financials": {"avg_move": 2.8, "volatility": "medium"},
        "Healthcare": {"avg_move": 5.1, "volatility": "high"},
        "Energy": {"avg_move": 3.8, "volatility": "medium"},
    }

    stock = next((s for s in TRACKED_EARNINGS if s["symbol"] == symbol), {})
    sector = stock.get("sector", "Technology")
    base = sector_moves.get(sector, {"avg_move": 3.5, "volatility": "medium"})

    return {
        "expected_move_pct": base["avg_move"],
        "volatility": base["volatility"],
        "upside_scenario": f"+{base['avg_move'] * 1.5:.1f}% on beat",
        "downside_scenario": f"-{base['avg_move'] * 1.2:.1f}% on miss",
        "note": "Estimates based on historical sector averages. Actual moves vary.",
    }
