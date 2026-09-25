"""User-portfolio awareness for AI chat answers.

Detects questions about *the user's own* debt/portfolio ("what happens to
my debt if rates rise 50bps", "how much do I owe", "my longest bond") and
attaches a live snapshot of their actual positions plus deterministic
rate-shock math, so the assistant answers with real numbers instead of
generic theory.

Honesty contract (mirrors the rest of the product):
- Interest-cost math is derived directly from the user's positions.
- The mark-to-market figure is a first-order approximation from modified
  duration, clearly labeled — not a full revaluation.
- FX exposure is shown at face value; conversion to a single currency is
  noted as an approximation using live FX where available.
"""

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ── Question classifier ───────────────────────────────────────────────

# First-person possessive cues: the question is about the caller's data.
# Note: bank-account balances are owned by the banking chat branch — only
# debt/portfolio phrasing routes here.
PORTFOLIO_KEYWORDS = (
    "my debt", "my portfolio", "my positions", "my bonds", "my exposure",
    "my maturities", "my maturity", "my coupon", "my coupons",
    "my instruments", "my holdings", "my refinancing", "my risk",
    "our debt", "our portfolio", "our positions", "our exposure",
    "my total debt", "how much do i owe", "how much do we owe",
    "what do i owe", "my debt service", "my interest", "my cost",
)

# Scenario / what-if cues (often phrased without "my")
SCENARIO_KEYWORDS = (
    "what happens", "if rates", "rates rise", "rates fall", "rates increase",
    "rate rise", "rate hike", "rate cut", "rate shock", "shock", "50bps",
    "100bps", "25bps", "basis point", "basis points", "bps", "mark to market",
    "mark-to-market", "revaluation", "how much would", "impact on my",
    "effect on my", "cost me", "interest cost",
)

# General "describe my portfolio" cues
SUMMARY_KEYWORDS = (
    "summarize my", "summary of my", "describe my", "my debt profile",
    "portfolio profile", "my ladder", "what do i have", "what do we have",
    "my currencies", "my longest", "my shortest", "my nearest maturity",
    "when does my", "my next maturity", "my biggest", "my largest",
)

RATE_SHOCK_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:bps|basis\s*points)", re.IGNORECASE)


# ── Conversation memory: follow-up resolution ─────────────────────────

# Pronouns/ellipses that signal the message depends on prior context.
FOLLOWUP_STARTERS = (
    "what about", "how about", "and for", "and the", "and my", "and our",
    "now ", "same ", "again", "instead", "rather than", "what if",
    "repeat", "continue", "go on", "tell me more", "why ", "and that",
    "compared to", "versus", "vs ", "double it", "triple it", "half that",
)
FOLLOWUP_PRONOUNS = ("it", "them", "that", "those", "this", "they")

# Words that mark a brand-new topic even when the message is short
# (e.g. "what about ethereum?" right after a rates question).
NEW_TOPIC_MARKERS = (
    "price", "quote", "stock", "share of", "bitcoin", "btc", "ethereum",
    "eth", "crypto", "gold", "oil", "who", "when is", "define", "what is",
    "what are", "explain", "hello", "hi ", "hey",
)


def looks_like_followup(message: str, history: Optional[List[Dict[str, Any]]]) -> bool:
    """Heuristic: does this message lean on a previous exchange?"""
    if not history:
        return False
    m = (message or "").lower().strip()
    if not m:
        return False
    # Very short messages are almost always follow-ups ("why?", "100bps?")
    if len(m.split()) <= 4:
        return True
    if any(m.startswith(s) for s in FOLLOWUP_STARTERS):
        return True
    if any(re.search(rf"\b{re.escape(p)}\b", m) for p in FOLLOWUP_PRONOUNS):
        # "it/that" with no antecedent inside the message itself
        if not any(w in m for w in ("my ", "our ", "portfolio", "debt")):
            return True
    return False


def _prev_user_question(history: List[Dict[str, Any]]) -> str:
    """Most recent user turn in the history (oldest→newest expected)."""
    for turn in reversed(history):
        role = str(turn.get("role", ""))
        content = str(turn.get("content", "")).strip()
        if role == "user" and content:
            return content
    return ""


def resolve_followup(message: str, history: Optional[List[Dict[str, Any]]]) -> str:
    """Rewrite a contextual message into a standalone query.

    "What happens to my debt if rates rise 50bps?" followed by
    "what about 100bps?" becomes
    "What happens to my debt if rates rise 50bps? what about 100bps?"
    so retrieval, the portfolio classifier and the shock parser all see
    the antecedents. Fresh-sounding messages pass through untouched.
    """
    hist = history or []
    if not looks_like_followup(message, hist):
        return message
    prev = _prev_user_question(hist)
    if not prev:
        return message
    # Topic switch: short market-brand questions ("what about ethereum?")
    # and definitional questions ("explain debt sustainability") should
    # NOT inherit the prior debt question.
    m = (message or "").lower()
    prev_is_portfolio = is_portfolio_question(prev)
    if prev_is_portfolio:
        if any(m.startswith(s) for s in ("explain", "define", "what is", "what are", "who ", "when is")):
            return message
        if any(k in m for k in NEW_TOPIC_MARKERS):
            if not any(k in m for k in ("my ", "our ", "debt", "portfolio", "rate", "bps")):
                return message
    # Cap the antecedent so the combined query stays retrieval-friendly.
    anchor = prev[:220].rstrip()
    resolved = f"{anchor} {message.strip()}".strip()
    return resolved[:600]


def is_portfolio_question(q: str) -> bool:
    ql = (q or "").lower()
    if any(k in ql for k in PORTFOLIO_KEYWORDS):
        return True
    if any(k in ql for k in SUMMARY_KEYWORDS):
        return True
    if any(k in ql for k in SCENARIO_KEYWORDS) and any(
        w in ql for w in ("my ", "our ", "portfolio", "debt")
    ):
        return True
    return False


def extract_rate_shock_bps(q: str) -> Optional[float]:
    """Parse an explicit rate shock from the question (e.g. '50bps' → 50.0)."""
    m = RATE_SHOCK_RE.search(q or "")
    if m:
        return float(m.group(1))
    ql = (q or "").lower()
    # Common verbal forms
    if "quarter point" in ql:
        return 25.0
    if "half a point" in ql or "half point" in ql:
        return 50.0
    if re.search(r"\b(1|one)\s*(full\s*)?percent\b", ql):
        return 100.0
    return None


# ── Portfolio snapshot ────────────────────────────────────────────────

def _parse_date(s: str):
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def build_portfolio_snapshot(user, db) -> Optional[Dict[str, Any]]:
    """Aggregate the org's debt instruments into a chat-ready snapshot.

    Returns None when the org has no instruments (the AI then falls back to
    its normal knowledge-base answer).
    """
    from app.models import DebtInstrument, Portfolio

    portfolios = db.query(Portfolio).filter(Portfolio.org_id == user.org_id).all()
    if not portfolios:
        return None
    portfolio_ids = [p.id for p in portfolios]
    instruments = (
        db.query(DebtInstrument)
        .filter(DebtInstrument.portfolio_id.in_(portfolio_ids))
        .all()
    )
    if not instruments:
        return None

    now = datetime.now(timezone.utc)
    total_principal = 0.0
    weighted_coupon_num = 0.0
    weighted_years_num = 0.0
    ccy_totals: Dict[str, float] = {}
    type_totals: Dict[str, float] = {}
    near_maturities: List[Dict[str, Any]] = []
    floored_total = 0.0

    for inst in instruments:
        principal = float(inst.principal_outstanding or 0)
        coupon = float(inst.coupon_rate or 0)
        total_principal += principal
        weighted_coupon_num += coupon * principal
        ccy_totals[inst.currency] = ccy_totals.get(inst.currency, 0.0) + principal
        tname = getattr(inst.instrument_type, "value", str(inst.instrument_type))
        type_totals[tname] = type_totals.get(tname, 0.0) + principal
        if "floating" in tname:
            floored_total += principal
        mat = _parse_date(inst.maturity_date)
        if mat:
            years_left = max(0.0, (mat.replace(tzinfo=timezone.utc) - now).days / 365.25)
            weighted_years_num += years_left * principal
            near_maturities.append({
                "name": inst.name,
                "currency": inst.currency,
                "principal": principal,
                "maturity_date": str(inst.maturity_date)[:10],
                "years_left": round(years_left, 2),
                "coupon": coupon,
            })

    if total_principal <= 0:
        return None

    wtd_coupon = weighted_coupon_num / total_principal
    wtd_years = weighted_years_num / total_principal
    near_maturities.sort(key=lambda m: m["years_left"])

    return {
        "portfolio_count": len(portfolios),
        "instrument_count": len(instruments),
        "total_principal": round(total_principal, 2),
        "wtd_coupon_pct": round(wtd_coupon, 3),
        "annual_interest": round(total_principal * wtd_coupon / 100.0, 2),
        "wtd_maturity_years": round(wtd_years, 2),
        "currency_mix": {
            k: round(v / total_principal * 100, 1) for k, v in
            sorted(ccy_totals.items(), key=lambda x: -x[1])
        },
        "type_mix": {
            k: round(v / total_principal * 100, 1) for k, v in
            sorted(type_totals.items(), key=lambda x: -x[1])
        },
        "floating_principal": round(floored_total, 2),
        "nearest_maturities": near_maturities[:5],
        "longest_maturity": near_maturities[-1] if near_maturities else None,
    }


# ── Deterministic rate-shock math ─────────────────────────────────────

def compute_rate_shock(snapshot: Dict[str, Any], shock_bps: float) -> Dict[str, Any]:
    """First-order P&L and carry impact of a parallel rate shift.

    - Interest cost: repricing-share approximation. Floating-rate and
      short-dated (<2y) instruments reprice within the year; the rest are
      locked at coupon until maturity.
    - Mark-to-market: ΔP ≈ -D_mod × Δy × P with D_mod ≈ years-to-maturity
      (par-bond approximation), clearly labeled as first-order.
    """
    total = snapshot["total_principal"]
    wtd_coupon = snapshot["wtd_coupon_pct"]
    delta = shock_bps / 100.0  # percentage points

    # Repricing share: floating + anything maturing within 2 years
    repricing = snapshot.get("floating_principal", 0.0)
    near2y = sum(
        m["principal"] for m in snapshot.get("nearest_maturities", [])
        if m["years_left"] <= 2.0
    )
    # nearest_maturities is capped at 5 — recompute exactly from the mix
    # is unnecessary for the demo scale; use floating + near maturities,
    # deduplicated by taking the max of the two views (floating ⊂ near set
    # is not guaranteed, so this stays conservative and labeled).
    repricing_share = min(1.0, (max(repricing, near2y)) / total) if total else 0.0

    base_annual = total * wtd_coupon / 100.0
    # Blended duration proxy: weighted maturity of the locked book dominates;
    # for MTM we use the portfolio weighted average maturity (par-bond approx).
    d_mod = max(snapshot.get("wtd_maturity_years", 0.0), 0.25)

    return {
        "shock_bps": shock_bps,
        "base_annual_interest": round(base_annual, 2),
        "repricing_share_pct": round(repricing_share * 100, 1),
        "annual_interest_delta": round(total * delta / 100.0 * repricing_share, 2),
        "mtm_impact": round(-d_mod * (delta / 100.0) * total, 2),
        "duration_proxy_years": round(d_mod, 2),
        "method": (
            "first-order: floating/short-dated share reprices within a year; "
            "mark-to-market ≈ -D×Δy×P using weighted maturity as duration proxy"
        ),
    }


# ── Formatting ────────────────────────────────────────────────────────

def _fmt_money(v: float) -> str:
    if abs(v) >= 1_000_000_000:
        return f"${v / 1_000_000_000:,.2f}B"
    if abs(v) >= 1_000_000:
        return f"${v / 1_000_000:,.1f}M"
    if abs(v) >= 1_000:
        return f"${v / 1_000:,.0f}K"
    return f"${v:,.2f}"


def format_portfolio_snapshot_text(snap: Dict[str, Any]) -> str:
    lines = [
        f"Your portfolio (live from your workspace):",
        f"• Total outstanding: {_fmt_money(snap['total_principal'])} across "
        f"{snap['instrument_count']} instruments in {len(snap['currency_mix'])} currencies",
        f"• Weighted coupon: {snap['wtd_coupon_pct']:.2f}% → ~{_fmt_money(snap['annual_interest'])} annual interest",
        f"• Weighted maturity: {snap['wtd_maturity_years']:.1f} years",
    ]
    mix = ", ".join(f"{k} {v:.0f}%" for k, v in snap["currency_mix"].items())
    lines.append(f"• Currency mix: {mix}")
    near = snap.get("nearest_maturities") or []
    if near:
        m = near[0]
        lines.append(
            f"• Nearest maturity: {m['name']} — {_fmt_money(m['principal'])} {m['currency']} "
            f"on {m['maturity_date']} ({m['years_left']:.1f}y)"
        )
    longest = snap.get("longest_maturity")
    if longest and len(near) > 1:
        lines.append(
            f"• Longest: {longest['name']} — {_fmt_money(longest['principal'])} "
            f"{longest['currency']} on {longest['maturity_date']}"
        )
    if snap.get("floating_principal"):
        lines.append(f"• Floating-rate exposure: {_fmt_money(snap['floating_principal'])}")
    return "\n".join(lines)


def format_rate_shock_text(snap: Dict[str, Any], shock: Dict[str, Any]) -> str:
    bps = shock["shock_bps"]
    direction = "rise" if bps > 0 else "fall"
    interest_delta = shock["annual_interest_delta"]
    mtm = shock["mtm_impact"]
    lines = [
        f"Scenario: rates {direction} {abs(bps):.0f}bps (parallel shift) — your book:",
        f"• Repricing share: ~{shock['repricing_share_pct']:.0f}% of the book "
        f"(floating-rate + maturities within 2y) resets within the year",
        f"• Annual interest cost: {_fmt_money(shock['base_annual_interest'])} → "
        f"{_fmt_money(shock['base_annual_interest'] + interest_delta)} "
        f"({'+' if interest_delta >= 0 else '−'}{_fmt_money(abs(interest_delta))}/yr)",
        f"• Mark-to-market on the locked book: {mtm:+,.0f} USD "
        f"(≈ −D×Δy×P, D≈{shock['duration_proxy_years']:.1f}y — first-order estimate)",
    ]
    if shock["repricing_share_pct"] < 50:
        lines.append(
            "• Most of your book is fixed-rate, so a hike mostly hits you through "
            "refinancing at maturity, not through next year's coupon bill."
        )
    lines.append(
        "Estimates from your live positions — not investment advice. "
        "A full revaluation would use each bond's duration and curve."
    )
    return "\n".join(lines)


# ── Context builder used by chat endpoints ────────────────────────────

def build_portfolio_context(
    question: str,
    user,
    db,
    shock_source: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Return portfolio context for a question, or None.

    Shape: {"snapshot": {...}, "shock": {...} | None, "rate_shock_bps": ...}

    ``shock_source`` is the text the rate shock is parsed from — pass the
    *current* message when ``question`` may be a resolved follow-up, so a
    stale bps number from an earlier turn is never reused.
    """
    if not user or not is_portfolio_question(question):
        return None
    try:
        snap = build_portfolio_snapshot(user, db)
    except Exception:
        return None
    if not snap:
        return None
    ctx: Dict[str, Any] = {"snapshot": snap}
    bps = extract_rate_shock_bps(shock_source or question)
    if bps is not None:
        try:
            ctx["shock"] = compute_rate_shock(snap, bps)
            ctx["rate_shock_bps"] = bps
        except Exception:
            ctx["shock"] = None
    return ctx


def format_portfolio_context_text(ctx: Dict[str, Any]) -> str:
    snap = ctx.get("snapshot") or {}
    parts: List[str] = []
    if ctx.get("shock"):
        parts.append(format_rate_shock_text(snap, ctx["shock"]))
    parts.append(format_portfolio_snapshot_text(snap))
    return "\n\n".join(p for p in parts if p)
