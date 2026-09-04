"""Maturity Ladder Optimizer — Smooth debt maturity profiles.

Given a portfolio with maturity concentrations (walls), recommends optimal
issuance across tenors (3M, 1Y, 2Y, 5Y, 10Y, 30Y) to create a smooth
maturity ladder while minimizing total cost of service.
"""

import math
from datetime import datetime, timezone, timedelta
from typing import Optional


def optimize_maturity_ladder(
    instruments: list[dict],
    target_avg_maturity: float = 7.0,
    total_issuance: float = 0,
    yield_curve: Optional[dict] = None,
    max_single_quarter_pct: float = 12.0,
) -> dict:
    """Recommend optimal maturity ladder to smooth out walls.

    Args:
        instruments: List of debt instruments with principal, coupon, maturity_date
        target_avg_maturity: Target weighted-average maturity in years
        total_issuance: New issuance amount to allocate across tenors
        yield_curve: Current yield curve {"3M": 0.042, "1Y": 0.040, ...}
        max_single_quarter_pct: Max % of total debt maturing in any single quarter

    Returns:
        Optimization result with recommended allocations and metrics
    """
    if not instruments:
        return {"error": "No instruments provided"}

    now = datetime.now(timezone.utc)
    total_principal = sum(float(i.get("principal_outstanding", i.get("principal", 0))) for i in instruments)
    if total_principal == 0:
        return {"error": "Total principal is zero"}

    # Default yield curve
    if not yield_curve:
        yield_curve = {
            "3M": 0.0442, "6M": 0.0430, "1Y": 0.0415, "2Y": 0.0415,
            "5Y": 0.0412, "7Y": 0.0420, "10Y": 0.0430, "20Y": 0.0455, "30Y": 0.0468,
        }

    # ── Step 1: Analyze current maturity distribution ──
    quarter_buckets = {}
    year_buckets = {}
    for inst in instruments:
        try:
            mat_date = datetime.strptime(inst.get("maturity_date", ""), "%Y-%m-%d")
            years_to_maturity = (mat_date - now).days / 365.25
            principal = float(inst.get("principal_outstanding", inst.get("principal", 0)))

            if years_to_maturity <= 0:
                bucket = "matured"
            elif years_to_maturity <= 0.25:
                bucket = "0-3M"
            elif years_to_maturity <= 0.5:
                bucket = "3-6M"
            elif years_to_maturity <= 1:
                bucket = "6M-1Y"
            elif years_to_maturity <= 2:
                bucket = "1-2Y"
            elif years_to_maturity <= 5:
                bucket = "2-5Y"
            elif years_to_maturity <= 10:
                bucket = "5-10Y"
            elif years_to_maturity <= 20:
                bucket = "10-20Y"
            else:
                bucket = "20-30Y"

            quarter_buckets[bucket] = quarter_buckets.get(bucket, 0) + principal
            year_key = str(mat_date.year)
            year_buckets[year_key] = year_buckets.get(year_key, 0) + principal
        except (ValueError, TypeError):
            continue

    # Current distribution percentages
    current_dist = {k: round(v / total_principal * 100, 2) for k, v in quarter_buckets.items()}

    # ── Step 2: Identify walls ──
    walls = []
    for bucket, pct in current_dist.items():
        if pct > max_single_quarter_pct:
            walls.append({
                "bucket": bucket,
                "percentage": pct,
                "amount": quarter_buckets[bucket],
                "severity": "critical" if pct > 20 else "warning",
            })

    # ── Step 3: Calculate current weighted average maturity ──
    weighted_maturity = 0
    for inst in instruments:
        try:
            mat_date = datetime.strptime(inst.get("maturity_date", ""), "%Y-%m-%d")
            years = max(0, (mat_date - now).days / 365.25)
            principal = float(inst.get("principal_outstanding", inst.get("principal", 0)))
            weighted_maturity += years * principal
        except (ValueError, TypeError):
            continue
    current_wam = weighted_maturity / total_principal if total_principal else 0

    # ── Step 4: Optimize target distribution ──
    # Target: smooth distribution across maturity buckets
    target_dist = {
        "0-3M": 5.0, "3-6M": 5.0, "6M-1Y": 8.0, "1-2Y": 12.0,
        "2-5Y": 20.0, "5-10Y": 25.0, "10-20Y": 15.0, "20-30Y": 10.0,
    }

    # Adjust targets based on current yield curve (favor lower-cost tenors)
    if yield_curve:
        # Map buckets to yield curve keys
        bucket_to_yield = {
            "0-3M": "3M", "3-6M": "6M", "6M-1Y": "1Y", "1-2Y": "2Y",
            "2-5Y": "5Y", "5-10Y": "10Y", "10-20Y": "20Y", "20-30Y": "30Y",
        }
        # Shift allocation toward cheaper tenors
        for bucket, target_pct in target_dist.items():
            yk = bucket_to_yield.get(bucket)
            if yk and yk in yield_curve:
                rate = yield_curve[yk]
                if rate < 0.042:  # Below average
                    target_dist[bucket] = target_pct * 1.15  # Boost cheap tenors
                elif rate > 0.045:  # Above average
                    target_dist[bucket] = target_pct * 0.85  # Reduce expensive tenors

    # Normalize to 100%
    total_target = sum(target_dist.values())
    target_dist = {k: round(v / total_target * 100, 2) for k, v in target_dist.items()}

    # ── Step 5: Calculate recommended actions ──
    actions = []
    total_gap = 0
    for bucket, target_pct in target_dist.items():
        current_pct = current_dist.get(bucket, 0)
        gap = target_pct - current_pct
        if abs(gap) > 2.0:  # Only recommend if gap > 2%
            target_amount = total_principal * target_pct / 100
            current_amount = quarter_buckets.get(bucket, 0)
            change_amount = target_amount - current_amount
            total_gap += abs(change_amount)

            # Map bucket to tenor for yield curve lookup
            bucket_to_tenor = {
                "0-3M": "3M", "3-6M": "6M", "6M-1Y": "1Y", "1-2Y": "2Y",
                "2-5Y": "5Y", "5-10Y": "10Y", "10-20Y": "20Y", "20-30Y": "30Y",
            }
            tenor = bucket_to_tenor.get(bucket, "")
            rate = yield_curve.get(tenor, 0)

            # Estimate annual cost
            annual_cost = change_amount * rate if change_amount > 0 else 0
            annual_savings = abs(change_amount) * rate if change_amount < 0 else 0

            actions.append({
                "bucket": bucket,
                "tenor": tenor,
                "current_pct": current_pct,
                "target_pct": target_pct,
                "gap_pct": round(gap, 2),
                "change_amount": round(change_amount, 0),
                "action": "issue" if change_amount > 0 else "let_mature",
                "yield_rate": rate,
                "annual_cost_impact": round(annual_cost, 0),
                "priority": "high" if abs(gap) > 8 else "medium",
            })

    # ── Step 6: Calculate improved WAM ──
    new_dist = {**current_dist}
    for a in actions:
        new_dist[a["bucket"]] = a["target_pct"]

    bucket_midpoints = {
        "0-3M": 0.125, "3-6M": 0.375, "6M-1Y": 0.75, "1-2Y": 1.5,
        "2-5Y": 3.5, "5-10Y": 7.5, "10-20Y": 15.0, "20-30Y": 25.0,
    }
    optimized_wam = sum(
        new_dist.get(b, 0) / 100 * m for b, m in bucket_midpoints.items()
    )

    # ── Step 7: Cost analysis ──
    total_annual_cost_before = sum(
        float(i.get("principal_outstanding", i.get("principal", 0))) * float(i.get("coupon_rate", i.get("coupon", 0)))
        for i in instruments
    )
    # Simplified: assume new issuance at current market rates
    new_issuance_cost = total_issuance * sum(yield_curve.values()) / len(yield_curve) if yield_curve else 0

    return {
        "current_state": {
            "total_principal": total_principal,
            "instrument_count": len(instruments),
            "current_wam_years": round(current_wam, 2),
            "maturity_distribution": current_dist,
            "walls_detected": walls,
            "wall_count": len(walls),
        },
        "target_state": {
            "target_wam_years": target_avg_maturity,
            "optimized_wam_years": round(optimized_wam, 2),
            "target_distribution": target_dist,
        },
        "actions": sorted(actions, key=lambda x: abs(x["gap_pct"]), reverse=True),
        "metrics": {
            "total_actions": len(actions),
            "total_reallocation": round(total_gap, 0),
            "current_annual_cost": round(total_annual_cost_before, 0),
            "walls_resolved": len([w for w in walls if w["severity"] == "critical"]),
            "wam_improvement": round(optimized_wam - current_wam, 2),
        },
        "yield_curve_used": yield_curve,
    }
