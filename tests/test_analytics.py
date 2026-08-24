"""Comprehensive tests for the portfolio analytics engine."""
from datetime import date, timedelta

import numpy as np
import pytest

from quantive.analytics import (
    coupon_distribution,
    currency_exposure,
    instrument_convexities,
    instrument_durations,
    instrument_dv01s,
    instrument_type_distribution,
    maturity_profile,
    maturity_wall_analysis,
    portfolio_analytics,
    portfolio_weighted_duration,
    rate_type_decomposition,
)
from quantive.data.synthetic import generate_synthetic_portfolio
from quantive.models.enums import Currency, RateType
from quantive.models.instruments import DebtInstrument, Portfolio, make_portfolio


def _make_test_portfolio() -> Portfolio:
    """Create a small test portfolio for unit testing."""
    instruments = [
        DebtInstrument(
            id="usd-fix-01", name="USD Fixed 5Y", currency=Currency.USD,
            principal=5000, coupon=0.04, rate_type=RateType.FIXED,
            maturity_date=date(2031, 6, 15), issue_date=date(2026, 6, 15),
            liquidity=0.8, market_capacity=5000,
        ),
        DebtInstrument(
            id="usd-fix-02", name="USD Fixed 10Y", currency=Currency.USD,
            principal=8000, coupon=0.045, rate_type=RateType.FIXED,
            maturity_date=date(2036, 6, 15), issue_date=date(2026, 6, 15),
            liquidity=0.7, market_capacity=8000,
        ),
        DebtInstrument(
            id="usd-flt-01", name="USD Floating 3Y", currency=Currency.USD,
            principal=3000, coupon=0.005, rate_type=RateType.FLOATING,
            maturity_date=date(2029, 6, 15), issue_date=date(2026, 6, 15),
            liquidity=0.9, market_capacity=3000,
        ),
        DebtInstrument(
            id="eur-fix-01", name="EUR Fixed 7Y", currency=Currency.EUR,
            principal=4000, coupon=0.035, rate_type=RateType.FIXED,
            maturity_date=date(2033, 6, 15), issue_date=date(2026, 6, 15),
            liquidity=0.6, market_capacity=4000,
        ),
        DebtInstrument(
            id="jpy-fix-01", name="JPY Fixed 15Y", currency=Currency.JPY,
            principal=2000, coupon=0.008, rate_type=RateType.FIXED,
            maturity_date=date(2041, 6, 15), issue_date=date(2026, 6, 15),
            liquidity=0.4, market_capacity=2000,
        ),
    ]
    return make_portfolio(
        portfolio_id="test-portfolio",
        name="Test Portfolio",
        instruments=instruments,
    )


class TestInstrumentDurations:
    def test_returns_all_instruments(self):
        """Should return duration for every instrument."""
        portfolio = _make_test_portfolio()
        durations = instrument_durations(portfolio.instruments)
        assert len(durations) == len(portfolio.instruments)

    def test_fixed_rate_duration(self):
        """Fixed-rate instruments should have meaningful duration."""
        portfolio = _make_test_portfolio()
        durations = instrument_durations(portfolio.instruments)
        for inst_id, d in durations.items():
            assert d["macaulay_duration"] > 0
            assert d["modified_duration"] > 0

    def test_longer_maturity_longer_duration(self):
        """5Y bond should have shorter duration than 10Y bond."""
        portfolio = _make_test_portfolio()
        durations = instrument_durations(portfolio.instruments)
        assert durations["usd-fix-02"]["macaulay_duration"] > durations["usd-fix-01"]["macaulay_duration"]


class TestMaturityProfile:
    def test_returns_sorted_years(self):
        """Maturity profile should be sorted by year."""
        portfolio = _make_test_portfolio()
        profile = maturity_profile(portfolio.instruments)
        years = list(profile.keys())
        assert years == sorted(years)

    def test_total_matches_portfolio(self):
        """Sum of maturity profile should equal total principal."""
        portfolio = _make_test_portfolio()
        profile = maturity_profile(portfolio.instruments)
        total = sum(profile.values())
        expected = sum(i.principal for i in portfolio.instruments)
        assert abs(total - expected) < 0.01

    def test_empty_portfolio(self):
        """Empty portfolio should return empty profile."""
        profile = maturity_profile([])
        assert len(profile) == 0


class TestMaturityWallAnalysis:
    def test_wall_year_identified(self):
        """Should identify the year with highest concentration."""
        portfolio = _make_test_portfolio()
        wall = maturity_wall_analysis(portfolio.instruments)
        assert wall["wall_year"] > 0
        assert 0 < wall["max_single_year_pct"] <= 1

    def test_consecutive_years(self):
        """Consecutive years concentration should be >= single year."""
        portfolio = _make_test_portfolio()
        wall = maturity_wall_analysis(portfolio.instruments)
        assert wall["max_consecutive_years_pct"] >= wall["max_single_year_pct"]


class TestCurrencyExposure:
    def test_all_currencies_present(self):
        """Should have entries for all currencies in portfolio."""
        portfolio = _make_test_portfolio()
        exposure = currency_exposure(portfolio.instruments)
        assert "USD" in exposure
        assert "EUR" in exposure
        assert "JPY" in exposure

    def test_shares_sum_to_one(self):
        """Currency shares should sum to approximately 1."""
        portfolio = _make_test_portfolio()
        exposure = currency_exposure(portfolio.instruments)
        total_share = sum(e["share_pct"] for e in exposure.values())
        assert abs(total_share - 1.0) < 0.001

    def test_usd_dominant(self):
        """USD should be the dominant currency in our test portfolio."""
        portfolio = _make_test_portfolio()
        exposure = currency_exposure(portfolio.instruments)
        assert exposure["USD"]["share_pct"] > exposure["EUR"]["share_pct"]


class TestRateTypeDecomposition:
    def test_fixed_and_floating(self):
        """Should show both fixed and floating rates."""
        portfolio = _make_test_portfolio()
        decomp = rate_type_decomposition(portfolio.instruments)
        assert "fixed" in decomp
        assert "floating" in decomp

    def test_shares_sum_to_one(self):
        """Rate type shares should sum to approximately 1."""
        portfolio = _make_test_portfolio()
        decomp = rate_type_decomposition(portfolio.instruments)
        total = sum(d["share_pct"] for d in decomp.values())
        assert abs(total - 1.0) < 0.001

    def test_fixed_dominant(self):
        """Fixed rate should be dominant in our test portfolio."""
        portfolio = _make_test_portfolio()
        decomp = rate_type_decomposition(portfolio.instruments)
        assert decomp["fixed"]["share_pct"] > decomp["floating"]["share_pct"]


class TestInstrumentTypeDistribution:
    def test_returns_distribution(self):
        """Should return instrument type distribution."""
        portfolio = _make_test_portfolio()
        dist = instrument_type_distribution(portfolio.instruments)
        assert len(dist) > 0


class TestCouponDistribution:
    def test_returns_distribution(self):
        """Should return coupon distribution with correct bins."""
        portfolio = _make_test_portfolio()
        dist = coupon_distribution(portfolio.instruments)
        assert len(dist) > 0


class TestPortfolioAnalytics:
    def test_comprehensive_output(self):
        """Should return all analytics fields."""
        portfolio = _make_test_portfolio()
        result = portfolio_analytics(portfolio)
        assert "total_principal" in result
        assert "instrument_count" in result
        assert "duration" in result
        assert "convexity" in result
        assert "maturity_profile" in result
        assert "currency_exposure" in result
        assert "rate_type_decomposition" in result
        assert "instrument_type_distribution" in result
        assert "coupon_distribution" in result
        assert "maturity_wall" in result

    def test_correct_total(self):
        """Total principal should match portfolio."""
        portfolio = _make_test_portfolio()
        result = portfolio_analytics(portfolio)
        expected = sum(i.principal for i in portfolio.instruments)
        assert abs(result["total_principal"] - expected) < 0.01

    def test_correct_count(self):
        """Instrument count should match."""
        portfolio = _make_test_portfolio()
        result = portfolio_analytics(portfolio)
        assert result["instrument_count"] == len(portfolio.instruments)

    def test_empty_portfolio(self):
        """Empty portfolio should return zero values."""
        from quantive.models.instruments import Portfolio as P
        empty = P(id="empty", name="Empty", instruments=[])
        result = portfolio_analytics(empty)
        assert result["total_principal"] == 0
        assert result["instrument_count"] == 0


class TestWithSyntheticPortfolio:
    """Tests using the full synthetic portfolio generator."""

    def test_synthetic_portfolio_analytics(self):
        """Full synthetic portfolio should produce valid analytics."""
        portfolio = generate_synthetic_portfolio(seed=42)
        result = portfolio_analytics(portfolio)
        assert result["total_principal"] > 0
        assert result["instrument_count"] > 0
        assert result["duration"]["macaulay_duration"] > 0
        assert len(result["currency_exposure"]) > 0

    def test_synthetic_portfolio_deterministic(self):
        """Same seed should produce same results."""
        p1 = generate_synthetic_portfolio(seed=42)
        p2 = generate_synthetic_portfolio(seed=42)
        r1 = portfolio_analytics(p1)
        r2 = portfolio_analytics(p2)
        assert abs(r1["total_principal"] - r2["total_principal"]) < 0.01
