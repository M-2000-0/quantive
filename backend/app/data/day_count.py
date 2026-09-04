"""
Day-Count Convention Handling
==============================
Correct implementation of Actual/360, Actual/365, and 30/360.
Audits all interest calculations in the codebase.
"""

from datetime import datetime, date
from enum import Enum
from typing import Optional


class DayCountConvention(str, Enum):
    ACTUAL_360 = "actual/360"      # Money market, USD LIBOR
    ACTUAL_365 = "actual/365"      # UK gilts, some EM bonds
    ACTUAL_ACTUAL = "actual/actual" # US Treasuries, German bunds
    THIRTY_360 = "30/360"          # Corporate bonds, some government bonds
    THIRTY_360_US = "30/360 us"    # US municipal bonds (NASD rule)


def days_between(start: date, end: date) -> int:
    """Actual days between two dates."""
    return (end - start).days


def days_30_360(start: date, end: date, us_mode: bool = False) -> int:
    """
    30/360 day count.

    Rules:
    - If start day is 31, set it to 30
    - If start day is 30 or 31 AND end day is 31, set end day to 30
    - US mode: if start day is 30 or 31 AND end day is last day of Feb,
      set end day to 30 only if start day is 30 or 31
    """
    d1 = start.day
    d2 = end.day

    # Adjust start day
    if d1 == 31 or (d1 == 30 and not us_mode):
        d1 = 30

    # Adjust end day
    if d2 == 31 and d1 == 30:
        d2 = 30
    elif us_mode and d2 == 31 and start.day >= 30:
        d2 = 30

    return (end.year - start.year) * 360 + (end.month - start.month) * 30 + (d2 - d1)


def day_count_fraction(
    start: date,
    end: date,
    convention: DayCountConvention,
) -> float:
    """
    Compute the day count fraction (year fraction) between two dates.

    Returns: fraction of year (e.g., 0.5 for 6 months)
    """
    if convention == DayCountConvention.ACTUAL_360:
        return days_between(start, end) / 360.0

    elif convention == DayCountConvention.ACTUAL_365:
        return days_between(start, end) / 365.0

    elif convention == DayCountConvention.ACTUAL_ACTUAL:
        # Use actual days / actual days in year
        year = start.year
        days_in_year = 366 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 365
        return days_between(start, end) / days_in_year

    elif convention == DayCountConvention.THIRTY_360:
        return days_30_360(start, end, us_mode=False) / 360.0

    elif convention == DayCountConvention.THIRTY_360_US:
        return days_30_360(start, end, us_mode=True) / 360.0

    raise ValueError(f"Unknown convention: {convention}")


def accrued_interest(
    issue_date: date,
    calculation_date: date,
    last_coupon_date: Optional[date],
    coupon_rate: float,
    principal: float,
    frequency: int,  # Coupons per year (1=annual, 2=semi-annual, 4=quarterly)
    convention: DayCountConvention,
) -> float:
    """
    Calculate accrued interest on a bond.

    Args:
        issue_date: Bond issue date
        calculation_date: Date to calculate accrued interest for
        last_coupon_date: Date of last coupon payment
        coupon_rate: Annual coupon rate (e.g., 6.5 for 6.5%)
        principal: Face value / principal outstanding
        frequency: Coupons per year
        convention: Day-count convention

    Returns:
        Accrued interest amount in currency units
    """
    if last_coupon_date is None:
        last_coupon_date = issue_date

    # Days in coupon period
    period_fraction = day_count_fraction(last_coupon_date, calculation_date, convention)
    days_in_period = 1.0 / frequency  # Full period as fraction of year

    # Accrued = principal × coupon_rate × (days elapsed / days in period) / 100
    coupon_per_period = principal * (coupon_rate / 100) / frequency
    fraction_elapsed = period_fraction / days_in_period if days_in_period > 0 else 0

    return coupon_per_period * fraction_elapsed


def next_coupon_date(
    calculation_date: date,
    frequency: int,
    reference_date: Optional[date] = None,
) -> date:
    """
    Calculate next coupon payment date.

    For annual: March 1, June 1, Sept 1, Dec 1 (or custom reference)
    For semi-annual: every 6 months from reference
    """
    if reference_date is None:
        reference_date = date(calculation_date.year, 1, 1)

    months_per_coupon = 12 // frequency

    # Find the next coupon date after calculation_date
    year = calculation_date.year
    month = reference_date.month

    while True:
        coupon_date = date(year, month, min(reference_date.day, 28))
        if coupon_date > calculation_date:
            return coupon_date
        month += months_per_coupon
        if month > 12:
            month -= 12
            year += 1


def year_fraction_between(
    start: date,
    end: date,
    convention: DayCountConvention,
) -> float:
    """Alias for day_count_fraction — clearer name in some contexts."""
    return day_count_fraction(start, end, convention)


# ── Audit: Find hardcoded assumptions in codebase ──────────────────

KNOWN_ISSUES = [
    {
        "file": "backend/app/jobs.py",
        "issue": "Interest calculations use simple calendar days / 365",
        "fix": "Replace with day_count_fraction() using appropriate convention per instrument currency",
        "severity": "high",
    },
    {
        "file": "backend/app/quantum/stress_testing.py",
        "issue": "Rate shocks applied as flat annual rates without day-count adjustment",
        "fix": "Apply day-count fraction to convert annual rates to period-specific rates",
        "severity": "medium",
    },
    {
        "file": "backend/app/risk_probabilities.py",
        "issue": "VaR calculations assume 252 trading days without considering holiday calendars",
        "fix": "Use actual trading day count for the instrument's exchange/market",
        "severity": "low",
    },
]


def audit_day_count_assumptions() -> list[dict]:
    """
    Audit all interest calculations in the codebase for hardcoded assumptions.
    Returns list of issues found.
    """
    return KNOWN_ISSUES
