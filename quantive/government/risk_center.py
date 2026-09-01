"""Government risk center — Pillar 4, Phase 2.

Central sovereign risk aggregation for government decision-makers.
Maps external risks to our internal sovereign-debt simulation outputs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal


@dataclass
class SovereignRisk:
    risk_id: str
    category: Literal["fiscal", "debt", "macro", "political", "external", "operational", "climate"]
    title: str
    description: str
    likelihood: Literal["rare", "unlikely", "possible", "likely", "almost_certain"]
    impact: Literal["negligible", "minor", "moderate", "major", "catastrophic"]
    score: float = 0.0          # 0-1 composite (likelihood × impact)
    trend: Literal["improving", "stable", "worsening"] = "stable"
    mitigation: str = ""
    owner: str = ""
    last_assessed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# likelihood/impact → numeric
_LIK = {"rare": 0.1, "unlikely": 0.3, "possible": 0.5, "likely": 0.7, "almost_certain": 0.9}
_IMP = {"negligible": 0.1, "minor": 0.3, "moderate": 0.5, "major": 0.7, "catastrophic": 0.9}


class RiskCenter:
    """Aggregates sovereign risks into a decision-ready risk register."""

    def __init__(self) -> None:
        self._risks: dict[str, SovereignRisk] = {}

    def register(self, risk: SovereignRisk) -> SovereignRisk:
        risk.score = round(_LIK[risk.likelihood] * _IMP[risk.impact], 3)
        self._risks[risk.risk_id] = risk
        return risk

    def register_many(self, risks: list[SovereignRisk]) -> None:
        for r in risks:
            self.register(r)

    def overall_exposure(self) -> float:
        """Weighted average composite risk (0-1)."""
        if not self._risks:
            return 0.0
        return round(sum(r.score for r in self._risks.values()) / len(self._risks), 3)

    def top_risks(self, n: int = 5) -> list[SovereignRisk]:
        return sorted(self._risks.values(), key=lambda r: r.score, reverse=True)[:n]

    def risks_by_category(self) -> dict[str, list[SovereignRisk]]:
        from collections import defaultdict
        result = defaultdict(list)
        for r in self._risks.values():
            result[r.category].append(r)
        return dict(result)

    def risk_heatmap(self) -> dict:
        """Decision-ready view: risk → (likelihood, impact, score, trend)."""
        return {
            r.risk_id: {
                "category": r.category,
                "title": r.title,
                "likelihood": r.likelihood,
                "impact": r.impact,
                "score": r.score,
                "trend": r.trend,
                "owner": r.owner,
                "mitigation": r.mitigation,
            }
            for r in self._risks.values()
        }

    def register_core_sovereign_risks(self) -> None:
        """Seed with the canonical sovereign risk set."""
        core = [
            SovereignRisk("r-debt-1", "debt", "Debt service burden spikes", "Rising rates raise refinancing costs", "possible", "major", mitigation="Duration management, liability operations", owner="Debt Office"),
            SovereignRisk("r-fiscal-1", "fiscal", "Fiscal deficit exceeds target", "Spending outpaces revenue", "likely", "moderate", mitigation="Expenditure rules, revenue measures", owner="MOF"),
            SovereignRisk("r-macro-1", "macro", "Growth shock", "External demand collapse", "possible", "major", mitigation="Countercyclical policy, buffers", owner="Central Bank"),
            SovereignRisk("r-external-1", "external", "FX reserve drawdown", "External stress", "unlikely", "major", mitigation="Reserve buffers, swap lines", owner="Central Bank"),
            SovereignRisk("r-political-1", "political", "Policy reversal", "Election/cabinet change", "possible", "moderate", mitigation="Independent fiscal council, legislation", owner="MOF"),
        ]
        self.register_many(core)
