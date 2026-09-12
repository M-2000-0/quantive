"""Deterministic opportunity detector. No LLMs, no invented amounts.

Reads ProfileFacts -> emits PersonalOpportunity rows with relevance + needs_*.
Every conclusion must cite a TaxRule id or be marked needs_verification.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.personal.models import PersonalOpportunity, ProfileFact, TaxRule

RULES_SEED: list[dict] = [
    {"id": "MX-2026-mortgage-interest", "jurisdiction": "MX", "tax_year": 2026,
     "topic": "housing", "title": "Mortgage interest — potentially relevant",
     "summary": "Mortgage interest may be relevant depending on regime and documentation. Requires verification.",
     "requirements": ["qualifying mortgage", "applicable tax regime"], "docs_required": ["annual mortgage statement"],
     "limits": {}, "sources": ["SAT — verify current rules"], "effective_from": "2026-01-01", "effective_to": "2026-12-31"},
    {"id": "GEN-2026-medical-expenses", "jurisdiction": "GEN", "tax_year": 2026,
     "topic": "health", "title": "Medical expenses — potentially relevant",
     "summary": "Medical expenses are often jurisdiction-limited. Documentation required.",
     "requirements": ["qualifying expenses", "receipts"], "docs_required": ["receipts", "insurance statements"],
     "limits": {}, "sources": ["Verify against current rules"], "effective_from": "2026-01-01", "effective_to": "2026-12-31"},
    {"id": "GEN-2026-retirement", "jurisdiction": "GEN", "tax_year": 2026,
     "topic": "retirement", "title": "Retirement contributions — potentially relevant",
     "summary": "Retirement contributions may have limits/incentives by jurisdiction.",
     "requirements": ["eligible account"], "docs_required": ["contribution statements"],
     "limits": {}, "sources": ["Verify against current rules"], "effective_from": "2026-01-01", "effective_to": "2026-12-31"},
    {"id": "GEN-2026-education", "jurisdiction": "GEN", "tax_year": 2026,
     "topic": "education", "title": "Education expenses — potentially relevant",
     "summary": "Education treatment varies widely. Low default relevance until confirmed.",
     "requirements": ["eligible expenses"], "docs_required": ["tuition receipts"],
     "limits": {}, "sources": ["Verify against current rules"], "effective_from": "2026-01-01", "effective_to": "2026-12-31"},
    {"id": "GEN-2026-home-office", "jurisdiction": "GEN", "tax_year": 2026,
     "topic": "work", "title": "Home office — needs verification",
     "summary": "Home-office treatment depends on regime, exclusivity, and activity. High verification burden.",
     "requirements": ["exclusive use evidence", "applicable regime"], "docs_required": ["expense records"],
     "limits": {}, "sources": ["Verify against current rules"], "effective_from": "2026-01-01", "effective_to": "2026-12-31"},
]


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


def detect(db: Session, user_id: str, tax_year: int = 2026, tier: str = "") -> list[PersonalOpportunity]:
    seed_rules(db)
    facts = _facts(db, user_id)

    def has(key: str, val: str) -> bool:
        return val in facts.get(key, [])

    candidates: list[dict] = []
    if has("housing", "mortgage") or has("mortgage_detail", "yes"):
        candidates.append({"title": "Mortgage interest", "category": "housing", "relevance": "high",
                           "why": "You indicated that you have a mortgage.",
                           "needs_info": ["Applicable tax regime", "Loan qualification"],
                           "needs_docs": ["Annual mortgage documentation"],
                           "rule_refs": ["MX-2026-mortgage-interest"],
                           "next_action": "Upload annual mortgage statement, then confirm regime."})
    if has("medical_exp", "yes"):
        candidates.append({"title": "Medical expenses", "category": "health", "relevance": "medium",
                           "why": "You reported qualifying medical expenses.",
                           "needs_info": ["Expense breakdown by category"],
                           "needs_docs": ["Receipts", "Insurance statements"],
                           "rule_refs": ["GEN-2026-medical-expenses"],
                           "next_action": "Organize receipts in Document Center."})
    if has("retirement", "yes"):
        candidates.append({"title": "Retirement contributions", "category": "retirement", "relevance": "medium",
                           "why": "You contribute to a retirement account.",
                           "needs_info": ["Account type", "Annual contributions"],
                           "needs_docs": ["Contribution statements"],
                           "rule_refs": ["GEN-2026-retirement"],
                           "next_action": "Confirm account type and totals."})
    if has("education_exp", "yes"):
        candidates.append({"title": "Education expenses", "category": "education", "relevance": "low",
                           "why": "You reported education expenses.",
                           "needs_info": ["Eligible recipient", "Institution type"],
                           "needs_docs": ["Tuition receipts"],
                           "rule_refs": ["GEN-2026-education"],
                           "next_action": "Confirm eligibility before any conclusion."})
    if has("home_office", "yes"):
        candidates.append({"title": "Home office", "category": "work", "relevance": "low",
                           "why": "You work from a dedicated home space. Treatment is regime-dependent.",
                           "needs_info": ["Tax regime", "Exclusive-use evidence"],
                           "needs_docs": ["Expense records"],
                           "rule_refs": ["GEN-2026-home-office"],
                           "next_action": "Answer 2 regime questions in Quantive Intelligence."})

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
