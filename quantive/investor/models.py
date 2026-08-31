"""Investor profile models — §3-5.

Distinguishes risk tolerance (psychological) vs risk capacity (financial).
Flags conflicts where tolerance > capacity.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class Horizon(str, Enum):
    SHORT = "short"    # < 2y
    MEDIUM = "medium"  # 2-7y
    LONG = "long"      # >7y


class InvestmentObjective(str, Enum):
    CAPITAL_PRESERVATION = "capital_preservation"
    INCOME = "income"
    BALANCED = "balanced"
    GROWTH = "growth"
    AGGRESSIVE_GROWTH = "aggressive_growth"
    SPECULATIVE = "speculative"


class ESGPreference(BaseModel):
    enabled: bool = False
    exclude_sectors: list[str] = Field(default_factory=list)
    min_esg_score: Optional[float] = Field(None, ge=0, le=100)


class RiskTolerance(BaseModel):
    """What losses is the user psychologically comfortable with?"""

    max_acceptable_drawdown: float = Field(0.20, ge=0, le=1, description="e.g. 0.40 = 40% DD ok")
    volatility_tolerance: Literal["low", "medium", "high"] = "medium"
    comfort_with_loss_pct: float = Field(20.0, ge=0, le=100)


class RiskCapacity(BaseModel):
    """What losses can the user financially withstand?"""

    max_sustainable_drawdown: float = Field(0.20, ge=0, le=1)
    liquidity_need_pct: float = Field(0.10, ge=0, le=1, description="Share needed liquid within 1y")
    investment_horizon_years: float = Field(5.0, ge=0)
    portfolio_size: float = Field(100_000, ge=0)
    income_stability: Literal["low", "medium", "high"] = "medium"


class InvestorProfile(BaseModel):
    """Full investor profile — §3."""

    id: str = Field(..., min_length=1)
    age_range: Optional[str] = Field(None, description="e.g. '30-40'")
    horizon: Horizon = Horizon.MEDIUM
    risk_tolerance: RiskTolerance = Field(default_factory=RiskTolerance)
    risk_capacity: RiskCapacity = Field(default_factory=RiskCapacity)
    investment_objective: InvestmentObjective = InvestmentObjective.BALANCED
    geographic_preferences: list[str] = Field(default_factory=list)
    sector_preferences: list[str] = Field(default_factory=list)
    esg: ESGPreference = Field(default_factory=ESGPreference)
    max_position_size: float = Field(0.20, ge=0, le=1)
    min_diversification: int = Field(5, ge=1)
    max_volatility: Optional[float] = Field(None, ge=0)
    max_drawdown_target: Optional[float] = Field(None, ge=0, le=1)
    rebalancing_preference: Literal["daily", "weekly", "monthly", "quarterly"] = "monthly"
    trading_frequency_preference: Literal["low", "medium", "high"] = "medium"
    investment_experience: Literal["novice", "intermediate", "experienced"] = "intermediate"
    concentration_preference: Literal["diversified", "moderate", "concentrated"] = "moderate"
    tax_considerations: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("id")
    @classmethod
    def _id_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("id must not be blank")
        return v.strip()

    def horizon_years(self) -> float:
        return {"short": 1.0, "medium": 5.0, "long": 10.0}[self.horizon.value]

    def is_speculative_allowed(self) -> bool:
        return self.investment_objective == InvestmentObjective.SPECULATIVE

    def risk_conflict(self) -> Optional[str]:
        """If tolerance > capacity, return conflict description."""
        tol = self.risk_tolerance.max_acceptable_drawdown
        cap = self.risk_capacity.max_sustainable_drawdown
        if tol > cap + 1e-9:
            return (
                f"Risk tolerance ({tol:.0%} DD) exceeds financial capacity ({cap:.0%} DD). "
                f"Quantive will constrain to capacity unless explicitly acknowledged."
            )
        return None
