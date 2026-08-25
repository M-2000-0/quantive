"""FX Rates Fetcher — Free data from ECB and Yahoo Finance.

Two sources (no API keys):
1. ECB Statistical Data Warehouse: EUR/USD, EUR/GBP, EUR/JPY, etc. (XML RSS)
2. Yahoo Finance direct HTTP: Any currency pair (v8 finance API)

ECB updates daily around 16:00 CET.
"""
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import requests

from app.market_data.cache import TTL_FX_RATES, get_cache

logger = logging.getLogger("quantive.market_data.fx")

# ECB RSS feed for euro exchange rates
ECB_RSS_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"
ECB_RSS_DAILY = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"

# Yahoo Finance v8 API (no key needed)
YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

# Common currency pairs for sovereign debt
KEY_CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "CNY", "INR", "BRL"]


def fetch_ecb_rates(use_cache: bool = True) -> dict:
    """Fetch EUR exchange rates from ECB (free, no API key).

    Returns:
        {
            "base": "EUR",
            "date": "2026-08-22",
            "source": "European Central Bank",
            "rates": {
                "USD": 1.0845,
                "GBP": 0.8562,
                "JPY": 161.23,
                ...
            },
            "fetched_at": "..."
        }
    """
    cache = get_cache()
    cache_key = "fx_ecb_rates"

    if use_cache:
        cached = cache.get(cache_key)
        if cached:
            return cached

    try:
        resp = requests.get(ECB_RSS_DAILY, timeout=15, headers={"User-Agent": "Quantive/1.0"})
        resp.raise_for_status()

        root = ET.fromstring(resp.text)

        # Parse XML — ECB uses Cube elements
        rates = {}
        date_str = ""

        for cube in root.iter():
            if cube.tag == "{http://www.ecb.int/vocabulary/2002-08-01/eurofxref}Cube":
                time_attr = cube.get("time")
                if time_attr:
                    date_str = time_attr
                currency = cube.get("currency")
                rate = cube.get("rate")
                if currency and rate:
                    rates[currency] = float(rate)

        # Add EUR = 1.0
        rates["EUR"] = 1.0

        result = {
            "base": "EUR",
            "date": date_str,
            "source": "European Central Bank",
            "rates": rates,
            "total_currencies": len(rates),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

        cache.set(cache_key, result, TTL_FX_RATES)
        return result

    except Exception as e:
        logger.warning(f"ECB rates fetch failed: {e}")
        return _fallback_fx_rates()


def fetch_yahoo_fx(
    base: str = "USD",
    quote: str = "EUR",
    use_cache: bool = True,
) -> dict:
    """Fetch FX rate from Yahoo Finance (free, no API key).

    Args:
        base: Base currency (e.g., "USD")
        quote: Quote currency (e.g., "EUR")

    Returns:
        {
            "pair": "USDEUR",
            "rate": 0.9218,
            "source": "Yahoo Finance",
            "fetched_at": "..."
        }
    """
    cache = get_cache()
    cache_key = f"fx_yahoo_{base}{quote}"

    if use_cache:
        cached = cache.get(cache_key)
        if cached:
            return cached

    try:
        symbol = f"{base}{quote}=X"
        url = YAHOO_QUOTE_URL.format(symbol=symbol)
        params = {"interval": "1d", "range": "1d"}
        headers = {"User-Agent": "Mozilla/5.0 (compatible; Quantive/1.0)"}

        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        chart = data.get("chart", {}).get("result", [])
        if not chart:
            return {"error": f"No data for {base}/{quote}"}

        meta = chart[0].get("meta", {})
        rate = meta.get("regularMarketPrice", 0)

        result = {
            "pair": f"{base}{quote}",
            "rate": rate,
            "source": "Yahoo Finance",
            "previous_close": meta.get("chartPreviousClose", 0),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

        cache.set(cache_key, result, TTL_FX_RATES)
        return result

    except Exception as e:
        logger.warning(f"Yahoo FX fetch failed for {base}/{quote}: {e}")
        return {"error": str(e)}


def fetch_all_key_rates(use_cache: bool = True) -> dict:
    """Fetch all key currency rates against USD.

    Uses ECB as primary source, Yahoo Finance as fallback.
    Returns rates as USD/XXX (direct quote from USD perspective).
    """
    cache = get_cache()
    cache_key = "fx_all_key_rates"

    if use_cache:
        cached = cache.get(cache_key)
        if cached:
            return cached

    # Try ECB first (EUR-based)
    ecb = fetch_ecb_rates(use_cache)
    ecb_rates = ecb.get("rates", {})

    usd_to_eur = ecb_rates.get("USD", 1.08)
    usd_base_rates = {}

    for ccy in KEY_CURRENCIES:
        if ccy == "USD":
            usd_base_rates["USD"] = 1.0
        elif ccy == "EUR":
            usd_base_rates["EUR"] = 1.0 / usd_to_eur if usd_to_eur else 0
        else:
            eur_to_ccy = ecb_rates.get(ccy)
            if eur_to_ccy:
                # Convert EUR/XXX to USD/XXX
                usd_base_rates[ccy] = eur_to_ccy / usd_to_eur if usd_to_eur else 0
            else:
                # Fallback to Yahoo Finance
                try:
                    yahoo = fetch_yahoo_fx("USD", ccy, use_cache=False)
                    usd_base_rates[ccy] = yahoo.get("rate", 0)
                except Exception:
                    usd_base_rates[ccy] = 0

    result = {
        "base": "USD",
        "date": ecb.get("date", ""),
        "source": ecb.get("source", "ECB + Yahoo Finance"),
        "rates": usd_base_rates,
        "cross_rates": ecb_rates,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    cache.set(cache_key, result, TTL_FX_RATES)
    return result


def _fallback_fx_rates() -> dict:
    """Fallback FX rates when APIs are unavailable."""
    return {
        "base": "EUR",
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "source": "Fallback",
        "rates": {
            "USD": 1.0845, "GBP": 0.8562, "JPY": 161.23, "CHF": 0.9421,
            "CAD": 1.4732, "AUD": 1.6543, "CNY": 7.8234, "INR": 90.45,
            "BRL": 5.3421, "EUR": 1.0,
        },
        "is_fallback": True,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
