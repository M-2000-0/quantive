"""Statutory Constraints Engine.

Ensures optimization recommendations never violate:
- Constitutional debt ceilings
- Balanced-budget mandates
- Legal limits on debt instruments
- International treaty obligations
- Central bank mandate boundaries
- Fiscal rule compliance (Maastricht, etc.)

This is critical because a mathematically optimal recommendation
that violates statutory law is not just useless — it's dangerous.
A minister who follows illegal advice faces personal liability.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, Float, Boolean
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.database import Base


class StatutoryRule(Base):
    """A statutory constraint that must be enforced."""
    __tablename__ = "statutory_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)  # debt_ceiling, fiscal_rule, instrument_limit
    jurisdiction = Column(String(10), nullable=False)  # ISO country code
    constraint_type = Column(String(20), nullable=False)  # hard, soft
    parameter = Column(String(100), nullable=False)  # e.g., "debt_to_gdp_ratio"
    operator = Column(String(10), nullable=False)  # <=, >=, ==, !=
    threshold_value = Column(Float, nullable=False)
    unit = Column(String(50), nullable=True)  # percent, currency, ratio
    effective_date = Column(DateTime(timezone=True), nullable=True)
    expiry_date = Column(DateTime(timezone=True), nullable=True)
    enabled = Column(Boolean, default=True)
    source = Column(Text, nullable=True)  # Legal reference


class ConstraintViolation(Base):
    """Records when a recommendation would violate a constraint."""
    __tablename__ = "constraint_violations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), default=func.now())
    rule_id = Column(String(50), nullable=False)
    recommendation_value = Column(Float, nullable=False)
    threshold_value = Column(Float, nullable=False)
    severity = Column(String(20), nullable=False)  # critical, high, medium
    blocked = Column(Boolean, default=True)
    recommendation_id = Column(String(36), nullable=True)


@dataclass
class ConstraintCheck:
    rule_id: str
    name: str
    passed: bool
    current_value: float
    threshold: float
    operator: str
    severity: str
    margin: float  # How close to the limit


class StatutoryConstraintsEngine:
    """Enforces legal and regulatory constraints on optimization.

    Design principle: Hard constraints are NEVER violated.
    The optimizer will reject any solution that breaks statutory law,
    even if the mathematical solution is superior.

    Soft constraints are warned but can be overridden with documented
    justification and approval.
    """

    # Pre-loaded common fiscal rules
    DEFAULT_RULES = [
        {
            "rule_id": "EU_DEBT_CEILING",
            "name": "Maastricht Debt Ceiling",
            "description": "EU member states must maintain gross government debt below 60% of GDP",
            "category": "fiscal_rule",
            "jurisdiction": "EU",
            "constraint_type": "hard",
            "parameter": "debt_to_gdp_ratio",
            "operator": "<=",
            "threshold_value": 60.0,
            "unit": "percent",
            "source": "Treaty on the Functioning of the European Union, Article 126",
        },
        {
            "rule_id": "EU_DEFICIT_CEILING",
            "name": "Maastricht Deficit Ceiling",
            "description": "EU member states must maintain budget deficit below 3% of GDP",
            "category": "fiscal_rule",
            "jurisdiction": "EU",
            "constraint_type": "hard",
            "parameter": "budget_deficit_to_gdp",
            "operator": "<=",
            "threshold_value": 3.0,
            "unit": "percent",
            "source": "Treaty on the Functioning of the European Union, Article 126",
        },
        {
            "rule_id": "US_DEBT_CEILING",
            "name": "US Debt Ceiling",
            "description": "US federal debt subject to statutory limit set by Congress",
            "category": "debt_ceiling",
            "jurisdiction": "US",
            "constraint_type": "hard",
            "parameter": "total_federal_debt",
            "operator": "<=",
            "threshold_value": 0,  # Must be dynamically set by Congress
            "unit": "currency",
            "source": "31 U.S.C. § 3101",
        },
        {
            "rule_id": "REVERSE_GAP_RULE",
            "name": "Excessive Deficit Procedure",
            "description": "Countries must demonstrate debt reduction toward 60% target",
            "category": "fiscal_rule",
            "jurisdiction": "EU",
            "constraint_type": "soft",
            "parameter": "debt_reduction_rate",
            "operator": ">=",
            "threshold_value": 1.0 / 20.0,  # 1/20th of excess per year
            "unit": "ratio",
            "source": "Stability and Growth Pact",
        },
        {
            "rule_id": "BANKING_LICENSE_LIMIT",
            "name": "Sovereign Exposure Limit",
            "description": "Banks cannot hold excessive sovereign debt concentration",
            "category": "instrument_limit",
            "jurisdiction": "GLOBAL",
            "constraint_type": "soft",
            "parameter": "single_issuer_concentration",
            "operator": "<=",
            "threshold_value": 25.0,
            "unit": "percent",
            "source": "Basel III / CRD IV",
        },
    ]

    def __init__(self, db: Session):
        self.db = db

    def load_default_rules(self, jurisdiction: str = "EU"):
        """Load default statutory rules for a jurisdiction."""
        for rule_data in self.DEFAULT_RULES:
            if rule_data["jurisdiction"] in (jurisdiction, "GLOBAL"):
                existing = self.db.query(StatutoryRule).filter(
                    StatutoryRule.rule_id == rule_data["rule_id"]
                ).first()
                if not existing:
                    rule = StatutoryRule(**rule_data)
                    self.db.add(rule)
        self.db.commit()

    def check_recommendation(
        self,
        recommendation: dict,
        jurisdiction: str = "EU",
    ) -> list[ConstraintCheck]:
        """Check if a recommendation violates any statutory constraints."""
        rules = self.db.query(StatutoryRule).filter(
            StatutoryRule.jurisdiction.in_([jurisdiction, "GLOBAL"]),
            StatutoryRule.enabled == True,
        ).all()

        checks = []
        for rule in rules:
            value = recommendation.get(rule.parameter)
            if value is None:
                continue

            passed = self._evaluate(value, rule.operator, rule.threshold_value)
            margin = abs(value - rule.threshold_value) / max(abs(rule.threshold_value), 0.01) * 100

            checks.append(ConstraintCheck(
                rule_id=rule.rule_id,
                name=rule.name,
                passed=passed,
                current_value=value,
                threshold=rule.threshold_value,
                operator=rule.operator,
                severity=rule.constraint_type,
                margin=round(margin, 1),
            ))

            # Record violations
            if not passed:
                violation = ConstraintViolation(
                    rule_id=rule.rule_id,
                    recommendation_value=value,
                    threshold_value=rule.threshold_value,
                    severity="critical" if rule.constraint_type == "hard" else "high",
                    blocked=rule.constraint_type == "hard",
                )
                self.db.add(violation)

        self.db.commit()
        return checks

    def get_constraints_report(self, jurisdiction: str = "EU") -> dict:
        """Generate constraints status report."""
        rules = self.db.query(StatutoryRule).filter(
            StatutoryRule.jurisdiction.in_([jurisdiction, "GLOBAL"]),
        ).all()

        violations = self.db.query(ConstraintViolation).filter(
            ConstraintViolation.blocked == True,
        ).count()

        return {
            "jurisdiction": jurisdiction,
            "total_rules": len(rules),
            "hard_constraints": sum(1 for r in rules if r.constraint_type == "hard"),
            "soft_constraints": sum(1 for r in rules if r.constraint_type == "soft"),
            "active_violations": violations,
            "compliance_score": 100 if violations == 0 else max(0, 100 - (violations * 10)),
        }

    def _evaluate(self, value: float, operator: str, threshold: float) -> bool:
        ops = {"<=": value <= threshold, ">=": value >= threshold, "==": value == threshold, "!=": value != threshold}
        return ops.get(operator, True)
