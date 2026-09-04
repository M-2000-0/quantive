"""Climate risk module for the National Risk Operating System."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ClimateImpact(BaseModel):
    """A quantified climate impact event or projection."""

    id: str = Field(..., description="Unique climate impact identifier")
    event_name: str = Field(..., description="Name of the climate event")
    event_type: str = Field(
        ...,
        description="Type: flood, drought, heatwave, hurricane, wildfire, sea_level_rise",
    )
    severity: str = Field(
        ..., description="Severity: low, medium, high, severe",
    )
    geographic_scope: List[str] = Field(
        default_factory=list, description="Affected regions or country codes"
    )
    probability: float = Field(
        ge=0, le=1, description="Probability (0.0 to 1.0)"
    )
    time_horizon_years: float = Field(
        ..., ge=0, description="Years from present until event"
    )
    economic_impact_usd: Optional[float] = Field(
        None, ge=0, description="Estimated economic impact in USD"
    )
    fiscal_impact_usd: Optional[float] = Field(
        None, ge=0, description="Estimated fiscal impact in USD"
    )
    affected_assets: List[str] = Field(
        default_factory=list, description="Asset identifiers at risk"
    )
    confidence: float = Field(
        ge=0, le=1, description="Scientific confidence (0.0 to 1.0)"
    )
    description: str = Field(..., description="Detailed impact description")
    related_risk_ids: List[str] = Field(
        default_factory=list, description="Related risk assessment IDs"
    )


class ClimateScenario(BaseModel):
    """A climate scenario for risk modeling and stress testing."""

    id: str = Field(..., description="Unique scenario identifier")
    scenario_name: str = Field(..., description="Name of the climate scenario")
    scenario_type: str = Field(
        ...,
        description="Type: baseline, moderate, severe, extreme",
    )
    warming_level: float = Field(
        ..., ge=0, description="Global warming level in °C above pre-industrial"
    )
    time_horizon_years: float = Field(
        ..., ge=0, description="Projection horizon in years"
    )
    climate_impacts: List[ClimateImpact] = Field(
        default_factory=list
    )
    economic_multiplier: float = Field(
        default=1.0, ge=0, description="GDP multiplier under this scenario"
    )
    fiscal_multiplier: float = Field(
        default=1.0, ge=0, description="Fiscal impact multiplier"
    )
    probability_weight: float = Field(
        default=1.0, ge=0, le=1, description="Probability weight for weighting"
    )
    related_risk_ids: List[str] = Field(
        default_factory=list, description="Related risk assessment IDs"
    )


class ClimateRisk(BaseModel):
    """Overall climate risk assessment for a government or portfolio."""

    id: str = Field(..., description="Unique climate risk assessment identifier")
    entity_id: str = Field(..., description="Government or portfolio identifier")
    entity_type: str = Field(
        default="government",
        description="Entity type: government, portfolio",
    )
    overall_score: float = Field(
        ge=0, le=100, description="Composite climate risk score (0-100)"
    )
    physical_risk_score: float = Field(
        ge=0, le=100, description="Physical climate risk sub-score (0-100)"
    )
    transition_risk_score: float = Field(
        ge=0, le=100, description="Transition/ policy risk sub-score (0-100)"
    )
    climate_scenarios: List[ClimateScenario] = Field(
        default_factory=list
    )
    high_impact_events: List[ClimateImpact] = Field(
        default_factory=list, description="Events with high economic impact"
    )
    last_assessed: datetime = Field(default_factory=datetime.utcnow)
    projection_horizon_years: float = Field(
        default=30.0, ge=0, description="Long-term projection horizon in years"
    )
    risk_factors: Dict[str, float] = Field(
        default_factory=dict, description="Component scores by factor"
    )
    adaptation_measures: List[str] = Field(
        default_factory=list, description="Active adaptation measures"
    )
    mitigation_priorities: List[str] = Field(
        default_factory=list, description="Prioritized mitigation actions"
    )
    related_risk_ids: List[str] = Field(
        default_factory=list, description="Related risk assessment IDs"
    )


class ClimateRiskSummary(BaseModel):
    """Summary view for dashboard display."""

    risk_id: str
    overall_score: float
    physical_risk_score: float
    transition_risk_score: float
    high_impact_count: int
    scenario_count: int
    last_assessed: datetime
    trending: str