"""Infrastructure risk module for the National Risk Operating System."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class AssetCriticality(BaseModel):
    """Criticality assessment for infrastructure asset."""

    id: str = Field(..., description="Unique asset identifier")
    asset_name: str = Field(..., description="Human-readable asset name")
    asset_type: str = Field(
        ...,
        description="Type: grid, water, transport, communications, energy, health",
    )
    criticality_level: str = Field(
        ...,
        description="Level: essential, important, secondary, ancillary",
    )
    dependency_count: int = Field(
        default=0, ge=0, description="Number of downstream systems dependent"
    )
    single_point_of_failure: bool = Field(
        default=False, description="Whether this is a single point of failure"
    )
    redundancy_available: bool = Field(
        default=False, description="Whether redundant paths or assets exist"
    )
    physical_location: str = Field(..., description="Geographic location identifier")
    last_assessed: datetime = Field(default_factory=datetime.utcnow)
    associated_risk_ids: List[str] = Field(
        default_factory=list, description="Related risk assessment IDs"
    )


class FailureMode(BaseModel):
    """A potential failure mode for infrastructure asset."""

    id: str = Field(..., description="Unique failure mode identifier")
    asset_id: str = Field(..., description="Parent asset identifier")
    mode_name: str = Field(..., description="Human-readable failure mode name")
    failure_type: str = Field(
        ...,
        description="Type: structural, operational, environmental, cyber, cascading",
    )
    probability: float = Field(
        ge=0, le=1, description="Probability (0.0 to 1.0)"
    )
    impact_score: float = Field(
        ge=0, le=100, description="Impact score if failure occurs (0-100)"
    )
    trigger_conditions: List[str] = Field(
        default_factory=list, description="Conditions that trigger this failure"
    )
    cascading_effects: List[str] = Field(
        default_factory=list, description="Downstream effects if failure occurs"
    )
    mitigation_actions: List[str] = Field(
        default_factory=list, description="Actions to prevent or reduce impact"
    )
    related_risk_ids: List[str] = Field(
        default_factory=list, description="Related risk assessment IDs"
    )


class InfrastructureRisk(BaseModel):
    """Overall infrastructure risk assessment."""

    id: str = Field(..., description="Unique infrastructure risk assessment identifier")
    entity_id: str = Field(..., description="Government or portfolio identifier")
    entity_type: str = Field(
        default="government",
        description="Entity type: government, portfolio",
    )
    overall_score: float = Field(
        ge=0, le=100, description="Composite infrastructure risk score (0-100)"
    )
    asset_criticality_scores: Dict[str, float] = Field(
        default_factory=dict, description="Criticality scores by asset ID"
    )
    failure_modes: List[FailureMode] = Field(
        default_factory=list
    )
    critical_assets: List[AssetCriticality] = Field(
        default_factory=list
    )
    system_risks: Dict[str, float] = Field(
        default_factory=dict, description="Risk scores by system type"
    )
    last_assessed: datetime = Field(default_factory=datetime.utcnow)
    projection_horizon_years: float = Field(
        default=20.0, ge=0, description="Projection horizon in years"
    )
    resilience_gaps: List[str] = Field(
        default_factory=list, description="Identified resilience gaps"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Infrastructure resilience recommendations"
    )
    related_risk_ids: List[str] = Field(
        default_factory=list, description="Related risk assessment IDs"
    )


class InfrastructureRiskSummary(BaseModel):
    """Summary view for dashboard display."""

    risk_id: str
    overall_score: float
    critical_asset_count: int
    high_risk_assets: int
    last_assessed: datetime
    trending: str