"""Geopolitical risk module for the National Risk Operating System."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from quantive.risk.enums import ConflictType


class AllianceStatus(str, Enum):
    """Status of international alliances and partnerships."""

    NATO = "NATO"
    EUROPEAN_UNION = "eu"
    COMMONWEALTH = "commonwealth"
    BILATERAL_TREATY = "bilateral_treaty"
    NON_ALIGNED = "non_aligned"
    RISKING_SANCTIONS = "risking_sanctions"


class GeopoliticalEvent(BaseModel):
    """A geopolitical event or development affecting risk."""

    id: str = Field(..., description="Unique geopolitical event identifier")
    event_name: str = Field(..., description="Name of the geopolitical event")
    event_type: ConflictType = Field(..., description="Type of event")
    primary_actors: List[str] = Field(
        default_factory=list, description="Primary actor identifiers"
    )
    secondary_actors: List[str] = Field(
        default_factory=list, description="Secondary actor identifiers"
    )
    affected_regions: List[str] = Field(
        default_factory=list, description="Affected geographic regions"
    )
    severity: str = Field(
        ..., description="Severity: low, medium, high, critical"
    )
    likelihood: float = Field(
        ge=0, le=1, description="Likelihood (0.0 to 1.0)"
    )
    time_horizon_years: float = Field(
        ..., ge=0, description="Years from present until significant effect"
    )
    description: str = Field(..., description="Detailed event description")
    implications_fiscal: str = Field(
        default="", description="Fiscal policy implications"
    )
    implications_debt: str = Field(
        default="", description="Public debt implications"
    )
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    related_risk_ids: List[str] = Field(
        default_factory=list, description="Related risk assessment IDs"
    )


class AllianceRelationship(BaseModel):
    """A bilateral or multilateral alliance relationship."""

    id: str = Field(..., description="Unique relationship identifier")
    actor_1: str = Field(..., description="First actor (country code)")
    actor_2: str = Field(..., description="Second actor (country code)")
    relationship_type: str = Field(
        ...,
        description="Type: alliance, partnership, treaty, non-aggression",
    )
    status: AllianceStatus = Field(..., description="Current relationship status")
    strength_score: float = Field(
        ge=0, le=100, description="Relationship strength (0-100)"
    )
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    treaty_obligations: List[str] = Field(
        default_factory=list, description="Key treaty or commitment identifiers"
    )
    related_risk_ids: List[str] = Field(
        default_factory=list, description="Related risk assessment IDs"
    )


class GeopoliticalRisk(BaseModel):
    """Overall geopolitical risk assessment."""

    id: str = Field(..., description="Unique geopolitical risk assessment identifier")
    entity_id: str = Field(..., description="Government or portfolio identifier")
    entity_type: str = Field(
        default="government",
        description="Entity type: government, portfolio",
    )
    overall_score: float = Field(
        ge=0, le=100, description="Composite geopolitical risk score (0-100)"
    )
    conflict_risk_score: float = Field(
        ge=0, le=100, description="Active conflict/sub-war risk sub-score (0-100)"
    )
    alliance_stability_score: float = Field(
        ge=0, le=100, description="Alliance and partnership stability sub-score (0-100)"
    )
    sanction_risk_score: float = Field(
        ge=0, le=100, description="Sanctions exposure sub-score (0-100)"
    )
    geopolitical_events: List[GeopoliticalEvent] = Field(
        default_factory=list
    )
    alliance_relationships: List[AllianceRelationship] = Field(
        default_factory=list
    )
    last_assessed: datetime = Field(default_factory=datetime.utcnow)
    projection_horizon_years: float = Field(
        default=15.0, ge=0, description="Projection horizon in years"
    )
    risk_factors: Dict[str, float] = Field(
        default_factory=dict, description="Component scores by factor"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Geopolitical risk mitigation recommendations"
    )
    related_risk_ids: List[str] = Field(
        default_factory=list, description="Related risk assessment IDs"
    )


class GeopoliticalRiskSummary(BaseModel):
    """Summary view for dashboard display."""

    risk_id: str
    overall_score: float
    conflict_risk_score: float
    alliance_stability_score: float
    active_events: int
    last_assessed: datetime
    trending: str