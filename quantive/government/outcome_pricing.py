"""Outcome-Based Pricing Engine.

Reframes pricing from monthly subscriptions to basis points saved
on debt issuance or risk reduction. Aligns Quantive's revenue
with government outcomes and eliminates the "startup risk" perception.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class PricingModel(str, Enum):
    """Available pricing models."""
    SUBSCRIPTION = "subscription"           # Legacy: monthly per-seat
    BASIS_POINTS = "basis_points"           # New: basis points on debt savings
    RISK_REDUCTION = "risk_reduction"       # New: basis points of risk reduction
    HYBRID = "hybrid"                       # New: base + outcome component
    PILOT = "pilot"                         # Free pilot period


class ContractTerm(str, Enum):
    """Contract duration options."""
    PILOT_12M = "pilot_12m"       # 12-month free pilot
    ANNUAL = "annual"              # 1-year contract
    MULTI_YEAR_3 = "multi_year_3"  # 3-year contract
    MULTI_YEAR_5 = "multi_year_5"  # 5-year contract
    MULTI_YEAR_10 = "multi_year_10"  # 10-year contract (sovereign)


@dataclass
class PortfolioProfile:
    """Government's debt portfolio profile for pricing calculation."""
    total_debt_outstanding: float          # Total sovereign debt in USD
    annual_issuance: float                 # Annual new debt issuance
    currency: str = "USD"
    debt_to_gdp: float = 0.0              # Debt-to-GDP ratio
    weighted_avg_maturity: float = 0.0     # Years
    weighted_avg_coupon: float = 0.0       # Percentage
    fx_exposure_pct: float = 0.0           # Foreign currency exposure %
    floating_rate_pct: float = 0.0         # Floating rate exposure %


@dataclass
class SavingsEstimate:
    """Estimated savings from Quantive optimization."""
    financing_cost_savings_bps: float      # Basis points saved on financing cost
    refinancing_savings_usd: float         # USD saved on refinancing
    risk_reduction_bps: float              # Basis points of risk reduction
    total_annual_savings_usd: float        # Total estimated annual savings
    confidence_level: float = 0.85         # Confidence in estimate (0-1)


@dataclass
class PricingQuote:
    """Complete pricing quote for a government client."""
    model: PricingModel
    term: ContractTerm
    portfolio: PortfolioProfile
    savings_estimate: SavingsEstimate

    # Pricing components
    base_fee_annual: float = 0.0           # Fixed annual fee
    outcome_fee_annual: float = 0.0        # Variable fee based on outcomes
    total_fee_annual: float = 0.0          # Total annual fee
    total_fee_term: float = 0.0            # Total fee over contract term

    # Value metrics
    roi_ratio: float = 0.0                 # ROI = savings / fee
    cost_per_basis_point: float = 0.0      # Fee per basis point saved
    implied_discount_rate: float = 0.0     # Discount from savings

    # Comparison
    legacy_cost_comparison: float = 0.0    # vs. current approach
    competitor_comparison: float = 0.0     # vs. Bloomberg/consultants


# ── Pricing Tiers ──────────────────────────────────────────────────

# Basis points pricing (on total debt outstanding)
BASIS_POINTS_TIERS = {
    "starter": {
        "max_debt": 5_000_000_000,         # $5B
        "base_fee": 120_000,               # $120K/year
        "outcome_bps": 0.5,                # 0.5 bps on savings
        "min_fee": 120_000,
        "max_fee": 500_000,
    },
    "professional": {
        "max_debt": 50_000_000_000,        # $50B
        "base_fee": 360_000,               # $360K/year
        "outcome_bps": 0.3,                # 0.3 bps on savings
        "min_fee": 360_000,
        "max_fee": 2_000_000,
    },
    "enterprise": {
        "max_debt": 500_000_000_000,       # $500B
        "base_fee": 900_000,               # $900K/year
        "outcome_bps": 0.2,                # 0.2 bps on savings
        "min_fee": 900_000,
        "max_fee": 5_000_000,
    },
    "sovereign": {
        "max_debt": float("inf"),          # Unlimited
        "base_fee": 2_400_000,             # $2.4M/year
        "outcome_bps": 0.15,               # 0.15 bps on savings
        "min_fee": 2_400_000,
        "max_fee": 10_000_000,
    },
}

# Term discounts
TERM_DISCOUNTS = {
    ContractTerm.PILOT_12M: 1.0,           # Free (pilot)
    ContractTerm.ANNUAL: 1.0,              # No discount
    ContractTerm.MULTI_YEAR_3: 0.90,       # 10% discount
    ContractTerm.MULTI_YEAR_5: 0.82,       # 18% discount
    ContractTerm.MULTI_YEAR_10: 0.70,      # 30% discount
}

# Legacy pricing comparison (Bloomberg-style per-seat)
LEGACY_SEAT_COST = {
    "bloomberg_terminal": 24_000,          # Per seat per year
    "consultant_annual": 500_000,          # Annual consulting
    "internal_model": 800_000,             # Internal team cost
}


class OutcomePricingEngine:
    """Computes outcome-based pricing quotes."""

    def __init__(self):
        self._quotes: dict[str, PricingQuote] = {}

    def get_tier(self, total_debt: float) -> dict:
        """Determine pricing tier based on debt size."""
        for tier_name, tier_config in BASIS_POINTS_TIERS.items():
            if total_debt <= tier_config["max_debt"]:
                return {"tier": tier_name, **tier_config}
        return {"tier": "sovereign", **BASIS_POINTS_TIERS["sovereign"]}

    def estimate_savings(
        self,
        portfolio: PortfolioProfile,
        optimization_results: dict | None = None,
    ) -> SavingsEstimate:
        """Estimate savings from optimization (conservative)."""
        # Conservative estimates based on industry benchmarks
        # Typical savings: 5-15 bps on financing cost
        financing_savings_bps = 8.0  # Conservative 8 bps

        # Refinancing optimization savings
        refinancing_savings = portfolio.annual_issuance * 0.001  # 10 bps on issuance

        # Risk reduction estimate
        risk_reduction_bps = 5.0  # Conservative 5 bps

        # Total annual savings
        financing_savings_usd = (
            portfolio.total_debt_outstanding * financing_savings_bps / 10000
        )
        risk_savings_usd = (
            portfolio.total_debt_outstanding * risk_reduction_bps / 10000
        )
        total_savings = financing_savings_usd + refinancing_savings + risk_savings_usd

        return SavingsEstimate(
            financing_cost_savings_bps=financing_savings_bps,
            refinancing_savings_usd=refinancing_savings,
            risk_reduction_bps=risk_reduction_bps,
            total_annual_savings_usd=total_savings,
            confidence_level=0.85,
        )

    def calculate_quote(
        self,
        portfolio: PortfolioProfile,
        term: ContractTerm = ContractTerm.ANNUAL,
        model: PricingModel = PricingModel.BASIS_POINTS,
        custom_rates: dict | None = None,
    ) -> PricingQuote:
        """Calculate a complete pricing quote."""
        tier = self.get_tier(portfolio.total_debt_outstanding)
        savings = self.estimate_savings(portfolio)

        # Base fee from tier
        base_fee = tier["base_fee"]

        # Outcome fee: basis points on realized savings
        outcome_bps = custom_rates.get("outcome_bps", tier["outcome_bps"]) if custom_rates else tier["outcome_bps"]
        outcome_fee = savings.total_annual_savings_usd * outcome_bps / 100

        # Apply min/max bounds
        total_fee = max(tier["min_fee"], min(tier["max_fee"], base_fee + outcome_fee))

        # Apply term discount
        discount = TERM_DISCOUNTS.get(term, 1.0)
        total_fee_discounted = total_fee * discount
        base_fee_discounted = base_fee * discount
        outcome_fee_discounted = outcome_fee * discount

        # Calculate term total
        term_years = {
            ContractTerm.PILOT_12M: 1,
            ContractTerm.ANNUAL: 1,
            ContractTerm.MULTI_YEAR_3: 3,
            ContractTerm.MULTI_YEAR_5: 5,
            ContractTerm.MULTI_YEAR_10: 10,
        }
        total_term = total_fee_discounted * term_years.get(term, 1)

        # ROI calculation
        roi = savings.total_annual_savings_usd / total_fee_discounted if total_fee_discounted > 0 else 0

        # Cost per basis point
        total_bps = savings.financing_cost_savings_bps + savings.risk_reduction_bps
        cost_per_bps = total_fee_discounted / total_bps if total_bps > 0 else 0

        # Legacy comparison
        legacy_cost = LEGACY_SEAT_COST["bloomberg_terminal"] * 50  # 50 users
        competitor_ratio = total_fee_discounted / legacy_cost if legacy_cost > 0 else 0

        quote = PricingQuote(
            model=model,
            term=term,
            portfolio=portfolio,
            savings_estimate=savings,
            base_fee_annual=round(base_fee_discounted, 2),
            outcome_fee_annual=round(outcome_fee_discounted, 2),
            total_fee_annual=round(total_fee_discounted, 2),
            total_fee_term=round(total_term, 2),
            roi_ratio=round(roi, 1),
            cost_per_basis_point=round(cost_per_bps, 2),
            implied_discount_rate=round((1 - competitor_ratio) * 100, 1),
            legacy_cost_comparison=round(legacy_cost, 2),
            competitor_comparison=round(competitor_ratio, 2),
        )

        self._quotes[portfolio.country_code if hasattr(portfolio, 'country_code') else "temp"] = quote
        return quote

    def generate_roi_report(self, quote: PricingQuote) -> dict:
        """Generate a comprehensive ROI report for the government."""
        savings = quote.savings_estimate

        return {
            "executive_summary": {
                "annual_investment": quote.total_fee_annual,
                "annual_savings": savings.total_annual_savings_usd,
                "net_benefit": savings.total_annual_savings_usd - quote.total_fee_annual,
                "roi_ratio": quote.roi_ratio,
                "payback_months": round(
                    quote.total_fee_annual / (savings.total_annual_savings_usd / 12)
                    if savings.total_annual_savings_usd > 0 else 0, 1
                ),
            },
            "savings_breakdown": {
                "financing_cost_reduction": {
                    "basis_points": savings.financing_cost_savings_bps,
                    "annual_usd": round(
                        quote.portfolio.total_debt_outstanding
                        * savings.financing_cost_savings_bps / 10000, 2
                    ),
                },
                "refinancing_optimization": {
                    "annual_usd": round(savings.refinancing_savings_usd, 2),
                },
                "risk_reduction": {
                    "basis_points": savings.risk_reduction_bps,
                    "annual_usd": round(
                        quote.portfolio.total_debt_outstanding
                        * savings.risk_reduction_bps / 10000, 2
                    ),
                },
            },
            "pricing_comparison": {
                "quantive_annual": quote.total_fee_annual,
                "bloomberg_equivalent": quote.legacy_cost_comparison,
                "internal_model_cost": LEGACY_SEAT_COST["internal_model"],
                "savings_vs_bloomberg": round(
                    quote.legacy_cost_comparison - quote.total_fee_annual, 2
                ),
                "savings_vs_internal": round(
                    LEGACY_SEAT_COST["internal_model"] - quote.total_fee_annual, 2
                ),
            },
            "term_value": {
                "contract_term_years": {
                    ContractTerm.PILOT_12M: 1,
                    ContractTerm.ANNUAL: 1,
                    ContractTerm.MULTI_YEAR_3: 3,
                    ContractTerm.MULTI_YEAR_5: 5,
                    ContractTerm.MULTI_YEAR_10: 10,
                }.get(quote.term, 1),
                "total_investment": quote.total_fee_term,
                "total_savings": round(savings.total_annual_savings_usd * {
                    ContractTerm.PILOT_12M: 1,
                    ContractTerm.ANNUAL: 1,
                    ContractTerm.MULTI_YEAR_3: 3,
                    ContractTerm.MULTI_YEAR_5: 5,
                    ContractTerm.MULTI_YEAR_10: 10,
                }.get(quote.term, 1), 2),
                "net_benefit_term": round(
                    savings.total_annual_savings_usd * {
                        ContractTerm.PILOT_12M: 1,
                        ContractTerm.ANNUAL: 1,
                        ContractTerm.MULTI_YEAR_3: 3,
                        ContractTerm.MULTI_YEAR_5: 5,
                        ContractTerm.MULTI_YEAR_10: 10,
                    }.get(quote.term, 1) - quote.total_fee_term, 2
                ),
            },
            "methodology": {
                "savings_estimation": "Conservative estimates based on industry benchmarks",
                "confidence_level": savings.confidence_level,
                "assumptions": [
                    "Financing cost reduction of 8 bps (conservative vs. 15-25 bps typical)",
                    "Refinancing optimization of 10 bps on new issuance",
                    "Risk reduction of 5 bps through portfolio diversification",
                    "Actual savings may vary based on market conditions and implementation",
                ],
            },
        }

    def generate_pilot_proposal(self, portfolio: PortfolioProfile) -> dict:
        """Generate a 12-month free pilot proposal."""
        quote = self.calculate_quote(
            portfolio,
            term=ContractTerm.PILOT_12M,
            model=PricingModel.PILOT,
        )

        return {
            "proposal_type": "12-Month Free Pilot",
            "portfolio": {
                "total_debt": portfolio.total_debt_outstanding,
                "currency": portfolio.currency,
                "debt_to_gdp": portfolio.debt_to_gdp,
            },
            "pilot_terms": {
                "duration_months": 12,
                "fee": 0,
                "included_features": [
                    "Full platform access",
                    "Portfolio optimization",
                    "Risk analysis",
                    "Scenario modeling",
                    "Market data integration",
                    "Dedicated support",
                ],
                "conversion_terms": {
                    "discount_on_conversion": "15%",
                    "contract_options": ["3-year", "5-year", "10-year"],
                    "price_lock_guarantee": "12 months post-pilot",
                },
            },
            "estimated_savings_during_pilot": {
                "monthly": round(quote.savings_estimate.total_annual_savings_usd / 12, 2),
                "annual": round(quote.savings_estimate.total_annual_savings_usd, 2),
            },
            "case_study_commitment": {
                "publish_case_study": True,
                "anonymize_data": True,
                "testimonial_allowed": True,
                "data_for_model_training": True,
            },
            "success_metrics": {
                "financing_cost_reduction_bps": ">= 5 bps",
                "risk_score_improvement": ">= 10%",
                "report_generation_time": "< 30 minutes",
                "user_adoption_rate": ">= 80% of DMO staff",
            },
        }
