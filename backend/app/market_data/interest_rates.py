"""Interest Rate Fetcher — Free data for benchmark rates.

Free sources (no API keys):
- NY Fed SOFR: https://markets.newyorkfed.org/api/rates/secured/sofr/last/1.json
- NY Fed Treasury rates: https://markets.newyorkfed.org/api/rates/last/1.json
- ECB interest rates: https://data-api.ecb.europa.eu/service/data/FM/D.U2.EUR.4F.KR.MRR_FR.LEV?
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import requests

from app.market_data.cache import TTL_INTEREST_RATES, get_cache

logger = logging.getLogger("quantive.market_data.rates")

# NY Fed API (no key required)
NYFed_SOFR_URL = "https://markets.newyorkfed.org/api/rates/secured/sofr/last/1.json"
NYFed_ALL_RATES_URL = "https://markets.newyorkfed.org/api/rates/last/1.json"

# ECB API (no key required)
ECB_KEY_RATE_URL = "https://data-api.ecb.europa.eu/service/data/FM/D.U2.EUR.4F.KR.MRR_FR.LEV?format=jsondata&lastNObservations=5"


def fetch_sofr(use_cache: bool = True) -> dict:
    """Fetch SOFR (Secured Overnight Financing Rate) from NY Fed.

    SOFR is the primary USD benchmark rate, replacing LIBOR.

    Returns:
        {
            "rate_name": "SOFR",
            "rate_pct": 4.31,
            "date": "2026-08-22",
            "source": "Federal Reserve Bank of New York",
            "fetched_at": "..."
        }
    """
    cache = get_cache()
    cache_key = "rate_sofr"

    if use_cache:
        cached = cache.get(cache_key)
        if cached:
            return cached

    try:
        resp = requests.get(NYFed_SOFR_URL, timeout=15, headers={"User-Agent": "Quantive/1.0"})
        resp.raise_for_status()
        data = resp.json()

        rates = data.get("refRates", [])
        if not rates:
            return _fallback_sofr()

        latest = rates[0]
        rate_pct = float(latest.get("percentRate", 0))
        date_str = latest.get("effectiveDate", "")

        result = {
            "rate_name": "SOFR",
            "rate_pct": rate_pct,
            "date": date_str,
            "source": "Federal Reserve Bank of New York",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

        cache.set(cache_key, result, TTL_INTEREST_RATES)
        return result

    except Exception as e:
        logger.warning(f"SOFR fetch failed: {e}")
        return _fallback_sofr()


def fetch_nyfed_rates(use_cache: bool = True) -> dict:
    """Fetch all NY Fed published rates (SOFR, Fed Funds, Treasury rates).

    Returns multiple benchmark rates in a single call.
    """
    cache = get_cache()
    cache_key = "rates_nyfed_all"

    if use_cache:
        cached = cache.get(cache_key)
        if cached:
            return cached

    try:
        resp = requests.get(NYFed_ALL_RATES_URL, timeout=15, headers={"User-Agent": "Quantive/1.0"})
        resp.raise_for_status()
        data = resp.json()

        rates = {}
        for entry in data.get("refRates", []):
            name = entry.get("type", "unknown")
            rate = entry.get("percentRate")
            if rate:
                rates[name] = {
                    "rate_pct": float(rate),
                    "date": entry.get("effectiveDate", ""),
                }

        result = {
            "source": "Federal Reserve Bank of New York",
            "rates": rates,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

        cache.set(cache_key, result, TTL_INTEREST_RATES)
        return result

    except Exception as e:
        logger.warning(f"NY Fed rates fetch failed: {e}")
        return {"source": "NY Fed (fallback)", "rates": {}, "error": str(e)}


def fetch_ecb_key_rate(use_cache: bool = True) -> dict:
    """Fetch ECB Main Refinancing Operations rate.

    This is the ECB's primary policy rate, equivalent to the Fed Funds rate.

    Returns:
        {
            "rate_name": "ECB MRR",
            "rate_pct": 4.50,
            "date": "2026-08-22",
            "source": "European Central Bank",
            "fetched_at": "..."
        }
    """
    cache = get_cache()
    cache_key = "rate_ecb_mrr"

    if use_cache:
        cached = cache.get(cache_key)
        if cached:
            return cached

    try:
        resp = requests.get(ECB_KEY_RATE_URL, timeout=15, headers={"User-Agent": "Quantive/1.0"})
        resp.raise_for_status()
        data = resp.json()

        datasets = data.get("dataSets", [])
        if not datasets:
            return _fallback_ecb_rate()

        obs = datasets[0].get("series", {}).get("0:0:0:0:0", {}).get("observations", {})
        if obs:
            # Get the latest observation
            latest_key = max(obs.keys())
            rate_val = obs[latest_key][0]

            dims = data.get("structure", {}).get("dimensions", {}).get("observation", [])
            time_dim = dims[0] if dims else {}
            time_values = time_dim.get("values", [])

            date_str = ""
            if int(latest_key) < len(time_values):
                date_str = time_values[int(latest_key)].get("id", "")

            result = {
                "rate_name": "ECB Main Refinancing Rate",
                "rate_pct": float(rate_val),
                "date": date_str,
                "source": "European Central Bank",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }

            cache.set(cache_key, result, TTL_INTEREST_RATES)
            return result

        return _fallback_ecb_rate()

    except Exception as e:
        logger.warning(f"ECB rate fetch failed: {e}")
        return _fallback_ecb_rate()


def fetch_all_benchmark_rates(use_cache: bool = True) -> dict:
    """Fetch all available benchmark interest rates.

    Combines SOFR, NY Fed rates, and ECB rates into a single response.
    """
    cache = get_cache()
    cache_key = "rates_all_benchmarks"

    if use_cache:
        cached = cache.get(cache_key)
        if cached:
            return cached

    sofr = fetch_sofr(use_cache)
    nyfed = fetch_nyfed_rates(use_cache)
    ecb = fetch_ecb_key_rate(use_cache)

    # Merge NY Fed rates
    all_rates = {}
    for name, data in nyfed.get("rates", {}).items():
        all_rates[name] = {
            "rate_pct": data["rate_pct"],
            "date": data.get("date", ""),
            "source": "NY Fed",
        }

    # Add SOFR explicitly
    all_rates["SOFR"] = {
        "rate_pct": sofr.get("rate_pct", 0),
        "date": sofr.get("date", ""),
        "source": "NY Fed",
    }

    # Add ECB
    all_rates["ECB_MRR"] = {
        "rate_pct": ecb.get("rate_pct", 0),
        "date": ecb.get("date", ""),
        "source": "ECB",
    }

    result = {
        "source": "NY Fed + ECB",
        "rates": all_rates,
        "summary": {
            "usd_sofr": sofr.get("rate_pct", 0),
            "eur_ecb": ecb.get("rate_pct", 0),
            "spread_bps": round((sofr.get("rate_pct", 0) - ecb.get("rate_pct", 0)) * 100, 1),
        },
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    cache.set(cache_key, result, TTL_INTEREST_RATES)
    return result


def _fallback_sofr() -> dict:
    return {
        "rate_name": "SOFR",
        "rate_pct": 4.31,
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "source": "Fallback",
        "is_fallback": True,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def _fallback_ecb_rate() -> dict:
    return {
        "rate_name": "ECB Main Refinancing Rate",
        "rate_pct": 4.50,
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "source": "Fallback",
        "is_fallback": True,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
