"""Government model (in-memory) for the quantive engine.

Lightweight, dependency-free version of the government entity/assumption
model used by the institutional memory engine (Layer 2) and the reasoning
engine (Layer 10). Mirrors the API of the SQLAlchemy-backed
``backend/app/models/government.py`` but stores state in memory so the
pure-python ``quantive`` package can run without a database connection.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def gen_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AssumptionCategory(str, enum.Enum):
    MACRO = "macro"
    MARKET = "market"
    POLICY = "policy"
    DEMOGRAPHIC = "demographic"
    CUSTOM = "custom"


class _Column:
    """Descriptor exposing a model attribute as a class-level comparator."""

    def __init__(self, name: str) -> None:
        self.name = name

    def __get__(self, obj: Any, objtype: Any = None) -> Any:
        if obj is None:
            return _Comparison(None, self.name)
        return getattr(obj, self.name)


class _VersionedAssumptionMeta(type):
    """Metaclass injecting class-level column comparators for filtering."""

    _COLUMN_NAMES = (
        "id", "entity_id", "name", "category", "value", "unit", "source",
        "version", "is_current", "changed_by", "change_reason",
        "previous_value", "administration_label", "minister_at_change",
        "transition_trigger", "associated_risks", "active_initiatives",
        "unresolved_issues", "upcoming_deadlines", "audit_hash",
        "knowledge_base_id", "persistence_status", "migration_timestamp",
        "created_at", "updated_at",
    )

    def __new__(mcs, name: str, bases: tuple, namespace: dict) -> type:
        cls = super().__new__(mcs, name, bases, namespace)
        for col in mcs._COLUMN_NAMES:
            setattr(cls, col, _Column(col))
        return cls


class VersionedAssumption(metaclass=_VersionedAssumptionMeta):
    """A single versioned, auditable assumption (in-memory)."""

    def __init__(
        self,
        id: Optional[str] = None,
        entity_id: str = "",
        name: str = "",
        category: AssumptionCategory = AssumptionCategory.CUSTOM,
        value: float = 0.0,
        unit: str = "",
        source: Optional[str] = None,
        version: int = 1,
        is_current: bool = True,
        changed_by: Optional[str] = None,
        change_reason: Optional[str] = None,
        previous_value: Optional[float] = None,
        administration_label: Optional[str] = None,
        minister_at_change: Optional[str] = None,
        transition_trigger: Optional[str] = None,
        associated_risks: Optional[dict] = None,
        active_initiatives: Optional[dict] = None,
        unresolved_issues: Optional[dict] = None,
        upcoming_deadlines: Optional[dict] = None,
        audit_hash: Optional[str] = None,
        knowledge_base_id: Optional[str] = None,
        persistence_status: str = "active",
        migration_timestamp: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        **kwargs: Any,
    ) -> None:
        self.id = id or gen_uuid()
        self.entity_id = entity_id
        self.name = name
        self.category = category
        self.value = value
        self.unit = unit
        self.source = source
        self.version = version
        self.is_current = is_current
        self.changed_by = changed_by
        self.change_reason = change_reason
        self.previous_value = previous_value
        self.administration_label = administration_label
        self.minister_at_change = minister_at_change
        self.transition_trigger = transition_trigger
        self.associated_risks = associated_risks or {}
        self.active_initiatives = active_initiatives or {}
        self.unresolved_issues = unresolved_issues or {}
        self.upcoming_deadlines = upcoming_deadlines or {}
        self.audit_hash = audit_hash
        self.knowledge_base_id = knowledge_base_id
        self.persistence_status = persistence_status
        self.migration_timestamp = migration_timestamp
        self.created_at = created_at or utcnow()
        self.updated_at = updated_at or self.created_at


# ── In-memory query model (SQLAlchemy-like façade) ─────────────────────────

class _Comparison:
    """Proxy for comparing a model attribute against a value."""

    def __init__(self, obj: Any, attr: str) -> None:
        self._obj = obj
        self._attr = attr

    def __eq__(self, other: Any) -> "_Predicate":
        return _Predicate(
            lambda row: getattr(row, self._attr) == other
        )

    def in_(self, values: List[Any]) -> "_Predicate":
        return _Predicate(
            lambda row: getattr(row, self._attr) in values
        )

    def desc(self) -> "_Desc":
        return _Desc(self._attr)


class _Desc:
    def __init__(self, attr: str) -> None:
        self.attr = attr


class _Predicate:
    def __init__(self, fn: Any) -> None:
        self.fn = fn


class _Count:
    def __init__(self, rows: List[Any]) -> None:
        self.rows = rows

    def __len__(self) -> int:
        return len(self.rows)

    def get(self, key: str, default: Any = None) -> Any:
        return self.rows[key] if key in self.rows else default


class _Query:
    """Chainable in-memory query mirroring SQLAlchemy's Query object."""

    def __init__(self, model: Any, rows: List[Any]) -> None:
        self._model = model
        self._rows = rows

    def filter(self, *predicates: Any) -> "_Query":
        rows = self._rows
        for p in predicates:
            fn = p.fn if isinstance(p, _Predicate) else p
            rows = [r for r in rows if fn(r)]
        return _Query(self._model, rows)

    def order_by(self, *criteria: Any) -> "_Query":
        asc_keys: List[str] = []
        desc_keys: List[str] = []
        for c in criteria:
            if isinstance(c, _Desc):
                desc_keys.append(c.attr)
            else:
                asc_keys.append(c)
        rows = self._rows
        for key in reversed(desc_keys):
            rows = sorted(rows, key=lambda r, k=key: getattr(r, k), reverse=True)
        for key in reversed(asc_keys):
            rows = sorted(rows, key=lambda r, k=key: getattr(r, k))
        return _Query(self._model, rows)

    def all(self) -> List[Any]:
        return list(self._rows)

    def first(self) -> Optional[Any]:
        return self._rows[0] if self._rows else None


class _InMemoryDB:
    """A minimal in-memory object store with a SQLAlchemy-like session API."""

    def __init__(self) -> None:
        self._store: Dict[type, List[Any]] = {}

    def query(self, model: Any) -> _Query:
        rows = self._store.setdefault(model, [])
        return _Query(model, list(rows))

    def add(self, obj: Any) -> None:
        self._store.setdefault(type(obj), []).append(obj)

    def commit(self) -> None:
        pass

    def refresh(self, obj: Any) -> None:
        for row in self._store.get(type(obj), []):
            if getattr(row, "id", None) == getattr(obj, "id", None):
                for attribute in ["id", "entity_id", "name", "value", "version"]:
                    setattr(obj, attribute, getattr(row, attribute))
                break


# Shared in-memory database instance used across the engine
db = _InMemoryDB()
