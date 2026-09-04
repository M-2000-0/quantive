"""API endpoints for Government Knowledge Graph - Layer 4.

Provides searchable graph data structure connecting:
- Policies, Agencies, Projects, Debt issuances, Budgets, Risks, Contractors

Supports Neo4j-ready structure and in-memory graph with search API.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import (
    ContingentLiability,
    DebtInstrument,
    EntityPortfolio,
    FiscalRule,
    GovernmentEntity,
    Portfolio,
    User,
)
from app.models.government import (
    AssumptionCategory,
    CLType,
    EntityType,
    FiscalRuleEvaluation,
    RuleType,
    GovernmentEntity as GovEntity,
    TransferLink,
    VersionedAssumption,
)
from app.security import get_current_user

router = APIRouter(prefix="/api/knowledge-graph", tags=["knowledge-graph"])


# ──────────────────────────────────────────────────────────────────────
# Graph Node/Edge Types for Government Domain
# ──────────────────────────────────────────────────────────────────────


class NodeType(str, enum.Enum):
    POLICY = "policy"
    AGENCY = "agency"
    PROJECT = "project"
    DEBT_ISSUANCE = "debt_issuance"
    BUDGET = "budget"
    RISK = "risk"
    CONTRACTOR = "contractor"


class RelationshipType(str, enum.Enum):
    ISSUED_BY = "issued_by"              # agency issues debt
    FUNDS_PROJECT = "funds_project"        # budget funds project
    PART_OF = "part_of"                    # project contains debt issuance
    SUBJECT_TO = "subject_to"              # risk applies to instrument/policy
    CONTRACTED_BY = "contracted_by"        # contractor works on project
    REGULATES = "regulates"                # policy regulates agency
    SUPPORTS = "supports"                  # budget supports project
    ASSOCIATED_WITH = "associated_with"    # risk associated with entity
    GOVERNS = "governs"                    # agency governs entity
    IMPLEMENTS = "implements"              # policy implemented by agency
    LOCATED_IN = "located_in"              # entity located in agency/jurisdiction
    ISSUED_UNDER = "issued_under"          # debt instrument issued under policy
    FUNDED_BY = "funded_by"                # project funded by budget
    CONTRACTED_FOR = "contracted_for"      # contractor contracted for project
    RELATES_TO = "relates_to"              # general relationship between any nodes


# ──────────────────────────────────────────────────────────────────────
# Graph Data Structures
# ──────────────────────────────────────────────────────────────────────


class KGNode:
    """Graph node representation."""

    def __init__(
        self,
        id: str,
        label: str,
        node_type: NodeType,
        title: str | None = None,
        description: str | None = None,
        data: dict | None = None,
    ):
        self.id = id
        self.label = label or id
        self.type = node_type
        self.title = title or label or ""
        self.description = description
        self.data = data or {}


class KGEdge:
    """Graph edge representation."""

    def __init__(
        self,
        source_id: str,
        target_id: str,
        relationship: RelationshipType,
        label: str | None = None,
        weight: float = 1.0,
        description: str | None = None,
    ):
        self.source_id = source_id
        self.target_id = target_id
        self.relationship = relationship
        self.label = label or relationship.value
        self.weight = weight
        self.description = description


# ──────────────────────────────────────────────────────────────────────
# Neo4j-Ready Model Definitions
# ──────────────────────────────────────────────────────────────────────

# These definitions make the structure Neo4j-compatible using neomodel-style
# patterns. The actual database access uses SQLAlchemy, but the graph model
# is designed to be translatable to Neo4j.

NODE_TYPE_MAP: dict[NodeType, str] = {
    NodeType.POLICY: "Policy",
    NodeType.AGENCY: "Agency",
    NodeType.PROJECT: "Project",
    NodeType.DEBT_ISSUANCE: "DebtIssuance",
    NodeType.BUDGET: "Budget",
    NodeType.RISK: "Risk",
    NodeType.CONTRACTOR: "Contractor",
}

REL_TYPE_MAP: dict[RelationshipType, str] = {
    RelationshipType.ISSUED_BY: "ISSUED_BY",
    RelationshipType.FUNDS_PROJECT: "FUNDS_PROJECT",
    RelationshipType.PART_OF: "PART_OF",
    RelationshipType.SUBJECT_TO: "SUBJECT_TO",
    RelationshipType.CONTRACTED_BY: "CONTRACTED_BY",
    RelationshipType.REGULATES: "REGULATES",
    RelationshipType.SUPPORTS: "SUPPORTS",
    RelationshipType.ASSOCIATED_WITH: "ASSOCIATED_WITH",
}


# ──────────────────────────────────────────────────────────────────────
# Helpers - convert DB models to graph nodes/edges
# ────────────────────────────────────────────────────────────────────


def kg_node_from_government_entity(e: GovEntity) -> KGNode:
    """Convert GovernmentEntity to KGNode."""
    return KGNode(
        id=e.id,
        label=e.name,
        node_type=NodeType.AGENCY,
        title=e.name,
        description=e.description or "",
        data={
            "entity_type": e.entity_type.value if hasattr(e.entity_type, "value") else str(e.entity_type),
            "iso_code": e.iso_code,
            "population": e.population,
            "gdp_local": float(e.gdp_local) if e.gdp_local else None,
            "currency": e.currency,
        },
    )


def kg_node_from_debt_instrument(i: DebtInstrument) -> KGNode:
    """Convert DebtInstrument to KGNode."""
    return KGNode(
        id=i.id,
        label=i.name,
        node_type=NodeType.DEBT_ISSUANCE,
        title=i.name,
        description=i.description or "",
        data={
            "instrument_type": (
                i.instrument_type.value if hasattr(i.instrument_type, "value") else str(i.instrument_type)
            ),
            "currency": i.currency,
            "principal_outstanding": float(i.principal_outstanding) if i.principal_outstanding else 0,
            "coupon_rate": float(i.coupon_rate) if i.coupon_rate else 0,
            "maturity_date": i.maturity_date,
            "issue_date": i.issue_date,
            "spread_bps": float(i.spread_bps or 0),
        },
    )


def kg_node_from_portfolio(p: Portfolio) -> KGNode:
    """Convert Portfolio to KGNode."""
    return KGNode(
        id=p.id,
        label=p.name,
        node_type=NodeType.POLICY,
        title=p.name,
        description=p.description or "",
        data={
            "asset_class": p.asset_class if hasattr(p, "asset_class") else "fixed_income",
            "currency": p.currency,
            "total_value": float(p.total_value) if hasattr(p, "total_value") else None,
        },
    )


def kg_node_from_contingent_liability(cl: ContingentLiability) -> KGNode:
    """Convert ContingentLiability to KGNode."""
    return KGNode(
        id=cl.id,
        label=cl.name,
        node_type=NodeType.RISK,
        title=cl.name,
        description=cl.name or "",
        data={
            "cl_type": cl.cl_type.value if hasattr(cl.cl_type, "value") else str(cl.cl_type),
            "exposure_amount": float(cl.exposure_amount) if cl.exposure_amount else 0,
            "probability_of_call": float(cl.probability_of_call) if cl.probability_of_call else 0,
            "expected_loss": float(cl.expected_loss) if cl.expected_loss else 0,
            "counterparty": cl.counterparty or "",
            "is_national_guarantee": cl.is_national_guarantee,
            "maturity_date": cl.maturity_date,
        },
    )


def kg_node_from_fiscal_rule(rule: FiscalRule) -> KGNode:
    """Convert FiscalRule to KGNode."""
    return KGNode(
        id=rule.id,
        label=rule.name,
        node_type=NodeType.POLICY,
        title=rule.name,
        description=rule.name or "",
        data={
            "rule_type": rule.rule_type.value if hasattr(rule.rule_type, "value") else str(rule.rule_type),
            "threshold_value": float(rule.threshold_value) if rule.threshold_value else 0,
            "threshold_unit": rule.threshold_unit or "",
            "is_hard_limit": rule.is_hard_limit,
            "statute_reference": rule.statute_reference or "",
        },
    )


def kg_edge_from_entity_portfolio(ep: EntityPortfolio) -> KGEdge:
    """Convert EntityPortfolio to KGEdge."""
    return KGEdge(
        source_id=ep.entity_id,
        target_id=ep.portfolio_id,
        relationship=RelationshipType.PART_OF,
        label="part_of",
        weight=1.0,
    )


def kg_edge_issued_by(entity_id: str, agency_id: str) -> KGEdge:
    """Create ISSUED_BY edge."""
    return KGEdge(
        source_id=agency_id,
        target_id=entity_id,
        relationship=RelationshipType.ISSUED_BY,
        label="issues",
        weight=1.0,
    )


def kg_edge_funds_project(budget_id: str, project_id: str) -> KGEdge:
    """Create FUNDS_PROJECT edge."""
    return KGEdge(
        source_id=budget_id,
        target_id=project_id,
        relationship=RelationshipType.FUNDS_PROJECT,
        label="funds",
        weight=1.0,
    )


def kg_edge_part_of(project_id: str, debt_id: str) -> KGEdge:
    """Create PART_OF edge."""
    return KGEdge(
        source_id=project_id,
        target_id=debt_id,
        relationship=RelationshipType.PART_OF,
        label="contains",
        weight=1.0,
    )


def kg_edge_subject_to(risk_id: str, entity_id: str) -> KGEdge:
    """Create SUBJECT_TO edge."""
    return KGEdge(
        source_id=entity_id,
        target_id=risk_id,
        relationship=RelationshipType.SUBJECT_TO,
        label="subject_to",
        weight=1.0,
    )


def kg_edge_contracted_by(project_id: str, contractor_id: str) -> KGEdge:
    """Create CONTRACTED_BY edge."""
    return KGEdge(
        source_id=contractor_id,
        target_id=project_id,
        relationship=RelationshipType.CONTRACTED_BY,
        label="contracts",
        weight=1.0,
    )


def kg_edge_regulates(policy_id: str, agency_id: str) -> KGEdge:
    """Create REGULATES edge."""
    return KGEdge(
        source_id=agency_id,
        target_id=policy_id,
        relationship=RelationshipType.REGULATES,
        label="regulates",
        weight=1.0,
    )


def kg_edge_supports(budget_id: str, project_id: str) -> KGEdge:
    """Create SUPPORTS edge."""
    return KGEdge(
        source_id=budget_id,
        target_id=project_id,
        relationship=RelationshipType.SUPPORTS,
        label="supports",
        weight=1.0,
    )


def kg_edge_associated_with(risk_id: str, entity_id: str) -> KGEdge:
    """Create ASSOCIATED_WITH edge."""
    return KGEdge(
        source_id=entity_id,
        target_id=risk_id,
        relationship=RelationshipType.ASSOCIATED_WITH,
        label="associated_with",
        weight=1.0,
    )


# ──────────────────────────────────────────────────────────────────────
# Search & Traversal Helpers
# ────────────────────────────────────────────────────────────────────


def search_nodes(
    db: Session,
    node_type: NodeType,
    query: str | None = None,
    filters: dict | None = None,
    limit: int = 50,
) -> List[KGNode]:
    """Search nodes by type with optional text query and filters."""

    from app.models import DebtInstrument, Portfolio
    from app.models.government import ContingentLiability, FiscalRule, GovernmentEntity

    nodes: List[KGNode] = []

    if node_type == NodeType.AGENCY:
        query_stmt = select(GovernmentEntity).where(
            GovernmentEntity.entity_type == EntityType.NATIONAL
        )
        if query:
            query_stmt = query_stmt.where(
                GovernmentEntity.name.ilike(f"%{query}%")
            )
        entities = db.execute(query_stmt).scalars().limit(limit).all()
        nodes = [kg_node_from_government_entity(e) for e in entities]

    elif node_type == NodeType.DEBT_ISSUANCE:
        query_stmt = select(DebtInstrument).options(
            joinedload(DebtInstrument.portfolio)
        )
        if query:
            query_stmt = query_stmt.where(
                DebtInstrument.name.ilike(f"%{query}%")
            )
        instruments = db.execute(query_stmt).scalars().limit(limit).all()
        nodes = [kg_node_from_debt_instrument(i) for i in instruments]

    elif node_type == NodeType.POLICY:
        query_stmt = select(FiscalRule)
        if query:
            query_stmt = query_stmt.where(
                FiscalRule.name.ilike(f"%{query}%")
            )
        rules = db.execute(query_stmt).scalars().limit(limit).all()
        nodes = [kg_node_from_fiscal_rule(r) for r in rules]

    elif node_type == NodeType.RISK:
        query_stmt = select(ContingentLiability)
        if query:
            query_stmt = query_stmt.where(
                ContingentLiability.name.ilike(f"%{query}%")
            )
        cls = db.execute(query_stmt).scalars().limit(limit).all()
        nodes = [kg_node_from_contingent_liability(c) for c in cls]

    elif node_type == NodeType.PROJECT:
        query_stmt = select(Portfolio)
        if query:
            query_stmt = query_stmt.where(
                Portfolio.name.ilike(f"%{query}%")
            )
        portfolios = db.execute(query_stmt).scalars().limit(limit).all()
        nodes = [kg_node_from_portfolio(p) for p in portfolios]

    elif node_type == NodeType.BUDGET:
        # Budget data comes from fiscal rules and entity portfolios
        query_stmt = select(FiscalRule).distinct()
        if query:
            query_stmt = query_stmt.where(
                FiscalRule.name.ilike(f"%{query}%")
            )
        rules = db.execute(query_stmt).scalars().limit(limit).all()
        nodes = [kg_node_from_fiscal_rule(r) for r in rules]

    elif node_type == NodeType.CONTRACTOR:
        # Contractor data - query from contingent liabilities or extend as needed
        query_stmt = select(ContingentLiability).distinct()
        if query:
            query_stmt = query_stmt.where(
                ContingentLiability.counterparty.ilike(f"%{query}%")
                | ContingentLiability.name.ilike(f"%{query}%")
            )
        cls = db.execute(query_stmt).scalars().limit(limit).all()
        nodes = [kg_node_from_contingent_liability(c) for c in cls]

    if filters:
        nodes = [n for n in nodes if _node_matches_filters(n, filters)]

    return nodes


def _node_matches_filters(node: KGNode, filters: dict) -> bool:
    """Check if node matches filter criteria."""
    for key, value in filters.items():
        if key in node.data:
            node_value = str(node.data[key])
            if isinstance(value, str):
                if value.lower() not in node_value.lower():
                    return False
            else:
                if node.data[key] != value:
                    return False
    return True


def traverse_graph(
    db: Session,
    start_node_id: str,
    relationship_types: list[RelationshipType] | None = None,
    max_depth: int = 2,
    node_types: list[NodeType] | None = None,
) -> dict:
    """Traverse graph from a starting node up to max_depth levels."""

    from app.models import DebtInstrument
    from app.models.government import ContingentLiability, FiscalRule, GovernmentEntity

    result: dict = {
        "start_id": start_node_id,
        "nodes": [],
        "edges": [],
        "path": [],
    }

    if relationship_types is None:
        relationship_types = list(RelationshipType)

    visited: set = set()
    current_frontier: list[tuple[str, int]] = [(start_node_id, 0)]  # (node_id, depth)

    while current_frontier:
        node_id, depth = current_frontier.pop(0)
        if node_id in visited or depth > max_depth:
            continue

        visited.add(node_id)
        result["nodes"].append(node_id)

        # Query node type and find connections based on relationship types
        node_label: str | None = None
        node_type_result: str | None = None

        # Try to identify the node and its connections
        # Agencies
        try:
            agency = db.query(GovernmentEntity).filter(GovernmentEntity.id == node_id).first()
            if agency:
                # Find connected nodes based on relationship types
                for rel_type in relationship_types:
                    if rel_type == RelationshipType.ISSUED_BY:
                        # Find debt instruments issued by this agency
                        edges = (
                            db.query(DebtInstrument)
                            .join(EntityPortfolio, EntityPortfolio.portfolio_id == DebtInstrument.portfolio_id)
                            .filter(EntityPortfolio.entity_id == node_id)
                            .all()
                        )
                        for edge in edges:
                            if edge.id not in visited:
                                result["edges"].append(
                                    {
                                        "source": node_id,
                                        "target": edge.id,
                                        "relationship": rel_type.value,
                                        "label": "issues",
                                        "weight": 1.0,
                                    }
                                )
                                if edge.id not in [n[0] for n in current_frontier]:
                                    current_frontier.append((edge.id, depth + 1))
                    elif rel_type == RelationshipType.FUNDS_PROJECT:
                        # This would connect budgets to projects - extend as needed
                        pass
                    elif rel_type == RelationshipType.PART_OF:
                        # Projects or debt instruments that are part of something
                        pass
                    elif rel_type == RelationshipType.SUBJECT_TO:
                        # Risks subject to this node
                        cl = db.query(ContingentLiability).filter(
                            ContingentLiability.instrument_ref_id == node_id
                        ).all()
                        for c in cl:
                            if c.id not in visited:
                                result["edges"].append(
                                    {
                                        "source": c.id,
                                        "target": node_id,
                                        "relationship": rel_type.value,
                                        "label": "subject_to",
                                        "weight": 1.0,
                                    }
                                )
                                if c.id not in [n[0] for n in current_frontier]:
                                    current_frontier.append((c.id, depth + 1))
                    elif rel_type == RelationshipType.CONTRACTED_BY:
                        # Contractors contracted for projects linked to this node
                        pass
                    elif rel_type == RelationshipType.REGULATES:
                        # Policies regulated by this agency
                        rules = db.query(FiscalRule).filter(FiscalRule.entity_id == node_id).all()
                        for r in rules:
                            if r.id not in visited:
                                result["edges"].append(
                                    {
                                        "source": node_id,
                                        "target": r.id,
                                        "relationship": rel_type.value,
                                        "label": "regulates",
                                        "weight": 1.0,
                                    }
                                )
                                if r.id not in [n[0] for n in current_frontier]:
                                    current_frontier.append((r.id, depth + 1))
                    elif rel_type == RelationshipType.SUPPORTS:
                        # Budgets supporting projects - extend as needed
                        pass
                    elif rel_type == RelationshipType.ASSOCIATED_WITH:
                        # Risks associated with this entity
                        cl = db.query(ContingentLiability).filter(
                            ContingentLiability.entity_id == node_id
                        ).all()
                        for c in cl:
                            if c.id not in visited:
                                result["edges"].append(
                                    {
                                        "source": node_id,
                                        "target": c.id,
                                        "relationship": rel_type.value,
                                        "label": "associated_with",
                                        "weight": 1.0,
                                    }
                                )
                                if c.id not in [n[0] for n in current_frontier]:
                                    current_frontier.append((c.id, depth + 1))
        except Exception:
            pass

        # Add next frontier nodes based on depth
        if depth < max_depth:
            current_frontier.extend(
                (neighbor_id, depth + 1)
                for neighbor_id, _ in current_frontier
                if neighbor_id not in visited
            )

    return result


# ──────────────────────────────────────────────────────────────────────
# API Endpoints
# ──────────────────────────────────────────────────────────────────────


@router.get("/")
def list_graph_overview(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get overview of the knowledge graph with entity counts and structure."""

    from app.models import DebtInstrument
    from app.models.government import ContingentLiability, FiscalRule, GovernmentEntity

    # Count entities by type
    entity_counts: dict[str, int] = {
        "agencies": db.query(GovernmentEntity).filter(
            GovernmentEntity.entity_type == EntityType.NATIONAL
        ).count(),
        "debt_instruments": db.query(DebtInstrument).count(),
        "portfolios": db.query(Portfolio).count(),
        "fiscal_rules": db.query(FiscalRule).count(),
        "contingent_liabilities": db.query(ContingentLiability).count(),
        "budgets": db.query(FiscalRule).count(),  # fiscal rules serve as budget markers
        "contractors": db.query(ContingentLiability).count(),  # contractor data via CL
    }

    # Get sample nodes for each type
    sample_nodes: dict[str, list[dict]] = {}
    for node_type in NodeType:
        try:
            nodes = search_nodes(db, node_type, limit=3)
            sample_nodes[node_type.value] = [
                {
                    "id": n.id,
                    "label": n.label,
                    "type": n.type.value,
                    "title": n.title,
                }
                for n in nodes
            ]
        except Exception:
            sample_nodes[node_type.value] = []

    # Get recent edges (sample traversals)
    recent_edges: list[dict] = []

    return {
        "entity_counts": entity_counts,
        "sample_nodes": sample_nodes,
        "recent_edges": recent_edges,
        "node_types": [nt.value for nt in NodeType],
        "relationship_types": [rt.value for rt in RelationshipType],
        "status": "active",
    }


@router.get("/search")
def search_knowledge_graph(
    query: str,
    node_types: Optional[list[str]] = None,
    filters: Optional[dict] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search the knowledge graph by text query across node types."""

    if not query or not query.strip():
        raise HTTPException(400, "Query parameter is required")

    if node_types is None:
        node_types = [nt.value for nt in NodeType]

    results: dict[str, list[dict]] = {nt: [] for nt in node_types}

    # Normalize node types
    valid_types = [NodeType(nt) for nt in node_types if nt in [nt.value for nt in NodeType]]

    for node_type in valid_types:
        nodes = search_nodes(db, node_type, query=query.strip(), filters=filters, limit=20)
        results[node_type.value] = [
            {
                "id": n.id,
                "label": n.label,
                "type": n.type.value,
                "title": n.title,
                "description": n.description,
                "data": n.data,
            }
            for n in nodes
        ]

    return {
        "query": query,
        "total_results": sum(len(v) for v in results.values()),
        "results": results,
        "facets": {
            "node_types": {nt.value: len(v) for nt, v in results.items()},
        },
    }


@router.get("/traverse/{start_node_id}")
def traverse_from_node(
    start_node_id: str,
    relationship_types: Optional[list[str]] = None,
    max_depth: int = 2,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Traverse graph from a starting node."""

    if relationship_types:
        rel_types = [RelationshipType(rt) for rt in relationship_types if rt in [rt.value for rt in RelationshipType]]
    else:
        rel_types = None

    result = traverse_graph(db, start_node_id, relationship_types=rel_types, max_depth=max_depth)

    # Enhance with node labels
    from app.models import DebtInstrument
    from app.models.government import ContingentLiability, FiscalRule, GovernmentEntity

    node_labels: dict[str, dict] = {}
    for node_id in result["nodes"]:
        # Try to identify node type and get label
        node_labels[node_id] = {"id": node_id, "label": node_id, "type": "unknown"}

    # Add some known node types
    entities = db.query(GovernmentEntity).filter(GovernmentEntity.id.in_(result["nodes"])).all()
    for e in entities:
        node_labels[e.id] = {
            "id": e.id,
            "label": e.name,
            "type": "agency",
        }

    instruments = db.query(DebtInstrument).filter(DebtInstrument.id.in_(result["nodes"])).all()
    for i in instruments:
        node_labels[i.id] = {
            "id": i.id,
            "label": i.name,
            "type": "debt_issuance",
        }

    result["node_labels"] = node_labels

    return {
        "start_node_id": start_node_id,
        "nodes_visited": len(result["nodes"]),
        "edges_traversed": len(result["edges"]),
        "path": result["nodes"],
        "node_labels": node_labels,
    }


@router.get("/structure")
def get_graph_structure(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the full graph structure with nodes and edges."""

    from app.models import DebtInstrument
    from app.models.government import ContingentLiability, FiscalRule, GovernmentEntity

    # Get all agencies
    agencies = db.query(GovernmentEntity).filter(
        GovernmentEntity.entity_type == EntityType.NATIONAL
    ).all()

    # Get all debt instruments
    instruments = db.query(DebtInstrument).options(
        joinedload(DebtInstrument.portfolio)
    ).all()

    # Get fiscal rules
    rules = db.query(FiscalRule).all()

    # Get contingent liabilities
    cls = db.query(ContingentLiability).all()

    nodes: list[dict] = []
    edges: list[dict] = []

    # Add agency nodes
    for a in agencies:
        nodes.append(
            {
                "id": a.id,
                "label": a.name,
                "type": "agency",
                "title": a.name,
                "description": a.description or "",
                "data": {
                    "entity_type": a.entity_type.value
                    if hasattr(a.entity_type, "value")
                    else str(a.entity_type),
                    "iso_code": a.iso_code,
                    "population": a.population,
                    "gdp_local": float(a.gdp_local) if a.gdp_local else None,
                    "currency": a.currency,
                },
            }
        )

    # Add debt instrument nodes
    for i in instruments:
        nodes.append(
            {
                "id": i.id,
                "label": i.name,
                "type": "debt_issuance",
                "title": i.name,
                "description": i.description or "",
                "data": {
                    "instrument_type": (
                        i.instrument_type.value
                        if hasattr(i.instrument_type, "value")
                        else str(i.instrument_type)
                    ),
                    "currency": i.currency,
                    "principal_outstanding": float(i.principal_outstanding)
                    if i.principal_outstanding
                    else 0,
                    "coupon_rate": float(i.coupon_rate) if i.coupon_rate else 0,
                    "maturity_date": i.maturity_date,
                    "issue_date": i.issue_date,
                    "spread_bps": float(i.spread_bps or 0),
                },
            }
        )

    # Add fiscal rule nodes
    for r in rules:
        nodes.append(
            {
                "id": r.id,
                "label": r.name,
                "type": "policy",
                "title": r.name,
                "description": r.name or "",
                "data": {
                    "rule_type": r.rule_type.value
                    if hasattr(r.rule_type, "value")
                    else str(r.rule_type),
                    "threshold_value": float(r.threshold_value) if r.threshold_value else 0,
                    "threshold_unit": r.threshold_unit or "",
                    "is_hard_limit": r.is_hard_limit,
                    "statute_reference": r.statute_reference or "",
                },
            }
        )

    # Add contingent liability nodes
    for c in cls:
        nodes.append(
            {
                "id": c.id,
                "label": c.name,
                "type": "risk",
                "title": c.name,
                "description": c.name or "",
                "data": {
                    "cl_type": c.cl_type.value if hasattr(c.cl_type, "value") else str(c.cl_type),
                    "exposure_amount": float(c.exposure_amount) if c.exposure_amount else 0,
                    "probability_of_call": float(c.probability_of_call) if c.probability_of_call else 0,
                    "expected_loss": float(c.expected_loss) if c.expected_loss else 0,
                    "counterparty": c.counterparty or "",
                    "is_national_guarantee": c.is_national_guarantee,
                    "maturity_date": c.maturity_date,
                },
            }
        )

    # Add edges based on EntityPortfolio relationships
    from app.models.government import EntityPortfolio

    ep_edges = db.query(EntityPortfolio).all()
    for ep in ep_edges:
        edges.append(
            {
                "source": ep.entity_id,
                "target": ep.portfolio_id,
                "relationship": "part_of",
                "label": "part_of",
                "weight": 1.0,
            }
        )

    # Add ISSUED_BY edges: agency → debt instrument (via portfolio)
    for i in instruments:
        if i.portfolio:
            # Find the entity linked to this portfolio
            ep = (
                db.query(EntityPortfolio)
                .filter(EntityPortfolio.portfolio_id == i.portfolio_id)
                .first()
            )
            if ep and ep.entity_id:
                edges.append(
                    {
                        "source": ep.entity_id,
                        "target": i.id,
                        "relationship": "issued_by",
                        "label": "issues",
                        "weight": 1.0,
                    }
                )

    # Add SUBJECT_TO edges: instruments → risks (contingent liabilities)
    for c in cls:
        if c.instrument_ref_id:
            edges.append(
                {
                    "source": c.instrument_ref_id,
                    "target": c.id,
                    "relationship": "subject_to",
                    "label": "subject_to",
                    "weight": 1.0,
                }
            )

    return {
        "nodes": nodes,
        "edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "node_types": [nt.value for nt in NodeType],
        "relationship_types": [rt.value for rt in RelationshipType],
    }


@router.get("/metrics")
def graph_metrics(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get graph metrics and statistics."""

    from app.models import DebtInstrument
    from app.models.government import ContingentLiability, FiscalRule, GovernmentEntity

    node_counts: dict[str, int] = {
        "agencies": db.query(GovernmentEntity).filter(
            GovernmentEntity.entity_type == EntityType.NATIONAL
        ).count(),
        "debt_instruments": db.query(DebtInstrument).count(),
        "policies": db.query(FiscalRule).count(),
        "risks": db.query(ContingentLiability).count(),
    }

    edge_counts: dict[str, int] = {
        "entity_portfolio_rels": db.query(EntityPortfolio).count(),
    }

    # Calculate connectivity metrics
    total_nodes = sum(node_counts.values())
    total_edges = sum(edge_counts.values())

    # Average degree
    avg_degree = (2 * total_edges) / total_nodes if total_nodes > 0 else 0

    # Component analysis (simplified)
    connected_components = max(1, total_nodes - total_edges)  # simplified

    return {
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "node_counts": node_counts,
        "edge_counts": edge_counts,
        "average_degree": round(avg_degree, 2),
        "connected_components": connected_components,
        "density": round(total_edges / (total_nodes * (total_nodes - 1)) if total_nodes > 1 else 0, 4),
    }