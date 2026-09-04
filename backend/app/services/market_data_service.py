"""
Real Market Data Service — FRED API Integration

Fetches live Treasury yields, economic indicators, and FX rates from
Federal Reserve Economic Data (FRED) with automatic fallback to cached
data when the API is unavailable.

API Key: Set FRED_API_KEY in environment
Free key: https://fred.stlouisfed.org/docs/api/api_key.html
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Optional

import httpx
from pydantic import BaseModel

logger = logging.getLogger("quantive.market_data")

# ── Configuration ─────────────────────────────────────────────────────

FRED_API_KEY = os.environ.get("FRED_API_KEY", "")
FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
CACHE_TTL_SECONDS = 300  # 5 minutes

# FRED Series IDs for Treasury yields
TREASURY_SERIES = {
    "3M": "DTB3",
    "6M": "DTB6",
    "1Y": "DGS1",
    "2Y": "DGS2",
    "3Y": "DGS3",
    "5Y": "DGS5",
    "7Y": "DGS7",
    "10Y": "DGS10",
    "20Y": "DGS20",
    "30Y": "DGS30",
}

# FRED Series IDs for economic indicators
INDICATOR_SERIES = {
    "CPIAUCSL": {"name": "CPI (All Urban Consumers)", "unit": "Index"},
    "UNRATE": {"name": "Unemployment Rate", "unit": "%"},
    "FEDFUNDS": {"name": "Federal Funds Rate", "unit": "%"},
    "DGS10": {"name": "10-Year Treasury Yield", "unit": "%"},
    "T10Y2Y": {"name": "10Y-2Y Spread", "unit": "%"},
    "VIXCLS": {"name": "VIX Volatility Index", "unit": "Index"},
    "DCOILWTICO": {"name": "WTI Crude Oil", "unit": "$/barrel"},
    "GOLDAMGBD228NLBM": {"name": "Gold Price", "unit": "$/oz"},
}

# Note: mock data removed. All data must come from FRED API or live providers.
# If FRED_API_KEY is not set, the service returns empty results with a 'fallback' status.


# ── Models ────────────────────────────────────────────────────────────

class TreasuryYield(BaseModel):
    date: str
    maturity: str
    yield_pct: float
    source: str = "fred"


class EconomicIndicator(BaseModel):
    id: str
    name: str
    value: float
    previous_value: Optional[float] = None
    change: Optional[float] = None
    unit: str
    last_updated: str
    source: str = "fred"


class MarketDataResponse(BaseModel):
    treasury_yields: list[TreasuryYield]
    indicators: list[EconomicIndicator]
    fetched_at: str
    data_fresh: bool
    source_status: str  # "live", "cached", "fallback"


# ── In-Memory Cache ───────────────────────────────────────────────────

_cache: dict[str, tuple[any, float]] = {}


def _get_cached(key: str) -> Optional[any]:
    if key in _cache:
        value, timestamp = _cache[key]
        if time.time() - timestamp < CACHE_TTL_SECONDS:
            return value
        del _cache[key]
    return None


def _set_cache(key: str, value: any) -> None:
    _cache[key] = (value, time.time())


# ── FRED API Client ──────────────────────────────────────────────────

async def _fetch_fred_series(
    series_id: str,
    start_date: str,
    end_date: str,
) -> list[dict]:
    """Fetch observations from FRED API."""
    if not FRED_API_KEY:
        logger.warning("FRED API key not configured")
        return []

    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "observation_start": start_date,
        "observation_end": end_date,
        "sort_order": "desc",
        "limit": "30",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(FRED_BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
            observations = data.get("observations", [])
            # Filter out missing values (FRED uses "." for missing)
            return [
                {"date": obs["date"], "value": float(obs["value"])}
                for obs in observations
                if obs["value"] != "."
            ]
    except httpx.HTTPStatusError as e:
        logger.error(f"FRED API HTTP error for {series_id}: {e.response.status_code}")
        return []
    except Exception as e:
        logger.error(f"FRED API error for {series_id}: {e}")
        return []


# ── Public API ────────────────────────────────────────────────────────

async def get_treasury_yields() -> list[TreasuryYield]:
    """Get current Treasury yield curve."""
    cache_key = "treasury_yields"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    results = []
    source = "fred"

    for maturity, series_id in TREASURY_SERIES.items():
        observations = await _fetch_fred_series(series_id, start_date, end_date)

        if observations:
            latest = observations[0]
            results.append(TreasuryYield(
                date=latest["date"],
                maturity=maturity,
                yield_pct=latest["value"],
                source="fred",
            ))
        else:
            # FRED API key not configured or series returned no data
            # Return empty — no mock data
            source = "no_api_key" if not FRED_API_KEY else source

    _set_cache(cache_key, results)
    return results


async def get_economic_indicators() -> list[EconomicIndicator]:
    """Get current economic indicators."""
    cache_key = "economic_indicators"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")

    results = []

    for series_id, info in INDICATOR_SERIES.items():
        observations = await _fetch_fred_series(series_id, start_date, end_date)

        if observations and len(observations) >= 2:
            current = observations[0]["value"]
            previous = observations[1]["value"]
            results.append(EconomicIndicator(
                id=series_id,
                name=info["name"],
                value=current,
                previous_value=previous,
                change=round(current - previous, 4),
                unit=info["unit"],
                last_updated=observations[0]["date"],
                source="fred",
            ))
        # If FRED returned no data and no API key, skip this indicator
        # No mock data fallback — data must be real

    _set_cache(cache_key, results)
    return results


async def get_market_snapshot() -> MarketDataResponse:
    """Get complete market data snapshot."""
    treasury_yields = await get_treasury_yields()
    indicators = await get_economic_indicators()

    # Determine data freshness and source
    has_live = any(y.source == "fred" for y in treasury_yields)
    has_fallback = any(y.source == "fallback" for y in treasury_yields)

    if has_live and not has_fallback:
        source_status = "live"
        data_fresh = True
    elif has_live and has_fallback:
        source_status = "partial"
        data_fresh = True
    else:
        source_status = "fallback"
        data_fresh = False

    return MarketDataResponse(
        treasury_yields=treasury_yields,
        indicators=indicators,
        fetched_at=datetime.now().isoformat(),
        data_fresh=data_fresh,
        source_status=source_status,
    )


async def get_health_status() -> dict:
    """Check market data service health."""
    cache_stats = {
        "entries": len(_cache),
        "ttl_seconds": CACHE_TTL_SECONDS,
    }

    fred_configured = bool(FRED_API_KEY)

    return {
        "status": "healthy" if fred_configured else "degraded",
        "fred_api_configured": fred_configured,
        "cache": cache_stats,
        "last_check": datetime.now().isoformat(),
    }
