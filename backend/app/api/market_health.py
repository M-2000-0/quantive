"""Market Data Health API — Ping all data sources and report live/fallback status.

Endpoints:
- GET /api/market/health — Ping all 6 sources and return status for each
- GET /api/market/health/{source} — Ping a specific source
"""

import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/market", tags=["market-health"])


class SourceHealth(BaseModel):
    name: str
    provider: str
    url: str
    status: str  # "live", "fallback", "error"
    latency_ms: Optional[float] = None
    last_value: Optional[str] = None
    error: Optional[str] = None
    tested_at: str = ""


def _test_treasury_yield() -> SourceHealth:
    """Test US Treasury yield curve fetch."""
    from datetime import datetime, timezone
    start = time.time()
    try:
        from app.market_data.yield_curve import fetch_treasury_yield_curve
        result = fetch_treasury_yield_curve()
        latency = round((time.time() - start) * 1000, 1)
        is_fallback = result.get("is_fallback", False)
        mat_count = len(result.get("maturities", []))
        spread = result.get("2y10y_spread_bps", "N/A")
        return SourceHealth(
            name="treasury_yield",
            provider="US Treasury.gov",
            url="home.treasury.gov/resource-center/data-chart-center/interest-rates",
            status="fallback" if is_fallback else "live",
            latency_ms=latency,
            last_value=f"{mat_count} maturities, 2s10s={spread}bps",
            tested_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        return SourceHealth(
            name="treasury_yield",
            provider="US Treasury.gov",
            url="home.treasury.gov",
            status="error",
            latency_ms=round((time.time() - start) * 1000, 1),
            error=str(e),
            tested_at=datetime.now(timezone.utc).isoformat(),
        )


def _test_ecb_fx() -> SourceHealth:
    """Test ECB FX rates."""
    from datetime import datetime, timezone
    start = time.time()
    try:
        from app.market_data.fx_rates import fetch_ecb_rates
        result = fetch_ecb_rates()
        latency = round((time.time() - start) * 1000, 1)
        is_fallback = result.get("is_fallback", False)
        rate_count = len(result.get("rates", {}))
        eurusd = result.get("rates", {}).get("USD", "N/A")
        return SourceHealth(
            name="ecb_fx",
            provider="European Central Bank",
            url="ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml",
            status="fallback" if is_fallback else "live",
            latency_ms=latency,
            last_value=f"{rate_count} currencies, EUR/USD={eurusd}",
            tested_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        return SourceHealth(
            name="ecb_fx",
            provider="European Central Bank",
            url="ecb.europa.eu",
            status="error",
            latency_ms=round((time.time() - start) * 1000, 1),
            error=str(e),
            tested_at=datetime.now(timezone.utc).isoformat(),
        )


def _test_sofr() -> SourceHealth:
    """Test SOFR rate from NY Fed."""
    from datetime import datetime, timezone
    start = time.time()
    try:
        from app.market_data.interest_rates import fetch_sofr
        result = fetch_sofr()
        latency = round((time.time() - start) * 1000, 1)
        is_fallback = result.get("is_fallback", False)
        rate = result.get("rate_pct", "N/A")
        return SourceHealth(
            name="sofr",
            provider="Federal Reserve Bank of New York",
            url="markets.newyorkfed.org/api/rates/secured/sofr",
            status="fallback" if is_fallback else "live",
            latency_ms=latency,
            last_value=f"SOFR={rate}%",
            tested_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        return SourceHealth(
            name="sofr",
            provider="Federal Reserve Bank of New York",
            url="markets.newyorkfed.org",
            status="error",
            latency_ms=round((time.time() - start) * 1000, 1),
            error=str(e),
            tested_at=datetime.now(timezone.utc).isoformat(),
        )


def _test_ecb_rate() -> SourceHealth:
    """Test ECB Main Refinancing Rate."""
    from datetime import datetime, timezone
    start = time.time()
    try:
        from app.market_data.interest_rates import fetch_ecb_key_rate
        result = fetch_ecb_key_rate()
        latency = round((time.time() - start) * 1000, 1)
        is_fallback = result.get("is_fallback", False)
        rate = result.get("rate_pct", "N/A")
        return SourceHealth(
            name="ecb_rate",
            provider="European Central Bank",
            url="data-api.ecb.europa.eu/service/data/FM/D.U2.EUR.4F.KR.MRR_FR.LEV",
            status="fallback" if is_fallback else "live",
            latency_ms=latency,
            last_value=f"ECB MRR={rate}%",
            tested_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        return SourceHealth(
            name="ecb_rate",
            provider="European Central Bank",
            url="data-api.ecb.europa.eu",
            status="error",
            latency_ms=round((time.time() - start) * 1000, 1),
            error=str(e),
            tested_at=datetime.now(timezone.utc).isoformat(),
        )


def _test_world_bank() -> SourceHealth:
    """Test World Bank economic indicators."""
    from datetime import datetime, timezone
    start = time.time()
    try:
        from app.market_data.economic import fetch_indicator
        result = fetch_indicator("FP.CPI.TOTL.ZG", "US", num_periods=1)
        latency = round((time.time() - start) * 1000, 1)
        has_error = "error" in result
        latest = result.get("latest_value")
        return SourceHealth(
            name="world_bank",
            provider="World Bank",
            url="api.worldbank.org/v2/country/US/indicator/FP.CPI.TOTL.ZG",
            status="error" if has_error else "live",
            latency_ms=latency,
            last_value=f"US CPI={latest}%" if latest else None,
            error=result.get("error"),
            tested_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        return SourceHealth(
            name="world_bank",
            provider="World Bank",
            url="api.worldbank.org",
            status="error",
            latency_ms=round((time.time() - start) * 1000, 1),
            error=str(e),
            tested_at=datetime.now(timezone.utc).isoformat(),
        )


def _test_yahoo_fx() -> SourceHealth:
    """Test Yahoo Finance FX fallback."""
    from datetime import datetime, timezone
    start = time.time()
    try:
        from app.market_data.fx_rates import fetch_yahoo_fx
        result = fetch_yahoo_fx("USD", "EUR", use_cache=False)
        latency = round((time.time() - start) * 1000, 1)
        has_error = "error" in result
        rate = result.get("rate")
        return SourceHealth(
            name="yahoo_fx",
            provider="Yahoo Finance",
            url="query1.finance.yahoo.com/v8/finance/chart/USDEUR=X",
            status="error" if has_error else "live",
            latency_ms=latency,
            last_value=f"USD/EUR={rate}" if rate else None,
            error=result.get("error"),
            tested_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        return SourceHealth(
            name="yahoo_fx",
            provider="Yahoo Finance",
            url="query1.finance.yahoo.com",
            status="error",
            latency_ms=round((time.time() - start) * 1000, 1),
            error=str(e),
            tested_at=datetime.now(timezone.utc).isoformat(),
        )


SOURCE_TESTERS = {
    "treasury_yield": _test_treasury_yield,
    "ecb_fx": _test_ecb_fx,
    "sofr": _test_sofr,
    "ecb_rate": _test_ecb_rate,
    "world_bank": _test_world_bank,
    "yahoo_fx": _test_yahoo_fx,
}


@router.get("/health")
def get_market_health():
    """Ping all 6 data sources and return live/fallback status for each."""
    results = []
    for name, tester in SOURCE_TESTERS.items():
        results.append(tester())

    live_count = sum(1 for r in results if r.status == "live")
    fallback_count = sum(1 for r in results if r.status == "fallback")
    error_count = sum(1 for r in results if r.status == "error")
    avg_latency = round(
        sum(r.latency_ms or 0 for r in results if r.status != "error") /
        max(1, len([r for r in results if r.status != "error"])),
        1,
    )

    return {
        "status": "healthy" if error_count == 0 else "degraded" if live_count > 0 else "offline",
        "summary": {
            "live": live_count,
            "fallback": fallback_count,
            "error": error_count,
            "total": len(results),
            "avg_latency_ms": avg_latency,
        },
        "sources": [r.model_dump() for r in results],
    }


@router.get("/health/{source_name}")
def get_source_health(source_name: str):
    """Ping a specific data source."""
    if source_name not in SOURCE_TESTERS:
        raise HTTPException(status_code=404, detail=f"Unknown source: {source_name}. Available: {list(SOURCE_TESTERS.keys())}")
    return SOURCE_TESTERS[source_name]()
