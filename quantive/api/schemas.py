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