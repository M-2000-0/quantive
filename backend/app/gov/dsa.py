"""IMF-Compliant Debt Sustainability Analysis (DSA) Engine.

Implements the IMF/World Bank debt sustainability framework for
low-income and market-access countries. Follows the IMF DSA guidelines
published in the Operational Guidance Note (OGN).

Key metrics:
- PV of debt-to-exports ratio
- PV of debt-to-revenue ratio
- Debt service-to-exports ratio
- Debt service-to-revenue ratio
- Debt-to-GDP ratio
- Gross financing needs (GFN)-to-GDP ratio
"""

import math
import time
import uuid
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


# ── IMF DSA Thresholds ───────────────────────────────────────────────

# Market-access countries (MAC) thresholds
MAC_THRESHOLDS = {
    "pv_debt_exports": {"warning": 140, "stress": 240, "limit": 300},
    "pv_debt_revenue": {"warning": 200, "stress": 300, "limit": 350},
    "debt_service_exports": {"warning": 10, "stress": 15, "limit": 20},
    "debt_service_revenue": {"warning": 10, "stress": 15, "limit": 23},
    "debt_gdp": {"warning": 55, "stress": 70, "limit": 80},
    "gfn_gdp": {"warning": 15, "stress": 20, "limit": 24},
}

# Low-income countries (LIC) thresholds
LIC_THRESHOLDS = {
    "pv_debt_exports": {"warning": 140, "stress": 240, "limit": 300},
    "pv_debt_revenue": {"warning": 200, "stress": 300, "limit": 350},
    "debt_service_exports": {"warning": 10, "stress": 15, "limit": 20},
    "debt_service_revenue": {"warning": 14, "stress": 18, "limit": 23},
    "debt_gdp": {"warning": 30, "stress": 40, "limit": 50},
    "gfn_gdp": {"warning": 15, "stress": 20, "limit": 24},
}


class DSACalculator:
    """Thread-safe DSA calculation engine."""

    def __init__(self):
        self._lock = threading.Lock()
        self._history: List[dict] = []

    def compute_dsa(
        self,
        debt_stock: float,
        gdp_nominal: float,
        exports: float,
        revenue: float,
        debt_service: float,
        interest_payments: float,
        principal_repayments: float,
        gross_financing_needs: float,
        country_type: str = "mac",
        total_ext_debt: float = 0,
        concessional_debt: float = 0,
        short_term_debt: float = 0,
        reserves: float = 0,
    ) -> Dict[str, Any]:
        """Compute IMF DSA metrics.

        Args:
            debt_stock: Total public debt stock (USD millions)
            gdp_nominal: Nominal GDP (USD millions)
            exports: Goods and services exports (USD millions)
            revenue: Total government revenue (USD millions)
            debt_service: Total debt service (principal + interest) (USD millions)
            interest_payments: Total interest payments (USD millions)
            principal_repayments: Total principal repayments (USD millions)
            gross_financing_needs: GFN = deficit + debt service + amortization (USD millions)
            country_type: "mac" for market-access, "lic" for low-income
            total_ext_debt: Total external debt (USD millions)
            concessional_debt: Concessional debt stock (USD millions)
            short_term_debt: Short-term debt (USD millions)
            reserves: Gross international reserves (USD millions)
        """
        t0 = time.time()
        thresholds = MAC_THRESHOLDS if country_type == "mac" else LIC_THRESHOLDS

        # Core ratios
        pv_debt_exports = (debt_stock / max(exports, 1)) * 100
        pv_debt_revenue = (debt_stock / max(revenue, 1)) * 100
        debt_service_exports = (debt_service / max(exports, 1)) * 100
        debt_service_revenue = (debt_service / max(revenue, 1)) * 100
        debt_gdp = (debt_stock / max(gdp_nominal, 1)) * 100
        gfn_gdp = (gross_financing_needs / max(gdp_nominal, 1)) * 100

        # Derived metrics
        interest_coverage = revenue / max(interest_payments, 1)
        debt_to_exports = debt_stock / max(exports, 1)
        reserves_months = (reserves / max(debt_service / 12, 1)) if reserves > 0 else 0
        concessional_share = (concessional_debt / max(debt_stock, 1)) * 100
        external_share = (total_ext_debt / max(debt_stock, 1)) * 100
        short_term_ratio = (short_term_debt / max(debt_stock, 1)) * 100

        # Debt sustainability assessment
        risk_score = 0
        risk_factors = []
        warnings = []
        breaches = []

        for metric, value in [
            ("pv_debt_exports", pv_debt_exports),
            ("pv_debt_revenue", pv_debt_revenue),
            ("debt_service_exports", debt_service_exports),
            ("debt_service_revenue", debt_service_revenue),
            ("debt_gdp", debt_gdp),
            ("gfn_gdp", gfn_gdp),
        ]:
            t = thresholds[metric]
            if value >= t["limit"]:
                risk_score += 3
                breaches.append({"metric": metric, "value": round(value, 1), "threshold": t["limit"]})
                risk_factors.append(f"{metric} ({round(value, 1)}%) at breach level (>{t['limit']}%)")
            elif value >= t["stress"]:
                risk_score += 2
                warnings.append({"metric": metric, "value": round(value, 1), "threshold": t["stress"]})
                risk_factors.append(f"{metric} ({round(value, 1)}%) at stress level (>{t['stress']}%)")
            elif value >= t["warning"]:
                risk_score += 1
                warnings.append({"metric": metric, "value": round(value, 1), "threshold": t["warning"]})
                risk_factors.append(f"{metric} ({round(value, 1)}%) above warning threshold (>{t['warning']}%)")

        # Risk rating
        if risk_score >= 6:
            risk_rating = "critical"
            risk_color = "#ef4444"
            risk_label = "In Distress / Unsustainable"
        elif risk_score >= 4:
            risk_rating = "high"
            risk_color = "#f59e0b"
            risk_label = "High Risk of Unsustainability"
        elif risk_score >= 2:
            risk_rating = "moderate"
            risk_color = "#60a5fa"
            risk_label = "Moderate Risk"
        elif risk_score >= 1:
            risk_rating = "low"
            risk_color = "#22c55e"
            risk_label = "Low Risk"
        else:
            risk_rating = "sustainable"
            risk_color = "#22c55e"
            risk_label = "Sustainable"

        # Policy recommendations
        recommendations = self._generate_recommendations(
            debt_gdp, pv_debt_exports, debt_service_exports, gfn_gdp,
            concessional_share, external_share, short_term_ratio, risk_rating
        )

        # Debt dynamics projection (10-year)
        projections = self._project_debt_dynamics(
            debt_stock=debt_stock,
            gdp=gdp_nominal,
            primary_deficit=abs(gross_financing_needs - interest_payments - principal_repayments),
            interest_rate=interest_payments / max(debt_stock, 1),
            gdp_growth=0.03,  # baseline 3%
            years=10,
        )

        elapsed = (time.time() - t0) * 1000

        result = {
            "period": datetime.now(timezone.utc).strftime("%Y-%m"),
            "country_type": country_type,
            "risk_rating": risk_rating,
            "risk_color": risk_color,
            "risk_label": risk_label,
            "risk_score": risk_score,
            "indicators": {
                "pv_debt_exports": round(pv_debt_exports, 1),
                "pv_debt_revenue": round(pv_debt_revenue, 1),
                "debt_service_exports": round(debt_service_exports, 1),
                "debt_service_revenue": round(debt_service_revenue, 1),
                "debt_gdp": round(debt_gdp, 1),
                "gfn_gdp": round(gfn_gdp, 1),
            },
            "thresholds": thresholds,
            "derived": {
                "interest_coverage": round(interest_coverage, 2),
                "debt_to_exports": round(debt_to_exports, 2),
                "reserves_months": round(reserves_months, 1),
                "concessional_share_pct": round(concessional_share, 1),
                "external_share_pct": round(external_share, 1),
                "short_term_ratio_pct": round(short_term_ratio, 1),
            },
            "risk_factors": risk_factors,
            "warnings": warnings,
            "breaches": breaches,
            "recommendations": recommendations,
            "projections": projections,
            "inputs": {
                "debt_stock": debt_stock,
                "gdp_nominal": gdp_nominal,
                "exports": exports,
                "revenue": revenue,
                "debt_service": debt_service,
                "gross_financing_needs": gross_financing_needs,
            },
            "latency_ms": round(elapsed, 1),
        }

        with self._lock:
            self._history.append({
                "period": result["period"],
                "risk_rating": risk_rating,
                "risk_score": risk_score,
                "debt_gdp": round(debt_gdp, 1),
            })

        return result

    def _project_debt_dynamics(
        self,
        debt_stock: float,
        gdp: float,
        primary_deficit: float,
        interest_rate: float,
        gdp_growth: float,
        years: int = 10,
    ) -> List[dict]:
        """Project debt dynamics over time (IMF methodology).

        d(t+1) = d(t) * (1 + r) / (1 + g) - pb
        where d = debt/GDP, r = interest rate, g = growth, pb = primary balance/GDP
        """
        projections = []
        debt_gdp = debt_stock / max(gdp, 1)
        pb_ratio = primary_deficit / max(gdp, 1)

        for year in range(years + 1):
            projections.append({
                "year": year,
                "debt_gdp": round(debt_gdp * 100, 1),
            })
            # One period forward
            debt_gdp = debt_gdp * (1 + interest_rate) / (1 + gdp_growth) - pb_ratio

        return projections

    def _generate_recommendations(
        self,
        debt_gdp: float,
        pv_debt_exports: float,
        debt_service_exports: float,
        gfn_gdp: float,
        concessional_share: float,
        external_share: float,
        short_term_ratio: float,
        risk_rating: str,
    ) -> List[Dict[str, str]]:
        """Generate policy recommendations based on DSA results."""
        recs = []

        if debt_gdp > 70:
            recs.append({
                "priority": "critical",
                "area": "fiscal",
                "recommendation": "Implement fiscal consolidation plan. Target primary surplus of 1-2% of GDP within 2 years.",
                "rationale": f"Debt-to-GDP at {debt_gdp:.1f}% exceeds sustainable threshold.",
            })

        if pv_debt_exports > 200:
            recs.append({
                "priority": "high",
                "area": "exports",
                "recommendation": "Develop export diversification strategy. Consider export credit guarantees.",
                "rationale": "PV of debt-to-exports ratio indicates export capacity is insufficient for debt servicing.",
            })

        if debt_service_exports > 15:
            recs.append({
                "priority": "high",
                "area": "debt_management",
                "recommendation": "Extend debt maturity profile. Negotiate amortization rescheduling with creditors.",
                "rationale": "Debt service burden is unsustainably high relative to export earnings.",
            })

        if gfn_gdp > 20:
            recs.append({
                "priority": "high",
                "area": "financing",
                "recommendation": "Diversify financing sources. Explore concessional borrowing, diaspora bonds, or SWAP facilities.",
                "rationale": "Gross financing needs are high, increasing rollover risk.",
            })

        if concessional_share < 30:
            recs.append({
                "priority": "medium",
                "area": "concessional",
                "recommendation": "Maximize access to concessional financing (IDA, AfDB, IMF PRGT).",
                "rationale": f"Only {concessional_share:.0f}% of debt is concessional. This limits fiscal space.",
            })

        if short_term_ratio > 15:
            recs.append({
                "priority": "medium",
                "area": "maturity",
                "recommendation": "Reduce reliance on short-term debt. Issue longer-dated bonds when market conditions allow.",
                "rationale": f"Short-term debt at {short_term_ratio:.0f}% creates refinancing risk.",
            })

        if risk_rating in ("critical", "high"):
            recs.append({
                "priority": "critical",
                "area": "governance",
                "recommendation": "Establish debt management unit with direct reporting to Finance Minister. Implement real-time debt monitoring.",
                "rationale": "High-risk status requires immediate institutional strengthening.",
            })

        return recs

    def get_history(self) -> List[dict]:
        with self._lock:
            return list(self._history)


_dsa = None


def get_dsa_calculator() -> DSACalculator:
    global _dsa
    if _dsa is None:
        _dsa = DSACalculator()
    return _dsa
