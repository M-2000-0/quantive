"""Debt instruments and portfolio models."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from quantive.models.enums import Currency, RateType


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DebtInstrument(BaseModel):
    """A single debt instrument.

    ``coupon`` is the annual coupon rate expressed as a decimal. For
    ``FIXED`` instruments it is the fixed coupon; for ``FLOATING`` instruments
    it is the spread paid over the reference benchmark rate.
    """

    id: str = Field(..., description="Stable unique instrument identifier")
    name: str = Field(..., description="Human readable instrument name")
    currency: Currency
    principal: float = Field(gt=0, description="Nominal face value outstanding (reporting-currency equivalent)")
    coupon: float = Field(ge=0, description="Annual coupon rate (fixed) or spread over benchmark (floating), as decimal")
    rate_type: RateType
    maturity_date: date
    issue_date: date
    callable: bool = Field(False, description="Instrument carries an issuer call option")
    liquidity: float = Field(0.5, ge=0, le=1, description="Market liquidity score, 0 = illiquid, 1 = deeply liquid")
    benchmark: Optional[str] = Field(None, description="Reference benchmark for floating instruments (e.g. SOFR)")
    market_capacity: Optional[float] = Field(None, ge=0, description="Maximum issuance capacity in this instrument")

    @field_validator("id")
    @classmethod
    def _id_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("instrument id must not be blank")
        return v.strip()

    @field_validator("maturity_date", "issue_date")
    @classmethod
    def _require_date(cls, v: date) -> date:
        return v

    @property
    def term_years(self) -> float:
        """Approximate term in years from issue to maturity."""
        return max(0.0, (self.maturity_date - self.issue_date).days / 365.25)

    def years_to_maturity(self, as_of: Optional[date] = None) -> float:
        ref = as_of or date.today()
        return max(0.0, (self.maturity_date - ref).days / 365.25)

    def is_foreign(self, reference_currency: Currency) -> bool:
        return self.currency != reference_currency

    @property
    def capacity(self) -> float:
        return self.market_capacity if self.market_capacity is not None else self.principal


class Portfolio(BaseModel):
    """A portfolio of debt instruments.

    ``instruments`` are the candidate issuance instruments. Computed views
    (currency exposure, maturity profile, rate exposure, total debt) are
    derived from the instruments via methods so that a portfolio is always a
    single source of truth.
    """

    id: str
    name: str
    description: Optional[str] = None
    reference_currency: Currency = Currency.USD
    instruments: List[DebtInstrument] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)

    @field_validator("id")
    @classmethod
    def _id_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("portfolio id must not be blank")
        return v.strip()

    def instrument_by_id(self, instrument_id: str) -> DebtInstrument:
        for inst in self.instruments:
            if inst.id == instrument_id:
                return inst
        raise KeyError(f"instrument {instrument_id!r} not found in portfolio {self.id!r}")

    def total_capacity(self) -> float:
        return sum(i.capacity for i in self.instruments)

    def total_principal(self) -> float:
        return sum(i.principal for i in self.instruments)

    def currency_exposure(self) -> Dict[Currency, float]:
        """Nominal principal exposure per currency."""
        out: Dict[Currency, float] = {}
        for inst in self.instruments:
            out[inst.currency] = out.get(inst.currency, 0.0) + inst.principal
        return out

    def rate_exposure(self) -> Dict[RateType, float]:
        """Nominal principal exposure per rate type."""
        out: Dict[RateType, float] = {}
        for inst in self.instruments:
            out[inst.rate_type] = out.get(inst.rate_type, 0.0) + inst.principal
        return out

    def maturity_profile(self, as_of: Optional[date] = None) -> Dict[int, float]:
        """Principal maturing per year bucket from today."""
        ref = as_of or date.today()
        out: Dict[int, float] = {}
        for inst in self.instruments:
            y = max(0, int((inst.maturity_date - ref).days / 365.25))
            out[y] = out.get(y, 0.0) + inst.principal
        return out

    def validate_unique_instrument_ids(self) -> None:
        seen: set[str] = set()
        for inst in self.instruments:
            if inst.id in seen:
                raise ValueError(f"duplicate instrument id {inst.id!r}")
            seen.add(inst.id)


def make_portfolio(
    portfolio_id: str,
    name: str,
    instruments: List[DebtInstrument],
    reference_currency: Currency = Currency.USD,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> Portfolio:
    portfolio = Portfolio(
        id=portfolio_id,
        name=name,
        instruments=instruments,
        reference_currency=reference_currency,
        description=description,
        tags=tags or [],
    )
    portfolio.validate_unique_instrument_ids()
    return portfolio