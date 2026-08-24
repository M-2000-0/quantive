"""Live Market Data API — Free sources, no API keys required.

Endpoints:
- GET /api/market/yield-curve — US Treasury yield curve
- GET /api/market/yield-curve/comparison — Current vs historical
- GET /api/market/fx — FX exchange rates
- GET /api/market/fx/{pair} — Specific currency pair
- GET /api/market/rates — Benchmark interest rates (SOFR, ECB, etc.)
- GET /api/market/economic/{country} — Country economic snapshot
- GET /api/market/snapshot — Complete market snapshot
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.market_data import economic, fx_rates, interest_rates, yield_curve
from app.market_data.cache import get_cache
from app.models import User
from app.security import get_current_user

router = APIRouter(prefix="/api/market", tags=["market-data"])


@router.get("/yield-curve")
def get_yield_curve(
    date: str = Query(None, description="Date YYYY-MM-DD (default: latest)"),
    user: User = Depends(get_current_user),
):
    """Fetch the current US Treasury yield curve.

    Free data from Treasury.gov — updated daily.
    Shows par yields for 1M through 30Y maturities.
    """
    return yield_curve.fetch_treasury_yield_curve(target_date=date)


@router.get("/yield-curve/comparison")
def get_yield_curve_comparison(user: User = Depends(get_current_user)):
    """Compare current yield curve vs 1 month and 1 year ago.

    Shows yield curve flattening/inversion trends.
    """
    return yield_curve.fetch_yield_curve_comparison()


@router.get("/fx")
def get_fx_rates(
    base: str = Query("USD", description="Base currency"),
    user: User = Depends(get_current_user),
):
    """Fetch key exchange rates against a base currency.

    Uses ECB data (free, no key) as primary source.
    Returns rates for USD, EUR, GBP, JPY, CHF, CAD, AUD, CNY, INR, BRL.
    """
    if base.upper() == "USD":
        return fx_rates.fetch_all_key_rates()
    else:
        ecb = fx_rates.fetch_ecb_rates()
        # Convert EUR-based to requested base
        rates = ecb.get("rates", {})
        base_to_eur = rates.get(base.upper(), 1.0)
        converted = {}
        for ccy, eur_rate in rates.items():
            if base.upper() == "EUR":
                converted[ccy] = eur_rate
            elif base_to_eur:
                converted[ccy] = eur_rate / base_to_eur
            else:
                converted[ccy] = 0

        return {
            "base": base.upper(),
            "date": ecb.get("date", ""),
            "source": ecb.get("source", "ECB"),
            "rates": converted,
            "fetched_at": ecb.get("fetched_at", ""),
        }


@router.get("/fx/{pair}")
def get_fx_pair(
    pair: str,
    user: User = Depends(get_current_user),
):
    """Fetch a specific FX pair rate (e.g., USD/EUR, GBP/JPY).

    Uses Yahoo Finance (free, no key).
    """
    if len(pair) != 6:
        raise HTTPException(status_code=422, detail="Pair must be 6 characters, e.g., USDEUR")
    base = pair[:3].upper()
    quote = pair[3:].upper()
    return fx_rates.fetch_yahoo_fx(base, quote)


@router.get("/rates")
def get_interest_rates(user: User = Depends(get_current_user)):
    """Fetch all benchmark interest rates.

    Includes: SOFR, Fed Funds, ECB MRR, and other benchmark rates.
    Free data from NY Fed and ECB.
    """
    return interest_rates.fetch_all_benchmark_rates()


@router.get("/rates/sofr")
def get_sofr(user: User = Depends(get_current_user)):
    """Fetch the current SOFR rate.

    SOFR (Secured Overnight Financing Rate) is the primary USD benchmark.
    Free data from the Federal Reserve Bank of New York.
    """
    return interest_rates.fetch_sofr()


@router.get("/rates/ecb")
def get_ecb_rate(user: User = Depends(get_current_user)):
    """Fetch the ECB Main Refinancing Rate.

    The ECB's primary policy rate.
    Free data from the European Central Bank.
    """
    return interest_rates.fetch_ecb_key_rate()


@router.get("/economic/{country_code}")
def get_economic_snapshot(
    country_code: str,
    user: User = Depends(get_current_user),
):
    """Fetch an economic snapshot for a country.

    Includes: inflation, GDP growth, debt-to-GDP, current account.
    Free data from the World Bank API.
    """
    country_code = country_code.upper()
    return economic.fetch_country_snapshot(country_code)


@router.get("/economic")
def get_economic_comparison(
    countries: str = Query("US,GB,JP,DE,CN,IN,BR,ZA", description="Comma-separated country codes"),
    user: User = Depends(get_current_user),
):
    """Compare economic indicators across multiple countries."""
    codes = [c.strip().upper() for c in countries.split(",") if c.strip()]
    return economic.fetch_multiple_countries(codes)


@router.get("/snapshot")
def get_market_snapshot(user: User = Depends(get_current_user)):
    """Get a complete market data snapshot.

    Combines yield curve, FX rates, interest rates, and key economic data
    into a single response. Ideal for dashboards.
    """
    return {
        "yield_curve": yield_curve.fetch_treasury_yield_curve(),
        "fx_rates": fx_rates.fetch_all_key_rates(),
        "interest_rates": interest_rates.fetch_all_benchmark_rates(),
        "fetched_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }


@router.get("/cache/stats")
def cache_stats(user: User = Depends(get_current_user)):
    """Get market data cache statistics."""
    return get_cache().stats()


@router.post("/cache/clear")
def clear_cache(user: User = Depends(get_current_user)):
    """Clear all cached market data (force refresh on next request)."""
    get_cache().clear()
    return {"detail": "Cache cleared"}
