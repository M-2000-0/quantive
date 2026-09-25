"""Tests for suggested follow-up question generation."""
from app.ai.followup_suggestions import MAX_SUGGESTIONS, suggest_followups

SNAP = {
    "total_principal": 1_000_000_000.0,
    "wtd_coupon_pct": 4.5,
    "wtd_maturity_years": 7.0,
    "floating_principal": 100_000_000.0,
    "currency_exposures_usd": {"USD": 700_000_000.0, "EUR": 200_000_000.0, "GBP": 100_000_000.0},
    "currency_mix": {"USD": 70.0, "EUR": 20.0, "GBP": 10.0},
    "nearest_maturities": [
        {"name": "T-Bill Rolling Program", "principal": 60_000_000.0,
         "maturity_date": "2026-12-01", "years_left": 0.2, "coupon": 4.1}
    ],
    "longest_maturity": None,
}


def _ctx(**kw):
    ctx = {"snapshot": SNAP}
    ctx.update(kw)
    return ctx


def test_rate_scenario_suggests_bps_escalation_and_fx():
    out = suggest_followups(
        "What happens to my debt if rates rise 50bps?", "answer",
        portfolio_context=_ctx(shock={"shock_bps": 50.0}, rate_shock_bps=50.0),
    )
    assert 2 <= len(out) <= MAX_SUGGESTIONS
    assert any("rates rise" in s.lower() for s in out)
    assert any("euro" in s.lower() or "pound" in s.lower() for s in out)


def test_fx_scenario_suggests_flip_and_rate_leg():
    out = suggest_followups(
        "what if the euro depreciates 10%?", "answer",
        portfolio_context=_ctx(fx_shock={"currency": "EUR", "pct": 10.0, "direction": "depreciate"}),
    )
    assert any("appreciates" in s for s in out)
    assert any("rates rise 50bps" in s for s in out)


def test_portfolio_summary_suggests_scenario_and_maturity():
    out = suggest_followups("Summarize my portfolio", "answer", portfolio_context=_ctx())
    assert any("rates rise 50bps" in s for s in out)
    assert any("T-Bill Rolling Program" in s for s in out)


def test_no_portfolio_market_fallback():
    out = suggest_followups("What is the price of Bitcoin?", "answer")
    assert 2 <= len(out) <= MAX_SUGGESTIONS
    assert all("my debt" not in s for s in out)


def test_no_portfolio_with_book_suggests_scenario():
    class U:
        org_id = "o"
    out = suggest_followups("hello", "answer", user=U(), db=object())
    # db=object() will fail the snapshot query → market fallback
    assert all("rates" not in s.lower() for s in out)


def test_dedupes_and_caps():
    out = suggest_followups(
        "rates", "answer",
        portfolio_context=_ctx(shock={"shock_bps": 100.0}, rate_shock_bps=100.0),
    )
    assert len(out) <= MAX_SUGGESTIONS
    assert len(set(out)) == len(out)


def test_no_suggestion_repeats_the_question_just_asked():
    q = "What is the price of Bitcoin?"
    out = suggest_followups(q, "answer")
    assert all(o.strip().lower() != q.strip().lower() for o in out)
