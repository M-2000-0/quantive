"""SLA Monitoring and Documentation.

Tracks service level agreements, monitors uptime, and manages
SLA breach penalties for government contracts.

This addresses the "No SLA Documentation" issue from the
Government Procurement Stress Test.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any


class SLAStatus(str, Enum):
    """Status of SLA monitoring."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


class IncidentSeverity(str, Enum):
    """Incident severity levels."""
    CRITICAL = "critical"  # Service down
    HIGH = "high"         # Major feature broken
    MEDIUM = "medium"     # Minor feature broken
    LOW = "low"           # Cosmetic/enhancement


@dataclass
class SLATarget:
    """A specific SLA target."""
    metric_name: str
    target_value: float
    unit: str
    measurement_period: str  # "monthly", "quarterly", "annual"


@dataclass
class SLABreach:
    """Record of an SLA breach."""
    breach_id: str
    incident_id: str
    severity: IncidentSeverity
    metric_name: str
    expected_value: float
    actual_value: float
    breach_duration_minutes: int
    detected_at: datetime
    resolved_at: datetime | None
    root_cause: str = ""
    remediation: str = ""


@dataclass
class ServiceCredit:
    """Service credit for SLA breach."""
    credit_id: str
    breach_id: str
    credit_percentage: float
    credit_amount_usd: float
    period: str
    status: str  # pending, applied, disputed


class SLAMonitor:
    """Monitors and tracks SLA compliance."""

    def __init__(self):
        self._targets: dict[str, SLATarget] = {}
        self._breaches: list[SLABreach] = []
        self._credits: list[ServiceCredit] = []
        self._uptime_records: list[dict] = []
        self._setup_default_targets()

    def _setup_default_targets(self):
        """Set up default SLA targets for government contracts."""
        self._targets = {
            "uptime": SLATarget(
                metric_name="Monthly Uptime",
                target_value=99.95,
                unit="percent",
                measurement_period="monthly",
            ),
            "api_response_p50": SLATarget(
                metric_name="API Response Time (P50)",
                target_value=200,
                unit="ms",
                measurement_period="monthly",
            ),
            "api_response_p95": SLATarget(
                metric_name="API Response Time (P95)",
                target_value=500,
                unit="ms",
                measurement_period="monthly",
            ),
            "api_response_p99": SLATarget(
                metric_name="API Response Time (P99)",
                target_value=1000,
                unit="ms",
                measurement_period="monthly",
            ),
            "rto": SLATarget(
                metric_name="Recovery Time Objective",
                target_value=4,
                unit="hours",
                measurement_period="incident",
            ),
            "rpo": SLATarget(
                metric_name="Recovery Point Objective",
                target_value=15,
                unit="minutes",
                measurement_period="incident",
            ),
            "incident_response_critical": SLATarget(
                metric_name="Critical Incident Response",
                target_value=15,
                unit="minutes",
                measurement_period="incident",
            ),
            "incident_response_high": SLATarget(
                metric_name="High Incident Response",
                target_value=60,
                unit="minutes",
                measurement_period="incident",
            ),
        }

    def record_uptime(
        self,
        timestamp: datetime,
        uptime_percent: float,
        response_time_p50: float = 0,
        response_time_p95: float = 0,
        response_time_p99: float = 0,
    ):
        """Record uptime metrics for a time period."""
        self._uptime_records.append({
            "timestamp": timestamp.isoformat(),
            "uptime_percent": uptime_percent,
            "response_time_p50": response_time_p50,
            "response_time_p95": response_time_p95,
            "response_time_p99": response_time_p99,
        })

    def check_sla_compliance(self) -> dict:
        """Check current SLA compliance status."""
        if not self._uptime_records:
            return {"status": "no_data", "message": "No uptime records available"}

        latest = self._uptime_records[-1]
        compliance = {}

        # Check uptime
        uptime_target = self._targets["uptime"]
        compliance["uptime"] = {
            "metric": uptime_target.metric_name,
            "target": uptime_target.target_value,
            "actual": latest["uptime_percent"],
            "compliant": latest["uptime_percent"] >= uptime_target.target_value,
            "breach": latest["uptime_percent"] < uptime_target.target_value,
        }

        # Check response times
        if latest["response_time_p50"] > 0:
            p50_target = self._targets["api_response_p50"]
            compliance["api_response_p50"] = {
                "metric": p50_target.metric_name,
                "target": p50_target.target_value,
                "actual": latest["response_time_p50"],
                "compliant": latest["response_time_p50"] <= p50_target.target_value,
            }

        if latest["response_time_p95"] > 0:
            p95_target = self._targets["api_response_p95"]
            compliance["api_response_p95"] = {
                "metric": p95_target.metric_name,
                "target": p95_target.target_value,
                "actual": latest["response_time_p95"],
                "compliant": latest["response_time_p95"] <= p95_target.target_value,
            }

        # Overall status
        all_compliant = all(c.get("compliant", True) for c in compliance.values())

        return {
            "status": "compliant" if all_compliant else "breach",
            "details": compliance,
            "last_check": latest["timestamp"],
        }

    def report_incident(
        self,
        incident_id: str,
        severity: IncidentSeverity,
        metric_name: str,
        expected_value: float,
        actual_value: float,
        breach_duration_minutes: int,
        root_cause: str = "",
    ) -> SLABreach:
        """Report an SLA incident."""
        breach = SLABreach(
            breach_id=f"breach-{incident_id}",
            incident_id=incident_id,
            severity=severity,
            metric_name=metric_name,
            expected_value=expected_value,
            actual_value=actual_value,
            breach_duration_minutes=breach_duration_minutes,
            detected_at=datetime.now(timezone.utc),
            resolved_at=None,
            root_cause=root_cause,
        )

        self._breaches.append(breach)

        # Calculate service credit
        credit = self._calculate_credit(breach)
        if credit:
            self._credits.append(credit)

        return breach

    def resolve_incident(
        self,
        breach_id: str,
        remediation: str,
    ) -> SLABreach | None:
        """Mark an incident as resolved."""
        for breach in self._breaches:
            if breach.breach_id == breach_id:
                breach.resolved_at = datetime.now(timezone.utc)
                breach.remediation = remediation
                return breach
        return None

    def _calculate_credit(self, breach: SLABreach) -> ServiceCredit | None:
        """Calculate service credit for a breach."""
        # Credit tiers based on uptime
        credit_tiers = [
            (99.90, 99.94, 10),
            (99.50, 99.89, 25),
            (99.00, 99.49, 50),
            (0, 98.99, 100),
        ]

        # Determine credit percentage based on severity
        credit_pct = 0
        if breach.severity == IncidentSeverity.CRITICAL:
            credit_pct = 50
        elif breach.severity == IncidentSeverity.HIGH:
            credit_pct = 25
        elif breach.severity == IncidentSeverity.MEDIUM:
            credit_pct = 10

        if credit_pct > 0:
            return ServiceCredit(
                credit_id=f"credit-{breach.breach_id}",
                breach_id=breach.breach_id,
                credit_percentage=credit_pct,
                credit_amount_usd=0,  # Calculated from contract value
                period=datetime.now(timezone.utc).strftime("%Y-%m"),
                status="pending",
            )
        return None

    def get_breach_history(
        self,
        days: int = 30,
    ) -> list[dict]:
        """Get breach history for the last N days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        recent_breaches = [
            b for b in self._breaches
            if b.detected_at >= cutoff
        ]

        return [
            {
                "breach_id": b.breach_id,
                "incident_id": b.incident_id,
                "severity": b.severity.value,
                "metric_name": b.metric_name,
                "expected_value": b.expected_value,
                "actual_value": b.actual_value,
                "breach_duration_minutes": b.breach_duration_minutes,
                "detected_at": b.detected_at.isoformat(),
                "resolved_at": b.resolved_at.isoformat() if b.resolved_at else None,
                "root_cause": b.root_cause,
                "remediation": b.remediation,
            }
            for b in recent_breaches
        ]

    def get_credits_summary(self) -> dict:
        """Get summary of service credits."""
        total_credits = len(self._credits)
        pending = sum(1 for c in self._credits if c.status == "pending")
        applied = sum(1 for c in self._credits if c.status == "applied")

        return {
            "total_credits": total_credits,
            "pending": pending,
            "applied": applied,
            "credits": [
                {
                    "credit_id": c.credit_id,
                    "breach_id": c.breach_id,
                    "credit_percentage": c.credit_percentage,
                    "period": c.period,
                    "status": c.status,
                }
                for c in self._credits
            ],
        }

    def get_sla_documentation(self) -> dict:
        """Get SLA documentation."""
        return {
            "uptime_commitment": {
                "monthly_uptime": ">= 99.95%",
                "planned_maintenance": "<= 4 hours/month (Sunday 02:00-06:00 UTC)",
                "unplanned_downtime": "<= 22 minutes/month",
                "rto": "<= 4 hours",
                "rpo": "<= 15 minutes",
            },
            "performance_targets": {
                "api_response_p50": "<= 200ms",
                "api_response_p95": "<= 500ms",
                "api_response_p99": "<= 1000ms",
                "concurrent_users": ">= 100",
            },
            "incident_response": {
                "critical": "15 minutes response, updates every 30 minutes, resolution in 4 hours",
                "high": "1 hour response, updates every 2 hours, resolution in 8 hours",
                "medium": "4 hours response, daily updates, resolution in 48 hours",
                "low": "24 hours response, weekly updates, next release",
            },
            "breach_penalties": {
                "99.95-99.99": "0% (meeting target)",
                "99.90-99.94": "10% monthly credit",
                "99.50-99.89": "25% monthly credit",
                "99.00-99.49": "50% monthly credit",
                "below 99.00": "100% monthly credit + termination right",
            },
            "exclusions": [
                "Scheduled maintenance windows (communicated 48h in advance)",
                "Force majeure events (natural disasters, war, government action)",
                "Customer-caused outages (misconfiguration, unauthorized changes)",
                "Third-party service failures (upstream data providers)",
            ],
        }


# Global instance
_sla_monitor: SLAMonitor | None = None


def get_sla_monitor() -> SLAMonitor:
    """Get the global SLA monitor."""
    global _sla_monitor
    if _sla_monitor is None:
        _sla_monitor = SLAMonitor()
    return _sla_monitor
