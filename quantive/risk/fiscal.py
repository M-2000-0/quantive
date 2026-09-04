"""Fiscal risk module — extends existing risk tracking."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class FiscalPressure(BaseModel):
    """A fiscal pressure point affecting sovereign debt sustainability."""

    id: str = Field(..., description="Unique fiscal pressure identifier")
    name: str = Field(..., description="Human-readable pressure name")
    pressure_type: str = Field(
        ...,
        description="Type: deficit, debt_service, primary_deficit, contingent_liability",
    )
    metric_name: str = Field(..., description="Economic metric (e.g., deficit_gdp, debt_service_ratio)")
    current_value: float = Field(..., description="Current metric value")
    threshold_warning: float = Field(
        ..., description="Warning threshold value"
    )
    threshold_critical: float = Field(
        ..., description="Critical threshold value"
    )
    direction: str = Field(
        default="deteriorating",
        description="Direction: improving, stable, deteriorating",
    )
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    time_horizon_years: float = Field(
        default=5.0, ge=0, description="Projection horizon in years"
    )
    contributing_factors: List[str] = Field(
        default_factory=list, description="Root cause factors"
    )
    policy_responses: List[str] = Field(
        default_factory=list, description="Active or planned policy responses"
    )
    associated_risk_ids: List[str] = Field(
        default_factory=list, description="Related risk assessment IDs"
    )
    stress_test_scenario: Optional[str] = Field(
        None, description="Applied stress scenario name"
    )


class SovereignRiskIndicator(BaseModel):
    """A sovereign risk indicator drawn from existing risk modules."""

    id: str = Field(..., description="Unique indicator identifier")
    indicator_name: str = Field(..., description="Name of the indicator")
    category: str = Field(
        ...,
        description="Category: debt_crisis, liquidity, maturity, fx_stress, rating, contagion",
    )
    value: float = Field(..., description="Current indicator value")
    baseline: float = Field(..., description="Historical baseline value")
    warning_threshold: float = Field(
        ..., description="Threshold triggering warning level"
    )
    critical_threshold: float = Field(
        ..., description="Threshold triggering critical level"
    )
    direction: str = Field(
        default="stable",
        description="Direction: improving, stable, deteriorating",
    )
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    source: str = Field(..., description="Data source (e.g., IMF, WorldBank, central_bank)")
    risk_score: float = Field(
        ge=0, le=100, description="Derived risk score (0-100)"
    )
    related_risk_ids: List[str] = Field(
        default_factory=list, description="Related risk assessment IDs"
    )


class FiscalRisk(BaseModel):
    """Overall fiscal risk assessment extending existing risk modules."""

    id: str = Field(..., description="Unique fiscal risk assessment identifier")
    entity_id: str = Field(..., description="Government or portfolio identifier")
    entity_type: str = Field(
        default="government",
        description="Entity type: government, portfolio",
    )
    overall_score: float = Field(
        ge=0, le=100, description="Composite fiscal risk score (0-100)"
    )
    debt_sustainability_score: float = Field(
        ge=0, le=100, description="Debt sustainability sub-score (0-100)"
    )
    pressure_score: float = Field(
        ge=0, le=100, description="Active fiscal pressure sub-score (0-100)"
    )
    risk_indicators: List[SovereignRiskIndicator] = Field(
        default_factory=list
    )
    fiscal_pressures: List[FiscalPressure] = Field(
        default_factory=list
    )
    last_assessed: datetime = Field(default_factory=datetime.utcnow)
    projection_horizon_years: float = Field(
        default=10.0, ge=0, description="Projection horizon in years"
    )
    fiscal_position: str = Field(
        default="precarious",
        description="Fiscal position: strong, adequate, precarious, critical",
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Fiscal policy recommendations"
    )
    related_risk_ids: List[str] = Field(
        default_factory=list, description="Related risk assessment IDs"
    )


class FiscalRiskSummary(BaseModel):
    """Summary view for dashboard display."""

    risk_id: str
    overall_score: float
    debt_sustainability_score: float
    pressure_count: int
    critical_indicators: int
    last_assessed: datetime
    trending: str