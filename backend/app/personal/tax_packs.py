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
    # ── Deductions (Schedule A / Above-the-Line) ──────────────────────
    _rule("US-2026-mortgage-interest", "US", 2026, "housing",
          "Mortgage interest (IRC §163) — potentially relevant",
          "May be deductible if you itemize; compare against the standard deduction. Acquisition-debt limits apply. " + VERIFY_IRS,
          ["itemize deductions", "qualifying acquisition debt"], ["Form 1098", "loan statements"], VERIFY_IRS),
    _rule("US-2026-salt", "US", 2026, "housing",
          "State and local taxes (IRC §164, $10K cap) — check current cap",
          "SALT deductibility has a $10,000 cap ($5,000 MFS). Itemizers only. Confirm current-year cap before assuming. " + VERIFY_IRS,
          ["itemize deductions"], ["property tax bills", "state income tax records"], VERIFY_IRS),
    _rule("US-2026-charitable", "US", 2026, "donations",
          "Charitable contributions (IRC §170) — potentially relevant",
          "Generally for itemizers, with AGI-percentage limits (60% cash, 30% appreciated property). Verify current limits. " + VERIFY_IRS,
          ["itemize deductions", "eligible organization"], ["receipts", "acknowledgment letters"], VERIFY_IRS),
    _rule("US-2026-charitable-bunching", "US", 2026, "donations",
          "Charitable contribution bunching — strategic opportunity",
          "Bunching two years of donations into one year may push you above the standard deduction threshold. Consider a donor-advised fund. " + VERIFY_IRS,
          ["itemize deductions", "eligible organization"], ["receipts", "DAF statements"], VERIFY_IRS),
    _rule("US-2026-medical-75pct", "US", 2026, "health",
          "Medical expenses (IRC §213, 7.5% AGI floor) — potentially relevant",
          "Only unreimbursed expenses exceeding 7.5% of AGI count, and only if you itemize. Verify the current floor. " + VERIFY_IRS,
          ["itemize deductions", "expenses above AGI floor"], ["receipts", "insurance statements"], VERIFY_IRS),
    _rule("US-2026-student-loan-interest", "US", 2026, "education",
          "Student loan interest (IRC §221) — potentially relevant",
          "Up to $2,500/year with income phaseouts; above-the-line deduction. Verify current phaseout ranges. " + VERIFY_IRS,
          ["eligible loan", "income within phaseout range"], ["Form 1098-E"], VERIFY_IRS),
    _rule("US-2026-home-office", "US", 2026, "work",
          "Home office (IRC §168(f)(1)) — needs verification",
          "Exclusive-and-regular-use test; simplified ($5/sqft, max $1,500) vs actual-expense method. Self-employed only. " + VERIFY_IRS,
          ["exclusive use evidence", "self-employment income"], ["expense records", "floor plan"], VERIFY_IRS),
    _rule("US-2026-hsa", "US", 2026, "health",
          "Health Savings Account (IRC §223) — potentially relevant",
          "Triple tax advantage: deductible contributions, tax-free growth, tax-free qualified withdrawals. 2026 limits apply. " + VERIFY_IRS,
          ["high-deductible health plan", "no other coverage"], ["Form 5498-SA", "Form 1099-SA"], VERIFY_IRS),
    _rule("US-2026-fsa", "US", 2026, "health",
          "Flexible Spending Account (IRC §125) — potentially relevant",
          "Pre-tax contributions for medical or dependent care expenses. Use-it-or-lose-it rules apply. " + VERIFY_IRS,
          ["employer FSA plan"], ["FSA election statements"], VERIFY_IRS),
    _rule("US-2026-dependent-care-fsa", "US", 2026, "family",
          "Dependent Care FSA (IRC §129) — potentially relevant",
          "Up to $5,000/year pre-tax for child/dependent care while you work. Coordinate with child care credit. " + VERIFY_IRS,
          ["qualifying dependent", "work-related care"], ["care provider receipts", "EIN/SSN"], VERIFY_IRS),

    # ── Retirement ────────────────────────────────────────────────────
    _rule("US-2026-401k", "US", 2026, "retirement",
          "401(k) contributions (IRC §402(g)) — potentially relevant",
          "Employee elective deferrals up to $23,500 (2026); catch-up for 50+. Employer match is additional. " + VERIFY_IRS,
          ["employer 401(k) plan"], ["W-2 Box 12"], VERIFY_IRS),
    _rule("US-2026-traditional-ira", "US", 2026, "retirement",
          "Traditional IRA deduction (IRC §219) — potentially relevant",
          "Deductible if not covered by workplace plan, or if below income phaseout. Verify current limits. " + VERIFY_IRS,
          ["eligible IRA", "income within limits"], ["Form 5498", "contribution receipts"], VERIFY_IRS),
    _rule("US-2026-roth-ira", "US", 2026, "retirement",
          "Roth IRA contributions (IRC §408A) — strategic opportunity",
          "Not deductible, but tax-free growth and withdrawals. Income phaseouts apply. Backdoor Roth may be available. " + VERIFY_IRS,
          ["income within phaseout"], ["Form 5498"], VERIFY_IRS),
    _rule("US-2026-roth-conversion", "US", 2026, "retirement",
          "Roth conversion ladder — strategic opportunity",
          "Convert Traditional IRA/401(k) to Roth in low-income years. Pay tax now for tax-free withdrawals later. Multi-year strategy. " + VERIFY_IRS,
          ["Traditional IRA or 401(k) balance", "low-income year"], ["conversion records"], VERIFY_IRS),
    _rule("US-2026-sep-ira", "US", 2026, "retirement",
          "SEP-IRA contributions (IRC §408(k)) — potentially relevant",
          "Self-employed can contribute up to 25% of net self-employment income, up to annual cap. " + VERIFY_IRS,
          ["self-employment income"], ["SEP-IRA contribution records"], VERIFY_IRS),
    _rule("US-2026-ira-catchup", "US", 2026, "retirement",
          "IRA/401(k) catch-up contributions (IRC §219(b)) — potentially relevant",
          "Age 50+ catch-up contributions: additional $7,500 for 401(k), $1,000 for IRA. Verify current amounts. " + VERIFY_IRS,
          ["age 50 or older"], ["contribution records"], VERIFY_IRS),
    _rule("US-2026-education-credit-saver", "US", 2026, "retirement",
          "Retirement Savings Contribution Credit (IRC §25B) — potentially relevant",
          "Credit for retirement contributions if AGI below threshold. Non-refundable. Verify current limits. " + VERIFY_IRS,
          ["AGI below threshold", "retirement contribution"], ["contribution records"], VERIFY_IRS),

    # ── Family & Dependents ───────────────────────────────────────────
    _rule("US-2026-child-tax-credit", "US", 2026, "family",
          "Child Tax Credit (IRC §24) — potentially relevant",
          "Credit per qualifying child under 17. Phaseout begins at $400K MFJ/$200K other. Verify current amounts. " + VERIFY_IRS,
          ["qualifying child under 17"], ["SSN for each child"], VERIFY_IRS),
    _rule("US-2026-child-care-credit", "US", 2026, "family",
          "Child and Dependent Care Credit (IRC §21) — potentially relevant",
          "Credit for work-related care expenses for children under 13 or disabled dependents. Percentage varies by AGI. " + VERIFY_IRS,
          ["qualifying dependent", "work-related care"], ["care provider receipts", "EIN/SSN"], VERIFY_IRS),
    _rule("US-2026-adoption-credit", "US", 2026, "family",
          "Adoption Credit (IRC §23) — potentially relevant",
          "Credit for qualified adoption expenses. Refundable portion may apply. Verify current limits. " + VERIFY_IRS,
          ["qualified adoption"], ["adoption documents", "expense receipts"], VERIFY_IRS),
    _rule("US-2026-dependent-exemption", "US", 2026, "family",
          "Dependent exemptions — currently suspended",
          "Personal exemptions are suspended through 2025 under TCJA. Verify whether extended. " + VERIFY_IRS,
          ["dependents"], [], VERIFY_IRS),

    # ── Education ─────────────────────────────────────────────────────
    _rule("US-2026-american-opportunity", "US", 2026, "education",
          "American Opportunity Tax Credit (IRC §25A) — potentially relevant",
          "Up to $2,500/student for first 4 years of undergrad. 40% refundable. Income phaseouts apply. " + VERIFY_IRS,
          ["enrolled at least half-time", "first 4 years of college"], ["Form 1098-T"], VERIFY_IRS),
    _rule("US-2026-lifetime-learning", "US", 2026, "education",
          "Lifetime Learning Credit (IRC §25A) — potentially relevant",
          "Up to $2,000 per return for tuition and fees. No limit on years. Income phaseouts. " + VERIFY_IRS,
          ["qualified education expenses"], ["Form 1098-T"], VERIFY_IRS),
    _rule("US-2026-529-plan", "US", 2026, "education",
          "529 Education Savings Plan — strategic opportunity",
          "Tax-free growth and withdrawals for qualified education expenses. Up to $10,000/year for K-12 tuition. " + VERIFY_IRS,
          ["529 plan account"], ["529 distribution statements"], VERIFY_IRS),
    _rule("US-2026-employer-education", "US", 2026, "education",
          "Employer education assistance (IRC §127) — potentially relevant",
          "Up to $5,250/year employer-provided education assistance is tax-free. Verify current limit. " + VERIFY_IRS,
          ["employer education benefit"], ["employer documentation"], VERIFY_IRS),

    # ── Investment & Capital Gains ────────────────────────────────────
    _rule("US-2026-tax-loss-harvesting", "US", 2026, "investments",
          "Tax-loss harvesting (IRC §1211/§1212) — strategic opportunity",
          "Offset capital gains with capital losses. Up to $3,000 net loss deduction against ordinary income. Wash sale rules apply. " + VERIFY_IRS,
          ["investment accounts with losses"], ["1099-B", "cost basis records"], VERIFY_IRS),
    _rule("US-2026-capital-gains-rates", "US", 2026, "investments",
          "Long-term capital gains rates (IRC §1(h)) — strategic opportunity",
          "Long-term gains taxed at 0%, 15%, or 20% depending on income. Net Investment Income Tax of 3.8% may apply. " + VERIFY_IRS,
          ["investment income"], ["1099-B", "1099-DIV"], VERIFY_IRS),
    _rule("US-2026-investment-interest", "US", 2026, "investments",
          "Investment interest expense (IRC §163(d)) — potentially relevant",
          "Deductible up to net investment income. Carryforward unused amounts. " + VERIFY_IRS,
          ["investment interest expense", "net investment income"], ["brokerage statements"], VERIFY_IRS),
    _rule("US-2026-qualified-dividends", "US", 2026, "investments",
          "Qualified dividend tax rates (IRC §1(h)) — strategic opportunity",
          "Qualified dividends taxed at capital gains rates (0/15/20%) rather than ordinary income rates. " + VERIFY_IRS,
          ["dividend income"], ["1099-DIV"], VERIFY_IRS),
    _rule("US-2026-qualified-business-income", "US", 2026, "business",
          "QBI deduction (IRC §199A) — potentially relevant",
          "Up to 20% deduction for qualified business income from pass-through entities. Income thresholds and W-2 limits apply. " + VERIFY_IRS,
          ["pass-through business income"], ["Schedule K-1", "business records"], VERIFY_IRS),

    # ── Self-Employment & Business ────────────────────────────────────
    _rule("US-2026-se-tax-deduction", "US", 2026, "business",
          "Self-employment tax deduction (IRC §164(f)) — potentially relevant",
          "Deductible portion (50%) of self-employment tax. Above-the-line deduction. " + VERIFY_IRS,
          ["self-employment income"], ["Schedule SE", "Schedule C"], VERIFY_IRS),
    _rule("US-2026-se-health-insurance", "US", 2026, "business",
          "Self-employed health insurance deduction (IRC §162(l)) — potentially relevant",
          "Above-the-line deduction for health insurance premiums if not eligible for employer plan. " + VERIFY_IRS,
          ["self-employment income", "no employer coverage"], ["premium payments", "Form 1095-A/B/C"], VERIFY_IRS),
    _rule("US-2026-business-expenses", "US", 2026, "business",
          "Business expenses (IRC §162) — potentially relevant",
          "Ordinary and necessary business expenses are deductible. Must be directly related to business. " + VERIFY_IRS,
          ["self-employment or business income"], ["receipts", "business records"], VERIFY_IRS),
    _rule("US-2026-section-179", "US", 2026, "business",
          "Section 179 expensing (IRC §179) — potentially relevant",
          "Immediate expensing of qualifying business assets up to annual limit. Phaseout begins at spending threshold. " + VERIFY_IRS,
          ["business asset purchase"], ["invoices", "asset records"], VERIFY_IRS),
    _rule("US-2026-depreciation", "US", 2026, "business",
          "MACRS depreciation (IRC §167/§168) — potentially relevant",
          "Accelerated depreciation for business assets. Bonus depreciation percentage changing yearly. " + VERIFY_IRS,
          ["business asset purchase"], ["asset records", "depreciation schedules"], VERIFY_IRS),
    _rule("US-2026-startup-costs", "US", 2026, "business",
          "Startup costs (IRC §195) — potentially relevant",
          "Deduct up to $5,000 in startup costs in year one (reduced if costs exceed $50K). Remainder amortized over 180 months. " + VERIFY_IRS,
          ["new business startup"], ["startup expense records"], VERIFY_IRS),
    _rule("US-2026-home-office-business", "US", 2026, "business",
          "Home office — self-employed (IRC §168(f)(1)) — potentially relevant",
          "Dedicate space exclusively for business. Simplified method ($5/sqft, max 300sqft) or actual expenses. " + VERIFY_IRS,
          ["exclusive use space", "self-employment income"], ["expense records", "photos"], VERIFY_IRS),
    _rule("US-2026-vehicle-expenses", "US", 2026, "business",
          "Vehicle expenses (IRC §162/§274) — potentially relevant",
          "Standard mileage rate or actual expenses for business use of vehicle. Must maintain mileage log. " + VERIFY_IRS,
          ["business vehicle use"], ["mileage log", "vehicle expenses"], VERIFY_IRS),
    _rule("US-2026-rental-expenses", "US", 2026, "business",
          "Rental property expenses (IRC §212/§274) — potentially relevant",
          "Mortgage interest, property tax, depreciation, repairs, insurance deductible against rental income. " + VERIFY_IRS,
          ["rental property income"], ["rental records", "expense receipts"], VERIFY_IRS),
    _rule("US-2026-bad-debt", "US", 2026, "business",
          "Business bad debt (IRC §166) — potentially relevant",
          "Deduct debts that become worthless during the tax year. Must have been included in income or be directly related to business. " + VERIFY_IRS,
          ["uncollectible business debt"], ["debt records", "collection attempts"], VERIFY_IRS),
    _rule("US-2026-rd-credit", "US", 2026, "business",
          "Research & Development Credit (IRC §41) — potentially relevant",
          "Credit for qualified research expenses. Small business alternative credit available. " + VERIFY_IRS,
          ["qualified R&D expenses"], ["research records", "expense documentation"], VERIFY_IRS),

    # ── Energy & Environment ──────────────────────────────────────────
    _rule("US-2026-energy-efficient-home", "US", 2026, "energy",
          "Energy Efficient Home Improvement Credit (IRC §25C) — potentially relevant",
          "Credit for qualifying energy-efficient home improvements (windows, doors, insulation, HVAC). Annual limits apply. " + VERIFY_IRS,
          ["energy-efficient home improvements"], ["receipts", "manufacturer certifications"], VERIFY_IRS),
    _rule("US-2026-solar-credit", "US", 2026, "energy",
          "Residential Clean Energy Credit (IRC §25D) — potentially relevant",
          "30% credit for solar electric, solar water heating, fuel cells, wind energy. No annual cap. Carryforward available. " + VERIFY_IRS,
          ["solar or clean energy installation"], ["installation invoices", "manufacturer certifications"], VERIFY_IRS),
    _rule("US-2026-ev-credit", "US", 2026, "energy",
          "Clean Vehicle Credit (IRC §30D) — potentially relevant",
          "Up to $7,500 credit for new EVs meeting assembly and battery requirements. Income and price caps apply. " + VERIFY_IRS,
          ["new qualifying EV purchase"], ["vehicle identification", "purchase documents"], VERIFY_IRS),
    _rule("US-2026-used-ev-credit", "US", 2026, "energy",
          "Used Clean Vehicle Credit (IRC §25E) — potentially relevant",
          "Up to $4,000 credit for used EVs from dealers. Income cap and price cap apply. " + VERIFY_IRS,
          ["used qualifying EV purchase from dealer"], ["purchase documents", "dealer records"], VERIFY_IRS),

    # ── Other Deductions & Credits ────────────────────────────────────
    _rule("US-2026-educator-expenses", "US", 2026, "education",
          "Educator expenses (IRC §62(c)) — potentially relevant",
          "Above-the-line deduction for K-12 teachers spending on classroom supplies. Verify current limit. " + VERIFY_IRS,
          ["K-12 educator"], ["expense receipts"], VERIFY_IRS),
    _rule("US-2026-alimony", "US", 2026, "family",
          "Alimony payments (IRC §215) — check agreement date",
          "Deductible for agreements finalized before 2019. Post-2018 alimony is not deductible by payer nor taxable to recipient. " + VERIFY_IRS,
          ["pre-2019 divorce agreement"], ["alimony payment records"], VERIFY_IRS),
    _rule("US-2026-mortgage-points", "US", 2026, "housing",
          "Mortgage points (IRC §163/§461) — potentially relevant",
          "Points paid on purchase mortgage fully deductible in year paid. Refinance points amortized over loan life. " + VERIFY_IRS,
          ["mortgage closing documents"], ["Form 1098", "HUD-1 settlement"], VERIFY_IRS),
    _rule("US-2026-state-refund", "US", 2026, "housing",
          "State tax refund recovery (IRC §111) — potentially relevant",
          "If you deducted state taxes last year and received a refund, the refund may be taxable this year. " + VERIFY_IRS,
          ["state tax refund received", "prior year itemized deductions"], ["Form 1099-G"], VERIFY_IRS),
    _rule("US-2026-capital-loss-carryforward", "US", 2026, "investments",
          "Capital loss carryforward (IRC §1212) — potentially relevant",
          "Unused capital losses carry forward indefinitely. Track across years for optimal harvesting. " + VERIFY_IRS,
          ["prior year capital losses"], ["Schedule D", "prior year returns"], VERIFY_IRS),
    _rule("US-2026-estimated-tax", "US", 2026, "compliance",
          "Estimated tax payments (IRC §6654) — compliance requirement",
          "Quarterly estimated tax payments required if expecting $1,000+ tax liability. Underpayment penalties apply. " + VERIFY_IRS,
          ["self-employment income", "withholding below liability"], ["1040-ES", "payment records"], VERIFY_IRS),
    _rule("US-2026-safe-harbor", "US", 2026, "compliance",
          "Estimated tax safe harbor — strategic opportunity",
          "Avoid underpayment penalty by paying 100% of prior year tax (110% if AGI > $150K) or 90% of current year. " + VERIFY_IRS,
          ["prior year tax liability"], ["prior year return"], VERIFY_IRS),
    _rule("US-2026-foreign-tax-credit", "US", 2026, "investments",
          "Foreign Tax Credit (IRC §901) — potentially relevant",
          "Credit for foreign taxes paid on foreign-source income. Avoids double taxation. " + VERIFY_IRS,
          ["foreign income or investments"], ["foreign tax statements", "Form 1116"], VERIFY_IRS),
    _rule("US-2026-net-investment-income", "US", 2026, "investments",
          "Net Investment Income Tax (IRC §1411) — compliance awareness",
          "3.8% surtax on net investment income if MAGI exceeds $200K single / $250K MFJ. " + VERIFY_IRS,
          ["investment income", "MAGI above threshold"], ["investment statements"], VERIFY_IRS),
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
