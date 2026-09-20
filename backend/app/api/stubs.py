"""Stub routes for frontend endpoints that don't have real backends yet.

Returns realistic mock data so pages load without 404 errors.
"""
import secrets
from datetime import datetime, timezone
from fastapi import APIRouter

router = APIRouter()

_NOW = datetime.now(timezone.utc).isoformat()


def _ok(data):
    return data


# ── Risk Summaries (frontend calls /risk/*, backend has no /risk router) ──

@router.get("/api/risk/cyber/summary")
def risk_cyber_summary(entity_id: str = "default"):
    return _ok({"overall": 78, "by_category": {"network": 82, "endpoint": 71, "cloud": 85, "identity": 74}, "category_counts": {"network": 12, "endpoint": 8, "cloud": 6, "identity": 4}})

@router.get("/api/risk/fiscal/summary")
def risk_fiscal_summary(entity_id: str = "default"):
    return _ok({"overall": 65, "by_category": {"debt": 60, "revenue": 70, "expenditure": 62, "deficit": 68}, "category_counts": {"debt": 5, "revenue": 8, "expenditure": 7, "deficit": 3}})

@router.get("/api/risk/climate/summary")
def risk_climate_summary(entity_id: str = "default"):
    return _ok({"overall": 55, "by_category": {"physical": 50, "transition": 62, "liability": 48}, "category_counts": {"physical": 4, "transition": 6, "liability": 3}})

@router.get("/api/risk/infrastructure/summary")
def risk_infrastructure_summary(entity_id: str = "default"):
    return _ok({"overall": 72, "by_category": {"transport": 68, "energy": 75, "digital": 80, "water": 65}, "category_counts": {"transport": 10, "energy": 8, "digital": 6, "water": 5}})

@router.get("/api/risk/geopolitical/summary")
def risk_geopolitical_summary(entity_id: str = "default"):
    return _ok({"overall": 60, "by_category": {"sanctions": 55, "trade": 65, "conflict": 45, "governance": 75}, "category_counts": {"sanctions": 3, "trade": 5, "conflict": 2, "governance": 7}})

@router.get("/api/risk/supply-chain/summary")
def risk_supply_chain_summary(entity_id: str = "default"):
    return _ok({"overall": 68, "by_category": {"logistics": 70, "suppliers": 65, "materials": 72, "labor": 64}, "category_counts": {"logistics": 8, "suppliers": 12, "materials": 6, "labor": 4}})

@router.get("/api/risk/aggregate/{entity_id}")
def risk_aggregate(entity_id: str, entity_type: str = "government"):
    return _ok({"overall_score": 67, "by_category": {"cyber": 78, "fiscal": 65, "climate": 55, "infrastructure": 72, "geopolitical": 60, "supply_chain": 68}, "category_counts": {"cyber": 30, "fiscal": 23, "climate": 13, "infrastructure": 29, "geopolitical": 17, "supply_chain": 30}})

@router.get("/api/risk/early-warning/{entity_id}")
def risk_early_warning(entity_id: str):
    return _ok({"signals": [
        {"id": secrets.token_hex(8), "name": "High Debt-to-GDP", "category": "fiscal", "indicator": "debt_to_gdp", "currentValue": 112.5, "threshold": 100, "unit": "%", "direction": "above", "status": "critical", "trend": "rising", "description": "Debt-to-GDP ratio exceeds 100% threshold", "lastUpdated": _NOW},
        {"id": secrets.token_hex(8), "name": "FX Volatility Spike", "category": "geopolitical", "indicator": "fx_volatility", "currentValue": 18.3, "threshold": 15, "unit": "%", "direction": "above", "status": "warning", "trend": "rising", "description": "Currency volatility above normal range", "lastUpdated": _NOW},
    ], "total_signals": 2, "critical_signals": 1})


# ── Procurement Intelligence (no backend exists) ──────────────────────────

@router.get("/api/procurement")
def procurement_list():
    return _ok({"data": [], "meta": {"total": 0}})

@router.post("/api/procurement")
def procurement_create():
    return _ok({"id": secrets.token_hex(8), "name": "Sample Request", "status": "draft", "created_at": _NOW})

@router.get("/api/procurement/{request_id}")
def procurement_get(request_id: str):
    return _ok({"id": request_id, "name": "Sample Request", "status": "active", "value": 50000, "items": []})

@router.get("/api/procurement/{request_id}/waste")
def procurement_waste(request_id: str):
    return _ok({"waste_items": [], "total_waste": 0, "waste_pct": 0})

@router.get("/api/procurement/{request_id}/waste/summary")
def procurement_waste_summary(request_id: str):
    return _ok({"total_waste": 0, "waste_pct": 0, "by_type": {}, "recommendations": []})

@router.get("/api/procurement/{request_id}/bottlenecks")
def procurement_bottlenecks(request_id: str):
    return _ok({"bottlenecks": [], "total_bottlenecks": 0})

@router.get("/api/procurement/{request_id}/bottlenecks/summary")
def procurement_bottlenecks_summary(request_id: str):
    return _ok({"total_bottlenecks": 0, "avg_delay_days": 0, "by_stage": {}})

@router.get("/api/procurement/{request_id}/benchmarks")
def procurement_benchmarks(request_id: str):
    return _ok({"vendors": [], "rankings": []})

@router.get("/api/procurement/{request_id}/benchmarks/summary")
def procurement_benchmarks_summary(request_id: str):
    return _ok({"total_vendors": 0, "avg_score": 0, "best_vendor": "", "price_range": {"min": 0, "max": 0, "avg": 0}})

@router.get("/api/procurement/{request_id}/forecast")
def procurement_forecast(request_id: str):
    return _ok({"scenarios": [], "expected_savings": 0, "risk_score": 0})

@router.get("/api/procurement/{request_id}/forecast/summary")
def procurement_forecast_summary(request_id: str):
    return _ok({"expected_savings": 0, "risk_score": 0, "confidence": 0, "scenarios_count": 0})

@router.get("/api/procurement/{request_id}/integrate")
def procurement_integrate(request_id: str):
    return _ok({"status": "ready", "problem_id": None})

@router.get("/api/procurement/health/check")
def procurement_health():
    return _ok({"status": "healthy", "modules": ["waste", "bottlenecks", "benchmarks", "forecast"]})


# ── Sovereign Mode enable/disable ────────────────────────────────────────

@router.post("/api/sovereign-mode/enable")
def sovereign_mode_enable():
    return _ok({"enabled": True, "activated_at": _NOW, "security_level": "maximum"})

@router.post("/api/sovereign-mode/disable")
def sovereign_mode_disable():
    return _ok({"enabled": False, "deactivated_at": _NOW})


# ── Pricing missing routes ───────────────────────────────────────────────

@router.post("/api/pricing/customize")
def pricing_customize():
    return _ok({"tier": "enterprise", "monthly_price": 2499, "features": ["unlimited"]})

@router.get("/api/pricing/optimizations")
def pricing_optimizations():
    return _ok([])


# ── Interoperability format path fixes ───────────────────────────────────

@router.post("/api/interoperability/parse/fpml")
def interoperability_parse_fpml():
    return _ok({"trades": [], "validation": {"valid": True, "errors": []}})

@router.post("/api/interoperability/parse/xbrl")
def interoperability_parse_xbrl():
    return _ok({"facts": [], "validation": {"valid": True, "errors": []}})

@router.get("/api/interoperability/supported-formats")
def interoperability_supported_formats():
    return _ok([{"id": "fpml", "name": "FpML", "extension": ".xml", "mime_type": "application/xml"},
                {"id": "xbrl", "name": "XBRL", "extension": ".xbrl", "mime_type": "application/xml"}])
