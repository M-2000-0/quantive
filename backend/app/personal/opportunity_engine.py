"""Deterministic opportunity detector. No LLMs, no invented amounts.

Reads ProfileFacts (+ user country) -> emits PersonalOpportunity rows with
relevance + needs_*. Every conclusion cites a TaxRule id from the user's
jurisdiction pack (or GEN fallback) or is marked needs_verification.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.personal.models import PersonalOpportunity, ProfileFact, TaxRule
from app.personal.tax_packs import PACKS, normalize_country

# Back-compat: full seed list (all packs). Tests may import this name.
RULES_SEED: list[dict] = [r for pack in PACKS.values() for r in pack]


def seed_rules(db: Session) -> None:
    for r in RULES_SEED:
        if not db.get(TaxRule, r["id"]):
            db.add(TaxRule(**r))
    db.commit()


def _facts(db: Session, user_id: str) -> dict[str, list[str]]:
    rows = db.query(ProfileFact).filter(ProfileFact.user_id == user_id).all()
    out: dict[str, list[str]] = {}
    for f in rows:
        vals: list[str] = []
        if f.value:
            vals.append(f.value)
        vj = f.value_json or {}
        if isinstance(vj, dict) and isinstance(vj.get("values"), list):
            vals += [str(x) for x in vj["values"]]
        out.setdefault(f.key, []).extend(vals)
        out.setdefault(f"{f.category}.{f.key}", []).extend(vals)
    return out


def _juris(facts: dict[str, list[str]]) -> str:
    raw = ""
    for v in facts.get("country", []):
        raw = v
        break
    return normalize_country(raw)


def _ref(juris: str, *candidates: str) -> list[str]:
    """First candidate matching the user's pack, else the GEN fallback."""
    for c in candidates:
        if c.startswith(juris + "-"):
            return [c]
    for c in candidates:
        if c.startswith("GEN-"):
            return [c]
    return list(candidates[:1])


def detect(db: Session, user_id: str, tax_year: int = 2026, tier: str = "") -> list[PersonalOpportunity]:
    seed_rules(db)
    facts = _facts(db, user_id)
    juris = _juris(facts)

    def has(key: str, val: str) -> bool:
        return val in facts.get(key, [])

    candidates: list[dict] = []
    if has("housing", "mortgage") or has("mortgage_detail", "yes"):
        candidates.append({"title": "Mortgage interest", "category": "housing", "relevance": "high",
                           "why": "You indicated that you have a mortgage.",
                           "needs_info": ["Applicable tax regime", "Loan qualification"],
                           "needs_docs": ["Annual mortgage documentation"],
                           "rule_refs": _ref(juris, f"{juris}-2026-mortgage-interest",
                                             "US-2026-mortgage-interest", "MX-2026-mortgage-interest",
                                             "GEN-2026-housing-interest"),
                           "next_action": "Upload annual mortgage statement, then confirm regime."})
    if has("medical_exp", "yes"):
        candidates.append({"title": "Medical expenses", "category": "health", "relevance": "medium",
                           "why": "You reported qualifying medical expenses.",
                           "needs_info": ["Expense breakdown by category"],
                           "needs_docs": ["Receipts", "Insurance statements"],
                           "rule_refs": _ref(juris, f"{juris}-2026-medical-75pct", "GEN-2026-medical-expenses"),
                           "next_action": "Organize receipts in Document Center."})
    if has("retirement", "yes"):
        candidates.append({"title": "Retirement contributions", "category": "retirement", "relevance": "medium",
                           "why": "You contribute to a retirement account.",
                           "needs_info": ["Account type", "Annual contributions"],
                           "needs_docs": ["Contribution statements"],
                           "rule_refs": _ref(juris, f"{juris}-2026-retirement", "GEN-2026-retirement"),
                           "next_action": "Confirm account type and totals."})
    if has("education_exp", "yes"):
        if juris == "US" and has("loans", "yes"):
            candidates.append({"title": "Student loan interest", "category": "education", "relevance": "medium",
                               "why": "You reported education expenses and loan interest.",
                               "needs_info": ["Eligible loan", "Income range"],
                               "needs_docs": ["Form 1098-E or loan statements"],
                               "rule_refs": ["US-2026-student-loan-interest"],
                               "next_action": "Confirm loan eligibility and income phaseout."})
        else:
            candidates.append({"title": "Education expenses", "category": "education", "relevance": "low",
                               "why": "You reported education expenses.",
                               "needs_info": ["Eligible recipient", "Institution type"],
                               "needs_docs": ["Tuition receipts"],
                               "rule_refs": ["GEN-2026-education"],
                               "next_action": "Confirm eligibility before any conclusion."})
    elif juris == "US" and has("loans", "yes"):
        candidates.append({"title": "Student loan interest", "category": "education", "relevance": "medium",
                           "why": "You pay interest on loans.",
                           "needs_info": ["Whether the loan is an eligible student loan", "Income range"],
                           "needs_docs": ["Form 1098-E or loan statements"],
                           "rule_refs": ["US-2026-student-loan-interest"],
                           "next_action": "Confirm this is an eligible student loan."})
    if has("home_office", "yes"):
        candidates.append({"title": "Home office", "category": "work", "relevance": "low",
                           "why": "You work from a dedicated home space. Treatment is regime-dependent.",
                           "needs_info": ["Tax regime", "Exclusive-use evidence"],
                           "needs_docs": ["Expense records"],
                           "rule_refs": _ref(juris, f"{juris}-2026-home-office", "GEN-2026-home-office"),
                           "next_action": "Answer 2 regime questions in Quantive Intelligence."})
    if has("donations", "yes"):
        candidates.append({"title": "Charitable donations", "category": "donations", "relevance": "medium" if juris == "US" else "low",
                           "why": "You made charitable donations.",
                           "needs_info": ["Eligible recipient", "Whether you itemize (US)"],
                           "needs_docs": ["Donation receipts", "Acknowledgment letters"],
                           "rule_refs": _ref(juris, f"{juris}-2026-charitable", "GEN-2026-donations"),
                           "next_action": "Gather receipts and confirm recipient eligibility."})
    if juris == "US" and (has("employment_detail", "yes") or has("housing", "own") or has("housing", "mortgage")):
        candidates.append({"title": "State and local taxes (SALT)", "category": "housing", "relevance": "low",
                           "why": "You may pay deductible state/local taxes. The cap must be confirmed for the current year.",
                           "needs_info": ["Whether you itemize", "Current-year SALT cap"],
                           "needs_docs": ["Property tax bills", "State tax records"],
                           "rule_refs": ["US-2026-salt"],
                           "next_action": "Confirm the current-year cap before assuming anything."})
    if juris == "BD":
        if has("employment_detail", "yes"):
            candidates.append({"title": "House rent allowance", "category": "housing", "relevance": "medium",
                               "why": "You are salaried and may receive house rent allowance.",
                               "needs_info": ["Actual rent paid", "Salary structure"],
                               "needs_docs": ["Rent receipts", "Salary certificate"],
                               "rule_refs": ["BD-2026-hra"],
                               "next_action": "Confirm the current exemption formula."})
        if has("retirement", "yes") or has("invest_accounts", "yes") or has("donations", "yes"):
            candidates.append({"title": "Investment tax rebate", "category": "retirement", "relevance": "medium",
                               "why": "You hold investments that may qualify for rebate under the yearly schedule.",
                               "needs_info": ["Investment types", "Current-year rebate schedule"],
                               "needs_docs": ["Investment certificates", "Premium receipts"],
                               "rule_refs": ["BD-2026-investment-rebate"],
                               "next_action": "Confirm the current assessment year's schedule."})
        if has("invest_accounts", "yes"):
            candidates.append({"title": "Savings instruments", "category": "financial", "relevance": "low",
                               "why": "You hold savings/investment instruments with NBR-specific treatment.",
                               "needs_info": ["Instrument types"],
                               "needs_docs": ["Certificates", "Interest statements"],
                               "rule_refs": ["BD-2026-savings-instruments"],
                               "next_action": "Verify current NBR circulars."})
        if has("rental_income", "yes"):
            candidates.append({"title": "Rental income deductions", "category": "housing", "relevance": "medium",
                               "why": "You receive rental income with potentially allowable deductions.",
                               "needs_info": ["Declared rental income", "Deductible expenses"],
                               "needs_docs": ["Rent deeds", "Municipal tax receipts"],
                               "rule_refs": ["BD-2026-rental-income"],
                               "next_action": "Verify allowable deductions before computing."})

    # Sovereign-only extras: Gov-grade market insight for individuals (10k).
    # Same privacy contract as Qubo: aggregates only, never individual data.
    if tier in ("personal_10k",):
        if has("invest_accounts", "yes") or has("investment_income", "yes"):
            candidates.append({"title": "Qubo trend alignment", "category": "sovereign", "relevance": "medium",
                               "why": "Your investor profile can be compared against aggregated Qubo age-bracket trends.",
                               "needs_info": ["Age bracket confirmation"],
                               "needs_docs": [],
                               "rule_refs": [],
                               "next_action": "Open Sovereign view for your bracket's investing vs spending trend."})
        candidates.append({"title": "Sovereign insight briefing", "category": "sovereign", "relevance": "low",
                           "why": "Sovereign tier includes a Gov-grade briefing built from aggregates only.",
                           "needs_info": [],
                           "needs_docs": [],
                           "rule_refs": [],
                           "next_action": "See Gov insights for where brackets like yours are allocating."})

    # Always surface profile-completeness as an action, not an opportunity.
    existing = {o.title: o for o in db.query(PersonalOpportunity)
                .filter(PersonalOpportunity.user_id == user_id,
                        PersonalOpportunity.tax_year == tax_year).all()}
    out: list[PersonalOpportunity] = []
    for c in candidates:
        row = existing.get(c["title"])
        if row is None:
            row = PersonalOpportunity(user_id=user_id, tax_year=tax_year, status="potentially_relevant", **c)
            db.add(row)
        else:
            for k, v in c.items():
                setattr(row, k, v)
        out.append(row)
    db.commit()
    for o in out:
        db.refresh(o)
    return out
