"""Fiscal Framework & Budget Tracking Module.

Tracks government revenue, expenditure, deficits, and multi-year
fiscal targets. Integrates with debt management for comprehensive
fiscal-debt analysis.
"""

import uuid
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


class FiscalTracker:
    def __init__(self):
        self._lock = threading.Lock()
        self._budgets: Dict[str, dict] = {}
        self._actuals: Dict[str, dict] = {}
        self._targets: Dict[str, dict] = {}

    def set_budget(self, fiscal_year: str, budget: dict) -> dict:
        """Set budget allocation for a fiscal year."""
        entry = {
            "fiscal_year": fiscal_year,
            "gdp_nominal": budget.get("gdp_nominal", 0),
            "revenue": {
                "tax_revenue": budget.get("tax_revenue", 0),
                "non_tax_revenue": budget.get("non_tax_revenue", 0),
                "grants": budget.get("grants", 0),
                "other": budget.get("other_revenue", 0),
            },
            "expenditure": {
                "recurrent": budget.get("recurrent_expenditure", 0),
                "capital": budget.get("capital_expenditure", 0),
                "interest_payments": budget.get("interest_payments", 0),
                "transfers": budget.get("transfers", 0),
                "wages": budget.get("wages", 0),
                "other": budget.get("other_expenditure", 0),
            },
            "deficit_financing": {
                "domestic_borrowing": budget.get("domestic_borrowing", 0),
                "external_borrowing": budget.get("external_borrowing", 0),
                "drawdown_reserves": budget.get("drawdown_reserves", 0),
            },
            "fiscal_rules": budget.get("fiscal_rules", {}),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        total_rev = sum(entry["revenue"].values())
        total_exp = sum(entry["expenditure"].values())
        entry["total_revenue"] = round(total_rev, 1)
        entry["total_expenditure"] = round(total_exp, 1)
        entry["fiscal_balance"] = round(total_rev - total_exp, 1)
        entry["fiscal_balance_gdp_pct"] = round((total_rev - total_exp) / max(entry["gdp_nominal"], 1) * 100, 2)
        entry["revenue_gdp_pct"] = round(total_rev / max(entry["gdp_nominal"], 1) * 100, 2)
        entry["expenditure_gdp_pct"] = round(total_exp / max(entry["gdp_nominal"], 1) * 100, 2)

        with self._lock:
            self._budgets[fiscal_year] = entry
        return entry

    def record_actual(self, fiscal_year: str, period: str, actuals: dict) -> dict:
        """Record actual revenue/expenditure for a period."""
        key = f"{fiscal_year}_{period}"
        entry = {
            "fiscal_year": fiscal_year,
            "period": period,
            "revenue": actuals.get("revenue", {}),
            "expenditure": actuals.get("expenditure", {}),
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }

        entry["total_revenue"] = sum(entry["revenue"].values())
        entry["total_expenditure"] = sum(entry["expenditure"].values())
        entry["balance"] = entry["total_revenue"] - entry["total_expenditure"]

        with self._lock:
            self._actuals[key] = entry
        return entry

    def set_fiscal_target(self, fiscal_year: str, targets: dict) -> dict:
        """Set fiscal targets/rules for a fiscal year."""
        entry = {
            "fiscal_year": fiscal_year,
            "max_deficit_gdp_pct": targets.get("max_deficit_gdp_pct"),
            "max_debt_gdp_pct": targets.get("max_debt_gdp_pct"),
            "min_revenue_gdp_pct": targets.get("min_revenue_gdp_pct"),
            "max_interest_revenue_pct": targets.get("max_interest_revenue_pct"),
            "primary_balance_target": targets.get("primary_balance_target"),
            "expenditure_ceiling": targets.get("expenditure_ceiling"),
            "current_balance_target": targets.get("current_balance_target"),
            "set_at": datetime.now(timezone.utc).isoformat(),
        }

        with self._lock:
            self._targets[fiscal_year] = entry
        return entry

    def fiscal_dashboard(self, fiscal_year: str) -> Dict[str, Any]:
        """Generate comprehensive fiscal dashboard."""
        with self._lock:
            budget = self._budgets.get(fiscal_year, {})
            targets = self._targets.get(fiscal_year, {})

        if not budget:
            return {"error": f"No budget data for {fiscal_year}"}

        # Aggregate actuals for this fiscal year
        total_actual_rev = 0
        total_actual_exp = 0
        periods_recorded = 0

        with self._lock:
            for key, actual in self._actuals.items():
                if key.startswith(fiscal_year):
                    total_actual_rev += actual["total_revenue"]
                    total_actual_exp += actual["total_expenditure"]
                    periods_recorded += 1

        # Budget execution rate
        exec_rate_rev = (total_actual_rev / max(budget["total_revenue"], 1)) * 100 if periods_recorded > 0 else 0
        exec_rate_exp = (total_actual_exp / max(budget["total_expenditure"], 1)) * 100 if periods_recorded > 0 else 0

        # Variance analysis
        revenue_variance = budget["total_revenue"] - total_actual_rev if periods_recorded > 0 else 0
        expenditure_variance = budget["total_expenditure"] - total_actual_exp if periods_recorded > 0 else 0

        # Fiscal rule compliance
        compliance = {}
        if targets:
            actual_deficit_pct = (total_actual_rev - total_actual_exp) / max(budget["gdp_nominal"], 1) * 100 if periods_recorded > 0 else None

            if targets.get("max_deficit_gdp_pct") is not None and actual_deficit_pct is not None:
                compliance["deficit_rule"] = {
                    "target": f"Deficit < {targets['max_deficit_gdp_pct']}% of GDP",
                    "actual": round(actual_deficit_pct, 2),
                    "status": "compliant" if actual_deficit_pct <= targets["max_deficit_gdp_pct"] else "breach",
                }

            if targets.get("max_debt_gdp_pct") is not None:
                compliance["debt_rule"] = {
                    "target": f"Debt < {targets['max_debt_gdp_pct']}% of GDP",
                    "status": "pending" if periods_recorded < 12 else "compliant",
                }

        return {
            "fiscal_year": fiscal_year,
            "gdp_nominal": budget.get("gdp_nominal", 0),
            "budget": {
                "total_revenue": budget["total_revenue"],
                "total_expenditure": budget["total_expenditure"],
                "fiscal_balance": budget["fiscal_balance"],
                "fiscal_balance_gdp_pct": budget["fiscal_balance_gdp_pct"],
                "revenue_breakdown": budget["revenue"],
                "expenditure_breakdown": budget["expenditure"],
            },
            "actuals": {
                "total_revenue": round(total_actual_rev, 1),
                "total_expenditure": round(total_actual_exp, 1),
                "fiscal_balance": round(total_actual_rev - total_actual_exp, 1),
                "periods_recorded": periods_recorded,
            },
            "execution": {
                "revenue_execution_pct": round(exec_rate_rev, 1),
                "expenditure_execution_pct": round(exec_rate_exp, 1),
                "revenue_variance": round(revenue_variance, 1),
                "expenditure_variance": round(expenditure_variance, 1),
            },
            "compliance": compliance,
            "targets": targets,
        }

    def multi_year_summary(self) -> List[dict]:
        """Multi-year fiscal summary."""
        with self._lock:
            years = sorted(self._budgets.keys())

        return [self.fiscal_dashboard(y) for y in years]


_fiscal = None


def get_fiscal_tracker() -> FiscalTracker:
    global _fiscal
    if _fiscal is None:
        _fiscal = FiscalTracker()
    return _fiscal
