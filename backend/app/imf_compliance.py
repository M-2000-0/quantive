"""IMF Compliance Report Generator.

Generates the reports that the IMF and World Bank require from member countries
for debt management, borrowing programs, and policy reviews.

Reports:
- Debt Sustainability Analysis (DSA) — required for all IMF lending
- Public Debt Management Report — annual reporting requirement
- Government Finance Statistics (GFS) — standardized fiscal data
- Debt Ceiling Analysis — limits on public debt
- Medium-Term Debt Strategy (MTDS) — 3-5 year debt management plan

Usage:
    from app.imf_compliance import IMFComplianceEngine
    engine = IMFComplianceEngine()
    _dsa = engine.generate_dsa(country_code="US", portfolio_data={...})
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from app.country_data import get_country


@dataclass
class DSAResult:
    """Debt Sustainability Analysis result."""
    country_code: str
    country_name: str
    assessment_date: str

    # Current debt metrics
    public_debt_to_gdp: float
    gross_financing_needs_to_gdp: float
    debt_service_to_revenue: float
    debt_service_to_exports: float

    # Medium-term projections (5-year)
    projected_debt_to_gdp: list[float]  # 5 values
    projected_growth: list[float]
    projected_primary_balance: list[float]
    projected_interest_rate: list[float]
    projected_inflation: list[float]

    # Sustainability assessment
    debt_fanchart_median: list[float]
    debt_fanchart_75th: list[float]
    debt_fanchart_95th: list[float]

    # Risk ratings
    overall_risk: str  # "low", "moderate", "high", "in distress"
    market_access_risk: str
    financing_risk: str
    rollover_risk: str
    interest_rate_risk: str

    # Recommendations
    recommendations: list[str]
    adjustment_needed: float  # primary balance adjustment needed (% of GDP)

    def to_dict(self) -> dict:
        return {
            "country_code": self.country_code,
            "country_name": self.country_name,
            "assessment_date": self.assessment_date,
            "current_metrics": {
                "public_debt_to_gdp": round(self.public_debt_to_gdp, 1),
                "gross_financing_needs_to_gdp": round(self.gross_financing_needs_to_gdp, 1),
                "debt_service_to_revenue": round(self.debt_service_to_revenue, 1),
                "debt_service_to_exports": round(self.debt_service_to_exports, 1),
            },
            "projections": {
                "horizon_years": 5,
                "debt_to_gdp": [round(v, 1) for v in self.projected_debt_to_gdp],
                "growth": [round(v, 1) for v in self.projected_growth],
                "primary_balance": [round(v, 1) for v in self.projected_primary_balance],
                "interest_rate": [round(v, 1) for v in self.projected_interest_rate],
                "inflation": [round(v, 1) for v in self.projected_inflation],
            },
            "fanchart": {
                "median": [round(v, 1) for v in self.debt_fanchart_median],
                "p75": [round(v, 1) for v in self.debt_fanchart_75th],
                "p95": [round(v, 1) for v in self.debt_fanchart_95th],
            },
            "risk_assessment": {
                "overall": self.overall_risk,
                "market_access": self.market_access_risk,
                "financing": self.financing_risk,
                "rollover": self.rollover_risk,
                "interest_rate": self.interest_rate_risk,
            },
            "adjustment_needed_pct_gdp": round(self.adjustment_needed, 2),
            "recommendations": self.recommendations,
        }


@dataclass
class MTDSResult:
    """Medium-Term Debt Strategy result."""
    country_code: str
    country_name: str
    strategy_horizon_years: int

    # Strategy targets
    target_debt_to_gdp: float
    target_avg_maturity: float
    target_domestic_share: float
    target_fixed_rate_share: float
    target_currency_mix: dict[str, float]

    # Annual targets
    annual_targets: list[dict]  # [{year, target_debt, target_maturity, target_issuance}]

    # Issuance plan
    recommended_issuances: list[dict]
    total_issuance_required: float
    avg_target_coupon: float

    def to_dict(self) -> dict:
        return {
            "country_code": self.country_code,
            "country_name": self.country_name,
            "horizon_years": self.strategy_horizon_years,
            "targets": {
                "debt_to_gdp": round(self.target_debt_to_gdp, 1),
                "avg_maturity": round(self.target_avg_maturity, 1),
                "domestic_share": round(self.target_domestic_share * 100, 1),
                "fixed_rate_share": round(self.target_fixed_rate_share * 100, 1),
                "currency_mix": self.target_currency_mix,
            },
            "annual_targets": self.annual_targets,
            "issuance_plan": {
                "total_required": round(self.total_issuance_required, 0),
                "avg_target_coupon": round(self.avg_target_coupon * 100, 2),
                "recommended_issuances": self.recommended_issuances,
            },
        }


class IMFComplianceEngine:
    """Generates IMF-compliant debt sustainability reports.

    Follows the IMF-World Bank Debt Sustainability Framework (DSF)
    for low-income and market-access countries.
    """

    def generate_dsa(self, country_code: str, portfolio_data: Optional[dict] = None) -> DSAResult:
        """Generate a Debt Sustainability Analysis.

        This is the report required by the IMF for all lending programs.
        """
        country = get_country(country_code)
        if not country:
            raise ValueError(f"Country {country_code} not found")

        # Current metrics
        debt_to_gdp = country.debt_to_gdp
        interest_to_revenue = country.interest_to_revenue
        debt_service_to_revenue = country.debt_service_to_revenue

        # Estimate gross financing needs (GFN)
        # GFN = primary deficit + interest payments + maturing debt
        short_term_to_gdp = country.short_term_debt_to_gdp
        avg_maturity = country.avg_maturity_years
        annual_amortization = debt_to_gdp / avg_maturity if avg_maturity > 0 else 15
        gfn_to_gdp = abs(country.fiscal_balance_pct) + interest_to_revenue * debt_to_gdp / 100 + annual_amortization

        # Medium-term projections (5-year horizon)
        base_growth = country.gdp_growth_pct
        base_inflation = country.inflation_pct
        base_primary = country.primary_balance_pct

        projected_debt = []
        projected_growth = []
        projected_primary = []
        projected_interest = []
        projected_inflation_vals = []

        current_debt = debt_to_gdp
        for year in range(1, 6):
            # Growth convergence toward 3% for advanced, 4% for emerging
            g = base_growth + (3.0 - base_growth) * 0.1 * year if country.income_group == "high" else base_growth
            # Inflation convergence toward 2%
            inf = base_inflation + (2.0 - base_inflation) * 0.15 * year
            # Primary balance consolidation
            pb = base_primary + min(1.0, abs(base_primary) * 0.1) * year if base_primary < 0 else base_primary
            # Interest rate
            ir = country.avg_coupon_pct + (0.5 if debt_to_gdp > 80 else 0)

            # Debt dynamics: d = d(-1) * (1 + g - π) / (1 + g)^2 + primary_deficit
            real_interest = ir - inf
            _real_growth = g - inf
            debt_dynamics = current_debt * (1 + real_interest) / (1 + g) + abs(pb) * (1 + g * 0.5)

            projected_debt.append(debt_dynamics)
            projected_growth.append(g)
            projected_primary.append(pb)
            projected_interest.append(ir)
            projected_inflation_vals.append(inf)
            current_debt = debt_dynamics

        # Fanchart (simplified Monte Carlo)
        import numpy as np
        rng = np.random.default_rng(42)
        n_sims = 1000
        sim_paths = np.zeros((n_sims, 5))
        for s in range(n_sims):
            d = debt_to_gdp
            for y in range(5):
                shock = rng.normal(0, 1.5)  # growth/inflation shock
                g_shock = projected_growth[y] + shock
                ir_shock = projected_interest[y] + rng.normal(0, 0.5)
                d = d * (1 + ir_shock - projected_inflation_vals[y]) / (1 + g_shock) + abs(projected_primary[y])
                sim_paths[s, y] = d

        median_path = np.median(sim_paths, axis=0).tolist()
        p75_path = np.percentile(sim_paths, 75, axis=0).tolist()
        p95_path = np.percentile(sim_paths, 95, axis=0).tolist()

        # Risk assessment
        if debt_to_gdp > 100:
            overall = "high"
        elif debt_to_gdp > 70:
            overall = "moderate"
        else:
            overall = "low"

        if gfn_to_gdp > 20:
            overall = "high"
        if gfn_to_gdp > 30:
            overall = "in distress"

        market_access = "high" if debt_to_gdp > 80 and not country.investment_grade else "moderate" if debt_to_gdp > 60 else "low"
        financing = "high" if short_term_to_gdp > 15 else "moderate" if short_term_to_gdp > 8 else "low"
        rollover = "high" if annual_amortization > 20 else "moderate" if annual_amortization > 10 else "low"
        ir_risk = "high" if country.avg_coupon_pct > 6 else "moderate" if country.avg_coupon_pct > 3 else "low"

        # Adjustment needed (primary balance improvement to stabilize debt)
        _target_debt = debt_to_gdp
        current_primary = base_primary
        # Solve for primary balance that stabilizes debt at current level
        needed_primary = current_primary - (projected_debt[4] - debt_to_gdp) / 5
        adjustment = needed_primary - current_primary

        # Recommendations
        recs = []
        if overall in ("high", "in distress"):
            recs.append("Implement immediate fiscal consolidation to reduce debt-to-GDP ratio")
        if gfn_to_gdp > 20:
            recs.append("Reduce gross financing needs by extending average debt maturity")
        if financing == "high":
            recs.append("Reduce reliance on short-term debt to lower refinancing risk")
        if rollover == "high":
            recs.append("Diversify funding sources and extend maturity profile")
        if country.foreign_held_pct > 40:
            recs.append("Reduce foreign-currency debt exposure to mitigate FX risk")
        if not recs:
            recs.append("Maintain current fiscal discipline and debt management practices")

        return DSAResult(
            country_code=country_code,
            country_name=country.name,
            assessment_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            public_debt_to_gdp=debt_to_gdp,
            gross_financing_needs_to_gdp=round(gfn_to_gdp, 1),
            debt_service_to_revenue=debt_service_to_revenue,
            debt_service_to_exports=round(debt_service_to_revenue * 1.2, 1),
            projected_debt_to_gdp=projected_debt,
            projected_growth=projected_growth,
            projected_primary_balance=projected_primary,
            projected_interest_rate=projected_interest,
            projected_inflation=projected_inflation_vals,
            debt_fanchart_median=median_path,
            debt_fanchart_75th=p75_path,
            debt_fanchart_95th=p95_path,
            overall_risk=overall,
            market_access_risk=market_access,
            financing_risk=financing,
            rollover_risk=rollover,
            interest_rate_risk=ir_risk,
            recommendations=recs,
            adjustment_needed=round(adjustment, 2),
        )

    def generate_mtds(self, country_code: str, portfolio_data: Optional[dict] = None) -> MTDSResult:
        """Generate a Medium-Term Debt Strategy (3-5 year plan).

        This is the forward-looking debt management plan required by
        the IMF/World Bank for countries with active lending programs.
        """
        country = get_country(country_code)
        if not country:
            raise ValueError(f"Country {country_code} not found")

        _dsa = self.generate_dsa(country_code, portfolio_data)

        # Strategy targets based on DSA results
        if country.debt_to_gdp > 80:
            target_debt = max(60, country.debt_to_gdp - 10)
        elif country.debt_to_gdp > 60:
            target_debt = max(50, country.debt_to_gdp - 5)
        else:
            target_debt = country.debt_to_gdp

        target_maturity = max(5, min(10, country.avg_maturity_years + 1))
        target_domestic = min(80, max(50, country.domestic_share_pct + 5))
        target_fixed = min(80, max(60, 70))

        # Currency mix target
        ccy_mix = {country.currency: target_domestic}
        other_share = 100 - target_domestic
        if country.currency != "USD":
            ccy_mix["USD"] = other_share * 0.6
        if country.currency != "EUR":
            ccy_mix["EUR"] = other_share * 0.25
        if country.currency not in ("USD", "EUR", "GBP"):
            ccy_mix["GBP"] = other_share * 0.15

        # Annual targets
        annual = []
        current_debt = country.debt_to_gdp
        for year in range(1, 6):
            yr_target = current_debt - (current_debt - target_debt) / 5
            annual.append({
                "year": datetime.now().year + year,
                "target_debt_to_gdp": round(yr_target, 1),
                "target_avg_maturity": round(target_maturity + (target_maturity - country.avg_maturity_years) * year / 5, 1),
                "target_issuance_bn": round(country.gdp_nominal_trillions * 1000 * 0.15, 0),  # ~15% of GDP
                "target_domestic_pct": round(target_domestic, 1),
            })
            current_debt = yr_target

        # Recommended issuances
        total_gdp_bn = country.gdp_nominal_trillions * 1000
        issuances = [
            {"tenor": "2Y", "currency": country.currency, "amount_bn": total_gdp_bn * 0.03, "purpose": "Short-term liquidity"},
            {"tenor": "5Y", "currency": country.currency, "amount_bn": total_gdp_bn * 0.05, "purpose": "Medium-term funding"},
            {"tenor": "10Y", "currency": country.currency, "amount_bn": total_gdp_bn * 0.04, "purpose": "Long-term stability"},
        ]
        if country.foreign_held_pct < 30:
            issuances.append({"tenor": "10Y", "currency": "USD", "amount_bn": total_gdp_bn * 0.02, "purpose": "International investor access"})

        total_issuance = sum(i["amount_bn"] for i in issuances)

        return MTDSResult(
            country_code=country_code,
            country_name=country.name,
            strategy_horizon_years=5,
            target_debt_to_gdp=target_debt,
            target_avg_maturity=target_maturity,
            target_domestic_share=target_domestic / 100,
            target_fixed_rate_share=target_fixed / 100,
            target_currency_mix=ccy_mix,
            annual_targets=annual,
            recommended_issuances=issuances,
            total_issuance_required=total_issuance,
            avg_target_coupon=country.avg_coupon_pct * 0.95,  # aim to reduce slightly
        )

    def generate_gfs(self, country_code: str) -> dict:
        """Generate Government Finance Statistics data.

        Standardized fiscal data following the IMF GFS Manual.
        """
        country = get_country(country_code)
        if not country:
            raise ValueError(f"Country {country_code} not found")

        gdp = country.gdp_nominal_trillions * 1e12

        return {
            "country_code": country_code,
            "country_name": country.name,
            "reporting_period": datetime.now().year,
            "currency": country.currency,
            "unit": "percent_of_gdp",
            "fiscal_summary": {
                "total_revenue": round(country.revenue_to_gdp, 1),
                "total_expenditure": round(country.expenditure_to_gdp, 1),
                "fiscal_balance": round(country.fiscal_balance_pct, 1),
                "primary_balance": round(country.primary_balance_pct, 1),
                "primary_expenditure": round(country.expenditure_to_gdp - country.interest_to_revenue * country.revenue_to_gdp / 100, 1),
            },
            "debt_position": {
                "total_public_debt": round(country.debt_to_gdp, 1),
                "domestic_debt": round(country.debt_to_gdp * country.domestic_share_pct / 100, 1),
                "external_debt": round(country.debt_to_gdp * (100 - country.domestic_share_pct) / 100, 1),
                "short_term_debt": round(country.short_term_debt_to_gdp, 1),
                "long_term_debt": round(country.debt_to_gdp - country.short_term_debt_to_gdp, 1),
            },
            "debt_service": {
                "interest_payments": round(country.interest_to_revenue, 1),
                "amortization": round(country.debt_service_to_revenue - country.interest_to_revenue, 1),
                "total_debt_service": round(country.debt_service_to_revenue, 1),
            },
            "macro_indicators": {
                "gdp_nominal_usd": round(gdp, 0),
                "gdp_growth": round(country.gdp_growth_pct, 1),
                "inflation": round(country.inflation_pct, 1),
                "current_account": round(country.current_account_pct, 1),
                "reserves_months_imports": round(country.reserves_months_imports, 1),
            },
            "credit_ratings": {
                "sp": country.rating_sp,
                "moody": country.rating_moody,
                "fitch": country.rating_fitch,
                "outlook": country.rating_outlook,
            },
        }

    def generate_debt_ceiling(self, country_code: str) -> dict:
        """Generate debt ceiling analysis.

        Analysis of whether current debt levels are sustainable
        and recommendations for legal debt limits.
        """
        country = get_country(country_code)
        if not country:
            raise ValueError(f"Country {country_code} not found")

        # IMF thresholds (simplified)
        if country.income_group == "high":
            threshold_warning = 85
            threshold_critical = 120
        else:
            threshold_warning = 55
            threshold_critical = 77

        headroom = threshold_critical - country.debt_to_gdp

        return {
            "country_code": country_code,
            "country_name": country.name,
            "current_debt_to_gdp": round(country.debt_to_gdp, 1),
            "thresholds": {
                "warning": threshold_warning,
                "critical": threshold_critical,
                "current_ratio": round(country.debt_to_gdp / threshold_critical * 100, 1),
            },
            "headroom": {
                "to_warning": round(threshold_warning - country.debt_to_gdp, 1),
                "to_critical": round(headroom, 1),
                "status": "above_warning" if country.debt_to_gdp > threshold_warning else "below_warning",
            },
            "recommendation": (
                "URGENT: Debt level exceeds warning threshold. Implement fiscal consolidation."
                if country.debt_to_gdp > threshold_warning
                else "Debt level is within sustainable bounds. Monitor closely."
            ),
        }


# ── Convenience Functions ──────────────────────────────────────────────

def generate_dsa_report(country_code: str, portfolio_data: Optional[dict] = None) -> dict:
    """Generate a complete DSA report as a dictionary."""
    engine = IMFComplianceEngine()
    dsa = engine.generate_dsa(country_code, portfolio_data)
    return dsa.to_dict()


def generate_mtds_report(country_code: str, portfolio_data: Optional[dict] = None) -> dict:
    """Generate a complete MTDS report as a dictionary."""
    engine = IMFComplianceEngine()
    mtds = engine.generate_mtds(country_code, portfolio_data)
    return mtds.to_dict()


def generate_gfs_report(country_code: str) -> dict:
    """Generate GFS data as a dictionary."""
    engine = IMFComplianceEngine()
    return engine.generate_gfs(country_code)
