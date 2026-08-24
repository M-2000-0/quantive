"""Financial calculations for debt instruments.

Bond pricing, yield calculations, duration, convexity, DV01, and other
risk metrics used throughout the optimization engine.
"""
from __future__ import annotations

import math
from datetime import date
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np


class DayCountConvention(str, Enum):
    """Day count conventions for bond calculations."""
    ACT_365 = "ACT/365"
    ACT_360 = "ACT/360"
    THIRTY_360 = "30/360"
    ACT_ACT = "ACT/ACT"


class CouponFrequency(str, Enum):
    ANNUAL = "annual"
    SEMI_ANNUAL = "semi_annual"
    QUARTERLY = "quarterly"


# --- Day Count Helpers ---

def _days_between(d1: date, d2: date, convention: DayCountConvention = DayCountConvention.ACT_365) -> float:
    """Calculate days between two dates according to a day count convention."""
    if convention == DayCountConvention.ACT_365:
        return (d2 - d1).days
    elif convention == DayCountConvention.ACT_360:
        return (d2 - d1).days
    elif convention == DayCountConvention.THIRTY_360:
        d1_day = min(d1.day, 30)
        d2_day = min(d2.day, 30) if d1_day == 30 else d2.day
        return 360 * (d2.year - d1.year) + 30 * (d2.month - d1.month) + (d2_day - d1_day)
    elif convention == DayCountConvention.ACT_ACT:
        days = (d2 - d1).days
        year_start = date(d1.year, 1, 1)
        year_end = date(d1.year + 1, 1, 1)
        days_in_year = (year_end - year_start).days
        return days / days_in_year if days_in_year > 0 else 0.0
    return (d2 - d1).days


def _coupon_periods_per_year(freq: CouponFrequency) -> int:
    return {
        CouponFrequency.ANNUAL: 1,
        CouponFrequency.SEMI_ANNUAL: 2,
        CouponFrequency.QUARTERLY: 4,
    }[freq]


# --- Bond Pricing ---

def bond_price(
    coupon_rate: float,
    face_value: float,
    yield_to_maturity: float,
    years_to_maturity: float,
    frequency: CouponFrequency = CouponFrequency.SEMI_ANNUAL,
    day_count: DayCountConvention = DayCountConvention.ACT_365,
) -> float:
    """Calculate the clean price of a fixed-rate bond.

    Args:
        coupon_rate: Annual coupon rate as decimal (e.g., 0.05 for 5%)
        face_value: Face (par) value of the bond
        yield_to_maturity: Annual YTM as decimal
        years_to_maturity: Time to maturity in years
        frequency: Coupon payment frequency
        day_count: Day count convention

    Returns:
        Bond clean price as percentage of face value (100 = par)
    """
    if years_to_maturity <= 0:
        return face_value

    n = _coupon_periods_per_year(frequency)
    periods = max(1, int(round(years_to_maturity * n)))
    coupon_per_period = (coupon_rate * face_value) / n
    ytm_per_period = yield_to_maturity / n

    if ytm_per_period == 0:
        return face_value + coupon_per_period * periods

    discount_factors = np.array([(1 + ytm_per_period) ** (-i) for i in range(1, periods + 1)])
    pv_coupons = float(np.sum(coupon_per_period * discount_factors))
    pv_face = face_value * (1 + ytm_per_period) ** (-periods)

    return pv_coupons + pv_face


def bond_price_from_cashflows(
    cashflows: List[Tuple[float, float]],
    yield_to_maturity: float,
) -> float:
    """Calculate bond price from a list of (time_in_years, cashflow) pairs."""
    price = 0.0
    for t, cf in cashflows:
        price += cf / ((1 + yield_to_maturity) ** t)
    return price


# --- Yield to Maturity ---

def yield_to_maturity(
    coupon_rate: float,
    face_value: float,
    market_price: float,
    years_to_maturity: float,
    frequency: CouponFrequency = CouponFrequency.SEMI_ANNUAL,
    max_iterations: int = 100,
    tolerance: float = 1e-10,
) -> float:
    """Calculate YTM using Newton-Raphson iteration.

    Args:
        coupon_rate: Annual coupon rate as decimal
        face_value: Face value
        market_price: Current market price
        years_to_maturity: Time to maturity in years
        frequency: Coupon payment frequency

    Returns:
        Yield to maturity as decimal
    """
    if years_to_maturity <= 0 or market_price <= 0:
        return 0.0

    # Initial guess: current yield
    coupon_per_year = coupon_rate * face_value
    current_yield = coupon_per_year / market_price if market_price > 0 else 0.0
    ytm = current_yield

    n = _coupon_periods_per_year(freq=frequency)

    for _ in range(max_iterations):
        price = bond_price(coupon_rate, face_value, ytm, years_to_maturity, frequency)
        diff = price - market_price

        if abs(diff) < tolerance:
            break

        # Derivative of price w.r.t. yield (modified duration * price approximation)
        dy = 1e-8
        price_up = bond_price(coupon_rate, face_value, ytm + dy, years_to_maturity, frequency)
        derivative = (price_up - price) / dy

        if abs(derivative) < 1e-15:
            break

        ytm -= diff / derivative

    return ytm


# --- Duration ---

def macaulay_duration(
    coupon_rate: float,
    face_value: float,
    yield_to_maturity: float,
    years_to_maturity: float,
    frequency: CouponFrequency = CouponFrequency.SEMI_ANNUAL,
) -> float:
    """Calculate Macaulay duration in years.

    The weighted average time to receipt of all cash flows, weighted by
    the present value of each cash flow.
    """
    if years_to_maturity <= 0:
        return 0.0

    n = _coupon_periods_per_year(freq=frequency)
    periods = max(1, int(round(years_to_maturity * n)))
    coupon_per_period = (coupon_rate * face_value) / n
    ytm_per_period = yield_to_maturity / n

    if ytm_per_period <= -1:
        return years_to_maturity

    price = bond_price(coupon_rate, face_value, yield_to_maturity, years_to_maturity, frequency)
    if price <= 0:
        return years_to_maturity

    weighted_time = 0.0
    for i in range(1, periods + 1):
        t = i / n  # time in years
        cf = coupon_per_period
        if i == periods:
            cf += face_value  # add principal at maturity
        pv = cf / ((1 + ytm_per_period) ** i)
        weighted_time += t * pv

    return weighted_time / price


def modified_duration(
    coupon_rate: float,
    face_value: float,
    yield_to_maturity: float,
    years_to_maturity: float,
    frequency: CouponFrequency = CouponFrequency.SEMI_ANNUAL,
) -> float:
    """Calculate modified duration (price sensitivity to yield changes)."""
    ytm = yield_to_maturity
    n = _coupon_periods_per_year(freq=frequency)
    mac_dur = macaulay_duration(coupon_rate, face_value, ytm, years_to_maturity, frequency)
    return mac_dur / (1 + ytm / n) if (1 + ytm / n) > 0 else mac_dur


def effective_duration(
    coupon_rate: float,
    face_value: float,
    yield_to_maturity: float,
    years_to_maturity: float,
    frequency: CouponFrequency = CouponFrequency.SEMI_ANNUAL,
    shift_bps: float = 10.0,
) -> float:
    """Calculate effective duration using finite difference.

    More accurate than modified duration for bonds with embedded options.
    """
    shift = shift_bps / 10000.0
    price = bond_price(coupon_rate, face_value, yield_to_maturity, years_to_maturity, frequency)
    price_up = bond_price(coupon_rate, face_value, yield_to_maturity + shift, years_to_maturity, frequency)
    price_down = bond_price(coupon_rate, face_value, yield_to_maturity - shift, years_to_maturity, frequency)

    if price <= 0:
        return years_to_maturity

    return (price_down - price_up) / (2 * shift * price)


def key_rate_durations(
    coupon_rate: float,
    face_value: float,
    yield_to_maturity: float,
    years_to_maturity: float,
    key_rates: Optional[List[int]] = None,
    frequency: CouponFrequency = CouponFrequency.SEMI_ANNUAL,
    shift_bps: float = 10.0,
) -> Dict[int, float]:
    """Calculate key rate durations at specified tenors.

    Key rate durations measure sensitivity to shifts at specific points
    on the yield curve.
    """
    if key_rates is None:
        key_rates = [1, 2, 3, 5, 7, 10, 15, 20, 30]

    shift = shift_bps / 10000.0
    base_price = bond_price(coupon_rate, face_value, yield_to_maturity, years_to_maturity, frequency)
    if base_price <= 0:
        return {k: 0.0 for k in key_rates}

    krd: Dict[int, float] = {}
    for kr in key_rates:
        # Approximate: shift only the cash flows near the key rate
        # This is a simplified model; a full implementation would shift the
        # entire yield curve at that tenor point
        if kr <= years_to_maturity:
            krd[kr] = (coupon_rate / yield_to_maturity) * (1.0 / kr) if yield_to_maturity > 0 else 0.0
        else:
            krd[kr] = 0.0

    return krd


# --- Convexity ---

def convexity(
    coupon_rate: float,
    face_value: float,
    yield_to_maturity: float,
    years_to_maturity: float,
    frequency: CouponFrequency = CouponFrequency.SEMI_ANNUAL,
) -> float:
    """Calculate bond convexity (second-order price sensitivity).

    Convexity measures the rate of change of duration with respect to yield,
    providing a more accurate price estimate for large yield changes.
    """
    if years_to_maturity <= 0:
        return 0.0

    n = _coupon_periods_per_year(freq=frequency)
    periods = max(1, int(round(years_to_maturity * n)))
    coupon_per_period = (coupon_rate * face_value) / n
    ytm_per_period = yield_to_maturity / n

    price = bond_price(coupon_rate, face_value, yield_to_maturity, years_to_maturity, frequency)
    if price <= 0:
        return 0.0

    weighted_convexity = 0.0
    for i in range(1, periods + 1):
        t = i / n
        cf = coupon_per_period
        if i == periods:
            cf += face_value
        pv = cf / ((1 + ytm_per_period) ** i)
        weighted_convexity += t * (t + 1) * pv

    return weighted_convexity / (price * (1 + ytm_per_period) ** 2 * n ** 2)


# --- DV01 / PV01 ---

def dv01(
    coupon_rate: float,
    face_value: float,
    yield_to_maturity: float,
    years_to_maturity: float,
    frequency: CouponFrequency = CouponFrequency.SEMI_ANNUAL,
    shift_bps: float = 1.0,
) -> float:
    """Calculate DV01 (Dollar Value of a Basis Point).

    The absolute change in bond price for a 1 basis point (0.01%) change
    in yield.
    """
    shift = shift_bps / 10000.0
    price = bond_price(coupon_rate, face_value, yield_to_maturity, years_to_maturity, frequency)
    price_down = bond_price(coupon_rate, face_value, yield_to_maturity - shift, years_to_maturity, frequency)
    return abs(price_down - price)


def pv01(
    coupon_rate: float,
    face_value: float,
    yield_to_maturity: float,
    years_to_maturity: float,
    frequency: CouponFrequency = CouponFrequency.SEMI_ANNUAL,
) -> float:
    """Alias for DV01 with 1bp shift."""
    return dv01(coupon_rate, face_value, yield_to_maturity, years_to_maturity, frequency, 1.0)


# --- Accrued Interest ---

def accrued_interest(
    coupon_rate: float,
    face_value: float,
    last_coupon_date: date,
    settlement_date: date,
    frequency: CouponFrequency = CouponFrequency.SEMI_ANNUAL,
    day_count: DayCountConvention = DayCountConvention.ACT_365,
) -> float:
    """Calculate accrued interest between last coupon date and settlement."""
    n = _coupon_periods_per_year(freq=frequency)
    period_days = 365.0 / n

    days_accrued = _days_between(last_coupon_date, settlement_date, day_count)
    coupon_per_period = (coupon_rate * face_value) / n

    return coupon_per_period * (days_accrued / period_days)


# --- Yield Curve Interpolation ---

def interpolate_yield(
    tenor: float,
    tenors: List[int],
    yields: List[float],
) -> float:
    """Linear interpolation of yield curve at a given tenor."""
    if tenor <= tenors[0]:
        return yields[0]
    if tenor >= tenors[-1]:
        return yields[-1]

    for i in range(len(tenors) - 1):
        if tenors[i] <= tenor <= tenors[i + 1]:
            t = (tenor - tenors[i]) / (tenors[i + 1] - tenors[i])
            return yields[i] * (1 - t) + yields[i + 1] * t

    return yields[-1]


def forward_rate(
    spot_rate_t1: float,
    t1: float,
    spot_rate_t2: float,
    t2: float,
) -> float:
    """Calculate the implied forward rate between two tenors.

    f(t1, t2) = ((1 + r2)^t2 / (1 + r1)^t1)^(1/(t2-t1)) - 1
    """
    if t2 <= t1 or t1 <= 0:
        return spot_rate_t2

    factor = ((1 + spot_rate_t2) ** t2) / ((1 + spot_rate_t1) ** t1)
    return factor ** (1 / (t2 - t1)) - 1


# --- Portfolio-Level Analytics ---

def portfolio_duration(
    weights: np.ndarray,
    durations: np.ndarray,
) -> float:
    """Calculate portfolio Macaulay/modified duration as weighted average."""
    if weights.sum() <= 0:
        return 0.0
    return float(np.dot(weights, durations) / weights.sum())


def portfolio_convexity(
    weights: np.ndarray,
    convexities: np.ndarray,
) -> float:
    """Calculate portfolio convexity as weighted average."""
    if weights.sum() <= 0:
        return 0.0
    return float(np.dot(weights, convexities) / weights.sum())


def portfolio_dv01(
    weights: np.ndarray,
    dv01s: np.ndarray,
) -> float:
    """Calculate portfolio DV01 as sum of weighted instrument DV01s."""
    return float(np.sum(weights * dv01s))


def price_change_approximation(
    modified_duration: float,
    convexity: float,
    yield_change: float,
) -> float:
    """Estimate bond price change using duration + convexity approximation.

    dP/P ≈ -D_mod * dy + 0.5 * C * dy²
    """
    return -modified_duration * yield_change + 0.5 * convexity * yield_change ** 2
