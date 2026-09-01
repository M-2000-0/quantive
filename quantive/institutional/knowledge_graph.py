"""Sovereign Knowledge Graph — Pillar 12, Phase 4.

Maps the relationships between entities (countries, debts, ministries, policies,
risks, decisions) into a persistent, queryable graph. This is strategic
infrastructure competitors cannot easily copy.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Entity:
    entity_id: str
    entity_type: str          # country, debt_issue, ministry, policy, risk, decision, metric
    name: str
    properties: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Edge:
    source: str
    target: str
    relationship: str        # "issues", "approves", "affects", "monitors", "depends_on"
    weight: float = 1.0
    properties: dict = field(default_factory=dict)


class KnowledgeGraph:
    """Persistent sovereign knowledge graph."""

    def __init__(self) -> None:
        self._entities: dict[str, Entity] = {}
        self._edges: list[Edge] = {}
        self._adjacency: dict[str, dict[str, list[str]]] = {}  # entity -> {rel -> [targets]}

    def add_entity(self, entity: Entity) -> None:
        self._entities[entity.entity_id] = entity
        self._adjacency.setdefault(entity.entity_id, {})

    def add_edge(self, source: str, target: str, relationship: str, weight: float = 1.0, properties: dict | None = None) -> None:
        key = f"{source}|{target}|{relationship}"
        self._edges[key] = Edge(source, target, relationship, weight, properties or {})
        self._adjacency.setdefault(source, {}).setdefault(relationship, []).append(target)
        self._adjacency.setdefault(target, {}).setdefault(f"in-{relationship}", []).append(source)

    def entity(self, entity_id: str) -> Entity | None:
        return self._entities.get(entity_id)

    def neighbors(self, entity_id: str, relationship: str | None = None) -> list[str]:
        adj = self._adjacency.get(entity_id, {})
        if relationship:
            return adj.get(relationship, [])
        result = []
        for targets in adj.values():
            result.extend(targets)
        return list(dict.fromkeys(result))  # unique

    def shortest_path(self, start: str, end: str) -> list[str]:
        """BFS shortest path between two entities."""
        if start == end:
            return [start]
        from collections import deque
        visited = {start}
        queue = deque([(start, [start])])
        while queue:
            node, path = queue.popleft()
            for nbr in self.neighbors(node):
                if nbr not in visited:
                    if nbr == end:
                        return path + [nbr]
                    visited.add(nbr)
                    queue.append((nbr, path + [nbr]))
        return []

    def query(self, entity_type: str | None = None, property_key: str | None = None, property_value: Any = None) -> list[Entity]:
        """Filter entities by type and/or property value."""
        result = []
        for e in self._entities.values():
            if entity_type and e.entity_type != entity_type:
                continue
            if property_key is not None:
                if e.properties.get(property_key) != property_value:
                    continue
            result.append(e)
        return result

    def degree(self, entity_id: str) -> int:
        return len(self.neighbors(entity_id))

    def stats(self) -> dict:
        return {
            "entities": len(self._entities),
            "edges": len(self._edges),
            "entity_types": sorted({e.entity_type for e in self._entities.values()}),
            "relationships": sorted({e.relationship for e in self._edges.values()}),
        }

    def seed_canonical(self) -> None:
        """Seed with a minimal sovereign structure for demo/testing."""
        self.add_entity(Entity("gov-1", "government", "Government of X"))
        self.add_entity(Entity("mof-1", "ministry", "Ministry of Finance"))
        self.add_entity(Entity("cb-1", "institution", "Central Bank"))
        self.add_entity(Entity("policy-debt-1", "policy", "Debt Sustainability Policy"))
        self.add_entity(Entity("risk-1", "risk", "Debt Service Risk"))
        self.add_edge("gov-1", "mof-1", "oversees")
        self.add_edge("gov-1", "cb-1", "appoints")
        self.add_edge("mof-1", "policy-debt-1", "administers")
        self.add_edge("policy-debt-1", "risk-1", "mitigates")
        self.add_edge("mof-1", "risk-1", "monitors")
