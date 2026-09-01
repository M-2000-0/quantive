"""Policy impact simulator — Phase 3 Decision Intelligence.

Models the fiscal/macro impact of candidate policy choices before implementation.
Answers: "what government decision becomes better because this exists?"
Honest: shocks + base rates, never fabricated precision.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from quantive.intelligence.forecasting import ForecastingEngine, Forecast


@dataclass
class PolicyOption:
    policy_id: str
    name: str
    description: str
    revenue_impact_annual: float = 0.0      # + = more revenue ($)
    expenditure_impact_annual: float = 0.0  # + = more spending ($)
    growth_impact_annual: float = 0.0       # + = higher GDP growth (percentage points)
    debt_sensitivity: float = 0.0           # impact on debt trajectory
    risk_level: Literal["low", "medium", "high"] = "medium"
    stakeholder_notes: str = ""


@dataclass
class PolicySimulationResult:
    policy: PolicyOption
    target: dict                          # {metric: {years, central, optimistic, pessimistic}}
    fiscal_balance_after: float
    debt_to_gdp_after: float
    years: list[int]
    assumptions: list[str]
    recommendation_key: str = ""          # e.g. "proceed", "proceed_with_conditions", "reconsider"


class PolicySimulator:
    """Compares policy options against a baseline over a horizon."""

    def __init__(self, forecaster: ForecastingEngine | None = None) -> None:
        self.forecaster = forecaster or ForecastingEngine()

    def simulate(
        self,
        policy: PolicyOption,
        *,
        baseline_gdp: float,
        baseline_revenue: float,
        baseline_expenditure: float,
        baseline_debt: float,
        years: list[int],
        baseline_growth_rate: float = 0.03,
    ) -> PolicySimulationResult:
        """Project fiscal outcomes with the policy's impacts layered in."""
        t_horizon = len(years)

        # GDP grows with baseline + policy growth impact
        gdp_cf = baseline_gdp
        revenue_cf = baseline_revenue
        expend_cf = baseline_expenditure
        debt_cf = baseline_debt

        gdp_traj: list[float] = []
        rev_traj: list[float] = []
        exp_traj: list[float] = []
        deficit_traj: list[float] = []
        debt_ratio_traj: list[float] = []

        for i in range(t_horizon):
            growth = baseline_growth_rate + policy.growth_impact_annual
            gdp_cf *= (1 + growth)
            revenue_cf *= (1 + baseline_growth_rate) + policy.revenue_impact_annual
            expend_cf *= (1 + baseline_growth_rate) + policy.expenditure_impact_annual
            # deficit = spending - revenue
            deficit = expend_cf - revenue_cf
            debt_cf = debt_cf * (1 - policy.debt_sensitivity) + deficit

            gdp_traj.append(gdp_cf)
            rev_traj.append(revenue_cf)
            exp_traj.append(expend_cf)
            deficit_traj.append(deficit)
            debt_ratio_traj.append(debt_cf / gdp_cf)

        # build forecast-style bands for key outputs
        debt_ratio_central = debt_ratio_traj
        return PolicySimulationResult(
            policy=policy,
            target={
                "gdp_growth": {
                    "years": years,
                    "central": [policy.growth_impact_annual + baseline_growth_rate] * t_horizon,
                },
                "debt_to_gdp": {
                    "years": years,
                    "central": debt_ratio_central,
                },
                "fiscal_deficit": {
                    "years": years,
                    "central": deficit_traj,
                },
                "revenue": {"years": years, "central": rev_traj},
                "expenditure": {"years": years, "central": exp_traj},
            },
            fiscal_balance_after=deficit_traj[-1] if deficit_traj else 0,
            debt_to_gdp_after=debt_ratio_traj[-1] if debt_ratio_traj else 0,
            years=years,
            assumptions=[
                f"baseline_gdp={baseline_gdp}",
                f"baseline_growth={baseline_growth_rate:.2%}",
                f"policy_growth_impact={policy.growth_impact_annual:.2%}",
                f"policy_revenue_impact={policy.revenue_impact_annual}",
                f"policy_expenditure_impact={policy.expenditure_impact_annual}",
            ],
        )

    def recommend(self, results: list[PolicySimulationResult]) -> str:
        """Simple decision support: which policy minimizes debt-to-GDP?"""
        best = min(results, key=lambda r: r.debt_to_gdp_after)
        return best.policy.policy_id
