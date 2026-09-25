"""Tests for banking/Qubo awareness in AI chat (banking_context)."""
from types import SimpleNamespace

import pytest

from app.ai.banking_context import (
    build_banking_context,
    build_banking_snapshot,
    build_qubo_snapshot,
    format_banking_context_text,
    format_banking_text,
    format_qubo_text,
    is_banking_question,
    is_qubo_question,
)


class _Q:
    """Fake query chain: query(...).filter(...).all() -> rows."""
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *a, **k):
        return self

    def order_by(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None


class _DB:
    def __init__(self, accounts=(), txns=(), findings=()):
        self._accounts, self._txns, self._findings = accounts, txns, findings

    def query(self, model):
        name = model.__name__
        return _Q({"BankAccount": self._accounts, "BankTransaction": self._txns,
                   "QuboFinding": self._findings}[name])


def _acct(cents, name="Operating"):
    return SimpleNamespace(balance_cents=cents, name=name, account_type="operating", currency="USD", org_id="o")


def _txn(cents, direction, category, days_ago):
    from datetime import datetime, timedelta, timezone
    return SimpleNamespace(
        amount_cents=cents, direction=direction, category=category,
        counterparty="X", memo="", status="posted", org_id="o",
        created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
    )


def _finding(cents, title, category, status="new", rule="QBIZ-2026-x"):
    from datetime import datetime, timezone
    return SimpleNamespace(
        amount_cents=cents, title=title, category=category, status=status,
        rule_id=rule, org_id="o", created_at=datetime.now(timezone.utc),
    )


USER = SimpleNamespace(org_id="o", id="u")


# ── Classifier ────────────────────────────────────────────────────────

def test_banking_classifier():
    assert is_banking_question("where is my money going? spending breakdown")
    assert is_banking_question("how much runway do I have?")
    assert is_banking_question("show recent transactions")
    assert not is_banking_question("what is the price of ethereum?")
    assert not is_banking_question("what happens to my debt if rates rise 50bps?")


def test_qubo_classifier():
    assert is_qubo_question("show my top deductions")
    assert is_qubo_question("any Qubo findings?")
    assert is_qubo_question("what are my tax breaks?")
    assert not is_qubo_question("what is the price of bitcoin?")


# ── Snapshot math ─────────────────────────────────────────────────────

def test_banking_snapshot_balances_and_burn():
    db = _DB(
        accounts=[_acct(1_000_000), _acct(2_000_000, "Reserve")],
        txns=[
            _txn(300_000, "out", "Payroll", 5),
            _txn(100_000, "out", "Software", 10),
            _txn(500_000, "in", "Income", 2),
        ],
    )
    snap = build_banking_snapshot(USER, db)
    assert snap["total_balance_cents"] == 3_000_000
    assert snap["account_count"] == 2
    assert snap["total_out_cents"] == 400_000
    assert snap["total_in_cents"] == 500_000
    assert snap["top_categories"][0]["category"] == "Payroll"
    assert snap["monthly_burn_cents"] > 0
    assert snap["runway_months"] == round(3_000_000 / snap["monthly_burn_cents"], 1)


def test_banking_snapshot_none_without_accounts():
    assert build_banking_snapshot(USER, _DB()) is None


def test_qubo_snapshot_aggregation():
    db = _DB(findings=[
        _finding(50_000, "A", "Travel", "new"),
        _finding(30_000, "B", "Travel", "accepted"),
        _finding(20_000, "C", "Software", "dismissed"),
    ])
    snap = build_qubo_snapshot(USER, db)
    assert snap["total_findings"] == 3
    assert snap["new_count"] == 1 and snap["accepted_count"] == 1 and snap["dismissed_count"] == 1
    assert snap["open_amount_cents"] == 80_000  # dismissed excluded
    assert snap["accepted_amount_cents"] == 30_000
    assert snap["top_categories"][0]["category"] == "Travel"


def test_qubo_snapshot_none_without_findings():
    assert build_qubo_snapshot(USER, _DB()) is None


# ── Context assembly ──────────────────────────────────────────────────

def test_build_context_dispatch_and_guards():
    db = _DB(accounts=[_acct(1_000_000)], findings=[_finding(10_000, "A", "Travel")])
    ctx = build_banking_context("show my spending and deductions", USER, db)
    assert "banking" in ctx and "qubo" in ctx
    assert build_banking_context("what is the price of ethereum?", USER, db) is None
    assert build_banking_context("", None, db) is None


# ── Formatting ────────────────────────────────────────────────────────

def test_formatting_includes_live_numbers_and_honesty_note():
    bdb = _DB(accounts=[_acct(3_000_000)], txns=[_txn(150_000, "out", "Payroll", 3)])
    qdb = _DB(findings=[_finding(82_154, "Wages", "Payroll", "new")])
    ctx = build_banking_context("spending and deductions", USER, bdb)
    ctx["qubo"] = build_qubo_snapshot(USER, qdb)
    text = format_banking_context_text(ctx)
    assert "$30,000.00" in text or "$3,000" in text
    assert "runway" in text.lower()
    assert "never promised savings" in text


def test_qubo_formatting_excludes_dismissed_from_top_findings():
    snap = {
        "total_findings": 2, "new_count": 1, "accepted_count": 0, "dismissed_count": 1,
        "open_amount_cents": 50_000, "accepted_amount_cents": 0,
        "top_categories": [{"category": "Travel", "amount_cents": 50_000}],
        "top_findings": [
            {"title": "Keep", "category": "Travel", "amount_cents": 50_000, "rule_id": "R1", "status": "new"},
            {"title": "Drop", "category": "Travel", "amount_cents": 20_000, "rule_id": "R2", "status": "dismissed"},
        ],
    }
    out = format_qubo_text(snap)
    assert "Keep" in out and "Drop" not in out


# ── Follow-up chips ───────────────────────────────────────────────────

def test_banking_turn_suggests_cross_stack_chips():
    from app.ai.followup_suggestions import suggest_followups
    out = suggest_followups("how much runway do I have?", "answer")
    assert any("spending" in s.lower() for s in out)
    assert any("qubo" in s.lower() or "deduction" in s.lower() for s in out)
    assert len(out) <= 3
