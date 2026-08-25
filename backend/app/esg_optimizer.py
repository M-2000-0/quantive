"""Green Bond / ESG Optimizer.

Extends the core optimization engine with climate-aware decision making:
- ESG scores for sovereign debt instruments
- Green bond eligibility assessment
- Carbon pricing integration
- Climate risk-weighted optimization
- Sustainability reporting aligned with EU Taxonomy / ICMA Green Bond Principles

This enables Quantive to serve the rapidly growing sustainable finance market.
"""

from dataclasses import dataclass, field

# ESG scores by country (source: composite from MSCI, Sustainalytics, World Bank governance indicators)
# Scale: 0-100 (higher = better)
COUNTRY_ESG_SCORES: dict[str, dict] = {
    "US": {"environmental": 55, "social": 65, "governance": 75, "overall": 65, "climate_var": 0.02},
    "UK": {"environmental": 62, "social": 68, "governance": 80, "overall": 70, "climate_var": 0.015},
    "DE": {"environmental": 72, "social": 70, "governance": 85, "overall": 76, "climate_var": 0.012},
    "FR": {"environmental": 68, "social": 65, "governance": 78, "overall": 70, "climate_var": 0.014},
    "JP": {"environmental": 58, "social": 60, "governance": 72, "overall": 63, "climate_var": 0.018},
    "CA": {"environmental": 60, "social": 70, "governance": 82, "overall": 71, "climate_var": 0.02},
    "AU": {"environmental": 48, "social": 68, "governance": 80, "overall": 65, "climate_var": 0.025},
    "CN": {"environmental": 42, "social": 50, "governance": 45, "overall": 46, "climate_var": 0.03},
    "IN": {"environmental": 38, "social": 45, "governance": 50, "overall": 44, "climate_var": 0.035},
    "BR": {"environmental": 40, "social": 48, "governance": 42, "overall": 43, "climate_var": 0.028},
    "KR": {"environmental": 52, "social": 55, "governance": 65, "overall": 57, "climate_var": 0.02},
    "MX": {"environmental": 45, "social": 48, "governance": 45, "overall": 46, "climate_var": 0.025},
    "ZA": {"environmental": 35, "social": 40, "governance": 38, "overall": 38, "climate_var": 0.04},
    "SA": {"environmental": 30, "social": 35, "governance": 30, "overall": 32, "climate_var": 0.035},
    "RU": {"environmental": 35, "social": 42, "governance": 25, "overall": 34, "climate_var": 0.03},
    "ID": {"environmental": 38, "social": 45, "governance": 42, "overall": 42, "climate_var": 0.03},
    "TR": {"environmental": 40, "social": 42, "governance": 38, "overall": 40, "climate_var": 0.025},
    "CH": {"environmental": 78, "social": 72, "governance": 90, "overall": 80, "climate_var": 0.008},
    "SE": {"environmental": 82, "social": 75, "governance": 88, "overall": 82, "climate_var": 0.008},
    "NO": {"environmental": 75, "social": 78, "governance": 90, "overall": 81, "climate_var": 0.01},
    "SG": {"environmental": 65, "social": 62, "governance": 85, "overall": 71, "climate_var": 0.015},
    "NL": {"environmental": 70, "social": 68, "governance": 85, "overall": 74, "climate_var": 0.012},
    "IT": {"environmental": 52, "social": 55, "governance": 58, "overall": 55, "climate_var": 0.018},
    "ES": {"environmental": 58, "social": 58, "governance": 65, "overall": 60, "climate_var": 0.016},
    "PL": {"environmental": 42, "social": 52, "governance": 55, "overall": 50, "climate_var": 0.022},
    "AR": {"environmental": 40, "social": 42, "governance": 30, "overall": 37, "climate_var": 0.02},
}

# Green bond eligibility criteria (ICMA Green Bond Principles aligned)
GREEN_BOND_CRITERIA = {
    "eligible_categories": [
        "renewable_energy",
        "energy_efficiency",
        "clean_transport",
        "sustainable_water",
        "pollution_prevention",
        "ecosystem_conservation",
        "green_buildings",
        "climate_adaptation",
    ],
    "proceeds_tracking": True,
    "external_review_required": True,
    "annual_reporting_required": True,
    "coupon_premium_bps": 5,  # typical green bond premium
}

# Carbon price scenarios ($/tonne CO2 equivalent)
CARBON_PRICE_SCENARIOS = {
    "current": 25,
    "moderate_2030": 75,
    "aggressive_2030": 150,
    "net_zero_2050": 250,
}

# Country carbon intensity (tonnes CO2 per $1M GDP)
CARBON_INTENSITY: dict[str, float] = {
    "US": 150, "UK": 95, "DE": 120, "FR": 85, "JP": 130,
    "CA": 170, "AU": 190, "CN": 350, "IN": 280, "BR": 120,
    "KR": 210, "MX": 160, "ZA": 320, "SA": 400, "RU": 280,
    "ID": 150, "TR": 180, "CH": 60, "SE": 45, "NO": 55,
    "SG": 130, "NL": 110, "IT": 105, "ES": 100, "PL": 240, "AR": 140,
}


@dataclass
class ESGInstrumentScore:
    instrument_id: str
    instrument_name: str
    currency: str
    country: str
    principal: float
    esg_score: float
    environmental: float
    social: float
    governance: float
    is_green_eligible: bool
    green_categories: list = field(default_factory=list)
    carbon_risk_score: float = 0.0
    climate_var_adjustment: float = 0.0


class ESGScoringEngine:
    """Scores debt instruments on ESG and climate metrics."""

    def __init__(self, instruments: list[dict], country_code: str = "US"):
        self.instruments = instruments
        self.country_code = country_code.upper()
        self.country_esg = COUNTRY_ESG_SCORES.get(self.country_code, {
            "environmental": 50, "social": 50, "governance": 50, "overall": 50, "climate_var": 0.025
        })

    def score_instruments(self) -> dict:
        """Score all instruments and assess green bond eligibility."""
        scores = []
        total_principal = 0.0
        green_principal = 0.0
        avg_esg_weighted = 0.0
        total_carbon_risk = 0.0

        for inst in self.instruments:
            score = self._score_single(inst)
            scores.append(score)
            total_principal += inst.get("principal_outstanding", 0)
            avg_esg_weighted += score.esg_score * inst.get("principal_outstanding", 0)
            total_carbon_risk += score.carbon_risk_score * inst.get("principal_outstanding", 0)
            if score.is_green_eligible:
                green_principal += inst.get("principal_outstanding", 0)

        avg_esg = avg_esg_weighted / total_principal if total_principal > 0 else 0
        avg_carbon_risk = total_carbon_risk / total_principal if total_principal > 0 else 0
        green_pct = (green_principal / total_principal * 100) if total_principal > 0 else 0

        # Carbon price impact analysis
        carbon_impacts = {}
        for scenario, price in CARBON_PRICE_SCENARIOS.items():
            carbon_intensity = CARBON_INTENSITY.get(self.country_code, 200)
            annual_carbon_cost = total_principal * carbon_intensity * price / 1e6
            carbon_impacts[scenario] = {
                "carbon_price_per_tonne": price,
                "estimated_annual_cost": round(annual_carbon_cost, 2),
                "cost_as_pct_of_debt": round(annual_carbon_cost / total_principal * 100, 3) if total_principal > 0 else 0,
            }

        # Climate risk rating
        climate_var = self.country_esg.get("climate_var", 0.025)
        climate_rating = (
            "AAA" if climate_var < 0.01 else
            "AA" if climate_var < 0.015 else
            "A" if climate_var < 0.02 else
            "BBB" if climate_var < 0.025 else
            "BB" if climate_var < 0.03 else
            "B" if climate_var < 0.04 else
            "CCC"
        )

        return {
            "country": self.country_code,
            "country_esg": self.country_esg,
            "instrument_scores": [self._inst_to_dict(s) for s in scores],
            "summary": {
                "total_instruments": len(self.instruments),
                "total_principal": total_principal,
                "green_eligible_principal": green_principal,
                "green_eligible_pct": round(green_pct, 1),
                "weighted_avg_esg": round(avg_esg, 1),
                "weighted_avg_carbon_risk": round(avg_carbon_risk, 1),
                "climate_risk_rating": climate_rating,
                "climate_var": climate_var,
            },
            "carbon_price_impacts": carbon_impacts,
            "recommendations": self._generate_recommendations(scores, green_pct, avg_esg),
        }

    def _score_single(self, inst: dict) -> ESGInstrumentScore:
        inst_type = inst.get("instrument_type", "")
        name = inst.get("name", "").lower()
        principal = inst.get("principal_outstanding", 0)

        # Base ESG from country
        env = self.country_esg["environmental"]
        soc = self.country_esg["social"]
        gov = self.country_esg["governance"]

        # Adjust for instrument type
        if "inflation" in inst_type:
            env -= 2  # inflation-linked often tied to fossil-fuel-producing economies
        if "green" in name or "sustainab" in name:
            env += 15
            gov += 5
        if "concessional" in inst_type:
            soc += 10  # concessional loans often for development

        # Green bond eligibility
        is_green = False
        green_cats = []
        green_keywords = {
            "renewable_energy": ["solar", "wind", "green", "clean", "renewable"],
            "energy_efficiency": ["efficiency", "retrofit", "insulation"],
            "clean_transport": ["rail", "transit", "electric", "metro"],
            "green_buildings": ["building", "construction", "green"],
            "climate_adaptation": ["adaptation", "resilience", "flood"],
        }
        for category, keywords in green_keywords.items():
            if any(kw in name for kw in keywords):
                is_green = True
                green_cats.append(category)

        # Carbon risk
        carbon_intensity = CARBON_INTENSITY.get(self.country_code, 200)
        carbon_risk = min(100, carbon_intensity / 4)  # normalize to 0-100

        # Climate VaR adjustment
        climate_var_adj = self.country_esg.get("climate_var", 0.025)

        esg_score = (env + soc + gov) / 3

        return ESGInstrumentScore(
            instrument_id=inst.get("id", ""),
            instrument_name=inst.get("name", ""),
            currency=inst.get("currency", "USD"),
            country=self.country_code,
            principal=principal,
            esg_score=round(esg_score, 1),
            environmental=round(min(100, max(0, env)), 1),
            social=round(min(100, max(0, soc)), 1),
            governance=round(min(100, max(0, gov)), 1),
            is_green_eligible=is_green,
            green_categories=green_cats,
            carbon_risk_score=round(carbon_risk, 1),
            climate_var_adjustment=climate_var_adj,
        )

    def _inst_to_dict(self, score: ESGInstrumentScore) -> dict:
        return {
            "instrument_id": score.instrument_id,
            "instrument_name": score.instrument_name,
            "currency": score.currency,
            "country": score.country,
            "principal": score.principal,
            "esg_score": score.esg_score,
            "environmental": score.environmental,
            "social": score.social,
            "governance": score.governance,
            "is_green_eligible": score.is_green_eligible,
            "green_categories": score.green_categories,
            "carbon_risk_score": score.carbon_risk_score,
            "climate_var_adjustment": score.climate_var_adjustment,
        }

    def _generate_recommendations(self, scores: list, green_pct: float, avg_esg: float) -> list[dict]:
        recs = []

        if green_pct < 10:
            recs.append({
                "type": "low_green_allocation",
                "severity": "high",
                "message": f"Only {green_pct:.0f}% of portfolio is green-eligible. Target 15-30% for ESG compliance.",
                "action": "Issue new green bonds or designate existing eligible instruments.",
            })

        if avg_esg < 50:
            recs.append({
                "type": "low_esg_score",
                "severity": "high",
                "message": f"Weighted ESG score is {avg_esg:.0f}/100. This may trigger exclusion from ESG indices.",
                "action": "Diversify into higher-rated sovereign issuers or increase green bond allocation.",
            })

        high_carbon = [s for s in scores if s.carbon_risk_score > 60]
        if high_carbon:
            total_high = sum(s.principal for s in high_carbon)
            recs.append({
                "type": "carbon_exposure",
                "severity": "medium",
                "message": (
                    f"{len(high_carbon)} instruments in high carbon-risk jurisdictions "
                    f"(${total_high / 1e9:.1f}B total)."
                ),
                "action": "Consider reducing exposure to high-carbon economies or offset with green investments.",
            })

        # EU Taxonomy alignment
        if green_pct < 30:
            recs.append({
                "type": "eu_taxonomy",
                "severity": "medium",
                "message": (
                    f"Portfolio is {green_pct:.0f}% green-aligned. "
                    f"EU Taxonomy requires 30%+ for 'sustainable' classification."
                ),
                "action": "Increase green bond allocation to meet EU Taxonomy thresholds.",
            })

        # ICMA Green Bond Principles
        non_green = [s for s in scores if not s.is_green_eligible]
        if non_green and green_pct > 0:
            recs.append({
                "type": "proceeds_allocation",
                "severity": "low",
                "message": "Ensure green bond proceeds are tracked and allocated per ICMA GBP.",
                "action": "Implement annual green bond reporting with external review.",
            })

        return recs


class ESGConstrainedOptimizer:
    """Extends core optimizer with ESG/climate constraints."""

    @staticmethod
    def add_esg_constraints(base_constraints: dict, esg_config: dict) -> dict:
        """Merge ESG constraints into existing optimization constraints."""
        enhanced = dict(base_constraints)

        min_esg_score = esg_config.get("min_esg_score", 0)
        if min_esg_score > 0:
            enhanced["min_esg_score"] = min_esg_score

        max_carbon_risk = esg_config.get("max_carbon_risk", 100)
        enhanced["max_carbon_risk"] = max_carbon_risk

        min_green_pct = esg_config.get("min_green_pct", 0)
        if min_green_pct > 0:
            enhanced["min_green_pct"] = min_green_pct

        carbon_price_scenario = esg_config.get("carbon_price_scenario")
        if carbon_price_scenario:
            price = CARBON_PRICE_SCENARIOS.get(carbon_price_scenario, 0)
            enhanced["carbon_price_per_tonne"] = price

        return enhanced

    @staticmethod
    def esg_adjusted_objective(
        instruments: list[dict],
        base_objective: dict,
        esg_config: dict,
    ) -> dict:
        """Create ESG-weighted objective function parameters."""
        enhanced = dict(base_objective)

        esg_weight = esg_config.get("esg_weight", 0.0)  # 0-1, how much to weight ESG
        if esg_weight > 0:
            enhanced["esg_weight"] = esg_weight
            enhanced["climate_risk_weight"] = esg_config.get("climate_risk_weight", esg_weight * 0.5)

        carbon_penalty = esg_config.get("carbon_penalty_bps", 0)
        if carbon_penalty > 0:
            enhanced["carbon_penalty_bps"] = carbon_penalty

        green_premium = esg_config.get("green_premium_bps", GREEN_BOND_CRITERIA["coupon_premium_bps"])
        enhanced["green_premium_bps"] = green_premium

        return enhanced
