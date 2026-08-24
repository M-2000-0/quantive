"""Comprehensive tests for the financial calculations module."""
import math
from datetime import date, timedelta

import numpy as np
import pytest

from quantive.financials import (
    CouponFrequency,
    DayCountConvention,
    accrued_interest,
    bond_price,
    bond_price_from_cashflows,
    convexity,
    dv01,
    effective_duration,
    forward_rate,
    interpolate_yield,
    macaulay_duration,
    modified_duration,
    portfolio_convexity,
    portfolio_dv01,
    portfolio_duration,
    price_change_approximation,
    pv01,
    yield_to_maturity,
)


class TestBondPrice:
    def test_par_bond(self):
        """A bond at par should have price = face value."""
        price = bond_price(
            coupon_rate=0.05,
            face_value=100,
            yield_to_maturity=0.05,
            years_to_maturity=10,
            frequency=CouponFrequency.SEMI_ANNUAL,
        )
        assert abs(price - 100) < 0.01

    def test_premium_bond(self):
        """A bond with coupon > YTM should trade at a premium."""
        price = bond_price(0.06, 100, 0.04, 10, CouponFrequency.SEMI_ANNUAL)
        assert price > 100

    def test_discount_bond(self):
        """A bond with coupon < YTM should trade at a discount."""
        price = bond_price(0.03, 100, 0.05, 10, CouponFrequency.SEMI_ANNUAL)
        assert price < 100

    def test_zero_coupon_bond(self):
        """Zero-coupon bond should be priced at discount to face."""
        price = bond_price(0.0, 100, 0.05, 10, CouponFrequency.SEMI_ANNUAL)
        expected = 100 / (1.025 ** 20)
        assert abs(price - expected) < 0.01

    def test_maturity_at_zero(self):
        """Bond at maturity should be worth face value."""
        price = bond_price(0.05, 100, 0.05, 0, CouponFrequency.SEMI_ANNUAL)
        assert abs(price - 100) < 0.01

    def test_zero_yield(self):
        """Bond with zero YTM should be worth sum of cashflows."""
        price = bond_price(0.05, 100, 0.0, 5, CouponFrequency.ANNUAL)
        assert price > 100

    def test_annual_frequency(self):
        """Annual coupon frequency should produce valid price."""
        price = bond_price(0.05, 100, 0.05, 10, CouponFrequency.ANNUAL)
        assert abs(price - 100) < 0.01

    def test_quarterly_frequency(self):
        """Quarterly coupon frequency should produce valid price."""
        price = bond_price(0.05, 100, 0.05, 10, CouponFrequency.QUARTERLY)
        assert abs(price - 100) < 0.01

    def test_long_maturity(self):
        """30-year bond should price correctly."""
        price = bond_price(0.05, 100, 0.05, 30, CouponFrequency.SEMI_ANNUAL)
        assert abs(price - 100) < 0.01

    def test_cashflow_pricing(self):
        """Pricing from explicit cashflows should match."""
        cashflows = [(0.5, 2.5), (1.0, 2.5), (1.5, 2.5), (2.0, 102.5)]
        price = bond_price_from_cashflows(cashflows, 0.05)
        assert price > 0


class TestYieldToMaturity:
    def test_par_ytm(self):
        """YTM of a par bond should equal the coupon rate."""
        ytm = yield_to_maturity(0.05, 100, 100, 10, CouponFrequency.SEMI_ANNUAL)
        assert abs(ytm - 0.05) < 0.001

    def test_premium_ytm(self):
        """YTM of a premium bond should be less than coupon rate."""
        ytm = yield_to_maturity(0.06, 100, 110, 10, CouponFrequency.SEMI_ANNUAL)
        assert ytm < 0.06

    def test_discount_ytm(self):
        """YTM of a discount bond should be greater than coupon rate."""
        ytm = yield_to_maturity(0.03, 100, 90, 10, CouponFrequency.SEMI_ANNUAL)
        assert ytm > 0.03

    def test_roundtrip(self):
        """Price -> YTM -> Price should be approximately round-trippable."""
        coupon = 0.05
        ytm = 0.06
        price = bond_price(coupon, 100, ytm, 10, CouponFrequency.SEMI_ANNUAL)
        recovered_ytm = yield_to_maturity(coupon, 100, price, 10, CouponFrequency.SEMI_ANNUAL)
        assert abs(recovered_ytm - ytm) < 0.001


class TestDuration:
    def test_par_bond_duration(self):
        """Duration of a par bond should be reasonable (roughly < maturity)."""
        dur = macaulay_duration(0.05, 100, 0.05, 10, CouponFrequency.SEMI_ANNUAL)
        assert 0 < dur < 10

    def test_zero_coupon_duration(self):
        """Zero-coupon bond Macaulay duration should equal maturity."""
        dur = macaulay_duration(0.0, 100, 0.05, 10, CouponFrequency.SEMI_ANNUAL)
        assert abs(dur - 10) < 0.1

    def test_modified_duration_positive(self):
        """Modified duration should be positive."""
        mod_dur = modified_duration(0.05, 100, 0.05, 10, CouponFrequency.SEMI_ANNUAL)
        assert mod_dur > 0

    def test_modified_less_than_macaulay(self):
        """Modified duration should be less than Macaulay duration."""
        mac = macaulay_duration(0.05, 100, 0.05, 10, CouponFrequency.SEMI_ANNUAL)
        mod = modified_duration(0.05, 100, 0.05, 10, CouponFrequency.SEMI_ANNUAL)
        assert mod < mac

    def test_effective_duration(self):
        """Effective duration should be close to modified duration for option-free bonds."""
        mod = modified_duration(0.05, 100, 0.05, 10, CouponFrequency.SEMI_ANNUAL)
        eff = effective_duration(0.05, 100, 0.05, 10, CouponFrequency.SEMI_ANNUAL)
        assert abs(mod - eff) < 0.5

    def test_duration_decreases_with_higher_coupon(self):
        """Higher coupon bonds should have shorter duration."""
        dur_low = macaulay_duration(0.03, 100, 0.05, 10)
        dur_high = macaulay_duration(0.08, 100, 0.05, 10)
        assert dur_high < dur_low

    def test_duration_increases_with_maturity(self):
        """Longer maturity bonds should have longer duration."""
        dur_short = macaulay_duration(0.05, 100, 0.05, 5)
        dur_long = macaulay_duration(0.05, 100, 0.05, 20)
        assert dur_long > dur_short


class TestConvexity:
    def test_convexity_positive(self):
        """Convexity should be positive for standard bonds."""
        c = convexity(0.05, 100, 0.05, 10, CouponFrequency.SEMI_ANNUAL)
        assert c > 0

    def test_zero_coupon_convexity(self):
        """Zero-coupon bond convexity should be high (highest among coupon structures)."""
        c_zc = convexity(0.0, 100, 0.05, 10, CouponFrequency.SEMI_ANNUAL)
        c_coupon = convexity(0.05, 100, 0.05, 10, CouponFrequency.SEMI_ANNUAL)
        assert c_zc > c_coupon  # Zero-coupon has higher convexity than coupon bond

    def test_convexity_increases_with_maturity(self):
        """Longer maturity should have higher convexity."""
        c_short = convexity(0.05, 100, 0.05, 5)
        c_long = convexity(0.05, 100, 0.05, 20)
        assert c_long > c_short


class TestDV01:
    def test_dv01_positive(self):
        """DV01 should be positive for standard bonds."""
        d = dv01(0.05, 100, 0.05, 10, CouponFrequency.SEMI_ANNUAL)
        assert d > 0

    def test_dv01_increases_with_maturity(self):
        """Longer maturity bonds should have higher DV01."""
        d_short = dv01(0.05, 100, 0.05, 5)
        d_long = dv01(0.05, 100, 0.05, 20)
        assert d_long > d_short

    def test_pv01_matches_dv01(self):
        """PV01 should equal DV01 with 1bp shift."""
        d1 = dv01(0.05, 100, 0.05, 10, shift_bps=1.0)
        d2 = pv01(0.05, 100, 0.05, 10)
        assert abs(d1 - d2) < 0.001


class TestAccruedInterest:
    def test_full_period(self):
        """Full coupon period accrued should be zero (at coupon date)."""
        today = date(2026, 6, 15)
        last_coupon = date(2025, 12, 15)
        ai = accrued_interest(0.05, 100, last_coupon, today, CouponFrequency.SEMI_ANNUAL)
        assert ai > 0


class TestYieldInterpolation:
    def test_exact_tenor(self):
        """Interpolation at exact tenor should return the exact yield."""
        tenors = [1, 5, 10, 30]
        yields = [0.03, 0.04, 0.045, 0.048]
        assert abs(interpolate_yield(5, tenors, yields) - 0.04) < 1e-10

    def test_midpoint(self):
        """Interpolation at midpoint should be average."""
        tenors = [1, 10]
        yields = [0.03, 0.05]
        mid = interpolate_yield(5.5, tenors, yields)
        assert abs(mid - 0.04) < 0.001


class TestForwardRate:
    def test_forward_rate_positive(self):
        """Forward rate between two positive rates should be reasonable."""
        f = forward_rate(0.03, 1, 0.04, 2)
        assert f > 0

    def test_flat_curve(self):
        """Forward rate on a flat curve should equal the spot rate."""
        f = forward_rate(0.05, 5, 0.05, 10)
        assert abs(f - 0.05) < 0.001


class TestPortfolioAnalytics:
    def test_portfolio_duration(self):
        """Portfolio duration should be weighted average."""
        weights = np.array([0.6, 0.4])
        durations = np.array([5.0, 10.0])
        result = portfolio_duration(weights, durations)
        assert abs(result - 7.0) < 0.01

    def test_portfolio_convexity(self):
        """Portfolio convexity should be weighted average."""
        weights = np.array([0.5, 0.5])
        convexities = np.array([30.0, 100.0])
        result = portfolio_convexity(weights, convexities)
        assert abs(result - 65.0) < 0.01

    def test_portfolio_dv01(self):
        """Portfolio DV01 should be sum of weighted instrument DV01s."""
        weights = np.array([0.6, 0.4])
        dv01s = np.array([500.0, 1000.0])
        result = portfolio_dv01(weights, dv01s)
        assert abs(result - 700.0) < 0.01


class TestPriceChangeApproximation:
    def test_small_move(self):
        """Duration+convexity approximation should be accurate for small moves."""
        mod_dur = 8.0
        conv = 75.0
        dy = 0.001  # 10bp
        approx = price_change_approximation(mod_dur, conv, dy)
        # Should be approximately -mod_dur * dy
        assert abs(approx - (-mod_dur * dy)) < 0.01

    def test_large_move_includes_convexity(self):
        """For large moves, convexity term should be significant."""
        mod_dur = 8.0
        conv = 75.0
        dy = 0.02  # 200bp
        approx = price_change_approximation(mod_dur, conv, dy)
        # Convexity adjustment should be positive
        convexity_term = 0.5 * conv * dy ** 2
        assert convexity_term > 0.01
