"""Tests for chained what-if scenarios (rate + FX composition).

Covers the "and if the euro depreciates 10% on top of that?" flow:
FX shock parsing, FX impact math, combined rate+FX scenario math, and the
chaining rule that the FX turn inherits bps from the anchored prior turn.
"""
from app.ai.portfolio_context import (
    compute_fx_impact,
    compute_rate_shock,
    extract_fx_shock,
    is_portfolio_question,
)

SNAP = {
    "total_principal": 1_000_000_000.0,
    "wtd_coupon_pct": 4.5,
    "wtd_maturity_years": 7.0,
    # Per-instrument duration aggregate (drives MTM when present).
    "wtd_duration_years": 7.0,
    "floating_principal": 100_000_000.0,
    "currency_exposures_usd": {"USD": 700_000_000.0, "EUR": 200_000_000.0, "GBP": 100_000_000.0},
    "currency_mix": {"USD": 70.0, "EUR": 20.0, "GBP": 10.0},
    "nearest_maturities": [],
}


# ── FX shock parsing ──────────────────────────────────────────────────

def test_parse_euro_depreciation():
    fx = extract_fx_shock("and if the euro depreciates 10% on top of that?")
    assert fx == {"currency": "EUR", "pct": 10.0, "direction": "depreciate"}


def test_parse_weaken_by_percent():
    fx = extract_fx_shock("what if EUR weakens by 5 percent")
    assert fx == {"currency": "EUR", "pct": 5.0, "direction": "depreciate"}


def test_parse_noun_form_appreciation():
    fx = extract_fx_shock("and a 15% appreciation of the pound?")
    assert fx == {"currency": "GBP", "pct": 15.0, "direction": "appreciate"}


def test_parse_dollar_strengthening():
    fx = extract_fx_shock("if the dollar strengthens 3%")
    assert fx == {"currency": "USD", "pct": 3.0, "direction": "appreciate"}


def test_no_fx_shock_in_market_or_rate_questions():
    assert extract_fx_shock("what about ethereum?") is None
    assert extract_fx_shock("rates rise 50bps") is None
    assert extract_fx_shock("what is the price of Bitcoin?") is None


# ── FX impact math ────────────────────────────────────────────────────

def test_fx_depreciation_mtm_is_negative():
    out = compute_fx_impact(SNAP, "EUR", 10.0, "depreciate")
    assert out["exposure_usd"] == 200_000_000.0
    assert out["revalued_usd"] == 180_000_000.0
    assert out["mtm_impact"] == -20_000_000.0
    assert out["share_of_book_pct"] == 20.0


def test_fx_appreciation_mtm_is_positive():
    out = compute_fx_impact(SNAP, "GBP", 10.0, "appreciate")
    assert out["mtm_impact"] == 10_000_000.0
    assert out["revalued_usd"] == 110_000_000.0


def test_fx_on_unheld_currency_is_zero():
    out = compute_fx_impact(SNAP, "JPY", 10.0, "depreciate")
    assert out["exposure_usd"] == 0.0
    assert out["mtm_impact"] == 0.0


# ── Combined rate + FX scenario ───────────────────────────────────────

def test_rate_only_unchanged():
    out = compute_rate_shock(SNAP, 50.0)
    assert out["mtm_impact"] == -35_000_000.0  # -D*dy*P = 7*0.005*1B
    assert out["duration_source"] == "per-instrument"
    assert "fx_impact" not in out
    assert "combined_mtm_impact" not in out


def test_combined_rate_and_fx():
    out = compute_rate_shock(SNAP, 50.0, fx_shock={"currency": "EUR", "pct": 10.0, "direction": "depreciate"})
    assert out["mtm_impact"] == -35_000_000.0
    assert out["fx_impact"]["mtm_impact"] == -20_000_000.0
    assert out["combined_mtm_impact"] == -55_000_000.0


def test_combined_opposite_directions_partial_offset():
    out = compute_rate_shock(SNAP, 100.0, fx_shock={"currency": "EUR", "pct": 5.0, "direction": "appreciate"})
    assert out["combined_mtm_impact"] == -70_000_000.0 + 10_000_000.0


# ── Portfolio classification for chained turns ────────────────────────

def test_chained_fx_turn_is_a_portfolio_question():
    # The chat endpoints feed the *resolved* question (anchor + FX turn),
    # so classification runs on the combined text.
    resolved = "What happens to my debt if rates rise 50bps? and if the euro depreciates 10% on top of that?"
    assert is_portfolio_question(resolved)
    assert is_portfolio_question("if the euro depreciates 10% what happens to my debt?")


def test_bare_fx_phrase_alone_is_not_portfolio():
    # Without an anchor the phrase has no possessive cue — callers must
    # resolve follow-ups before classifying (resolve_followup does).
    assert not is_portfolio_question("and if the euro depreciates 10%?")
    assert not is_portfolio_question("will the euro depreciate this year")
