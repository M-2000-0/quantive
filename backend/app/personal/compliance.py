"""Compliance monitoring system.

Continuously monitors tax compliance status: withholding adequacy,
estimated tax obligations, document completeness, and filing deadlines.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.personal.models import (
    ComplianceAlert,
    FinancialConnection,
    ProfileFact,
    Transaction,
)


# ── 2026 Tax Brackets (Single filer) ────────────────────────────────
BRACKETS_2026_SINGLE = [
    (11925, 0.10),
    (48475, 0.12),
    (103350, 0.22),
    (197300, 0.24),
    (250525, 0.32),
    (626350, 0.35),
    (float("inf"), 0.37),
]

BRACKETS_2026_MFJ = [
    (23850, 0.10),
    (96950, 0.12),
    (206700, 0.22),
    (394600, 0.24),
    (501050, 0.32),
    (751600, 0.35),
    (float("inf"), 0.37),
]

STANDARD_DEDUCTION_2026 = {
    "single": 15700_00,  # $15,700 in cents
    "married": 31400_00,
    "married_filing_separately": 15700_00,
    "head_of_household": 23550_00,
}

# Estimated tax safe harbor thresholds
SAFE_HARBOR_RATE = 1.0  # 100% of prior year tax
SAFE_HARBOR_HIGH_INCOME_RATE = 1.1  # 110% if AGI > $150K
HIGH_INCOME_THRESHOLD = 150000_00  # $150,000 in cents

# Underpayment penalty threshold
UNDERPAYMENT_THRESHOLD = 1000_00  # $1,000


def _get_bracket(filing_status: str) -> list[tuple[int, float]]:
    if filing_status in ("married", "married_filing_jointly"):
        return BRACKETS_2026_MFJ
    return BRACKETS_2026_SINGLE


def _get_standard_deduction(filing_status: str) -> int:
    return STANDARD_DEDUCTION_2026.get(filing_status, STANDARD_DEDUCTION_2026["single"])


def calculate_federal_tax(taxable_income: int, filing_status: str = "single") -> dict:
    """Calculate federal income tax using 2026 brackets."""
    brackets = _get_bracket(filing_status)
    tax = 0
    prev_limit = 0
    marginal_rate = 0.0
    bracket_label = ""

    for limit, rate in brackets:
        if taxable_income <= prev_limit:
            break
        taxable_in_bracket = min(taxable_income, limit) - prev_limit
        tax += int(taxable_in_bracket * rate)
        marginal_rate = rate
        bracket_label = f"{int(rate * 100)}%"
        prev_limit = limit

    effective_rate = (tax / taxable_income * 100) if taxable_income > 0 else 0.0

    return {
        "tax": tax,
        "marginal_rate": marginal_rate,
        "bracket": bracket_label,
        "effective_rate": round(effective_rate, 1),
    }


def calculate_se_tax(net_se_income: int) -> dict:
    """Calculate self-employment tax (Social Security + Medicare)."""
    # Social Security: 12.4% on first $168,600 (2026 est.)
    ss_wage_base = 168600_00
    ss_tax = int(min(net_se_income, ss_wage_base) * 0.124)

    # Medicare: 2.9% on all SE income
    medicare_tax = int(net_se_income * 0.029)

    # Additional Medicare Tax: 0.9% on SE income over $200,000
    additional_medicare = int(max(0, net_se_income - 200000_00) * 0.009)

    total = ss_tax + medicare_tax + additional_medicare
    deductible_se_tax = total // 2  # 50% deductible

    return {
        "total_se_tax": total,
        "social_security": ss_tax,
        "medicare": medicare_tax,
        "additional_medicare": additional_medicare,
        "deductible_portion": deductible_se_tax,
    }


def analyze_withholding(user_id: str, db: Session) -> dict:
    """Analyze whether current withholding is adequate."""
    # Get user facts
    facts = {}
    for f in db.query(ProfileFact).filter(ProfileFact.user_id == user_id).all():
        facts[f.key] = f.value

    filing_status = facts.get("filing_status", "single")

    # Get YTD income from transactions
    now = datetime.now(timezone.utc)
    ytd_start = f"{now.year}-01-01"
    ytd_end = now.strftime("%Y-%m-%d")

    # Income (negative amounts from payroll/revenue transactions)
    income_txns = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.date >= ytd_start,
        Transaction.date <= ytd_end,
        Transaction.tax_tag.in_(["taxable-revenue", "revenue", "rental"]),
        Transaction.excluded == False,
    ).all()

    ytd_income = sum(-t.amount for t in income_txns if t.amount < 0)

    # Withholding/payments (positive amounts = payments made)
    tax_payments = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.date >= ytd_start,
        Transaction.date <= ytd_end,
        Transaction.tax_tag == "tax-paid",
        Transaction.excluded == False,
    ).all()

    ytd_withholding = sum(t.amount for t in tax_payments)

    # Estimate annual income (annualize based on months elapsed)
    months_elapsed = now.month
    projected_annual_income = int(ytd_income * 12 / max(months_elapsed, 1))

    # Calculate tax
    standard_deduction = _get_standard_deduction(filing_status)
    taxable_income = max(0, projected_annual_income - standard_deduction)
    tax_calc = calculate_federal_tax(taxable_income, filing_status)

    projected_tax = tax_calc["tax"]

    # SE income estimation
    se_income = sum(-t.amount for t in income_txns
                    if t.amount < 0 and t.category in ("revenue", "payroll") and "freelance" in t.name.lower())
    se_tax = calculate_se_tax(se_income) if se_income > 0 else {"total_se_tax": 0, "deductible_portion": 0}

    total_projected_tax = projected_tax + se_tax["total_se_tax"]

    # Projected withholding (annualize current withholding)
    projected_withholding = int(ytd_withholding * 12 / max(months_elapsed, 1))

    # Estimated quarterly payments needed
    remaining_quarters = max(0, 4 - ((now.month - 1) // 3 + 1))
    shortfall = max(0, total_projected_tax - projected_withholding)
    quarterly_payment = shortfall // max(remaining_quarters, 1)

    return {
        "ytd_income": ytd_income,
        "ytd_withholding": ytd_withholding,
        "projected_annual_income": projected_annual_income,
        "projected_total_tax": total_projected_tax,
        "projected_withholding": projected_withholding,
        "shortfall": shortfall,
        "quarterly_payment_needed": quarterly_payment,
        "remaining_quarters": remaining_quarters,
        "filing_status": filing_status,
        "bracket": tax_calc["bracket"],
        "marginal_rate": tax_calc["marginal_rate"],
        "effective_rate": tax_calc["effective_rate"],
        "standard_deduction": standard_deduction,
        "taxable_income": taxable_income,
        "se_tax": se_tax,
    }


def generate_compliance_alerts(user_id: str, db: Session) -> list[ComplianceAlert]:
    """Generate compliance alerts based on current financial state."""
    alerts = []
    now = datetime.now(timezone.utc)

    # Clear old acknowledged alerts
    db.query(ComplianceAlert).filter(
        ComplianceAlert.user_id == user_id,
        ComplianceAlert.acknowledged == True
    ).delete()
    db.commit()

    # Check if there are any financial connections
    has_connections = db.query(FinancialConnection).filter(
        FinancialConnection.user_id == user_id,
        FinancialConnection.status == "active"
    ).first() is not None

    if not has_connections:
        alerts.append(ComplianceAlert(
            user_id=user_id,
            alert_type="document_missing",
            severity="info",
            title="No bank accounts connected",
            description="Connect your bank accounts for real-time compliance monitoring.",
            action_url="/personal/connections",
        ))
        db.add(alerts[-1])
        db.commit()
        return alerts

    # Analyze withholding
    analysis = analyze_withholding(user_id, db)

    # Shortfall alert
    if analysis["shortfall"] > UNDERPAYMENT_THRESHOLD:
        alerts.append(ComplianceAlert(
            user_id=user_id,
            alert_type="withholding",
            severity="warning",
            title=f"Estimated tax shortfall: ${analysis['shortfall'] / 100:,.0f}",
            description=f"Your projected tax liability exceeds your withholding by ${analysis['shortfall'] / 100:,.0f}. "
                        f"Consider increasing withholding or making estimated payments.",
            amount=analysis["shortfall"],
        ))
        db.add(alerts[-1])

    # Quarterly estimated tax reminders
    quarter_deadlines = [
        (4, 15, "Q1 estimated tax"),
        (6, 15, "Q2 estimated tax"),
        (9, 15, "Q3 estimated tax"),
        (1, 15, "Q4 estimated tax (prior year)"),
    ]

    for month, day, label in quarter_deadlines:
        deadline = datetime(now.year, month, day, tzinfo=timezone.utc)
        if now < deadline and (deadline - now).days <= 30:
            existing = db.query(ComplianceAlert).filter(
                ComplianceAlert.user_id == user_id,
                ComplianceAlert.alert_type == "estimated_tax",
                ComplianceAlert.due_date == deadline.strftime("%Y-%m-%d"),
            ).first()
            if not existing:
                alerts.append(ComplianceAlert(
                    user_id=user_id,
                    alert_type="estimated_tax",
                    severity="warning",
                    title=f"{label} due {deadline.strftime('%b %d')}",
                    description=f"Your estimated tax payment is due on {deadline.strftime('%B %d, %Y')}. "
                                f"Recommended quarterly payment: ${analysis['quarterly_payment_needed'] / 100:,.0f}",
                    amount=analysis["quarterly_payment_needed"],
                    due_date=deadline.strftime("%Y-%m-%d"),
                    action_url="/personal/projection",
                ))
                db.add(alerts[-1])

    # Transaction categorization review
    uncategorized_count = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.tax_tag == "review",
        Transaction.excluded == False,
    ).count()

    if uncategorized_count > 0:
        alerts.append(ComplianceAlert(
            user_id=user_id,
            alert_type="document_missing",
            severity="info",
            title=f"{uncategorized_count} transactions need review",
            description="Some transactions have uncertain tax treatment and need your review.",
            action_url="/personal/transactions",
        ))
        db.add(alerts[-1])

    # State filing check (simplified)
    facts = {}
    for f in db.query(ProfileFact).filter(ProfileFact.user_id == user_id).all():
        facts[f.key] = f.value

    if facts.get("income_sources") and "employment" in (facts.get("income_sources") or ""):
        alerts.append(ComplianceAlert(
            user_id=user_id,
            alert_type="state_filing",
            severity="info",
            title="Check state filing obligations",
            description="Based on your income sources, you may need to file state tax returns. "
                        "Verify your state filing requirements.",
            action_url="/personal/compliance",
        ))
        db.add(alerts[-1])

    db.commit()
    return alerts


def get_compliance_status(user_id: str, db: Session) -> dict:
    """Get overall compliance status."""
    analysis = analyze_withholding(user_id, db)
    alerts = generate_compliance_alerts(user_id, db)

    # Score compliance (100 = perfect)
    score = 100
    critical_count = sum(1 for a in alerts if a.severity == "critical")
    warning_count = sum(1 for a in alerts if a.severity == "warning")
    score -= critical_count * 25
    score -= warning_count * 10
    score = max(0, score)

    return {
        "score": score,
        "analysis": analysis,
        "alerts": [
            {
                "id": a.id,
                "type": a.alert_type,
                "severity": a.severity,
                "title": a.title,
                "description": a.description,
                "amount": a.amount,
                "due_date": a.due_date,
                "action_url": a.action_url,
                "acknowledged": a.acknowledged,
            }
            for a in alerts
        ],
        "uncategorized_txns": db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.tax_tag == "review",
            Transaction.excluded == False,
        ).count(),
    }
