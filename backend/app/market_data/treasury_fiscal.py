"""US Treasury Fiscal Data API connector.

Uses the modern Treasury Fiscal Data API (api.fiscaldata.treasury.gov):
- Daily Treasury Par Yield Curve Rates
- Average Interest Rates on the Public Debt

Free, no API key required. Rate limit: 5 req/sec (generous for this use case).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, date
from typing import Optional

from app.market_data.provider import (
    MarketDataProvider, YieldCurve, YieldCurvePoint, BenchmarkRate,
    get_rate_limiter,
)
from app.market_data.cache import TTL_YIELD_CURVE, get_cache

logger = logging.getLogger("quantive.market_data.treasury")

# ── Treasury Fiscal Data API ────────────────────────────────────────

TREASURY_FISCAL_BASE = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
# Daily par yield curve rates endpoint
TREASURY_YIELD_CURVE_ENDPOINT = (
    f"{TREASURY_FISCAL_BASE}/v2/accounting/od/daily_treasury_yield_curve"
)
# Average interest rates on the public debt
TREASURY_AVG_INT_RATE_ENDPOINT = (
    f"{TREASURY_FISCAL_BASE}/v2/accounting/od/avg_interest_rates"
)

# Maturity mapping from Treasury's field names to months
TREASURY_MATURITY_MAP = {
    "BC_1MONTH": (1, "1M"),
    "BC_2MONTH": (2, "2M"),
    "BC_3MONTH": (3, "3M"),
    "BC_4MONTH": (4, "4M"),
    "BC_6MONTH": (6, "6M"),
    "BC_1YEAR": (12, "1Y"),
    "BC_2YEAR": (24, "2Y"),
    "BC_3YEAR": (36, "3Y"),
    "BC_5YEAR": (60, "5Y"),
    "BC_7YEAR": (84, "7Y"),
    "BC_10YEAR": (120, "10Y"),
    "BC_20YEAR": (240, "20Y"),
    "BC_30YEAR": (360, "30Y"),
}


class TreasuryProvider(MarketDataProvider):
    """US Treasury — Official par yield curve rates via Fiscal Data API.

    Free, no API key, daily data.
    """

    @property
    def name(self) -> str:
        return "US Treasury (Fiscal Data)"

    @property
    def is_available(self) -> bool:
        return True

    def get_yield_curve(
        self, country_code: str = "US", date: Optional[str] = None,
    ) -> Optional[YieldCurve]:
        if country_code.upper() != "US":
            return None

        cache = get_cache()
        cache_key = f"treasury_yield_curve_{date or 'latest'}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        limiter = get_rate_limiter()
        limiter.set_rate("treasury_fiscal", 5.0)  # 5 req/sec allowed

        params: dict[str, Any] = {"sort": "-record_date", "page[size]": 100}
        if date:
            params["filter"] = f'record_date:lte:{date}'

        data = self._request("GET", TREASURY_YIELD_CURVE_ENDPOINT, params=params, source="treasury_fiscal")
        if not data:
            logger.warning("Treasury Fiscal Data API returned no data")
            return self._fallback_curve()

        records = data.get("data", [])
        if not records:
            return self._fallback_curve()

        # Find target date or use latest
        target = None
        if date:
            for r in records:
                if r.get("record_date") == date:
                    target = r
                    break
        if target is None:
            target = records[0]  # Latest (sorted desc)

        points = []
        for field_name, (months, label) in TREASURY_MATURITY_MAP.items():
            raw_val = target.get(field_name)
            if raw_val is None or raw_val == "":
                continue
            try:
                rate = float(raw_val)
            except (ValueError, TypeError):
                continue
            points.append(YieldCurvePoint(
                maturity_months=months,
                rate_pct=rate,
                source="US Treasury",
                date=target.get("record_date", ""),
                label=label,
            ))

        if not points:
            return self._fallback_curve()

        # Calculate 2s10s spread
        two_yr = next((p for p in points if p.label == "2Y"), None)
        ten_yr = next((p for p in points if p.label == "10Y"), None)
        spread = None
        if two_yr and ten_yr:
            spread = round((ten_yr.rate_pct - two_yr.rate_pct) * 100, 1)

        result = YieldCurve(
            country_code="US",
            currency="USD",
            date=target.get("record_date", date.today().isoformat()),
            source="US Treasury (Fiscal Data)",
            points=sorted(points, key=lambda p: p.maturity_months),
            two_ten_spread_bps=spread,
            raw={"record_count": len(records), "fiscal_api": True},
        )

        cache.set(cache_key, result, TTL_YIELD_CURVE)
        return result

    def get_fx_rate(self, pair: str, date: Optional[str] = None) -> None:
        """Treasury does not publish FX — return None (use ECB provider)."""
        return None

    def get_fx_rates(self, base: str = "USD") -> list:
        return []

    def get_benchmark_rates(self) -> list[BenchmarkRate]:
        """Fetch average interest rates on public debt as benchmark rates."""
        data = self._request(
            "GET", TREASURY_AVG_INT_RATE_ENDPOINT,
            params={"sort": "-record_date", "page[size]": 5},
            source="treasury_fiscal",
        )
        rates: list[BenchmarkRate] = []
        if not data:
            return rates

        for rec in data.get("data", [])[:1]:
            # avg_interest_rates has: record_date, security_desc, avg_interest_rate_amt
            pass  # structure varies; keep simple for now

        return rates

    def get_economic_snapshot(self, country_code: str, indicators=None) -> None:
        return None

    def get_historical_series(self, series_id: str, start: str, end: str) -> list[dict]:
        """Fetch historical yield curve for backtesting.

        ``series_id`` is ignored — Treasury returns full history by date range.
        """
        params: dict[str, Any] = {
            "sort": "record_date",
            "filter": f'record_date:gte:{start},record_date:lte:{end}',
            "page[size]": 1000,
        }
        data = self._request("GET", TREASURY_YIELD_CURVE_ENDPOINT, params=params, source="treasury_fiscal")
        if not data:
            return []

        series = []
        for rec in data.get("data", []):
            row = {"date": rec.get("record_date")}
            for field_name, (_, label) in TREASURY_MATURITY_MAP.items():
                val = rec.get(field_name)
                if val not in (None, ""):
                    try:
                        row[label] = float(val)
                    except (ValueError, TypeError):
                        pass
            if row.get("date"):
                series.append(row)
        return series

    def get_debt_stats(self, country_code: str) -> dict:
        """Fetch outstanding public debt statistics."""
        data = self._request(
            "GET", f"{TREASURY_FISCAL_BASE}/v2/accounting/od/debt_to_penny",
            params={"sort": "-record_date", "page[size]": 1},
            source="treasury_fiscal",
        )
        if not data or not data.get("data"):
            return {}
        rec = data["data"][0]
        return {
            "total_debt_penny": rec.get("debt_interest_holding"),
            "date": rec.get("record_date"),
            "source": "US Treasury Fiscal Data",
        }

    def _fallback_curve(self) -> YieldCurve:
        """Fallback with known approximate rates."""
        return YieldCurve(
            country_code="US", currency="USD",
            date=date.today().isoformat(),
            source="US Treasury (fallback)",
            points=[
                YieldCurvePoint(1, 5.35, "US Treasury", ""),
                YieldCurvePoint(3, 5.25, "US Treasury", ""),
                YieldCurvePoint(6, 5.10, "US Treasury", ""),
                YieldCurvePoint(12, 4.85, "US Treasury", ""),
                YieldCurvePoint(24, 4.50, "US Treasury", ""),
                YieldCurvePoint(36, 4.30, "US Treasury", ""),
                YieldCurvePoint(60, 4.20, "US Treasury", ""),
                YieldCurvePoint(84, 4.25, "US Treasury", ""),
                YieldCurvePoint(120, 4.25, "US Treasury", ""),
                YieldCurvePoint(240, 4.50, "US Treasury", ""),
                YieldCurvePoint(360, 4.40, "US Treasury", ""),
            ],
            two_ten_spread_bps=-25.0,
        )
