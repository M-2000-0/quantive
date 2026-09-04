"""Data Quality API — Monitor market data health and integrity.

Endpoints:
- GET /api/data-quality/health — Overall quality health score
- GET /api/data-quality/sources — Per-source health status
- GET /api/data-quality/freshness — Data freshness status
- GET /api/data-quality/anomalies — Recent anomalies
- GET /api/data-quality/metrics — Detailed quality metrics
"""

from fastapi import APIRouter, Depends, Query

from app.market_data.quality import get_quality_service
from app.models import User
from app.security import get_current_user

router = APIRouter(prefix="/api/data-quality", tags=["data-quality"])


@router.get("/health")
def get_quality_health(user: User = Depends(get_current_user)):
    """Get overall data quality health score."""
    service = get_quality_service()
    metrics = service.get_quality_metrics()
    return {
        "status": "healthy" if metrics["overall_health_score"] >= 80 else "degraded",
        "health_score": metrics["overall_health_score"],
        "completeness": metrics["completeness"],
        "sources_healthy": metrics["sources"]["healthy"],
        "sources_total": metrics["sources"]["total"],
        "last_updated": metrics["last_updated"],
    }


@router.get("/sources")
def get_source_health(user: User = Depends(get_current_user)):
    """Get health status for all data sources."""
    service = get_quality_service()
    return service.get_source_health()


@router.get("/sources/{source_name}")
def get_source_detail(source_name: str, user: User = Depends(get_current_user)):
    """Get detailed health for a specific source."""
    service = get_quality_service()
    return service.get_source_health(source_name)


@router.get("/freshness")
def get_freshness(user: User = Depends(get_current_user)):
    """Get freshness status for all data types."""
    service = get_quality_service()
    return service.get_freshness()


@router.get("/anomalies")
def get_anomalies(
    hours: int = Query(24, ge=1, le=168, description="Lookback hours"),
    severity: str = Query(None, description="Filter by severity: low, medium, high, critical"),
    user: User = Depends(get_current_user),
):
    """Get recent data anomalies."""
    service = get_quality_service()
    return {
        "anomalies": service.get_anomalies(hours=hours, severity=severity),
        "period_hours": hours,
    }


@router.get("/metrics")
def get_quality_metrics(user: User = Depends(get_current_user)):
    """Get detailed quality metrics for monitoring."""
    service = get_quality_service()
    return service.get_quality_metrics()
