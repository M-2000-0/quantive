"""Procurement API endpoints (Layer 7 — Procurement Intelligence)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from quantive.procurement.algorithms import (
    detect_waste,
    detect_bottlenecks,
    benchmark_vendors,
    forecast_outcomes,
    integrate_with_optimization,
)
from quantive.procurement.models import (
    ProcurementRequest,
    ProcurementResponse,
    WasteAlert,
    VendorMetrics,
    BenchmarkData,
    ForecastProjection,
    WasteType,
    BottleneckType,
)
from quantive.api.state import state
from quantive.models.instruments import Portfolio
from quantive.models.optimization import (
    OptimizationProblem,
    ScenarioConfiguration,
    SolverConfiguration,
)

router = APIRouter(prefix="/procurement", tags=["procurement"])


# ── Helper: get or create a procurement request from state ──────────────

def _get_request(request_id: str) -> ProcurementRequest:
    """Retrieve a procurement request from state, or raise 404."""
    request = state.procurement_requests.get(request_id)
    if request is None:
        raise HTTPException(status_code=404, detail=f"procurement request {request_id!r} not found")
    return request


def _save_request(request: ProcurementRequest) -> None:
    """Save a procurement request to state."""
    state.procurement_requests[request.id] = request


# ── Waste Detection Endpoints ────────────────────────────────────────

@router.post("/{request_id}/waste", response_model=List[WasteAlert], status_code=200)
def detect_waste_endpoint(
    request_id: str,
) -> List[WasteAlert]:
    """Detect waste in a procurement request.

    Evaluates all items for known waste patterns (overpayment, maverick spending,
    duplicate orders, contract violations, inefficient lead times, poor quality
    rework, suboptimal quantities, redundant approvals, specification creep,
    unused contracts).

    Returns:
        List of WasteAlert objects sorted by monetary impact (highest first).
    """
    request = _get_request(request_id)
    return detect_waste(request)


@router.get("/{request_id}/waste/summary")
def waste_summary(request_id: str) -> dict:
    """Get waste detection summary for a procurement request."""
    request = _get_request(request_id)
    alerts = detect_waste(request)
    total_impact = sum(a.monetary_impact for a in alerts)
    total_estimated = sum(i.estimated_value for i in request.items)

    by_type: Dict[str, int] = {}
    for alert in alerts:
        wtype = alert.waste_type
        by_type[wtype] = by_type.get(wtype, 0) + 1

    return {
        "request_id": request_id,
        "total_alerts": len(alerts),
        "total_monetary_impact": round(total_impact, 2),
        "total_estimated_value": round(total_estimated, 2),
        "waste_percentage": round((total_impact / total_estimated * 100) if total_estimated else 0, 2),
        "by_type": {k: v for k, v in by_type.items()},
        "severity_breakdown": {
            "critical": sum(1 for a in alerts if a.severity == "critical"),
            "high": sum(1 for a in alerts if a.severity == "high"),
            "medium": sum(1 for a in alerts if a.severity == "medium"),
            "low": sum(1 for a in alerts if a.severity == "low"),
        },
    }


# ── Bottleneck Detection Endpoints ──────────────────────────────────

@router.post("/{request_id}/bottlenecks", response_model=List[Dict[str, Any]], status_code=200)
def detect_bottlenecks_endpoint(request_id: str) -> List[Dict[str, Any]]:
    """Identify workflow bottlenecks in a procurement request.

    Analyzes approval chains, supplier dependency, compliance reviews,
    budget approval, logistics, and documentation gaps.

    Returns:
        List of bottleneck dictionaries sorted by severity.
    """
    request = _get_request(request_id)
    return detect_bottlenecks(request)


@router.get("/{request_id}/bottlenecks/summary")
def bottlenecks_summary(request_id: str) -> dict:
    """Get bottleneck summary for a procurement request."""
    request = _get_request(request_id)
    bottlenecks = detect_bottlenecks(request)
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}

    by_type: Dict[str, int] = {}
    for b in bottlenecks:
        btype = b["type"]
        by_type[btype] = by_type.get(btype, 0) + 1

    return {
        "request_id": request_id,
        "total_bottlenecks": len(bottlenecks),
        "by_severity": {
            "high_or_critical": len([b for b in bottlenecks if severity_order.get(b["severity"], 99) < 2]),
            "medium": len([b for b in bottlenecks if severity_order.get(b["severity"], 99) == 2]),
            "low": len([b for b in bottlenecks if severity_order.get(b["severity"], 99) > 2]),
        },
        "by_type": {str(k.value if hasattr(k, 'value') else k): v for k, v in by_type.items()},
        "estimated_delay_days": sum(b.get("impact_days", 0) for b in bottlenecks),
    }


# ── Vendor Benchmarking Endpoints ───────────────────────────────────

@router.post("/{request_id}/benchmarks", response_model=List[BenchmarkData], status_code=200)
def benchmark_vendors_endpoint(
    request_id: str,
    vendor_metrics: Optional[List[VendorMetrics]] = None,
) -> List[BenchmarkData]:
    """Benchmark vendors against peer categories and metrics.

    Compares vendor performance metrics to category benchmarks and provides
    percentile rankings and interpretive insights.

    If vendor_metrics are provided, they are used as the peer set; otherwise
    simulated peer data is generated.

    Returns:
        List of BenchmarkData objects with percentile rankings and insights.
    """
    request = _get_request(request_id)

    # Convert provided metrics to dict
    metrics_dict: Dict[str, VendorMetrics] = {}
    if vendor_metrics:
        for vm in vendor_metrics:
            metrics_dict[vm.vendor_id] = vm

    results = benchmark_vendors(request, metrics_dict)
    return results


@router.get("/{request_id}/benchmarks/summary")
def benchmarks_summary(request_id: str) -> dict:
    """Get vendor benchmark summary for a procurement request."""
    request = _get_request(request_id)
    benchmarks = benchmark_vendors(request, {})

    by_category: Dict[str, List[dict]] = {}
    for b in benchmarks:
        cat = b.category
        by_category.setdefault(cat, []).append({
            "metric": b.metric,
            "user_value": b.user_value,
            "peer_median": b.peer_median,
            "percentile": b.percentile,
            "insight": b.insight,
        })

    return {
        "request_id": request_id,
        "total_benchmarks": len(benchmarks),
        "by_category": by_category,
    }


# ── Outcome Forecasting Endpoints ───────────────────────────────────

@router.post("/{request_id}/forecast", response_model=ForecastProjection, status_code=200)
def forecast_outcomes_endpoint(request_id: str) -> ForecastProjection:
    """Forecast procurement outcomes based on request data.

    Generates cost projections, savings estimates, confidence scores,
    and scenario outcomes for the procurement horizon.

    Returns:
        ForecastProjection with projected totals, confidence, and scenarios.
    """
    request = _get_request(request_id)
    return forecast_outcomes(request)


@router.get("/{request_id}/forecast/summary")
def forecast_summary(request_id: str) -> dict:
    """Get forecast summary for a procurement request."""
    request = _get_request(request_id)
    forecast = forecast_outcomes(request)

    # Build scenario summary
    scenario_summaries = []
    for scenario in forecast.scenarios:
        scenario_summaries.append({
            "name": scenario.get("name", "Unknown"),
            "probability": scenario.get("probability", 0),
            "projected_total": scenario.get("projected_total", 0),
            "projected_savings": scenario.get("projected_savings", 0),
        })

    return {
        "request_id": request_id,
        "horizon_days": forecast.horizon_days,
        "projected_total": forecast.projected_total,
        "projected_savings": forecast.projected_savings,
        "confidence": forecast.confidence,
        "scenarios": scenario_summaries,
        "risk_factors": forecast.risk_factors,
    }


# ── Integration Endpoint ────────────────────────────────────────────

@router.post("/{request_id}/integrate", status_code=202)
def integrate_endpoint(
    request_id: str,
    problem_id: Optional[str] = Query(None, description="Optimization problem to integrate with"),
) -> dict:
    """Integrate procurement analysis with the optimization/scenario engine.

    Merges procurement waste insights, vendor benchmarks, and outcome forecasts
    into an optimization problem context for scenario analysis and decision
    support.

    Args:
        request_id: The procurement request ID
        problem_id: Optional optimization problem ID to integrate with

    Returns:
        Integration status and merged data.
    """
    request = _get_request(request_id)

    # Get or create optimization problem
    problem = None
    if problem_id:
        from quantive.api.routers.optimization import _problem_payload
        try:
            problem = _problem_payload(problem_id)
        except HTTPException:
            problem = None

    integration = integrate_with_optimization(request, problem._data if problem else None)

    # Save integration result
    integration_id = f"procurement-integration-{request_id}-{uuid.uuid4().hex[:8]}"
    state.procurement_integrations[integration_id] = {
        "request_id": request_id,
        "integration_id": integration_id,
        "waste_detected": integration.get("waste_detected"),
        "bottlenecks": integration.get("bottlenecks"),
        "vendor_benchmarks": integration.get("vendor_benchmarks"),
        "forecast": integration.get("forecast"),
        "integrated_at": datetime.utcnow().isoformat(),
    }

    return {
        "integration_id": integration_id,
        "request_id": request_id,
        "status": "integrated",
        "waste_detected_percentage": integration.get("waste_detected", {}).get("waste_percentage", 0),
        "bottlenecks_count": len(integration.get("bottlenecks", [])),
        "benchmarks_count": len(integration.get("vendor_benchmarks", [])),
        "forecast_confidence": integration.get("forecast", {}).get("confidence", 0),
    }


# ── List/Create Procurement Requests ────────────────────────────────

@router.post("", status_code=201, response_model=ProcurementResponse)
def create_request(request: ProcurementRequest) -> ProcurementResponse:
    """Create a new procurement request.

    Initializes a procurement request with items and metadata.
    Waste detection, bottleneck analysis, and forecasting are available
    via dedicated endpoints.
    """
    _save_request(request)
    return ProcurementResponse(
        request_id=request.id,
        analysis_id=f"analysis-{request.id}",
        items_evaluated=len(request.items),
        waste_detected=0.0,
        bottlenecks=[],
        vendor_benchmarks=[],
        forecast=None,
        recommendations=[],
        status="pending",
        completed_at=datetime.utcnow().isoformat(),
    )


@router.get("", response_model=List[ProcurementRequest])
def list_requests() -> List[ProcurementRequest]:
    """List all procurement requests stored in state."""
    return list(state.procurement_requests.values())


@router.get("/{request_id}")
def get_request(request_id: str) -> ProcurementRequest:
    """Retrieve a procurement request by ID."""
    return _get_request(request_id)


# ── Health/Status ────────────────────────────────────────────────────

@router.get("/health/check")
def procurement_health() -> dict:
    """Health check for procurement intelligence layer."""
    return {
        "layer": "procurement-intelligence",
        "status": "operational",
        "requests_stored": len(state.procurement_requests),
        "integrations": len(state.procurement_integrations),
    }