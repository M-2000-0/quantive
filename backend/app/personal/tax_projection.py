"""Tax projection calculator.

Provides YTD tracking, bracket analysis, what-if scenarios,
and quarterly estimated tax calculations.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.personal.compliance import (
    BRACKETS_2026_MFJ,
    BRACKETS_2026_SINGLE,
    STANDARD_DEDUCTION_2026,
    calculate_federal_tax,
    calculate_se_tax,
)
from app.personal.models import ProfileFact, TaxProjection, Transaction


def get_ytd_data(user_id: str, db: Session) -> dict:
    """Get year-to-date income and withholding from transactions."""
    now = datetime.now(timezone.utc)
    year_start = f"{now.year}-01-01"
    year_end = now.strftime("%Y-%m-%d")

    # Income (negative amounts = inflows)
    income_txns = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.date >= year_start,
        Transaction.date <= year_end,
        Transaction.tax_tag.in_(["taxable-revenue", "revenue", "rental"]),
        Transaction.excluded == False,
    ).all()

    ytd_income = sum(-t.amount for t in income_txns if t.amount < 0)

    # Withholding/payments
    tax_payments = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.date >= year_start,
        Transaction.date <= year_end,
        Transaction.tax_tag == "tax-paid",
        Transaction.excluded == False,
    ).all()

    ytd_withholding = sum(t.amount for t in tax_payments)

    # Deductible expenses
    deductible_txns = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.date >= year_start,
        Transaction.date <= year_end,
        Transaction.tax_tag == "deductible",
        Transaction.excluded == False,
    ).all()

    ytd_deductible = sum(t.amount for t in deductible_txns)

    # SE income breakdown
    se_income = 0
    for t in income_txns:
        if t.amount < 0 and t.category in ("revenue",):
            se_income += -t.amount

    return {
        "ytd_income": ytd_income,
        "ytd_withholding": ytd_withholding,
        "ytd_deductible": ytd_deductible,
        "se_income": se_income,
        "months_elapsed": now.month,
    }


def project_annual(user_id: str, db: Session, additional_income: int = 0,
                   additional_deductions: int = 0) -> dict:
    """Project annual tax liability with optional adjustments."""
    facts = {}
    for f in db.query(ProfileFact).filter(ProfileFact.user_id == user_id).all():
        facts[f.key] = f.value

    filing_status = facts.get("filing_status", "single")
    ytd = get_ytd_data(user_id, db)

    now = datetime.now(timezone.utc)
    months = max(ytd["months_elapsed"], 1)

    # Annualize income
    projected_annual_income = int(ytd["ytd_income"] * 12 / months) + additional_income

    # Deductions
    standard_deduction = STANDARD_DEDUCTION_2026.get(filing_status, STANDARD_DEDUCTION_2026["single"])
    projected_itemized = ytd["ytd_deductible"] * 12 // months + additional_deductions

    # Choose better deduction
    use_standard = standard_deduction >= projected_itemized
    deduction = standard_deduction if use_standard else projected_itemized

    # Taxable income
    taxable_income = max(0, projected_annual_income - deduction)

    # Federal tax
    tax_calc = calculate_federal_tax(taxable_income, filing_status)

    # SE tax
    se_tax = calculate_se_tax(ytd["se_income"]) if ytd["se_income"] > 0 else {
        "total_se_tax": 0, "deductible_portion": 0
    }

    # Total tax
    total_tax = tax_calc["tax"] + se_tax["total_se_tax"]

    # Effective rate
    effective_rate = (total_tax / projected_annual_income * 100) if projected_annual_income > 0 else 0.0

    # Quarterly breakdown
    quarterly = total_tax // 4

    # Withholding analysis
    projected_withholding = int(ytd["ytd_withholding"] * 12 / months)
    shortfall = max(0, total_tax - projected_withholding)

    # Bracket visualization
    brackets = BRACKETS_2026_MFJ if filing_status in ("married", "married_filing_jointly") else BRACKETS_2026_SINGLE
    bracket_viz = _build_bracket_viz(taxable_income, brackets)

    return {
        "tax_year": now.year,
        "filing_status": filing_status,
        "projected_annual_income": projected_annual_income,
        "standard_deduction": standard_deduction,
        "projected_itemized": projected_itemized,
        "use_standard": use_standard,
        "deduction_used": deduction,
        "taxable_income": taxable_income,
        "federal_tax": tax_calc["tax"],
        "marginal_rate": tax_calc["marginal_rate"],
        "bracket": tax_calc["bracket"],
        "effective_rate": round(effective_rate, 1),
        "se_tax": se_tax,
        "total_tax": total_tax,
        "projected_withholding": projected_withholding,
        "shortfall": shortfall,
        "quarterly_payment": quarterly,
        "bracket_visualization": bracket_viz,
    }


def _build_bracket_viz(taxable_income: int, brackets: list[tuple[int, float]]) -> list[dict]:
    """Build bracket visualization data."""
    viz = []
    prev_limit = 0
    cumulative = 0

    for limit, rate in brackets:
        if taxable_income <= prev_limit:
            break
        income_in_bracket = min(taxable_income, limit) - prev_limit
        tax_in_bracket = int(income_in_bracket * rate)
        cumulative += tax_in_bracket

        viz.append({
            "bracket": f"{int(rate * 100)}%",
            "range_min": prev_limit,
            "range_max": limit if limit != float("inf") else None,
            "income_in_bracket": income_in_bracket,
            "tax_in_bracket": tax_in_bracket,
            "cumulative_tax": cumulative,
            "pct_of_income": round(income_in_bracket / taxable_income * 100, 1) if taxable_income > 0 else 0,
        })

        prev_limit = limit

    return viz


def what_if(user_id: str, db: Session, scenario: dict) -> dict:
    """Run what-if scenarios for tax planning."""
    base = project_annual(user_id, db)

    # Apply scenario modifications
    additional_income = scenario.get("additional_income", 0)
    additional_deductions = scenario.get("additional_deductions", 0)
    roth_conversion = scenario.get("roth_conversion", 0)
    capital_gain = scenario.get("capital_gain", 0)
    capital_loss = scenario.get("capital_loss", 0)

    adjusted = project_annual(
        user_id, db,
        additional_income=additional_income + capital_gain - capital_loss,
        additional_deductions=additional_deductions,
    )

    # Calculate impact
    tax_difference = adjusted["total_tax"] - base["total_tax"]
    marginal_rate = base["marginal_rate"]

    # Specific scenario insights
    insights = []

    if roth_conversion > 0:
        # Roth conversion: taxed at marginal rate
        conversion_tax = int(roth_conversion * marginal_rate)
        insights.append({
            "type": "roth_conversion",
            "description": f"Converting ${roth_conversion / 100:,.0f} to Roth would cost ${conversion_tax / 100:,.0f} in additional tax",
            "tax_impact": conversion_tax,
            "future_benefit": "Tax-free growth and withdrawals in retirement",
        })

    if capital_loss > 0:
        # Tax-loss harvesting benefit
        max_loss_deduction = min(capital_loss, 300_00_00)  # $30K max
        tax_savings = int(max_loss_deduction * marginal_rate)
        insights.append({
            "type": "tax_loss_harvesting",
            "description": f"Harvesting ${capital_loss / 100:,.0f} in losses could save ${tax_savings / 100:,.0f}",
            "tax_impact": -tax_savings,
            "carryforward": max(0, capital_loss - 300_00_00),
        })

    return {
        "base": base,
        "scenario": adjusted,
        "tax_difference": tax_difference,
        "insights": insights,
    }


def save_projection(user_id: str, db: Session) -> TaxProjection:
    """Save current projection snapshot."""
    projection = project_annual(user_id, db)

    now = datetime.now(timezone.utc)
    tp = TaxProjection(
        user_id=user_id,
        tax_year=now.year,
        ytd_income=projection["projected_annual_income"],
        ytd_withholding=projection["projected_withholding"],
        projected_total_income=projection["projected_annual_income"],
        projected_total_tax=projection["total_tax"],
        estimated_quarterly=projection["quarterly_payment"],
        bracket=projection["bracket"],
        marginal_rate=projection["marginal_rate"],
        effective_rate=projection["effective_rate"],
        standard_deduction=projection["standard_deduction"],
        itemized_deductions=projection["projected_itemized"],
        use_standard=projection["use_standard"],
        detail=projection,
    )
    db.add(tp)
    db.commit()
    db.refresh(tp)
    return tp
