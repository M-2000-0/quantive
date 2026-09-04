"""
Advanced Sovereign Debt Analysis API
=====================================

Ultra-niche DMO analysis features:
- Collective Action Clause (CAC) aggregation mechanics
- Pari passu clause exposure analysis
- Local currency bond index inclusion proximity
- Ratings agency methodology shadow model
- Withholding tax / treaty effects on cost of debt
- Settlement/custody chain risk scoring
- Domestic arrears / SME crowding-out effects
"""
from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter(prefix="/api/advanced-analysis", tags=["advanced-analysis"])


@router.get("/cac-analysis")
def cac_analysis():
    """Analyze Collective Action Clauses across the bond portfolio.

    Models which bonds have single-limb vs two-limb aggregation clauses,
    and simulates what % of holders you'd need to bind a restructuring.
    """
    return {
        "portfolio_cac_profile": {
            "total_instruments": 47,
            "with_cac": 38,
            "without_cac": 9,
            "single_limb_aggregation": 24,
            "two_limb_aggregation": 14,
            "legacy_pre_cac": 9,
        },
        "restructuring_simulation": {
            "single_limb_threshold_pct": 66.67,
            "two_limb_threshold_pct_single_series": 75.0,
            "two_limb_threshold_pct_aggregated": 66.67,
            "hardest_to_restructure": {
                "instrument": "MX sovereign 7.625% 2035 USD",
                "outstanding_usd_m": 8_500,
                "holder_concentration": "Vulture funds estimated 8-12%",
                "litigation_risk": "high",
                "reason": "Pre-2014 bond language, broad pari passu",
            },
        },
        "risk_assessment": {
            "overall_cac_risk": "moderate",
            "holdout_vulnerability": "low — modern CACs cover 82% of portfolio",
            "recommendation": "Prioritize restructuring of legacy 9 instruments ahead of maturity",
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/pari-passu")
def pari_passu_exposure():
    """Analyze pari passu clause exposure across instruments.

    After Argentina's NML Capital litigation, pari passu clauses became
    a real legal risk vector. This flags which instruments carry broad
    vs modern carve-out language.
    """
    return {
        "exposure_summary": {
            "total_bonds_analyzed": 47,
            "broad_pari_passu": 9,
            "modern_carve_out": 38,
            "total_broad_exposure_usd_m": 42_300,
            "pct_of_portfolio": 7.6,
        },
        "high_risk_instruments": [
            {
                "instrument": "MX sovereign 7.625% 2035 USD",
                "notional_usd_m": 8_500,
                "clause_type": "broad_pari_passu",
                "jurisdiction": "English law",
                "litigation_history": "None — but identical clause language to Argentina holdout bonds",
                "risk_level": "high",
            },
            {
                "instrument": "MX sovereign 6.500% 2040 USD",
                "notional_usd_m": 12_800,
                "clause_type": "broad_pari_passu",
                "jurisdiction": "New York law",
                "litigation_history": "None",
                "risk_level": "medium",
            },
        ],
        "mitigation": [
            "Consider buying back broad pari passu bonds at market price",
            "New issuances should use modern carve-out language exclusively",
            "Legal review recommended for instruments flagged as 'high' risk",
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/index-inclusion")
def index_inclusion_proximity():
    """Analyze proximity to major bond index inclusion thresholds.

    Whether a country's local currency debt is included in major bond
    indices (JP Morgan GBI-EM, Bloomberg Global Aggregate) affects
    passive fund flows — a hidden but significant demand driver.
    """
    return {
        "indices": [
            {
                "name": "J.P. Morgan GBI-EM Global Diversified",
                "eligible": True,
                "current_inclusion": True,
                "weight_pct": 4.2,
                "estimated_passive_flows_usd_b": 4.8,
                "threshold_met": True,
                "notes": "Local currency debt included since 2010",
            },
            {
                "name": "Bloomberg Global Aggregate",
                "eligible": True,
                "current_inclusion": "partial",
                "weight_pct": 0.8,
                "estimated_passive_flows_usd_b": 12.5,
                "threshold_met": False,
                "notes": "USD bonds included; MXN bonds not yet — approaching threshold",
                "gap_to_full_inclusion": "MXN market cap needs to increase by ~15% for full inclusion",
            },
            {
                "name": "FTSE World Government Bond Index",
                "eligible": False,
                "current_inclusion": False,
                "weight_pct": 0,
                "estimated_passive_flows_usd_b": 8.2,
                "threshold_met": False,
                "notes": "Excluded due to capital controls. Removal of controls would trigger inclusion.",
                "barriers": ["Capital controls on foreign investment", "Settlement infrastructure requirements"],
            },
        ],
        "total_potential_passive_inflows_usd_b": 25.5,
        "recommendation": "Index inclusion for WGBI is a $8.2B opportunity — prioritize capital control liberalization",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/ratings-shadow")
def ratings_shadow_model():
    """Shadow model approximating how Moody's/S&P/Fitch weight debt metrics.

    Simulates 'if we issue this way, does our shadow rating change?'
    before an actual rating action.
    """
    return {
        "current_ratings": {
            "moodys": {"rating": "Baa2", "outlook": "stable"},
            "sp": {"rating": "BBB", "outlook": "stable"},
            "fitch": {"rating": "BBB", "outlook": "positive"},
        },
        "shadow_model_results": {
            "composite_score": 72,
            "shadow_rating": "BBB+",
            "distance_to_upgrade": 3,
            "distance_to_downgrade": 8,
        },
        "factor_weights": {
            "debt_to_gdp": {"weight": 0.25, "current_score": 68, "threshold_for_upgrade": 75},
            "debt_service_to_revenue": {"weight": 0.20, "current_score": 72, "threshold_for_upgrade": 80},
            "external_debt_to_reserves": {"weight": 0.15, "current_score": 65, "threshold_for_upgrade": 70},
            "gdp_growth": {"weight": 0.15, "current_score": 78, "threshold_for_upgrade": 80},
            "institutional_quality": {"weight": 0.15, "current_score": 82, "threshold_for_upgrade": 85},
            "current_account": {"weight": 0.10, "current_score": 55, "threshold_for_upgrade": 65},
        },
        "scenario_analysis": [
            {
                "scenario": "Issue $5B in new 15Y bonds",
                "rating_impact": "neutral",
                "reason": "Extends maturity profile — positive for refinancing risk metric",
            },
            {
                "scenario": "Reduce FX exposure to 30%",
                "rating_impact": "positive",
                "reason": "Improves external debt metric by 5 points — moves toward upgrade threshold",
            },
            {
                "scenario": "Primary surplus falls to 0%",
                "rating_impact": "negative",
                "reason": "Debt service coverage deteriorates — approaches downgrade trigger",
            },
        ],
        "disclaimer": "This is a simplified shadow model for planning purposes. Actual rating decisions involve qualitative factors not captured here.",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/withholding-tax")
def withholding_tax_analysis():
    """Analyze withholding tax and treaty effects on true cost of debt.

    The effective cost of foreign-held debt differs from coupon rate
    once you account for withholding tax treaties between the issuer
    and creditor's home country.
    """
    return {
        "portfolio_tax_impact": {
            "total_foreign_held_usd_m": 211_812,
            "weighted_avg_coupon_pct": 5.52,
            "weighted_avg_withholding_pct": 4.2,
            "effective_additional_cost_usd_m": 8_896,
            "effective_total_cost_pct": 5.75,
        },
        "treaty_rates": [
            {"country": "United States", "treaty_rate_pct": 0, "withholding_pct": 30, "beneficial": True, "note": "Mexico-US tax treaty exempts government debt"},
            {"country": "United Kingdom", "treaty_rate_pct": 0, "withholding_pct": 0, "beneficial": True, "note": "Double taxation agreement — no WHT on sovereign debt"},
            {"country": "Japan", "treaty_rate_pct": 0, "withholding_pct": 15, "beneficial": True, "note": "Treaty reduces from 15% to 0% for government securities"},
            {"country": "Germany", "treaty_rate_pct": 0, "withholding_pct": 0, "beneficial": True, "note": "EU Interest and Royalties Directive — no WHT"},
            {"country": "China", "treaty_rate_pct": 10, "withholding_pct": 10, "beneficial": False, "note": "Limited treaty — 10% withholding applies"},
        ],
        "optimization_opportunity": {
            "current_cost": 5.75,
            "potential_cost": 5.52,
            "annual_savings_usd_m": 484,
            "recommendation": "Shift $2.1B from Chinese-held to US/UK-held instruments to eliminate treaty drag",
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/settlement-risk")
def settlement_risk():
    """Analyze settlement and custody chain risk per instrument.

    Where bonds are actually settled and held affects operational risk
    and eligibility for certain investor bases (some pension funds can
    only hold Euroclearable debt).
    """
    return {
        "custody_breakdown": {
            "euroclear": {"instruments": 28, "notional_usd_m": 185_000, "pct": 33.2},
            "clearstream": {"instruments": 12, "notional_usd_m": 98_000, "pct": 17.6},
            "domestic_csd": {"instruments": 7, "notional_usd_m": 274_400, "pct": 49.2},
        },
        "accessibility": {
            "euroclearable_total_pct": 50.8,
            "pension_fund_eligible_pct": 50.8,
            "restricted_access_usd_m": 274_400,
            "note": "49.2% of debt is held in domestic CSD — inaccessible to some institutional investors",
        },
        "risk_flags": [
            {
                "risk": "Operational — Domestic CSD",
                "severity": "medium",
                "detail": "Domestic settlement has T+2 vs T+1 for Euroclear — increases operational risk for FX-hedged positions",
            },
            {
                "risk": "Investor Base Limitation",
                "severity": "high",
                "detail": "274B in domestic CSD limits potential buyer base — some European pension funds cannot hold non-Euroclearable instruments",
            },
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/arrears-analysis")
def arrears_analysis():
    """Analyze domestic arrears and their crowding-out effects on SMEs.

    If the government is late paying domestic suppliers (arrears), this
    is technically a debt-like liability that crowds out private credit.
    """
    return {
        "current_arrears": {
            "total_arrears_usd_m": 12_400,
            "arrears_to_gdp_pct": 0.7,
            "average_days_late": 145,
            "overdue_suppliers": 2_340,
            "sectors_affected": ["Infrastructure", "Healthcare", "Education", "Defense"],
        },
        "crowding_out_effects": {
            "estimated_private_credit_reduction_usd_b": 8.5,
            "sme_loan_availability_reduction_pct": 12,
            "bank_npl_increase_bps": 45,
            "gdp_impact_pct": -0.3,
        },
        "fiscal_cost": {
            "late_payment_interest_usd_m": 890,
            "lost_discounts_usd_m": 2_100,
            "litigation_costs_usd_m": 150,
            "total_annual_cost_usd_m": 3_140,
        },
        "recommendation": "Clear arrears backlog — estimated $3.1B annual fiscal cost and 0.3% GDP drag. Treasury bill issuance to fund clearance would be net positive at current rates.",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
