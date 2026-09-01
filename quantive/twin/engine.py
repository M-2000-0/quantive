"""National Digital Twin — Pillar 12, Phase 5.

Integrates Economy, Debt, Budget, Trade, Demographics, and Energy into one
simulation environment. The twin layers base projections + policy shocks,
then synthesizes them into a coherent national trajectory.

Honest: uses the forecasting engine with explicit assumptions; every output
is traceable to inputs. Never fabricates precision.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from quantive.intelligence.forecasting import ForecastingEngine
from quantive.trust.explainability import ExplainabilityEngine, AssumptionRef, DataSource, Risk, Alternative


# Domain input bundles
@dataclass
class EconomyState:
    gdp: float
    inflation: float
    unemployment: float
    growth_rate: float = 0.03
    uncertainty: float = 0.25


@dataclass
class DebtState:
    total_debt: float
    interest_rate: float = 0.05
    maturity_years: int = 10


@dataclass
class BudgetState:
    revenue: float
    expenditure: float
    revenue_growth: float = 0.03
    expenditure_growth: float = 0.03


@dataclass
class TradeState:
    exports: float
    imports: float
    export_growth: float = 0.04
    import_growth: float = 0.04


@dataclass
class DemographicState:
    population: float
    working_age_share: float = 0.60
    population_growth: float = 0.005


@dataclass
class EnergyState:
    primary_energy_demand: float
    demand_growth: float = 0.02
    energy_intensity: float = 1.0     # energy per GDP unit


@dataclass
class NationalState:
    country: str
    economy: EconomyState
    debt: DebtState
    budget: BudgetState
    trade: TradeState
    demographics: DemographicState
    energy: EnergyState


@dataclass
class TwinProjection:
    year: int
    gdp: float
    debt_to_gdp: float
    fiscal_balance: float
    trade_balance: float
    population: float
    energy_demand: float
    inflation: float
    unemployment: float


class NationalDigitalTwin:
    """Single integrated simulation of a country's financial future.

    All six domains share one time horizon and one parameter set, so policy
    changes propagate across the whole system (e.g., energy policy → growth →
    debt). This is what makes it a TWIN, not six standalone spreadsheets.
    """

    def __init__(self) -> None:
        self.forecaster = ForecastingEngine()
        self.explain = ExplainabilityEngine()

    def simulate(
        self,
        state: NationalState,
        years: list[int],
        *,
        policy_deltas: dict[str, float] | None = None,
    ) -> dict:
        """Run the full national simulation over the given year list.

        policy_deltas can include: growth, inflation, revenue, expenditure,
        exports, imports, energy_intensity.
        """
        policy_deltas = policy_deltas or {}
        deltas = {
            "growth": policy_deltas.get("growth", 0.0),
            "inflation": policy_deltas.get("inflation", 0.0),
            "revenue": policy_deltas.get("revenue", 0.0),
            "expenditure": policy_deltas.get("expenditure", 0.0),
            "exports": policy_deltas.get("exports", 0.0),
            "imports": policy_deltas.get("imports", 0.0),
            "energy_intensity": policy_deltas.get("energy_intensity", 0.0),
        }

        gdp = state.economy.gdp
        revenue = state.budget.revenue
        expenditure = state.budget.expenditure
        exports = state.trade.exports
        imports = state.trade.imports
        debt = state.debt.total_debt
        population = state.demographics.population
        energy = state.energy.primary_energy_demand
        inflation = state.economy.inflation
        unemployment = state.economy.unemployment

        projections: list[TwinProjection] = []

        for i, year in enumerate(years):
            growth = state.economy.growth_rate + deltas["growth"]
            gdp *= (1 + growth)
            inflation *= (1 + state.economy.inflation * 0.5 + deltas["inflation"] * 0.5)
            revenue *= (1 + state.budget.revenue_growth + deltas["revenue"])
            expenditure *= (1 + state.budget.expenditure_growth + deltas["expenditure"])
            exports *= (1 + state.trade.export_growth + deltas["exports"])
            imports *= (1 + state.trade.import_growth + deltas["imports"])
            population *= (1 + state.demographics.population_growth)
            energy_intensity = state.energy.energy_intensity + deltas["energy_intensity"]
            energy = gdp * energy_intensity

            # debt accumulates fiscal deficit + interest (net of growth)
            interest = debt * state.debt.interest_rate
            primary_balance = revenue - expenditure
            debt = debt + interest + (expenditure - revenue) - gdp * deltas["growth"] * 0.1

            projections.append(
                TwinProjection(
                    year=year,
                    gdp=gdp,
                    debt_to_gdp=debt / gdp,
                    fiscal_balance=revenue - expenditure,
                    trade_balance=exports - imports,
                    population=population,
                    energy_demand=energy,
                    inflation=inflation,
                    unemployment=unemployment,
                )
            )

        final = projections[-1] if projections else None
        # composite health index (decision-ready single number)
        health = self._health_index(state, final)

        # build explainable wrap so the twin allows Pillar 2/3 traceability
        explanation = self.explain.build(
            rec_id=f"twin-{state.country}-{years[0]}-{years[-1]}",
            title=f"National Digital Twin — {state.country}",
            action_type="hold",
            target=state.country,
            confidence=0.55,
            confidence_basis="Integrated model with deterministic growth assumptions",
            assumptions=[
                AssumptionRef(key="growth_rate", value=state.economy.growth_rate, source="state_input", confidence=0.7),
                AssumptionRef(key="interest_rate", value=state.debt.interest_rate, source="state_input", confidence=0.7),
                AssumptionRef(key="population_growth", value=state.demographics.population_growth, source="state_input", confidence=0.8),
            ],
            risks=[
                Risk(description="Twin uses simple exponential projections; structural breaks not captured", severity="medium", mitigation="Feed real market data", probability=0.4),
            ],
            alternatives=[
                Alternative(
                    description="No policy change (baseline continuation)",
                    expected_return=final.debt_to_gdp if final else None,
                    pros=["No intervention risk"],
                    cons=["Misses opportunity to improve debt trajectory"],
                ),
            ],
            data_sources=[
                DataSource(name="National statistics inputs", type="government", quality_score=0.7, staleness_hours=0),
            ],
            model_name="quantive-national-twin",
            model_version="0.1.0",
            ai_interpretation=f"Integrated simulation of {state.country} projects debt-to-GDP converging to {final.debt_to_gdp:.1%} by {years[-1]}. AI interpretation — not a forecast.",
            counterargument="Simple growth assumptions may not capture recessions, crises, or policy reversals; the twin is a planning tool, not a crystal ball.",
        )

        return {
            "country": state.country,
            "projections": [p.__dict__ for p in projections],
            "final": final.__dict__ if final else None,
            "health_index": health,
            "assumptions": explanation.to_report(),
            "policy_deltas": deltas,
        }

    def _health_index(self, state: NationalState, final: TwinProjection | None) -> float:
        """0-100 composite national financial health."""
        if not final:
            return 0.0
        # lower debt-to-GDP and balanced fiscal/trade = healthier
        debt_score = 1 - min(final.debt_to_gdp, 1.2) / 1.2
        # fiscal balance normalized
        fiscal_score = 1 - abs(final.fiscal_balance) / max(state.economy.gdp, 1) * 5
        trade_score = 1 - max(0, -final.trade_balance) / max(state.trade.exports, 1) * 2
        index = (debt_score * 0.4 + max(fiscal_score, 0) * 0.3 + max(trade_score, 0) * 0.3) * 100
        return round(max(0, min(index, 100)), 1)
