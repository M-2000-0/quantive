"""Chat API — conversational interface for Qubo / Banking data.

Returns contextual answers about the user's financial data, Qubo findings,
transactions, and tax deductions. No external LLM dependency — deterministic
rule-based responses that surface real data.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.models.banking import BankAccount, BankTransaction, QuboFinding, TaxDocument, BusinessProfile
from app.security import get_current_user

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list)


def _cents(n: int) -> str:
    return f"${n / 100:,.2f}"


def _answer(user: User, message: str, db: Session) -> str:
    msg = message.lower().strip()

    # Gather context
    accounts = db.query(BankAccount).filter(BankAccount.org_id == user.org_id).all()
    txns = (
        db.query(BankTransaction)
        .filter(BankTransaction.org_id == user.org_id, BankTransaction.status == "posted")
        .order_by(BankTransaction.created_at.desc())
        .limit(200)
        .all()
    )
    findings = (
        db.query(QuboFinding)
        .filter(QuboFinding.org_id == user.org_id)
        .order_by(QuboFinding.created_at.desc())
        .all()
    )
    docs = (
        db.query(TaxDocument)
        .filter(TaxDocument.org_id == user.org_id)
        .all()
    )
    profile = db.query(BusinessProfile).filter(BusinessProfile.org_id == user.org_id).first()

    total_balance = sum(a.balance_cents for a in accounts)
    total_in = sum(t.amount_cents for t in txns if t.direction == "in")
    total_out = sum(t.amount_cents for t in txns if t.direction == "out")
    new_findings = [f for f in findings if f.status == "new"]
    accepted = [f for f in findings if f.status == "accepted"]
    accepted_amount = sum(f.amount_cents for f in accepted)

    # Category breakdown
    cat_out: dict[str, int] = {}
    for t in txns:
        if t.direction == "out":
            cat_out[t.category] = cat_out.get(t.category, 0) + t.amount_cents

    # ── Greeting ────────────────────────────────────────────────────
    if any(w in msg for w in ("hello", "hi", "hey", "good morning", "good afternoon")):
        name = profile.legal_name if profile and profile.legal_name else "there"
        return (
            f"Hey {name}! I'm your Quantive assistant. I can help with:\n\n"
            "• **Banking** — balances, transactions, transfers\n"
            "• **Qubo tax deductions** — scan results, findings, accept/dismiss\n"
            "• **Documents** — upload status, what's needed\n"
            "• **Quarterly estimates** — set-asides and projections\n\n"
            "What would you like to know?"
        )

    # ── Balance / accounts ──────────────────────────────────────────
    if any(w in msg for w in ("balance", "how much", "account", "accounts", "funds")):
        if not accounts:
            return "You don't have any accounts yet. Head to **Banking → Open account** to get started."
        lines = [f"**{_c.account_type.title()}** ({_c.name}): **{_cents(_c.balance_cents)}**" for _c in accounts]
        return f"Your current balances:\n\n" + "\n".join(lines) + f"\n\n**Total: {_cents(total_balance)}**"

    # ── Spending / categories ───────────────────────────────────────
    if any(w in msg for w in ("spend", "spending", "categories", "where", "expense", "expenses")):
        if not cat_out:
            return "No outgoing transactions yet."
        sorted_cats = sorted(cat_out.items(), key=lambda x: -x[1])
        lines = [f"• **{cat}**: {_cents(amt)}" for cat, amt in sorted_cats[:8]]
        return f"Your top spending categories:\n\n" + "\n".join(lines) + f"\n\n**Total outflows: {_cents(total_out)}** across {len(txns)} transactions."

    # ── Income ──────────────────────────────────────────────────────
    if any(w in msg for w in ("income", "revenue", "incoming", "earned")):
        return f"Total income recorded: **{_cents(total_in)}** from {sum(1 for t in txns if t.direction == 'in')} incoming transactions."

    # ── Qubo / deductions ───────────────────────────────────────────
    if any(w in msg for w in ("qubo", "deduction", "deductions", "tax", "write-off", "write off")):
        if not findings:
            return (
                "No Qubo findings yet. Go to **Qubo → Scan ledger** to check your transactions "
                "against current tax rules. The scan looks at outflows in categories like Payroll, "
                "Software, Utilities, and Travel."
            )
        parts = [
            f"**{len(findings)} total findings** ({len(new_findings)} new, {len(accepted)} accepted)",
            f"**Accepted deductions total:** {_cents(accepted_amount)}",
            "",
        ]
        if new_findings:
            parts.append("**New findings needing review:**")
            for f in new_findings[:5]:
                parts.append(f"• {f.title} — {_cents(f.amount_cents)} ({f.category})")
            if len(new_findings) > 5:
                parts.append(f"  …and {len(new_findings) - 5} more")
        parts.append("")
        parts.append("Go to **Qubo workspace** to review and accept/dismiss findings.")
        return "\n".join(parts)

    # ── Quarterly estimates ─────────────────────────────────────────
    if any(w in msg for w in ("quarterly", "quarter", "set-aside", "estimate", "estimates")):
        if not accepted:
            return "No accepted findings yet. Accept some Qubo deductions first to see quarterly estimates."
        q = {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0}
        for f in accepted:
            month = f.created_at.month if f.created_at else 1
            q["Q1" if month <= 3 else "Q2" if month <= 6 else "Q3" if month <= 9 else "Q4"] += f.amount_cents
        rate = 0.25
        lines = [f"**{k}**: {_cents(v)} deductions → **{_cents(int(v * rate))}** set-aside" for k, v in q.items()]
        annual = int(accepted_amount * rate)
        return (
            "Based on your **accepted findings** at a 25% illustrative rate:\n\n"
            + "\n".join(lines)
            + f"\n\n**Annual estimated set-aside: {_cents(annual)}**\n\n"
            "Note: This is illustrative. Actual tax liability depends on jurisdiction, income, and other factors."
        )

    # ── Documents ───────────────────────────────────────────────────
    if any(w in msg for w in ("document", "documents", "upload", "receipt", "receipts", "file", "files")):
        if not docs:
            return (
                "No documents uploaded yet. You can attach supporting documents (receipts, invoices, "
                "payroll registers, W-2s) directly to Qubo findings from the **Qubo workspace**."
            )
        by_status: dict[str, list] = {}
        for d in docs:
            by_status.setdefault(d.status, []).append(d)
        parts = [f"**{len(docs)} total documents**"]
        for status, ds in by_status.items():
            parts.append(f"• {status}: {len(ds)}")
        parts.append("")
        parts.append("Upload documents from the Qubo workspace by clicking **+ Upload document** on any finding.")
        return "\n".join(parts)

    # ── Findings needing action ─────────────────────────────────────
    if any(w in msg for w in ("review", "action", "pending", "new findings")):
        if not new_findings:
            return "Nothing pending! All findings have been reviewed. Nice work."
        parts = [f"**{len(new_findings)} findings need your review:**\n"]
        for f in new_findings[:5]:
            parts.append(f"• **{f.title}** — {_cents(f.amount_cents)}")
            parts.append(f"  Rule: {f.rule_id} | {f.jurisdiction} {f.tax_year}")
        return "\n".join(parts)

    # ── Recent transactions ─────────────────────────────────────────
    if any(w in msg for w in ("recent", "transaction", "transactions", "latest")):
        if not txns:
            return "No transactions recorded yet."
        parts = ["**Recent transactions:**\n"]
        for t in txns[:8]:
            sign = "+" if t.direction == "in" else "−"
            parts.append(f"• {sign}{_cents(t.amount_cents)} — {t.counterparty or t.category} ({t.category})")
        return "\n".join(parts)

    # ── Jurisdiction / country ──────────────────────────────────────
    if any(w in msg for w in ("jurisdiction", "country", "where am i", "location")):
        country = profile.country if profile else "US"
        return f"Your registered jurisdiction is **{country}**. You can change this in the Qubo workspace jurisdiction dropdown."

    # ── Help / what can you do ──────────────────────────────────────
    if any(w in msg for w in ("help", "what can you", "how do", "commands", "options")):
        return (
            "I can help with anything about your Quantive data:\n\n"
            "**Banking**\n"
            "• \"What's my balance?\" — account totals\n"
            "• \"Show recent transactions\" — latest activity\n"
            "• \"Where am I spending?\" — category breakdown\n"
            "• \"What's my income?\" — incoming totals\n\n"
            "**Qubo Tax**\n"
            "• \"Show my deductions\" — Qubo findings overview\n"
            "• \"What needs review?\" — pending findings\n"
            "• \"Quarterly estimates\" — set-aside projections\n"
            "• \"Upload status\" — document tracker\n\n"
            "**Other**\n"
            "• \"What's my jurisdiction?\" — country setting\n"
            "• \"Help\" — this message"
        )

    # ── Fallback ────────────────────────────────────────────────────
    return (
        "I'm not sure what you mean. Try asking about:\n\n"
        "• **Balances** — \"What's my balance?\"\n"
        "• **Transactions** — \"Show recent transactions\"\n"
        "• **Spending** — \"Where am I spending?\"\n"
        "• **Tax deductions** — \"Show my Qubo deductions\"\n"
        "• **Quarterly estimates** — \"What are my quarterly estimates?\"\n"
        "• **Documents** — \"What documents do I have?\"\n"
        "• **Help** — \"What can you do?\""
    )


@router.post("")
def chat(body: ChatRequest, db: Session = Depends(get_db)):
    try:
        # Use first user for demo/testing (no auth required)
        user = db.query(User).order_by(User.created_at).first()
        if not user:
            return {"role": "assistant", "content": "No user found. Please register first."}
        answer = _answer(user, body.message, db)
        return {"role": "assistant", "content": answer}
    except Exception as e:
        return {"role": "assistant", "content": f"I hit an error: {type(e).__name__}: {e}. Make sure you have data in the system."}
