"""SLA Monitoring API endpoints.

Exposes SLA compliance, incident tracking, and breach penalties.
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.models import User
from app.security import get_current_user

router = APIRouter(prefix="/api/sla", tags=["sla"])


class UptimeRecordRequest(BaseModel):
    uptime_percent: float = Field(..., ge=0, le=100)
    response_time_p50: float = Field(default=0, ge=0)
    response_time_p95: float = Field(default=0, ge=0)
    response_time_p99: float = Field(default=0, ge=0)


class IncidentRequest(BaseModel):
    incident_id: str = Field(..., min_length=3)
    severity: str = Field(..., description="critical, high, medium, low")
    metric_name: str = Field(..., description="Metric that was breached")
    expected_value: float = Field(..., description="Expected SLA value")
    actual_value: float = Field(..., description="Actual value achieved")
    breach_duration_minutes: int = Field(..., ge=0)
    root_cause: str = Field(default="", max_length=2000)


class IncidentResolutionRequest(BaseModel):
    remediation: str = Field(..., min_length=10, max_length=2000)


@router.get("/compliance")
def check_sla_compliance(user: User = Depends(get_current_user)):
    """Check current SLA compliance status."""
    from quantive.government.sla_monitor import get_sla_monitor

    monitor = get_sla_monitor()
    return monitor.check_sla_compliance()


@router.post("/uptime")
def record_uptime(
    request: UptimeRecordRequest,
    user: User = Depends(get_current_user),
):
    """Record uptime metrics."""
    from datetime import datetime, timezone
    from quantive.government.sla_monitor import get_sla_monitor

    monitor = get_sla_monitor()
    monitor.record_uptime(
        timestamp=datetime.now(timezone.utc),
        uptime_percent=request.uptime_percent,
        response_time_p50=request.response_time_p50,
        response_time_p95=request.response_time_p95,
        response_time_p99=request.response_time_p99,
    )

    return {"message": "Uptime recorded successfully"}


@router.post("/incident")
def report_incident(
    request: IncidentRequest,
    user: User = Depends(get_current_user),
):
    """Report an SLA incident."""
    from quantive.government.sla_monitor import IncidentSeverity, get_sla_monitor

    monitor = get_sla_monitor()

    severity_map = {
        "critical": IncidentSeverity.CRITICAL,
        "high": IncidentSeverity.HIGH,
        "medium": IncidentSeverity.MEDIUM,
        "low": IncidentSeverity.LOW,
    }
    severity = severity_map.get(request.severity, IncidentSeverity.MEDIUM)

    breach = monitor.report_incident(
        incident_id=request.incident_id,
        severity=severity,
        metric_name=request.metric_name,
        expected_value=request.expected_value,
        actual_value=request.actual_value,
        breach_duration_minutes=request.breach_duration_minutes,
        root_cause=request.root_cause,
    )

    return {
        "breach_id": breach.breach_id,
        "incident_id": breach.incident_id,
        "severity": breach.severity.value,
        "detected_at": breach.detected_at.isoformat(),
        "message": "Incident reported and SLA breach recorded",
    }


@router.post("/incident/{breach_id}/resolve")
def resolve_incident(
    breach_id: str,
    request: IncidentResolutionRequest,
    user: User = Depends(get_current_user),
):
    """Resolve an SLA incident."""
    from quantive.government.sla_monitor import get_sla_monitor

    monitor = get_sla_monitor()
    breach = monitor.resolve_incident(breach_id, request.remediation)

    if not breach:
        return {"error": "Breach not found"}, 404

    return {
        "breach_id": breach.breach_id,
        "resolved_at": breach.resolved_at.isoformat() if breach.resolved_at else None,
        "remediation": breach.remediation,
        "message": "Incident resolved",
    }


@router.get("/breaches")
def get_breach_history(
    days: int = Query(30, ge=1, le=365),
    user: User = Depends(get_current_user),
):
    """Get breach history."""
    from quantive.government.sla_monitor import get_sla_monitor

    monitor = get_sla_monitor()
    breaches = monitor.get_breach_history(days=days)

    return {"breaches": breaches, "total": len(breaches), "period_days": days}


@router.get("/credits")
def get_credits_summary(user: User = Depends(get_current_user)):
    """Get service credits summary."""
    from quantive.government.sla_monitor import get_sla_monitor

    monitor = get_sla_monitor()
    return monitor.get_credits_summary()


@router.get("/documentation")
def get_sla_documentation(user: User = Depends(get_current_user)):
    """Get SLA documentation."""
    from quantive.government.sla_monitor import get_sla_monitor

    monitor = get_sla_monitor()
    return monitor.get_sla_documentation()
