"""Tests for Market Data connectors and cache."""
import time
from unittest.mock import MagicMock, patch

import pytest

from app.market_data.cache import MarketDataCache, get_cache


# ── Cache Tests ─────────────────────────────────────────────────────────────

class TestMarketDataCache:
    """Tests for the TTL cache."""

    def test_set_and_get(self):
        cache = MarketDataCache()
        cache.set("key1", {"data": "value"}, ttl_seconds=60)
        assert cache.get("key1") == {"data": "value"}

    def test_expired_entry_returns_none(self):
        cache = MarketDataCache()
        cache._store["expired"] = MagicMock(data="old", fetched_at=time.time() - 100, ttl_seconds=1)
        assert cache.get("expired") is None

    def test_invalidate(self):
        cache = MarketDataCache()
        cache.set("key1", "value", 60)
        cache.invalidate("key1")
        assert cache.get("key1") is None

    def test_clear(self):
        cache = MarketDataCache()
        cache.set("a", 1, 60)
        cache.set("b", 2, 60)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_stats(self):
        cache = MarketDataCache()
        cache.set("a", 1, 60)
        stats = cache.stats()
        assert stats["total_entries"] == 1
        assert stats["active_entries"] == 1

    def test_singleton(self):
        c1 = get_cache()
        c2 = get_cache()
        assert c1 is c2


# ── Yield Curve Tests ──────────────────────────────────────────────────────

class TestYieldCurve:
    """Tests for yield curve fetcher."""

    def test_fallback_returns_valid_structure(self):
        from app.market_data.yield_curve import _fallback_yield_curve
        result = _fallback_yield_curve()
        assert "maturities" in result
        assert len(result["maturities"]) > 0
        assert result["currency"] == "USD"
        assert result["is_fallback"] is True

    def test_fallback_has_all_maturities(self):
        from app.market_data.yield_curve import _fallback_yield_curve
        result = _fallback_yield_curve()
        labels = [m["label"] for m in result["maturities"]]
        assert "1M" in labels
        assert "10Y" in labels
        assert "30Y" in labels

    def test_fallback_rates_are_numeric(self):
        from app.market_data.yield_curve import _fallback_yield_curve
        result = _fallback_yield_curve()
        for mat in result["maturities"]:
            assert isinstance(mat["rate_pct"], float)
            assert mat["rate_pct"] > 0

    def test_fetch_returns_dict(self):
        from app.market_data.yield_curve import fetch_treasury_yield_curve
        result = fetch_treasury_yield_curve(use_cache=False)
        assert isinstance(result, dict)
        assert "maturities" in result
        assert "date" in result


# ── FX Rate Tests ──────────────────────────────────────────────────────────

class TestFXRates:
    """Tests for FX rate fetcher."""

    def test_fallback_returns_valid_structure(self):
        from app.market_data.fx_rates import _fallback_fx_rates
        result = _fallback_fx_rates()
        assert "rates" in result
        assert "EUR" in result["rates"]
        assert "USD" in result["rates"]
        assert result["rates"]["EUR"] == 1.0

    def test_fallback_all_rates_positive(self):
        from app.market_data.fx_rates import _fallback_fx_rates
        result = _fallback_fx_rates()
        for ccy, rate in result["rates"].items():
            assert rate > 0, f"{ccy} rate should be positive"

    def test_ecb_fetch_returns_dict(self):
        from app.market_data.fx_rates import fetch_ecb_rates
        result = fetch_ecb_rates(use_cache=False)
        assert isinstance(result, dict)
        assert "base" in result
        assert "rates" in result

    def test_yahoo_fx_returns_dict(self):
        from app.market_data.fx_rates import fetch_yahoo_fx
        result = fetch_yahoo_fx("USD", "EUR", use_cache=False)
        assert isinstance(result, dict)
        # Should have either rate or error
        assert "rate" in result or "error" in result


# ── Interest Rate Tests ────────────────────────────────────────────────────

class TestInterestRates:
    """Tests for interest rate fetcher."""

    def test_fallback_sofr(self):
        from app.market_data.interest_rates import _fallback_sofr
        result = _fallback_sofr()
        assert result["rate_name"] == "SOFR"
        assert result["rate_pct"] > 0
        assert result["is_fallback"] is True

    def test_fallback_ecb(self):
        from app.market_data.interest_rates import _fallback_ecb_rate
        result = _fallback_ecb_rate()
        assert "ECB" in result["rate_name"]
        assert result["rate_pct"] > 0

    def test_fetch_sofr_returns_dict(self):
        from app.market_data.interest_rates import fetch_sofr
        result = fetch_sofr(use_cache=False)
        assert isinstance(result, dict)
        assert "rate_pct" in result


# ── Economic Indicator Tests ───────────────────────────────────────────────

class TestEconomicIndicators:
    """Tests for economic indicator fetcher."""

    def test_fetch_indicator_returns_dict(self):
        from app.market_data.economic import fetch_indicator
        result = fetch_indicator("FP.CPI.TOTL.ZG", "US", use_cache=False)
        assert isinstance(result, dict)
        # Should have either data or error
        assert "data" in result or "error" in result

    def test_country_snapshot_returns_dict(self):
        from app.market_data.economic import fetch_country_snapshot
        result = fetch_country_snapshot("US", use_cache=False)
        assert isinstance(result, dict)
        assert "country" in result
        assert "indicators" in result

    def test_summary_builds_correctly(self):
        from app.market_data.economic import _build_summary
        indicators = {
            "inflation_cpi": {"latest_value": 3.5},
            "gdp_growth": {"latest_value": 2.1},
            "debt_to_gdp": {"latest_value": 85},
        }
        summary = _build_summary(indicators)
        assert summary["inflation_pct"] == 3.5
        assert summary["gdp_growth_pct"] == 2.1
        assert summary["assessment"] == "Stable"

    def test_high_inflation_detected(self):
        from app.market_data.economic import _build_summary
        indicators = {"inflation_cpi": {"latest_value": 9.0}}
        summary = _build_summary(indicators)
        assert "inflation" in summary["assessment"].lower()

    def test_recession_detected(self):
        from app.market_data.economic import _build_summary
        indicators = {"gdp_growth": {"latest_value": -2.0}}
        summary = _build_summary(indicators)
        assert "recession" in summary["assessment"].lower()
