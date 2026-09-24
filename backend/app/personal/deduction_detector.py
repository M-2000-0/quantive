"""Deduction Detector — the core killer feature.

Scans user transactions, classifies them into IRS deduction categories,
matches against tax rules, and generates specific deduction recommendations
with estimated tax savings. Runs continuously on connected accounts.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.personal.compliance import (
    BRACKETS_2026_MFJ,
    BRACKETS_2026_SINGLE,
    STANDARD_DEDUCTION_2026,
    calculate_federal_tax,
)
from app.personal.models import (
    PersonalOpportunity,
    ProfileFact,
    Recommendation,
    Transaction,
)
from app.personal.tax_packs import PACKS

logger = logging.getLogger(__name__)

# ── IRS Deduction Categories (Schedule A line items) ─────────────────
DEDUCTION_CATEGORIES: dict[str, dict] = {
    "medical_dental": {
        "schedule_a_line": "1-4",
        "agi_floor": 0.075,
        "irc": "\u00a7213",
        "description": "Medical and dental expenses",
    },
    "salt": {
        "schedule_a_line": "5-7",
        "cap": 10000,
        "irc": "\u00a7164",
        "description": "State and local taxes (SALT)",
    },
    "mortgage_interest": {
        "schedule_a_line": "8a-8e",
        "irc": "\u00a7163",
        "description": "Home mortgage interest",
    },
    "charitable_cash": {
        "schedule_a_line": "12",
        "agi_limit": 0.60,
        "irc": "\u00a7170",
        "description": "Cash charitable contributions",
    },
    "charitable_property": {
        "schedule_a_line": "13",
        "agi_limit": 0.30,
        "irc": "\u00a7170",
        "description": "Non-cash charitable contributions",
    },
    "casualty_theft": {
        "schedule_a_line": "15",
        "irc": "\u00a7165",
        "description": "Casualty and theft losses",
    },
}

# ── Transaction merchant / category keyword mappings ──────────────────
# Maps Plaid-style categories and merchant name substrings to deduction
# categories.  Keys are lowercase.
_CATEGORY_MAP: dict[str, str] = {
    # Medical & Dental
    "doctor": "medical_dental",
    "physician": "medical_dental",
    "hospital": "medical_dental",
    "medical": "medical_dental",
    "dental": "medical_dental",
    "dentist": "medical_dental",
    "pharmacy": "medical_dental",
    "drugstore": "medical_dental",
    "cvs": "medical_dental",
    "walgreens": "medical_dental",
    "vision": "medical_dental",
    "optometrist": "medical_dental",
    "eyecare": "medical_dental",
    "lenscrafters": "medical_dental",
    "lab": "medical_dental",
    "urgent care": "medical_dental",
    "health insurance": "medical_dental",
    "insurance premium": "medical_dental",
    "dental insurance": "medical_dental",
    "blue cross": "medical_dental",
    "aetna": "medical_dental",
    "cigna": "medical_dental",
    "united health": "medical_dental",
    "unitedhealthcare": "medical_dental",
    "humana": "medical_dental",
    "kaiser": "medical_dental",
    "metlife": "medical_dental",
    # SALT — State & Local Taxes
    "property tax": "salt",
    "real estate tax": "salt",
    "state tax": "salt",
    "city tax": "salt",
    "county tax": "salt",
    "local tax": "salt",
    "township tax": "salt",
    "school tax": "salt",
    # Mortgage Interest
    "mortgage": "mortgage_interest",
    "home equity": "mortgage_interest",
    "home loan": "mortgage_interest",
    "escrow": "mortgage_interest",
    "housing loan": "mortgage_interest",
    # Charitable — Cash
    "charity": "charitable_cash",
    "donation": "charitable_cash",
    "church": "charitable_cash",
    "temple": "charitable_cash",
    "mosque": "charitable_cash",
    "synagogue": "charitable_cash",
    "nonprofit": "charitable_cash",
    "non-profit": "charitable_cash",
    "red cross": "charitable_cash",
    "salvation army": "charitable_cash",
    "goodwill": "charitable_cash",
    "united way": "charitable_cash",
    "gofundme": "charitable_cash",
    "kiva": "charitable_cash",
    "donorschoose": "charitable_cash",
    "world vision": "charitable_cash",
    "plan international": "charitable_cash",
    "st jude": "charitable_cash",
    "wikipedia": "charitable_cash",
    "foundation": "charitable_cash",
    # Charitable — Property (in-kind)
    "thrift": "charitable_property",
    "salvation army donation": "charitable_property",
    "goodwill donation": "charitable_property",
    "habitat for humanity": "charitable_property",
    # Casualty & Theft
    "casualty": "casualty_theft",
    "flood insurance claim": "casualty_theft",
    "disaster": "casualty_theft",
    "theft loss": "casualty_theft",
}

# Tax-deductible transaction tax_tags (from Plaid sync / manual tagging)
_DEDUCTIBLE_TAX_TAGS = {"deductible", "tax-paid", "charitable", "medical", "mortgage"}


# ── Helpers ───────────────────────────────────────────────────────────

def _cents_to_dollars(cents: int) -> float:
    return round(cents / 100, 2)


def _dollars_to_cents(dollars: float) -> int:
    return int(round(dollars * 100))


def _year_end_date() -> datetime:
    """Return Dec 31 of the current UTC year."""
    now = datetime.now(timezone.utc)
    return datetime(now.year, 12, 31, tzinfo=timezone.utc)


def _days_until_year_end() -> int:
    now = datetime.now(timezone.utc)
    deadline = _year_end_date()
    return max(0, (deadline - now).days)


# ── Transaction Classifier ───────────────────────────────────────────

class TransactionClassifier:
    """Maps transaction categories / merchant names to deduction categories.

    Performs eligibility checks and returns enriched transaction dicts
    ready for aggregation by DeductionDetector.
    """

    def __init__(self, filing_status: str, agi_cents: int, is_self_employed: bool = False):
        self.filing_status = filing_status
        self.agi_cents = agi_cents
        self.is_self_employed = is_self_employed
        self.standard_deduction = STANDARD_DEDUCTION_2026.get(
            filing_status, STANDARD_DEDUCTION_2026["single"]
        )

    # ── Classification logic ──────────────────────────────────────────

    def classify(self, txn: Transaction) -> Optional[dict]:
        """Return a classification dict or None if not deductible."""
        if txn.excluded:
            return None

        amount_cents = abs(txn.amount)
        if amount_cents == 0:
            return None

        category = self._match_category(txn)
        if category is None:
            return None

        meta = DEDUCTION_CATEGORIES[category]
        eligible = self._check_eligibility(category, amount_cents, meta)
        if not eligible:
            return None

        return {
            "txn_id": txn.id,
            "date": txn.date,
            "name": txn.name,
            "merchant_name": txn.merchant_name,
            "amount_cents": amount_cents,
            "deduction_category": category,
            "schedule_a_line": meta["schedule_a_line"],
            "irc": meta["irc"],
            "confidence": txn.confidence,
            "tax_tag": txn.tax_tag,
        }

    def _match_category(self, txn: Transaction) -> Optional[str]:
        """Match a transaction to a deduction category via keywords."""
        # 1. Explicit tax_tag fast-path
        if txn.tax_tag in _DEDUCTIBLE_TAX_TAGS:
            tag_map = {
                "deductible": None,  # needs keyword match below
                "tax-paid": "salt",
                "charitable": "charitable_cash",
                "medical": "medical_dental",
                "mortgage": "mortgage_interest",
            }
            mapped = tag_map.get(txn.tax_tag)
            if mapped:
                return mapped

        # 2. Keyword match on category + merchant + name
        haystack = " ".join([
            (txn.category or "").lower(),
            (txn.merchant_name or "").lower(),
            (txn.name or "").lower(),
        ])

        # Sort by key length descending so longer (more specific) matches win
        for keyword in sorted(_CATEGORY_MAP, key=len, reverse=True):
            if keyword in haystack:
                return _CATEGORY_MAP[keyword]

        return None

    # ── Eligibility checks ────────────────────────────────────────────

    def _check_eligibility(self, category: str, amount_cents: int, meta: dict) -> bool:
        """Apply IRS eligibility rules.  Returns True if potentially deductible."""
        if category == "medical_dental":
            return self._eligible_medical(amount_cents)
        if category == "salt":
            return self._eligible_salt(amount_cents)
        if category in ("charitable_cash", "charitable_property"):
            return self._eligible_charitable(amount_cents, category)
        if category == "casualty_theft":
            return self._eligible_casualty(amount_cents)
        # mortgage_interest: always potentially deductible (caps depend on loan)
        return True

    def _eligible_medical(self, amount_cents: int) -> bool:
        """Medical expenses are deductible only to the extent they exceed
        7.5% of AGI, and only if the taxpayer itemizes."""
        floor_cents = int(self.agi_cents * 0.075)
        return amount_cents > floor_cents

    def _eligible_salt(self, amount_cents: int) -> bool:
        """SALT is capped at $10,000 ($5,000 if MFS).  Must itemize."""
        cap = 5000_00 if self.filing_status == "married_filing_separately" else 10000_00
        return amount_cents <= cap  # flag transactions potentially within the cap

    def _eligible_charitable(self, amount_cents: int, category: str) -> bool:
        """Charitable contributions are deductible only if the taxpayer
        itemizes.  Cash is limited to 60% AGI; property to 30% AGI."""
        if category == "charitable_cash":
            limit = int(self.agi_cents * 0.60)
        else:
            limit = int(self.agi_cents * 0.30)
        return amount_cents <= limit

    def _eligible_casualty(self, amount_cents: int) -> bool:
        """Casualty losses must be in a federally declared disaster area
        and exceed $100 per event + 10% AGI total."""
        agi_10pct = int(self.agi_cents * 0.10)
        return amount_cents > agi_10pct


# ── Deduction Detector ───────────────────────────────────────────────

class DeductionDetector:
    """Main engine: scan transactions, classify, compute impact, generate opportunities."""

    def __init__(self, db: Session, user_id: str, tax_year: int = 2026):
        self.db = db
        self.user_id = user_id
        self.tax_year = tax_year

    # ── Public API ────────────────────────────────────────────────────

    def detect(self) -> list[dict]:
        """Main entry point.  Returns a list of deduction opportunity dicts."""
        profile = self._get_user_profile()
        start_date = f"{self.tax_year}-01-01"
        end_date = f"{self.tax_year}-12-31"

        transactions = self._get_transactions(start_date, end_date)
        if not transactions:
            return []

        classified = self._classify_transactions(transactions)
        if not classified:
            return []

        impact = self._calculate_deduction_impact(classified, profile)
        opportunities = self._generate_deduction_opportunities(classified, impact)
        return self._deduplicate_against_existing(opportunities)

    # ── Profile helpers ───────────────────────────────────────────────

    def _get_user_profile(self) -> dict:
        """Fetch filing status, AGI, income, existing deductions from ProfileFacts."""
        facts = {}
        for f in self.db.query(ProfileFact).filter(
            ProfileFact.user_id == self.user_id
        ).all():
            facts[f.key] = f.value

        filing_status = facts.get("filing_status", "single")

        # Estimate AGI from income transactions
        income_txns = self.db.query(Transaction).filter(
            Transaction.user_id == self.user_id,
            Transaction.date >= f"{self.tax_year}-01-01",
            Transaction.date <= f"{self.tax_year}-12-31",
            Transaction.tax_tag.in_(["taxable-revenue", "revenue"]),
            Transaction.excluded == False,
        ).all()
        agi_cents = sum(-t.amount for t in income_txns if t.amount < 0)

        # Annualize if partial year
        now = datetime.now(timezone.utc)
        if now.year == self.tax_year and now.month < 12:
            agi_cents = int(agi_cents * 12 / max(now.month, 1))

        is_self_employed = any(
            v in ("business", "freelance", "self-employed")
            for k, v in facts.items()
            if k == "income_sources"
        )

        # Existing claimed deductions
        claimed = {}
        for f in self.db.query(ProfileFact).filter(
            ProfileFact.user_id == self.user_id,
            ProfileFact.category == "deduction_claimed",
        ).all():
            claimed[f.key] = f.value

        # Standard deduction for filing status
        standard = STANDARD_DEDUCTION_2026.get(filing_status, STANDARD_DEDUCTION_2026["single"])

        return {
            "filing_status": filing_status,
            "agi_cents": agi_cents,
            "is_self_employed": is_self_employed,
            "standard_deduction_cents": standard,
            "claimed_deductions": claimed,
        }

    # ── Transaction retrieval ─────────────────────────────────────────

    def _get_transactions(self, start_date: str, end_date: str) -> list[Transaction]:
        """Get transactions in the given date range."""
        return self.db.query(Transaction).filter(
            Transaction.user_id == self.user_id,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.excluded == False,
        ).order_by(Transaction.date).all()

    # ── Classification ────────────────────────────────────────────────

    def _classify_transactions(
        self, transactions: list[Transaction]
    ) -> dict[str, list[dict]]:
        """Classify transactions into deduction categories with amounts.

        Returns {category_key: [classification_dict, ...]}.
        """
        profile = self._get_user_profile()
        classifier = TransactionClassifier(
            filing_status=profile["filing_status"],
            agi_cents=profile["agi_cents"],
            is_self_employed=profile["is_self_employed"],
        )

        result: dict[str, list[dict]] = {}
        for txn in transactions:
            cls = classifier.classify(txn)
            if cls:
                cat = cls["deduction_category"]
                result.setdefault(cat, []).append(cls)

        return result

    # ── Impact calculation ────────────────────────────────────────────

    def _calculate_deduction_impact(
        self, classified: dict[str, list[dict]], profile: dict
    ) -> list[dict]:
        """Calculate the actual tax impact of each deduction category.

        Returns a list of dicts with per-category totals and estimated savings.
        """
        agi_cents = profile["agi_cents"]
        filing_status = profile["filing_status"]
        standard = profile["standard_deduction_cents"]

        # Compute current taxable income under standard deduction
        taxable_standard = max(0, agi_cents - standard)
        tax_standard = calculate_federal_tax(taxable_standard, filing_status)
        marginal_rate = tax_standard["marginal_rate"]

        impacts = []
        for category, txns in classified.items():
            meta = DEDUCTION_CATEGORIES[category]
            raw_total = sum(t["amount_cents"] for t in txns)

            deductible_amount = self._compute_deductible_amount(
                category, raw_total, agi_cents, meta
            )

            if deductible_amount <= 0:
                continue

            # Tax savings = deductible_amount * marginal_rate
            savings_min = int(deductible_amount * marginal_rate * 0.90)  # conservative
            savings_max = int(deductible_amount * marginal_rate * 1.10)  # optimistic

            # Audit risk flags
            audit_risk = self._assess_audit_risk(category, deductible_amount, agi_cents)

            impacts.append({
                "category": category,
                "description": meta["description"],
                "irc": meta["irc"],
                "schedule_a_line": meta["schedule_a_line"],
                "transaction_count": len(txns),
                "raw_total_cents": raw_total,
                "deductible_amount_cents": deductible_amount,
                "marginal_rate": marginal_rate,
                "estimated_savings_min_cents": savings_min,
                "estimated_savings_max_cents": savings_max,
                "audit_risk": audit_risk,
                "transactions": txns,
            })

        # Sort by savings (descending)
        impacts.sort(key=lambda i: i["deductible_amount_cents"], reverse=True)
        return impacts

    def _compute_deductible_amount(
        self, category: str, raw_total: int, agi_cents: int, meta: dict
    ) -> int:
        """Apply category-specific caps and floors to compute deductible amount."""
        if category == "medical_dental":
            floor = int(agi_cents * 0.075)
            return max(0, raw_total - floor)

        if category == "salt":
            cap = meta.get("cap", 10000_00)
            return min(raw_total, cap)

        if category == "charitable_cash":
            limit = int(agi_cents * 0.60)
            return min(raw_total, limit)

        if category == "charitable_property":
            limit = int(agi_cents * 0.30)
            return min(raw_total, limit)

        if category == "casualty_theft":
            agi_10pct = int(agi_cents * 0.10)
            return max(0, raw_total - agi_10pct)

        # mortgage_interest — no computed cap here (loan-specific)
        return raw_total

    def _assess_audit_risk(self, category: str, amount_cents: int, agi_cents: int) -> str:
        """Return 'high', 'medium', or 'low' audit risk for a deduction."""
        if category == "casualty_theft":
            return "high"
        if category == "charitable_property":
            return "high"
        if category == "medical_dental":
            # Large medical deductions relative to AGI raise flags
            if agi_cents > 0 and amount_cents / agi_cents > 0.15:
                return "high"
            return "medium"
        if category == "salt":
            if amount_cents >= 10000_00:
                return "medium"  # at the cap boundary
            return "low"
        if category == "charitable_cash":
            if amount_cents > 5000_00:
                return "medium"
            return "low"
        return "low"

    # ── Opportunity generation ────────────────────────────────────────

    def _generate_deduction_opportunities(
        self, classified: dict[str, list[dict]], impact: list[dict]
    ) -> list[dict]:
        """Generate specific deduction opportunities from classified data."""
        profile = self._get_user_profile()
        standard = profile["standard_deduction_cents"]
        agi_cents = profile["agi_cents"]
        filing_status = profile["filing_status"]

        # Sum all itemizable deductions detected
        total_itemizable = sum(i["deductible_amount_cents"] for i in impact)

        opportunities = []
        for item in impact:
            category = item["category"]
            meta = DEDUCTION_CATEGORIES[category]

            # Determine priority based on dollar impact
            amount_dollars = _cents_to_dollars(item["deductible_amount_cents"])
            if amount_dollars > 500:
                priority = "high"
            elif amount_dollars > 100:
                priority = "medium"
            else:
                priority = "low"

            # Determine rec type (year-end vs immediate)
            days_left = _days_until_year_end()
            rec_type = "year_end" if days_left <= 60 else "immediate"

            # Build the recommendation
            why = self._build_why_text(category, item, profile)
            action_steps = self._build_action_steps(category, item, profile)
            risks = self._build_risks(category, item)

            # Check if itemizing is beneficial
            itemize_beneficial = total_itemizable > standard
            itemize_note = "" if itemize_beneficial else (
                " Note: Your total detected itemized deductions may not exceed "
                "the standard deduction. Verify before acting."
            )

            opportunities.append({
                "title": f"{meta['description']} deduction",
                "category": "deduction_detection",
                "priority": priority,
                "type": rec_type,
                "why": why + itemize_note,
                "estimated_savings_min_cents": item["estimated_savings_min_cents"],
                "estimated_savings_max_cents": item["estimated_savings_max_cents"],
                "irc_section": meta["irc"],
                "action_steps": action_steps,
                "risks": risks,
                "confidence": self._compute_confidence(item),
                "deduction_category": category,
                "transaction_count": item["transaction_count"],
                "raw_total_cents": item["raw_total_cents"],
                "deductible_amount_cents": item["deductible_amount_cents"],
                "schedule_a_line": meta["schedule_a_line"],
                "audit_risk": item["audit_risk"],
                "deadline": f"{self.tax_year}-12-31" if rec_type == "year_end" else "",
                "itemize_required": True,
                "itemize_beneficial": itemize_beneficial,
            })

        return opportunities

    def _build_why_text(self, category: str, item: dict, profile: dict) -> str:
        """Build a human-readable explanation for why this deduction is available."""
        amount = _cents_to_dollars(item["deductible_amount_cents"])
        marginal = round(profile.get("agi_cents", 0) and item["marginal_rate"] * 100, 1)
        count = item["transaction_count"]

        base = {
            "medical_dental": (
                f"You have {count} medical/dental transaction(s) totaling "
                f"${_cents_to_dollars(item['raw_total_cents']):,.2f}. After applying the "
                f"7.5%-of-AGI floor, ${amount:,.2f} may be deductible on Schedule A "
                f"(IRC {item['irc']})."
            ),
            "salt": (
                f"You have {count} state/local tax payment(s) totaling "
                f"${_cents_to_dollars(item['raw_total_cents']):,.2f}. The SALT deduction is "
                f"capped at $10,000. Your deductible amount is ${amount:,.2f} (IRC {item['irc']})."
            ),
            "mortgage_interest": (
                f"You have {count} mortgage-related transaction(s) totaling "
                f"${amount:,.2f}. Mortgage interest is deductible on Schedule A if you "
                f"itemize (IRC {item['irc']})."
            ),
            "charitable_cash": (
                f"You have {count} charitable donation(s) totaling "
                f"${amount:,.2f}. Cash contributions are deductible up to 60% of AGI "
                f"if you itemize (IRC {item['irc']})."
            ),
            "charitable_property": (
                f"You have {count} non-cash donation(s) totaling "
                f"${amount:,.2f}. Non-cash contributions are deductible up to 30% of AGI "
                f"if you itemize (IRC {item['irc']})."
            ),
            "casualty_theft": (
                f"You have {count} casualty/theft loss(es) totaling "
                f"${amount:,.2f}. These are deductible only in federally declared "
                f"disaster areas and must exceed 10% of AGI (IRC {item['irc']})."
            ),
        }

        return base.get(category, f"Potential deduction of ${amount:,.2f} (IRC {item['irc']}).")

    def _build_action_steps(self, category: str, item: dict, profile: dict) -> list[str]:
        """Build specific action steps for claiming this deduction."""
        steps: list[str] = []
        count = item["transaction_count"]

        if category == "medical_dental":
            steps = [
                "Gather all receipts, EOBs, and insurance statements for the year.",
                f"Total your unreimbursed medical expenses and confirm they exceed 7.5% of your AGI.",
                "Ensure you are itemizing deductions (Schedule A) to claim these.",
                "Keep records for 3 years in case of audit.",
            ]
        elif category == "salt":
            steps = [
                "Add up state income tax (or sales tax) + property tax paid this year.",
                "Confirm your combined SALT does not exceed the $10,000 cap ($5,000 if MFS).",
                "Ensure you are itemizing deductions to claim SALT.",
                "Keep property tax bills and state tax returns as documentation.",
            ]
        elif category == "mortgage_interest":
            steps = [
                "Locate Form 1098 from your mortgage lender.",
                "Confirm the loan is acquisition debt (used to buy, build, or improve your home).",
                "Ensure you are itemizing deductions to claim mortgage interest.",
                "If you paid points at closing, those may also be deductible this year.",
            ]
        elif category == "charitable_cash":
            steps = [
                "Collect donation receipts and written acknowledgment letters.",
                "For donations over $250, you must have a contemporaneous written acknowledgment.",
                "Confirm the organization is a qualified 501(c)(3) charity.",
                "Consider bunching donations into one year to exceed the standard deduction.",
            ]
        elif category == "charitable_property":
            steps = [
                "Document the fair market value of donated property at time of donation.",
                "Get a written receipt from the charitable organization.",
                "For non-cash donations over $500, file Form 8283 with your return.",
                "For items over $5,000, you may need a qualified appraisal.",
            ]
        elif category == "casualty_theft":
            steps = [
                "Confirm the loss occurred in a federally declared disaster area.",
                "Document the loss with photos, police reports, or insurance claims.",
                "Subtract any insurance reimbursement from the loss amount.",
                "Each loss must exceed $100; total must exceed 10% of AGI.",
                "File Form 4684 with your return.",
            ]

        steps.append("Verify all amounts against IRS publications for the current tax year.")
        return steps

    def _build_risks(self, category: str, item: dict) -> list[str]:
        """Build risk warnings for this deduction."""
        risks: list[str] = []

        if item["audit_risk"] == "high":
            risks.append("High audit risk — ensure thorough documentation.")
        elif item["audit_risk"] == "medium":
            risks.append("Moderate audit risk — keep detailed records.")

        if category == "medical_dental":
            risks.extend([
                "Only unreimbursed expenses qualify.",
                "The 7.5% AGI floor means many taxpayers cannot benefit.",
            ])
        elif category == "salt":
            risks.extend([
                "The $10,000 SALT cap may limit your deduction.",
                "Alternative Minimum Tax (AMT) may disallow part of SALT.",
            ])
        elif category == "mortgage_interest":
            risks.extend([
                "Home equity loan interest is only deductible if used to buy, build, or improve the home.",
                "Acquisition debt limit is $750K for loans after 12/15/2017.",
            ])
        elif category in ("charitable_cash", "charitable_property"):
            risks.extend([
                "Donations to non-qualified organizations are not deductible.",
                "Appreciated property donations have special rules — consult a tax professional.",
            ])
        elif category == "casualty_theft":
            risks.extend([
                "Only losses in federally declared disaster areas qualify.",
                "The 10% AGI floor and $100 per-event threshold apply.",
            ])

        risks.append("You must itemize deductions (Schedule A) to claim these.")
        return risks

    def _compute_confidence(self, item: dict) -> str:
        """Determine confidence level based on classification source."""
        confidences = [t.get("confidence", "auto") for t in item["transactions"]]
        if all(c == "verified" for c in confidences):
            return "high"
        if any(c == "user_reported" or c == "manual" for c in confidences):
            return "medium"
        return "medium"

    # ── Deduplication ─────────────────────────────────────────────────

    def _deduplicate_against_existing(self, opportunities: list[dict]) -> list[dict]:
        """Filter out opportunities the user has already claimed or dismissed."""
        existing = {
            opp.title
            for opp in self.db.query(PersonalOpportunity).filter(
                PersonalOpportunity.user_id == self.user_id,
                PersonalOpportunity.tax_year == self.tax_year,
                PersonalOpportunity.dismissed == True,
            ).all()
        }

        claimed_keys = {
            f.key
            for f in self.db.query(ProfileFact).filter(
                ProfileFact.user_id == self.user_id,
                ProfileFact.category == "deduction_claimed",
            ).all()
        }

        filtered = []
        for opp in opportunities:
            if opp["title"] in existing:
                continue
            # Check if this specific deduction category was already claimed
            claim_key = f"{self.tax_year}_{opp['deduction_category']}"
            if claim_key in claimed_keys:
                continue
            filtered.append(opp)

        return filtered

    # ── Persistence helpers ───────────────────────────────────────────

    def persist_opportunities(self, opportunities: list[dict]) -> list[PersonalOpportunity]:
        """Persist deduction opportunities as PersonalOpportunity rows."""
        rows = []
        for opp in opportunities:
            row = PersonalOpportunity(
                user_id=self.user_id,
                tax_year=self.tax_year,
                title=opp["title"],
                category=opp["category"],
                relevance=opp["priority"],
                why=opp["why"],
                needs_info=[],
                needs_docs=opp["action_steps"],
                rule_refs=[opp["irc_section"]],
                next_action=opp["action_steps"][0] if opp["action_steps"] else "",
                status="potentially_relevant",
            )
            self.db.add(row)
            rows.append(row)
        self.db.commit()
        for r in rows:
            self.db.refresh(r)
        return rows

    def persist_recommendations(self, opportunities: list[dict]) -> list[Recommendation]:
        """Persist deduction opportunities as Recommendation rows."""
        recs = []
        for opp in opportunities:
            rec = Recommendation(
                user_id=self.user_id,
                tax_year=self.tax_year,
                title=opp["title"],
                category=opp["category"],
                priority=opp["priority"],
                type=opp["type"],
                why=opp["why"],
                estimated_savings_min=opp["estimated_savings_min_cents"],
                estimated_savings_max=opp["estimated_savings_max_cents"],
                confidence=opp["confidence"],
                irc_section=opp["irc_section"],
                action_steps=opp["action_steps"],
                risks=opp["risks"],
                deadline=opp["deadline"],
                status="new",
            )
            self.db.add(rec)
            recs.append(rec)
        self.db.commit()
        for r in recs:
            self.db.refresh(r)
        return recs


# ── Public summary function ──────────────────────────────────────────

def get_deduction_summary(
    user_id: str, db: Session, tax_year: int = 2026
) -> dict:
    """Return a comprehensive summary of all detected deductions.

    Returns:
        total_detected: total dollar amount of deductions found
        total_estimated_savings: total estimated tax savings
        deductions_by_category: breakdown by category
        standard_vs_itemized: comparison showing whether itemizing is beneficial
        deductions_found: list of specific deduction opportunities
        next_actions: prioritized list of actions to take
        days_until_deadline: days remaining until year-end
    """
    detector = DeductionDetector(db, user_id, tax_year)
    opportunities = detector.detect()

    total_detected = sum(o["deductible_amount_cents"] for o in opportunities)
    total_savings_min = sum(o["estimated_savings_min_cents"] for o in opportunities)
    total_savings_max = sum(o["estimated_savings_max_cents"] for o in opportunities)

    # Breakdown by category
    by_category: dict[str, dict] = {}
    for opp in opportunities:
        cat = opp["deduction_category"]
        if cat not in by_category:
            by_category[cat] = {
                "description": DEDUCTION_CATEGORIES[cat]["description"],
                "irc": DEDUCTION_CATEGORIES[cat]["irc"],
                "total_amount_cents": 0,
                "transaction_count": 0,
                "items": [],
            }
        by_category[cat]["total_amount_cents"] += opp["deductible_amount_cents"]
        by_category[cat]["transaction_count"] += opp["transaction_count"]
        by_category[cat]["items"].append({
            "title": opp["title"],
            "amount_cents": opp["deductible_amount_cents"],
            "savings_min_cents": opp["estimated_savings_min_cents"],
            "savings_max_cents": opp["estimated_savings_max_cents"],
            "confidence": opp["confidence"],
            "audit_risk": opp["audit_risk"],
        })

    # Standard vs. itemized comparison
    profile = detector._get_user_profile()
    standard = profile["standard_deduction_cents"]
    itemize_beneficial = total_detected > standard
    gap_to_standard = standard - total_detected

    standard_vs_itemized = {
        "standard_deduction_cents": standard,
        "detected_itemized_cents": total_detected,
        "itemize_beneficial": itemize_beneficial,
        "gap_to_standard_cents": max(0, gap_to_standard),
        "excess_over_standard_cents": max(0, total_detected - standard),
    }

    # Prioritized next actions
    next_actions = []
    sorted_opps = sorted(opportunities, key=lambda o: (
        {"high": 0, "medium": 1, "low": 2}.get(o["priority"], 2),
        -o["deductible_amount_cents"],
    ))
    for opp in sorted_opps:
        for step in opp["action_steps"][:1]:
            next_actions.append({
                "action": step,
                "category": opp["deduction_category"],
                "priority": opp["priority"],
                "irc": opp["irc_section"],
            })

    return {
        "total_detected_cents": total_detected,
        "total_detected_dollars": _cents_to_dollars(total_detected),
        "total_estimated_savings_min_cents": total_savings_min,
        "total_estimated_savings_max_cents": total_savings_max,
        "total_estimated_savings_min_dollars": _cents_to_dollars(total_savings_min),
        "total_estimated_savings_max_dollars": _cents_to_dollars(total_savings_max),
        "deductions_by_category": by_category,
        "standard_vs_itemized": standard_vs_itemized,
        "deductions_found": opportunities,
        "next_actions": next_actions,
        "days_until_deadline": _days_until_year_end(),
        "tax_year": tax_year,
        "filing_status": profile["filing_status"],
        "agi_dollars": _cents_to_dollars(profile["agi_cents"]),
    }
