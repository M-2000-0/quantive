"""Assumption tracking — Pillar 9, Pillar 12, Pillar 2.

Every model run, optimization, and recommendation must record its assumptions.
Assumptions are versioned, auditable, and linked to their source.
When an assumption changes, the system knows what downstream decisions are affected.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from quantive.trust.audit import AuditTrail, ActionType


@dataclass
class Assumption:
    """A single assumption with full provenance."""
    id: str
    category: Literal["data", "model", "policy", "market", "regulatory", "custom"]
    key: str                     # e.g. "risk_free_rate", "gdp_growth_forecast"
    value: Any
    unit: str = ""               # e.g. "percent", "USD", "ratio"
    source: str = ""             # e.g. "IMF WEO April 2024", "user_input"
    confidence: float = 1.0      # 0-1, how confident are we in this assumption
    rationale: str = ""          # why this value was chosen
    alternatives: list[dict] = field(default_factory=list)  # [{"value": x, "reason": "..."}]
    created_by: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1
    superseded_by: str | None = None  # id of newer version
    tags: list[str] = field(default_factory=list)


@dataclass
class AssumptionSet:
    """A collection of assumptions for a specific model run or decision."""
    id: str
    name: str
    description: str = ""
    assumptions: list[Assumption] = field(default_factory=list)
    created_by: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1
    parent_set_id: str | None = None  # if derived from another set


class AssumptionRegistry:
    """Central registry for all assumptions in Quantive.

    Features:
    - Versioning: old assumptions are superseded, not deleted
    - Provenance: every assumption knows its source and rationale
    - Lineage: track which decisions were made under which assumptions
    - Conflict detection: flag contradictory assumptions
    """

    def __init__(self, audit: AuditTrail | None = None) -> None:
        self.audit = audit or AuditTrail()
        self._assumptions: dict[str, Assumption] = {}
        self._sets: dict[str, AssumptionSet] = {}
        self._lineage: dict[str, list[str]] = {}  # assumption_id → [decision_ids that used it]

    def register(
        self,
        *,
        assumption_id: str,
        category: Literal["data", "model", "policy", "market", "regulatory", "custom"],
        key: str,
        value: Any,
        unit: str = "",
        source: str = "",
        confidence: float = 1.0,
        rationale: str = "",
        alternatives: list[dict] | None = None,
        created_by: str = "",
        tags: list[str] | None = None,
    ) -> Assumption:
        """Register a new assumption."""
        assumption = Assumption(
            id=assumption_id,
            category=category,
            key=key,
            value=value,
            unit=unit,
            source=source,
            confidence=confidence,
            rationale=rationale,
            alternatives=alternatives or [],
            created_by=created_by,
            tags=tags or [],
        )

        self._assumptions[assumption_id] = assumption

        self.audit.record(
            actor=created_by or "system",
            action=ActionType.CREATE,
            target_type="assumption",
            target_id=assumption_id,
            details={"category": category, "key": key, "value": value, "source": source},
            data_sources=[source] if source else [],
        )

        return assumption

    def update(
        self,
        assumption_id: str,
        *,
        new_value: Any,
        updated_by: str,
        rationale: str = "",
        source: str = "",
        confidence: float | None = None,
    ) -> Assumption:
        """Update an assumption → creates new version, supersedes old."""
        old = self._assumptions[assumption_id]
        old.superseded_by = f"{assumption_id}-v{old.version + 1}"

        new_id = f"{assumption_id}-v{old.version + 1}"
        new = Assumption(
            id=new_id,
            category=old.category,
            key=old.key,
            value=new_value,
            unit=old.unit,
            source=source or old.source,
            confidence=confidence if confidence is not None else old.confidence,
            rationale=rationale,
            alternatives=old.alternatives.copy(),
            created_by=updated_by,
            version=old.version + 1,
            tags=old.tags.copy(),
        )

        self._assumptions[new_id] = new

        self.audit.record(
            actor=updated_by,
            action=ActionType.MODIFY,
            target_type="assumption",
            target_id=new_id,
            details={
                "old_value": old.value,
                "new_value": new_value,
                "previous_version": old.id,
                "rationale": rationale,
            },
            data_sources=[source] if source else [],
        )

        return new

    def create_set(
        self,
        *,
        set_id: str,
        name: str,
        description: str = "",
        assumption_ids: list[str],
        created_by: str = "",
    ) -> AssumptionSet:
        """Bundle assumptions into a named set for a model run or decision."""
        assumptions = [self._assumptions[aid] for aid in assumption_ids if aid in self._assumptions]
        assumption_set = AssumptionSet(
            id=set_id,
            name=name,
            description=description,
            assumptions=assumptions,
            created_by=created_by,
        )
        self._sets[set_id] = assumption_set

        self.audit.record(
            actor=created_by or "system",
            action=ActionType.CREATE,
            target_type="assumption_set",
            target_id=set_id,
            details={"name": name, "assumption_count": len(assumptions)},
        )

        return assumption_set

    def link_to_decision(self, assumption_id: str, decision_id: str) -> None:
        """Record that a decision was made using this assumption."""
        self._lineage.setdefault(assumption_id, []).append(decision_id)

    def get_affected_decisions(self, assumption_id: str) -> list[str]:
        """What decisions are affected if this assumption changes?"""
        return self._lineage.get(assumption_id, [])

    def detect_conflicts(self, assumption_ids: list[str]) -> list[str]:
        """Detect contradictory assumptions in a set."""
        conflicts: list[str] = []
        assumptions = [self._assumptions[aid] for aid in assumption_ids if aid in self._assumptions]

        # group by key
        by_key: dict[str, list[Assumption]] = {}
        for a in assumptions:
            by_key.setdefault(a.key, []).append(a)

        for key, group in by_key.items():
            if len(group) > 1:
                values = [a.value for a in group]
                # conflict if same key has different values
                if len(set(str(v) for v in values)) > 1:
                    conflicts.append(
                        f"Conflict on '{key}': {[f'{a.id}={a.value}' for a in group]}"
                    )

            # low confidence warnings
            for a in group:
                if a.confidence < 0.3:
                    conflicts.append(
                        f"Low confidence ({a.confidence:.0%}) on '{key}' from {a.source or 'unknown source'}"
                    )

        return conflicts

    def get(self, assumption_id: str) -> Assumption | None:
        return self._assumptions.get(assumption_id)

    def get_set(self, set_id: str) -> AssumptionSet | None:
        return self._sets.get(set_id)

    def list_by_category(self, category: str) -> list[Assumption]:
        return [a for a in self._assumptions.values() if a.category == category and a.superseded_by is None]

    def list_active(self) -> list[Assumption]:
        """All assumptions that haven't been superseded."""
        return [a for a in self._assumptions.values() if a.superseded_by is None]

    def export_set(self, set_id: str) -> dict:
        """Export an assumption set as a plain dict (for reports, audit, API)."""
        s = self._sets.get(set_id)
        if not s:
            return {}
        return {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "version": s.version,
            "created_by": s.created_by,
            "created_at": s.created_at.isoformat(),
            "assumptions": [
                {
                    "id": a.id,
                    "category": a.category,
                    "key": a.key,
                    "value": a.value,
                    "unit": a.unit,
                    "source": a.source,
                    "confidence": a.confidence,
                    "rationale": a.rationale,
                    "alternatives": a.alternatives,
                }
                for a in s.assumptions
            ],
        }
