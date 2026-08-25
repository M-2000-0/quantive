"""Yield Curve Fetcher — Free data from US Treasury.gov.

Fetches daily Treasury yield curve rates from:
- https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/all/

Returns par yields for maturities: 1M, 2M, 3M, 4M, 6M, 1Y, 2Y, 3Y, 5Y, 7Y, 10Y, 20Y, 30Y

No API key required — this is public US government data.
"""
import csv
import io
import logging
from datetime import date, datetime, timezone
from typing import Optional

import requests

from app.market_data.cache import TTL_YIELD_CURVE, get_cache

logger = logging.getLogger("quantive.market_data.yield_curve")

# Treasury.gov CSV endpoint (current year)
TREASURY_CSV_URL = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/all/{year}?type=daily_treasury_yield_curve&field_tdr_date_value={year}&page&_format=csv"

# Maturity labels mapping
TREASURY_MATURITIES = [
    ("BC_1MONTH", "1M", 1/12),
    ("BC_2MONTH", "2M", 2/12),
    ("BC_3MONTH", "3M", 3/12),
    ("BC_4MONTH", "4M", 4/12),
    ("BC_6MONTH", "6M", 6/12),
    ("BC_1YEAR", "1Y", 1),
    ("BC_2YEAR", "2Y", 2),
    ("BC_3YEAR", "3Y", 3),
    ("BC_5YEAR", "5Y", 5),
    ("BC_7YEAR", "7Y", 7),
    ("BC_10YEAR", "10Y", 10),
    ("BC_20YEAR", "20Y", 20),
    ("BC_30YEAR", "30Y", 30),
]


def fetch_treasury_yield_curve(
    target_date: Optional[str] = None,
    use_cache: bool = True,
) -> dict:
    """Fetch the US Treasury yield curve.

    Args:
        target_date: Date in YYYY-MM-DD format. None = latest available.
        use_cache: Whether to use cached data

    Returns:
        {
            "date": "2026-08-22",
            "source": "US Treasury",
            "currency": "USD",
            "maturities": [
                {"label": "1M", "years": 0.083, "rate_pct": 4.35},
                {"label": "3M", "years": 0.25, "rate_pct": 4.42},
                ...
                {"label": "30Y", "years": 30, "rate_pct": 4.68},
            ],
            "2y10y_spread_bps": 33,
            "fetched_at": "2026-08-24T10:00:00Z"
        }
    """
    cache = get_cache()
    cache_key = f"yield_curve_usd_{target_date or 'latest'}"

    if use_cache:
        cached = cache.get(cache_key)
        if cached:
            return cached

    try:
        year = date.today().year
        url = TREASURY_CSV_URL.format(year=year)

        resp = requests.get(url, timeout=30, headers={"User-Agent": "Quantive/1.0"})
        resp.raise_for_status()

        # Parse CSV
        reader = csv.DictReader(io.StringIO(resp.text))
        rows = list(reader)

        if not rows:
            return _fallback_yield_curve()

        # Find the target row or use the latest
        target_row = None
        if target_date:
            for row in rows:
                if row.get("Date", "") == target_date:
                    target_row = row
                    break
        if not target_row:
            target_row = rows[-1]  # Latest

        # Parse yields
        maturities = []
        rates = {}
        for csv_col, label, years in TREASURY_MATURITIES:
            val = target_row.get(csv_col, "")
            try:
                rate = float(val)
                rates[label] = rate
                maturities.append({
                    "label": label,
                    "years": years,
                    "rate_pct": rate,
                })
            except (ValueError, TypeError):
                pass

        # Calculate 2s10s spread
        spread_bps = None
        if "2Y" in rates and "10Y" in rates:
            spread_bps = round((rates["10Y"] - rates["2Y"]) * 100, 1)

        # Parse the date
        raw_date = target_row.get("Date", "")
        try:
            parsed_date = datetime.strptime(raw_date, "%m/%d/%Y").strftime("%Y-%m-%d")
        except ValueError:
            parsed_date = raw_date

        result = {
            "date": parsed_date,
            "source": "US Treasury",
            "currency": "USD",
            "maturities": maturities,
            "2y10y_spread_bps": spread_bps,
            "total_instruments": len(maturities),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

        cache.set(cache_key, result, TTL_YIELD_CURVE)
        return result

    except Exception as e:
        logger.warning(f"Treasury yield curve fetch failed: {e}")
        return _fallback_yield_curve()


def fetch_yield_curve_comparison(
    use_cache: bool = True,
) -> dict:
    """Fetch current yield curve vs 1 month and 1 year ago for comparison.

    Useful for showing yield curve flattening/inversion trends.
    """
    cache = get_cache()
    cache_key = "yield_curve_comparison"

    if use_cache:
        cached = cache.get(cache_key)
        if cached:
            return cached

    try:
        year = date.today().year
        url = TREASURY_CSV_URL.format(year=year)
        resp = requests.get(url, timeout=30, headers={"User-Agent": "Quantive/1.0"})
        resp.raise_for_status()

        reader = csv.DictReader(io.StringIO(resp.text))
        rows = list(reader)

        if len(rows) < 20:
            return {"error": "Insufficient historical data"}

        # Current (latest)
        current = rows[-1]
        # ~1 month ago
        month_ago = rows[-22] if len(rows) > 22 else rows[0]
        # ~1 year ago (same index from a year of data)
        year_ago_url = TREASURY_CSV_URL.format(year=year - 1)
        try:
            year_resp = requests.get(year_ago_url, timeout=30, headers={"User-Agent": "Quantive/1.0"})
            year_resp.raise_for_status()
            year_rows = list(csv.DictReader(io.StringIO(year_resp.text)))
            year_ago = year_rows[-1] if year_rows else None
        except Exception:
            year_ago = None

        def _parse_row(row):
            maturities = {}
            for csv_col, label, years in TREASURY_MATURITIES:
                try:
                    maturities[label] = float(row.get(csv_col, 0) or 0)
                except (ValueError, TypeError):
                    maturities[label] = 0
            return maturities

        result = {
            "current": {"date": current.get("Date", ""), "rates": _parse_row(current)},
            "one_month_ago": {"date": month_ago.get("Date", ""), "rates": _parse_row(month_ago)},
            "one_year_ago": {"date": year_ago.get("Date", ""), "rates": _parse_row(year_ago)} if year_ago else None,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

        cache.set(cache_key, result, TTL_YIELD_CURVE)
        return result

    except Exception as e:
        logger.warning(f"Yield curve comparison fetch failed: {e}")
        return {"error": str(e)}


def _fallback_yield_curve() -> dict:
    """Fallback yield curve with typical values when API is unavailable."""
    return {
        "date": date.today().isoformat(),
        "source": "US Treasury (fallback)",
        "currency": "USD",
        "maturities": [
            {"label": "1M", "years": 1/12, "rate_pct": 4.35},
            {"label": "3M", "years": 3/12, "rate_pct": 4.42},
            {"label": "6M", "years": 6/12, "rate_pct": 4.38},
            {"label": "1Y", "years": 1, "rate_pct": 4.25},
            {"label": "2Y", "years": 2, "rate_pct": 4.15},
            {"label": "3Y", "years": 3, "rate_pct": 4.10},
            {"label": "5Y", "years": 5, "rate_pct": 4.12},
            {"label": "7Y", "years": 7, "rate_pct": 4.20},
            {"label": "10Y", "years": 10, "rate_pct": 4.30},
            {"label": "20Y", "years": 20, "rate_pct": 4.55},
            {"label": "30Y", "years": 30, "rate_pct": 4.68},
        ],
        "2y10y_spread_bps": 15.0,
        "total_instruments": 11,
        "is_fallback": True,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
