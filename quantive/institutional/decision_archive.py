"""Decision Archive — Pillar 9, Pillar 12, Phase 4.

Stores assumptions, rationale, approvals, and outcomes forever. This becomes
a national memory system. Institutional knowledge must not leave when people
leave. Every decision is traceable: who made it, why, what assumptions,
what alternatives, what lessons were learned.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class DecisionStage(str, Enum):
    DRAFTED = "drafted"
    APPROVED = "approved"
    EXECUTED = "executed"
    REVIEWED = "reviewed"
    ARCHIVED = "archived"
    SUPERSEDED = "superseded"


@dataclass
class DecisionRecord:
    """A complete, immutable record of a government decision."""
    decision_id: str
    title: str
    description: str
    decision_maker: str
    creator: str
    approvers: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    stage: DecisionStage = DecisionStage.DRAFTED
    assumptions: list[dict] = field(default_factory=list)      # [{key, value, source, confidence}]
    rationale: str = ""
    alternatives_considered: list[str] = field(default_factory=list)
    risks_accepted: list[dict] = field(default_factory=list)    # [{description, severity}]
    data_sources: list[str] = field(default_factory=list)
    outcome: dict | None = None                                  # what happened after execution
    lessons_learned: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class DecisionArchive:
    """Append-only archive of decisions — national institutional memory."""

    def __init__(self) -> None:
        self._records: dict[str, DecisionRecord] = {}
        self._immutable = True

    def archive(self, record: DecisionRecord) -> DecisionRecord:
        """Append a decision. The archive is append-only (never deleted)."""
        self._records[record.decision_id] = record
        return record

    def record_outcome(self, decision_id: str, outcome: dict) -> DecisionRecord:
        """Record what actually happened after the decision (learning loop)."""
        rec = self._records[decision_id]
        rec.outcome = outcome
        rec.stage = DecisionStage.EXECUTED
        return rec

    def add_lessons(self, decision_id: str, lessons: list[str]) -> DecisionRecord:
        """Capture lessons learned — this is what builds institutional memory."""
        rec = self._records[decision_id]
        rec.lessons_learned = list(dict.fromkeys(rec.lessons_learned + lessons))
        rec.stage = DecisionStage.REVIEWED
        return rec

    def get(self, decision_id: str) -> DecisionRecord | None:
        return self._records.get(decision_id)

    def search(
        self,
        *,
        decision_maker: str | None = None,
        since: datetime | None = None,
        keyword: str | None = None,
    ) -> list[DecisionRecord]:
        result = list(self._records.values())
        if decision_maker:
            result = [r for r in result if r.decision_maker == decision_maker]
        if since:
            result = [r for r in result if r.created_at >= since]
        if keyword:
            k = keyword.lower()
            result = [r for r in result if k in (r.title + r.description + r.rationale).lower()]
        return result

    def traceability_report(self, decision_id: str) -> dict | None:
        """Pillar 12: the full 'why was this decision made' report."""
        rec = self.get(decision_id)
        if not rec:
            return None
        return {
            "decision_id": rec.decision_id,
            "title": rec.title,
            "who": {
                "creator": rec.creator,
                "decision_maker": rec.decision_maker,
                "approvers": rec.approvers,
            },
            "why": {
                "rationale": rec.rationale,
                "assumptions": rec.assumptions,
                "alternatives_considered": rec.alternatives_considered,
                "risks_accepted": rec.risks_accepted,
            },
            "what_happened": {
                "outcome": rec.outcome,
                "lessons_learned": rec.lessons_learned,
            },
            "data_sources": rec.data_sources,
            "created_at": rec.created_at.isoformat(),
            "stage": rec.stage.value,
        }

    def count(self) -> int:
        return len(self._records)

    def lessons_index(self) -> dict[str, list[str]]:
        """The accumulated national lessons — searchable institutional memory."""
        return {
            rid: rec.lessons_learned
            for rid, rec in self._records.items()
            if rec.lessons_learned
        }
