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

    def has_any(key: str, *vals: str) -> bool:
        fact_vals = facts.get(key, [])
        return any(v in fact_vals for v in vals)

    candidates: list[dict] = []

    # ── Housing & Mortgage ────────────────────────────────────────────
    if has("housing", "mortgage") or has("mortgage_detail", "yes"):
        candidates.append({"title": "Mortgage interest", "category": "housing", "relevance": "high",
                           "why": "You indicated that you have a mortgage. Mortgage interest is deductible if you itemize deductions.",
                           "needs_info": ["Whether you itemize", "Loan type (acquisition vs home equity)"],
                           "needs_docs": ["Form 1098", "Annual mortgage statement"],
                           "rule_refs": _ref(juris, f"{juris}-2026-mortgage-interest", "GEN-2026-housing-interest"),
                           "next_action": "Check if itemizing exceeds the standard deduction. Upload Form 1098."})
        # Mortgage points
        if has("tax_regime", "yes") or has("tax_regime", "needs_confirmation"):
            candidates.append({"title": "Mortgage points", "category": "housing", "relevance": "medium",
                               "why": "If you paid mortgage points at closing, they may be deductible this year.",
                               "needs_info": ["Whether points were paid", "Loan type"],
                               "needs_docs": ["HUD-1 settlement statement", "Form 1098"],
                               "rule_refs": _ref(juris, "US-2026-mortgage-points"),
                               "next_action": "Review your closing documents for points paid."})

    # ── SALT (State and Local Taxes) ──────────────────────────────────
    if juris == "US" and (has("employment_detail", "yes") or has("housing", "own") or has("housing", "mortgage")):
        candidates.append({"title": "State and local taxes (SALT)", "category": "housing", "relevance": "medium",
                           "why": "You may pay deductible state/local income or property taxes. The SALT deduction is capped at $10,000 ($5,000 MFS).",
                           "needs_info": ["Whether you itemize", "State tax paid", "Property tax paid"],
                           "needs_docs": ["Property tax bills", "State income tax records"],
                           "rule_refs": ["US-2026-salt"],
                           "next_action": "Add up state income tax + property tax. If combined > $10K, the cap applies."})
        # State tax refund
        candidates.append({"title": "State tax refund recovery", "category": "housing", "relevance": "low",
                           "why": "If you itemized last year and received a state tax refund, it may be taxable this year.",
                           "needs_info": ["Prior year filing status (itemize vs standard)", "State refund amount"],
                           "needs_docs": ["Form 1099-G", "Prior year return"],
                           "rule_refs": ["US-2026-state-refund"],
                           "next_action": "Check Form 1099-G received in January."})

    # ── Medical & Health ──────────────────────────────────────────────
    if has("medical_exp", "yes"):
        candidates.append({"title": "Medical expenses (7.5% AGI floor)", "category": "health", "relevance": "medium",
                           "why": "You reported medical expenses. Only unreimbursed expenses exceeding 7.5% of AGI are deductible if you itemize.",
                           "needs_info": ["Total unreimbursed medical expenses", "Estimated AGI"],
                           "needs_docs": ["Receipts", "Insurance statements (EOB)", "Prescription records"],
                           "rule_refs": _ref(juris, "US-2026-medical-75pct", "GEN-2026-medical-expenses"),
                           "next_action": "Add up all medical expenses. Compare to 7.5% of your AGI."})

    if has("health_insurance", "yes"):
        if has_any("income_sources", "business", "freelance"):
            candidates.append({"title": "Self-employed health insurance deduction", "category": "health", "relevance": "high",
                               "why": "If you're self-employed and pay your own health insurance, premiums may be fully deductible above-the-line.",
                               "needs_info": ["Self-employment status", "Whether eligible for employer coverage"],
                               "needs_docs": ["Premium payment records", "Form 1095-A/B/C"],
                               "rule_refs": ["US-2026-se-health-insurance"],
                               "next_action": "Confirm you're not eligible for employer-subsidized coverage."})
        else:
            candidates.append({"title": "HSA/FSA optimization", "category": "health", "relevance": "medium",
                               "why": "If you have a high-deductible health plan, an HSA offers triple tax advantage.",
                               "needs_info": ["HDHP enrollment status", "Current HSA/FSA balances"],
                               "needs_docs": ["HSA/FSA statements"],
                               "rule_refs": ["US-2026-hsa", "US-2026-fsa"],
                               "next_action": "Check if your plan qualifies for HSA contributions."})

    # ── Retirement ────────────────────────────────────────────────────
    if has("retirement", "yes"):
        candidates.append({"title": "Retirement contributions", "category": "retirement", "relevance": "high",
                           "why": "You contribute to a retirement account. Verify you're maximizing tax-advantaged contributions.",
                           "needs_info": ["Account type (401k/IRA/Roth/SEP)", "Annual contribution amount", "Age"],
                           "needs_docs": ["Contribution statements", "W-2 Box 12", "Form 5498"],
                           "rule_refs": _ref(juris, "US-2026-401k", "US-2026-traditional-ira", "US-2026-roth-ira"),
                           "next_action": "Check if you've hit the annual limit. Consider catch-up if 50+."})
        # Roth conversion opportunity
        if has_any("income_sources", "business", "freelance") or has("filing_status", "single"):
            candidates.append({"title": "Roth conversion ladder", "category": "retirement", "relevance": "medium",
                               "why": "If you're in a lower income year, converting Traditional IRA/401(k) to Roth can save on lifetime taxes.",
                               "needs_info": ["Traditional IRA/401(k) balance", "Current year income estimate"],
                               "needs_docs": ["Account statements"],
                               "rule_refs": ["US-2026-roth-conversion"],
                               "next_action": "Estimate this year's income. If unusually low, consider a partial conversion."})
        # SEP-IRA for self-employed
        if has_any("income_sources", "business", "freelance"):
            candidates.append({"title": "SEP-IRA contributions", "category": "retirement", "relevance": "high",
                               "why": "As a self-employed individual, a SEP-IRA allows contributions up to 25% of net income.",
                               "needs_info": ["Net self-employment income", "Current SEP-IRA balance"],
                               "needs_docs": ["Business financials", "SEP-IRA contribution records"],
                               "rule_refs": ["US-2026-sep-ira"],
                               "next_action": "Calculate your net SE income and determine maximum SEP contribution."})
        # Retirement Saver's Credit
        candidates.append({"title": "Retirement Savings Credit", "category": "retirement", "relevance": "low",
                           "why": "If your AGI is below the threshold, you may qualify for a credit on retirement contributions.",
                           "needs_info": ["AGI estimate", "Filing status"],
                           "needs_docs": ["Contribution records"],
                           "rule_refs": ["US-2026-education-credit-saver"],
                           "next_action": "Check the current income thresholds for the Saver's Credit."})

    # ── Education ─────────────────────────────────────────────────────
    if has("education_exp", "yes"):
        if juris == "US" and has("loans", "yes"):
            candidates.append({"title": "Student loan interest", "category": "education", "relevance": "medium",
                               "why": "You reported education expenses and loan interest. Up to $2,500 deductible above-the-line.",
                               "needs_info": ["Eligible student loan", "Income phaseout check"],
                               "needs_docs": ["Form 1098-E"],
                               "rule_refs": ["US-2026-student-loan-interest"],
                               "next_action": "Verify income is within the phaseout range."})
        else:
            candidates.append({"title": "Education expenses", "category": "education", "relevance": "low",
                               "why": "You reported education expenses. May qualify for American Opportunity or Lifetime Learning credit.",
                               "needs_info": ["Eligible recipient", "Institution type", "Enrollment status"],
                               "needs_docs": ["Form 1098-T", "Tuition receipts"],
                               "rule_refs": _ref(juris, "US-2026-american-opportunity", "US-2026-lifetime-learning", "GEN-2026-education"),
                               "next_action": "Determine if AOTC (first 4 years) or LLC applies."})
    elif juris == "US" and has("loans", "yes"):
        candidates.append({"title": "Student loan interest", "category": "education", "relevance": "medium",
                           "why": "You pay interest on loans. If they're qualified student loans, up to $2,500 is deductible.",
                           "needs_info": ["Whether the loan is a qualified student loan", "Income range"],
                           "needs_docs": ["Form 1098-E"],
                           "rule_refs": ["US-2026-student-loan-interest"],
                           "next_action": "Confirm this is an eligible student loan (not a personal loan)."})
    # 529 plan opportunity
    if has_any("family", "children", "dependents") or has("dependents_count", "1") or has("dependents_count", "2") or has("dependents_count", "3+"):
        candidates.append({"title": "529 Education Savings Plan", "category": "education", "relevance": "medium",
                           "why": "If you have children, a 529 plan offers tax-free growth for education expenses.",
                           "needs_info": ["Children's ages", "Existing education savings"],
                           "needs_docs": ["529 plan statements (if existing)"],
                           "rule_refs": ["US-2026-529-plan"],
                           "next_action": "Consider opening a 529 plan if you haven't already."})
    # Educator expenses
    if has("employment_detail", "yes"):
        candidates.append({"title": "Educator expense deduction", "category": "education", "relevance": "low",
                           "why": "If you're a K-12 teacher, you can deduct up to $300 in unreimbursed classroom expenses above-the-line.",
                           "needs_info": ["Whether you're a K-12 educator", "Classroom expenses"],
                           "needs_docs": ["Expense receipts"],
                           "rule_refs": ["US-2026-educator-expenses"],
                           "next_action": "Track classroom supplies purchased out-of-pocket."})

    # ── Work & Home Office ────────────────────────────────────────────
    if has("home_office", "yes"):
        candidates.append({"title": "Home office deduction", "category": "work", "relevance": "high",
                           "why": "You have a dedicated home office. Self-employed individuals can deduct a portion of home expenses.",
                           "needs_info": ["Self-employment status", "Office square footage", "Total home square footage"],
                           "needs_docs": ["Expense records", "Photos of dedicated space"],
                           "rule_refs": _ref(juris, "US-2026-home-office", "GEN-2026-home-office"),
                           "next_action": "Measure your home office. Choose simplified ($5/sqft) or actual expenses method."})
    if has("work_expenses", "yes"):
        candidates.append({"title": "Business expense deduction", "category": "work", "relevance": "medium",
                           "why": "Work-related expenses may be deductible if you're self-employed or a qualifying employee.",
                           "needs_info": ["Employment type", "Expense categories"],
                           "needs_docs": ["Receipts", "Expense records"],
                           "rule_refs": _ref(juris, "US-2026-business-expenses"),
                           "next_action": "Organize receipts by category (supplies, software, travel, etc.)."})
    # Vehicle expenses
    if has("work_expenses", "yes"):
        candidates.append({"title": "Vehicle expense deduction", "category": "work", "relevance": "low",
                           "why": "If you use a vehicle for business, you may deduct mileage or actual expenses.",
                           "needs_info": ["Business vehicle use percentage", "Mileage records"],
                           "needs_docs": ["Mileage log", "Vehicle expense receipts"],
                           "rule_refs": ["US-2026-vehicle-expenses"],
                           "next_action": "Start a mileage log if you haven't already."})

    # ── Family & Dependents ───────────────────────────────────────────
    if has_any("family", "children", "dependents"):
        candidates.append({"title": "Child Tax Credit", "category": "family", "relevance": "high",
                           "why": "You have qualifying children. The Child Tax Credit provides a credit per child under 17.",
                           "needs_info": ["Number of qualifying children under 17", "Income level"],
                           "needs_docs": ["SSN for each child"],
                           "rule_refs": ["US-2026-child-tax-credit"],
                           "next_action": "Ensure each child has an SSN. Check income phaseout thresholds."})
        candidates.append({"title": "Child and Dependent Care Credit", "category": "family", "relevance": "medium",
                           "why": "If you pay for child care while you work, you may qualify for the Child and Dependent Care Credit.",
                           "needs_info": ["Care expenses", "Care provider info", "Income level"],
                           "needs_docs": ["Care provider receipts", "Provider EIN/SSN"],
                           "rule_refs": ["US-2026-child-care-credit", "US-2026-dependent-care-fsa"],
                           "next_action": "Coordinate DCFSA and CDCC — you can't double-dip the same expenses."})
    if has("dependents_count", "1") or has("dependents_count", "2") or has("dependents_count", "3+"):
        # Dependent care FSA
        candidates.append({"title": "Dependent Care FSA", "category": "family", "relevance": "medium",
                           "why": "If your employer offers a Dependent Care FSA, you can set aside up to $5,000 pre-tax for child care.",
                           "needs_info": ["Employer DCFSA availability", "Care expenses"],
                           "needs_docs": ["DCFSA enrollment documents"],
                           "rule_refs": ["US-2026-dependent-care-fsa"],
                           "next_action": "Check if your employer offers a DCFSA during open enrollment."})

    # ── Charitable Donations ──────────────────────────────────────────
    if has("donations", "yes"):
        candidates.append({"title": "Charitable donations", "category": "donations", "relevance": "medium" if juris == "US" else "low",
                           "why": "You made charitable donations. If you itemize, these are deductible with AGI limits.",
                           "needs_info": ["Whether you itemize", "Total donation amount", "Type of donation (cash vs property)"],
                           "needs_docs": ["Donation receipts", "Acknowledgment letters over $250"],
                           "rule_refs": _ref(juris, "US-2026-charitable", "GEN-2026-donations"),
                           "next_action": "Gather receipts. Consider bunching donations for itemization."})
        # Charitable bunching
        candidates.append({"title": "Charitable contribution bunching", "category": "donations", "relevance": "medium",
                           "why": "Bunching two years of donations into one year may push you above the standard deduction threshold.",
                           "needs_info": ["Current year standard deduction vs itemized total", "Donation history"],
                           "needs_docs": ["Donation receipts", "DAF statements"],
                           "rule_refs": ["US-2026-charitable-bunching"],
                           "next_action": "Compare your potential itemized deductions to the standard deduction."})

    # ── Investments ───────────────────────────────────────────────────
    if has("invest_accounts", "yes") or has("investment_income", "yes"):
        candidates.append({"title": "Tax-loss harvesting", "category": "investments", "relevance": "high",
                           "why": "If your investments have unrealized losses, harvesting them can offset gains and reduce taxes.",
                           "needs_info": ["Unrealized gains/losses", "Cost basis method"],
                           "needs_docs": ["1099-B", "Cost basis statements"],
                           "rule_refs": ["US-2026-tax-loss-harvesting"],
                           "next_action": "Review your portfolio for positions with unrealized losses before year-end."})
        candidates.append({"title": "Long-term capital gains optimization", "category": "investments", "relevance": "medium",
                           "why": "Holding investments for 1+ year qualifies for lower capital gains rates (0/15/20%).",
                           "needs_info": ["Holding periods", "Expected income"],
                           "needs_docs": ["1099-B", "Purchase confirmations"],
                           "rule_refs": ["US-2026-capital-gains-rates"],
                           "next_action": "Review positions approaching 1-year holding period."})
        candidates.append({"title": "Foreign Tax Credit", "category": "investments", "relevance": "low",
                           "why": "If you invest in foreign funds or have foreign income, you may be eligible for the Foreign Tax Credit.",
                           "needs_info": ["Foreign investments", "Foreign taxes paid"],
                           "needs_docs": ["Foreign tax statements", "Form 1116"],
                           "rule_refs": ["US-2026-foreign-tax-credit"],
                           "next_action": "Check your brokerage statements for foreign taxes withheld."})

    # ── Self-Employment & Business ────────────────────────────────────
    if has_any("income_sources", "business", "freelance"):
        candidates.append({"title": "Self-employment tax deduction", "category": "business", "relevance": "high",
                           "why": "You can deduct 50% of self-employment tax as an above-the-line deduction.",
                           "needs_info": ["Net self-employment income"],
                           "needs_docs": ["Schedule SE", "Schedule C"],
                           "rule_refs": ["US-2026-se-tax-deduction"],
                           "next_action": "Ensure Schedule SE is filed with your return."})
        candidates.append({"title": "QBI deduction (Section 199A)", "category": "business", "relevance": "high",
                           "why": "As a pass-through business owner, you may deduct up to 20% of qualified business income.",
                           "needs_info": ["QBI amount", "W-2 wages paid", "Income level"],
                           "needs_docs": ["Schedule K-1", "Business financials"],
                           "rule_refs": ["US-2026-qualified-business-income"],
                           "next_action": "Calculate QBI and check W-2 wage limitations."})
        candidates.append({"title": "Section 179 expensing", "category": "business", "relevance": "medium",
                           "why": "If you purchased business assets, Section 179 allows immediate expensing up to the annual limit.",
                           "needs_info": ["Business asset purchases this year", "Total Section 179 claimed"],
                           "needs_docs": ["Asset purchase invoices", "Asset records"],
                           "rule_refs": ["US-2026-section-179"],
                           "next_action": "List all business asset purchases and their costs."})
        candidates.append({"title": "Startup costs deduction", "category": "business", "relevance": "low",
                           "why": "If you started a new business this year, up to $5,000 in startup costs may be deductible.",
                           "needs_info": ["New business started this year", "Startup expense total"],
                           "needs_docs": ["Startup expense records"],
                           "rule_refs": ["US-2026-startup-costs"],
                           "next_action": "Track all pre-launch expenses separately."})
        # R&D Credit
        candidates.append({"title": "R&D Tax Credit", "category": "business", "relevance": "low",
                           "why": "If your business conducts qualified research, you may be eligible for the R&D tax credit.",
                           "needs_info": ["Qualified research expenses", "Research activity records"],
                           "needs_docs": ["Research expense records", "Project documentation"],
                           "rule_refs": ["US-2026-rd-credit"],
                           "next_action": "Document qualifying research activities and expenses."})

    # ── Rental Income ─────────────────────────────────────────────────
    if has("rental_income", "yes"):
        if juris == "US":
            candidates.append({"title": "Rental property expenses", "category": "business", "relevance": "high",
                               "why": "Rental property income allows deductions for mortgage interest, depreciation, repairs, insurance, and property tax.",
                               "needs_info": ["Rental income amount", "Expense categories", "Depreciation basis"],
                               "needs_docs": ["Rental records", "Expense receipts", "Property tax bills"],
                               "rule_refs": ["US-2026-rental-expenses"],
                               "next_action": "Organize all rental-related expenses and depreciation schedules."})
        else:
            candidates.append({"title": "Rental income deductions", "category": "housing", "relevance": "medium",
                               "why": "You receive rental income with potentially allowable deductions.",
                               "needs_info": ["Declared rental income", "Deductible expenses"],
                               "needs_docs": ["Rent deeds", "Municipal tax receipts"],
                               "rule_refs": _ref(juris, "BD-2026-rental-income"),
                               "next_action": "Verify allowable deductions before computing."})

    # ── Energy ────────────────────────────────────────────────────────
    if has_any("housing", "own", "mortgage"):
        candidates.append({"title": "Energy efficiency home improvements", "category": "energy", "relevance": "low",
                           "why": "Energy-efficient home improvements (windows, insulation, HVAC) may qualify for tax credits.",
                           "needs_info": ["Planned or completed energy improvements"],
                           "needs_docs": ["Receipts", "Manufacturer certifications"],
                           "rule_refs": ["US-2026-energy-efficient-home"],
                           "next_action": "Keep receipts for any energy-efficient home improvements."})
        candidates.append({"title": "Solar/清洁能源 credit", "category": "energy", "relevance": "low",
                           "why": "Installing solar panels or other clean energy systems qualifies for a 30% tax credit.",
                           "needs_info": ["Solar installation plans or recent purchase"],
                           "needs_docs": ["Installation invoices", "Manufacturer certifications"],
                           "rule_refs": ["US-2026-solar-credit"],
                           "next_action": "If considering solar, the 30% credit is available through 2032."})

    # ── Compliance & Deadlines ────────────────────────────────────────
    if has_any("income_sources", "business", "freelance"):
        candidates.append({"title": "Estimated tax payments", "category": "compliance", "relevance": "high",
                           "why": "If you have self-employment income, quarterly estimated tax payments are required to avoid penalties.",
                           "needs_info": ["Expected annual tax liability", "Current withholding"],
                           "needs_docs": ["1040-ES", "Payment records"],
                           "rule_refs": ["US-2026-estimated-tax", "US-2026-safe-harbor"],
                           "next_action": "Calculate your estimated tax liability and make quarterly payments."})

    # ── Foreign Tax Credit ────────────────────────────────────────────
    if has("invest_accounts", "yes"):
        candidates.append({"title": "Net Investment Income Tax awareness", "category": "investments", "relevance": "low",
                           "why": "If your MAGI exceeds $200K (single) / $250K (MFJ), a 3.8% surtax applies to net investment income.",
                           "needs_info": ["MAGI estimate", "Investment income total"],
                           "needs_docs": ["Investment statements"],
                           "rule_refs": ["US-2026-net-investment-income"],
                           "next_action": "Monitor your MAGI if you're near the threshold."})

    # ── Sovereign-tier extras ─────────────────────────────────────────
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

    # ── Persist opportunities ─────────────────────────────────────────
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
