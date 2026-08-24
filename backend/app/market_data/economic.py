"""Economic Indicators Fetcher — Free data from World Bank API.

The World Bank API is completely free and requires no API key.

Provides:
- CPI / Inflation rates (FP.CPI.TOTL.ZG)
- GDP growth (NY.GDP.MKTP.KD.ZG)
- Government debt to GDP (GC.DOD.TOTL.GD.ZS)
- Current account balance (BN.CAB.XOKA.GD.ZS)
- Foreign reserves (FI.RES.TOTL.CD)

API docs: https://datahelpdesk.worldbank.org/knowledgebase/articles/898581
"""
import logging
from datetime import datetime, timezone
from typing import Optional

import requests

from app.market_data.cache import TTL_ECONOMIC_INDICATORS, get_cache

logger = logging.getLogger("quantive.market_data.economic")

# World Bank API base
WB_API_BASE = "https://api.worldbank.org/v2"

# Indicator codes
INDICATORS = {
    "inflation_cpi": "FP.CPI.TOTL.ZG",
    "gdp_growth": "NY.GDP.MKTP.KD.ZG",
    "debt_to_gdp": "GC.DOD.TOTL.GD.ZS",
    "current_account": "BN.CAB.XOKA.GD.ZS",
    "reserves_months_imports": "FI.RES.TOTL.MP.ZS",
    "policy_rate": "FR.INR.RINR",
}

# Country codes for sovereign debt context
KEY_COUNTRIES = {
    "US": "United States",
    "GB": "United Kingdom",
    "JP": "Japan",
    "DE": "Germany",
    "FR": "France",
    "CN": "China",
    "IN": "India",
    "BR": "Brazil",
    "ZA": "South Africa",
    "NG": "Nigeria",
    "KE": "Kenya",
    "GH": "Ghana",
    "CO": "Colombia",
    "MX": "Mexico",
    "ID": "Indonesia",
}


def fetch_indicator(
    indicator_code: str,
    country_code: str = "US",
    num_periods: int = 5,
    use_cache: bool = True,
) -> dict:
    """Fetch a single economic indicator from the World Bank.

    Args:
        indicator_code: World Bank indicator code (e.g., "FP.CPI.TOTL.ZG")
        country_code: ISO 2-letter country code
        num_periods: Number of recent data points

    Returns:
        {
            "indicator": "Inflation, CPI",
            "country": "US",
            "country_name": "United States",
            "data": [
                {"year": "2025", "value": 3.2},
                {"year": "2024", "value": 4.1},
                ...
            ],
            "latest_value": 3.2,
            "source": "World Bank",
            "fetched_at": "..."
        }
    """
    cache = get_cache()
    cache_key = f"wb_{indicator_code}_{country_code}"

    if use_cache:
        cached = cache.get(cache_key)
        if cached:
            return cached

    try:
        url = f"{WB_API_BASE}/country/{country_code}/indicator/{indicator_code}"
        params = {
            "format": "json",
            "per_page": num_periods,
            "mrv": num_periods,
        }

        resp = requests.get(url, params=params, timeout=20, headers={"User-Agent": "Quantive/1.0"})
        resp.raise_for_status()
        data = resp.json()

        if not data or len(data) < 2:
            return {"error": f"No data for {indicator_code} in {country_code}"}

        metadata = data[0]
        records = data[1] if len(data) > 1 else []

        data_points = []
        for rec in (records or []):
            if rec.get("value") is not None:
                data_points.append({
                    "year": str(rec.get("date", "")),
                    "value": round(float(rec["value"]), 2),
                })

        result = {
            "indicator": metadata.get("indicator", {}).get("value", indicator_code),
            "indicator_code": indicator_code,
            "country": country_code,
            "country_name": metadata.get("country", {}).get("value", country_code),
            "data": data_points,
            "latest_value": data_points[0]["value"] if data_points else None,
            "latest_year": data_points[0]["year"] if data_points else None,
            "source": "World Bank",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

        cache.set(cache_key, result, TTL_ECONOMIC_INDICATORS)
        return result

    except Exception as e:
        logger.warning(f"World Bank fetch failed for {indicator_code}/{country_code}: {e}")
        return {"error": str(e), "source": "World Bank"}


def fetch_country_snapshot(country_code: str = "US", use_cache: bool = True) -> dict:
    """Fetch a complete economic snapshot for a country.

    Returns inflation, GDP growth, debt-to-GDP, and current account
    in a single response.
    """
    cache = get_cache()
    cache_key = f"wb_snapshot_{country_code}"

    if use_cache:
        cached = cache.get(cache_key)
        if cached:
            return cached

    indicators = {}
    for name, code in INDICATORS.items():
        data = fetch_indicator(code, country_code, num_periods=3, use_cache=use_cache)
        indicators[name] = data

    result = {
        "country": country_code,
        "country_name": KEY_COUNTRIES.get(country_code, country_code),
        "indicators": indicators,
        "summary": _build_summary(indicators),
        "source": "World Bank",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    cache.set(cache_key, result, TTL_ECONOMIC_INDICATORS)
    return result


def fetch_multiple_countries(
    country_codes: Optional[list[str]] = None,
    use_cache: bool = True,
) -> dict:
    """Fetch economic indicators for multiple countries for comparison.

    Default: US, UK, Japan, Germany, China, India, Brazil, South Africa.
    """
    if country_codes is None:
        country_codes = ["US", "GB", "JP", "DE", "CN", "IN", "BR", "ZA"]

    snapshots = {}
    for code in country_codes:
        snapshots[code] = fetch_country_snapshot(code, use_cache)

    return {
        "countries": snapshots,
        "count": len(snapshots),
        "source": "World Bank",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def _build_summary(indicators: dict) -> dict:
    """Build a plain-English summary from indicator data."""
    inflation = indicators.get("inflation_cpi", {}).get("latest_value")
    gdp_growth = indicators.get("gdp_growth", {}).get("latest_value")
    debt_gdp = indicators.get("debt_to_gdp", {}).get("latest_value")

    assessment = "Stable"
    if inflation and inflation > 5:
        assessment = "High inflation risk"
    elif inflation and inflation > 8:
        assessment = "Severe inflation concern"
    elif debt_gdp and debt_gdp > 100:
        assessment = "Elevated debt risk"
    elif gdp_growth and gdp_growth < -1:
        assessment = "Recession risk"

    return {
        "inflation_pct": inflation,
        "gdp_growth_pct": gdp_growth,
        "debt_to_gdp_pct": debt_gdp,
        "assessment": assessment,
    }
