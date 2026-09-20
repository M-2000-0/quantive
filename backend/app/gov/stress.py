"""Sovereign Debt Stress Testing Engine.

Simulates adverse macroeconomic scenarios and their impact on
debt sustainability metrics. Supports:
- Interest rate shocks
- FX devaluation
- GDP contraction
- Revenue shortfall
- Commodity price collapse
- Combined/historical scenarios
"""

import math
import time
import uuid
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


class StressTestEngine:
    def __init__(self):
        self._lock = threading.Lock()
        self._scenarios: Dict[str, dict] = {}
        self._results: List[dict] = []

    def get_default_scenarios(self) -> List[dict]:
        """Return predefined stress scenarios."""
        return [
            {
                "id": "rate_shock_mild",
                "name": "Interest Rate Shock (+200bps)",
                "category": "interest_rate",
                "severity": "moderate",
                "description": "Central bank raises rates by 200bps to combat inflation",
                "shocks": {"interest_rate_change_bps": 200},
            },
            {
                "id": "rate_shock_severe",
                "name": "Interest Rate Shock (+500bps)",
                "category": "interest_rate",
                "severity": "severe",
                "description": "Aggressive tightening cycle due to inflation and currency pressure",
                "shocks": {"interest_rate_change_bps": 500},
            },
            {
                "id": "fx_devaluation_mild",
                "name": "Currency Depreciation (15%)",
                "category": "fx",
                "severity": "moderate",
                "description": "Currency loses 15% against USD due to capital outflows",
                "shocks": {"fx_change_pct": -15},
            },
            {
                "id": "fx_devaluation_severe",
                "name": "Currency Crisis (35%)",
                "category": "fx",
                "severity": "severe",
                "description": "Balance of payments crisis, currency depreciates 35%",
                "shocks": {"fx_change_pct": -35},
            },
            {
                "id": "gdp_recession",
                "name": "GDP Recession (-3%)",
                "category": "growth",
                "severity": "moderate",
                "description": "Economic contraction of 3% due to external demand shock",
                "shocks": {"gdp_growth_change_pct": -6},
            },
            {
                "id": "gdp_crisis",
                "name": "Economic Crisis (-8%)",
                "category": "growth",
                "severity": "severe",
                "description": "Deep recession combining demand shock and financial stress",
                "shocks": {"gdp_growth_change_pct": -11},
            },
            {
                "id": "revenue_shock",
                "name": "Revenue Collapse (-20%)",
                "category": "fiscal",
                "severity": "severe",
                "description": "Tax revenue falls 20% due to economic slowdown",
                "shocks": {"revenue_change_pct": -20},
            },
            {
                "id": "commodity_crash",
                "name": "Commodity Price Collapse (-40%)",
                "category": "external",
                "severity": "severe",
                "description": "Major export commodity prices drop 40%",
                "shocks": {"export_change_pct": -40, "revenue_change_pct": -15, "gdp_growth_change_pct": -4},
            },
            {
                "id": "combined_sri_lanka",
                "name": "Sri Lanka-type Crisis",
                "category": "combined",
                "severity": "extreme",
                "description": "Combined FX crisis, GDP contraction, and revenue collapse",
                "shocks": {"fx_change_pct": -40, "gdp_growth_change_pct": -8, "revenue_change_pct": -25, "interest_rate_change_bps": 800, "export_change_pct": -15},
            },
            {
                "id": "combined_greece",
                "name": "Greece-type Crisis",
                "category": "combined",
                "severity": "extreme",
                "description": "Sovereign debt crisis with austerity and recession",
                "shocks": {"gdp_growth_change_pct": -10, "revenue_change_pct": -30, "interest_rate_change_bps": 1000},
            },
        ]

    def run_stress_test(
        self,
        baseline: Dict[str, float],
        scenario_shocks: Dict[str, float],
        projection_years: int = 10,
    ) -> Dict[str, Any]:
        """Run a stress test against baseline DSA metrics.

        Args:
            baseline: {
                debt_stock, gdp, exports, revenue, interest_rate,
                primary_balance, fx_rate (vs USD), short_term_debt_ext
            }
            scenario_shocks: {
                interest_rate_change_bps, fx_change_pct, gdp_growth_change_pct,
                revenue_change_pct, export_change_pct
            }
        """
        t0 = time.time()

        debt = baseline.get("debt_stock", 0)
        gdp = baseline.get("gdp", 1)
        exports = baseline.get("exports", 1)
        revenue = baseline.get("revenue", 1)
        base_rate = baseline.get("interest_rate", 0.05)
        base_growth = baseline.get("baseline_gdp_growth", 0.03)
        base_pb = baseline.get("primary_balance", 0)
        fx_rate = baseline.get("fx_rate", 1)
        st_debt_ext = baseline.get("short_term_debt_ext", 0)

        # Apply shocks
        rate_change = scenario_shocks.get("interest_rate_change_bps", 0) / 10000
        fx_change = scenario_shocks.get("fx_change_pct", 0) / 100
        growth_change = scenario_shocks.get("gdp_growth_change_pct", 0) / 100
        rev_change = scenario_shocks.get("revenue_change_pct", 0) / 100
        exp_change = scenario_shocks.get("export_change_pct", 0) / 100

        stressed_rate = base_rate + rate_change
        stressed_growth = base_growth + growth_change
        stressed_revenue = revenue * (1 + rev_change)
        stressed_exports = exports * (1 + exp_change)
        new_fx_rate = fx_rate * (1 + fx_change)

        # FX impact on external debt
        fx_impact = (new_fx_rate / max(fx_rate, 0.001)) - 1
        stressed_debt = debt * (1 + max(0, fx_impact * 0.4))  # ~40% of debt is external

        # Project over time
        projections = []
        d = stressed_debt
        g = gdp

        for year in range(projection_years + 1):
            debt_gdp = d / max(g, 1) * 100
            interest = d * stressed_rate
            debt_service = interest + d * 0.15  # 15% amortization assumption
            debt_service_exports = debt_service / max(stressed_exports * ((1 + stressed_growth) ** year), 1) * 100
            debt_service_revenue = debt_service / max(stressed_revenue * ((1 + 0.02) ** year), 1) * 100

            projections.append({
                "year": year,
                "debt_stock": round(d, 1),
                "gdp": round(g, 1),
                "debt_gdp": round(debt_gdp, 1),
                "interest_payments": round(interest, 1),
                "debt_service": round(debt_service, 1),
                "debt_service_exports": round(debt_service_exports, 1),
                "debt_service_revenue": round(debt_service_revenue, 1),
            })

            # Advance one period
            d = d * (1 + stressed_rate) / (1 + stressed_growth) - base_pb
            g = g * (1 + stressed_growth)

        # Risk assessment
        final = projections[-1] if projections else {}
        initial_debt_gdp = projections[0]["debt_gdp"] if projections else 0
        final_debt_gdp = final.get("debt_gdp", 0)
        debt_path = "rising" if final_debt_gdp > initial_debt_gdp + 10 else "falling" if final_debt_gdp < initial_debt_gdp - 10 else "stable"

        # Determine severity
        if final_debt_gdp > 90:
            severity = "critical"
            severity_color = "#ef4444"
            severity_label = "Debt becomes unsustainable"
        elif final_debt_gdp > 70:
            severity = "high"
            severity_color = "#f59e0b"
            severity_label = "Debt reaches stress levels"
        elif final_debt_gdp > 55:
            severity = "moderate"
            severity_color = "#60a5fa"
            severity_label = "Manageable but concerning"
        else:
            severity = "low"
            severity_color = "#22c55e"
            severity_label = "Remains sustainable"

        elapsed = (time.time() - t0) * 1000

        result = {
            "id": str(uuid.uuid4())[:12],
            "scenario_shocks": scenario_shocks,
            "baseline": baseline,
            "stressed_params": {
                "stressed_rate": round(stressed_rate * 100, 2),
                "stressed_growth": round(stressed_growth * 100, 2),
                "stressed_revenue": round(stressed_revenue, 1),
                "stressed_exports": round(stressed_exports, 1),
                "fx_impact_pct": round(fx_change * 100, 1),
            },
            "initial_debt_gdp": round(initial_debt_gdp, 1),
            "final_debt_gdp": round(final_debt_gdp, 1),
            "debt_path": debt_path,
            "severity": severity,
            "severity_color": severity_color,
            "severity_label": severity_label,
            "projections": projections,
            "latency_ms": round(elapsed, 1),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        with self._lock:
            self._results.append(result)

        return result

    def run_custom_scenario(self, baseline: Dict[str, float], shocks: Dict[str, float]) -> Dict[str, Any]:
        return self.run_stress_test(baseline, shocks)

    def get_history(self) -> List[dict]:
        with self._lock:
            return list(self._results[-50:])


_stress = None


def get_stress_engine() -> StressTestEngine:
    global _stress
    if _stress is None:
        _stress = StressTestEngine()
    return _stress
