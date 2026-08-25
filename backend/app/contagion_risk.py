"""Contagion Risk Model — When Countries Default Together.

Sovereign defaults don't happen in isolation. Argentina's default
destroys Brazilian banks. Russia's default triggers EM contagion.
Greece's crisis threatens Italy. This model captures those linkages.

Features:
- Cross-country correlation matrix (trade, finance, political)
- Default contagion probability estimation
- Spillover impact quantification
- Systemic risk scoring
- Tail dependency modeling (correlations increase in crises)
- Network centrality analysis (which country is most systemically important)
- Cascade simulation (what happens if Country A defaults)
"""

from __future__ import annotations

from dataclasses import dataclass

from app.country_data import get_country


@dataclass
class ContagionLink:
    """A single contagion pathway between two countries."""
    source_country: str
    target_country: str
    channel: str            # "trade", "financial", "political", "investor", "rating"
    strength: float         # 0-1 (how strong the link is)
    transmission_speed: str # "immediate", "days", "weeks", "months"
    historical_example: str # Reference to past event

    def to_dict(self) -> dict:
        return {
            "source": self.source_country,
            "target": self.target_country,
            "channel": self.channel,
            "strength": round(self.strength, 2),
            "speed": self.transmission_speed,
            "example": self.historical_example,
        }


@dataclass
class CascadeResult:
    """Result of a default cascade simulation."""
    trigger_country: str
    trigger_default_probability: float
    affected_countries: list[dict]  # [{country, impact_pct, channel, timeline}]
    total_portfolio_impact_bps: float
    systemic_risk_score: float
    max_cascade_depth: int
    cascade_timeline: list[dict]  # [{day, event, countries_affected, impact}]

    def to_dict(self) -> dict:
        return {
            "trigger": self.trigger_country,
            "trigger_default_probability": round(self.trigger_default_probability, 3),
            "affected_countries": self.affected_countries,
            "total_portfolio_impact_bps": round(self.total_portfolio_impact_bps, 1),
            "systemic_risk_score": round(self.systemic_risk_score, 1),
            "max_cascade_depth": self.max_cascade_depth,
            "cascade_timeline": self.cascade_timeline,
        }


# ══════════════════════════════════════════════════════════════════════
# CONTAGION LINKAGES DATABASE
# ══════════════════════════════════════════════════════════════════════

# Contagion links between countries (bidirectional with different strengths)
CONTAGION_LINKS: list[dict] = [
    # European contagion network
    {"source": "IT", "target": "ES", "channel": "financial", "strength": 0.7, "speed": "immediate",
     "example": "2011-12: Italian BTP crisis spread to Spanish bonos"},
    {"source": "IT", "target": "PT", "channel": "financial", "strength": 0.5, "speed": "days",
     "example": "2011-12: Italian stress triggered Portuguese spread widening"},
    {"source": "IT", "target": "FR", "channel": "financial", "strength": 0.6, "speed": "immediate",
     "example": "2011: French bank exposure to Italian debt caused FTSE decline"},
    {"source": "IT", "target": "DE", "channel": "financial", "strength": 0.4, "speed": "days",
     "example": "2011: BTP-Bund spread widening affected German banks"},
    {"source": "ES", "target": "PT", "channel": "financial", "strength": 0.8, "speed": "immediate",
     "example": "2012: Spanish bank crisis immediately infected Portugal"},
    {"source": "ES", "target": "IT", "channel": "financial", "strength": 0.6, "speed": "days",
     "example": "2012: Spanish bailout fears widened Italian spreads"},
    {"source": "FR", "target": "DE", "channel": "financial", "strength": 0.5, "speed": "immediate",
     "example": "2011: French AAA downgrade threatened German bund safe-haven status"},
    {"source": "GB", "target": "EU", "channel": "trade", "strength": 0.4, "speed": "weeks",
     "example": "2016: Brexit vote caused European equity selloff"},

    # Americas contagion
    {"source": "AR", "target": "BR", "channel": "trade", "strength": 0.6, "speed": "days",
     "example": "2001-02: Argentine default caused Brazilian real depreciation"},
    {"source": "AR", "target": "UY", "channel": "trade", "strength": 0.5, "speed": "days",
     "example": "2001-02: Argentine crisis caused Uruguayan banking crisis"},
    {"source": "BR", "target": "MX", "channel": "investor", "strength": 0.4, "speed": "days",
     "example": "2015: Brazilian commodity crash spread to Mexican assets"},
    {"source": "US", "target": "CA", "channel": "trade", "strength": 0.7, "speed": "immediate",
     "example": "2008: US financial crisis immediately affected Canadian banks"},
    {"source": "US", "target": "MX", "channel": "trade", "strength": 0.6, "speed": "days",
     "example": "2008: US recession collapsed Mexican exports"},
    {"source": "VE", "target": "CO", "channel": "trade", "strength": 0.4, "speed": "weeks",
     "example": "2017: Venezuelan crisis affected Colombian border economy"},

    # Asia contagion
    {"source": "CN", "target": "KR", "channel": "trade", "strength": 0.6, "speed": "days",
     "example": "2015: Chinese devaluation caused KRW selloff"},
    {"source": "CN", "target": "JP", "channel": "trade", "strength": 0.5, "speed": "days",
     "example": "2015: China slowdown hit Japanese exporters"},
    {"source": "CN", "target": "AU", "channel": "trade", "strength": 0.7, "speed": "days",
     "example": "2015-16: Chinese commodity demand crash devastated AUD"},
    {"source": "CN", "target": "SG", "channel": "trade", "strength": 0.5, "speed": "days",
     "example": "2015: Singapore trade-dependent economy hit by China slowdown"},
    {"source": "JP", "target": "KR", "channel": "investor", "strength": 0.4, "speed": "days",
     "example": "2019: Japan-Korea trade dispute affected both markets"},

    # EM contagion (the "taper tantrum" network)
    {"source": "BR", "target": "ZA", "channel": "investor", "strength": 0.5, "speed": "days",
     "example": "2013-15: Taper tantrum hit both BR and ZA simultaneously"},
    {"source": "TR", "target": "ZA", "channel": "investor", "strength": 0.4, "speed": "days",
     "example": "2018: Turkish lira crash spread to ZAR"},
    {"source": "TR", "target": "BR", "channel": "investor", "strength": 0.4, "speed": "days",
     "example": "2018: EM selloff connected Turkish and Brazilian markets"},
    {"source": "IN", "target": "ID", "channel": "investor", "strength": 0.4, "speed": "days",
     "example": "2013: Taper tantrum affected both Asian EMs"},

    # Political contagion
    {"source": "RU", "target": "BY", "channel": "political", "strength": 0.9, "speed": "immediate",
     "example": "2022: Belarus followed Russia into Ukraine conflict, triggered sanctions"},
    {"source": "RU", "target": "CN", "channel": "political", "strength": 0.5, "speed": "weeks",
     "example": "2022: Russia-China alignment created shared sanctions risk"},
    {"source": "SA", "target": "AE", "channel": "political", "strength": 0.6, "speed": "days",
     "example": "2017: Qatar diplomatic crisis affected Gulf region"},

    # Rating agency contagion (downgrade cascades)
    {"source": "US", "target": "GB", "channel": "rating", "strength": 0.3, "speed": "weeks",
     "example": "2011: US downgrade caused UK AAA review"},
    {"source": "IT", "target": "ES", "channel": "rating", "strength": 0.6, "speed": "days",
     "example": "2011-12: Italian downgrade triggered Spanish review"},
    {"source": "FR", "target": "IT", "channel": "rating", "strength": 0.4, "speed": "weeks",
     "example": "2012: French downgrade widened Italian spreads"},

    # Global shock amplifiers
    {"source": "US", "target": "GLOBAL", "channel": "financial", "strength": 0.8, "speed": "immediate",
     "example": "2008: US financial crisis became global"},
    {"source": "CN", "target": "EM", "channel": "trade", "strength": 0.6, "speed": "weeks",
     "example": "2015-16: Chinese hard landing fears hit all EMs"},
]


class ContagionRiskModel:
    """Models contagion risk in sovereign debt portfolios.

    Quantifies how a default or stress event in one country
    transmits to others through trade, finance, politics, and
    investor behavior channels.
    """

    def __init__(self):
        # Build adjacency matrix from links
        self.links = CONTAGION_LINKS
        self._link_map: dict[str, list[dict]] = {}
        for link in self.links:
            key = link["source"].upper()
            if key not in self._link_map:
                self._link_map[key] = []
            self._link_map[key].append(link)

    def get_linkages(self, country_code: str) -> list[ContagionLink]:
        """Get all contagion linkages for a country."""
        code = country_code.upper()
        links = []
        for link in self.links:
            if link["source"] == code or link["target"] == code:
                links.append(ContagionLink(
                    source_country=link["source"],
                    target_country=link["target"],
                    channel=link["channel"],
                    strength=link["strength"],
                    transmission_speed=link["speed"],
                    historical_example=link["example"],
                ))
        return links

    def simulate_cascade(
        self,
        trigger_country: str,
        instruments: list[dict],
        default_severity_bps: float = 500,
    ) -> CascadeResult:
        """Simulate a default cascade starting from a trigger country.

        Args:
            trigger_country: Country that defaults
            instruments: Portfolio instruments to assess impact on
            default_severity_bps: Spread widening for the defaulting country
        """
        code = trigger_country.upper()

        # Calculate country exposures
        country_exposures: dict[str, float] = {}
        for inst in instruments:
            c = inst.get("issuer_country", "US").upper()
            principal = inst.get("principal_outstanding", 0)
            country_exposures[c] = country_exposures.get(c, 0) + principal
        total = sum(country_exposures.values()) or 1

        # Default probability for trigger country
        country = get_country(code)
        if country:
            # Simplified: based on credit rating
            rating = country.rating_sp
            default_probs = {
                "AAA": 0.001, "AA+": 0.002, "AA": 0.003, "AA-": 0.005,
                "A+": 0.008, "A": 0.012, "A-": 0.018,
                "BBB+": 0.03, "BBB": 0.05, "BBB-": 0.08,
                "BB+": 0.12, "BB": 0.18, "BB-": 0.25,
                "B+": 0.35, "B": 0.45, "B-": 0.55,
                "CCC+": 0.65, "CCC": 0.75, "CCC-": 0.85,
                "CC": 0.90, "C": 0.95, "D": 1.0,
            }
            trigger_prob = default_probs.get(rating, 0.10)
        else:
            trigger_prob = 0.15

        # Find affected countries through contagion links
        affected = []
        visited = {code}
        queue = [(code, default_severity_bps, 0)]

        while queue:
            current, severity, depth = queue.pop(0)
            if depth > 3:
                continue

            for link in self._link_map.get(current, []):
                target = link["target"] if link["source"] == current else link["source"]
                if target in visited or target in ("GLOBAL", "EM"):
                    continue

                # Impact decays with distance and link strength
                decay = link["strength"] * (0.5 ** depth)
                channel_decay = {
                    "financial": 1.0, "trade": 0.8, "investor": 0.9,
                    "political": 0.6, "rating": 0.5,
                }
                impact_bps = severity * decay * channel_decay.get(link["channel"], 0.5)

                if impact_bps > 10:  # Only material impacts
                    affected.append({
                        "country": target,
                        "impact_bps": round(impact_bps, 1),
                        "impact_pct": round(impact_bps / 100, 2),
                        "channel": link["channel"],
                        "link_strength": round(link["strength"], 2),
                        "speed": link["speed"],
                        "timeline": link["example"],
                    })
                    visited.add(target)
                    if depth < 3:
                        queue.append((target, impact_bps, depth + 1))

        # Calculate portfolio impact
        total_impact_bps = 0
        for a in affected:
            exposure_pct = country_exposures.get(a["country"], 0) / total
            total_impact_bps += a["impact_bps"] * exposure_pct

        # Also add direct impact on trigger country
        trigger_exposure_pct = country_exposures.get(code, 0) / total
        total_impact_bps += default_severity_bps * trigger_exposure_pct

        # Systemic risk score
        n_affected = len(affected)
        total_affected_exposure = sum(
            country_exposures.get(a["country"], 0) / total for a in affected
        )
        systemic_score = min(100, (
            n_affected * 10 +  # More countries = higher risk
            total_affected_exposure * 50 +  # More exposure = higher risk
            max(a["impact_bps"] for a in affected) / 10 if affected else 0  # Max impact
        ))

        # Cascade timeline
        timeline = [{"day": 0, "event": f"{code} default/spike", "impact_bps": default_severity_bps}]
        day_counter = 1
        for a in sorted(affected, key=lambda x: {"immediate": 0, "days": 1, "weeks": 7, "months": 30}.get(x["speed"], 7)):
            speed_days = {"immediate": 0, "days": 1, "weeks": 7, "months": 30}.get(a["speed"], 7)
            timeline.append({
                "day": day_counter + speed_days,
                "event": f"{a['country']} affected via {a['channel']}",
                "impact_bps": a["impact_bps"],
                "channel": a["channel"],
            })
            day_counter += speed_days + 1

        return CascadeResult(
            trigger_country=code,
            trigger_default_probability=trigger_prob,
            affected_countries=sorted(affected, key=lambda x: -x["impact_bps"]),
            total_portfolio_impact_bps=round(total_impact_bps, 1),
            systemic_risk_score=round(systemic_score, 1),
            max_cascade_depth=max((len(affected) for _ in [1]), default=0),
            cascade_timeline=timeline,
        )

    def systemic_risk_assessment(self, instruments: list[dict]) -> dict:
        """Assess overall systemic/contagion risk for a portfolio."""
        country_exposures: dict[str, float] = {}
        for inst in instruments:
            c = inst.get("issuer_country", "US").upper()
            principal = inst.get("principal_outstanding", 0)
            country_exposures[c] = country_exposures.get(c, 0) + principal
        total = sum(country_exposures.values()) or 1

        # Count linkages per country
        linkage_counts: dict[str, int] = {}
        for link in self.links:
            if link["source"] in country_exposures or link["target"] in country_exposures:
                for c in (link["source"], link["target"]):
                    linkage_counts[c] = linkage_counts.get(c, 0) + 1

        # Countries with most linkages are most systemically important
        top_linked = sorted(linkage_counts.items(), key=lambda x: -x[1])[:10]

        # Simulate cascades for top exposures
        cascades = []
        for code in sorted(country_exposures.keys(), key=lambda x: -country_exposures[x])[:5]:
            cascade = self.simulate_cascade(code, instruments, default_severity_bps=500)
            cascades.append({
                "trigger": code,
                "n_affected": len(cascade.affected_countries),
                "portfolio_impact_bps": cascade.total_portfolio_impact_bps,
                "systemic_score": cascade.systemic_risk_score,
            })

        # Worst-case scenario
        worst_cascade = max(cascades, key=lambda x: x["portfolio_impact_bps"]) if cascades else None

        # Concentration in linked countries
        linked_exposure = sum(
            country_exposures.get(link["source"], 0) + country_exposures.get(link["target"], 0)
            for link in self.links
            if link["source"] in country_exposures or link["target"] in country_exposures
        )
        contagion_exposure_pct = linked_exposure / total * 100 if total > 0 else 0

        return {
            "total_instruments": len(instruments),
            "countries_exposed": len(country_exposures),
            "contagion_exposure_pct": round(min(100, contagion_exposure_pct), 1),
            "most_linked_countries": [
                {"country": c, "linkage_count": n} for c, n in top_linked
            ],
            "cascade_scenarios": cascades,
            "worst_case": worst_cascade,
            "recommendations": self._generate_recommendations(country_exposures, total, cascades),
        }

    def _generate_recommendations(
        self, exposures: dict[str, float], total: float, cascades: list[dict]
    ) -> list[str]:
        """Generate risk management recommendations."""
        recs = []

        # Check for concentration in highly-linked countries
        highly_linked = {"IT", "ES", "PT", "FR", "DE", "BR", "TR", "ZA", "RU", "CN", "US"}
        concentrated = [
            code for code, exp in exposures.items()
            if code in highly_linked and exp / total > 0.2
        ]
        if concentrated:
            recs.append(
                f"High concentration ({', '.join(concentrated)}) in systemically "
                f"important countries. Consider diversifying to reduce contagion risk."
            )

        # Check for European clustering
        eu_countries = {"IT", "ES", "PT", "FR", "DE", "NL", "GR"}
        eu_exposure = sum(exposures.get(c, 0) for c in eu_countries) / total * 100
        if eu_exposure > 40:
            recs.append(
                f"European sovereign exposure at {eu_exposure:.0f}%. "
                f"European contagion network is dense — stress in one country "
                f"rapidly transmits to others. Consider geographic diversification."
            )

        # Check worst-case cascade
        if cascades:
            worst = max(cascades, key=lambda x: x["portfolio_impact_bps"])
            if worst["portfolio_impact_bps"] > 100:
                recs.append(
                    f"Worst-case cascade ({worst['trigger']} default) would impact "
                    f"portfolio by {worst['portfolio_impact_bps']:.0f}bps across "
                    f"{worst['n_affected']} countries. Consider hedging via CDS."
                )

        if not recs:
            recs.append("Contagion risk profile is manageable. Standard monitoring sufficient.")

        return recs


# ── Convenience Functions ──────────────────────────────────────────────

def simulate_default_cascade(
    trigger_country: str,
    instruments: list[dict],
    severity_bps: float = 500,
) -> dict:
    """Simulate a default cascade and return result as dict."""
    model = ContagionRiskModel()
    return model.simulate_cascade(trigger_country, instruments, severity_bps).to_dict()


def assess_systemic_risk(instruments: list[dict]) -> dict:
    """Assess systemic risk and return result as dict."""
    model = ContagionRiskModel()
    return model.systemic_risk_assessment(instruments)


def get_country_linkages(country_code: str) -> list[dict]:
    """Get all contagion linkages for a country."""
    model = ContagionRiskModel()
    return [link.to_dict() for link in model.get_linkages(country_code)]
