"""Unified market data engine — aggregates all providers behind the same interface.

Wraps the legacy dict-returning modules (yield_curve, fx_rates, economic,
interest_rates) and the new typed connectors (treasury_fiscal, imf_connector)
so downstream code never needs to know which provider supplied the data.
"""
from __future__ import annotations

import logging
from typing import Optional

from app.market_data.provider import (
    MarketDataProvider, YieldCurve, FxRate, MacroIndicator,
    EconomicSnapshot, BenchmarkRate,
)
from app.market_data.treasury_fiscal import TreasuryProvider
from app.market_data.imf_connector import IMFProvider
from app.market_data.cache import get_cache

logger = logging.getLogger("quantive.market_data.engine")


class _DictToYieldCurve:
    """Adapter: convert legacy yield_curve.py dict → YieldCurve dataclass."""

    @staticmethod
    def convert(data: dict) -> Optional[YieldCurve]:
        if not data or "maturities" not in data:
            return None
        points = []
        for m in data["maturities"]:
            points.append(YieldCurvePoint(
                maturity_months=int(m.get("years", 0) * 12) if isinstance(m.get("years"), float) else int(m.get("years", 0)),
                rate_pct=float(m["rate_pct"]),
                source=data.get("source", ""),
                date=data.get("date", ""),
                label=m.get("label", ""),
            ))
        return YieldCurve(
            country_code="US", currency="USD",
            date=data.get("date", ""),
            source=data.get("source", ""),
            points=sorted(points, key=lambda p: p.maturity_months),
            two_ten_spread_bps=data.get("2y10y_spread_bps"),
            raw=data,
        )


class _DictToFxRate:
    """Adapter: convert legacy fx_rates.py dict → list[UxRate]."""

    @staticmethod
    def convert(data: dict, base: str = "USD") -> list[FxRate]:
        rates = data.get("rates", {})
        result = []
        for ccy, val in rates.items():
            if ccy == base:
                continue
            pair = f"{base}/{ccy}" if base != "USD" else f"{ccy}/{base}"
            result.append(FxRate(
                pair=pair,
                rate=float(val),
                date=data.get("date", ""),
                source=data.get("source", ""),
            ))
        return result


class _DictToEconomicSnapshot:
    """Adapter: convert legacy economic.py dict → EconomicSnapshot."""

    @staticmethod
    def convert(data: dict) -> Optional[EconomicSnapshot]:
        if not data or "indicators" not in data:
            return None
        indicators = []
        for name, ind in data.get("indicators", {}).items():
            if isinstance(ind, dict):
                latest = ind.get("latest_value")
                if latest is not None:
                    indicators.append(MacroIndicator(
                        indicator=name,
                        value=float(latest),
                        unit="%",
                        country=data.get("country", ""),
                        date=str(ind.get("latest_year", "")),
                        source=data.get("source", ""),
                    ))
        return EconomicSnapshot(
            country_code=data.get("country", ""),
            country_name=data.get("country_name", ""),
            indicators=indicators,
            source=data.get("source", ""),
            date=data.get("fetched_at", ""),
        )


class MarketDataEngine:
    """Unified market data engine.

    Aggregates all providers behind the standard interface.
    Priority order for each data type:
      - Yield curve: Treasury (Fiscal Data) → Treasury CSV → ECB → fallback
      - FX: ECB → Yahoo Finance → IMF
      - Benchmark rates: NY Fed → ECB → IMF
      - Economic: World Bank → IMF → fallback
    """

    def __init__(self):
        self.providers: list[MarketDataProvider] = [
            TreasuryProvider(),
            IMFProvider(),
        ]
        self._cache = get_cache()

    def get_yield_curve(
        self, country_code: str = "US", date: Optional[str] = None,
        prefer_provider: Optional[str] = None,
    ) -> Optional[YieldCurve]:
        """Get yield curve from highest-priority available provider."""
        # Try named provider first
        if prefer_provider:
            for p in self.providers:
                if p.name == prefer_provider:
                    curve = p.get_yield_curve(country_code, date)
                    if curve and not curve.is_empty:
                        return curve

        # Fallback: legacy yield_curve.py
        try:
            from app.market_data.yield_curve import fetch_treasury_yield_curve
            data = fetch_treasury_yield_curve(date=date, use_cache=False)
            curve = _DictToYieldCurve.convert(data)
            if curve:
                return curve
        except Exception as e:
            logger.warning(f"Legacy treasury yield curve failed: {e}")

        # Try typed providers
        for p in self.providers:
            curve = p.get_yield_curve(country_code, date)
            if curve and not curve.is_empty:
                return curve

        return None

    def get_fx_rates(self, base: str = "USD") -> list[FxRate]:
        """Get all key FX rates."""
        # Legacy ECB + Yahoo
        try:
            from app.market_data.fx_rates import fetch_all_key_rates
            data = fetch_all_key_rates(use_cache=False)
            return _DictToFxRate.convert(data, base)
        except Exception as e:
            logger.warning(f"Legacy FX fetch failed: {e}")

        # Typed providers
        rates: list[FxRate] = []
        for p in self.providers:
            try:
                rates.extend(p.get_fx_rates(base))
            except Exception:
                continue
        return rates

    def get_benchmark_rates(self) -> list[BenchmarkRate]:
        """Get all benchmark interest rates."""
        rates: list[BenchmarkRate] = []

        # Legacy SOFR + NY Fed
        try:
            from app.market_data.interest_rates import fetch_all_benchmark_rates
            data = fetch_all_benchmark_rates(use_cache=False)
            for name, info in data.get("rates", {}).items():
                if isinstance(info, dict) and "rate_pct" in info:
                    rates.append(BenchmarkRate(
                        name=name,
                        rate_pct=float(info["rate_pct"]),
                        date=info.get("date", ""),
                        source=info.get("source", ""),
                    ))
        except Exception as e:
            logger.warning(f"Legacy benchmark rates failed: {e}")

        # Typed providers
        for p in self.providers:
            try:
                rates.extend(p.get_benchmark_rates())
            except Exception:
                continue
        return rates

    def get_economic_snapshot(
        self, country_code: str, indicators: Optional[list[str]] = None,
    ) -> Optional[EconomicSnapshot]:
        """Get macro snapshot for a country."""
        # Legacy World Bank
        try:
            from app.market_data.economic import fetch_country_snapshot
            data = fetch_country_snapshot(country_code, use_cache=False)
            snap = _DictToEconomicSnapshot.convert(data)
            if snap:
                return snap
        except Exception as e:
            logger.warning(f"Legacy economic snapshot failed: {e}")

        # Typed providers
        for p in self.providers:
            try:
                snap = p.get_economic_snapshot(country_code, indicators)
                if snap:
                    return snap
            except Exception:
                continue
        return None

    def get_historical_yield_curve(
        self, start: str, end: str,
    ) -> list[dict]:
        """Get historical yield curve series for backtesting."""
        try:
            from app.market_data.treasury_fiscal import TreasuryProvider
            tp = TreasuryProvider()
            return tp.get_historical_series("daily_treasury_yield_curve", start, end)
        except Exception:
            return []

    def get_snapshot(self, country_code: str = "US") -> dict:
        """Comprehensive market data snapshot."""
        return {
            "country": country_code,
            "yield_curve": self.get_yield_curve(country_code),
            "fx_rates": self.get_fx_rates("USD"),
            "benchmark_rates": self.get_benchmark_rates(),
            "economic": self.get_economic_snapshot(country_code),
            "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            "providers": [p.name for p in self.providers],
        }

    def health_check(self) -> list[dict]:
        return [p.health_check() for p in self.providers]


# Singleton engine
_engine: Optional[MarketDataEngine] = None


def get_market_data_engine() -> MarketDataEngine:
    global _engine
    if _engine is None:
        _engine = MarketDataEngine()
    return _engine
