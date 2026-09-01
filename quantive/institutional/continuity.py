"""Government continuity engine — Pillar 12, Pillar 11, Phase 4.

Ensures government operations continue across transitions, personnel changes,
and crises. Stores critical knowledge so it survives when people leave.
Also models institutional readiness for scale (100 countries / decades).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ContinuityRisk(str, Enum):
    PEOPLE_DEPENDENCE = "key_person_dependence"
    PROCESS_GAP = "process_gap"
    DOCUMENTATION_LOSS = "documentation_loss"
    TRANSITION = "transition"
    SYSTEM_DEPENDENCE = "system_dependence"


@dataclass
class CriticalKnowledge:
    knowledge_id: str
    domain: str
    title: str
    content: str
    owner: str
    criticality: float = 1.0        # 0-1
    documented: bool = True
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DepartmentStatus:
    department: str
    key_person_dependence: float = 0.0   # 0-1
    documentation_coverage: float = 1.0  # 0-1
    process_maturity: float = 1.0        # 0-1
    transition_ready: float = 1.0        # 0-1


class ContinuityEngine:
    """Assesses and strengthens government operational continuity."""

    def __init__(self) -> None:
        self._knowledge: dict[str, CriticalKnowledge] = {}
        self._departments: dict[str, DepartmentStatus] = {}
        self._transition_plans: dict[str, str] = {}

    def add_knowledge(self, k: CriticalKnowledge) -> None:
        self._knowledge[k.knowledge_id] = k

    def add_department(self, d: DepartmentStatus) -> None:
        self._departments[d.department] = d

    @staticmethod
    def _dept_score(d: DepartmentStatus) -> float:
        """Continuity score per department (0-1), clamped.

        Key-person dependence is heavily weighted because it's the dominant
        continuity risk: if one person leaving can break a function, that's a
        continuity failure regardless of documentation alone.
        """
        raw = (
            1.0
            - d.key_person_dependence * 0.6          # dominant risk factor
            + d.documentation_coverage * 0.15
            + d.process_maturity * 0.15
            + d.transition_ready * 0.10
        )
        return max(0.0, min(raw, 1.0))

    def continuity_index(self) -> float:
        """0-1 overall continuity readiness (clamped)."""
        if not self._departments:
            return 0.0
        scores = [self._dept_score(d) for d in self._departments.values()]
        return round(sum(scores) / len(scores), 3)

    def at_risk_departments(self, threshold: float = 0.6) -> list[str]:
        """Departments most at risk of continuity failure."""
        return [
            name for name, d in self._departments.items() if self._dept_score(d) < threshold
        ]

    def knowledge_gaps(self) -> list[str]:
        """Domains with critical undocumented knowledge (bus factor)."""
        gaps = []
        for k in self._knowledge.values():
            if not k.documented and k.criticality > 0.7:
                gaps.append(k.title)
        return gaps

    def register_transition_plan(self, domain: str, plan: str) -> None:
        self._transition_plans[domain] = plan

    def transition_readiness(self) -> dict:
        """Pillar 10: making exit/transition easier increases trust."""
        return {
            domain: bool(plan) for domain, plan in self._transition_plans.items()
        }

    def summary(self) -> dict:
        return {
            "continuity_index": self.continuity_index(),
            "at_risk_departments": self.at_risk_departments(),
            "knowledge_gaps": self.knowledge_gaps(),
            "knowledge_records": len(self._knowledge),
            "departments_monitored": len(self._departments),
            "transition_plans": self.transition_readiness(),
        }
