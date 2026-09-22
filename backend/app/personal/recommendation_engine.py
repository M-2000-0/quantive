"""Personalized tax-saving recommendation engine.

Generates ranked, explainable recommendations based on the user's
financial profile, opportunity detection, compliance status, and
tax projection.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.personal.compliance import analyze_withholding, calculate_federal_tax, STANDARD_DEDUCTION_2026
from app.personal.models import (
    PersonalOpportunity,
    ProfileFact,
    Recommendation,
    Transaction,
)
from app.personal.tax_projection import project_annual


def generate_recommendations(user_id: str, db: Session, tax_year: int = 2026) -> list[Recommendation]:
    """Generate personalized recommendations based on user profile and data."""
    now = datetime.now(timezone.utc)

    # Get user facts
    facts = {}
    for f in db.query(ProfileFact).filter(ProfileFact.user_id == user_id).all():
        facts[f.key] = f.value

    # Get existing opportunities
    opportunities = db.query(PersonalOpportunity).filter(
        PersonalOpportunity.user_id == user_id,
        PersonalOpportunity.tax_year == tax_year,
        PersonalOpportunity.dismissed == False,
    ).all()

    # Get projection
    projection = project_annual(user_id, db)

    # Get withholding analysis
    withholding = analyze_withholding(user_id, db)

    # Clear old recommendations
    db.query(Recommendation).filter(
        Recommendation.user_id == user_id,
        Recommendation.tax_year == tax_year,
        Recommendation.status == "new",
    ).delete()
    db.commit()

    recommendations = []

    # ── Compliance Recommendations ────────────────────────────────────
    if withholding["shortfall"] > 100_00:  # $100+ shortfall
        recommendations.append(Recommendation(
            user_id=user_id,
            tax_year=tax_year,
            title="Increase withholding or make estimated payment",
            category="compliance",
            priority="high",
            type="compliance",
            why=f"Your projected tax liability (${projection['total_tax'] / 100:,.0f}) exceeds your current withholding "
                f"(${projection['projected_withholding'] / 100:,.0f}) by ${withholding['shortfall'] / 100:,.0f}. "
                f"Underpayment penalties apply if you owe $1,000+ at filing.",
            estimated_savings_min=0,
            estimated_savings_max=-withholding["shortfall"],
            confidence="high",
            irc_section="IRC §6654",
            action_steps=[
                f"Option 1: Increase W-4 withholding by ${(withholding['shortfall'] // 3).max(0) / 100:,.0f}/month",
                f"Option 2: Make estimated payment of ${withholding['quarterly_payment_needed'] / 100:,.0f} by next deadline",
                "Use the IRS withholding calculator for precise adjustment",
            ],
            risks=["Underpayment penalty of ~5% annually on shortfall", "May overpay if income changes"],
            deadline="quarterly",
        ))

    # ── Deduction Recommendations ─────────────────────────────────────
    if not projection["use_standard"]:
        savings = projection["projected_itemized"] - projection["standard_deduction"]
        recommendations.append(Recommendation(
            user_id=user_id,
            tax_year=tax_year,
            title="Itemize deductions this year",
            category="deductions",
            priority="high",
            type="strategic",
            why=f"Your projected itemized deductions (${projection['projected_itemized'] / 100:,.0f}) exceed the standard "
                f"deduction (${projection['standard_deduction'] / 100:,.0f}) by ${savings / 100:,.0f}.",
            estimated_savings_min=int(savings * projection["marginal_rate"]),
            estimated_savings_max=int(savings * projection["marginal_rate"]),
            confidence="high",
            irc_section="IRC §63",
            action_steps=[
                "Ensure all deductible expenses are tracked",
                "Consider bunching deductions into this year",
                "Keep receipts for all itemized deductions",
            ],
            risks=["Standard deduction may be better if income changes"],
        ))
    else:
        gap = projection["standard_deduction"] - projection["projected_itemized"]
        if gap < 500_00_00:  # Within $500 of standard deduction
            recommendations.append(Recommendation(
                user_id=user_id,
                tax_year=tax_year,
                title="Consider deduction bunching",
                category="deductions",
                priority="medium",
                type="strategic",
                why=f"You're ${gap / 100:,.0f} away from benefiting from itemizing. "
                    f"Bunching deductions could push you over the threshold.",
                estimated_savings_min=0,
                estimated_savings_max=int(gap * projection["marginal_rate"]),
                confidence="medium",
                irc_section="IRC §63",
                action_steps=[
                    "Consider prepaying January expenses in December",
                    "Make charitable contributions before year-end",
                    "Bunch medical procedures into one year if possible",
                ],
                risks=["May not reach threshold even with bunching"],
            ))

    # ── Retirement Recommendations ────────────────────────────────────
    if facts.get("retirement") == "yes":
        # Check if maximizing contributions
        ytd_retirement = 0
        now_month = now.month
        for t in db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.date >= f"{now.year}-01-01",
            Transaction.category == "retirement",
            Transaction.excluded == False,
        ).all():
            ytd_retirement += abs(t.amount)

        annualized_retirement = int(ytd_retirement * 12 / max(now_month, 1))
        max_401k = 23500_00  # $23,500

        if annualized_retirement < max_401k:
            gap = max_401k - annualized_retirement
            tax_savings = int(gap * projection["marginal_rate"])
            recommendations.append(Recommendation(
                user_id=user_id,
                tax_year=tax_year,
                title="Maximize 401(k) contributions",
                category="retirement",
                priority="high",
                type="behavioral",
                why=f"You're on track to contribute ${annualized_retirement / 100:,.0f} to your 401(k), "
                    f"which is ${gap / 100:,.0f} below the $23,500 limit. Increasing contributions saves "
                    f"${tax_savings / 100:,.0f} in taxes.",
                estimated_savings_min=tax_savings,
                estimated_savings_max=tax_savings,
                confidence="high",
                irc_section="IRC §402(g)",
                action_steps=[
                    f"Increase 401(k) contribution by ${(gap // max(1, 12 - now_month + 1)) / 100:,.0f}/month",
                    "Contact HR or adjust through payroll portal",
                    "Consider catch-up contribution if age 50+",
                ],
                risks=["Reduces take-home pay", "Contribution limits may change"],
            ))

    # ── Opportunity-Specific Recommendations ──────────────────────────
    for opp in opportunities:
        if opp.relevance == "high" and opp.rule_refs:
            # Check if we already have a recommendation for this
            existing_titles = {r.title for r in recommendations}
            if opp.title not in existing_titles:
                recommendations.append(Recommendation(
                    user_id=user_id,
                    tax_year=tax_year,
                    title=f"Review: {opp.title}",
                    category=opp.category,
                    priority="medium",
                    type="immediate",
                    why=opp.why,
                    confidence="medium",
                    irc_section=opp.rule_refs[0] if opp.rule_refs else "",
                    action_steps=[opp.next_action] if opp.next_action else [],
                    risks=["Verify eligibility before acting"],
                ))

    # ── Tax-Loss Harvesting (if applicable) ──────────────────────────
    if facts.get("invest_accounts") == "yes" or facts.get("investment_income") == "yes":
        # Check for potential harvesting
        investment_txns = db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.category == "investment",
            Transaction.excluded == False,
        ).count()

        if investment_txns > 0:
            recommendations.append(Recommendation(
                user_id=user_id,
                tax_year=tax_year,
                title="Review portfolio for tax-loss harvesting",
                category="investments",
                priority="medium",
                type="year_end",
                why="If you have investments with unrealized losses, harvesting them before year-end "
                    "can offset capital gains and reduce your tax bill.",
                estimated_savings_min=0,
                estimated_savings_max=500_00_00,  # $500 estimate
                confidence="low",
                irc_section="IRC §1211",
                action_steps=[
                    "Review brokerage positions for unrealized losses",
                    "Check wash sale rules (30-day window)",
                    "Consider substitute securities to maintain exposure",
                    "Harvest before December 31",
                ],
                risks=["Wash sale rules", "May miss recovery", "Transaction costs"],
                deadline="12-31",
            ))

    # ── HSA Recommendation ────────────────────────────────────────────
    if facts.get("health_insurance") == "yes":
        recommendations.append(Recommendation(
            user_id=user_id,
            tax_year=tax_year,
            title="Maximize HSA contributions (if eligible)",
            category="health",
            priority="medium",
            type="behavioral",
            why="If you have a high-deductible health plan, an HSA offers triple tax advantage: "
                "deductible contributions, tax-free growth, and tax-free withdrawals for medical expenses.",
            estimated_savings_min=0,
            estimated_savings_max=830_00_00,  # $830 max deduction
            confidence="low",
            irc_section="IRC §223",
            action_steps=[
                "Verify your health plan qualifies for HSA",
                "Contribute up to the annual limit",
                "Invest HSA funds for long-term growth",
            ],
            risks=["Must have qualifying HDHP", "Penalties for non-qualified withdrawals"],
        ))

    # ── Sort by priority and confidence ───────────────────────────────
    priority_order = {"high": 0, "medium": 1, "low": 2}
    confidence_order = {"high": 0, "medium": 1, "low": 2}
    recommendations.sort(key=lambda r: (
        priority_order.get(r.priority, 2),
        confidence_order.get(r.confidence, 2),
    ))

    # Persist
    for rec in recommendations:
        db.add(rec)
    db.commit()

    for rec in recommendations:
        db.refresh(rec)

    return recommendations


def update_recommendation_status(rec_id: str, status: str, user_id: str, db: Session) -> Optional[Recommendation]:
    """Update a recommendation's status."""
    rec = db.query(Recommendation).filter(
        Recommendation.id == rec_id,
        Recommendation.user_id == user_id,
    ).first()
    if not rec:
        return None
    rec.status = status
    db.commit()
    db.refresh(rec)
    return rec
