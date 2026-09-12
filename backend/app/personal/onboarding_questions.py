"""24-question adaptive onboarding. Baseline max 24, dynamically skipped.

Each question: id, group, prompt, kind, options?, allow_multiple?, follow_if?
Engine in api.py skips questions whose `requires` fact is absent/negative.
"""
from __future__ import annotations

QUESTIONS: list[dict] = [
    {"id": "income_sources", "group": "income", "prompt": "How do you currently earn money?",
     "kind": "multi", "options": ["employment", "business", "freelance", "investments", "rental", "other"]},
    {"id": "employment_detail", "group": "income", "prompt": "Are you employed by a company or organization?",
     "kind": "single", "options": ["yes", "no"], "requires": {"fact": "income_sources", "has": "employment"}},
    {"id": "business_detail", "group": "income", "prompt": "Do you own or operate a business?",
     "kind": "single", "options": ["yes", "no"], "requires": {"fact": "income_sources", "has": "business"}},
    {"id": "freelance_detail", "group": "income", "prompt": "Do you do freelance or independent work?",
     "kind": "single", "options": ["yes", "no"], "requires": {"fact": "income_sources", "has": "freelance"}},
    {"id": "investment_income", "group": "income", "prompt": "Do you receive investment income (dividends, interest, gains)?",
     "kind": "single", "options": ["yes", "no"]},
    {"id": "rental_income", "group": "income", "prompt": "Do you receive rental income?",
     "kind": "single", "options": ["yes", "no"]},
    {"id": "housing", "group": "housing", "prompt": "What best describes your housing?",
     "kind": "multi", "options": ["rent", "own", "mortgage", "rental_property", "primary_residence"]},
    {"id": "mortgage_detail", "group": "housing", "prompt": "Do you pay mortgage interest?",
     "kind": "single", "options": ["yes", "no"], "requires": {"fact": "housing", "has": "mortgage"}},
    {"id": "work_home", "group": "work", "prompt": "Do you work from home?",
     "kind": "single", "options": ["yes", "no", "sometimes"]},
    {"id": "home_office", "group": "work", "prompt": "Do you have a dedicated home office space?",
     "kind": "single", "options": ["yes", "no"], "requires": {"fact": "work_home", "has_any": ["yes", "sometimes"]}},
    {"id": "work_expenses", "group": "work", "prompt": "Do you pay for work equipment or professional expenses?",
     "kind": "single", "options": ["yes", "no"]},
    {"id": "family", "group": "family", "prompt": "Do you have a spouse/partner or dependents?",
     "kind": "multi", "options": ["spouse", "children", "dependents", "none"]},
    {"id": "dependents_count", "group": "family", "prompt": "How many dependents?",
     "kind": "single", "options": ["0", "1", "2", "3+"], "requires": {"fact": "family", "has_any": ["children", "dependents"]}},
    {"id": "education_exp", "group": "family", "prompt": "Did you pay education expenses (you or dependents)?",
     "kind": "single", "options": ["yes", "no"]},
    {"id": "medical_exp", "group": "health", "prompt": "Did you pay medical, dental, or vision expenses?",
     "kind": "single", "options": ["yes", "no"]},
    {"id": "health_insurance", "group": "health", "prompt": "Do you pay health insurance premiums?",
     "kind": "single", "options": ["yes", "no"]},
    {"id": "retirement", "group": "financial", "prompt": "Do you contribute to a retirement account?",
     "kind": "single", "options": ["yes", "no"]},
    {"id": "invest_accounts", "group": "financial", "prompt": "Do you hold investment or brokerage accounts?",
     "kind": "single", "options": ["yes", "no"]},
    {"id": "donations", "group": "financial", "prompt": "Did you make charitable donations?",
     "kind": "single", "options": ["yes", "no"]},
    {"id": "loans", "group": "financial", "prompt": "Do you pay interest on loans (non-mortgage)?",
     "kind": "single", "options": ["yes", "no"]},
    {"id": "country", "group": "tax", "prompt": "What is your country of tax residence?",
     "kind": "single", "options": ["MX", "US", "other"]},
    {"id": "tax_regime", "group": "tax", "prompt": "Do you know your applicable tax regime?",
     "kind": "single", "options": ["yes", "no", "needs_confirmation"]},
    {"id": "filing_status", "group": "tax", "prompt": "What is your filing status?",
     "kind": "single", "options": ["single", "married", "other", "unknown"]},
    {"id": "docs_ready", "group": "tax", "prompt": "Do you have income/housing/medical documents ready to organize?",
     "kind": "single", "options": ["yes", "some", "no"]},
]

MAX_BASELINE = 24


def _norm_answer(a) -> list[str]:
    if a is None:
        return []
    if isinstance(a, list):
        return [str(x) for x in a]
    return [str(a)]


def visible_questions(answers: dict) -> list[dict]:
    """Return questions that apply given answers so far (adaptive skip)."""
    out = []
    for q in QUESTIONS:
        req = q.get("requires")
        if not req:
            out.append(q)
            continue
        prev = _norm_answer(answers.get(req["fact"]))
        if "has" in req and req["has"] not in prev:
            continue
        if "has_any" in req and not any(v in prev for v in req["has_any"]):
            continue
        out.append(q)
    return out
