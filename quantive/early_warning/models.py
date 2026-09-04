"""Pydantic models for the Early Warning System (Layer 5)."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class IndicatorConfig(BaseModel):
    """Configuration for an early warning indicator."""

    name: str = Field(..., description="Human-readable indicator name")
    description: str = Field(..., description="What the indicator measures")
    threshold: float = Field(..., ge=0, description="Warning threshold value")
    critical_threshold: float = Field(
        ..., ge=0, description="Critical threshold value"
    )
    direction: str = Field(
        ...,
        description="'above_danger' or 'below_danger' - which side of threshold is dangerous",
    )
    unit: str = Field(..., description="Unit of measurement")
    lookahead_months: int = Field(
        ..., ge=1, description="How many months ahead the indicator can detect"
    )
    bias_adjustment: float = Field(
        default=0.0,
        description="Bias direction adjustment factor from assumption registry",
    )


class WarningDetail(BaseModel):
    """Details of a single warning signal."""

    id: str = Field(default_factory=lambda: f"ew-{datetime.utcnow().isoformat()}")
    name: str
    category: str
    indicator: str
    current_value: float
    threshold: float
    unit: str
    direction: str
    status: str = Field(
        default="normal",
        description="'normal' | 'watch' | 'warning' | 'critical'",
    )
    trend: str = Field(
        default="stable",
        description="'improving' | 'stable' | 'deteriorating'",
    )
    description: str = Field(default="", description="Human-readable warning description")
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    months_until_crisis: Optional[float] = Field(
        default=None, description="Estimated months until crisis if trend continues"
    )
    bias_adjustment: float = Field(
        default=0.0, description="Adjusted threshold from assumption registry bias"
    )


class EarlyWarningResult(BaseModel):
    """Result of an early warning detection run."""

    entity_id: str
    run_timestamp: datetime = Field(default_factory=datetime.utcnow)
    warnings: List[WarningDetail] = Field(default_factory=list)
    summary: Dict[str, int] = Field(
        default_factory=lambda: {"normal": 0, "watch": 0, "warning": 0, "critical": 0}
    )
    total_months_lead: float = Field(
        default=0.0, description="Average months of lead time across all warnings"
    )


class EarlyWarningRequest(BaseModel):
    """Request to trigger early warning detection."""

    entity_id: str
    include_scenarios: bool = Field(
        default=True, description="Whether to include scenario projections"
    )
    bias_adjustment_mode: str = Field(
        default="registry",
        description="Bias adjustment mode: 'registry' | 'fixed' | 'none'",
    )
    horizon_months: Optional[int] = Field(
        default=12,
        ge=1,
        le=60,
        description="Analysis horizon in months",
    )


class ScenarioProjection(BaseModel):
    """A scenario projection for an indicator."""

    indicator_name: str
    current_value: float
    projected_values: Dict[int, float] = Field(
        default_factory=dict, description="Month -> projected value"
    )
    scenario_name: str = "baseline"
    confidence: float = 1.0