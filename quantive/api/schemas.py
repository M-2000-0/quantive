"""API request/response schemas."""
from __future__ import annotations

from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field

from quantive.models.enums import Currency, StrategyProfile
from quantive.models.instruments import DebtInstrument
from quantive.models.optimization import (
    Constraint,
    OptimizationObjective,
    ScenarioConfiguration,
    SolverConfiguration,
)
from quantive.risk import RiskCategory, RiskSeverity, TrendDirection


class SyntheticPortfolioRequest(BaseModel):
    synthetic: Literal[True] = True
    seed: int = Field(42)
    name: str = "Synthetic Demonstration Portfolio"
    portfolio_id: Optional[str] = None


class PortfolioUploadRequest(BaseModel):
    synthetic: Literal[False] = False
    name: str = Field(..., description="Portfolio name")
    portfolio_id: Optional[str] = None
    description: Optional[str] = None
    reference_currency: Currency = Currency.USD
    instruments: List[DebtInstrument] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


PortfolioCreateRequest = Union[SyntheticPortfolioRequest, PortfolioUploadRequest]


class OptimizationProblemCreate(BaseModel):
    portfolio_id: str
    name: str = "Sovereign Debt Optimization"
    financing_requirement: float = Field(gt=0)
    objectives: Optional[OptimizationObjective] = None
    constraints: Optional[List[Constraint]] = None
    scenario_config: Optional[ScenarioConfiguration] = None
    solver_config: Optional[SolverConfiguration] = None
    profile: StrategyProfile = StrategyProfile.BEST_OVERALL
    problem_id: Optional[str] = None


class RunResponse(BaseModel):
    job_id: str
    problem_id: str
    status: str


# ── Layer 6 Risk Schemas ────────────────────────────────────────────────

class RiskCategoryLiteral(BaseModel):
    value: str


class RiskSeverityLiteral(BaseModel):
    value: str


class TrendDirectionLiteral(BaseModel):
    value: str


class AggregatedRiskResponse(BaseModel):
    overall_score: float
    by_category: dict
    category_counts: dict


class EarlyWarningSignalResponse(BaseModel):
    id: str
    name: str
    category: str
    indicator: str
    currentValue: float
    threshold: float
    unit: str
    direction: str
    status: str
    trend: str
    description: str
    lastUpdated: str