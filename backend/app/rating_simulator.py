"""Rating Agency Simulator.

Models how S&P, Moody's, and Fitch assess sovereign creditworthiness.
Based on published rating methodologies:
- S&P: sovereign rating methodology (GCI, EFI, fiscal assessment)
- Moody's: sovereign bond ratings (economic strength, institutional strength, fiscal strength, susceptibility)
- Fitch: rating guidelines (macroeconomic performance, public finance, external finance)

This simulator allows users to ask "what-if" questions about how changes
in their debt strategy would affect credit ratings.
"""

from dataclasses import dataclass, field
from typing import Optional

# S&P methodology weights (from published sovereign rating criteria)
SP_WEIGHTS = {
    "institutional_assessment": 0.25,
    "economic_assessment": 0.25,
    "external_assessment": 0.25,
    "fiscal_assessment": 0.25,
}

# Moody's methodology weights
MOODYS_WEIGHTS = {
    "economic_strength": 0.30,
    "institutional_strength": 0.25,
    "fiscal_strength": 0.25,
    "susceptibility_to_event_risk": 0.20,
}

# Fitch methodology weights
FITCH_WEIGHTS = {
    "macroeconomic_performance": 0.20,
    "public_finances": 0.25,
    "external_finances": 0.20,
    "structural_features": 0.15,
    "governance": 0.20,
}

# Rating scales
SP_SCALE = ["AAA", "AA+", "AA", "AA-", "A+", "A", "A-", "BBB+", "BBB", "BBB-", "BB+", "BB", "BB-", "B+", "B", "B-", "CCC+", "CCC", "CC", "C", "D"]
MOODYS_SCALE = ["Aaa", "Aa1", "Aa2", "Aa3", "A1", "A2", "A3", "Baa1", "Baa2", "Baa3", "Ba1", "Ba2", "Ba3", "B1", "B2", "B3", "Caa1", "Caa2", "Caa3", "Ca", "C"]
FITCH_SCALE = ["AAA", "AA+", "AA", "AA-", "A+", "A", "A-", "BBB+", "BBB", "BBB-", "BB+", "BB", "BB-", "B+", "B", "B-", "CCC+", "CCC", "CC", "C", "D"]

# Country baseline data for rating assessment
COUNTRY_RATING_DATA: dict[str, dict] = {
    "US": {
        "gdp_per_capita": 76000, "gdp_growth": 2.5, "inflation": 3.2, "unemployment": 3.7,
        "debt_to_gdp": 123, "deficit_to_gdp": -6.3, "primary_balance": -3.8,
        "reserves_months": 2, "current_account_pct": -3.5, "external_debt_pct": 95,
        "institutions_score": 85, "rule_of_law": 90, "political_stability": 75,
        "currency_reserve_status": True, "sp_rating": "AA+", "moodys_rating": "Aaa", "fitch_rating": "AAA",
    },
    "UK": {
        "gdp_per_capita": 46000, "gdp_growth": 1.8, "inflation": 4.0, "unemployment": 4.1,
        "debt_to_gdp": 100, "deficit_to_gdp": -4.1, "primary_balance": -1.5,
        "reserves_months": 2, "current_account_pct": -3.8, "external_debt_pct": 310,
        "institutions_score": 82, "rule_of_law": 88, "political_stability": 72,
        "currency_reserve_status": True, "sp_rating": "AA", "moodys_rating": "Aa3", "fitch_rating": "AA-",
    },
    "DE": {
        "gdp_per_capita": 51000, "gdp_growth": 0.3, "inflation": 2.9, "unemployment": 3.0,
        "debt_to_gdp": 66, "deficit_to_gdp": -2.5, "primary_balance": 0.5,
        "reserves_months": 3, "current_account_pct": 5.0, "external_debt_pct": 175,
        "institutions_score": 90, "rule_of_law": 92, "political_stability": 80,
        "currency_reserve_status": True, "sp_rating": "AAA", "moodys_rating": "Aaa", "fitch_rating": "AAA",
    },
    "FR": {
        "gdp_per_capita": 44000, "gdp_growth": 0.7, "inflation": 2.3, "unemployment": 7.3,
        "debt_to_gdp": 112, "deficit_to_gdp": -5.5, "primary_balance": -2.0,
        "reserves_months": 2, "current_account_pct": -2.0, "external_debt_pct": 280,
        "institutions_score": 78, "rule_of_law": 85, "political_stability": 65,
        "currency_reserve_status": True, "sp_rating": "AA", "moodys_rating": "Aa3", "fitch_rating": "AA-",
    },
    "JP": {
        "gdp_per_capita": 34000, "gdp_growth": 1.0, "inflation": 3.3, "unemployment": 2.5,
        "debt_to_gdp": 264, "deficit_to_gdp": -4.5, "primary_balance": -2.0,
        "reserves_months": 24, "current_account_pct": 3.5, "external_debt_pct": 18,
        "institutions_score": 80, "rule_of_law": 88, "political_stability": 82,
        "currency_reserve_status": False, "sp_rating": "A+", "moodys_rating": "A1", "fitch_rating": "A+",
    },
    "CN": {
        "gdp_per_capita": 12700, "gdp_growth": 5.2, "inflation": 0.2, "unemployment": 5.2,
        "debt_to_gdp": 83, "deficit_to_gdp": -7.6, "primary_balance": -5.0,
        "reserves_months": 18, "current_account_pct": 1.8, "external_debt_pct": 15,
        "institutions_score": 45, "rule_of_law": 50, "political_stability": 55,
        "currency_reserve_status": False, "sp_rating": "A+", "moodys_rating": "A1", "fitch_rating": "A+",
    },
    "IN": {
        "gdp_per_capita": 2600, "gdp_growth": 7.8, "inflation": 5.4, "unemployment": 3.2,
        "debt_to_gdp": 81, "deficit_to_gdp": -5.8, "primary_balance": -2.5,
        "reserves_months": 10, "current_account_pct": -1.2, "external_debt_pct": 20,
        "institutions_score": 50, "rule_of_law": 55, "political_stability": 55,
        "currency_reserve_status": False, "sp_rating": "BBB-", "moodys_rating": "Baa3", "fitch_rating": "BBB-",
    },
    "BR": {
        "gdp_per_capita": 10400, "gdp_growth": 2.9, "inflation": 4.6, "unemployment": 7.9,
        "debt_to_gdp": 74, "deficit_to_gdp": -7.4, "primary_balance": -1.5,
        "reserves_months": 14, "current_account_pct": -2.5, "external_debt_pct": 35,
        "institutions_score": 42, "rule_of_law": 48, "political_stability": 45,
        "currency_reserve_status": False, "sp_rating": "BB", "moodys_rating": "Ba2", "fitch_rating": "BB-",
    },
    "ZA": {
        "gdp_per_capita": 6200, "gdp_growth": 0.6, "inflation": 5.1, "unemployment": 32.0,
        "debt_to_gdp": 74, "deficit_to_gdp": -4.3, "primary_balance": -1.0,
        "reserves_months": 5, "current_account_pct": -1.5, "external_debt_pct": 45,
        "institutions_score": 38, "rule_of_law": 42, "political_stability": 35,
        "currency_reserve_status": False, "sp_rating": "BB-", "moodys_rating": "Ba2", "fitch_rating": "BB-",
    },
    "TR": {
        "gdp_per_capita": 11000, "gdp_growth": 4.5, "inflation": 65.0, "unemployment": 9.5,
        "debt_to_gdp": 35, "deficit_to_gdp": -3.0, "primary_balance": 1.5,
        "reserves_months": 3, "current_account_pct": -4.0, "external_debt_pct": 55,
        "institutions_score": 35, "rule_of_law": 38, "political_stability": 30,
        "currency_reserve_status": False, "sp_rating": "B+", "moodys_rating": "B3", "fitch_rating": "B+",
    },
    "RU": {
        "gdp_per_capita": 12000, "gdp_growth": 3.6, "inflation": 7.4, "unemployment": 2.9,
        "debt_to_gdp": 18, "deficit_to_gdp": -1.9, "primary_balance": 0.5,
        "reserves_months": 20, "current_account_pct": 4.5, "external_debt_pct": 12,
        "institutions_score": 25, "rule_of_law": 28, "political_stability": 25,
        "currency_reserve_status": False, "sp_rating": "CC", "moodys_rating": "Ca", "fitch_rating": "CC",
    },
    "KR": {
        "gdp_per_capita": 33000, "gdp_growth": 2.1, "inflation": 3.6, "unemployment": 2.7,
        "debt_to_gdp": 54, "deficit_to_gdp": -3.5, "primary_balance": -0.5,
        "reserves_months": 10, "current_account_pct": 1.5, "external_debt_pct": 35,
        "institutions_score": 68, "rule_of_law": 75, "political_stability": 65,
        "currency_reserve_status": False, "sp_rating": "AA", "moodys_rating": "Aa2", "fitch_rating": "AA-",
    },
    "CH": {
        "gdp_per_capita": 92000, "gdp_growth": 1.3, "inflation": 1.7, "unemployment": 2.3,
        "debt_to_gdp": 30, "deficit_to_gdp": 0.5, "primary_balance": 1.5,
        "reserves_months": 48, "current_account_pct": 8.0, "external_debt_pct": 100,
        "institutions_score": 92, "rule_of_law": 95, "political_stability": 92,
        "currency_reserve_status": False, "sp_rating": "AAA", "moodys_rating": "Aaa", "fitch_rating": "AAA",
    },
}


@dataclass
class RatingAssessment:
    agency: str
    current_rating: str
    simulated_rating: str
    rating_change: str
    score: float
    components: dict
    key_drivers: list = field(default_factory=list)
    outlook: str = "stable"


class RatingSimulatorEngine:
    """Simulates sovereign credit rating assessments."""

    def __init__(self, country_code: str, portfolio_data: Optional[dict] = None):
        self.country_code = country_code.upper()
        self.data = COUNTRY_RATING_DATA.get(self.country_code, self._default_data())
        self.portfolio = portfolio_data

    def _default_data(self) -> dict:
        return {
            "gdp_per_capita": 5000, "gdp_growth": 3.0, "inflation": 5.0, "unemployment": 8.0,
            "debt_to_gdp": 60, "deficit_to_gdp": -4.0, "primary_balance": -1.5,
            "reserves_months": 6, "current_account_pct": -2.0, "external_debt_pct": 50,
            "institutions_score": 50, "rule_of_law": 55, "political_stability": 50,
            "currency_reserve_status": False, "sp_rating": "BBB", "moodys_rating": "Baa2", "fitch_rating": "BBB",
        }

    def simulate_all(self, shocks: Optional[dict] = None) -> dict:
        """Run rating simulation for all three agencies with optional shocks."""
        d = dict(self.data)
        if shocks:
            d = self._apply_shocks(d, shocks)

        sp = self._simulate_sp(d)
        moodys = self._simulate_moodys(d)
        fitch = self._simulate_fitch(d)

        # Overall assessment
        _ratings = [sp.simulated_rating, moodys.simulated_rating, fitch.simulated_rating]
        avg_score = (sp.score + moodys.score + fitch.score) / 3

        # Determine outlook
        outlook = "stable"
        if avg_score > self._rating_to_score(sp.current_rating, "sp") + 5:
            outlook = "positive"
        elif avg_score < self._rating_to_score(sp.current_rating, "sp") - 5:
            outlook = "negative"

        # Collect all key drivers
        all_drivers = sp.key_drivers + moodys.key_drivers + fitch.key_drivers
        unique_drivers = list({d["metric"]: d for d in all_drivers}.values())

        return {
            "country": self.country_code,
            "current_ratings": {
                "sp": d.get("sp_rating", "NR"),
                "moodys": d.get("moodys_rating", "NR"),
                "fitch": d.get("fitch_rating", "NR"),
            },
            "simulated_ratings": {
                "sp": sp.simulated_rating,
                "moodys": moodys.simulated_rating,
                "fitch": fitch.simulated_rating,
            },
            "rating_changes": {
                "sp": sp.rating_change,
                "moodys": moodys.rating_change,
                "fitch": fitch.rating_change,
            },
            "assessments": {
                "sp": self._assessment_to_dict(sp),
                "moodys": self._assessment_to_dict(moodys),
                "fitch": self._assessment_to_dict(fitch),
            },
            "outlook": outlook,
            "average_score": round(avg_score, 1),
            "key_drivers": unique_drivers[:10],
            "input_data": d,
            "shocks_applied": shocks or {},
        }

    def _apply_shocks(self, data: dict, shocks: dict) -> dict:
        d = dict(data)
        for key, value in shocks.items():
            if key in d:
                current = d[key]
                if isinstance(current, (int, float)):
                    if isinstance(value, str) and value.startswith("+"):
                        d[key] = current + float(value[1:])
                    elif isinstance(value, str) and value.startswith("-"):
                        d[key] = current - float(value[1:])
                    else:
                        d[key] = float(value)
                else:
                    d[key] = value
        return d

    def _simulate_sp(self, d: dict) -> RatingAssessment:
        """Simulate S&P rating based on their published methodology."""
        # Institutional assessment (0-100)
        inst = (d["institutions_score"] + d["rule_of_law"] + d["political_stability"]) / 3

        # Economic assessment (0-100)
        gdp_pc_score = min(100, d["gdp_per_capita"] / 1000 * 2)
        growth_score = min(100, max(0, d["gdp_growth"] * 15 + 20))
        inflation_score = min(100, max(0, 100 - d["inflation"] * 10))
        econ = (gdp_pc_score + growth_score + inflation_score) / 3

        # External assessment (0-100)
        reserve_score = min(100, d["reserves_months"] * 8)
        ca_score = min(100, max(0, 50 - abs(d["current_account_pct"]) * 5))
        ext_score = min(100, max(0, 100 - d["external_debt_pct"] * 0.5))
        external = (reserve_score + ca_score + ext_score) / 3

        # Fiscal assessment (0-100)
        debt_score = min(100, max(0, 100 - max(0, d["debt_to_gdp"] - 30) * 0.8))
        deficit_score = min(100, max(0, 100 - abs(d["deficit_to_gdp"]) * 8))
        primary_score = min(100, max(0, 60 + d["primary_balance"] * 5))
        fiscal = (debt_score + deficit_score + primary_score) / 3

        # Currency bonus
        currency_bonus = 8 if d.get("currency_reserve_status") else 0

        # Weighted score
        score = (
            inst * SP_WEIGHTS["institutional_assessment"] +
            econ * SP_WEIGHTS["economic_assessment"] +
            external * SP_WEIGHTS["external_assessment"] +
            fiscal * SP_WEIGHTS["fiscal_assessment"] +
            currency_bonus
        )

        rating = self._score_to_rating(score, "sp")
        current = d.get("sp_rating", "BBB")

        return RatingAssessment(
            agency="S&P",
            current_rating=current,
            simulated_rating=rating,
            rating_change=self._compute_change(current, rating, "sp"),
            score=round(score, 1),
            components={
                "institutional": round(inst, 1),
                "economic": round(econ, 1),
                "external": round(external, 1),
                "fiscal": round(fiscal, 1),
                "currency_bonus": currency_bonus,
            },
            key_drivers=self._get_drivers_sp(d, inst, econ, external, fiscal),
        )

    def _simulate_moodys(self, d: dict) -> RatingAssessment:
        """Simulate Moody's rating based on their published methodology."""
        # Economic strength (0-100)
        gdp_pc_score = min(100, d["gdp_per_capita"] / 800 * 2)
        growth_score = min(100, max(0, d["gdp_growth"] * 12 + 30))
        diversification = 60 if d["gdp_per_capita"] > 20000 else 40
        econ_strength = (gdp_pc_score + growth_score + diversification) / 3

        # Institutional strength (0-100)
        inst_strength = (d["institutions_score"] + d["rule_of_law"]) / 2

        # Fiscal strength (0-100)
        debt_score = min(100, max(0, 120 - d["debt_to_gdp"]))
        interest_burden = min(100, max(0, 100 - abs(d["deficit_to_gdp"] - d["primary_balance"]) * 8))
        fiscal_strength = (debt_score + interest_burden) / 2

        # Susceptibility to event risk (lower = better, inverted)
        event_risk = 100 - min(100, max(0, (
            abs(d["current_account_pct"]) * 5 +
            max(0, d["inflation"] - 3) * 5 +
            (100 - d["political_stability"]) * 0.3
        )))

        # Weighted score
        score = (
            econ_strength * MOODYS_WEIGHTS["economic_strength"] +
            inst_strength * MOODYS_WEIGHTS["institutional_strength"] +
            fiscal_strength * MOODYS_WEIGHTS["fiscal_strength"] +
            event_risk * MOODYS_WEIGHTS["susceptibility_to_event_risk"]
        )

        currency_bonus = 6 if d.get("currency_reserve_status") else 0
        score += currency_bonus

        rating = self._score_to_rating(score, "moodys")
        current = d.get("moodys_rating", "Baa2")

        return RatingAssessment(
            agency="Moody's",
            current_rating=current,
            simulated_rating=rating,
            rating_change=self._compute_change(current, rating, "moodys"),
            score=round(score, 1),
            components={
                "economic_strength": round(econ_strength, 1),
                "institutional_strength": round(inst_strength, 1),
                "fiscal_strength": round(fiscal_strength, 1),
                "event_risk_resistance": round(event_risk, 1),
                "currency_bonus": currency_bonus,
            },
            key_drivers=self._get_drivers_moodys(d, econ_strength, inst_strength, fiscal_strength, event_risk),
        )

    def _simulate_fitch(self, d: dict) -> RatingAssessment:
        """Simulate Fitch rating based on their published methodology."""
        # Macroeconomic performance (0-100)
        macro = (
            min(100, d["gdp_per_capita"] / 900 * 2) * 0.4 +
            min(100, max(0, d["gdp_growth"] * 15 + 20)) * 0.3 +
            min(100, max(0, 100 - d["inflation"] * 10)) * 0.3
        )

        # Public finances (0-100)
        pub_fin = (
            min(100, max(0, 110 - d["debt_to_gdp"])) * 0.5 +
            min(100, max(0, 100 - abs(d["deficit_to_gdp"]) * 8)) * 0.3 +
            min(100, max(0, 60 + d["primary_balance"] * 5)) * 0.2
        )

        # External finances (0-100)
        ext_fin = (
            min(100, d["reserves_months"] * 8) * 0.4 +
            min(100, max(0, 50 - abs(d["current_account_pct"]) * 5)) * 0.3 +
            min(100, max(0, 100 - d["external_debt_pct"] * 0.5)) * 0.3
        )

        # Structural features (0-100)
        structural = (
            d["institutions_score"] * 0.4 +
            d["rule_of_law"] * 0.3 +
            60 if d.get("currency_reserve_status") else 40 * 0.3
        )

        # Governance (0-100)
        governance = (d["institutions_score"] + d["rule_of_law"] + d["political_stability"]) / 3

        score = (
            macro * FITCH_WEIGHTS["macroeconomic_performance"] +
            pub_fin * FITCH_WEIGHTS["public_finances"] +
            ext_fin * FITCH_WEIGHTS["external_finances"] +
            structural * FITCH_WEIGHTS["structural_features"] +
            governance * FITCH_WEIGHTS["governance"]
        )

        rating = self._score_to_rating(score, "fitch")
        current = d.get("fitch_rating", "BBB")

        return RatingAssessment(
            agency="Fitch",
            current_rating=current,
            simulated_rating=rating,
            rating_change=self._compute_change(current, rating, "fitch"),
            score=round(score, 1),
            components={
                "macroeconomic": round(macro, 1),
                "public_finances": round(pub_fin, 1),
                "external_finances": round(ext_fin, 1),
                "structural_features": round(structural, 1),
                "governance": round(governance, 1),
            },
            key_drivers=self._get_drivers_fitch(d, macro, pub_fin, ext_fin),
        )

    def _score_to_rating(self, score: float, agency: str) -> str:
        if agency == "sp":
            scale = SP_SCALE
        elif agency == "moodys":
            scale = MOODYS_SCALE
        else:
            scale = FITCH_SCALE

        # Map score 0-100 to rating index
        idx = max(0, min(len(scale) - 1, int((100 - score) / 100 * len(scale))))
        return scale[idx]

    def _rating_to_score(self, rating: str, agency: str) -> float:
        if agency == "sp":
            scale = SP_SCALE
        elif agency == "moodys":
            scale = MOODYS_SCALE
        else:
            scale = FITCH_SCALE

        if rating in scale:
            idx = scale.index(rating)
            return 100 - (idx / len(scale) * 100)
        return 50.0

    def _compute_change(self, current: str, simulated: str, agency: str) -> str:
        current_score = self._rating_to_score(current, agency)
        simulated_score = self._rating_to_score(simulated, agency)
        diff = simulated_score - current_score
        if diff > 5:
            return "upgrade"
        elif diff < -5:
            return "downgrade"
        return "unchanged"

    def _get_drivers_sp(self, d, inst, econ, ext, fiscal) -> list:
        drivers = []
        if inst < 50:
            drivers.append({"metric": "institutional_assessment", "impact": "negative", "detail": "Weak institutional framework limits rating upside"})
        if d["debt_to_gdp"] > 80:
            drivers.append({"metric": "debt_level", "impact": "negative", "detail": f"Debt/GDP at {d['debt_to_gdp']}% constrains fiscal flexibility"})
        if d["gdp_growth"] > 4:
            drivers.append({"metric": "growth", "impact": "positive", "detail": f"Strong GDP growth ({d['gdp_growth']}%) supports rating"})
        if d["reserves_months"] > 12:
            drivers.append({"metric": "reserves", "impact": "positive", "detail": f"Adequate reserves ({d['reserves_months']} months) provide buffer"})
        if d["inflation"] > 10:
            drivers.append({"metric": "inflation", "impact": "negative", "detail": f"High inflation ({d['inflation']}%) erodes fiscal capacity"})
        if d.get("currency_reserve_status"):
            drivers.append({"metric": "reserve_currency", "impact": "positive", "detail": "Reserve currency status provides exceptional financing flexibility"})
        return drivers

    def _get_drivers_moodys(self, d, econ, inst, fiscal, event) -> list:
        drivers = []
        if econ < 40:
            drivers.append({"metric": "economic_strength", "impact": "negative", "detail": "Weak economic fundamentals constrain rating"})
        if d["institutions_score"] > 80:
            drivers.append({"metric": "institutional_strength", "impact": "positive", "detail": "Strong institutional framework supports creditworthiness"})
        if d["debt_to_gdp"] > 100:
            drivers.append({"metric": "fiscal_strength", "impact": "negative", "detail": f"High debt/GDP ({d['debt_to_gdp']}%) weakens fiscal profile"})
        if event < 50:
            drivers.append({"metric": "event_risk", "impact": "negative", "detail": "Elevated susceptibility to political and external shocks"})
        if d["primary_balance"] > 0:
            drivers.append({"metric": "primary_balance", "impact": "positive", "detail": "Primary surplus indicates fiscal discipline"})
        return drivers

    def _get_drivers_fitch(self, d, macro, pub, ext) -> list:
        drivers = []
        if macro > 70:
            drivers.append({"metric": "macro_performance", "impact": "positive", "detail": "Strong macroeconomic performance supports rating"})
        if d["debt_to_gdp"] > 80:
            drivers.append({"metric": "public_finances", "impact": "negative", "detail": f"Elevated debt/GDP ({d['debt_to_gdp']}%) pressures public finance assessment"})
        if ext < 40:
            drivers.append({"metric": "external_position", "impact": "negative", "detail": "Weak external position increases vulnerability"})
        if d["current_account_pct"] > 2:
            drivers.append({"metric": "current_account", "impact": "positive", "detail": f"Current account surplus ({d['current_account_pct']}%) supports external assessment"})
        return drivers

    def _assessment_to_dict(self, assessment: RatingAssessment) -> dict:
        return {
            "agency": assessment.agency,
            "current_rating": assessment.current_rating,
            "simulated_rating": assessment.simulated_rating,
            "change": assessment.rating_change,
            "score": assessment.score,
            "components": assessment.components,
            "key_drivers": assessment.key_drivers,
        }
