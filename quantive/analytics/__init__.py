"""Portfolio analytics engine.

Computes comprehensive risk and composition analytics for a debt portfolio,
including duration, convexity, DV01, maturity profile, currency exposure,
rate-type decomposition, and cost distribution.
"""
from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional


from quantive.financials import (
    convexity as calc_convexity,
    dv01 as calc_dv01,
    effective_duration,
    macaulay_duration,
    modified_duration,
)
from quantive.models.enums import RateType
from quantive.models.instruments import DebtInstrument, Portfolio


# --- Duration Analytics ---

def instrument_durations(
    instruments: List[DebtInstrument],
    as_of: Optional[date] = None,
    discount_rate: float = 0.05,
) -> Dict[str, Dict[str, float]]:
    """Calculate Macaulay, modified, and effective duration for each instrument."""
    result = {}
    for inst in instruments:
        ytm = inst.coupon if inst.rate_type == RateType.FIXED else discount_rate
        ytm = max(ytm, 0.001)
        tt = inst.years_to_maturity(as_of)

        mac_dur = macaulay_duration(inst.coupon, inst.principal, ytm, tt)
        mod_dur = modified_duration(inst.coupon, inst.principal, ytm, tt)
        eff_dur = effective_duration(inst.coupon, inst.principal, ytm, tt)

        result[inst.id] = {
            "macaulay_duration": round(mac_dur, 4),
            "modified_duration": round(mod_dur, 4),
            "effective_duration": round(eff_dur, 4),
        }
    return result


def portfolio_weighted_duration(
    portfolio: Portfolio,
    weights: Optional[Dict[str, float]] = None,
    as_of: Optional[date] = None,
    discount_rate: float = 0.05,
) -> Dict[str, float]:
    """Calculate weighted portfolio duration metrics."""
    if not portfolio.instruments:
        return {"macaulay_duration": 0.0, "modified_duration": 0.0, "effective_duration": 0.0}

    durations = instrument_durations(portfolio.instruments, as_of, discount_rate)
    total = sum(i.principal for i in portfolio.instruments)
    if total <= 0:
        return {"macaulay_duration": 0.0, "modified_duration": 0.0, "effective_duration": 0.0}

    mac_w, mod_w, eff_w = 0.0, 0.0, 0.0
    for inst in portfolio.instruments:
        w = (inst.principal / total) if weights is None else weights.get(inst.id, 0)
        d = durations[inst.id]
        mac_w += w * d["macaulay_duration"]
        mod_w += w * d["modified_duration"]
        eff_w += w * d["effective_duration"]

    return {
        "macaulay_duration": round(mac_w, 4),
        "modified_duration": round(mod_w, 4),
        "effective_duration": round(eff_w, 4),
    }


# --- Convexity Analytics ---

def instrument_convexities(
    instruments: List[DebtInstrument],
    as_of: Optional[date] = None,
    discount_rate: float = 0.05,
) -> Dict[str, float]:
    """Calculate convexity for each instrument."""
    result = {}
    for inst in instruments:
        ytm = inst.coupon if inst.rate_type == RateType.FIXED else discount_rate
        ytm = max(ytm, 0.001)
        tt = inst.years_to_maturity(as_of)
        result[inst.id] = round(calc_convexity(inst.coupon, inst.principal, ytm, tt), 4)
    return result


# --- DV01 Analytics ---

def instrument_dv01s(
    instruments: List[DebtInstrument],
    as_of: Optional[date] = None,
    discount_rate: float = 0.05,
) -> Dict[str, float]:
    """Calculate DV01 for each instrument."""
    result = {}
    for inst in instruments:
        ytm = inst.coupon if inst.rate_type == RateType.FIXED else discount_rate
        ytm = max(ytm, 0.001)
        tt = inst.years_to_maturity(as_of)
        result[inst.id] = round(calc_dv01(inst.coupon, inst.principal, ytm, tt), 2)
    return result


# --- Maturity Profile ---

def maturity_profile(
    instruments: List[DebtInstrument],
    as_of: Optional[date] = None,
) -> Dict[int, float]:
    """Principal maturing per year bucket from today."""
    ref = as_of or date.today()
    profile: Dict[int, float] = {}
    for inst in instruments:
        y = max(0, int(round(inst.years_to_maturity(ref))))
        profile[y] = profile.get(y, 0.0) + inst.principal
    return dict(sorted(profile.items()))


def maturity_wall_analysis(
    instruments: List[DebtInstrument],
    as_of: Optional[date] = None,
) -> Dict[str, float]:
    """Analyze maturity wall - identify concentration risks."""
    profile = maturity_profile(instruments, as_of)
    total = sum(i.principal for i in instruments)
    if total <= 0:
        return {"max_single_year_pct": 0.0, "max_consecutive_years_pct": 0.0, "wall_year": 0}

    max_single = 0.0
    wall_year = 0
    for year, amount in profile.items():
        pct = amount / total
        if pct > max_single:
            max_single = pct
            wall_year = year

    # Find the worst consecutive 3-year window
    years = sorted(profile.keys())
    max_consecutive = 0.0
    for i in range(len(years)):
        window = sum(profile.get(years[i + j], 0) for j in range(3) if i + j < len(years))
        if window / total > max_consecutive:
            max_consecutive = window / total

    return {
        "max_single_year_pct": round(max_single, 4),
        "max_consecutive_years_pct": round(max_consecutive, 4),
        "wall_year": wall_year,
        "years_to_wall": wall_year,
    }


# --- Currency Exposure ---

def currency_exposure(
    instruments: List[DebtInstrument],
) -> Dict[str, Dict[str, float]]:
    """Detailed currency exposure analysis."""
    total = sum(i.principal for i in instruments)
    if total <= 0:
        return {}

    exposure: Dict[str, Dict[str, float]] = {}
    for inst in instruments:
        ccy = inst.currency.value
        if ccy not in exposure:
            exposure[ccy] = {"principal": 0.0, "count": 0, "avg_coupon": 0.0, "total_coupon_weighted": 0.0}
        exposure[ccy]["principal"] += inst.principal
        exposure[ccy]["count"] += 1
        exposure[ccy]["total_coupon_weighted"] += inst.coupon * inst.principal

    for ccy, data in exposure.items():
        data["share_pct"] = round(data["principal"] / total, 4)
        data["avg_coupon"] = round(data["total_coupon_weighted"] / data["principal"], 6) if data["principal"] > 0 else 0.0
        del data["total_coupon_weighted"]

    return exposure


# --- Rate Type Decomposition ---

def rate_type_decomposition(
    instruments: List[DebtInstrument],
) -> Dict[str, Dict[str, float]]:
    """Fixed vs floating rate decomposition."""
    total = sum(i.principal for i in instruments)
    if total <= 0:
        return {}

    result: Dict[str, Dict[str, float]] = {}
    for inst in instruments:
        rt = inst.rate_type.value
        if rt not in result:
            result[rt] = {"principal": 0.0, "count": 0, "weighted_coupon": 0.0, "total_coupon_weighted": 0.0}
        result[rt]["principal"] += inst.principal
        result[rt]["count"] += 1
        result[rt]["total_coupon_weighted"] += inst.coupon * inst.principal

    for rt, data in result.items():
        data["share_pct"] = round(data["principal"] / total, 4)
        data["weighted_coupon"] = round(data["total_coupon_weighted"] / data["principal"], 6) if data["principal"] > 0 else 0.0
        del data["total_coupon_weighted"]

    return result


# --- Instrument Type Distribution ---

def instrument_type_distribution(
    instruments: List[DebtInstrument],
) -> Dict[str, Dict[str, float]]:
    """Distribution of instruments by rate type (fixed/floating) and currency."""
    total = sum(i.principal for i in instruments)
    if total <= 0:
        return {}

    result: Dict[str, Dict[str, float]] = {}
    for inst in instruments:
        # Use rate_type as the primary distribution key
        t = inst.rate_type.value if hasattr(inst, 'rate_type') else "unknown"
        if t not in result:
            result[t] = {"principal": 0.0, "count": 0}
        result[t]["principal"] += inst.principal
        result[t]["count"] += 1

    for t, data in result.items():
        data["share_pct"] = round(data["principal"] / total, 4)

    return result


# --- Coupon Distribution ---

def coupon_distribution(
    instruments: List[DebtInstrument],
    bins: Optional[List[float]] = None,
) -> Dict[str, int]:
    """Distribution of instruments by coupon rate ranges."""
    if bins is None:
        bins = [0.0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10, 1.0]

    labels = []
    for i in range(len(bins) - 1):
        labels.append(f"{bins[i]*100:.1f}%-{bins[i+1]*100:.1f}%")

    counts = {label: 0 for label in labels}
    for inst in instruments:
        for i in range(len(bins) - 1):
            if bins[i] <= inst.coupon < bins[i + 1]:
                counts[labels[i]] += 1
                break

    return counts


# --- Comprehensive Portfolio Summary ---

def portfolio_analytics(
    portfolio: Portfolio,
    weights: Optional[Dict[str, float]] = None,
    as_of: Optional[date] = None,
    discount_rate: float = 0.05,
) -> Dict:
    """Run comprehensive analytics on a portfolio."""
    instruments = portfolio.instruments
    total = sum(i.principal for i in instruments)

    if total <= 0 or not instruments:
        return {
            "total_principal": 0,
            "instrument_count": 0,
            "duration": portfolio_weighted_duration(portfolio, weights, as_of, discount_rate),
            "maturity_profile": {},
            "currency_exposure": {},
            "rate_type_decomposition": {},
            "instrument_type_distribution": {},
            "coupon_distribution": {},
            "maturity_wall": {},
        }

    return {
        "total_principal": round(total, 2),
        "instrument_count": len(instruments),
        "duration": portfolio_weighted_duration(portfolio, weights, as_of, discount_rate),
        "convexity": {
            "weighted": round(sum(
                (i.principal / total) * calc_convexity(i.coupon, i.principal, max(i.coupon, 0.001), i.years_to_maturity(as_of))
                for i in instruments
            ), 4),
        },
        "maturity_profile": maturity_profile(instruments, as_of),
        "currency_exposure": currency_exposure(instruments),
        "rate_type_decomposition": rate_type_decomposition(instruments),
        "instrument_type_distribution": instrument_type_distribution(instruments),
        "coupon_distribution": coupon_distribution(instruments),
        "maturity_wall": maturity_wall_analysis(instruments, as_of),
    }
