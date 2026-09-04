"""
Market Data Quality Framework

Provides:
- Range validation for all data types
- Cross-source consistency checks
- Anomaly detection (spikes, gaps, reversals)
- Source health scoring (0-100)
- Freshness tracking with staleness alerts
- Quality metrics for monitoring

Implements the Quantive Data Integrity Framework.
"""

import logging
import math
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("quantive.market_data.quality")


# ── Enums ─────────────────────────────────────────────────────────────

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


class AnomalyType(str, Enum):
    SPIKE = "spike"
    DROP = "drop"
    MISSING = "missing"
    DUPLICATE = "duplicate"
    REVERSAL = "reversal"
    OUT_OF_RANGE = "out_of_range"


# ── Data Models ───────────────────────────────────────────────────────

@dataclass
class ValidationRule:
    """A single validation rule for a data type."""
    field_name: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    required: bool = True
    description: str = ""


@dataclass
class ValidationResult:
    """Result of validating a single data point."""
    is_valid: bool
    field_name: str
    value: Any
    rule: ValidationRule
    error_message: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class Anomaly:
    """Detected anomaly in market data."""
    anomaly_type: AnomalyType
    field_name: str
    value: float
    expected_range: tuple[float, float]
    severity: str  # "low", "medium", "high", "critical"
    message: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class SourceHealth:
    """Health status of a data source."""
    source_name: str
    health_score: float  # 0-100
    status: HealthStatus
    completeness: float  # 0-1
    timeliness: float  # 0-1
    accuracy: float  # 0-1
    last_successful_fetch: Optional[float] = None
    consecutive_failures: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    avg_response_time_ms: float = 0
    last_error: Optional[str] = None


@dataclass
class FreshnessInfo:
    """Freshness status of a data point."""
    data_type: str
    last_updated: Optional[float] = None
    expected_frequency_seconds: int = 300  # 5 minutes default
    is_stale: bool = False
    staleness_level: str = "fresh"  # "fresh", "warning", "critical", "dead"
    age_seconds: Optional[float] = None


# ── Validation Rules ──────────────────────────────────────────────────

VALIDATION_RULES: dict[str, list[ValidationRule]] = {
    "treasury_yield": [
        ValidationRule("yield_pct", min_value=-1.0, max_value=25.0, description="Treasury yield percentage"),
        ValidationRule("maturity", required=True, description="Maturity label"),
        ValidationRule("date", required=True, description="Observation date"),
    ],
    "fx_rate": [
        ValidationRule("rate", min_value=0.001, max_value=10000.0, description="Exchange rate"),
        ValidationRule("pair", required=True, description="Currency pair"),
    ],
    "economic_indicator": [
        ValidationRule("value", min_value=-50.0, max_value=500.0, description="Indicator value"),
        ValidationRule("indicator_code", required=True, description="Indicator code"),
    ],
    "interest_rate": [
        ValidationRule("rate_pct", min_value=-5.0, max_value=30.0, description="Interest rate percentage"),
    ],
}

# Specific ranges for known indicators
INDICATOR_RANGES: dict[str, tuple[float, float]] = {
    "inflation_cpi": (-5.0, 50.0),
    "gdp_growth": (-30.0, 30.0),
    "debt_to_gdp": (0.0, 300.0),
    "unemployment_rate": (0.0, 50.0),
    "fed_funds_rate": (-1.0, 25.0),
    "vix": (5.0, 150.0),
    "gold_price": (100.0, 10000.0),
    "oil_price": (0.0, 300.0),
}


# ── Core Quality Service ──────────────────────────────────────────────

class DataQualityService:
    """Central service for market data quality assurance."""

    def __init__(self):
        self._lock = threading.Lock()
        self._source_health: dict[str, SourceHealth] = {}
        self._freshness: dict[str, FreshnessInfo] = {}
        self._anomalies: list[Anomaly] = []
        self._validation_log: list[ValidationResult] = []
        self._max_anomalies = 1000
        self._max_validation_log = 5000

    # ── Range Validation ──────────────────────────────────────────

    def validate_range(
        self,
        field_name: str,
        value: float,
        data_type: str = "treasury_yield",
    ) -> ValidationResult:
        """Validate a data point against its range rules."""
        rules = VALIDATION_RULES.get(data_type, [])
        for rule in rules:
            if rule.field_name != field_name:
                continue

            if rule.min_value is not None and value < rule.min_value:
                result = ValidationResult(
                    is_valid=False,
                    field_name=field_name,
                    value=value,
                    rule=rule,
                    error_message=f"{field_name}={value} below minimum {rule.min_value}",
                )
                self._log_validation(result)
                return result

            if rule.max_value is not None and value > rule.max_value:
                result = ValidationResult(
                    is_valid=False,
                    field_name=field_name,
                    value=value,
                    rule=rule,
                    error_message=f"{field_name}={value} above maximum {rule.max_value}",
                )
                self._log_validation(result)
                return result

        # Check indicator-specific ranges
        if field_name in INDICATOR_RANGES:
            min_val, max_val = INDICATOR_RANGES[field_name]
            if value < min_val or value > max_val:
                result = ValidationResult(
                    is_valid=False,
                    field_name=field_name,
                    value=value,
                    rule=ValidationRule(field_name, min_val, max_val),
                    error_message=f"{field_name}={value} outside expected range [{min_val}, {max_val}]",
                )
                self._log_validation(result)
                return result

        result = ValidationResult(
            is_valid=True,
            field_name=field_name,
            value=value,
            rule=ValidationRule(field_name, description="auto"),
        )
        self._log_validation(result)
        return result

    def validate_batch(
        self,
        data_points: list[dict],
        data_type: str = "treasury_yield",
    ) -> list[ValidationResult]:
        """Validate a batch of data points."""
        results = []
        for point in data_points:
            for field_name, value in point.items():
                if isinstance(value, (int, float)):
                    result = self.validate_range(field_name, float(value), data_type)
                    results.append(result)
        return results

    # ── Cross-Source Consistency ───────────────────────────────────

    def check_consistency(
        self,
        values: list[float],
        source_names: list[str],
        field_name: str,
        tolerance_pct: float = 1.0,
    ) -> dict:
        """Check consistency across multiple sources."""
        if len(values) < 2:
            return {"consistent": True, "message": "Single source, no comparison needed"}

        avg = sum(values) / len(values)
        if avg == 0:
            return {"consistent": False, "message": "Average is zero, cannot compare"}

        deviations = []
        for i, (val, src) in enumerate(zip(values, source_names)):
            deviation_pct = abs(val - avg) / abs(avg) * 100
            deviations.append({
                "source": src,
                "value": val,
                "deviation_pct": round(deviation_pct, 2),
            })

        max_deviation = max(d["deviation_pct"] for d in deviations)

        if max_deviation <= tolerance_pct:
            return {
                "consistent": True,
                "message": f"All sources within {tolerance_pct}% tolerance",
                "max_deviation_pct": max_deviation,
                "details": deviations,
            }
        elif max_deviation <= tolerance_pct * 3:
            return {
                "consistent": True,
                "message": f"Sources divergent but within acceptable range (max {max_deviation:.1f}%)",
                "max_deviation_pct": max_deviation,
                "warning": True,
                "details": deviations,
            }
        else:
            return {
                "consistent": False,
                "message": f"Sources divergent by {max_deviation:.1f}% — data rejected",
                "max_deviation_pct": max_deviation,
                "details": deviations,
            }

    def check_yield_curve_ordering(
        self,
        yields: dict[str, float],
    ) -> dict:
        """Verify yield curve has normal ordering (longer tenor = higher yield, generally)."""
        maturity_years = {
            "1M": 1/12, "3M": 3/12, "6M": 6/12, "1Y": 1,
            "2Y": 2, "3Y": 3, "5Y": 5, "7Y": 7,
            "10Y": 10, "20Y": 20, "30Y": 30,
        }

        issues = []
        sorted_maturities = sorted(
            [(m, yields.get(m, 0), maturity_years.get(m, 0)) for m in yields],
            key=lambda x: x[2],
        )

        for i in range(1, len(sorted_maturities)):
            prev_label, prev_yield, prev_years = sorted_maturities[i - 1]
            curr_label, curr_yield, curr_years = sorted_maturities[i]

            # Allow inversion for short end (normal in some conditions)
            if curr_years > 2 and curr_yield < prev_yield:
                issues.append({
                    "from": prev_label,
                    "to": curr_label,
                    "from_yield": prev_yield,
                    "to_yield": curr_yield,
                    "inversion_bps": round((prev_yield - curr_yield) * 100, 1),
                })

        return {
            "normal": len(issues) == 0,
            "inversions": issues,
            "message": "Normal curve" if not issues else f"{len(issues)} inversion(s) detected",
        }

    # ── Anomaly Detection ─────────────────────────────────────────

    def detect_anomalies(
        self,
        current_value: float,
        historical_values: list[float],
        field_name: str,
        threshold_std: float = 3.0,
    ) -> list[Anomaly]:
        """Detect anomalies in incoming data."""
        anomalies = []

        if len(historical_values) < 5:
            return anomalies

        mean = sum(historical_values) / len(historical_values)
        variance = sum((x - mean) ** 2 for x in historical_values) / len(historical_values)
        std = math.sqrt(variance) if variance > 0 else 0

        if std == 0:
            return anomalies

        z_score = (current_value - mean) / std

        # Spike detection
        if z_score > threshold_std:
            anomalies.append(Anomaly(
                anomaly_type=AnomalyType.SPIKE,
                field_name=field_name,
                value=current_value,
                expected_range=(mean - threshold_std * std, mean + threshold_std * std),
                severity="high" if z_score > 4 else "medium",
                message=f"Spike detected: {field_name}={current_value} (z-score={z_score:.2f})",
            ))

        # Drop detection
        if z_score < -threshold_std:
            anomalies.append(Anomaly(
                anomaly_type=AnomalyType.DROP,
                field_name=field_name,
                value=current_value,
                expected_range=(mean - threshold_std * std, mean + threshold_std * std),
                severity="high" if z_score < -4 else "medium",
                message=f"Drop detected: {field_name}={current_value} (z-score={z_score:.2f})",
            ))

        # Direction reversal (if we have at least 3 points)
        if len(historical_values) >= 3:
            last_two = historical_values[-2:]
            if current_value > last_two[1] > last_two[0]:
                # Was going down, now going up — check if significant
                reversal = abs(current_value - last_two[0]) / std
                if reversal > threshold_std:
                    anomalies.append(Anomaly(
                        anomaly_type=AnomalyType.REVERSAL,
                        field_name=field_name,
                        value=current_value,
                        expected_range=(last_two[0] - std, last_two[0] + std),
                        severity="low",
                        message=f"Direction reversal: {field_name} changed direction significantly",
                    ))

        # Store anomalies
        with self._lock:
            self._anomalies.extend(anomalies)
            if len(self._anomalies) > self._max_anomalies:
                self._anomalies = self._anomalies[-self._max_anomalies:]

        return anomalies

    # ── Source Health Scoring ──────────────────────────────────────

    def record_fetch(
        self,
        source_name: str,
        success: bool,
        response_time_ms: float = 0,
        error: Optional[str] = None,
    ):
        """Record a fetch attempt for health scoring."""
        with self._lock:
            if source_name not in self._source_health:
                self._source_health[source_name] = SourceHealth(
                    source_name=source_name,
                    health_score=100.0,
                    status=HealthStatus.HEALTHY,
                    completeness=1.0,
                    timeliness=1.0,
                    accuracy=1.0,
                )

            health = self._source_health[source_name]
            health.total_requests += 1

            if success:
                health.successful_requests += 1
                health.consecutive_failures = 0
                health.last_successful_fetch = time.time()
                # Update rolling average response time
                if health.avg_response_time_ms == 0:
                    health.avg_response_time_ms = response_time_ms
                else:
                    health.avg_response_time_ms = (
                        health.avg_response_time_ms * 0.8 + response_time_ms * 0.2
                    )
            else:
                health.consecutive_failures += 1
                health.last_error = error

            # Calculate health score
            health.health_score = self._calculate_health_score(health)
            health.status = self._determine_status(health.health_score)

    def _calculate_health_score(self, health: SourceHealth) -> float:
        """Calculate health score (0-100) based on success rate and recency."""
        if health.total_requests == 0:
            return 100.0

        success_rate = health.successful_requests / health.total_requests
        success_score = success_rate * 60  # 60% weight

        # Recency score (how recently did we get a successful fetch?)
        if health.last_successful_fetch:
            age_minutes = (time.time() - health.last_successful_fetch) / 60
            if age_minutes < 5:
                recency_score = 40
            elif age_minutes < 15:
                recency_score = 30
            elif age_minutes < 60:
                recency_score = 20
            else:
                recency_score = 10
        else:
            recency_score = 0

        # Penalty for consecutive failures
        failure_penalty = min(health.consecutive_failures * 5, 30)

        score = max(0, success_score + recency_score - failure_penalty)
        return round(score, 1)

    def _determine_status(self, score: float) -> HealthStatus:
        """Determine health status from score."""
        if score >= 90:
            return HealthStatus.HEALTHY
        elif score >= 70:
            return HealthStatus.DEGRADED
        elif score >= 50:
            return HealthStatus.UNHEALTHY
        else:
            return HealthStatus.CRITICAL

    def get_source_health(self, source_name: Optional[str] = None) -> dict:
        """Get health status for one or all sources."""
        with self._lock:
            if source_name:
                health = self._source_health.get(source_name)
                if not health:
                    return {"error": f"Source '{source_name}' not found"}
                return {
                    "source": health.source_name,
                    "health_score": health.health_score,
                    "status": health.status.value,
                    "completeness": health.completeness,
                    "timeliness": health.timeliness,
                    "accuracy": health.accuracy,
                    "total_requests": health.total_requests,
                    "success_rate": (
                        health.successful_requests / health.total_requests
                        if health.total_requests > 0 else 0
                    ),
                    "consecutive_failures": health.consecutive_failures,
                    "avg_response_time_ms": round(health.avg_response_time_ms, 1),
                    "last_error": health.last_error,
                }
            else:
                return {
                    name: {
                        "health_score": h.health_score,
                        "status": h.status.value,
                        "success_rate": (
                            h.successful_requests / h.total_requests
                            if h.total_requests > 0 else 0
                        ),
                    }
                    for name, h in self._source_health.items()
                }

    # ── Freshness Tracking ─────────────────────────────────────────

    def update_freshness(
        self,
        data_type: str,
        last_updated: Optional[float] = None,
        expected_frequency_seconds: int = 300,
    ):
        """Update freshness tracking for a data type."""
        now = time.time()
        updated = last_updated or now
        age = now - updated

        if age < expected_frequency_seconds:
            level = "fresh"
        elif age < expected_frequency_seconds * 2:
            level = "warning"
        elif age < expected_frequency_seconds * 5:
            level = "critical"
        else:
            level = "dead"

        with self._lock:
            self._freshness[data_type] = FreshnessInfo(
                data_type=data_type,
                last_updated=updated,
                expected_frequency_seconds=expected_frequency_seconds,
                is_stale=level != "fresh",
                staleness_level=level,
                age_seconds=age,
            )

    def get_freshness(self) -> dict:
        """Get freshness status for all data types."""
        with self._lock:
            return {
                name: {
                    "staleness_level": f.staleness_level,
                    "age_seconds": round(f.age_seconds, 1) if f.age_seconds else None,
                    "expected_frequency_seconds": f.expected_frequency_seconds,
                    "is_stale": f.is_stale,
                }
                for name, f in self._freshness.items()
            }

    # ── Quality Metrics ───────────────────────────────────────────

    def get_quality_metrics(self) -> dict:
        """Get overall data quality metrics."""
        with self._lock:
            total_sources = len(self._source_health)
            healthy_sources = sum(
                1 for h in self._source_health.values()
                if h.status == HealthStatus.HEALTHY
            )
            total_requests = sum(h.total_requests for h in self._source_health.values())
            successful_requests = sum(h.successful_requests for h in self._source_health.values())
            total_anomalies = len(self._anomalies)
            recent_anomalies = sum(
                1 for a in self._anomalies
                if time.time() - a.timestamp < 3600
            )
            stale_data = sum(
                1 for f in self._freshness.values()
                if f.is_stale
            )

        completeness = successful_requests / total_requests if total_requests > 0 else 1.0
        health_ratio = healthy_sources / total_sources if total_sources > 0 else 1.0

        return {
            "overall_health_score": round(health_ratio * 60 + completeness * 40, 1),
            "completeness": round(completeness, 3),
            "sources": {
                "total": total_sources,
                "healthy": healthy_sources,
                "degraded": total_sources - healthy_sources,
            },
            "requests": {
                "total": total_requests,
                "successful": successful_requests,
                "success_rate": round(completeness, 3),
            },
            "anomalies": {
                "total": total_anomalies,
                "last_hour": recent_anomalies,
            },
            "freshness": {
                "total_types": len(self._freshness),
                "stale": stale_data,
            },
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    def get_anomalies(
        self,
        hours: int = 24,
        severity: Optional[str] = None,
    ) -> list[dict]:
        """Get recent anomalies."""
        cutoff = time.time() - (hours * 3600)
        with self._lock:
            recent = [
                a for a in self._anomalies
                if a.timestamp > cutoff
            ]
            if severity:
                recent = [a for a in recent if a.severity == severity]

        return [
            {
                "type": a.anomaly_type.value,
                "field": a.field_name,
                "value": a.value,
                "expected_range": a.expected_range,
                "severity": a.severity,
                "message": a.message,
                "timestamp": datetime.fromtimestamp(a.timestamp, tz=timezone.utc).isoformat(),
            }
            for a in sorted(recent, key=lambda x: x.timestamp, reverse=True)
        ]

    # ── Internal Helpers ──────────────────────────────────────────

    def _log_validation(self, result: ValidationResult):
        """Log a validation result."""
        with self._lock:
            self._validation_log.append(result)
            if len(self._validation_log) > self._max_validation_log:
                self._validation_log = self._validation_log[-self._max_validation_log:]

        if not result.is_valid:
            logger.warning(f"Validation failed: {result.error_message}")


# ── Singleton ─────────────────────────────────────────────────────────

_quality_service: Optional[DataQualityService] = None


def get_quality_service() -> DataQualityService:
    global _quality_service
    if _quality_service is None:
        _quality_service = DataQualityService()
    return _quality_service
