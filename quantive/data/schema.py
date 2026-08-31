"""Unified market data schema — OHLCV + fundamentals, provider-agnostic.

All downstream engines consume these validated models so swapping data sources
is a config change, not a code change.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Literal, Optional

import pandas as pd
from pydantic import BaseModel, Field, field_validator


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OHLCVBar(BaseModel):
    """Single OHLCV bar — validated, timezone-aware."""

    ticker: str = Field(..., min_length=1, description="Ticker symbol, upper-cased")
    timestamp: datetime = Field(..., description="Bar open time, UTC")
    open: float = Field(..., ge=0)
    high: float = Field(..., ge=0)
    low: float = Field(..., ge=0)
    close: float = Field(..., ge=0)
    volume: float = Field(..., ge=0)
    adj_close: Optional[float] = Field(None, ge=0, description="Split/dividend adjusted close")
    source: str = Field("unknown")
    interval: str = Field("1d", description="Bar interval: 1d, 1h, 5m etc")

    @field_validator("ticker")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("timestamp")
    @classmethod
    def _utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)

    @field_validator("high")
    @classmethod
    def _high_gte_low(cls, v: float, info) -> float:  # noqa: ARG003
        return v

    def model_post_validate(self, ctx):  # type: ignore[override]
        if self.high < max(self.open, self.close, self.low) - 1e-9:
            raise ValueError(f"high {self.high} < max(open,close,low)")
        if self.low > min(self.open, self.close) + 1e-9:
            raise ValueError(f"low {self.low} > min(open,close)")
        return self


class FundamentalSnapshot(BaseModel):
    """Point-in-time fundamentals for one ticker."""

    ticker: str = Field(..., min_length=1)
    as_of: date
    # Valuation
    pe: Optional[float] = None
    forward_pe: Optional[float] = None
    peg: Optional[float] = None
    price_to_sales: Optional[float] = None
    price_to_book: Optional[float] = None
    ev_to_ebitda: Optional[float] = None
    ev_to_sales: Optional[float] = None
    fcf_yield: Optional[float] = None
    earnings_yield: Optional[float] = None
    # Growth / quality
    revenue_growth: Optional[float] = None
    eps_growth: Optional[float] = None
    fcf_growth: Optional[float] = None
    roic: Optional[float] = None
    roe: Optional[float] = None
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    # Health
    debt_to_equity: Optional[float] = None
    net_debt: Optional[float] = None
    interest_coverage: Optional[float] = None
    current_ratio: Optional[float] = None
    free_cash_flow: Optional[float] = None
    cash_reserves: Optional[float] = None
    # Earnings quality flags
    accruals: Optional[float] = None
    earnings_surprise: Optional[float] = None
    source: str = "unknown"

    @field_validator("ticker")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.strip().upper()


class DataQualityIssue(BaseModel):
    """One data quality finding."""

    severity: Literal["error", "warning", "info"]
    code: str
    message: str
    ticker: Optional[str] = None
    timestamp: Optional[datetime] = None
    field: Optional[str] = None


class DataQualityReport(BaseModel):
    """Result of a quality check run."""

    dataset_id: str
    checked_at: datetime = Field(default_factory=_utcnow)
    total_bars: int = 0
    issues: list[DataQualityIssue] = Field(default_factory=list)
    passed: bool = True
    stats: dict = Field(default_factory=dict)

    @property
    def errors(self) -> list[DataQualityIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[DataQualityIssue]:
        return [i for i in self.issues if i.severity == "warning"]


# -- Helpers to convert to/from pandas ------------------------------------

def bars_to_dataframe(bars: list[OHLCVBar]) -> pd.DataFrame:
    """Convert validated bars to a sorted DataFrame indexed by timestamp."""
    if not bars:
        return pd.DataFrame(columns=["ticker", "timestamp", "open", "high", "low", "close", "volume", "adj_close"])
    df = pd.DataFrame([b.model_dump() for b in bars])
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values(["ticker", "timestamp"]).reset_index(drop=True)
    return df


def dataframe_to_bars(df: pd.DataFrame) -> list[OHLCVBar]:
    """Convert DataFrame to validated bars — raises on bad data."""
    bars: list[OHLCVBar] = []
    for _, row in df.iterrows():
        bars.append(OHLCVBar(**row.to_dict()))
    return bars
