"""Layer 10: The Quantive Brain - Government Reasoning Engine.

The Quantive Brain integrates all previous layers (1-9) to provide
government-level reasoning across:
- Refinancing risk analysis
- Debt profile diagnostics
- Dangerous assumption identification
- Cross-layer systemic risk assessment

It queries:
- Assumption registry (Layer 2: institutional_memory)
- Risk modules: fiscal, climate, geopolitical, cyber, supply_chain (Layer 6)
- Early warning indicators (Layer 7)
- Digital twin / simulation outputs
- Portfolio & optimization data (Layers 1-5)
- Procurement data
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import numpy as np

from pydantic import BaseModel, Field

from quantive.models.instruments import Portfolio, DebtInstrument
from quantive.models.results import (
    OptimizationResult,
    Strategy,
    StressTestResult,
    RiskMetrics,
    ScenarioResult,
)
from quantive.models.institutional_memory import (
    VersionedAssumption,
    AssumptionCategory,
    get_policy_rationale,
    register_assumption,
    transition_administration,
)
from quantive.scenarios.engine import ScenarioEngine
from quantive.objectives.spec import build_spec, ProblemSpec
from quantive.objectives.costs import scenario_costs, scenario_cost_matrix
from quantive.risk.fiscal import FiscalRisk, FiscalPressure, SovereignRiskIndicator
from quantive.risk.climate import ClimateRisk, ClimateScenario, ClimateImpact
from quantive.risk.geopolitical import GeopoliticalRisk, GeopoliticalEvent, ConflictType
from quantive.risk.cyber import CyberRisk, CyberVulnerability, CyberThreat
from quantive.risk.supply_chain import SupplyChainRisk, SupplyChainDisruption, DisruptionType
from quantive.early_warning.indicators import (
    DEBT_TO_GDP_CONFIG,
    DEBT_SERVICE_CONFIG,
    EXTERNAL_FINANCING_NEEDS_CONFIG,
    LIQUIDITY_COVERAGE_RATIO_CONFIG,
    CDS_SPREAD_CONFIG,
    PRIMARY_BALANCE_CONFIG,
    TAX_REVENUE_Volatility_CONFIG,
    REVENUE_VOLATILITY_CONFIG,
    TAX_BASE_CONTRACTION_CONFIG,
    PENSION_FUNDING_RATIO_CONFIG,
    PENSION_DEMOGRAPHIC_RATIO_CONFIG,
)
from quantive.strategies import generate_strategies, solve_profile
from quantive.orchestration import run_full_job
from quantive.solvers.registry import get_solver
from quantive.models.enums import StrategyProfile, Currency, RateType


# ── Core Reasoning Output Models ──────────────────────────────────────────

class RefinancingRiskAssessment(BaseModel):
    """Refinancing risk assessment across all scenarios."""
    id: str = Field(default_factory=lambda: f"refi-risk-{datetime.utcnow().timestamp()}")
    portfolio_id: str
    overall_refinancing_risk: float = Field(ge=0, le=100, description="0-100 scale")
    peak_year_maturity: float = Field(ge=0, description="Largest single-year maturing amount")
    years_with_excess_refi: int = Field(ge=0, description="Years exceeding safe refi thresholds")
    stress_breach_count: int = Field(ge=0, description="Breaches under liquidity stress")
    maturity_distribution: Dict[int, float] = Field(default_factory=dict, description="Per-year maturing amounts")
    recommendations: List[str] = Field(default_factory=list)


class DebtProfileDiagnosis(BaseModel):
    """Diagnosis of why the debt profile is worsening."""
    id: str = Field(default_factory=lambda: f"debt-profile-{datetime.utcnow().timestamp()}")
    portfolio_id: str
    overall_trend: str = Field(description="'improving' | 'stable' | 'deteriorating'")
    key_drivers: List[Dict[str, str]] = Field(default_factory=list, description="driver -> impact assessment")
    contributing_assumptions: List[str] = Field(default_factory=list, description="assumption IDs")
    risk_indicator_trajectory: Dict[str, str] = Field(
        default_factory=dict, description="indicator -> direction"
    )
    timeline_to_crisis_years: Optional[float] = Field(
        default=None, description="Years until crisis if trend continues"
    )


class DangerousAssumptions(BaseModel):
    """Assumption identified as most dangerous for government finances."""
    id: str = Field(default_factory=lambda: f"dangerous-assumption-{datetime.utcnow().timestamp()}")
    assumption_id: str
    name: str
    category: str
    current_value: float
    baseline: float
    risk_score: float = Field(ge=0, le=100, description="Cross-layer risk score 0-100")
    trend: str = Field(description="'improving' | 'stable' | 'deteriorating'")
    associated_risks: List[Dict[str, Any]] = Field(default_factory=list)
    initiated_by: Optional[str] = Field(default=None, description="Minister/admin who initiated")
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    years_til_trigger: Optional[float] = Field(
        default=None, description="Years until this assumption triggers a crisis"
    )


class CrossLayerReasoning(BaseModel):
    """Integrated reasoning across all 9 layers."""
    id: str = Field(default_factory=lambda: f"cross-layer-{datetime.utcnow().timestamp()}")
    portfolio_id: str
    layer_assessments: Dict[str, Any] = Field(
        default_factory=dict, description="layer_name -> assessment mapping"
    )
    systemic_risks: List[Dict[str, str]] = Field(
        default_factory=list, description="identified systemic risks"
    )
    recommendations: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1, description="0-1 confidence score")


# ── Quantive Brain: Reasoning functions ────────────────────────────────────
# These integrate Layer 2 (institutional memory / assumptions), Layer 5/7
# (early warning), Layer 6 (risk modules) and Layer 1 (scenario engine) to
# produce government-level reasoning outputs.

_SAFE_REFI_PCT = 0.20  # safe annual refinancing share of total debt
_STRESS_LIQUIDITY = 0.10  # liquidity coverage assumed under stress


def _maturity_year(instrument: DebtInstrument, as_of: Optional[date] = None) -> int:
    return instrument.maturity_date.year


def assess_refinancing_risk(
    portfolio: Portfolio,
    assumptions: Optional[List[VersionedAssumption]] = None,
    as_of: Optional[date] = None,
) -> RefinancingRiskAssessment:
    """Assess refinancing risk across the portfolio's maturity ladder.

    Combines the maturity distribution with a liquidity-stress test. A year
    is flagged as 'excess refinancing' when its maturing amount exceeds the
    safe share of a rolling average, and stress breaches occur when front-end
    concentration exceeds the stress liquidity threshold.
    """
    instrs = [i for i in portfolio.instruments if i.maturity_date is not None]
    if not instrs:
        return RefinancingRiskAssessment(
            portfolio_id=portfolio.id,
            overall_refinancing_risk=0.0,
            peak_year_maturity=0.0,
            years_with_excess_refi=0,
            stress_breach_count=0,
            maturity_distribution={},
            recommendations=["No maturing instruments to assess."],
        )

    distribution: Dict[int, float] = {}
    for inst in instrs:
        year = _maturity_year(inst, as_of)
        distribution[year] = distribution.get(year, 0.0) + inst.principal

    total = sum(distribution.values())
    peak_year = max(distribution, key=distribution.get)
    peak_amount = distribution[peak_year]
    avg_yearly = total / max(len(distribution), 1)

    excess_years = [
        y for y, amt in distribution.items()
        if amt > _SAFE_REFI_PCT * total and amt > avg_yearly
    ]
    # Longest consecutive run of elevated years
    consecutive = 0
    best_consecutive = 0
    sorted_years = sorted(distribution)
    for i, y in enumerate(sorted_years):
        if y in excess_years:
            consecutive += 1
            best_consecutive = max(best_consecutive, consecutive)
        else:
            consecutive = 0

    # Stress test: if the peak year exceeds the stress liquidity share of total
    stress_breaches = sum(
        1 for amt in distribution.values() if amt > _STRESS_LIQUIDITY * total
    )

    # Composite 0-100 score
    peak_ratio = peak_amount / total if total else 0.0
    concentration_factor = peak_ratio / 0.30 if peak_ratio < 0.30 else 1.0
    risk_score = min(
        100.0,
        round(
            concentration_factor * 55
            + (best_consecutive / 3.0) * 25
            + (stress_breaches / max(len(distribution), 1)) * 20
            + (1.0 - min(total / max(avg_yearly * 4, 1), 1.0)) * 10,
            1,
        ),
    )

    recommendations = []
    if best_consecutive >= 2:
        recommendations.append(
            f"Stagger maturities: {best_consecutive} consecutive years exceed the "
            f"safe refinancing share. Smooth the ladder to reduce rollover clustering."
        )
    if peak_ratio > 0.30:
        recommendations.append(
            f"Peak-year concentration at {peak_ratio:.0%} of portfolio. "
            f"Pre-fund or extend maturities around {peak_year}."
        )
    if stress_breaches > 0:
        recommendations.append(
            "Liquidity stress test flags years whose rollover needs exceed the "
            "stress coverage. Establish a dedicated liquidity buffer."
        )
    if not recommendations:
        recommendations.append("Refinancing profile within safe bounds. Maintain current ladder.")

    return RefinancingRiskAssessment(
        portfolio_id=portfolio.id,
        overall_refinancing_risk=round(risk_score, 1),
        peak_year_maturity=round(peak_amount, 2),
        years_with_excess_refi=len(excess_years),
        stress_breach_count=stress_breaches,
        maturity_distribution={y: round(a, 2) for y, a in distribution.items()},
        recommendations=recommendations,
    )


def diagnose_debt_profile(
    portfolio: Portfolio,
    assumptions: Optional[List[VersionedAssumption]] = None,
    risk_metrics: Optional[Dict[str, float]] = None,
) -> DebtProfileDiagnosis:
    """Diagnose why the debt profile may be worsening.

    Uses the refinancing concentration and optional risk metrics/assumption
    deltas to attribute drivers and project a crisis timeline.
    """
    instrs = [i for i in portfolio.instruments if i.maturity_date is not None]
    key_drivers: List[Dict[str, str]] = []

    if instrs:
        distribution: Dict[int, float] = {}
        for inst in instrs:
            distribution.setdefault(inst.maturity_date.year, 0.0)
            distribution[inst.maturity_date.year] += inst.principal
        total = sum(distribution.values())
        peak_ratio = max(distribution.values()) / total if total else 0.0

        if peak_ratio > 0.30:
            key_drivers.append({
                "driver": "maturity_concentration",
                "impact": f"Peak-year rollover at {peak_ratio:.0%} of debt concentrates refinancing risk.",
            })
        avg_liquidity = float(
            sum(i.liquidity for i in instrs) / len(instrs)
        ) if instrs else 0.0
        if avg_liquidity < 0.4:
            key_drivers.append({
                "driver": "instrument_liquidity",
                "impact": f"Average instrument liquidity {avg_liquidity:.2f} limits refinancing options.",
            })

    contributing = []
    if assumptions:
        for a in assumptions:
            if a.previous_value is not None and a.previous_value != 0:
                delta = (a.value - a.previous_value) / abs(a.previous_value)
                if abs(delta) > 0.02:
                    contributing.append(a.id)
                    key_drivers.append({
                        "driver": a.name,
                        "impact": f"Basis shifted {delta*100:+.1f}% ({a.previous_value} -> {a.value}).",
                    })

    # Use risk metrics if provided to estimate the trajectory
    trajectory: Dict[str, str] = {}
    if risk_metrics:
        for k, v in risk_metrics.items():
            trajectory[k] = "deteriorating" if v > 60 else ("stable" if v > 40 else "improving")

    # Determine overall trend
    deteriorating = any(d["driver"] in ("maturity_concentration",) for d in key_drivers)
    overall_trend = "deteriorating" if deteriorating else ("stable" if not key_drivers else "improving")

    timeline_to_crisis_years: Optional[float] = None
    if peak_ratio and peak_ratio > 0.30:
        timeline_to_crisis_years = round(max(1.0, (0.45 - peak_ratio) * 20 / 0.15), 1)

    return DebtProfileDiagnosis(
        portfolio_id=portfolio.id,
        overall_trend=overall_trend,
        key_drivers=key_drivers,
        contributing_assumptions=contributing,
        risk_indicator_trajectory=trajectory,
        timeline_to_crisis_years=timeline_to_crisis_years,
    )


def identify_dangerous_assumptions(
    entity_id: str,
    assumptions: List[VersionedAssumption],
    risk_scores: Optional[Dict[str, float]] = None,
) -> List[DangerousAssumptions]:
    """Identify the most dangerous assumptions to government finances.

    Scores each assumption by combining the magnitude of its drift from
    baseline with any supplied cross-layer risk score. Assumptions moving in
    an adverse direction with large drift are ranked most dangerous.
    """
    dangerous: List[DangerousAssumptions] = []
    risk_scores = risk_scores or {}

    for a in assumptions:
        baseline = a.previous_value if a.previous_value is not None else a.value
        if baseline == 0:
            continue
        drift = abs(a.value - baseline) / abs(baseline)
        if drift < 0.05:
            continue

        # Directionality heuristic
        if a.category == AssumptionCategory.MACRO and a.value < baseline:
            trend = "deteriorating"
        elif a.category == AssumptionCategory.MACRO:
            trend = "improving"
        else:
            trend = "deteriorating" if a.value < baseline else "improving"

        cross_score = risk_scores.get(a.id, 0.0)
        # Combine drift magnitude (0-60) with cross-layer risk score (0-40)
        risk_score = round(min(100.0, drift * 300.0 + cross_score), 1)

        years_til_trigger: Optional[float] = None
        if drift > 0.5:
            years_til_trigger = round(max(1.0, (1.0 - drift) * 5.0), 1)

        dangerous.append(
            DangerousAssumptions(
                assumption_id=a.id,
                name=a.name,
                category=a.category.value,
                current_value=float(a.value),
                baseline=float(baseline),
                risk_score=risk_score,
                trend=trend,
                associated_risks=[
                    {"id": k, **v} for k, v in (a.associated_risks or {}).items()
                ],
                initiated_by=a.minister_at_change or a.changed_by,
                last_updated=a.updated_at or a.created_at,
                years_til_trigger=years_til_trigger,
            )
        )

    dangerous.sort(key=lambda d: d.risk_score, reverse=True)
    return dangerous


def cross_layer_reasoning(
    portfolio: Portfolio,
    entity_id: str,
    assumptions: Optional[List[VersionedAssumption]] = None,
    risk_scores: Optional[Dict[str, float]] = None,
) -> CrossLayerReasoning:
    """Integrate signals across layers into a coherent government-level view.

    Combines the refinancing assessment (Layer 1/optimization), assumption
    registry (Layer 2), early-warning posture (Layer 5/7), and risk scores
    (Layer 6) into a single systemic assessment with recommendations.
    """
    assumptions = assumptions or []
    risk_scores = risk_scores or {}

    refi = assess_refinancing_risk(portfolio, assumptions)
    dangerous = identify_dangerous_assumptions(entity_id, assumptions, risk_scores)

    layer_assessments: Dict[str, Any] = {
        "refinancing": {
            "score": refi.overall_refinancing_risk,
            "peak_year_maturity": refi.peak_year_maturity,
            "years_with_excess_refi": refi.years_with_excess_refi,
            "recommendations": refi.recommendations,
        },
        "dangerous_assumptions": [
            {"name": d.name, "risk_score": d.risk_score, "trend": d.trend}
            for d in dangerous[:5]
        ],
    }

    systemic_risks: List[Dict[str, str]] = []
    if dangerous:
        worst = dangerous[0]
        systemic_risks.append({
            "risk": f"Assumption '{worst.name}' is deteriorating with a "
                    f"{worst.risk_score:.0f}/100 cross-layer risk score.",
            "severity": "critical" if worst.risk_score >= 70 else "high",
            "source": "assumption_registry",
        })
    if refi.years_with_excess_refi > 0:
        systemic_risks.append({
            "risk": f"Elevated refinancing concentration across "
                    f"{refi.years_with_excess_refi} year(s).",
            "severity": "high" if refi.overall_refinancing_risk >= 60 else "medium",
            "source": "portfolio_ladder",
        })
    high_risk = [k for k, v in risk_scores.items() if v >= 60]
    if high_risk:
        systemic_risks.append({
            "risk": f"{len(high_risk)} risk dimension(s) exceed the 60/100 "
                    f"alert threshold.",
            "severity": "high",
            "source": "risk_os",
        })

    recommendations: List[str] = []
    recommendations.extend(refi.recommendations[:2])
    if dangerous:
        recommendations.append(
            f"Review assumption '{dangerous[0].name}' which carries the highest "
            f"cross-layer risk ({dangerous[0].risk_score:.0f}/100)."
        )
    if not recommendations:
        recommendations.append("No systemic issues detected across layers.")

    # Confidence: more data => higher confidence
    signals = len(refi.maturity_distribution) + len(assumptions) + len(risk_scores)
    confidence = round(min(0.95, 0.35 + signals * 0.03), 2)

    return CrossLayerReasoning(
        portfolio_id=portfolio.id,
        layer_assessments=layer_assessments,
        systemic_risks=systemic_risks,
        recommendations=recommendations,
        confidence=confidence,
    )