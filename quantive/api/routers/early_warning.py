"""Early Warning API endpoints for Layer 5 (Sovereign Early Warning System).

Provides REST endpoints for:
- Triggering early warning detection runs
- Retrieving current warning signals
- Scenario projections and analysis
- Bias tracking integration with assumption registry
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from quantive.early_warning.engine import EarlyWarningEngine, INDICATOR_REGISTRY
from quantive.early_warning.models import (
    EarlyWarningRequest,
    EarlyWarningResult,
    WarningDetail,
)
from quantive.api.schemas import EarlyWarningSignalResponse


router = APIRouter(prefix="/early-warning", tags=["early-warning"])


# Engine instance
_engine = EarlyWarningEngine()


@router.get("/signals/{entity_id}")
def get_early_warning_signals(
    entity_id: str,
    horizon_months: int = Query(
        12, ge=1, le=60, description="Analysis horizon in months"
    ),
    include_scenarios: bool = Query(
        True, description="Include scenario projections"
    ),
) -> dict:
    """Get early warning signals for a government entity.

    Queries the assumption registry for current indicator values and bias
    directions, then runs detection to produce warning signals.

    Args:
        entity_id: Government/entity identifier
        horizon_months: Analysis horizon in months (1-60)
        include_scenarios: Whether to include scenario projections

    Returns:
        Dict with warnings, summary, and average lead time
    """
    # In production, fetch from DB
    # For now, run detection with mock data
    engine = EarlyWarningEngine()

    # Mock indicator values - in production would come from DB
    indicator_values = {
        "debt_to_gdp": 62.5,
        "debt_service": 21.3,
        "external_financing_needs": 16.2,
        "liquidity_coverage": 14.8,
        "foreign_reserve_coverage": 1.4,
        "cds_spread": 295.0,
        "external_debt_ratio": 38.0,
        "primary_balance": -2.1,
        "tax_revenue_volatility": 0.14,
        "revenue_volatility": 0.08,
        "tax_base_contraction": -2.5,
        "pension_funding_ratio": 78.5,
        "pension_demographic_ratio": 0.28,
    }

    assumptions = {
        "debt_to_gdp": {"bias_direction": "deteriorating"},
        "debt_service": {"bias_direction": "stable"},
        "cds_spread": {"bias_direction": "deteriorating"},
        "pension_funding_ratio": {"bias_direction": "deteriorating"},
        "primary_balance": {"bias_direction": "improving"},
    }

    request = EarlyWarningRequest(
        entity_id=entity_id,
        include_scenarios=include_scenarios,
        horizon_months=horizon_months,
    )

    result = engine.detect(
        entity_id=entity_id,
        indicator_values=indicator_values,
        assumptions=assumptions,
        request=request,
    )

    # Convert to dict for JSON response
    signals = []
    for warning in result.warnings:
        signals.append(
            {
                "id": warning.id,
                "name": warning.name,
                "category": warning.category,
                "indicator": warning.indicator,
                "currentValue": warning.current_value,
                "threshold": warning.threshold,
                "unit": warning.unit,
                "direction": warning.direction,
                "status": warning.status,
                "trend": warning.trend,
                "description": warning.description,
                "lastUpdated": warning.last_updated.isoformat(),
                "monthsUntilCrisis": warning.months_until_crisis,
                "biasAdjustment": warning.bias_adjustment,
            }
        )

    return {
        "entity_id": entity_id,
        "signals": signals,
        "summary": result.summary,
        "total_months_lead": result.total_months_lead,
        "run_timestamp": result.run_timestamp.isoformat(),
    }


@router.post("/detect/{entity_id}")
def trigger_detection(
    entity_id: str,
    request: EarlyWarningRequest,
) -> EarlyWarningResult:
    """Trigger an early warning detection run for an entity.

    This endpoint accepts a full EarlyWarningRequest and returns the
    complete detection result including all warnings, summaries, and
    scenario projections.

    Args:
        entity_id: Government/entity identifier
        request: EarlyWarningRequest with configuration

    Returns:
        EarlyWarningResult with all detected warnings
    """
    # Mock indicator values and assumptions
    indicator_values = {
        "debt_to_gdp": 62.5,
        "debt_service": 21.3,
        "external_financing_needs": 16.2,
        "liquidity_coverage": 14.8,
        "foreign_reserve_coverage": 1.4,
        "cds_spread": 295.0,
        "external_debt_ratio": 38.0,
        "primary_balance": -2.1,
        "tax_revenue_volatility": 0.14,
        "revenue_volatility": 0.08,
        "tax_base_contraction": -2.5,
        "pension_funding_ratio": 78.5,
        "pension_demographic_ratio": 0.28,
    }

    assumptions = {
        "debt_to_gdp": {"bias_direction": "deteriorating"},
        "debt_service": {"bias_direction": "stable"},
        "cds_spread": {"bias_direction": "deteriorating"},
        "pension_funding_ratio": {"bias_direction": "deteriorating"},
        "primary_balance": {"bias_direction": "improving"},
    }

    engine = EarlyWarningEngine()

    result = engine.detect(
        entity_id=entity_id,
        indicator_values=indicator_values,
        assumptions=assumptions,
        request=request,
    )

    return result


@router.get("/indicators")
def list_indicators() -> dict:
    """List all available early warning indicators with configurations.

    Returns:
        Dict mapping indicator names to their configs (thresholds, units, lookahead, etc.)
    """
    indicator_info: Dict[str, dict] = {}
    for name, config in INDICATOR_REGISTRY.items():
        indicator_info[name] = {
            "name": config.name,
            "description": config.description,
            "threshold": config.threshold,
            "critical_threshold": config.critical_threshold,
            "direction": config.direction,
            "unit": config.unit,
            "lookahead_months": config.lookahead_months,
            "bias_adjustment": config.bias_adjustment,
        }
    return {
        "indicators": indicator_info,
        "total": len(indicator_info),
        "risk_categories": {
            "debt_crisis": ["debt_to_gdp", "debt_service", "external_financing_needs"],
            "liquidity": ["liquidity_coverage", "foreign_reserve_coverage"],
            "rating": ["cds_spread", "external_debt_ratio"],
            "fiscal_instability": ["primary_balance", "tax_revenue_volatility"],
            "revenue_collapse": ["revenue_volatility", "tax_base_contraction"],
            "pension_stress": ["pension_funding_ratio", "pension_demographic_ratio"],
        },
    }


@router.get("/categories")
def risk_categories() -> dict:
    """Get risk category information for the early warning system.

    Returns:
        Dict mapping risk categories to their indicator lists and descriptions
    """
    return {
        "categories": {
            "debt_crisis": {
                "description": "Indicators of sovereign debt unsustainability and potential default",
                "indicators": [
                    {"name": "debt_to_gdp", "threshold": 60.0},
                    {"name": "debt_service", "threshold": 25.0},
                    {"name": "external_financing_needs", "threshold": 15.0},
                ],
            },
            "liquidity": {
                "description": "Indicators of liquidity stress and funding risks",
                "indicators": [
                    {"name": "liquidity_coverage", "threshold": 15.0},
                    {"name": "foreign_reserve_coverage", "threshold": 1.5},
                ],
            },
            "rating": {
                "description": "Indicators of rating downgrade risk",
                "indicators": [
                    {"name": "cds_spread", "threshold": 250.0},
                    {"name": "external_debt_ratio", "threshold": 40.0},
                ],
            },
            "fiscal_instability": {
                "description": "Indicators of structural fiscal instability",
                "indicators": [
                    {"name": "primary_balance", "threshold": -3.0},
                    {"name": "tax_revenue_volatility", "threshold": 0.15},
                ],
            },
            "revenue_collapse": {
                "description": "Indicators of revenue collapse risk",
                "indicators": [
                    {"name": "revenue_volatility", "threshold": 0.10},
                    {"name": "tax_base_contraction", "threshold": -5.0},
                ],
            },
            "pension_stress": {
                "description": "Indicators of pension system stress",
                "indicators": [
                    {"name": "pension_funding_ratio", "threshold": 80.0},
                    {"name": "pension_demographic_ratio", "threshold": 0.25},
                ],
            },
        }
    }


@router.post("/scenarios/project")
def project_scenarios(
    entity_id: str,
    indicator_name: str = Query(..., description="Indicator to project"),
    current_value: float = Query(..., description="Current indicator value"),
    months_ahead: int = Query(12, ge=1, le=60, description="Projection horizon"),
    bias_direction: str = Query(
        "stable", description="Bias direction: improving|deteriorating|stable"
    ),
) -> dict:
    """Project scenarios for a specific early warning indicator.

    Creates baseline, optimistic, and pessimistic scenarios based on current
    value, bias direction, and indicator configuration.

    Args:
        entity_id: Government/entity identifier
        indicator_name: Name of the indicator to project
        current_value: Current value of the indicator
        months_ahead: Number of months to project
        bias_direction: Bias direction from assumption registry

    Returns:
        Scenario projections for baseline, optimistic, and pessimistic cases
    """
    from quantive.early_warning.indicators import (
        DEBT_TO_GDP_CONFIG,
        DEBT_SERVICE_CONFIG,
        LIQUIDITY_COVERAGE_RATIO_CONFIG,
        CDS_SPREAD_CONFIG,
        PRIMARY_BALANCE_CONFIG,
        TAX_REVENUE_Volatility_CONFIG,
        REVENUE_VOLATILITY_CONFIG,
        TAX_BASE_CONTRACTION_CONFIG,
        PENSION_FUNDING_RATIO_CONFIG,
        PENSION_DEMOGRAPHIC_RATIO_CONFIG,
    )

    config_map: Dict[str, object] = {
        "debt_to_gdp": DEBT_TO_GDP_CONFIG,
        "debt_service": DEBT_SERVICE_CONFIG,
        "liquidity_coverage": LIQUIDITY_COVERAGE_RATIO_CONFIG,
        "cds_spread": CDS_SPREAD_CONFIG,
        "primary_balance": PRIMARY_BALANCE_CONFIG,
        "tax_revenue_volatility": TAX_REVENUE_Volatility_CONFIG,
        "revenue_volatility": REVENUE_VOLATILITY_CONFIG,
        "tax_base_contraction": TAX_BASE_CONTRACTION_CONFIG,
        "pension_funding_ratio": PENSION_FUNDING_RATIO_CONFIG,
        "pension_demographic_ratio": PENSION_DEMOGRAPHIC_RATIO_CONFIG,
    }

    config = config_map.get(indicator_name)
    if config is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown indicator: {indicator_name}. "
            f"Available: {list(config_map.keys())}",
        )

    from quantive.early_warning.scenario_analysis import (
        default_scenario_analyzer,
    )

    analyzer = default_scenario_analyzer
    scenarios = analyzer.project_scenarios(
        current_value=current_value,
        indicator_config=config,
        months_ahead=months_ahead,
        bias_direction=bias_direction,
    )

    result: Dict[str, dict] = {}
    for scenario in scenarios:
        result[scenario.scenario_name] = {
            "current_value": scenario.current_value,
            "projected_values": scenario.projected_values,
            "confidence": scenario.confidence,
        }

    return {
        "entity_id": entity_id,
        "indicator_name": indicator_name,
        "months_ahead": months_ahead,
        "bias_direction": bias_direction,
        "scenarios": result,
    }