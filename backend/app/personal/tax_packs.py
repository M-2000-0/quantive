"""Versioned tax-knowledge packs by (jurisdiction, tax year).

Honesty contract (enforced by tests):
- Every rule summary must tell the user to VERIFY against the cited authority.
- Sources name the authority + what to check, never a fabricated section number.
- No dollar savings, no eligibility guarantees — relevance + requirements only.
- Unknown/unsupported countries fall back to GEN (generic) rules only.

Jurisdiction codes: MX, US, BD, GEN (generic fallback).
"""
from __future__ import annotations

VERIFY_IRS = "IRS publications for the current tax year — verify before acting"
VERIFY_NBR = "NBR / Finance Act for the current assessment year — verify before acting"
VERIFY_SAT = "SAT / miscelánea fiscal vigente — verificar antes de actuar"
VERIFY_GEN = "Current rules of your jurisdiction — verify with a qualified professional"


def _rule(rid, juris, year, topic, title, summary, requirements, docs, sources):
    return {
        "id": rid, "jurisdiction": juris, "tax_year": year, "topic": topic,
        "title": title, "summary": summary, "requirements": requirements,
        "docs_required": docs, "limits": {},
        "sources": sources if isinstance(sources, list) else [sources],
        "effective_from": f"{year}-01-01", "effective_to": f"{year}-12-31",
    }


GEN_2026 = [
    _rule("GEN-2026-medical-expenses", "GEN", 2026, "health",
          "Medical expenses — potentially relevant",
          "Medical expenses are often jurisdiction-limited. Documentation required. Verify thresholds and eligible categories.",
          ["qualifying expenses", "receipts"], ["receipts", "insurance statements"], VERIFY_GEN),
    _rule("GEN-2026-retirement", "GEN", 2026, "retirement",
          "Retirement contributions — potentially relevant",
          "Retirement contributions may have limits or incentives depending on jurisdiction and account type. Verify.",
          ["eligible account"], ["contribution statements"], VERIFY_GEN),
    _rule("GEN-2026-education", "GEN", 2026, "education",
          "Education expenses — potentially relevant",
          "Education treatment varies widely by jurisdiction. Low default relevance until confirmed. Verify.",
          ["eligible expenses"], ["tuition receipts"], VERIFY_GEN),
    _rule("GEN-2026-home-office", "GEN", 2026, "work",
          "Home office — needs verification",
          "Home-office treatment depends on regime, exclusivity, and activity. High verification burden. Verify.",
          ["exclusive use evidence", "applicable regime"], ["expense records"], VERIFY_GEN),
    _rule("GEN-2026-housing-interest", "GEN", 2026, "housing",
          "Housing loan interest — potentially relevant",
          "Housing loan interest may be relevant depending on loan type, regime, and documentation. Verify.",
          ["qualifying loan", "applicable tax regime"], ["annual loan statement"], VERIFY_GEN),
    _rule("GEN-2026-donations", "GEN", 2026, "donations",
          "Charitable donations — potentially relevant",
          "Donation treatment (deduction vs credit, eligible recipients, receipt thresholds) varies by jurisdiction. Verify.",
          ["eligible recipient", "proof of donation"], ["donation receipts"], VERIFY_GEN),
]

MX_2026 = [
    _rule("MX-2026-mortgage-interest", "MX", 2026, "housing",
          "Mortgage interest — potentially relevant",
          "Mortgage interest may be relevant depending on regime and documentation. Requires verification. " + VERIFY_SAT,
          ["qualifying mortgage", "applicable tax regime"], ["annual mortgage statement (constancia anual)"],
          VERIFY_SAT),
]

US_2026 = [
    _rule("US-2026-mortgage-interest", "US", 2026, "housing",
          "Mortgage interest (Schedule A) — potentially relevant",
          "May be deductible if you itemize; compare against the standard deduction. Acquisition-debt limits apply. " + VERIFY_IRS,
          ["itemize deductions", "qualifying acquisition debt"], ["Form 1098", "loan statements"], VERIFY_IRS),
    _rule("US-2026-salt", "US", 2026, "housing",
          "State and local taxes (SALT) — check current cap",
          "SALT deductibility has a statutory cap that Congress has revisited — confirm the current-year cap before assuming anything. Itemizers only. " + VERIFY_IRS,
          ["itemize deductions", "current-year cap"], ["property tax bills", "state tax records"], VERIFY_IRS),
    _rule("US-2026-student-loan-interest", "US", 2026, "education",
          "Student loan interest — potentially relevant",
          "Up to a statutory annual maximum with income phaseouts; must verify current figures and eligibility. " + VERIFY_IRS,
          ["eligible loan", "income within phaseout range"], ["Form 1098-E", "loan statements"], VERIFY_IRS),
    _rule("US-2026-medical-75pct", "US", 2026, "health",
          "Medical expenses (7.5% AGI floor) — potentially relevant",
          "Only unreimbursed expenses above a percentage-of-AGI floor count, and only if you itemize. Verify the current floor. " + VERIFY_IRS,
          ["itemize deductions", "expenses above AGI floor"], ["receipts", "insurance statements"], VERIFY_IRS),
    _rule("US-2026-retirement", "US", 2026, "retirement",
          "Retirement contributions (401k / IRA) — potentially relevant",
          "Pre-tax limits and Traditional IRA deductibility phaseouts change yearly; Roth contributions are generally not deductible. " + VERIFY_IRS,
          ["eligible plan", "income within limits"], ["W-2 / 5498", "contribution statements"], VERIFY_IRS),
    _rule("US-2026-charitable", "US", 2026, "donations",
          "Charitable donations — potentially relevant",
          "Generally for itemizers, with AGI-percentage limits and substantiation thresholds. Verify current limits. " + VERIFY_IRS,
          ["itemize deductions", "eligible organization"], ["acknowledgment letters", "receipts"], VERIFY_IRS),
    _rule("US-2026-home-office", "US", 2026, "work",
          "Home office — needs verification",
          "Exclusive-and-regular-use test; simplified vs actual-expense methods. Employees vs self-employed differ. " + VERIFY_IRS,
          ["exclusive use evidence", "self-employment or eligible use"], ["expense records", "floor plan"], VERIFY_IRS),
]

BD_2026 = [
    _rule("BD-2026-investment-rebate", "BD", 2026, "retirement",
          "Investment tax rebate — potentially relevant",
          "Rebates on allowable investments (e.g. insurance premiums, DPS, savings instruments, equities) follow yearly caps and rates set in the Finance Act. Confirm the current assessment year's schedule. " + VERIFY_NBR,
          ["allowable investment", "current-year rebate schedule"], ["investment certificates", "premium receipts"], VERIFY_NBR),
    _rule("BD-2026-hra", "BD", 2026, "housing",
          "House rent allowance (salaried) — potentially relevant",
          "Salaried taxpayers may have an exempt portion of house rent allowance under yearly rules. Confirm the current exemption formula. " + VERIFY_NBR,
          ["salaried income", "actual rent paid"], ["rent receipts", "salary certificate"], VERIFY_NBR),
    _rule("BD-2026-savings-instruments", "BD", 2026, "financial",
          "Savings instruments (interest treatment) — potentially relevant",
          "Interest and encashment treatment of savings certificates and bonds follows NBR circulars that change periodically. Verify current circulars. " + VERIFY_NBR,
          ["qualifying instrument"], ["certificates", "interest statements"], VERIFY_NBR),
    _rule("BD-2026-rental-income", "BD", 2026, "housing",
          "Rental (house property) income deductions — potentially relevant",
          "Allowable deductions from rental income (repairs, municipal tax, etc.) follow yearly rules. Verify before computing. " + VERIFY_NBR,
          ["rental income declared"], ["rent deeds", "municipal tax receipts"], VERIFY_NBR),
]

PACKS: dict[tuple[str, int], list[dict]] = {
    ("GEN", 2026): GEN_2026,
    ("MX", 2026): MX_2026,
    ("US", 2026): US_2026,
    ("BD", 2026): BD_2026,
}

SUPPORTED_JURISDICTIONS = ["MX", "US", "BD"]


def rules_for(jurisdiction: str, tax_year: int = 2026) -> list[dict]:
    """Jurisdiction pack + generic fallback. Unknown countries get GEN only."""
    juris = (jurisdiction or "").upper()
    out = list(PACKS.get(("GEN", tax_year), []))
    if juris in SUPPORTED_JURISDICTIONS:
        out = list(PACKS.get((juris, tax_year), [])) + out
    return out


def normalize_country(value: str) -> str:
    v = (value or "").strip().upper()
    return v if v in SUPPORTED_JURISDICTIONS else "GEN"
