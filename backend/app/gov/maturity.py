"""Maturity Profile & Rollover Risk Analyzer.

Tracks debt maturity schedules, identifies concentration risk,
and calculates rollover requirements by year, currency, and instrument type.
"""

import math
import uuid
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta


class MaturityAnalyzer:
    def __init__(self):
        self._lock = threading.Lock()
        self._instruments: Dict[str, dict] = {}

    def add_instrument(self, instrument: dict) -> dict:
        """Add a debt instrument to the portfolio."""
        inst = {
            "id": instrument.get("id", str(uuid.uuid4())[:12]),
            "name": instrument.get("name", ""),
            "isin": instrument.get("isin", ""),
            "type": instrument.get("type", "bond"),  # bond, treasury_bill, loan, facility, sukuks
            "currency": instrument.get("currency", "USD"),
            "coupon_rate": instrument.get("coupon_rate", 0),
            "face_value": instrument.get("face_value", 0),
            "outstanding": instrument.get("outstanding", instrument.get("face_value", 0)),
            "issue_date": instrument.get("issue_date", ""),
            "maturity_date": instrument.get("maturity_date", ""),
            "investor_type": instrument.get("investor_type", "external"),  # external, domestic, multilateral, bilateral
            "investor_name": instrument.get("investor_name", ""),
            "rating": instrument.get("rating", ""),
            "collateral": instrument.get("collateral", ""),
            "amortization": instrument.get("amortization", "bullet"),  # bullet, amortizing, zero_coupon
            "callable": instrument.get("callable", False),
            "call_date": instrument.get("call_date", ""),
        }

        with self._lock:
            self._instruments[inst["id"]] = inst
        return inst

    def remove_instrument(self, instrument_id: str) -> bool:
        with self._lock:
            if instrument_id in self._instruments:
                del self._instruments[instrument_id]
                return True
        return False

    def get_instruments(self) -> List[dict]:
        with self._lock:
            return list(self._instruments.values())

    def compute_maturity_profile(self, as_of_date: str = None) -> Dict[str, Any]:
        """Compute maturity profile analysis."""
        if as_of_date is None:
            as_of_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        as_of = datetime.strptime(as_of_date, "%Y-%m-%d")

        # Group by maturity bucket
        buckets = {
            "0-1Y": {"debt": 0, "instruments": [], "interest": 0},
            "1-2Y": {"debt": 0, "instruments": [], "interest": 0},
            "2-3Y": {"debt": 0, "instruments": [], "interest": 0},
            "3-5Y": {"debt": 0, "instruments": [], "interest": 0},
            "5-7Y": {"debt": 0, "instruments": [], "interest": 0},
            "7-10Y": {"debt": 0, "instruments": [], "interest": 0},
            "10-15Y": {"debt": 0, "instruments": [], "interest": 0},
            "15-20Y": {"debt": 0, "instruments": [], "interest": 0},
            "20Y+": {"debt": 0, "instruments": [], "interest": 0},
        }

        by_currency = {}
        by_type = {}
        by_investor = {}
        total_outstanding = 0
        total_annual_service = 0

        with self._lock:
            for inst in self._instruments.values():
                try:
                    mat_date = datetime.strptime(inst["maturity_date"], "%Y-%m-%d")
                except (ValueError, KeyError):
                    continue

                years_to_maturity = (mat_date - as_of).days / 365.25
                outstanding = inst["outstanding"]
                coupon = inst["coupon_rate"]
                annual_interest = outstanding * coupon / 100

                total_outstanding += outstanding
                total_annual_service += annual_interest

                # Assign to bucket
                bucket = self._get_bucket(years_to_maturity)
                if bucket:
                    buckets[bucket]["debt"] += outstanding
                    buckets[bucket]["instruments"].append(inst["id"])
                    buckets[bucket]["interest"] += annual_interest

                # By currency
                cur = inst["currency"]
                by_currency[cur] = by_currency.get(cur, 0) + outstanding

                # By type
                typ = inst["type"]
                by_type[typ] = by_type.get(typ, 0) + outstanding

                # By investor
                inv = inst["investor_type"]
                by_investor[inv] = by_investor.get(inv, 0) + outstanding

        # Concentration risk analysis
        concentration = self._analyze_concentration(buckets, total_outstanding)

        # Rollover risk
        rollover = self._analyze_rollover_risk(buckets, total_outstanding)

        # Average maturity
        avg_maturity = self._compute_avg_maturity()

        # Weighted average coupon
        weighted_coupon = self._compute_weighted_coupon(total_outstanding)

        return {
            "as_of_date": as_of_date,
            "total_outstanding": round(total_outstanding, 2),
            "total_instruments": len(self._instruments),
            "avg_maturity_years": round(avg_maturity, 1),
            "weighted_avg_coupon_pct": round(weighted_coupon, 2),
            "annual_interest_estimate": round(total_annual_service, 2),
            "buckets": {k: {
                "debt_outstanding": round(v["debt"], 2),
                "pct_of_total": round((v["debt"] / max(total_outstanding, 1)) * 100, 1),
                "annual_interest": round(v["interest"], 2),
                "instrument_count": len(v["instruments"]),
            } for k, v in buckets.items()},
            "by_currency": {k: {"amount": round(v, 2), "pct": round(v / max(total_outstanding, 1) * 100, 1)} for k, v in sorted(by_currency.items(), key=lambda x: -x[1])},
            "by_type": {k: {"amount": round(v, 2), "pct": round(v / max(total_outstanding, 1) * 100, 1)} for k, v in sorted(by_type.items(), key=lambda x: -x[1])},
            "by_investor": {k: {"amount": round(v, 2), "pct": round(v / max(total_outstanding, 1) * 100, 1)} for k, v in sorted(by_investor.items(), key=lambda x: -x[1])},
            "concentration_risk": concentration,
            "rollover_risk": rollover,
        }

    def _get_bucket(self, years: float) -> Optional[str]:
        if years <= 1: return "0-1Y"
        elif years <= 2: return "1-2Y"
        elif years <= 3: return "2-3Y"
        elif years <= 5: return "3-5Y"
        elif years <= 7: return "5-7Y"
        elif years <= 10: return "7-10Y"
        elif years <= 15: return "10-15Y"
        elif years <= 20: return "15-20Y"
        else: return "20Y+"

    def _analyze_concentration(self, buckets: dict, total: float) -> dict:
        """Check for maturity concentration risk."""
        alerts = []
        near_term_pct = (buckets["0-1Y"]["debt"] + buckets["1-2Y"]["debt"]) / max(total, 1) * 100
        single_year_max = max(v["debt"] for v in buckets.values()) / max(total, 1) * 100

        if near_term_pct > 30:
            alerts.append(f"ALERT: {near_term_pct:.0f}% of debt matures within 2 years. Severe rollover risk.")
        elif near_term_pct > 20:
            alerts.append(f"WARNING: {near_term_pct:.0f}% of debt matures within 2 years.")

        if single_year_max > 25:
            alerts.append(f"WARNING: Single maturity bucket holds {single_year_max:.0f}% of total debt.")

        return {
            "near_term_2y_pct": round(near_term_pct, 1),
            "max_bucket_pct": round(single_year_max, 1),
            "alerts": alerts,
            "rating": "high" if near_term_pct > 30 else "moderate" if near_term_pct > 20 else "low",
        }

    def _analyze_rollover_risk(self, buckets: dict, total: float) -> dict:
        """Calculate rollover requirements."""
        year1 = buckets["0-1Y"]["debt"]
        year2 = buckets["1-2Y"]["debt"]

        return {
            "year_1_rollover": round(year1, 2),
            "year_2_rollover": round(year2, 2),
            "year_1_pct": round(year1 / max(total, 1) * 100, 1),
            "year_2_pct": round(year2 / max(total, 1) * 100, 1),
            "assessment": "critical" if year1 / max(total, 1) > 0.25 else "high" if year1 / max(total, 1) > 0.15 else "moderate" if year1 / max(total, 1) > 0.10 else "low",
        }

    def _compute_avg_maturity(self) -> float:
        if not self._instruments:
            return 0
        as_of = datetime.now(timezone.utc)
        total_weighted = 0
        total_value = 0
        for inst in self._instruments.values():
            try:
                mat = datetime.strptime(inst["maturity_date"], "%Y-%m-%d")
                years = (mat - as_of).days / 365.25
                if years > 0:
                    total_weighted += years * inst["outstanding"]
                    total_value += inst["outstanding"]
            except (ValueError, KeyError):
                continue
        return total_weighted / max(total_value, 1)

    def _compute_weighted_coupon(self, total: float) -> float:
        if total <= 0:
            return 0
        weighted = sum(inst["coupon_rate"] * inst["outstanding"] for inst in self._instruments.values())
        return weighted / total


_maturity = None


def get_maturity_analyzer() -> MaturityAnalyzer:
    global _maturity
    if _maturity is None:
        _maturity = MaturityAnalyzer()
    return _maturity
