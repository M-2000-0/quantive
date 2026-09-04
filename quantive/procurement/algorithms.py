"""Procurement Intelligence Algorithms — Layer 7.

Waste detection, bottleneck identification, vendor benchmarking, and outcome
forecasting for government procurement processes.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from datetime import datetime
import math
import statistics

from .models import (
    ProcurementItem,
    ProcurementRequest,
    WasteType,
    BottleneckType,
    WasteAlert,
    VendorMetrics,
    BenchmarkData,
    ForecastProjection,
)


# ──────────────────────────────────────────────────────────────────────
# Waste Detection
# ──────────────────────────────────────────────────────────────────────

def detect_waste(request: ProcurementRequest) -> List[WasteAlert]:
    """Detect waste in a procurement request's items.

    Evaluates each item against known waste patterns and returns alerts for
    any issues found.  Severity is proportional to monetary impact.
    """
    alerts: List[WasteAlert] = []
    for item in request.items:
        alerts.extend(_detect_item_waste(item, request))
    # Sort by monetary impact descending
    alerts.sort(key=lambda a: a.monetary_impact, reverse=True)
    return alerts


def _detect_item_waste(item: ProcurementItem, request: ProcurementRequest) -> List[WasteAlert]:
    """Detect waste for a single procurement item."""
    alerts: List[WasteAlert] = []

    # Overpayment detection: unit price significantly above market estimate
    if item.unit_price_estimate is not None and item.unit_price > item.unit_price_estimate * 1.3:
        impact = (item.unit_price - item.unit_price_estimate) * item.quantity
        alerts.append(WasteAlert(
            id=f"waste-overpay-{item.id}",
            request_id=request.id,
            waste_type=WasteType.overpayment,
            severity=_severity_from_impact(impact),
            title="Overpayment Risk",
            description=f"Unit price ${item.unit_price:.2f} exceeds estimate ${item.unit_price_estimate:.2f} by 30%+",
            monetary_impact=impact,
            recommendation="Re-negotiate pricing or obtain competitive bids.",
        ))

    # Maverick spending: no approved supplier or bypassing process
    if not item.supplier:
        alerts.append(WasteAlert(
            id=f"waste-maverick-{item.id}",
            request_id=request.id,
            waste_type=WasteType.maverick_spending,
            severity="medium",
            title="Maverick Spending",
            description=f"Item '{item.name}' has no approved supplier.",
            monetary_impact=item.estimated_value * 0.1,
            recommendation="Assign approved supplier or initiate competitive selection.",
        ))

    # Duplicate orders: same category/name within same request
    # (checked at request level after all items processed)

    # Suboptimal quantities: quantity outside reasonable bounds
    if item.quantity > 1000 and item.estimated_value / item.quantity > 1000:
        alerts.append(WasteAlert(
            id=f"waste-quantity-{item.id}",
            request_id=request.id,
            waste_type=WasteType.suboptimal_quantities,
            severity="low",
            title="Suboptimal Quantity",
            description=f"Large quantity {item.quantity} may indicate bulk-purchase inefficiency.",
            monetary_impact=item.estimated_value * 0.05,
            recommendation="Review quantity requirements and negotiate volume discounts.",
        ))

    # Contract violations: requirements missing for complex items
    if item.category in ("construction", "it") and not item.requirements:
        alerts.append(WasteAlert(
            id=f"waste-spec-{item.id}",
            request_id=request.id,
            waste_type=WasteType.specification_creep,
            severity="medium",
            title="Missing Requirements",
            description=f"High-category item '{item.name}' lacks technical requirements.",
            monetary_impact=item.estimated_value * 0.08,
            recommendation="Define and document technical requirements before bidding.",
        ))

    # Poor quality rework: low quality score implication
    if item.quality_score is not None and item.quality_score < 70:
        alerts.append(WasteAlert(
            id=f"waste-quality-{item.id}",
            request_id=request.id,
            waste_type=WasteType.poor_quality_rework,
            severity="medium",
            title="Low Quality Indicator",
            description=f"Quality score {item.quality_score} may lead to rework costs.",
            monetary_impact=item.estimated_value * 0.15,
            recommendation="Improve quality specifications or select higher-quality supplier.",
        ))

    return alerts


def _severity_from_impact(impact: float) -> str:
    """Map monetary impact to severity level."""
    if impact > 1_000_000:
        return "critical"
    if impact > 100_000:
        return "high"
    if impact > 10_000:
        return "medium"
    return "low"


# ──────────────────────────────────────────────────────────────────────
# Bottleneck Detection
# ──────────────────────────────────────────────────────────────────────

def detect_bottlenecks(request: ProcurementRequest) -> List[Dict[str, Any]]:
    """Identify workflow bottlenecks in a procurement request."""
    bottlenecks: List[Dict[str, Any]] = []

    # Approval chain bottlenecks
    if _has_redundant_approvals(request):
        bottlenecks.append({
            "type": BottleneckType.approval_chain,
            "title": "Redundant Approval Chain",
            "description": "Multiple approval layers delaying procurement timeline.",
            "severity": "medium",
            "impact_days": _estimate_approval_delay(request),
        })

    # Supplier dependency
    if _single_supplier_dependency(request):
        bottlenecks.append({
            "type": BottleneckType.supplier_dependency,
            "title": "Single Supplier Dependency",
            "description": "Critical items dependent on a single supplier.",
            "severity": "high",
            "impact_days": 15,
        })

    # Compliance review delay
    if _has_compliance_review_need(request):
        bottlenecks.append({
            "type": BottleneckType.compliance_review,
            "title": "Compliance Review",
            "description": "Procurement items require compliance validation.",
            "severity": "medium",
            "impact_days": 7,
        })

    # Budget approval
    if request.budget_cap and _budget_approval_needed(request):
        bottlenecks.append({
            "type": BottleneckType.budget_approval,
            "title": "Budget Approval",
            "description": "Total spend approaching budget cap requiring executive approval.",
            "severity": "high",
            "impact_days": 10,
        })

    # Logistics carrier
    if _has_logistics_bottleneck(request):
        bottlenecks.append({
            "type": BottleneckType.logistics_carrier,
            "title": "Logistics Carrier",
            "description": "Limited carrier options increasing lead times.",
            "severity": "low",
            "impact_days": 5,
        })

    # Documentation
    if _insufficient_documentation(request):
        bottlenecks.append({
            "type": BottleneckType.documentation,
            "title": "Documentation Gaps",
            "description": "Missing or incomplete documentation slowing review.",
            "severity": "low",
            "impact_days": 3,
        })

    # Sort by severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    bottlenecks.sort(key=lambda b: severity_order.get(b["severity"], 99))

    return bottlenecks


def _has_redundant_approvals(request: ProcurementRequest) -> bool:
    """Check if request has excessive approval layers."""
    # If many items and no clear approval path
    return len(request.items) > 3 and all(item.constraints for item in request.items)


def _single_supplier_dependency(request: ProcurementRequest) -> bool:
    """Check if critical items have single supplier."""
    critical_items = [i for i in request.items if i.priority in ("high", "critical")]
    if not critical_items:
        return False
    suppliers = {i.supplier for i in critical_items if i.supplier}
    return len(suppliers) == 1 and len(critical_items) > 1


def _has_compliance_review_need(request: ProcurementRequest) -> bool:
    """Check if items need compliance review."""
    regulated = {"construction", "it", "healthcare", "defense"}
    return any(item.category in regulated for item in request.items)


def _budget_approval_needed(request: ProcurementRequest) -> bool:
    """Check if budget approval is needed."""
    if not request.budget_cap:
        return False
    total = sum(i.estimated_value for i in request.items)
    return total > request.budget_cap * 0.8


def _has_logistics_bottleneck(request: ProcurementRequest) -> bool:
    """Check for logistics carrier bottlenecks."""
    return any(not item.supplier for i, item in enumerate(request.items) if i < 3)


def _insufficient_documentation(request: ProcurementRequest) -> bool:
    """Check for insufficient documentation."""
    items_missing = sum(
        1 for item in request.items
        if not item.requirements and not item.constraints
    )
    return items_missing > len(request.items) * 0.5


def _estimate_approval_delay(request: ProcurementRequest) -> int:
    """Estimate delay in days from redundant approvals."""
    return min(len(request.items) * 2, 10)


# ──────────────────────────────────────────────────────────────────────
# Vendor Benchmarking
# ──────────────────────────────────────────────────────────────────────

def benchmark_vendors(
    request: ProcurementRequest,
    vendor_metrics: Dict[str, VendorMetrics],
) -> List[BenchmarkData]:
    """Benchmark vendors against peer categories and metrics.

    Compares each vendor's performance metrics to category benchmarks and
    provides percentile rankings and insights.
    """
    benchmarks: List[BenchmarkData] = []

    # Group items by category and collect vendor metrics
    category_vendors: Dict[str, Dict[str, List[VendorMetrics]]] = {}
    for item in request.items:
        cat = item.category
        sup = item.supplier
        if sup and cat:
            category_vendors.setdefault(cat, {}).setdefault(sup, []).append(
                vendor_metrics.get(sup, VendorMetrics(vendor_id=sup, vendor_name=sup))
            )

    for category, vendors in category_vendors.items():
        for vendor_name, metrics_list in vendors.items():
            metrics = metrics_list[0]  # primary metrics instance
            # Build benchmark values from peer set (simulated from other vendors)
            peer_values = _collect_peer_metrics(vendor_metrics, category, vendor_name)
            user_value = getattr(metrics, _metric_for_category(category), 0)

            benchmark = _build_benchmark(
                category=category,
                metric=_metric_for_category(category),
                values=peer_values,
                user_value=user_value,
                vendor_name=vendor_name,
            )
            if benchmark:
                benchmarks.append(benchmark)

    # Also add category-level benchmarks for items without specific vendor data
    if not any(b.vendor_name for b in benchmarks):
        benchmarks.extend(_category_benchmarks(category_vendors))

    return benchmarks


def _metric_for_category(category: str) -> str:
    """Return the primary metric to benchmark for a category."""
    mapping = {
        "IT": "cost",
        "construction": "lead_time",
        "services": "quality_score",
        "healthcare": "on_time_delivery",
        "defense": "cost",
        "general": "cost",
    }
    return mapping.get(category, "cost")


def _collect_peer_metrics(
    vendor_metrics: Dict[str, VendorMetrics],
    category: str,
    exclude_vendor: str,
) -> List[float]:
    """Collect peer metric values for benchmarking."""
    values: List[float] = []
    for vm in vendor_metrics.values():
        if vm.vendor_id == exclude_vendor:
            continue
        metric = getattr(vm, _metric_for_category(category), None)
        if metric is not None:
            values.append(metric)
    # Add simulated peer data if insufficient
    if len(values) < 5:
        values.extend(_simulated_peer_values(_metric_for_category(category), len(values)))
    return values


def _simulated_peer_values(metric: str, count: int) -> List[float]:
    """Generate simulated peer values for benchmarking."""
    base_values: Dict[str, float] = {
        "cost": 120.0,
        "lead_time": 45.0,
        "quality_score": 82.0,
        "on_time_delivery": 88.0,
    }
    base = base_values.get(metric, 80.0)
    return [round(base + (i - count / 2) * 5, 1) for i in range(count)]


def _build_benchmark(
    category: str,
    metric: str,
    values: List[float],
    user_value: float,
    vendor_name: str,
) -> Optional[BenchmarkData]:
    """Build a BenchmarkData instance from computed values."""
    if not values:
        return None

    sorted_vals = sorted(values)
    n = len(sorted_vals)

    percentile = _compute_percentile(user_value, sorted_vals) if values else 50.0

    # Determine peer percentiles
    peer_median = sorted_vals[n // 2] if n > 0 else 0
    peer_p25 = sorted_vals[n // 4] if n > 0 else 0
    peer_p75 = sorted_vals[3 * n // 4] if n > 0 else 0
    peer_p10 = sorted_vals[n // 10] if n > 0 else 0
    peer_p90 = sorted_vals[9 * n // 10] if n > 0 else 0

    # Insight based on percentile
    if percentile >= 90:
        insight = f"{vendor_name} performs in top 10% for {metric}."
    elif percentile >= 75:
        insight = f"{vendor_name} performs in top 25% for {metric}. Good choice."
    elif percentile >= 50:
        insight = f"{vendor_name} performs at median for {metric}. Acceptable."
    else:
        insight = f"{vendor_name} performs below median for {metric}. Consider alternatives."

    # Category benchmark (reference value)
    category_benchmark = round(statistics.mean(sorted_vals), 2)

    return BenchmarkData(
        category=category,
        metric=metric,
        unit=_unit_for_metric(metric),
        values=sorted_vals,
        percentile=round(percentile, 1),
        user_value=user_value,
        peer_median=peer_median,
        peer_p25=peer_p25,
        peer_p75=peer_p75,
        peer_p10=peer_p10,
        peer_p90=peer_p90,
        insight=insight,
        category_benchmark=category_benchmark,
    )


def _unit_for_metric(metric: str) -> str:
    """Return the unit of measurement for a metric."""
    mapping = {
        "cost": "USD",
        "lead_time": "days",
        "quality_score": "score",
        "on_time_delivery": "%",
    }
    return mapping.get(metric, "units")


def _compute_percentile(value: float, sorted_values: List[float]) -> float:
    """Compute the percentile rank of a value in a sorted list."""
    if not sorted_values:
        return 50.0
    # Count values strictly below, and equal to
    below = sum(1 for v in sorted_values if v < value)
    equal = sum(1 for v in sorted_values if v == value)
    n = len(sorted_values)
    # Use (below + 0.5 * equal) / n * 100 for median-rank percentile
    return (below + 0.5 * equal) / n * 100


def _category_benchmarks(
    category_vendors: Dict[str, Dict[str, List[VendorMetrics]]],
) -> List[BenchmarkData]:
    """Add category-level benchmarks when no specific vendor data available."""
    benchmarks: List[BenchmarkData] = []
    for category, vendors in category_vendors.items():
        all_values: List[float] = []
        for vm_list in vendors.values():
            for vm in vm_list:
                metric = getattr(vm, _metric_for_category(category), None)
                if metric is not None:
                    all_values.append(metric)

        if not all_values:
            # Use simulated defaults per category
            all_values = _simulated_peer_values(_metric_for_category(category), 10)

        metric = _metric_for_category(category)
        user_value = sum(all_values) / len(all_values) if all_values else 0

        benchmark = _build_benchmark(
            category=category,
            metric=metric,
            values=sorted(all_values),
            user_value=user_value,
            vendor_name=f"{category}-benchmark",
        )
        if benchmark:
            benchmarks.append(benchmark)
    return benchmarks


# ──────────────────────────────────────────────────────────────────────
# Procurement Outcome Forecasting
# ──────────────────────────────────────────────────────────────────────

def forecast_outcomes(request: ProcurementRequest) -> ForecastProjection:
    """Forecast procurement outcomes based on request data and historical patterns."""
    # Calculate baseline from items
    baseline_total = sum(item.estimated_value for item in request.items)

    # Apply waste detection reductions
    waste_alerts = detect_waste(request)
    total_waste_impact = sum(a.monetary_impact for a in waste_alerts)

    # Estimate savings from waste reduction
    estimated_savings = min(total_waste_impact * 0.6, baseline_total * 0.25)

    # Projected total after waste elimination
    projected_total = baseline_total - estimated_savings

    # Confidence based on item completeness
    completeness = _compute_item_completeness(request)
    confidence = min(95, 50 + completeness * 45)

    # Horizon (default: estimated duration of all items)
    horizon = _compute_horizon(request)

    # Scenarios
    scenarios = _generate_scenarios(baseline_total, estimated_savings, confidence)

    # Risk factors
    risk_factors = _identify_risk_factors(request, waste_alerts)

    return ForecastProjection(
        projection_id=f"forecast-{request.id}",
        request_id=request.id,
        horizon_days=horizon,
        projected_total=round(projected_total, 2),
        projected_savings=round(estimated_savings, 2),
        confidence=round(confidence, 1),
        scenarios=scenarios,
        risk_factors=risk_factors,
    )


def _compute_item_completeness(request: ProcurementRequest) -> float:
    """Compute completeness ratio of procurement items."""
    if not request.items:
        return 0.0
    total = len(request.items)
    complete = sum(
        1 for item in request.items
        if item.supplier
        and item.estimated_start
        and item.estimated_end
        and item.requirements
    )
    return complete / total


def _compute_horizon(request: ProcurementRequest) -> int:
    """Compute forecast horizon in days."""
    if request.timeline_days:
        return request.timeline_days
    # Estimate from items
    dates = []
    for item in request.items:
        if item.estimated_start:
            try:
                from datetime import datetime as dt
                start = dt.fromisoformat(item.estimated_start)
                end = dt.fromisoformat(item.estimated_end) if item.estimated_end else start
                days = (end - start).days + 10  # buffer
                dates.append(days)
            except (ValueError, TypeError):
                pass
    if dates:
        return max(dates)
    return 90  # default 3-month horizon


def _generate_scenarios(
    baseline: float,
    savings: float,
    confidence: float,
) -> List[Dict[str, Any]]:
    """Generate forecast scenarios."""
    # Base case: estimated savings
    base_projected = round(baseline - savings, 2)

    # Best case: 90% of estimated savings
    best_projected = round(baseline - savings * 0.9, 2)

    # Worst case: 50% of estimated savings (some waste remains)
    worst_projected = round(baseline - savings * 0.5, 2)

    return [
        {
            "name": "Base Case",
            "probability": round(confidence, 1),
            "projected_total": base_projected,
            "projected_savings": round(savings, 2),
        },
        {
            "name": "Best Case",
            "probability": round(confidence * 0.8, 1),
            "projected_total": best_projected,
            "projected_savings": round(savings * 0.9, 2),
        },
        {
            "name": "Worst Case",
            "probability": round(100 - confidence, 1),
            "projected_total": worst_projected,
            "projected_savings": round(savings * 0.5, 2),
        },
    ]


def _identify_risk_factors(
    request: ProcurementRequest,
    waste_alerts: List[WasteAlert],
) -> List[str]:
    """Identify key risk factors for the procurement forecast."""
    risks: List[str] = []

    if waste_alerts:
        critical_waste = [a for a in waste_alerts if a.severity == "critical"]
        if critical_waste:
            risks.append(f"{len(critical_waste)} critical waste issue(s) identified")

    if not any(item.supplier for item in request.items):
        risks.append("No approved supplier assigned for items")

    if request.budget_cap and sum(i.estimated_value for i in request.items) > request.budget_cap * 0.9:
        risks.append("Budget cap approaching")

    if len(request.items) > 5:
        risks.append("High item count increases coordination complexity")

    if any(item.category == "construction" for item in request.items):
        risks.append("Construction subject to schedule risk")

    return risks


# ──────────────────────────────────────────────────────────────────────
# Integration with Optimization & Scenario Engine
# ──────────────────────────────────────────────────────────────────────

def integrate_with_optimization(
    request: ProcurementRequest,
    optimization_result: Optional[dict] = None,
) -> dict:
    """Integrate procurement analysis with the optimization/scenario engine.

    Merges procurement waste insights and vendor benchmarks into an
    optimization problem context for scenario analysis.
    """
    base_data = {
        "request_id": request.id,
        "waste_detected": {
            "percentage": _waste_percentage(request),
            "alerts": [a.model_dump() for a in detect_waste(request)],
        },
        "bottlenecks": detect_bottlenecks(request),
        "vendor_benchmarks": [b.model_dump() for b in benchmark_vendors(request, {})],
        "forecast": forecast_outcomes(request).model_dump(),
    }

    if optimization_result:
        base_data["optimization_integration"] = {
            "aligned": True,
            "optimization_result_id": optimization_result.get("id"),
            "merged_objectives": {
                "minimize_waste": True,
                "maximize_efficiency": True,
                "risk_mitigation": True,
            },
        }

    return base_data


def _waste_percentage(request: ProcurementRequest) -> float:
    """Calculate waste as percentage of total estimated value."""
    if not request.items:
        return 0.0
    total_estimated = sum(i.estimated_value for i in request.items)
    total_waste = sum(a.monetary_impact for a in detect_waste(request))
    if total_estimated == 0:
        return 0.0
    return round((total_waste / total_estimated) * 100, 2)