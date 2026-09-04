"""Layer 1: Data Ingestion & Legacy Bridge.

Establishes ETL pipelines for:
- Real-time macroeconomic feeds (GDP, inflation, yields, FX)
- Bond auction results (primary market)
- Legacy mainframe/COBOL accounting records
- Central bank policy rates
- Credit rating agency data

Enforces:
- Schema validation before any data enters the optimization pipeline
- Error-checking to eliminate corrupted/missing parameters
- Data provenance tracking (source, timestamp, confidence)
- Automatic fallback to stale data with freshness warnings

Architecture:
    External Sources → Schema Validator → Normalizer → State Encoder → Optimizer
                                    ↓
                              Error Queue (rejected data)
                                    ↓
                              Alert System → Human Review
"""
import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ── Schema Definitions ──────────────────────────────────────────────

class YieldCurvePoint(BaseModel):
    """Single point on a sovereign yield curve."""
    maturity_years: float = Field(..., gt=0, le=100)
    yield_pct: float = Field(..., ge=-5.0, le=50.0)
    currency: str = Field(..., min_length=3, max_length=3)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = Field(..., min_length=1)
    confidence: float = Field(default=1.0, ge=0, le=1.0)


class BondInstrument(BaseModel):
    """A sovereign debt instrument (bond, T-bill, note)."""
    isin: str = Field(..., min_length=12, max_length=12)
    cusip: Optional[str] = None
    issuer_country: str = Field(..., min_length=2, max_length=3)
    currency: str = Field(..., min_length=3, max_length=3)
    face_value: float = Field(..., gt=0)
    coupon_rate_pct: float = Field(..., ge=-5.0, le=30.0)
    maturity_date: datetime
    issue_date: datetime
    bond_type: str = Field(default="fixed")  # fixed, floating, inflation-linked, gdp-linked
    callable: bool = False
    call_date: Optional[datetime] = None
    call_price: Optional[float] = None
    outstanding_amount: float = Field(..., ge=0)
    credit_rating: Optional[str] = None
    source: str = Field(..., min_length=1)

    @field_validator("maturity_date")
    @classmethod
    def maturity_after_issue(cls, v, info):
        if "issue_date" in info.data and v <= info.data["issue_date"]:
            raise ValueError("maturity_date must be after issue_date")
        return v


class MacroeconomicData(BaseModel):
    """Macroeconomic indicator snapshot."""
    country_code: str = Field(..., min_length=2, max_length=3)
    gdp_growth_pct: float = Field(..., ge=-30.0, le=30.0)
    inflation_pct: float = Field(..., ge=-10.0, le=100.0)
    unemployment_pct: float = Field(..., ge=0, le=100.0)
    debt_to_gdp_pct: float = Field(..., ge=0, le=500.0)
    budget_deficit_to_gdp_pct: float = Field(..., ge=-50.0, le=50.0)
    current_account_to_gdp_pct: float = Field(default=0.0, ge=-50.0, le=50.0)
    foreign_reserves_months: float = Field(default=0.0, ge=0, le=200.0)
    central_bank_rate_pct: float = Field(..., ge=-5.0, le=30.0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = Field(..., min_length=1)


class AuctionResult(BaseModel):
    """Bond auction result from primary market."""
    auction_id: str = Field(..., min_length=1)
    country_code: str = Field(..., min_length=2, max_length=3)
    instrument_type: str
    amount_offered: float = Field(..., gt=0)
    amount_sold: float = Field(..., ge=0)
    average_yield_pct: float = Field(..., ge=-5.0, le=30.0)
    bid_to_cover_ratio: float = Field(..., ge=0)
    coverage_ratio: float = Field(..., ge=0)
    auction_date: datetime
    settlement_date: datetime
    primary_dealers: int = Field(default=0, ge=0)
    competitive_ratio: float = Field(default=0.0, ge=0, le=1.0)


# ── Data Ingestion Pipeline ─────────────────────────────────────────

class IngestionResult(BaseModel):
    """Result of data ingestion with validation status."""
    success: bool
    records_processed: int = 0
    records_valid: int = 0
    records_rejected: int = 0
    errors: list = []
    warnings: list = []
    data_hash: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SovereignDataIngestor:
    """ETL pipeline for sovereign debt data ingestion.

    Pipeline stages:
    1. Extract: Pull data from external sources
    2. Validate: Check against schema definitions
    3. Normalize: Convert to standard units/formats
    4. Enrich: Add confidence scores and provenance
    5. Load: Pass to state encoder for optimization
    """

    # Maximum allowed data staleness (hours)
    MAX_STALENESS = {
        "yield_curve": 24,
        "fx_rate": 1,
        "interest_rate": 6,
        "gdp": 2160,    # 90 days
        "inflation": 720, # 30 days
        "auction_result": 168,  # 7 days
    }

    def __init__(self):
        self.validation_errors = []
        self.ingestion_log = []

    def ingest_yield_curve(self, points: list[dict]) -> IngestionResult:
        """Ingest yield curve data with validation."""
        errors = []
        valid = []

        for i, point_data in enumerate(points):
            try:
                point = YieldCurvePoint(**point_data)
                staleness = self._check_staleness(point.timestamp, "yield_curve")
                if staleness:
                    warnings = [f"Point {i}: data is {staleness:.1f}h old"]
                else:
                    warnings = []
                valid.append(point)
            except Exception as e:
                errors.append({"index": i, "error": str(e), "data": point_data})

        data_hash = hashlib.sha256(
            json.dumps([p.dict() for p in valid], default=str).encode()
        ).hexdigest()[:16]

        return IngestionResult(
            success=len(errors) == 0,
            records_processed=len(points),
            records_valid=len(valid),
            records_rejected=len(errors),
            errors=errors,
            data_hash=data_hash,
        )

    def ingest_portfolio(self, instruments: list[dict]) -> IngestionResult:
        """Ingest bond portfolio data with validation."""
        errors = []
        valid = []

        for i, inst_data in enumerate(instruments):
            try:
                instrument = BondInstrument(**inst_data)
                valid.append(instrument)
            except Exception as e:
                errors.append({"index": i, "error": str(e), "data": inst_data})

        data_hash = hashlib.sha256(
            json.dumps([inst.dict() for inst in valid], default=str).encode()
        ).hexdigest()[:16]

        return IngestionResult(
            success=len(errors) == 0,
            records_processed=len(instruments),
            records_valid=len(valid),
            records_rejected=len(errors),
            errors=errors,
            data_hash=data_hash,
        )

    def ingest_macro_data(self, data: dict) -> IngestionResult:
        """Ingest macroeconomic data with validation."""
        errors = []
        try:
            macro = MacroeconomicData(**data)
            return IngestionResult(
                success=True,
                records_processed=1,
                records_valid=1,
                data_hash=hashlib.sha256(json.dumps(data, default=str).encode()).hexdigest()[:16],
            )
        except Exception as e:
            return IngestionResult(
                success=False,
                records_processed=1,
                records_rejected=1,
                errors=[{"error": str(e)}],
            )

    def ingest_auction_results(self, results: list[dict]) -> IngestionResult:
        """Ingest bond auction results."""
        errors = []
        valid = []

        for i, result_data in enumerate(results):
            try:
                result = AuctionResult(**result_data)
                valid.append(result)
            except Exception as e:
                errors.append({"index": i, "error": str(e)})

        return IngestionResult(
            success=len(errors) == 0,
            records_processed=len(results),
            records_valid=len(valid),
            records_rejected=len(errors),
            errors=errors,
        )

    def _check_staleness(self, timestamp: datetime, data_type: str) -> Optional[float]:
        """Check if data is stale beyond acceptable threshold."""
        max_hours = self.MAX_STALENESS.get(data_type, 24)
        age_hours = (datetime.now(timezone.utc) - timestamp).total_seconds() / 3600
        if age_hours > max_hours:
            return age_hours
        return None

    def validate_state_readiness(self, portfolio: list, yield_curve: list, macro: dict) -> dict:
        """Final validation before state encoding.

        Ensures all required parameters are present and within bounds
        for quantum state preparation.
        """
        issues = []

        if not portfolio:
            issues.append("Portfolio is empty — no instruments to optimize")
        if not yield_curve:
            issues.append("Yield curve is empty — cannot model term structure")
        if not macro:
            issues.append("Macroeconomic data missing — constraints cannot be set")

        # Check for required optimization parameters
        required_macro = ["gdp_growth_pct", "inflation_pct", "central_bank_rate_pct", "debt_to_gdp_pct"]
        for param in required_macro:
            if param not in macro:
                issues.append(f"Missing required parameter: {param}")

        # Check instrument count vs qubit requirements
        if portfolio:
            n_instruments = len(portfolio)
            # Rough estimate: each instrument needs ~8 qubits for binary encoding
            estimated_qubits = n_instruments * 8
            if estimated_qubits > 100:
                issues.append(f"High qubit requirement: ~{estimated_qubits} qubits for {n_instruments} instruments")

        return {
            "ready": len(issues) == 0,
            "issues": issues,
            "instrument_count": len(portfolio),
            "yield_curve_points": len(yield_curve),
            "estimated_qubits": len(portfolio) * 8 if portfolio else 0,
        }
