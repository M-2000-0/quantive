"""Year-End Tax Sprint — November-December countdown dashboard.

Creates urgency by showing users exactly what tax-saving moves remain
before the December 31 deadline. Calculates remaining opportunities
and tracks completion.
"""
from __future__ import annotations

from datetime import datetime, timezone, date
from typing import Optional

from sqlalchemy.orm import Session

from app.personal.models import (
    ComplianceAlert,
    PersonalOpportunity,
    ProfileFact,
    Recommendation,
    Transaction,
    TaxProjection,
)
from app.personal.compliance import analyze_withholding, STANDARD_DEDUCTION_2026
from app.personal.tax_projection import project_annual


# Deadlines for various tax moves (month, day)
TAX_DEADLINES = {
    "estimated_q4": (1, 15),      # Q4 estimated payment due Jan 15 (next year)
    "ira_contribution": (4, 15),  # IRA contribution deadline (tax filing)
    "hsa_contribution": (4, 15),  # HSA contribution deadline (tax filing)
    "charitable_year_end": (12, 31),  # Charitable donations for this year
    "gift_tax_year_end": (12, 31),  # Annual gift exclusion
    "retroactive_ira": (4, 15),   # Traditional IRA for prior year
    "roth_conversion": (12, 31),  # Roth conversion must be completed by Dec 31
    "estimated_tax_payments": (12, 31),  # Safe harbor payments
    "stock_gifts": (12, 31),      # Charitable stock gifts
    "section_179": (12, 31),      # Section 179 equipment purchase
    "charitable_daf": (12, 31),   # Donor-advised fund contributions
    "401k_increases": (12, 31),   # Increase 401k contributions
    "flexible_spending": (12, 31), # FSA use-it-or-lose-it
    "dependent_care_fsa": (12, 31), # DCFSA deadline
    "energy_improvements": (12, 31), # Energy credits
    "ev_purchase": (12, 31),      # EV credit purchase
}

# 2026 contribution limits
HSA_LIMITS_2026 = {"individual": 4_300_00, "family": 8_550_00, "catch_up": 1_000_00}
IRA_LIMITS_2026 = {"under_50": 7_000_00, "catch_up": 1_000_00}
_401K_LIMITS_2026 = {"under_50": 23_500_00, "catch_up": 7_500_00}
FSA_LIMIT_2026 = 3_300_00
DCFSA_LIMIT_2026 = 5_000_00
ANNUAL_GIFT_EXCLUSION_2026 = 19_000_00

# Sections 179 limit (2026 est.)
SECTION_179_LIMIT = 1_250_000_00
SECTION_179_PHASE_OUT = 3_130_000_00

# EV credit (Section 30D)
EV_CREDIT_AMOUNT = 7_500_00

# Energy credit (Section 25C)
ENERGY_CREDIT_MAX = 3_200_00


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _tax_year_end(tax_year: int) -> date:
    return date(tax_year, 12, 31)


def _deadline_date(month: int, day: int, year: int) -> date:
    return date(year, month, day)


def _get_facts(user_id: str, db: Session) -> dict:
    """Load all profile facts into a dict keyed by fact key."""
    facts: dict[str, str] = {}
    for f in db.query(ProfileFact).filter(ProfileFact.user_id == user_id).all():
        facts[f.key] = f.value
    return facts


def _get_facts_json(user_id: str, db: Session) -> dict:
    """Load profile facts with value_json into nested dict."""
    facts: dict[str, dict] = {}
    for f in db.query(ProfileFact).filter(ProfileFact.user_id == user_id).all():
        facts[f.key] = {"value": f.value, "value_json": f.value_json or {}}
    return facts


def _marginal_rate(user_id: str, db: Session, tax_year: int = 2026) -> float:
    """Get the user's marginal tax rate from their latest projection."""
    projection = db.query(TaxProjection).filter(
        TaxProjection.user_id == user_id,
        TaxProjection.tax_year == tax_year,
    ).order_by(TaxProjection.created_at.desc()).first()
    if projection and projection.marginal_rate > 0:
        return projection.marginal_rate
    result = project_annual(user_id, db)
    return result.get("marginal_rate", 0.22)


def _ytd_contributions(user_id: str, db: Session, category: str) -> int:
    """Sum YTD contributions for a given transaction category."""
    now = datetime.now(timezone.utc)
    year_start = f"{now.year}-01-01"
    txns = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.date >= year_start,
        Transaction.category == category,
        Transaction.excluded == False,
    ).all()
    return sum(abs(t.amount) for t in txns)


def _is_eligible_for_hsa(facts: dict) -> bool:
    """Check if user has an HDHP and is HSA-eligible."""
    if facts.get("health_insurance") != "yes":
        return False
    plan_type = facts.get("health_plan_type", "").lower()
    return plan_type in ("hdhp", "high_deductible", "high-deductible")


def _is_eligible_for_ira(facts: dict) -> bool:
    """Check if user can contribute to a Traditional IRA."""
    has_employer_plan = facts.get("employer_retirement_plan") == "yes"
    filing_status = facts.get("filing_status", "single")
    income_str = facts.get("estimated_income", "0")
    try:
        income = int(income_str)
    except (ValueError, TypeError):
        income = 0
    # Simplified: most filers are eligible unless high income + employer plan
    if has_employer_plan and filing_status == "single" and income > 83000_00:
        return False
    if has_employer_plan and filing_status in ("married", "married_filing_jointly") and income > 136000_00:
        return False
    return True


def _is_eligible_for_roth(facts: dict) -> bool:
    """Check Roth IRA income eligibility."""
    filing_status = facts.get("filing_status", "single")
    income_str = facts.get("estimated_income", "0")
    try:
        income = int(income_str)
    except (ValueError, TypeError):
        income = 0
    # 2026 Roth phaseout ranges (estimated)
    if filing_status == "single":
        return income < 161000_00
    if filing_status in ("married", "married_filing_jointly"):
        return income < 240000_00
    return True


def _remaining_bracket_space(facts: dict, projection: dict) -> int:
    """Estimate how much room remains in the user's current bracket."""
    marginal_rate = projection.get("marginal_rate", 0.22)
    taxable_income = projection.get("taxable_income", 0)

    # Map rate to bracket top
    bracket_tops = {
        0.10: 11925_00,
        0.12: 48475_00,
        0.22: 103350_00,
        0.24: 197300_00,
        0.32: 250525_00,
        0.35: 626350_00,
        0.37: float("inf"),
    }
    top = bracket_tops.get(marginal_rate, 103350_00)
    return max(0, int(top - taxable_income))


def get_sprint_actions(user_id: str, db: Session, tax_year: int = 2026) -> list[dict]:
    """Generate the list of available year-end tax moves based on user profile."""
    today = _today()
    year_end = _tax_year_end(tax_year)
    facts = _get_facts(user_id, db)
    projection = project_annual(user_id, db)
    marginal_rate = _marginal_rate(user_id, db, tax_year)
    days_left = max(0, (year_end - today).days)

    actions: list[dict] = []

    # ── Roth Conversion ───────────────────────────────────────────────
    has_traditional = facts.get("retirement") == "yes" and facts.get("traditional_ira_balance")
    if has_traditional and _is_eligible_for_roth(facts):
        bracket_space = _remaining_bracket_space(facts, projection)
        if bracket_space > 0:
            conversion_amount = min(bracket_space, 100_000_00)  # Cap at $100K
            tax_cost = int(conversion_amount * marginal_rate)
            actions.append({
                "id": "roth_conversion",
                "title": "Complete Roth conversion",
                "category": "retirement",
                "deadline": f"{tax_year}-12-31",
                "days_left": days_left,
                "estimated_savings": int(conversion_amount * 0.05),  # Simplified long-term benefit
                "status": "available",
                "priority": "high" if conversion_amount > 50_00_00 else "medium",
                "why": (
                    f"You have ${bracket_space / 100:,.0f} of space in the {int(marginal_rate * 100)}% bracket. "
                    f"Converting now costs ${tax_cost / 100:,.0f} but saves on future higher-rate withdrawals."
                ),
                "action_steps": [
                    "Contact your IRA custodian",
                    f"Request partial conversion of ${conversion_amount / 100:,.0f}",
                    "Specify withholding election (optional but recommended)",
                    "Document conversion for tax filing",
                ],
                "irc_section": "§408A",
                "requires": ["Traditional IRA balance", "Income estimate"],
            })

    # ── HSA Last-Minute Contribution ─────────────────────────────────
    if _is_eligible_for_hsa(facts):
        family_status = facts.get("filing_status", "single")
        is_family = family_status in ("married", "married_filing_jointly", "head_of_household")
        limit = HSA_LIMITS_2026["family"] if is_family else HSA_LIMITS_2026["individual"]
        ytd = _ytd_contributions(user_id, db, "hsa")
        remaining = max(0, limit - ytd)
        if remaining > 0:
            savings = int(remaining * marginal_rate)
            actions.append({
                "id": "hsa_contribution",
                "title": "Make HSA contribution",
                "category": "health",
                "deadline": f"{tax_year + 1}-04-15",
                "days_left": max(0, (date(tax_year + 1, 4, 15) - today).days),
                "estimated_savings": savings,
                "status": "available",
                "priority": "high" if remaining > 100_00_00 else "medium",
                "why": (
                    f"You have ${remaining / 100:,.0f} of HSA space remaining. "
                    f"Triple tax advantage: deductible, tax-free growth, tax-free medical withdrawals."
                ),
                "action_steps": [
                    "Log into your HSA provider portal",
                    f"Contribute up to ${remaining / 100:,.0f}",
                    "Invest funds for long-term growth (don't leave as cash)",
                    "Save receipts for future medical expense withdrawals",
                ],
                "irc_section": "§223",
                "requires": ["HDHP enrollment"],
            })

    # ── IRA Contribution ─────────────────────────────────────────────
    if _is_eligible_for_ira(facts):
        age_str = facts.get("age", "30")
        try:
            age = int(age_str)
        except (ValueError, TypeError):
            age = 30
        is_catchup = age >= 50
        limit = IRA_LIMITS_2026["under_50"]
        if is_catchup:
            limit += IRA_LIMITS_2026["catch_up"]
        ytd = _ytd_contributions(user_id, db, "ira")
        remaining = max(0, limit - ytd)
        if remaining > 0:
            savings = int(remaining * marginal_rate)
            actions.append({
                "id": "ira_contribution",
                "title": "Contribute to IRA",
                "category": "retirement",
                "deadline": f"{tax_year + 1}-04-15",
                "days_left": max(0, (date(tax_year + 1, 4, 15) - today).days),
                "estimated_savings": savings,
                "status": "available",
                "priority": "high" if remaining > 100_00_00 else "medium",
                "why": (
                    f"${remaining / 100:,.0f} of IRA contribution space remaining. "
                    f"Traditional: deductible at your {int(marginal_rate * 100)}% marginal rate. "
                    f"Roth: tax-free growth."
                ),
                "action_steps": [
                    "Choose Traditional or Roth based on current vs future tax rate",
                    "Fund the account (direct contribution or backdoor if over income limit)",
                    "Invest the funds (don't leave as cash)",
                ],
                "irc_section": "§219",
                "requires": ["Earned income", "Filing status"],
            })

    # ── Charitable Bunching / Stock Gifts ────────────────────────────
    has_donations = facts.get("donations") == "yes"
    if has_donations or facts.get("charitable_giving", "").lower() in ("yes", "regular"):
        # Estimate: if standard deduction user, bunching could help
        use_standard = projection.get("use_standard", True)
        if use_standard:
            gap_to_itemize = projection.get("standard_deduction", 15700_00) - projection.get("projected_itemized", 0)
            if gap_to_itemize < 100_00_00:  # Within $1,000 of itemizing
                bunching_amount = gap_to_itemize + 50_00_00  # Push $500 over
                savings = int(bunching_amount * marginal_rate)
                actions.append({
                    "id": "charitable_bunching",
                    "title": "Charitable contribution bunching",
                    "category": "charitable",
                    "deadline": f"{tax_year}-12-31",
                    "days_left": days_left,
                    "estimated_savings": savings,
                    "status": "available",
                    "priority": "high" if savings > 500_00 else "medium",
                    "why": (
                        f"Bunching ${bunching_amount / 100:,.0f} in charitable contributions this year "
                        f"could push you past the standard deduction, saving ${savings / 100:,.0f}. "
                        f"Skip donating next year to net the benefit."
                    ),
                    "action_steps": [
                        "Calculate total charitable giving for this year and next",
                        "Make next year's donations before December 31",
                        "Get written acknowledgment for all donations > $250",
                        "Consider donating appreciated stock for additional benefit",
                    ],
                    "irc_section": "§170",
                    "requires": ["Donation amount estimate"],
                })

    # Charitable stock gifts
    if facts.get("invest_accounts") == "yes":
        actions.append({
            "id": "stock_gifts",
            "title": "Donate appreciated stock",
            "category": "charitable",
            "deadline": f"{tax_year}-12-31",
            "days_left": days_left,
            "estimated_savings": 0,  # Depends on holdings
            "status": "available",
            "priority": "medium",
            "why": (
                "Donating appreciated stock avoids capital gains tax AND provides a deduction. "
                "You deduct the full fair market value without paying gains."
            ),
            "action_steps": [
                "Identify positions with unrealized gains held > 1 year",
                "Contact your brokerage to transfer shares directly to charity",
                "Ensure the charity is a qualified 501(c)(3)",
                "Get acknowledgment letter for tax filing",
            ],
            "irc_section": "§170",
            "requires": ["Brokerage account", "Charity EIN"],
        })

    # ── Donor-Advised Fund (DAF) ─────────────────────────────────────
    if facts.get("invest_accounts") == "yes":
        actions.append({
            "id": "charitable_daf",
            "title": "Contribute to Donor-Advised Fund",
            "category": "charitable",
            "deadline": f"{tax_year}-12-31",
            "days_left": days_left,
            "estimated_savings": 0,
            "status": "available",
            "priority": "medium",
            "why": (
                "A DAF lets you front-load charitable deductions, invest tax-free, "
                "and distribute grants over time. Great for bunching strategy."
            ),
            "action_steps": [
                "Open a DAF (Fidelity, Schwab, or Vanguard Charitable)",
                "Contribute cash or appreciated assets before Dec 31",
                "Claim the deduction this year, distribute grants in future years",
            ],
            "irc_section": "§170",
            "requires": ["Minimum contribution ($5,000 typical)"],
        })

    # ── Section 179 Equipment Purchase ────────────────────────────────
    if any(facts.get(k) in ("yes", "self-employed", "business") for k in ("income_sources", "business", "self_employed")):
        actions.append({
            "id": "section_179",
            "title": "Section 179 equipment purchase",
            "category": "business",
            "deadline": f"{tax_year}-12-31",
            "days_left": days_left,
            "estimated_savings": 0,  # Depends on purchase amount
            "status": "available",
            "priority": "medium",
            "why": (
                f"Section 179 allows immediate expensing of business equipment up to "
                f"${SECTION_179_LIMIT / 100:,.0f}. Must be placed in service by Dec 31."
            ),
            "action_steps": [
                "Identify needed business equipment or software",
                "Purchase and place in service before December 31",
                "Ensure the asset qualifies (not real property with exceptions)",
                "Document business use percentage",
            ],
            "irc_section": "§179",
            "requires": ["Business use > 50%", "Qualified property"],
        })

    # ── 401(k) Contribution Increase ─────────────────────────────────
    if facts.get("retirement") == "yes":
        ytd_401k = _ytd_contributions(user_id, db, "retirement")
        remaining_401k = max(0, _401K_LIMITS_2026["under_50"] - ytd_401k)
        if remaining_401k > 0:
            monthly_needed = remaining_401k // max(1, 12 - today.month + 1)
            savings = int(remaining_401k * marginal_rate)
            actions.append({
                "id": "401k_increase",
                "title": "Increase 401(k) contributions",
                "category": "retirement",
                "deadline": f"{tax_year}-12-31",
                "days_left": days_left,
                "estimated_savings": savings,
                "status": "available",
                "priority": "high" if remaining_401k > 200_00_00 else "medium",
                "why": (
                    f"${remaining_401k / 100:,.0f} of 401(k) space remaining. "
                    f"Increase payroll deductions by ${monthly_needed / 100:,.0f}/month. "
                    f"Reduces taxable income at your {int(marginal_rate * 100)}% marginal rate."
                ),
                "action_steps": [
                    "Log into your payroll/HR portal",
                    f"Increase 401(k) contribution by ${monthly_needed / 100:,.0f}/month",
                    "Note: payroll changes may take 1-2 pay periods to process",
                    "Consider catch-up contribution if age 50+",
                ],
                "irc_section": "§402(g)",
                "requires": ["Employer 401(k) plan"],
            })

    # ── FSA Use-It-Or-Lose-It ────────────────────────────────────────
    has_fsa = facts.get("flexible_spending") == "yes"
    if has_fsa:
        actions.append({
            "id": "flexible_spending",
            "title": "Use FSA balance before year-end",
            "category": "health",
            "deadline": f"{tax_year}-12-31",
            "days_left": days_left,
            "estimated_savings": 0,
            "status": "available",
            "priority": "high",
            "why": (
                "FSA funds typically expire at year-end. Use remaining balance for "
                "eligible medical, dental, or vision expenses."
            ),
            "action_steps": [
                "Check your FSA balance",
                "Schedule eligible medical appointments before Dec 31",
                "Purchase eligible items (glasses, contacts, OTC medications)",
                "Submit claims before the deadline",
            ],
            "irc_section": "§129",
            "requires": ["Active FSA balance"],
        })

    # ── Dependent Care FSA ────────────────────────────────────────────
    has_kids = any(facts.get(k) in ("yes",) for k in ("family", "children", "dependents"))
    if has_kids:
        actions.append({
            "id": "dependent_care_fsa",
            "title": "Maximize Dependent Care FSA",
            "category": "family",
            "deadline": f"{tax_year}-12-31",
            "days_left": days_left,
            "estimated_savings": int(DCFSA_LIMIT_2026 * marginal_rate),
            "status": "available",
            "priority": "medium",
            "why": (
                f"Dependent Care FSA allows ${DCFSA_LIMIT_2026 / 100:,.0f} pre-tax for childcare. "
                f"Saves ${int(DCFSA_LIMIT_2026 * marginal_rate) / 100:,.0f} in taxes."
            ),
            "action_steps": [
                "Check if your employer offers a DCFSA",
                "Enroll during open enrollment or within 30 days of qualifying event",
                "Submit dependent care expenses for reimbursement",
            ],
            "irc_section": "§129",
            "requires": ["Qualifying dependent", "Childcare expenses"],
        })

    # ── Tax-Loss Harvesting ───────────────────────────────────────────
    if facts.get("invest_accounts") == "yes":
        actions.append({
            "id": "tax_loss_harvesting",
            "title": "Tax-loss harvesting",
            "category": "investments",
            "deadline": f"{tax_year}-12-31",
            "days_left": days_left,
            "estimated_savings": 0,  # Depends on portfolio
            "status": "available",
            "priority": "high",
            "why": (
                "Sell investments with unrealized losses to offset gains. "
                "Up to $3,000 in net losses can offset ordinary income. "
                "Must sell by Dec 31 (T+1 settlement)."
            ),
            "action_steps": [
                "Review brokerage for positions with unrealized losses",
                "Sell before Dec 29 (account for settlement timing)",
                "Check wash sale rules (30-day window before/after)",
                "Consider substitute securities to maintain market exposure",
            ],
            "irc_section": "§1211",
            "requires": ["Brokerage account", "Unrealized losses"],
        })

    # ── SALT Prepayment ──────────────────────────────────────────────
    if facts.get("filing_status") != "single" or facts.get("housing") in ("own", "mortgage"):
        actions.append({
            "id": "salt_prepayment",
            "title": "Prepay state/local taxes",
            "category": "deductions",
            "deadline": f"{tax_year}-12-31",
            "days_left": days_left,
            "estimated_savings": 0,
            "status": "available",
            "priority": "low",
            "why": (
                "Prepaying state income or property taxes before Dec 31 "
                "can increase itemized deductions. Note: SALT is capped at $10,000."
            ),
            "action_steps": [
                "Calculate current SALT paid vs $10,000 cap",
                "If under the cap, consider prepaying January property tax",
                "Verify your state allows prepayment deduction",
                "Keep records of prepayment",
            ],
            "irc_section": "§164",
            "requires": ["Property ownership or state income tax"],
        })

    # ── Estimated Tax Payment Adjustment ──────────────────────────────
    withholding = analyze_withholding(user_id, db)
    if withholding["shortfall"] > 1000_00:
        actions.append({
            "id": "estimated_tax_adjustment",
            "title": "Adjust estimated tax payments",
            "category": "compliance",
            "deadline": f"{tax_year + 1}-01-15",
            "days_left": max(0, (date(tax_year + 1, 1, 15) - today).days),
            "estimated_savings": 0,
            "status": "available",
            "priority": "high",
            "why": (
                f"Projected shortfall of ${withholding['shortfall'] / 100:,.0f}. "
                f"Make estimated payment by Jan 15 to avoid underpayment penalties."
            ),
            "action_steps": [
                f"Make estimated payment of ${withholding['quarterly_payment_needed'] / 100:,.0f}",
                "Use IRS Direct Pay or EFTPS",
                "Consider increasing W-4 withholding for next year",
            ],
            "irc_section": "§6654",
            "requires": ["Income estimate"],
        })

    # ── EV Purchase ──────────────────────────────────────────────────
    actions.append({
        "id": "ev_purchase",
        "title": "Purchase qualifying EV",
        "category": "energy",
        "deadline": f"{tax_year}-12-31",
        "days_left": days_left,
        "estimated_savings": EV_CREDIT_AMOUNT,
        "status": "available",
        "priority": "low",
        "why": (
            f"Clean Vehicle Credit up to ${EV_CREDIT_AMOUNT / 100:,.0f}. "
            "Must take delivery before Dec 31. Income and MSRP limits apply."
        ),
        "action_steps": [
            "Verify income is below $150K (single) / $300K (MFJ)",
            "Confirm vehicle MSRP is below $55K (sedan) / $80K (SUV/truck)",
            "Check manufacturer's tax credit eligibility",
            "Take delivery before December 31",
            "Claim credit on tax return (Form 8936)",
        ],
        "irc_section": "§30D",
        "requires": ["Income verification", "Vehicle eligibility"],
    })

    # ── Energy Improvements ──────────────────────────────────────────
    if facts.get("housing") in ("own", "mortgage"):
        actions.append({
            "id": "energy_improvements",
            "title": "Energy-efficient home improvements",
            "category": "energy",
            "deadline": f"{tax_year}-12-31",
            "days_left": days_left,
            "estimated_savings": ENERGY_CREDIT_MAX,
            "status": "available",
            "priority": "low",
            "why": (
                f"Energy Efficient Home Improvement Credit up to ${ENERGY_CREDIT_MAX / 100:,.0f}/year. "
                "Covers windows, doors, insulation, HVAC, and heat pumps."
            ),
            "action_steps": [
                "Check qualifying improvements (windows, insulation, HVAC)",
                "Purchase and install before December 31",
                "Get manufacturer certifications",
                "Claim credit on Form 5695",
            ],
            "irc_section": "§25C",
            "requires": ["Homeownership"],
        })

    # ── Gift Tax Exclusion ────────────────────────────────────────────
    actions.append({
        "id": "gift_exclusion",
        "title": "Annual gift tax exclusion",
        "category": "estate",
        "deadline": f"{tax_year}-12-31",
        "days_left": days_left,
        "estimated_savings": 0,
        "status": "available",
        "priority": "low",
        "why": (
            f"Give up to ${ANNUAL_GIFT_EXCLUSION_2026 / 100:,.0f} per recipient tax-free. "
            "Reduces your estate without using lifetime exemption."
        ),
        "action_steps": [
            "Identify family members or others to gift",
            f"Transfer up to ${ANNUAL_GIFT_EXCLUSION_2026 / 100:,.0f} per recipient",
            "File Form 709 if total gifts exceed exclusion",
            "Consider 529 plan contributions (5-year election available)",
        ],
        "irc_section": "§2503",
        "requires": ["Recipient identification"],
    })

    return actions


def get_sprint_status(user_id: str, db: Session, tax_year: int = 2026) -> dict:
    """Main entry point: full sprint status with actions, deadlines, and summary."""
    today = _today()
    year_end = _tax_year_end(tax_year)
    sprint_start = date(tax_year, 11, 1)

    is_sprint_active = sprint_start <= today <= year_end
    days_remaining = max(0, (year_end - today).days)

    actions = get_sprint_actions(user_id, db, tax_year)

    # Check action statuses from existing recommendations
    existing_recs = {
        r.title: r.status
        for r in db.query(Recommendation).filter(
            Recommendation.user_id == user_id,
            Recommendation.tax_year == tax_year,
        ).all()
    }

    for action in actions:
        rec_status = existing_recs.get(action["title"], "")
        if rec_status in ("implemented",):
            action["status"] = "completed"
        elif rec_status in ("accepted", "viewed"):
            action["status"] = "started"

    # Calculate totals
    total_potential = sum(a["estimated_savings"] for a in actions if a["status"] != "completed")
    actions_taken = sum(1 for a in actions if a["status"] in ("completed", "started"))
    actions_remaining = sum(1 for a in actions if a["status"] == "available")

    # Missed deadlines
    missed = []
    for action_id, (m, d) in TAX_DEADLINES.items():
        deadline = _deadline_date(m, d, tax_year)
        if today > deadline and deadline.year == tax_year:
            # Check if relevant to user
            if action_id not in [a["id"] for a in actions]:
                missed.append({
                    "action": action_id.replace("_", " ").title(),
                    "deadline": deadline.isoformat(),
                })

    # Upcoming deadlines (after year-end)
    upcoming = []
    upcoming_deadlines = [
        ("Q4 estimated tax", date(tax_year + 1, 1, 15)),
        ("IRA contribution", date(tax_year + 1, 4, 15)),
        ("HSA contribution", date(tax_year + 1, 4, 15)),
    ]
    for label, dl in upcoming_deadlines:
        if today <= dl:
            upcoming.append({
                "action": label,
                "deadline": dl.isoformat(),
                "days": (dl - today).days,
            })

    # Sort actions: high priority first, then by estimated savings
    priority_order = {"high": 0, "medium": 1, "low": 2}
    actions.sort(key=lambda a: (
        priority_order.get(a["priority"], 2),
        -a["estimated_savings"],
    ))

    return {
        "sprint_active": is_sprint_active,
        "days_remaining": days_remaining,
        "total_potential_savings": total_potential,
        "actions_taken": actions_taken,
        "actions_remaining": actions_remaining,
        "actions": actions,
        "missed_deadlines": missed,
        "upcoming_deadlines": upcoming,
    }


def update_sprint_progress(
    user_id: str, action_id: str, status: str, db: Session
) -> dict:
    """Update the status of a sprint action.

    Args:
        user_id: The user's ID.
        action_id: The sprint action ID (e.g. 'roth_conversion').
        status: New status: 'started', 'completed', 'available'.
        db: Database session.

    Returns:
        dict with success flag and updated action info.
    """
    valid_statuses = {"available", "started", "completed"}
    if status not in valid_statuses:
        return {"success": False, "error": f"Invalid status. Must be one of: {valid_statuses}"}

    # Find matching recommendation by category/title pattern
    rec = db.query(Recommendation).filter(
        Recommendation.user_id == user_id,
        Recommendation.irc_section != "",
    ).first()

    # Try to find a recommendation that matches the action
    action_map = {
        "roth_conversion": "Roth conversion",
        "hsa_contribution": "HSA",
        "ira_contribution": "IRA",
        "charitable_bunching": "Charitable",
        "401k_increase": "401(k)",
        "tax_loss_harvesting": "Tax-loss harvesting",
    }

    search_term = action_map.get(action_id, action_id.replace("_", " "))
    rec = db.query(Recommendation).filter(
        Recommendation.user_id == user_id,
        Recommendation.title.ilike(f"%{search_term}%"),
    ).first()

    if rec:
        status_map = {"available": "new", "started": "viewed", "completed": "implemented"}
        rec.status = status_map.get(status, rec.status)
        db.commit()

    # Audit log
    from app.personal.models import PersonalAudit
    audit = PersonalAudit(
        user_id=user_id,
        action=f"sprint_progress_{status}",
        entity="sprint_action",
        entity_id=action_id,
    )
    db.add(audit)
    db.commit()

    return {
        "success": True,
        "action_id": action_id,
        "status": status,
    }


def get_sprint_summary(user_id: str, db: Session, tax_year: int = 2026) -> dict:
    """Summary stats for the dashboard header."""
    status = get_sprint_status(user_id, db, tax_year)

    # Find biggest remaining action
    remaining_actions = [a for a in status["actions"] if a["status"] == "available"]
    biggest = max(remaining_actions, key=lambda a: a["estimated_savings"]) if remaining_actions else None

    # Urgency message
    days = status["days_remaining"]
    savings = status["total_potential_savings"]
    if days <= 7:
        urgency = f"Only {days} days left! Save ${savings / 100:,.0f} before time runs out."
    elif days <= 14:
        urgency = f"{days} days left to save ${savings / 100:,.0f}. Act now!"
    elif days <= 30:
        urgency = f"{days} days remaining. ${savings / 100:,.0f} in tax savings available."
    else:
        urgency = f"{days} days left in the year. ${savings / 100:,.0f} in opportunities await."

    return {
        "days_remaining": days,
        "total_potential_savings": savings,
        "actions_completed": status["actions_taken"],
        "actions_total": len(status["actions"]),
        "biggest_remaining_action": {
            "id": biggest["id"],
            "title": biggest["title"],
            "estimated_savings": biggest["estimated_savings"],
        } if biggest else None,
        "urgency_message": urgency,
        "sprint_active": status["sprint_active"],
    }
