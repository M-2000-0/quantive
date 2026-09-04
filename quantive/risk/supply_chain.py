"""Supply chain risk module for the National Risk Operating System."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class DisruptionType(str, Enum):
    """Types of supply chain disruptions."""

    PORT_CONGESTION = "port_congestion"
    TRANSPORT_DISABLED = "transport_disabled"
    RAW_MATERIAL_SHORTAGE = "raw_material_shortage"
    MANUFACTURING_OUTAGE = "manufacturing_outage"
    LOGISTICS_ROUTE_BLOCKED = "logistics_route_blocked"
    SINGLE_SUPPLIER_FAILURE = "single_supplier_failure"
    GEOPOLITICAL_INTERDICTION = "geopolitical_interdiction"
    CYBER_SUPPLY_CHAIN = "cyber_supply_chain"
    NATURAL_DISASTER = "natural_disaster"
    DEMAND_SPIKE = "demand_spike"


class TierLevel(str, Enum):
    """Tier level of supply chain dependency."""

    TIER_1 = "tier_1"
    TIER_2 = "tier_2"
    TIER_3 = "tier_3"
    TIER_4_PLUS = "tier_4+"


class SupplyChainDisruption(BaseModel):
    """A supply chain disruption event."""

    id: str = Field(..., description="Unique disruption identifier")
    disruption_type: DisruptionType = Field(..., description="Type of disruption")
    severity: str = Field(
        ..., description="Severity: low, medium, high, critical"
    )
    affected_segments: List[str] = Field(
        default_factory=list, description="Supply chain segments affected"
    )
    impacted_countries: List[str] = Field(
        default_factory=list, description="Countries impacted"
    )
    affected_assets: List[str] = Field(
        default_factory=list, description="Asset identifiers affected"
    )
    probability: float = Field(
        ge=0, le=1, description="Probability (0.0 to 1.0)"
    )
    estimated_duration_days: float = Field(
        ge=0, description="Estimated disruption duration in days"
    )
    economic_impact_usd: Optional[float] = Field(
        None, ge=0, description="Estimated economic impact in USD"
    )
    fiscal_impact_usd: Optional[float] = Field(
        None, ge=0, description="Estimated fiscal impact in USD"
    )
    trigger_conditions: List[str] = Field(
        default_factory=list, description="Conditions that triggered the disruption"
    )
    mitigation_status: str = Field(
        default="pending",
        description="Status: pending, mitigated, in_progress, resolved",
    )
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    related_risk_ids: List[str] = Field(
        default_factory=list, description="Related risk assessment IDs"
    )


class SupplyChainRisk(BaseModel):
    """Overall supply chain risk assessment."""

    id: str = Field(..., description="Unique supply chain risk assessment identifier")
    entity_id: str = Field(..., description="Government or portfolio identifier")
    entity_type: str = Field(
        default="government",
        description="Entity type: government, portfolio",
    )
    overall_score: float = Field(
        ge=0, le=100, description="Composite supply chain risk score (0-100)"
    )
    disruption_risk_score: float = Field(
        ge=0, le=100, description="Active disruption risk sub-score (0-100)"
    )
    dependency_score: float = Field(
        ge=0, le=100, description="Supplier/concentration dependency sub-score (0-100)"
    )
    single_point_failure_score: float = Field(
        ge=0, le=100, description="Single point of failure sub-score (0-100)"
    )
    disruptions: List[SupplyChainDisruption] = Field(
        default_factory=list
    )
    critical_dependencies: List[str] = Field(
        default_factory=list, description="Critical asset or supplier identifiers"
    )
    tier_dependence: Dict[TierLevel, float] = Field(
        default_factory=dict, description="Dependency proportion by tier level"
    )
    last_assessed: datetime = Field(default_factory=datetime.utcnow)
    projection_horizon_years: float = Field(
        default=10.0, ge=0, description="Projection horizon in years"
    )
    resilience_measures: List[str] = Field(
        default_factory=list, description="Active resilience building measures"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Supply chain risk mitigation recommendations"
    )
    related_risk_ids: List[str] = Field(
        default_factory=list, description="Related risk assessment IDs"
    )


class SupplyChainRiskSummary(BaseModel):
    """Summary view for dashboard display."""

    risk_id: str
    overall_score: float
    disruption_risk_score: float
    dependency_score: float
    critical_dependencies_count: int
    last_assessed: datetime
    trending: str