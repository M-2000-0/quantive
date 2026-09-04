"""
Fiscal Rule Compliance Engine
==============================
Monitors debt service-to-revenue ceilings, debt-to-budget limits,
consolidated national+subnational rollup views.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class FiscalRule:
    """A fiscal rule / borrowing limit."""
    rule_id: str
    name: str
    entity_type: str  # "national", "subnational", "consolidated"
    metric: str       # "debt_to_revenue", "debt_service_to_revenue", "debt_to_gdp", "deficit_to_gdp"
    limit_value: float
    limit_direction: str  # "below" or "above" (e.g., debt_to_gdp must be below 60%)
    warning_threshold: float = 0.9  # Alert at 90% of limit
    source: str = ""  # Legal reference
    active: bool = True


@dataclass
class ComplianceCheck:
    """Result of checking a fiscal rule."""
    rule_id: str
    rule_name: str
    entity_id: str
    entity_name: str
    current_value: float
    limit_value: float
    utilization_pct: float
    status: str  # "compliant", "warning", "breach"
    gap_to_limit: float
    message: str


@dataclass
class ConsolidatedView:
    """National + subnational consolidated debt view."""
    national_debt: float
    subnational_debt: float
    guaranteed_debt: float  # Nationally guaranteed subnational
    total_consolidated: float
    entities: list[dict]


class FiscalRuleEngine:
    """
    Monitors compliance with fiscal rules for sovereign and subnational debt.
    """

    # Common fiscal rules (IMF Fiscal Rules Database)
    STANDARD_RULES = [
        FiscalRule("IMF_DEBT_GDP", "Debt-to-GDP Ceiling", "national", "debt_to_gdp", 60.0, "below",
                   source="IMF fiscal rule, EU Maastricht criteria"),
        FiscalRule("IMF_DEFICIT_GDP", "Deficit-to-GDP Ceiling", "national", "deficit_to_gdp", 3.0, "below",
                   source="IMF fiscal rule, EU Maastricht criteria"),
        FiscalRule("IMF_DSR_REVENUE", "Debt Service-to-Revenue", "subnational", "debt_service_to_revenue", 25.0, "below",
                   source="Common subnational borrowing limit"),
        FiscalRule("IMF_DEBT_BUDGET", "Debt-to-Budget Ceiling", "subnational", "debt_to_budget", 50.0, "below",
                   source="Typical subnational limit"),
    ]

    def __init__(self, rules: list[FiscalRule] = None):
        self.rules = rules or self.STANDARD_RULES

    def check_compliance(
        self,
        entity_id: str,
        entity_name: str,
        entity_type: str,
        metrics: dict,
    ) -> list[ComplianceCheck]:
        """Check all applicable rules for an entity."""
        checks = []
        for rule in self.rules:
            if not rule.active:
                continue
            if rule.entity_type != entity_type and rule.entity_type != "consolidated":
                continue

            value = metrics.get(rule.metric)
            if value is None:
                continue

            # Calculate utilization
            utilization = (value / rule.limit_value * 100) if rule.limit_value > 0 else 0

            # Determine status
            if rule.limit_direction == "below":
                compliant = value <= rule.limit_value
                warning = value > rule.limit_value * rule.warning_threshold
                gap = rule.limit_value - value
            else:
                compliant = value >= rule.limit_value
                warning = value < rule.limit_value * rule.warning_threshold
                gap = value - rule.limit_value

            if not compliant:
                status = "breach"
            elif warning:
                status = "warning"
            else:
                status = "compliant"

            checks.append(ComplianceCheck(
                rule_id=rule.rule_id,
                rule_name=rule.name,
                entity_id=entity_id,
                entity_name=entity_name,
                current_value=round(value, 2),
                limit_value=rule.limit_value,
                utilization_pct=round(utilization, 1),
                status=status,
                gap_to_limit=round(gap, 2),
                message=self._message(rule, value, status),
            ))

        return checks

    def _message(self, rule: FiscalRule, value: float, status: str) -> str:
        if status == "breach":
            return f"BREACH: {rule.name} at {value:.1f} (limit: {rule.limit_value})"
        elif status == "warning":
            return f"WARNING: {rule.name} approaching limit at {value:.1f}"
        return f"Compliant: {rule.name} at {value:.1f}"

    def consolidated_view(
        self,
        national_debt: float,
        subnational_entities: list[dict],
    ) -> ConsolidatedView:
        """
        Build consolidated national + subnational view.
        Flags nationally guaranteed subnational debt as distinct risk.
        """
        sub_total = sum(e.get("debt", 0) for e in subnational_entities)
        guaranteed = sum(e.get("guaranteed", 0) for e in subnational_entities)

        return ConsolidatedView(
            national_debt=national_debt,
            subnational_debt=sub_total,
            guaranteed_debt=guaranteed,
            total_consolidated=national_debt + sub_total,
            entities=[
                {
                    "name": e.get("name", ""),
                    "debt": e.get("debt", 0),
                    "guaranteed": e.get("guaranteed", 0),
                    "is_guaranteed": e.get("guaranteed", 0) > 0,
                }
                for e in subnational_entities
            ],
        )
