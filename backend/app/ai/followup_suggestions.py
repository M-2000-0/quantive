"""Suggested follow-up questions for AI chat answers.

After each answer the assistant proposes 2–3 next questions, rendered as
clickable chips in the widget. Generation is deterministic (no extra model
call): the last portfolio context and market context on the turn decide
which template set applies, and portfolio suggestions quote the caller's
own numbers from the same snapshot the answer used.
"""
from typing import Any, Dict, List, Optional

from app.ai.portfolio_context import (
    _fmt_money,
    build_portfolio_snapshot,
    extract_fx_shock,
)

MAX_SUGGESTIONS = 3

# ── Scenario suggestions (portfolio snapshot aware) ───────────────────

SCENARIO_BPS_LADDER = [25, 100, 200]


def _scenario_suggestions(snap: Dict[str, Any], current_bps: Optional[float]) -> List[str]:
    out: List[str] = []
    if current_bps is not None:
        # First chip escalates the scenario just answered (new total shock),
        # second offers the next clean rung on the ladder (skipped when it
        # duplicates the escalation number).
        out.append(f"What happens to my debt if rates rise {current_bps + 25:g}bps on top of that?")
        higher = [b for b in SCENARIO_BPS_LADDER if b > current_bps and b != current_bps + 25]
        if higher:
            out.append(f"What if rates rise {higher[0]:g}bps?")
        else:
            out.append("What if rates fall 100bps instead?")
        return out[:2]
    return [f"What if rates rise {b:g}bps?" for b in SCENARIO_BPS_LADDER[:2]]


def _fx_suggestions(snap: Dict[str, Any], current_fx: Optional[Dict[str, Any]]) -> List[str]:
    exposures = snap.get("currency_exposures_usd") or {}
    held = [c for c in ("EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "CNY") if exposures.get(c, 0.0) > 0]
    names = {"EUR": "euro", "GBP": "pound", "JPY": "yen", "CHF": "Swiss franc",
             "CAD": "Canadian dollar", "AUD": "Australian dollar", "CNY": "yuan"}
    out: List[str] = []
    if current_fx:
        # Chain: same currency, opposite direction.
        other = "appreciates" if current_fx["direction"] == "depreciate" else "depreciates"
        out.append(f"What if the {names.get(current_fx['currency'], current_fx['currency'])} "
                   f"{other} 10% instead?")
        other_ccys = [c for c in held if c != current_fx["currency"]]
        if other_ccys:
            out.append(f"And if the {names.get(other_ccys[0], other_ccys[0]).lower()} depreciates 10% on top of that?")
    elif held:
        out.append(f"What happens to my debt if the {names.get(held[0], held[0]).lower()} depreciates 10%?")
    return out[:2]


def _maturity_suggestion(snap: Dict[str, Any]) -> str:
    near = (snap.get("nearest_maturities") or [{}])[0]
    return f"When does my {near.get('name', 'nearest bond')} mature and how much do I owe?"


# ── Market suggestions (mirror market_context symbols) ────────────────

MARKET_SUGGESTIONS = [
    "What is the price of Bitcoin?",
    "How are Treasury yields moving today?",
    "How is the market doing today?",
]


def suggest_followups(
    question: str,
    answer: str,
    portfolio_context: Optional[Dict[str, Any]] = None,
    user=None,
    db=None,
) -> List[str]:
    """Return up to 3 suggested next questions for this exchange."""
    ctx = portfolio_context or {}
    snap = ctx.get("snapshot")
    has_shock = bool(ctx.get("shock"))
    fx_in_ctx = ctx.get("fx_shock")

    out: List[str] = []

    if has_shock:
        out.extend(_scenario_suggestions(snap, ctx.get("rate_shock_bps")))
        if fx_in_ctx or (snap or {}).get("currency_exposures_usd"):
            out.extend(_fx_suggestions(snap, fx_in_ctx) if fx_in_ctx else
                       [_fx_suggestions(snap, None)[0]])
    elif fx_in_ctx:
        # FX-only scenario answered: offer the rate leg and the flip.
        out.extend(_fx_suggestions(snap, fx_in_ctx)[:1])
        out.append("What happens to my debt if rates rise 50bps?")
    elif snap:
        # Portfolio question without a scenario: offer one + position detail.
        out.append("What happens to my debt if rates rise 50bps?")
        out.append(_maturity_suggestion(snap))
    else:
        # Not a portfolio question: if the user has a book, steer toward it;
        # otherwise fall back to market questions.
        if user is not None and db is not None:
            try:
                snap2 = build_portfolio_snapshot(user, db)
            except Exception:
                snap2 = None
            if snap2:
                out.append("What happens to my debt if rates rise 50bps?")
                out.append("Summarize my portfolio")
            else:
                out.extend(MARKET_SUGGESTIONS[:2])
        else:
            out.extend(MARKET_SUGGESTIONS[:2])

    # Market flavor rotates in when there's room.
    for m in MARKET_SUGGESTIONS:
        if len(out) >= MAX_SUGGESTIONS:
            break
        if m.lower() not in {o.lower() for o in out} and m.lower() not in (question or "").lower():
            out.append(m)

    # Never suggest the question just answered.
    q_norm = (question or "").strip().lower()
    out = [o for o in out if o.strip().lower() != q_norm]
    return out[:MAX_SUGGESTIONS]
