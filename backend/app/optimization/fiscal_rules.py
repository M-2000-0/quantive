"""Fiscal rule compliance engine.

Evaluates government entities against their fiscal rules and returns
severity-rated compliance reports with headroom analysis.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger("quantive.fiscal_rules")


@dataclass
class RuleInput:
    """Raw data about an entity needed to evaluate fiscal rules."""
    entity_id: str
    entity_name: str
    entity_type: str

    # Debt metrics
    total_debt: float = 0.0
    gdp: float = 0.0
    annual_revenue: float = 0.0
    annual_debt_service: float = 0.0
    current_balance: float = 0.0
    deficit: float = 0.0

    # Maturity profile: {year: amount maturing}
    maturity_profile: dict[str, float] = field(default_factory=dict)

    # Currency breakdown
    local_currency_debt: float = 0.0
    foreign_currency_debt: float = 0.0

    # Contingent liabilities (for total public sector view)
    contingent_liabilities: float = 0.0


@dataclass
class RuleResult:
    rule_id: str
    rule_name: str
    rule_type: str
    current_value: float
    threshold_value: float
    threshold_unit: str
    headroom: float
    headroom_pct: float
    severity: str  # "ok", "info", "warning", "breach", "critical"
    is_hard_limit: bool
    message: str
    statute_reference: str | None = None


@dataclass
class ComplianceReport:
    entity_id: str
    entity_name: str
    evaluated_at: str
    rules: list[RuleResult]
    overall_severity: str  # worst severity across all rules
    total_rules: int
    passing: int
    warnings: int
    breaches: int


class FiscalRuleEngine:
    """Evaluates a set of fiscal rules against entity data."""

    def evaluate(self, rules: list[dict], entity_data: RuleInput) -> ComplianceReport:
        results: list[RuleResult] = []

        for rule in rules:
            try:
                result = self._evaluate_rule(rule, entity_data)
                if result:
                    results.append(result)
            except Exception as e:
                logger.warning(f"Failed to evaluate rule {rule.get('id')}: {e}")

        worst = "ok"
        severity_order = {"ok": 0, "info": 1, "warning": 2, "breach": 3, "critical": 4}
        for r in results:
            if severity_order.get(r.severity, 0) > severity_order.get(worst, 0):
                worst = r.severity

        passing = sum(1 for r in results if r.severity in ("ok", "info"))
        warnings = sum(1 for r in results if r.severity == "warning")
        breaches = sum(1 for r in results if r.severity in ("breach", "critical"))

        return ComplianceReport(
            entity_id=entity_data.entity_id,
            entity_name=entity_data.entity_name,
            evaluated_at=datetime.now(timezone.utc).isoformat(),
            rules=results,
            overall_severity=worst,
            total_rules=len(results),
            passing=passing,
            warnings=warnings,
            breaches=breaches,
        )

    def _evaluate_rule(self, rule: dict, data: RuleInput) -> RuleResult | None:
        rule_type = rule.get("rule_type", "")

        evaluators = {
            "debt_ceiling": self._eval_debt_ceiling,
            "debt_service_ratio": self._eval_debt_service_ratio,
            "deficit_limit": self._eval_deficit_limit,
            "current_balance": self._eval_current_balance,
            "maturity_concentration": self._eval_maturity_concentration,
            "fx_exposure_limit": self._eval_fx_exposure,
        }

        evaluator = evaluators.get(rule_type)
        if not evaluator:
            return None

        return evaluator(rule, data)

    def _make_result(self, rule: dict, current: float, threshold: float,
                     unit: str, data: RuleInput) -> RuleResult:
        headroom = threshold - current
        headroom_pct = (headroom / threshold * 100) if threshold != 0 else 0
        is_hard = rule.get("is_hard_limit", True)

        # Determine severity
        if headroom < 0:
            severity = "critical" if is_hard else "breach"
            msg = f"EXCEEDS limit by {abs(headroom):.2f} {unit}"
        elif headroom_pct < 5:
            severity = "breach" if is_hard else "warning"
            msg = f"Within 5% of limit — {headroom:.2f} {unit} remaining"
        elif headroom_pct < 15:
            severity = "warning"
            msg = f"Approaching limit — {headroom_pct:.1f}% headroom"
        elif headroom_pct < 30:
            severity = "info"
            msg = f"Adequate headroom — {headroom_pct:.1f}%"
        else:
            severity = "ok"
            msg = f"Well within limit — {headroom_pct:.1f}% headroom"

        return RuleResult(
            rule_id=rule.get("id", ""),
            rule_name=rule.get("name", ""),
            rule_type=rule.get("rule_type", ""),
            current_value=current,
            threshold_value=threshold,
            threshold_unit=unit,
            headroom=headroom,
            headroom_pct=headroom_pct,
            severity=severity,
            is_hard_limit=is_hard,
            message=msg,
            statute_reference=rule.get("statute_reference"),
        )

    def _eval_debt_ceiling(self, rule: dict, data: RuleInput) -> RuleResult | None:
        if data.gdp <= 0:
            return None
        current = (data.total_debt / data.gdp) * 100
        threshold = float(rule.get("threshold_value", 60))
        return self._make_result(rule, current, threshold, "% GDP", data)

    def _eval_debt_service_ratio(self, rule: dict, data: RuleInput) -> RuleResult | None:
        if data.annual_revenue <= 0:
            return None
        current = (data.annual_debt_service / data.annual_revenue) * 100
        threshold = float(rule.get("threshold_value", 20))
        return self._make_result(rule, current, threshold, "% Revenue", data)

    def _eval_deficit_limit(self, rule: dict, data: RuleInput) -> RuleResult | None:
        if data.gdp <= 0:
            return None
        current = abs(data.deficit / data.gdp) * 100
        threshold = float(rule.get("threshold_value", 3))
        return self._make_result(rule, current, threshold, "% GDP", data)

    def _eval_current_balance(self, rule: dict, data: RuleInput) -> RuleInput | None:
        if data.gdp <= 0:
            return None
        current = -(data.current_balance / data.gdp) * 100  # positive = surplus
        threshold = float(rule.get("threshold_value", -2))
        # current_balance rule: value must be ≥ threshold (e.g. ≥ -2% GDP)
        headroom = current - threshold
        headroom_pct = (headroom / abs(threshold) * 100) if threshold != 0 else 0

        if headroom < 0:
            severity = "breach"
            msg = f"Current balance deficit exceeds limit"
        elif headroom_pct < 15:
            severity = "warning"
            msg = f"Current balance approaching limit"
        else:
            severity = "ok"
            msg = f"Current balance within limit"

        return RuleResult(
            rule_id=rule.get("id", ""),
            rule_name=rule.get("name", ""),
            rule_type="current_balance",
            current_value=current,
            threshold_value=threshold,
            threshold_unit="% GDP",
            headroom=headroom,
            headroom_pct=headroom_pct,
            severity=severity,
            is_hard_limit=rule.get("is_hard_limit", True),
            message=msg,
            statute_reference=rule.get("statute_reference"),
        )

    def _eval_maturity_concentration(self, rule: dict, data: RuleInput) -> RuleResult | None:
        if not data.maturity_profile or data.total_debt <= 0:
            return None
        max_year = max(data.maturity_profile.values()) if data.maturity_profile else 0
        current = (max_year / data.total_debt) * 100
        threshold = float(rule.get("threshold_value", 15))
        return self._make_result(rule, current, threshold, "% Total", data)

    def _eval_fx_exposure(self, rule: dict, data: RuleInput) -> RuleResult | None:
        if data.total_debt <= 0:
            return None
        current = (data.foreign_currency_debt / data.total_debt) * 100
        threshold = float(rule.get("threshold_value", 30))
        return self._make_result(rule, current, threshold, "% Total", data)


# ── Consolidated View Calculator ────────────────────────────────────

@dataclass
class EntityDebtSummary:
    entity_id: str
    entity_name: str
    entity_type: str
    parent_id: str | None
    direct_debt: float
    contingent_liability_exposure: float
    contingent_liability_expected_loss: float
    guaranteed_by_national: float  # CLs guaranteed by national govt
    net_debt: float  # direct + expected CL loss
    total_public_sector_debt: float  # direct + all CLs
    transfers_received: float
    self_funded_debt_service_pct: float  # % of debt service funded locally
    instrument_count: int
    currency: str
    children: list["EntityDebtSummary"] = field(default_factory=list)


class ConsolidatedViewEngine:
    """Computes consolidated public-sector debt views with drill-down."""

    def build_entity_summary(
        self,
        entity: dict,
        instruments: list[dict],
        contingent_liabilities: list[dict],
        transfers: list[dict],
    ) -> EntityDebtSummary:
        direct_debt = sum(i.get("principal_outstanding", 0) for i in instruments)

        cl_exposure = sum(cl.get("exposure_amount", 0) for cl in contingent_liabilities)
        cl_expected_loss = sum(cl.get("expected_loss", 0) for cl in contingent_liabilities)
        guaranteed_by_national = sum(
            cl.get("exposure_amount", 0)
            for cl in contingent_liabilities
            if cl.get("is_national_guarantee")
        )

        transfers_total = sum(t.get("annual_amount", 0) for t in transfers)

        # Debt service estimate (simple: coupon * principal for each instrument)
        annual_ds = sum(
            i.get("principal_outstanding", 0) * i.get("coupon_rate", 0)
            for i in instruments
        )
        self_funded_pct = max(0, min(100,
            ((annual_ds - transfers_total) / annual_ds * 100) if annual_ds > 0 else 100
        ))

        return EntityDebtSummary(
            entity_id=entity.get("id", ""),
            entity_name=entity.get("name", ""),
            entity_type=entity.get("entity_type", ""),
            parent_id=entity.get("parent_id"),
            direct_debt=direct_debt,
            contingent_liability_exposure=cl_exposure,
            contingent_liability_expected_loss=cl_expected_loss,
            guaranteed_by_national=guaranteed_by_national,
            net_debt=direct_debt + cl_expected_loss,
            total_public_sector_debt=direct_debt + cl_exposure,
            transfers_received=transfers_total,
            self_funded_debt_service_pct=self_funded_pct,
            instrument_count=len(instruments),
            currency=entity.get("currency", "USD"),
        )

    def build_consolidated_tree(
        self,
        entities: list[dict],
        instruments_by_entity: dict[str, list[dict]],
        cls_by_entity: dict[str, list[dict]],
        transfers_by_entity: dict[str, list[dict]],
    ) -> list[EntityDebtSummary]:
        """Build a tree of EntityDebtSummary, then compute rollup for each parent."""
        summaries = {}
        for ent in entities:
            eid = ent["id"]
            summaries[eid] = self.build_entity_summary(
                entity=ent,
                instruments=instruments_by_entity.get(eid, []),
                contingent_liabilities=cls_by_entity.get(eid, []),
                transfers=transfers_by_entity.get(eid, []),
            )

        # Attach children
        roots = []
        for eid, summary in summaries.items():
            parent_id = summary.parent_id
            if parent_id and parent_id in summaries:
                summaries[parent_id].children.append(summary)
            elif parent_id is None:
                roots.append(summary)

        return roots

    def compute_rollup(self, summary: EntityDebtSummary) -> dict:
        """Recursive rollup: entity + all descendants."""
        total_direct = summary.direct_debt
        total_cl = summary.contingent_liability_exposure
        total_cl_loss = summary.contingent_liability_expected_loss
        total_guaranteed = summary.guaranteed_by_national
        total_transfers = summary.transfers_received
        total_instruments = summary.instrument_count

        for child in summary.children:
            child_rollup = self.compute_rollup(child)
            total_direct += child_rollup["direct_debt"]
            total_cl += child_rollup["contingent_liability_exposure"]
            total_cl_loss += child_rollup["contingent_liability_expected_loss"]
            total_guaranteed += child_rollup["guaranteed_by_national"]
            total_transfers += child_rollup["transfers_received"]
            total_instruments += child_rollup["instrument_count"]

        return {
            "entity_id": summary.entity_id,
            "entity_name": summary.entity_name,
            "entity_type": summary.entity_type,
            "direct_debt": total_direct,
            "contingent_liability_exposure": total_cl,
            "contingent_liability_expected_loss": total_cl_loss,
            "guaranteed_by_national": total_guaranteed,
            "net_debt": total_direct + total_cl_loss,
            "total_public_sector_debt": total_direct + total_cl,
            "transfers_received": total_transfers,
            "instrument_count": total_instruments,
            "child_count": len(summary.children),
            "currency": summary.currency,
        }
