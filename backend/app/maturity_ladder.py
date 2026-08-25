"""Debt Maturity Ladder & Cash Flow Projection Engine.

Provides:
- Maturity ladder: bucket debt by year, visualize upcoming maturities
- Cash flow projection: model principal + interest payments annually
- Refinancing risk: identify dangerous maturity walls
- Redemption profile: amortization schedule for all instruments
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class MaturityBucket:
    year: int
    instruments: list = field(default_factory=list)
    total_principal: float = 0.0
    total_interest: float = 0.0
    count: int = 0


@dataclass
class CashFlowYear:
    year: int
    principal_repayments: float = 0.0
    interest_payments: float = 0.0
    total_outflows: float = 0.0
    new_issuances_needed: float = 0.0
    cumulative_deficit: float = 0.0
    refinancing_ratio: float = 0.0  # % of total debt maturing that year
    avg_coupon: float = 0.0
    currencies: dict = field(default_factory=dict)
    instrument_breakdown: dict = field(default_factory=dict)


class MaturityLadderEngine:
    """Constructs the maturity profile of a debt portfolio."""

    def __init__(self, instruments: list[dict], horizon_years: int = 20):
        self.instruments = instruments
        self.horizon = horizon_years
        self.current_year = datetime.now(timezone.utc).year

    def build_ladder(self) -> dict:
        """Build maturity ladder grouped by year."""
        buckets: dict[int, dict] = {}

        for inst in self.instruments:
            maturity_str = inst.get("maturity_date", "")
            if not maturity_str:
                continue
            try:
                mat_year = int(maturity_str[:4])
            except (ValueError, IndexError):
                continue

            if mat_year < self.current_year:
                mat_year = self.current_year  # already matured or maturing this year
            if mat_year > self.current_year + self.horizon:
                continue  # beyond horizon

            if mat_year not in buckets:
                buckets[mat_year] = {
                    "year": mat_year,
                    "instruments": [],
                    "total_principal": 0.0,
                    "total_interest": 0.0,
                    "count": 0,
                }

            principal = inst.get("principal_outstanding", 0)
            coupon = inst.get("coupon_rate", 0)
            annual_interest = principal * coupon

            buckets[mat_year]["instruments"].append({
                "id": inst.get("id", ""),
                "name": inst.get("name", ""),
                "type": inst.get("instrument_type", ""),
                "currency": inst.get("currency", "USD"),
                "principal": principal,
                "coupon_rate": coupon,
                "maturity_date": maturity_str,
            })
            buckets[mat_year]["total_principal"] += principal
            buckets[mat_year]["total_interest"] += annual_interest
            buckets[mat_year]["count"] += 1

        # Sort by year
        sorted_buckets = [buckets[y] for y in sorted(buckets.keys())]

        # Compute cumulative metrics
        total_debt = sum(inst.get("principal_outstanding", 0) for inst in self.instruments)
        running_matured = 0.0

        for bucket in sorted_buckets:
            running_matured += bucket["total_principal"]
            bucket["pct_of_total"] = (bucket["total_principal"] / total_debt * 100) if total_debt > 0 else 0
            bucket["cumulative_pct"] = (running_matured / total_debt * 100) if total_debt > 0 else 0

        # Identify maturity walls (years where >20% of total debt matures)
        wall_threshold = total_debt * 0.20
        walls = [
            {"year": b["year"], "amount": b["total_principal"], "pct": b["pct_of_total"]}
            for b in sorted_buckets if b["total_principal"] > wall_threshold
        ]

        # Smoothness score: 0 = perfectly smooth, 100 = all matures in one year
        principals = [b["total_principal"] for b in sorted_buckets]
        if principals and total_debt > 0:
            avg_per_year = total_debt / len(principals) if principals else 0
            max_deviation = max(abs(p - avg_per_year) for p in principals) if principals else 0
            smoothness_score = min(100, (max_deviation / avg_per_year * 100)) if avg_per_year > 0 else 0
        else:
            smoothness_score = 0

        return {
            "total_debt": total_debt,
            "horizon_years": self.horizon,
            "current_year": self.current_year,
            "num_instruments": len(self.instruments),
            "buckets": sorted_buckets,
            "maturity_walls": walls,
            "smoothness_score": round(smoothness_score, 1),
            "years_to_first_maturity": (
                sorted_buckets[0]["year"] - self.current_year
                if sorted_buckets else self.horizon
            ),
            "average_years_to_maturity": self._weighted_avg_maturity(),
        }

    def _weighted_avg_maturity(self) -> float:
        total_principal = 0.0
        weighted_sum = 0.0
        for inst in self.instruments:
            mat_str = inst.get("maturity_date", "")
            if not mat_str:
                continue
            try:
                mat_year = int(mat_str[:4])
            except (ValueError, IndexError):
                continue
            principal = inst.get("principal_outstanding", 0)
            years = max(0, mat_year - self.current_year)
            weighted_sum += principal * years
            total_principal += principal
        return round(weighted_sum / total_principal, 1) if total_principal > 0 else 0


class CashFlowProjectionEngine:
    """Projects annual cash flows from a debt portfolio."""

    def __init__(self, instruments: list[dict], horizon_years: int = 15, annual_budget: float = 0.0):
        self.instruments = instruments
        self.horizon = horizon_years
        self.current_year = datetime.now(timezone.utc).year
        self.annual_budget = annual_budget

    def project(self) -> dict:
        """Generate annual cash flow projections."""
        years = list(range(self.current_year, self.current_year + self.horizon + 1))
        cash_flows: dict[int, dict] = {}

        for year in years:
            cash_flows[year] = {
                "year": year,
                "principal_repayments": 0.0,
                "interest_payments": 0.0,
                "total_outflows": 0.0,
                "instruments_maturing": 0,
                "currencies": defaultdict(float),
                "instrument_types": defaultdict(float),
                "avg_coupon_weighted": 0.0,
            }

        total_interest_weight = 0.0
        total_interest_sum = 0.0

        for inst in self.instruments:
            mat_str = inst.get("maturity_date", "")
            if not mat_str:
                continue
            try:
                mat_year = int(mat_str[:4])
            except (ValueError, IndexError):
                continue

            principal = inst.get("principal_outstanding", 0)
            coupon = inst.get("coupon_rate", 0)
            currency = inst.get("currency", "USD")
            inst_type = inst.get("instrument_type", "unknown")

            # Interest is paid every year until maturity
            for year in years:
                if year < mat_year:
                    # Still outstanding — pay interest
                    annual_interest = principal * coupon
                    cash_flows[year]["interest_payments"] += annual_interest
                    cash_flows[year]["total_outflows"] += annual_interest
                    cash_flows[year]["currencies"][currency] += annual_interest
                    cash_flows[year]["instrument_types"][inst_type] += annual_interest
                elif year == mat_year:
                    # Maturity year — pay principal + final interest
                    cash_flows[year]["principal_repayments"] += principal
                    cash_flows[year]["total_outflows"] += principal + (principal * coupon)
                    cash_flows[year]["interest_payments"] += principal * coupon
                    cash_flows[year]["currencies"][currency] += principal + (principal * coupon)
                    cash_flows[year]["instrument_types"][inst_type] += principal
                    cash_flows[year]["instruments_maturing"] += 1
                    break

            total_interest_weight += principal * coupon * max(1, min(self.horizon, mat_year - self.current_year))
            total_interest_sum += principal * coupon

        # Calculate refinancing ratios and deficits
        total_debt = sum(inst.get("principal_outstanding", 0) for inst in self.instruments)
        cumulative_deficit = 0.0

        projection_years = []
        for year in years:
            cf = cash_flows[year]
            cf["refinancing_ratio"] = (
                cf["principal_repayments"] / total_debt * 100
                if total_debt > 0 else 0
            )

            # New issuances needed = principal maturing (to maintain debt level)
            cf["new_issuances_needed"] = cf["principal_repayments"]

            # Net cash flow
            if self.annual_budget > 0:
                cf["net_cash_flow"] = self.annual_budget - cf["total_outflows"]
                cumulative_deficit += cf["net_cash_flow"]
            else:
                cf["net_cash_flow"] = cf["new_issuances_needed"] - cf["total_outflows"]

            cf["cumulative_deficit"] = cumulative_deficit

            # Convert defaultdicts
            cf["currencies"] = dict(cf["currencies"])
            cf["instrument_types"] = dict(cf["instrument_types"])

            projection_years.append(cf)

        # Refinancing risk score
        max_annual_repay = max((cf["principal_repayments"] for cf in projection_years), default=0)
        avg_annual_repay = (
            sum(cf["principal_repayments"] for cf in projection_years) / len(projection_years)
            if projection_years else 0
        )
        concentration_ratio = (max_annual_repay / avg_annual_repay) if avg_annual_repay > 0 else 0
        refinancing_risk = min(100, concentration_ratio * 25)

        # Debt service coverage ratio (if budget provided)
        if self.annual_budget > 0:
            avg_annual_outflow = (
                sum(cf["total_outflows"] for cf in projection_years) / len(projection_years)
                if projection_years else 0
            )
            dscr = self.annual_budget / avg_annual_outflow if avg_annual_outflow > 0 else float("inf")
        else:
            dscr = None

        # Upcoming maturity wall in next 3 years
        near_term_repay = sum(
            cf["principal_repayments"]
            for cf in projection_years
            if cf["year"] <= self.current_year + 3
        )

        return {
            "total_debt": total_debt,
            "horizon_years": self.horizon,
            "annual_budget": self.annual_budget,
            "projections": projection_years,
            "summary": {
                "total_interest_over_horizon": sum(cf["interest_payments"] for cf in projection_years),
                "total_principal_repayments": sum(cf["principal_repayments"] for cf in projection_years),
                "total_outflows": sum(cf["total_outflows"] for cf in projection_years),
                "max_single_year_repayment": max_annual_repay,
                "avg_annual_repayment": round(avg_annual_repay, 2),
                "refinancing_risk_score": round(refinancing_risk, 1),
                "concentration_ratio": round(concentration_ratio, 2),
                "debt_service_coverage_ratio": round(dscr, 2) if dscr is not None else None,
                "near_term_maturities_3yr": near_term_repay,
                "near_term_pct": round(near_term_repay / total_debt * 100, 1) if total_debt > 0 else 0,
            },
        }


def generate_refinancing_recommendations(maturity_data: dict, cash_flow_data: dict) -> list[dict]:
    """Generate actionable recommendations based on maturity and cash flow analysis."""
    recs = []

    # Check maturity walls
    walls = maturity_data.get("maturity_walls", [])
    if walls:
        for wall in walls:
            recs.append({
                "type": "maturity_wall",
                "severity": "high",
                "year": wall["year"],
                "message": (
                    f"Maturity wall in {wall['year']}: ${wall['amount'] / 1e9:.1f}B "
                    f"({wall['pct']:.0f}% of total debt) matures. "
                    f"Consider extending maturities through buy-backs or new long-dated issuance."
                ),
                "action": f"Begin refinancing preparations for {wall['year']} at least 18 months in advance.",
            })

    # Check refinancing risk
    summary = cash_flow_data.get("summary", {})
    risk_score = summary.get("refinancing_risk_score", 0)
    if risk_score > 50:
        recs.append({
            "type": "refinancing_risk",
            "severity": "high",
            "message": (
                f"High refinancing concentration (risk score: {risk_score}). "
                f"Max single-year repayment is ${summary.get('max_single_year_repayment', 0) / 1e9:.1f}B."
            ),
            "action": "Diversify maturity profile by issuing across multiple tenors.",
        })

    # Check near-term maturities
    near_pct = summary.get("near_term_pct", 0)
    if near_pct > 30:
        recs.append({
            "type": "near_term_pressure",
            "severity": "medium",
            "message": (
                f"{near_pct:.0f}% of debt matures within 3 years "
                f"(${summary.get('near_term_maturities_3yr', 0) / 1e9:.1f}B)."
            ),
            "action": "Prioritize long-dated issuance to push maturities further out.",
        })

    # Check smoothness
    smoothness = maturity_data.get("smoothness_score", 0)
    if smoothness > 40:
        recs.append({
            "type": "uneven_profile",
            "severity": "medium",
            "message": (
                f"Maturity profile uneven (smoothness score: {smoothness}/100). "
                f"This creates volatile annual refinancing needs."
            ),
            "action": "Target a smoother maturity profile with evenly distributed tenors.",
        })

    # Check DSCR
    dscr = summary.get("debt_service_coverage_ratio")
    if dscr is not None and dscr < 2.0:
        recs.append({
            "type": "dscr_low",
            "severity": "high" if dscr < 1.5 else "medium",
            "message": f"Debt service coverage ratio is {dscr:.1f}x (below recommended 2.0x).",
            "action": "Increase revenue or reduce debt service through refinancing at lower rates.",
        })

    # Currency concentration
    all_currencies = defaultdict(float)
    for cf in cash_flow_data.get("projections", []):
        for ccy, amt in cf.get("currencies", {}).items():
            all_currencies[ccy] += amt

    if all_currencies:
        total_outflow = sum(all_currencies.values())
        max_ccy = max(all_currencies.items(), key=lambda x: x[1])
        max_pct = max_ccy[1] / total_outflow * 100 if total_outflow > 0 else 0
        if max_pct > 60:
            recs.append({
                "type": "currency_concentration",
                "severity": "medium",
                "message": (
                    f"Currency concentration: {max_ccy[0]} accounts for {max_pct:.0f}% "
                    f"of total outflows over the projection horizon."
                ),
                "action": "Diversify into other currencies to reduce FX risk.",
            })

    return recs
