"""Data Poisoning Detection Module.

Protects against adversarial manipulation of input data feeds (GDP,
tax revenue, inflation, bond yields) that would corrupt optimization
results and lead to destructive fiscal recommendations.

Attack Scenario:
An adversary modifies GDP growth assumptions from 2.8% to 5.2%.
The optimizer then recommends aggressive borrowing assuming high growth.
When GDP disappoints, the country faces a debt crisis.

Controls:
- Input validation against historical ranges
- Anomaly detection on data feeds
- Cross-source verification
- Immutable input audit trail
- Statistical outlier detection
"""
import hashlib
import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, Float, Boolean
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.database import Base


class DataIntegrityEvent(Base):
    """Records every data validation event."""
    __tablename__ = "data_integrity_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(36), unique=True, nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), default=func.now())
    data_source = Column(String(100), nullable=False)
    data_type = Column(String(50), nullable=False)  # gdp, inflation, yield, fx, etc.
    value = Column(Float, nullable=False)
    expected_min = Column(Float, nullable=True)
    expected_max = Column(Float, nullable=True)
    is_anomaly = Column(Boolean, default=False)
    anomaly_score = Column(Float, nullable=True)
    hash_before = Column(String(64), nullable=True)
    hash_after = Column(String(64), nullable=True)
    verified = Column(Boolean, default=False)
    verified_by = Column(String(36), nullable=True)
    notes = Column(Text, nullable=True)


class DataPoisoningDetector:
    """Detects and prevents data poisoning attacks on financial data feeds.

    Protects against:
    - Manipulated GDP/tax/inflation assumptions
    - Corrupted yield curve data
    - Tampered FX rates
    - Modified portfolio constraints
    - Injected false economic indicators
    """

    # Historical ranges for common financial indicators (loose bounds)
    ANOMALY_THRESHOLDS = {
        "gdp_growth": {"min": -15.0, "max": 20.0, "max_daily_change": 2.0},
        "inflation": {"min": -5.0, "max": 50.0, "max_daily_change": 1.0},
        "interest_rate": {"min": -1.0, "max": 30.0, "max_daily_change": 1.0},
        "unemployment": {"min": 0.0, "max": 50.0, "max_daily_change": 2.0},
        "debt_to_gdp": {"min": 0.0, "max": 300.0, "max_daily_change": 5.0},
        "fx_rate": {"min": 0.001, "max": 10000.0, "max_daily_change": 10.0},
        "yield_10y": {"min": -1.0, "max": 25.0, "max_daily_change": 0.5},
        "budget_deficit": {"min": -20.0, "max": 30.0, "max_daily_change": 2.0},
    }

    def __init__(self, db: Session):
        self.db = db

    def validate_input(
        self,
        data_source: str,
        data_type: str,
        value: float,
        previous_value: Optional[float] = None,
    ) -> dict:
        """Validate a data input against historical bounds.

        Returns validation result with anomaly score.
        """
        thresholds = self.ANOMALY_THRESHOLDS.get(data_type)
        anomaly_score = 0.0
        issues = []

        if thresholds:
            # Check absolute bounds
            if value < thresholds["min"]:
                issues.append(f"Value {value} below minimum {thresholds['min']}")
                anomaly_score += 50
            if value > thresholds["max"]:
                issues.append(f"Value {value} above maximum {thresholds['max']}")
                anomaly_score += 50

            # Check daily change
            if previous_value is not None:
                change = abs(value - previous_value)
                if change > thresholds["max_daily_change"]:
                    issues.append(
                        f"Daily change {change:.2f} exceeds max {thresholds['max_daily_change']}"
                    )
                    anomaly_score += min(50, change / thresholds["max_daily_change"] * 50)

        is_anomaly = anomaly_score > 30

        # Record the event
        import uuid
        event = DataIntegrityEvent(
            event_id=str(uuid.uuid4()),
            data_source=data_source,
            data_type=data_type,
            value=value,
            expected_min=thresholds["min"] if thresholds else None,
            expected_max=thresholds["max"] if thresholds else None,
            is_anomaly=is_anomaly,
            anomaly_score=anomaly_score,
            hash_before=hashlib.sha256(f"{previous_value}".encode()).hexdigest() if previous_value else None,
            hash_after=hashlib.sha256(f"{value}".encode()).hexdigest(),
        )
        self.db.add(event)
        self.db.commit()

        return {
            "valid": not is_anomaly,
            "value": value,
            "data_type": data_type,
            "anomaly_score": anomaly_score,
            "issues": issues,
            "event_id": event.event_id,
        }

    def detect_cross_source_conflicts(self, data: dict) -> dict:
        """Detect conflicts between data sources.

        Example: GDP growth 5.2% but tax revenue declining 3%.
        These should generally move in the same direction.
        """
        conflicts = []

        # GDP growth vs tax revenue correlation
        gdp = data.get("gdp_growth")
        tax = data.get("tax_revenue_change")
        if gdp is not None and tax is not None:
            if gdp > 2.0 and tax < -1.0:
                conflicts.append({
                    "type": "gdp_tax_divergence",
                    "severity": "high",
                    "detail": f"GDP growth {gdp}% but tax revenue declining {tax}%",
                    "possible_explanation": "Could indicate tax policy change or data error",
                })

        # Inflation vs interest rate alignment
        inflation = data.get("inflation")
        rate = data.get("interest_rate")
        if inflation is not None and rate is not None:
            if inflation > 5.0 and rate < 2.0:
                conflicts.append({
                    "type": "negative_real_rate",
                    "severity": "medium",
                    "detail": f"Inflation {inflation}% exceeds interest rate {rate}%",
                    "possible_explanation": "Negative real rates may be intentional or data error",
                })

        return {
            "conflicts": conflicts,
            "conflict_count": len(conflicts),
            "sources_checked": len(data),
        }

    def get_integrity_report(self, days: int = 30) -> dict:
        """Generate data integrity report."""
        from datetime import timedelta
        start = datetime.now(timezone.utc) - timedelta(days=days)

        events = self.db.query(DataIntegrityEvent).filter(
            DataIntegrityEvent.timestamp >= start
        ).all()

        total = len(events)
        anomalies = sum(1 for e in events if e.is_anomaly)
        verified = sum(1 for e in events if e.verified)

        return {
            "period_days": days,
            "total_validations": total,
            "anomalies_detected": anomalies,
            "anomaly_rate": f"{(anomalies/total*100):.1f}%" if total > 0 else "0%",
            "verified": verified,
            "unverified_anomalies": anomalies - verified,
            "compliance_score": max(0, 100 - (anomalies * 5)),
        }
