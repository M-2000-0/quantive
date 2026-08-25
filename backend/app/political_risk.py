"""Political Risk Model — The Factor That Kills Sovereign Portfolios.

Interest rate models fail because the biggest risk isn't rates — it's
politics. A government change, a coup, a sanctions regime, or a capital
controls event can wipe out portfolio value overnight.

Features:
- Regime stability scoring (democratic backsliding, coup risk)
- Government change probability modeling
- Capital controls risk assessment
- Geopolitical risk scoring (conflict proximity, alliances)
- Expropriation risk (resource nationalism, debt restructuring)
- Policy continuity assessment
- Political event impact simulation
"""

from __future__ import annotations

from dataclasses import dataclass

from app.country_data import get_country


@dataclass
class PoliticalRiskProfile:
    """Complete political risk profile for a country."""
    country_code: str
    country_name: str
    assessment_date: str

    # Overall scores
    political_risk_score: float     # 1-100 (100 = highest risk)
    political_risk_tier: str        # "low", "moderate", "elevated", "high", "critical"

    # Component scores
    regime_stability: float         # 1-100
    government_change_risk: float   # 1-100
    capital_controls_risk: float    # 1-100
    expropriation_risk: float       # 1-100
    conflict_risk: float            # 1-100
    sanctions_exposure: float       # 1-100
    policy_continuity: float        # 1-100 (higher = more stable)

    # Indicators
    democracy_index: float          # 0-10 (Freedom House)
    corruption_index: float         # 0-100 (CPI, higher = cleaner)
    press_freedom: float            # 0-100 (RSF, higher = freer)
    rule_of_law: float              # 0-100 (WJP)
    civil_unrest_index: float       # 0-100 (higher = more unrest)

    # Specific risks
    next_election_years: list[int]
    leadership_stability: str       # "stable", "transitioning", "uncertain", "contested"
    military_in_power: bool
    sanctions_lists: list[str]      # Which lists the country appears on

    # Event scenarios
    likely_events: list[dict]      # [{event, probability, timeline, impact}]
    recommendations: list[str]

    def to_dict(self) -> dict:
        return {
            "country_code": self.country_code,
            "country_name": self.country_name,
            "assessment_date": self.assessment_date,
            "overall": {
                "risk_score": round(self.political_risk_score, 1),
                "risk_tier": self.political_risk_tier,
            },
            "component_scores": {
                "regime_stability": round(self.regime_stability, 1),
                "government_change_risk": round(self.government_change_risk, 1),
                "capital_controls_risk": round(self.capital_controls_risk, 1),
                "expropriation_risk": round(self.expropriation_risk, 1),
                "conflict_risk": round(self.conflict_risk, 1),
                "sanctions_exposure": round(self.sanctions_exposure, 1),
                "policy_continuity": round(self.policy_continuity, 1),
            },
            "indicators": {
                "democracy_index": round(self.democracy_index, 1),
                "corruption_index": round(self.corruption_index, 1),
                "press_freedom": round(self.press_freedom, 1),
                "rule_of_law": round(self.rule_of_law, 1),
                "civil_unrest_index": round(self.civil_unrest_index, 1),
            },
            "context": {
                "next_election_years": self.next_election_years,
                "leadership_stability": self.leadership_stability,
                "military_in_power": self.military_in_power,
                "sanctions_lists": self.sanctions_lists,
            },
            "likely_events": self.likely_events,
            "recommendations": self.recommendations,
        }


# ══════════════════════════════════════════════════════════════════════
# POLITICAL RISK DATA (26 sovereigns — production uses live feeds)
# ══════════════════════════════════════════════════════════════════════

POLITICAL_RISK_DATA: dict[str, dict] = {
    "US": {
        "democracy_index": 7.8, "corruption_index": 69, "press_freedom": 71,
        "rule_of_law": 80, "civil_unrest_index": 25,
        "regime_stability": 65, "govt_change_risk": 30, "capital_controls": 5,
        "expropriation": 2, "conflict_risk": 15, "sanctions_exposure": 0,
        "policy_continuity": 70, "leadership": "stable", "military": False,
        "elections": [2026, 2028], "sanctions_lists": [],
        "events": [
            {"event": "Presidential transition", "probability": 0.15, "timeline": "2-4 years",
             "impact": "Moderate policy shifts possible, especially trade and sanctions"},
        ],
    },
    "GB": {
        "democracy_index": 8.3, "corruption_index": 71, "press_freedom": 78,
        "rule_of_law": 85, "civil_unrest_index": 20,
        "regime_stability": 75, "govt_change_risk": 25, "capital_controls": 3,
        "expropriation": 1, "conflict_risk": 10, "sanctions_exposure": 0,
        "policy_continuity": 75, "leadership": "stable", "military": False,
        "elections": [2025, 2029], "sanctions_lists": [],
        "events": [],
    },
    "JP": {
        "democracy_index": 8.1, "corruption_index": 73, "press_freedom": 74,
        "rule_of_law": 87, "civil_unrest_index": 8,
        "regime_stability": 85, "govt_change_risk": 20, "capital_controls": 3,
        "expropriation": 1, "conflict_risk": 10, "sanctions_exposure": 0,
        "policy_continuity": 85, "leadership": "stable", "military": False,
        "elections": [2025], "sanctions_lists": [],
        "events": [
            {"event": "BOJ policy normalization", "probability": 0.7, "timeline": "1-2 years",
             "impact": "Significant: end of yield curve control could spike JGB yields"},
        ],
    },
    "DE": {
        "democracy_index": 8.7, "corruption_index": 78, "press_freedom": 82,
        "rule_of_law": 90, "civil_unrest_index": 15,
        "regime_stability": 70, "govt_change_risk": 35, "capital_controls": 2,
        "expropriation": 1, "conflict_risk": 10, "sanctions_exposure": 0,
        "policy_continuity": 80, "leadership": "stable", "military": False,
        "elections": [2025, 2029], "sanctions_lists": [],
        "events": [
            {"event": "Coalition government instability", "probability": 0.3, "timeline": "1-3 years",
             "impact": "Moderate: policy gridlock possible on fiscal spending"},
        ],
    },
    "FR": {
        "democracy_index": 7.7, "corruption_index": 69, "press_freedom": 75,
        "rule_of_law": 78, "civil_unrest_index": 35,
        "regime_stability": 55, "govt_change_risk": 40, "capital_controls": 3,
        "expropriation": 3, "conflict_risk": 10, "sanctions_exposure": 0,
        "policy_continuity": 60, "leadership": "stable", "military": False,
        "elections": [2027], "sanctions_lists": [],
        "events": [
            {"event": "Parliamentary gridlock", "probability": 0.4, "timeline": "1-2 years",
             "impact": "Moderate: inability to pass fiscal consolidation"},
        ],
    },
    "IT": {
        "democracy_index": 7.6, "corruption_index": 56, "press_freedom": 71,
        "rule_of_law": 65, "civil_unrest_index": 30,
        "regime_stability": 55, "govt_change_risk": 45, "capital_controls": 5,
        "expropriation": 3, "conflict_risk": 10, "sanctions_exposure": 0,
        "policy_continuity": 55, "leadership": "stable", "military": False,
        "elections": [2028], "sanctions_lists": [],
        "events": [
            {"event": "Sovereign debt stress", "probability": 0.15, "timeline": "2-5 years",
             "impact": "High: BTP-Bund spread widening, potential ECB intervention"},
            {"event": "EU fiscal rule enforcement", "probability": 0.5, "timeline": "1-3 years",
             "impact": "Moderate: forced austerity could trigger political backlash"},
        ],
    },
    "CA": {
        "democracy_index": 8.9, "corruption_index": 74, "press_freedom": 82,
        "rule_of_law": 88, "civil_unrest_index": 15,
        "regime_stability": 80, "govt_change_risk": 25, "capital_controls": 2,
        "expropriation": 2, "conflict_risk": 5, "sanctions_exposure": 0,
        "policy_continuity": 80, "leadership": "stable", "military": False,
        "elections": [2025], "sanctions_lists": [],
        "events": [],
    },
    "CN": {
        "democracy_index": 2.0, "corruption_index": 45, "press_freedom": 10,
        "rule_of_law": 50, "civil_unrest_index": 20,
        "regime_stability": 80, "govt_change_risk": 5, "capital_controls": 85,
        "expropriation": 30, "conflict_risk": 25, "sanctions_exposure": 20,
        "policy_continuity": 85, "leadership": "stable", "military": False,
        "elections": [], "sanctions_lists": [],
        "events": [
            {"event": "Taiwan escalation", "probability": 0.10, "timeline": "5-10 years",
             "impact": "Catastrophic: sanctions, capital freeze, global market crash"},
            {"event": "Property sector contagion", "probability": 0.4, "timeline": "1-3 years",
             "impact": "High: growth slowdown, capital controls tightening"},
        ],
    },
    "IN": {
        "democracy_index": 5.0, "corruption_index": 40, "press_freedom": 35,
        "rule_of_law": 55, "civil_unrest_index": 30,
        "regime_stability": 70, "govt_change_risk": 20, "capital_controls": 40,
        "expropriation": 15, "conflict_risk": 25, "sanctions_exposure": 5,
        "policy_continuity": 70, "leadership": "stable", "military": False,
        "elections": [2029], "sanctions_lists": [],
        "events": [
            {"event": "Border conflict escalation", "probability": 0.2, "timeline": "2-5 years",
             "impact": "Moderate: INR depreciation, capital outflows"},
        ],
    },
    "BR": {
        "democracy_index": 6.9, "corruption_index": 38, "press_freedom": 55,
        "rule_of_law": 45, "civil_unrest_index": 35,
        "regime_stability": 50, "govt_change_risk": 35, "capital_controls": 20,
        "expropriation": 20, "conflict_risk": 20, "sanctions_exposure": 5,
        "policy_continuity": 50, "leadership": "stable", "military": False,
        "elections": [2026], "sanctions_lists": [],
        "events": [
            {"event": "Fiscal slippage", "probability": 0.4, "timeline": "1-2 years",
             "impact": "High: BRL depreciation, spread widening"},
        ],
    },
    "RU": {
        "democracy_index": 2.0, "corruption_index": 28, "press_freedom": 8,
        "rule_of_law": 25, "civil_unrest_index": 25,
        "regime_stability": 70, "govt_change_risk": 10, "capital_controls": 90,
        "expropriation": 60, "conflict_risk": 85, "sanctions_exposure": 95,
        "policy_continuity": 60, "leadership": "stable", "military": False,
        "elections": [2030], "sanctions_lists": ["OFAC", "EU", "UK"],
        "events": [
            {"event": "Escalation of Ukraine conflict", "probability": 0.3, "timeline": "1-3 years",
             "impact": "Critical: additional sanctions, full capital freeze"},
            {"event": "Sovereign debt restructuring", "probability": 0.2, "timeline": "3-5 years",
             "impact": "Critical: full loss for foreign bondholders"},
        ],
    },
    "AU": {
        "democracy_index": 8.9, "corruption_index": 77, "press_freedom": 79,
        "rule_of_law": 88, "civil_unrest_index": 12,
        "regime_stability": 85, "govt_change_risk": 20, "capital_controls": 2,
        "expropriation": 2, "conflict_risk": 5, "sanctions_exposure": 0,
        "policy_continuity": 85, "leadership": "stable", "military": False,
        "elections": [2025], "sanctions_lists": [],
        "events": [],
    },
    "KR": {
        "democracy_index": 7.1, "corruption_index": 62, "press_freedom": 60,
        "rule_of_law": 72, "civil_unrest_index": 20,
        "regime_stability": 70, "govt_change_risk": 25, "capital_controls": 15,
        "expropriation": 5, "conflict_risk": 40, "sanctions_exposure": 5,
        "policy_continuity": 70, "leadership": "stable", "military": False,
        "elections": [2027], "sanctions_lists": [],
        "events": [
            {"event": "DPRK provocation", "probability": 0.5, "timeline": "1-2 years",
             "impact": "Moderate: KRW depreciation, temporary market disruption"},
        ],
    },
    "MX": {
        "democracy_index": 6.3, "corruption_index": 31, "press_freedom": 50,
        "rule_of_law": 40, "civil_unrest_index": 35,
        "regime_stability": 55, "govt_change_risk": 30, "capital_controls": 15,
        "expropriation": 15, "conflict_risk": 35, "sanctions_exposure": 5,
        "policy_continuity": 50, "leadership": "stable", "military": False,
        "elections": [2030], "sanctions_lists": [],
        "events": [
            {"event": "USMCA renegotiation", "probability": 0.3, "timeline": "2-4 years",
             "impact": "High: trade disruption, MXN depreciation"},
        ],
    },
    "ZA": {
        "democracy_index": 7.1, "corruption_index": 43, "press_freedom": 60,
        "rule_of_law": 45, "civil_unrest_index": 50,
        "regime_stability": 40, "govt_change_risk": 45, "capital_controls": 30,
        "expropriation": 35, "conflict_risk": 30, "sanctions_exposure": 5,
        "policy_continuity": 35, "leadership": "contested", "military": False,
        "elections": [2029], "sanctions_lists": [],
        "events": [
            {"event": "Land reform escalation", "probability": 0.3, "timeline": "2-5 years",
             "impact": "High: expropriation risk, investor confidence collapse"},
            {"event": "Energy crisis deepening", "probability": 0.5, "timeline": "1-3 years",
             "impact": "Moderate: growth contraction, fiscal pressure"},
        ],
    },
    "SA": {
        "democracy_index": 2.0, "corruption_index": 52, "press_freedom": 8,
        "rule_of_law": 55, "civil_unrest_index": 15,
        "regime_stability": 75, "govt_change_risk": 10, "capital_controls": 20,
        "expropriation": 10, "conflict_risk": 35, "sanctions_exposure": 5,
        "policy_continuity": 80, "leadership": "stable", "military": False,
        "elections": [], "sanctions_lists": [],
        "events": [
            {"event": "Oil price collapse", "probability": 0.2, "timeline": "1-3 years",
             "impact": "High: fiscal deficit, SAR peg pressure"},
            {"event": "Regional conflict escalation", "probability": 0.15, "timeline": "2-5 years",
             "impact": "Critical: energy supply disruption, capital flight"},
        ],
    },
    "TR": {
        "democracy_index": 4.3, "corruption_index": 36, "press_freedom": 25,
        "rule_of_law": 35, "civil_unrest_index": 40,
        "regime_stability": 45, "govt_change_risk": 30, "capital_controls": 50,
        "expropriation": 25, "conflict_risk": 40, "sanctions_exposure": 15,
        "policy_continuity": 40, "leadership": "stable", "military": False,
        "elections": [2028], "sanctions_lists": [],
        "events": [
            {"event": "Currency crisis", "probability": 0.25, "timeline": "1-2 years",
             "impact": "High: TRY depreciation, capital controls tightening"},
        ],
    },
    "AR": {
        "democracy_index": 6.9, "corruption_index": 38, "press_freedom": 55,
        "rule_of_law": 35, "civil_unrest_index": 45,
        "regime_stability": 35, "govt_change_risk": 50, "capital_controls": 70,
        "expropriation": 40, "conflict_risk": 15, "sanctions_exposure": 5,
        "policy_continuity": 25, "leadership": "contested", "military": False,
        "elections": [2027], "sanctions_lists": [],
        "events": [
            {"event": "Sovereign default/restructuring", "probability": 0.2, "timeline": "2-5 years",
             "impact": "Critical: full loss for foreign bondholders"},
            {"event": "Capital controls reimposition", "probability": 0.35, "timeline": "1-3 years",
             "impact": "High: investor lock-in, currency collapse"},
        ],
    },
    "PL": {
        "democracy_index": 6.5, "corruption_index": 56, "press_freedom": 55,
        "rule_of_law": 55, "civil_unrest_index": 20,
        "regime_stability": 65, "govt_change_risk": 30, "capital_controls": 5,
        "expropriation": 5, "conflict_risk": 30, "sanctions_exposure": 0,
        "policy_continuity": 65, "leadership": "stable", "military": False,
        "elections": [2027], "sanctions_lists": [],
        "events": [
            {"event": "EU rule-of-law conflict", "probability": 0.3, "timeline": "1-3 years",
             "impact": "Moderate: EU fund suspension possible"},
        ],
    },
    "NL": {
        "democracy_index": 8.7, "corruption_index": 80, "press_freedom": 82,
        "rule_of_law": 90, "civil_unrest_index": 15,
        "regime_stability": 65, "govt_change_risk": 35, "capital_controls": 2,
        "expropriation": 1, "conflict_risk": 5, "sanctions_exposure": 0,
        "policy_continuity": 75, "leadership": "stable", "military": False,
        "elections": [2028], "sanctions_lists": [],
        "events": [],
    },
    "ES": {
        "democracy_index": 7.9, "corruption_index": 60, "press_freedom": 73,
        "rule_of_law": 68, "civil_unrest_index": 25,
        "regime_stability": 55, "govt_change_risk": 40, "capital_controls": 3,
        "expropriation": 3, "conflict_risk": 10, "sanctions_exposure": 0,
        "policy_continuity": 60, "leadership": "stable", "military": False,
        "elections": [2027], "sanctions_lists": [],
        "events": [
            {"event": "Catalan/separatist tension", "probability": 0.15, "timeline": "3-5 years",
             "impact": "Moderate: political instability, BTP spread widening"},
        ],
    },
    "SG": {
        "democracy_index": 4.9, "corruption_index": 83, "press_freedom": 45,
        "rule_of_law": 85, "civil_unrest_index": 5,
        "regime_stability": 90, "govt_change_risk": 5, "capital_controls": 10,
        "expropriation": 1, "conflict_risk": 5, "sanctions_exposure": 0,
        "policy_continuity": 90, "leadership": "stable", "military": False,
        "elections": [2030], "sanctions_lists": [],
        "events": [],
    },
    "NO": {
        "democracy_index": 9.8, "corruption_index": 84, "press_freedom": 90,
        "rule_of_law": 92, "civil_unrest_index": 8,
        "regime_stability": 90, "govt_change_risk": 15, "capital_controls": 2,
        "expropriation": 1, "conflict_risk": 5, "sanctions_exposure": 0,
        "policy_continuity": 90, "leadership": "stable", "military": False,
        "elections": [2025], "sanctions_lists": [],
        "events": [],
    },
    "SE": {
        "democracy_index": 9.4, "corruption_index": 83, "press_freedom": 88,
        "rule_of_law": 88, "civil_unrest_index": 18,
        "regime_stability": 75, "govt_change_risk": 25, "capital_controls": 2,
        "expropriation": 1, "conflict_risk": 10, "sanctions_exposure": 0,
        "policy_continuity": 75, "leadership": "stable", "military": False,
        "elections": [2026], "sanctions_lists": [],
        "events": [],
    },
    "CH": {
        "democracy_index": 9.1, "corruption_index": 82, "press_freedom": 88,
        "rule_of_law": 95, "civil_unrest_index": 5,
        "regime_stability": 95, "govt_change_risk": 5, "capital_controls": 5,
        "expropriation": 1, "conflict_risk": 2, "sanctions_exposure": 0,
        "policy_continuity": 95, "leadership": "stable", "military": False,
        "elections": [2027], "sanctions_lists": [],
        "events": [],
    },
}


class PoliticalRiskModel:
    """Models political risk for sovereign debt portfolios.

    Combines multiple political risk factors into a composite score
    and generates actionable intelligence for portfolio managers.
    """

    def analyze_country(self, country_code: str) -> PoliticalRiskProfile:
        """Generate a complete political risk profile for a country."""
        from datetime import datetime, timezone

        code = country_code.upper()
        data = POLITICAL_RISK_DATA.get(code)
        country = get_country(code)

        if not data:
            # Default risk profile for countries without specific data
            data = {
                "democracy_index": 4.0, "corruption_index": 35, "press_freedom": 35,
                "rule_of_law": 40, "civil_unrest_index": 40,
                "regime_stability": 40, "govt_change_risk": 50, "capital_controls": 30,
                "expropriation": 20, "conflict_risk": 30, "sanctions_exposure": 10,
                "policy_continuity": 40, "leadership": "uncertain", "military": False,
                "elections": [], "sanctions_lists": [],
                "events": [{"event": "Political instability", "probability": 0.3,
                           "timeline": "2-5 years", "impact": "Moderate to high uncertainty"}],
            }

        name = country.name if country else code

        # Compute composite political risk score (0-100, higher = riskier)
        # Weights: regime stability (20%), govt change (15%), capital controls (15%),
        #          expropriation (15%), conflict (15%), sanctions (10%), unrest (10%)
        composite = (
            (100 - data["regime_stability"]) * 0.20 +
            data["govt_change_risk"] * 0.15 +
            data["capital_controls"] * 0.15 +
            data["expropriation"] * 0.15 +
            data["conflict_risk"] * 0.15 +
            data["sanctions_exposure"] * 0.10 +
            data["civil_unrest_index"] * 0.10
        )

        # Tier classification
        if composite < 20:
            tier = "low"
        elif composite < 40:
            tier = "moderate"
        elif composite < 60:
            tier = "elevated"
        elif composite < 80:
            tier = "high"
        else:
            tier = "critical"

        # Recommendations
        recs = []
        if data["capital_controls"] > 50:
            recs.append(
                "HIGH capital controls risk. Consider reducing foreign-currency exposure "
                "and maintaining liquidity buffers outside the jurisdiction."
            )
        if data["expropriation"] > 30:
            recs.append(
                "Elevated expropriation risk. Limit direct investment and prefer "
                "sovereign bonds over quasi-sovereign or corporate exposure."
            )
        if data["conflict_risk"] > 40:
            recs.append(
                "Significant conflict risk. Maintain hedging via CDS and consider "
                "geographic diversification away from conflict zones."
            )
        if data["sanctions_exposure"] > 50:
            recs.append(
                "SANCTIONS EXPOSURE DETECTED. Screen all instruments and counterparties "
                "before trading. Ensure compliance with OFAC/EU regulations."
            )
        if data["policy_continuity"] < 40:
            recs.append(
                "Low policy continuity. Prepare for potential regime policy shifts "
                "that could affect debt management, fiscal policy, or investor access."
            )
        if data["civil_unrest_index"] > 40:
            recs.append(
                "Elevated civil unrest. Monitor for protests, strikes, or political "
                "crises that could disrupt debt service or market access."
            )
        if composite < 30:
            recs.append(
                "Political risk profile is manageable. Standard monitoring sufficient."
            )

        return PoliticalRiskProfile(
            country_code=code,
            country_name=name,
            assessment_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            political_risk_score=round(composite, 1),
            political_risk_tier=tier,
            regime_stability=float(data["regime_stability"]),
            government_change_risk=float(data["govt_change_risk"]),
            capital_controls_risk=float(data["capital_controls"]),
            expropriation_risk=float(data["expropriation"]),
            conflict_risk=float(data["conflict_risk"]),
            sanctions_exposure=float(data["sanctions_exposure"]),
            policy_continuity=float(data["policy_continuity"]),
            democracy_index=float(data["democracy_index"]),
            corruption_index=float(data["corruption_index"]),
            press_freedom=float(data["press_freedom"]),
            rule_of_law=float(data["rule_of_law"]),
            civil_unrest_index=float(data["civil_unrest_index"]),
            next_election_years=data["elections"],
            leadership_stability=data["leadership"],
            military_in_power=data["military"],
            sanctions_lists=data["sanctions_lists"],
            likely_events=data["events"],
            recommendations=recs,
        )

    def portfolio_political_risk(self, instruments: list[dict]) -> dict:
        """Assess political risk for a portfolio based on country exposures."""
        # Aggregate country exposures
        country_exposures: dict[str, float] = {}
        for inst in instruments:
            country = inst.get("issuer_country", "US").upper()
            principal = inst.get("principal_outstanding", 0)
            country_exposures[country] = country_exposures.get(country, 0) + principal

        total = sum(country_exposures.values()) or 1

        # Analyze each country
        profiles = {}
        weighted_risk = 0
        for country, exposure in country_exposures.items():
            profile = self.analyze_country(country)
            profiles[country] = profile.to_dict()
            weighted_risk += profile.political_risk_score * (exposure / total)

        # Concentration risk
        shares = [(exposure / total) ** 2 for exposure in country_exposures.values()]
        hhi = sum(shares) * 10000

        return {
            "total_exposure_usd": round(total, 0),
            "weighted_political_risk": round(weighted_risk, 1),
            "concentration_hhi": round(hhi, 0),
            "country_breakdown": {
                code: {
                    "exposure_usd": round(exp, 0),
                    "exposure_pct": round(exp / total * 100, 1),
                    "risk_score": profiles[code]["overall"]["risk_score"],
                    "risk_tier": profiles[code]["overall"]["risk_tier"],
                }
                for code, exp in country_exposures.items()
            },
            "country_profiles": profiles,
        }


# ── Convenience Functions ──────────────────────────────────────────────

def analyze_political_risk(country_code: str) -> dict:
    """Analyze political risk for a country and return result as dict."""
    model = PoliticalRiskModel()
    return model.analyze_country(country_code).to_dict()


def portfolio_political_risk(instruments: list[dict]) -> dict:
    """Analyze portfolio political risk and return result as dict."""
    model = PoliticalRiskModel()
    return model.portfolio_political_risk(instruments)
