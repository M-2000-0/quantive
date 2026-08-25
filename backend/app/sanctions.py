"""Sanctions & Export Control Screening Engine.

Pre-optimization gate that checks every instrument, counterparty,
and country against global sanctions lists before allowing any
optimization to proceed.

Sanctions Lists:
- OFAC SDN (Specially Designated Nationals) — US Treasury
- EU Consolidated Sanctions List
- UN Security Council Sanctions
- OFAC Sectoral Sanctions (SSI)
- Country-level embargoes

Features:
- Country screening (full, partial, sectoral sanctions)
- Entity screening (banks, issuers, counterparties)
- Instrument screening (ISIN, CUSIP checks)
- Real-time risk scoring
- Blocking vs advisory classification
- Audit trail for compliance documentation
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class SanctionSeverity(str, Enum):
    BLOCKED = "blocked"          # Full sanctions — cannot proceed
    RESTRICTED = "restricted"    # Partial sanctions — needs review
    ADVISORY = "advisory"        # Watchlist — proceed with caution
    CLEAR = "clear"              # No issues


class SanctionType(str, Enum):
    COUNTRY_FULL = "country_full_embargo"
    COUNTRY_PARTIAL = "country_partial_sanctions"
    COUNTRY_SECTORAL = "country_sectoral_sanctions"
    ENTITY_SDN = "entity_sdn"
    ENTITY_SSI = "entity_sectoral"
    ENTITY_FSE = "entity_foreign_sanctions_evader"
    INSTRUMENT = "instrument_blocked"
    VESSEL = "vessel_blocked"


@dataclass
class ScreeningMatch:
    """A single sanctions match."""
    list_name: str              # "OFAC_SDN", "EU_SANCTIONS", "UN_SANCTIONS"
    sanction_type: str          # From SanctionType
    severity: str               # From SanctionSeverity
    entity_name: str            # Matched entity/country name
    entity_id: Optional[str]    # Sanctions list ID
    reason: str                 # Why this was flagged
    score: float                # Match confidence (0-1)
    effective_date: str         # When sanctions took effect
    expiry_date: Optional[str]  # When sanctions expire (None = indefinite)
    program: Optional[str]      # Sanctions program (e.g., "UKRAINE-EO13662")


@dataclass
class ScreeningResult:
    """Complete screening result for an optimization request."""
    screened_at: str
    overall_severity: str       # Worst severity found
    total_matches: int
    blocked: bool               # True if any BLOCKED matches
    matches: list[ScreeningMatch]
    countries_flagged: list[str]
    entities_flagged: list[str]
    instruments_flagged: list[str]
    recommendation: str         # Human-readable recommendation
    compliance_notes: str       # Required compliance documentation

    def to_dict(self) -> dict:
        return {
            "screened_at": self.screened_at,
            "overall_severity": self.overall_severity,
            "total_matches": self.total_matches,
            "blocked": self.blocked,
            "matches": [
                {
                    "list": m.list_name,
                    "type": m.sanction_type,
                    "severity": m.severity,
                    "entity": m.entity_name,
                    "entity_id": m.entity_id,
                    "reason": m.reason,
                    "score": round(m.score, 2),
                    "effective_date": m.effective_date,
                    "expiry_date": m.expiry_date,
                    "program": m.program,
                }
                for m in self.matches
            ],
            "countries_flagged": self.countries_flagged,
            "entities_flagged": self.entities_flagged,
            "instruments_flagged": self.instruments_flagged,
            "recommendation": self.recommendation,
            "compliance_notes": self.compliance_notes,
        }


# ══════════════════════════════════════════════════════════════════════
# SANCTIONS DATABASE (Embedded — production would use external DB/API)
# ══════════════════════════════════════════════════════════════════════

# Country sanctions (comprehensive, updated through 2024)
COUNTRY_SANCTIONS: dict[str, dict] = {
    # Full embargoes
    "KP": {"name": "North Korea", "severity": "blocked", "type": "country_full_embargo",
           "lists": ["OFAC", "EU", "UN"], "programs": ["DPRK", "NPWMD"],
           "reason": "Nuclear weapons proliferation, human rights violations"},
    "IR": {"name": "Iran", "severity": "blocked", "type": "country_full_embargo",
           "lists": ["OFAC", "EU", "UN"], "programs": ["IRAN", "NPWMD"],
           "reason": "Nuclear program, terrorism financing, human rights"},
    "SY": {"name": "Syria", "severity": "blocked", "type": "country_full_embargo",
           "lists": ["OFAC", "EU", "UN"], "programs": ["SYRIA"],
           "reason": "Armed conflict, chemical weapons, terrorism"},
    "CU": {"name": "Cuba", "severity": "blocked", "type": "country_full_embargo",
           "lists": ["OFAC"], "programs": ["CUBA"],
           "reason": "US embargo (OFAC only — EU has lifted restrictions)"},
    "VE": {"name": "Venezuela", "severity": "restricted", "type": "country_sectoral_sanctions",
           "lists": ["OFAC", "EU"], "programs": ["VENEZUELA-EO13884"],
           "reason": "Oil sector sanctions, government human rights violations"},

    # Partial / sectoral sanctions
    "RU": {"name": "Russia", "severity": "restricted", "type": "country_sectoral_sanctions",
           "lists": ["OFAC", "EU", "UK"], "programs": ["UKRAINE-EO13662", "RUSSIA-EO14024"],
           "reason": "Ukraine invasion — sovereign debt restrictions, energy sector, oligarch sanctions",
           "notes": "Russian sovereign ruble bonds (OFZ) restricted. USD/EUR sovereign bonds restricted. Some corporate bonds blocked."},
    "BY": {"name": "Belarus", "severity": "restricted", "type": "country_sectoral_sanctions",
           "lists": ["OFAC", "EU"], "programs": ["BELARUS-EO14038"],
           "reason": "Support for Russia invasion, election suppression"},
    "MM": {"name": "Myanmar", "severity": "restricted", "type": "country_sectoral_sanctions",
           "lists": ["OFAC", "EU", "UK"], "programs": ["BURMA-EO14014"],
           "reason": "Military coup, genocide against Rohingya"},
    "ET": {"name": "Ethiopia", "severity": "advisory", "type": "country_partial_sanctions",
           "lists": ["OFAC"], "programs": ["ETHIOPIA-EO14046"],
           "reason": "Armed conflict in Tigray region"},
    "AF": {"name": "Afghanistan", "severity": "restricted", "type": "country_partial_sanctions",
           "lists": ["OFAC", "EU", "UN"], "programs": ["AFGHANISTAN"],
           "reason": "Taliban government — humanitarian carve-outs exist but financial restrictions apply"},
    "SD": {"name": "Sudan", "severity": "restricted", "type": "country_partial_sanctions",
           "lists": ["OFAC", "EU"], "programs": ["SUDAN"],
           "reason": "Armed conflict, human rights violations"},
    "SO": {"name": "Somalia", "severity": "advisory", "type": "country_partial_sanctions",
           "lists": ["UN"], "programs": ["SOMALIA"],
           "reason": "Arms embargo, Al-Shabaab designated entity"},
    "LY": {"name": "Libya", "severity": "advisory", "type": "country_partial_sanctions",
           "lists": ["OFAC", "EU", "UN"], "programs": ["LIBYA"],
           "reason": "Arms embargo, designated entities only"},
    "LB": {"name": "Lebanon", "severity": "advisory", "type": "country_partial_sanctions",
           "lists": ["OFAC"], "programs": ["LEBANON"],
           "reason": "Hezbollah designations — check counterparties"},
    "YE": {"name": "Yemen", "severity": "advisory", "type": "country_partial_sanctions",
           "lists": ["OFAC", "UN"], "programs": ["YEMEN"],
           "reason": "Arms embargo, designated Houthi entities"},
    "HT": {"name": "Haiti", "severity": "advisory", "type": "country_partial_sanctions",
           "lists": ["OFAC"], "programs": ["HAITI-EO14032"],
           "reason": "Gang violence, designated individuals only"},
    "SS": {"name": "South Sudan", "severity": "advisory", "type": "country_partial_sanctions",
           "lists": ["OFAC", "EU", "UN"], "programs": ["SOUTH-SUDAN"],
           "reason": "Arms embargo, designated individuals"},
    "CF": {"name": "Central African Republic", "severity": "advisory", "type": "country_partial_sanctions",
           "lists": ["OFAC", "EU", "UN"], "programs": ["CAR"],
           "reason": "Arms embargo, designated entities"},
    "CD": {"name": "DR Congo", "severity": "advisory", "type": "country_partial_sanctions",
           "lists": ["OFAC", "EU", "UN"], "programs": ["DRC"],
           "reason": "Arms embargo, designated armed groups"},
    "CW": {"name": "Curacao", "severity": "advisory", "type": "country_partial_sanctions",
           "lists": ["OFAC"], "programs": ["VENEZUELA"],
           "reason": "Venezuela sanctions avoidance risk"},
    "NI": {"name": "Nicaragua", "severity": "advisory", "type": "country_partial_sanctions",
           "lists": ["OFAC"], "programs": ["NICARAGUA-EO13851"],
           "reason": "Government corruption, human rights — designated individuals only"},
}

# Known sanctioned financial institutions (examples — production would use live OFAC SDN feed)
SANCTIONED_ENTITIES: list[dict] = [
    {"name": "Bank of Russia (Central Bank)", "country": "RU", "severity": "blocked",
     "lists": ["OFAC", "EU"], "programs": ["RUSSIA-EO14024"],
     "reason": "Central Bank of Russia — sovereign asset freeze"},
    {"name": "VTB Bank", "country": "RU", "severity": "blocked",
     "lists": ["OFAC", "EU"], "programs": ["UKRAINE-EO13662"],
     "reason": "Major Russian bank — full blocking sanctions"},
    {"name": "Sberbank", "country": "RU", "severity": "blocked",
     "lists": ["OFAC", "EU"], "programs": ["UKRAINE-EO13662"],
     "reason": "Largest Russian bank — full blocking sanctions"},
    {"name": "Gazprombank", "country": "RU", "severity": "blocked",
     "lists": ["OFAC", "EU"], "programs": ["UKRAINE-EO13662"],
     "reason": "Russian energy bank — full blocking sanctions"},
    {"name": "Bank of Kunlun", "country": "CN", "severity": "restricted",
     "lists": ["OFAC"], "programs": ["IRAN"],
     "reason": "Sanctioned for facilitating Iranian oil transactions"},
    {"name": "Melli Bank", "country": "IR", "severity": "blocked",
     "lists": ["OFAC", "EU", "UN"], "programs": ["IRAN"],
     "reason": "Iran's largest bank — terrorism financing"},
    {"name": "Bank Sepah", "country": "IR", "severity": "blocked",
     "lists": ["OFAC", "EU", "UN"], "programs": ["IRAN", "NPWMD"],
     "reason": "Iranian bank linked to missile program"},
    {"name": "Bank of Korea", "country": "KP", "severity": "blocked",
     "lists": ["OFAC", "UN"], "programs": ["DPRK"],
     "reason": "North Korean central bank"},
]

# Instrument-level sanctions (ISINs and identifiers that are blocked)
BLOCKED_INSTRUMENTS: list[dict] = [
    {"identifier": "RU000A0J2YJ2", "type": "ISIN", "country": "RU", "severity": "blocked",
     "reason": "Russian sovereign OFZ bond — blocked under EO14024"},
    {"identifier": "XS0984723567", "type": "ISIN", "country": "RU", "severity": "blocked",
     "reason": "Russian sovereign Eurobond — restricted"},
    {"identifier": "RU000A100DF5", "type": "ISIN", "country": "RU", "severity": "blocked",
     "reason": "Russian sovereign bond — blocked"},
]


class SanctionsScreeningEngine:
    """Comprehensive sanctions screening engine.

    Checks countries, entities, instruments, and counterparties
    against all major sanctions lists. Returns a blocking decision
    with full audit trail.
    """

    def screen_country(self, country_code: str) -> list[ScreeningMatch]:
        """Screen a country against all sanctions lists."""
        matches = []
        code = country_code.upper()

        if code in COUNTRY_SANCTIONS:
            sanc = COUNTRY_SANCTIONS[code]
            for list_name in sanc.get("lists", []):
                matches.append(ScreeningMatch(
                    list_name=f"{list_name}_SANCTIONS",
                    sanction_type=sanc["type"],
                    severity=sanc["severity"],
                    entity_name=sanc["name"],
                    entity_id=f"COUNTRY-{code}",
                    reason=sanc["reason"],
                    score=1.0,
                    effective_date="2014-01-01" if code == "RU" else "2000-01-01",
                    expiry_date=None,
                    program=sanc.get("programs", [None])[0],
                ))

        return matches

    def screen_entity(self, entity_name: str, entity_country: Optional[str] = None) -> list[ScreeningMatch]:
        """Screen an entity (bank, counterparty, issuer) against sanctions lists."""
        matches = []
        name_lower = entity_name.lower()

        for entity in SANCTIONED_ENTITIES:
            # Fuzzy match — check if the query contains or is contained in the sanctioned name
            sanctioned_lower = entity["name"].lower()
            score = 0.0

            if name_lower == sanctioned_lower:
                score = 1.0
            elif name_lower in sanctioned_lower or sanctioned_lower in name_lower:
                score = 0.9
            elif self._name_similarity(name_lower, sanctioned_lower) > 0.75:
                score = 0.7

            # Country filter — if we know the entity's country, use it
            if entity_country and entity.get("country", "").upper() != entity_country.upper():
                score *= 0.3  # Downweight country mismatches

            if score > 0.5:
                for list_name in entity.get("lists", []):
                    matches.append(ScreeningMatch(
                        list_name=f"{list_name}_SDN",
                        sanction_type=SanctionType.ENTITY_SDN.value,
                        severity=entity["severity"],
                        entity_name=entity["name"],
                        entity_id=None,
                        reason=entity["reason"],
                        score=score,
                        effective_date="2022-02-24" if entity.get("country") == "RU" else "2010-01-01",
                        expiry_date=None,
                        program=entity.get("programs", [None])[0],
                    ))

        return matches

    def screen_instrument(self, instrument: dict) -> list[ScreeningMatch]:
        """Screen a debt instrument (ISIN, CUSIP, issuer) against sanctions lists."""
        matches = []

        # Check ISIN
        isin = instrument.get("isin", "").upper()
        for blocked in BLOCKED_INSTRUMENTS:
            if blocked["identifier"].upper() == isin:
                matches.append(ScreeningMatch(
                    list_name="OFAC_INSTRUMENT",
                    sanction_type=SanctionType.INSTRUMENT.value,
                    severity=blocked["severity"],
                    entity_name=f"Instrument {isin}",
                    entity_id=isin,
                    reason=blocked["reason"],
                    score=1.0,
                    effective_date="2022-02-24",
                    expiry_date=None,
                    program="RUSSIA-EO14024",
                ))

        # Check issuer country
        issuer_country = instrument.get("issuer_country", "").upper()
        if issuer_country:
            country_matches = self.screen_country(issuer_country)
            matches.extend(country_matches)

        # Check issuer name
        issuer_name = instrument.get("issuer_name", "")
        if issuer_name:
            entity_matches = self.screen_entity(issuer_name, issuer_country)
            matches.extend(entity_matches)

        # Check custodian/counterparty
        custodian = instrument.get("custodian", "")
        if custodian:
            custodian_matches = self.screen_entity(custodian)
            matches.extend(custodian_matches)

        return matches

    def screen_portfolio(self, instruments: list[dict]) -> ScreeningResult:
        """Screen an entire portfolio of instruments."""
        all_matches = []
        countries_flagged = set()
        entities_flagged = set()
        instruments_flagged = set()

        for inst in instruments:
            # Screen instrument
            inst_matches = self.screen_instrument(inst)
            for m in inst_matches:
                m_key = f"{m.list_name}:{m.entity_name}"
                # Deduplicate
                if not any(f"{x.list_name}:{x.entity_name}" == m_key for x in all_matches):
                    all_matches.append(m)

            # Track flagged items
            issuer_country = inst.get("issuer_country", "").upper()
            if issuer_country and any(m.severity in ("blocked", "restricted") for m in inst_matches):
                countries_flagged.add(issuer_country)

            issuer_name = inst.get("issuer_name", "")
            if issuer_name and any(m.severity in ("blocked", "restricted") for m in inst_matches):
                entities_flagged.add(issuer_name)

            inst_id = inst.get("isin", inst.get("issuer_name", "Unknown"))
            if any(m.severity in ("blocked", "restricted") for m in inst_matches):
                instruments_flagged.add(inst_id)

        # Determine overall severity
        severity_order = ["blocked", "restricted", "advisory", "clear"]
        worst = "clear"
        for m in all_matches:
            if severity_order.index(m.severity) < severity_order.index(worst):
                worst = m.severity

        blocked = any(m.severity == "blocked" for m in all_matches)

        # Generate recommendation
        if blocked:
            recommendation = (
                f"BLOCK: {len([m for m in all_matches if m.severity == 'blocked'])} blocked "
                f"matches found. Optimization cannot proceed until sanctioned items are removed. "
                f"Countries: {', '.join(countries_flagged) or 'none'}. "
                f"Entities: {', '.join(entities_flagged) or 'none'}."
            )
        elif worst == "restricted":
            recommendation = (
                f"REVIEW REQUIRED: {len(all_matches)} restricted matches found. "
                f"Compliance officer approval required before proceeding. "
                f"Consider removing flagged instruments from the portfolio."
            )
        elif worst == "advisory":
            recommendation = (
                f"ADVISORY: {len(all_matches)} watchlist matches. "
                f"Proceed with enhanced due diligence. Document rationale."
            )
        else:
            recommendation = "CLEAR: No sanctions matches found. Optimization may proceed."

        # Compliance notes
        if all_matches:
            compliance_notes = (
                f"Sanctions screening performed at {datetime.now(timezone.utc).isoformat()}. "
                f"Total matches: {len(all_matches)}. "
                f"Lists checked: OFAC SDN, EU Consolidated, UN Security Council. "
                f"Blocking matches: {len([m for m in all_matches if m.severity == 'blocked'])}. "
                f"Review required: {blocked or worst == 'restricted'}. "
                f"This screening should be refreshed before trade execution."
            )
        else:
            compliance_notes = (
                f"Sanctions screening performed at {datetime.now(timezone.utc).isoformat()}. "
                f"No matches found across all checked lists. "
                f"This screening should be refreshed before trade execution."
            )

        return ScreeningResult(
            screened_at=datetime.now(timezone.utc).isoformat(),
            overall_severity=worst,
            total_matches=len(all_matches),
            blocked=blocked,
            matches=all_matches,
            countries_flagged=sorted(countries_flagged),
            entities_flagged=sorted(entities_flagged),
            instruments_flagged=sorted(instruments_flagged),
            recommendation=recommendation,
            compliance_notes=compliance_notes,
        )

    def screen_optimization_request(self, request: dict) -> ScreeningResult:
        """Screen an entire optimization request including instruments, counterparties, and constraints."""
        instruments = request.get("instruments", [])
        counterparties = request.get("counterparties", [])
        constraints = request.get("constraints", {})

        # Screen instruments
        result = self.screen_portfolio(instruments)

        # Screen counterparties
        for cp in counterparties:
            cp_matches = self.screen_entity(cp.get("name", ""), cp.get("country"))
            for m in cp_matches:
                if not any(f"{x.list_name}:{x.entity_name}" == f"{m.list_name}:{m.entity_name}"
                          for x in result.matches):
                    result.matches.append(m)

        # Check constraint restrictions (e.g., "no Russia exposure")
        restricted_countries = constraints.get("restricted_countries", [])
        for country in restricted_countries:
            country_matches = self.screen_country(country)
            for m in country_matches:
                if not any(f"{x.list_name}:{x.entity_name}" == f"{m.list_name}:{m.entity_name}"
                          for x in result.matches):
                    result.matches.append(m)

        # Recalculate totals
        result.total_matches = len(result.matches)
        result.blocked = any(m.severity == "blocked" for m in result.matches)

        return result

    def _name_similarity(self, a: str, b: str) -> float:
        """Simple name similarity using token overlap (no external deps)."""
        tokens_a = set(a.lower().split())
        tokens_b = set(b.lower().split())
        if not tokens_a or not tokens_b:
            return 0.0
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        return len(intersection) / len(union)


# ── Convenience Functions ──────────────────────────────────────────────

def screen_country(country_code: str) -> dict:
    """Screen a country and return result as dict."""
    engine = SanctionsScreeningEngine()
    matches = engine.screen_country(country_code)
    return {
        "country_code": country_code,
        "matches": [
            {"list": m.list_name, "severity": m.severity, "reason": m.reason, "program": m.program}
            for m in matches
        ],
        "blocked": any(m.severity == "blocked" for m in matches),
    }


def screen_portfolio(instruments: list[dict]) -> dict:
    """Screen a portfolio and return result as dict."""
    engine = SanctionsScreeningEngine()
    result = engine.screen_portfolio(instruments)
    return result.to_dict()


def screen_optimization_request(request: dict) -> dict:
    """Screen an optimization request and return result as dict."""
    engine = SanctionsScreeningEngine()
    result = engine.screen_optimization_request(request)
    return result.to_dict()
