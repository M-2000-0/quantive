"""Scenario decision wrapper — Phase 3 Decision Intelligence.

Runs the core scenario engine through the trust layer so every scenario
carries assumptions, risks, and data sources (Pillar 2/3).
"""
from __future__ import annotations

from dataclasses import dataclass

from quantive.scenarios.engine import ScenarioEngine
from quantive.trust.explainability import ExplainableRecommendation, AssumptionRef, DataSource, Risk, Alternative
from quantive.trust.explainability import ExplainabilityEngine


@dataclass
class ScenarioDecision:
    scenario_id: str
    name: str
    summary: dict
    explanation: ExplainableRecommendation
    recommendation_key: str


class ScenarioDecisionEngine:
    """Adds Pillar 2/3 explainability to scenario runs for decision-makers."""

    def __init__(self, scenario_engine: ScenarioEngine | None = None) -> None:
        self._engine = scenario_engine or ScenarioEngine()
        self._explain = ExplainabilityEngine()

    def assess(
        self,
        scenario_ids: list[str] | None = None,
        *,
        decision_title: str,
        target: str,
    ) -> list[ScenarioDecision]:
        scenarios = self._engine.named(scenario_ids) if scenario_ids else self._engine.monte_carlo(1)
        decisions: list[ScenarioDecision] = []
        for sc in scenarios:
            # build an explainable wrapper using scenario outputs
            rec = self._build_explanation(sc, decision_title, target)
            rec_id = f"scenario-{sc.id}"
            decisions.append(
                ScenarioDecision(
                    scenario_id=str(getattr(sc, "id", rec_id)),
                    name=getattr(sc, "description", decision_title),
                    summary={"shocks_present": True, "severity": self._severity(sc)},
                    explanation=rec,
                    recommendation_key=self._severity(sc),
                )
            )
        return decisions

    def _severity(self, sc) -> str:
        # map a scenario to a stress classification based on available fields
        for attr in ("severity", "stress_level", "label", "scenario_type"):
            v = getattr(sc, attr, None)
            if v is not None:
                return str(v)
        return "moderate"

    def _build_explanation(self, sc, title: str, target: str) -> ExplainableRecommendation:
        # Represent each scenario as an explainable, traceable decision document
        description = getattr(sc, "description", title)
        return self._explain.build(
            rec_id=f"sc-{getattr(sc, 'id', 'x')}",
            title=f"{title}: {description}",
            action_type="rebalance",
            target=target,
            confidence=0.6,
            confidence_basis="Scenario model with deterministic seed; confidence reflects model structural uncertainty",
            confidence_limitations=[
                "Scenario parameters are stress assumptions, not forecasts",
                "Second-order effects are approximations",
            ],
            assumptions=[
                AssumptionRef(key="seed", value=getattr(sc, "seed", "42"), source="scenario_engine", confidence=0.9),
            ],
            risks=[
                Risk(
                    description=f"Scenario '{description}' may not capture tail risk",
                    severity="medium",
                    mitigation="Run Monte-Carlo ensemble across seeds",
                    probability=0.3,
                ),
            ],
            alternatives=[
                Alternative(
                    description="Run with baseline (no stress) assumptions",
                    pros=["Lower alarm", "Stable view"],
                    cons=["Misses tail risk", "Not decision-safe"],
                ),
            ],
            data_sources=[
                DataSource(name="Scenario configuration", type="model_output", quality_score=0.7, staleness_hours=0),
            ],
            model_name="quantive-scenario-engine",
            model_version="0.1.0",
            ai_interpretation=(
                f"Scenario '{description}' models a {self._severity(sc)} stress condition. "
                f"This is an AI interpretation of the scenario model — not a forecast."
            ),
            counterargument="Scenario stress levels are model choices, not certainties; different assumptions give different pictures.",
        )
