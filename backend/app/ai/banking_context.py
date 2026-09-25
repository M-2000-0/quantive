"""Banking + Qubo tax awareness for AI chat answers.

Detects questions about the user's *cash* (balances, spending, runway,
income) and *tax deductions* (Qubo findings), and attaches live numbers
from the banking ledger and the Qubo findings table so the assistant
answers with the caller's own data instead of generic advice.

Same honesty contract as portfolio_context: numbers come from the
caller's workspace; anything illustrative (the set-aside rate) is labeled
as such; no advice, just the math on their own data.
"""
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# ── Question classifier ───────────────────────────────────────────────

BANKING_KEYWORDS = (
    "balance", "balances", "account", "accounts", "cash", "runway",
    "spend", "spending", "expense", "expenses", "income", "revenue",
    "transaction", "transactions", "burn", "payroll", "my money",
    "my funds", "my cash", "my accounts", "my runway",
)

QUBO_KEYWORDS = (
    "qubo", "deduction", "deductions", "write-off", "write off",
    "writeoff", "tax break", "tax breaks", "deductible", "set-aside",
    "quarterly estimate", "quarterly estimates", "my tax",
)


def is_banking_question(q: str) -> bool:
    ql = (q or "").lower()
    return any(k in ql for k in BANKING_KEYWORDS)


def is_qubo_question(q: str) -> bool:
    ql = (q or "").lower()
    return any(k in ql for k in QUBO_KEYWORDS)


# ── Ledger aggregation ────────────────────────────────────────────────

def _cents_to_str(v: int) -> str:
    return f"${v / 100:,.2f}"


def _fmt_cents_compact(v: int) -> str:
    dollars = v / 100.0
    if abs(dollars) >= 1e6:
        return f"${dollars / 1e6:,.1f}M"
    if abs(dollars) >= 1e3:
        return f"${dollars / 1e3:,.1f}K"
    return f"${dollars:,.0f}"


def build_banking_snapshot(user, db) -> Optional[Dict[str, Any]]:
    """Aggregate the org's banking ledger into a chat-ready snapshot.

    Returns None when the org has no accounts (AI then falls back to its
    normal knowledge-base answer).
    """
    from app.models.banking import BankAccount, BankTransaction

    accounts = (
        db.query(BankAccount)
        .filter(BankAccount.org_id == user.org_id)
        .all()
    )
    if not accounts:
        return None
    txns = (
        db.query(BankTransaction)
        .filter(BankTransaction.org_id == user.org_id)
        .order_by(BankTransaction.created_at.desc())
        .limit(200)
        .all()
    )

    now = datetime.now(timezone.utc)
    total_cents = sum(a.balance_cents for a in accounts)
    total_in = sum(t.amount_cents for t in txns if t.direction == "in")
    total_out = sum(t.amount_cents for t in txns if t.direction == "out")

    cat_out: Dict[str, int] = {}
    cat_out_count: Dict[str, int] = {}
    for t in txns:
        if t.direction == "out":
            cat_out[t.category] = cat_out.get(t.category, 0) + t.amount_cents
            cat_out_count[t.category] = cat_out_count.get(t.category, 0) + 1
    top_categories = [
        {"category": c, "amount_cents": v, "count": cat_out_count.get(c, 0)}
        for c, v in sorted(cat_out.items(), key=lambda x: -x[1])
    ]

    # Burn/runway: average monthly outflow over the observed window.
    out_txns = [t for t in txns if t.direction == "out" and t.created_at]
    monthly_burn_cents = 0
    window_months = 0
    if out_txns:
        oldest = min(t.created_at for t in out_txns)
        window_days = max((now - oldest.replace(tzinfo=now.tzinfo)).days, 1)
        window_months = max(window_days / 30.44, 0.5)
        monthly_burn_cents = int(total_out / window_months)

    payroll_cents = cat_out.get("Payroll", 0)
    recent = [
        {
            "direction": t.direction,
            "amount_cents": t.amount_cents,
            "counterparty": t.counterparty or t.category,
            "category": t.category,
            "status": t.status,
            "memo": (t.memo or "")[:80],
        }
        for t in txns[:8]
    ]

    return {
        "account_count": len(accounts),
        "accounts": [
            {
                "name": a.name,
                "type": a.account_type,
                "balance_cents": a.balance_cents,
                "currency": a.currency,
            }
            for a in accounts
        ],
        "total_balance_cents": total_cents,
        "txn_count": len(txns),
        "total_in_cents": total_in,
        "total_out_cents": total_out,
        "monthly_burn_cents": monthly_burn_cents,
        "burn_window_months": round(window_months, 1),
        # Runway = months of cash at observed burn (capped for display).
        "runway_months": round(total_cents / monthly_burn_cents, 1) if monthly_burn_cents > 0 else None,
        "payroll_cents": payroll_cents,
        "top_categories": top_categories[:8],
        "recent_transactions": recent,
    }


def build_qubo_snapshot(user, db) -> Optional[Dict[str, Any]]:
    """Aggregate Qubo findings for the org (deductions view)."""
    from app.models.qubo_tax import QuboFinding

    findings = (
        db.query(QuboFinding)
        .filter(QuboFinding.org_id == user.org_id)
        .order_by(QuboFinding.amount_cents.desc())
        .all()
    )
    if not findings:
        return None

    new_f = [f for f in findings if f.status == "new"]
    accepted = [f for f in findings if f.status == "accepted"]
    dismissed = [f for f in findings if f.status == "dismissed"]

    cat_totals: Dict[str, int] = {}
    for f in findings:
        if f.status != "dismissed":
            cat_totals[f.category] = cat_totals.get(f.category, 0) + f.amount_cents
    top_categories = [
        {"category": c, "amount_cents": v}
        for c, v in sorted(cat_totals.items(), key=lambda x: -x[1])
    ]

    open_amount = sum(f.amount_cents for f in findings if f.status != "dismissed")
    return {
        "total_findings": len(findings),
        "new_count": len(new_f),
        "accepted_count": len(accepted),
        "dismissed_count": len(dismissed),
        "open_amount_cents": open_amount,
        "accepted_amount_cents": sum(f.amount_cents for f in accepted),
        "top_categories": top_categories[:6],
        "top_findings": [
            {
                "title": f.title,
                "category": f.category,
                "amount_cents": f.amount_cents,
                "rule_id": f.rule_id,
                "status": f.status,
            }
            for f in findings[:6]
        ],
    }


# ── Context builder ───────────────────────────────────────────────────

def build_banking_context(question: str, user, db) -> Optional[Dict[str, Any]]:
    """Return banking/Qubo context for a question, or None.

    Shape: {"banking": {...}} or {"qubo": {...}} (either or both).
    """
    if not user:
        return None
    wants_banking = is_banking_question(question)
    wants_qubo = is_qubo_question(question)
    if not wants_banking and not wants_qubo:
        return None
    ctx: Dict[str, Any] = {}
    try:
        if wants_banking:
            snap = build_banking_snapshot(user, db)
            if snap:
                ctx["banking"] = snap
    except Exception:
        ctx["banking"] = None
    try:
        if wants_qubo:
            snap = build_qubo_snapshot(user, db)
            if snap:
                ctx["qubo"] = snap
    except Exception:
        ctx["qubo"] = None
    return ctx or None


# ── Formatting ────────────────────────────────────────────────────────

def format_banking_text(snap: Dict[str, Any]) -> str:
    lines = [
        "Your banking (live from your ledger):",
        f"• Total cash: {_cents_to_str(snap['total_balance_cents'])} across {snap['account_count']} accounts",
    ]
    for a in snap["accounts"]:
        lines.append(f"  - {a['name']} ({a['type']}): {_cents_to_str(a['balance_cents'])} {a['currency']}")
    lines.append(
        f"• Flows (last {snap['txn_count']} txns): in {_fmt_cents_compact(snap['total_in_cents'])} / "
        f"out {_fmt_cents_compact(snap['total_out_cents'])}"
    )
    if snap.get("top_categories"):
        cats = ", ".join(
            f"{c['category']} {_fmt_cents_compact(c['amount_cents'])}"
            for c in snap["top_categories"][:5]
        )
        lines.append(f"• Top spending: {cats}")
    if snap.get("runway_months") is not None:
        lines.append(
            f"• Observed burn ≈ {_fmt_cents_compact(snap['monthly_burn_cents'])}/mo "
            f"→ runway ≈ {snap['runway_months']:.0f} months"
        )
    if snap.get("payroll_cents"):
        lines.append(f"• Payroll outflow: {_fmt_cents_compact(snap['payroll_cents'])}")
    return "\n".join(lines)


def format_qubo_text(snap: Dict[str, Any]) -> str:
    lines = [
        "Your Qubo tax findings (live from your workspace):",
        f"• {snap['total_findings']} findings — {snap['new_count']} new, "
        f"{snap['accepted_count']} accepted, {snap['dismissed_count']} dismissed",
        f"• Potentially deductible (open): {_cents_to_str(snap['open_amount_cents'])}",
        f"• Accepted deductions: {_cents_to_str(snap['accepted_amount_cents'])}",
    ]
    if snap.get("top_categories"):
        cats = ", ".join(
            f"{c['category']} {_fmt_cents_compact(c['amount_cents'])}"
            for c in snap["top_categories"][:5]
        )
        lines.append(f"• By category: {cats}")
    if snap.get("top_findings"):
        lines.append("• Largest open findings:")
        for f in snap["top_findings"][:4]:
            if f["status"] == "dismissed":
                continue
            lines.append(f"  - {f['title']} — {_fmt_cents_compact(f['amount_cents'])} ({f['category']}, {f['rule_id']})")
    lines.append(
        "Note: amounts are outflows that may qualify — never promised savings. "
        "Verify requirements per finding in the Qubo workspace."
    )
    return "\n".join(lines)


def format_banking_context_text(ctx: Dict[str, Any]) -> str:
    parts: List[str] = []
    if ctx.get("banking"):
        parts.append(format_banking_text(ctx["banking"]))
    if ctx.get("qubo"):
        parts.append(format_qubo_text(ctx["qubo"]))
    return "\n\n".join(parts)
