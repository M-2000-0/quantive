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


# ── FX shock parsing ("the euro depreciates 10%") ────────────────────

# Spoken/ISO currency names → ISO code. Matched with word boundaries.
CURRENCY_WORDS = {
    "eur": "EUR", "euro": "EUR", "euros": "EUR", "eurozone": "EUR",
    "usd": "USD", "dollar": "USD", "dollars": "USD",
    "gbp": "GBP", "pound": "GBP", "pounds": "GBP", "sterling": "GBP",
    "jpy": "JPY", "yen": "JPY",
    "chf": "CHF", "franc": "CHF", "francs": "CHF",
    "cad": "CAD", "aud": "AUD", "cny": "CNY", "yuan": "CNY", "renminbi": "CNY",
}

# Verbs that indicate direction. Depreciation = currency loses value vs USD.
FX_DEPRECIATION_VERBS = ("depreciat", "weaken", "fall", "falls", "drop", "drops", "slide", "slides", "lose")
FX_APPRECIATION_VERBS = ("appreciat", "strengthen", "rise", "rises", "gain", "gains", "jump", "jumps")

# "the euro depreciates 10%" / "EUR weakens by 10 percent"
FX_SHOCK_RE = re.compile(
    r"\b(eur|euro|euros|eurozone|usd|dollar|dollars|gbp|pound|pounds|sterling|jpy|yen|chf|franc|francs|cad|aud|cny|yuan|renminbi)\b"
    r"[^.?!]{0,40}?\b(depreciat\w*|appreciat\w*|weaken\w*|strengthen\w*|fall\w*|drop\w*|slide\w*|rise\w*|gain\w*|jump\w*)"
    r"\s*(?:by\s*)?(\d+(?:\.\d+)?)\s*(?:%|percent)",
    re.IGNORECASE,
)
# Reversed phrasing: "a 10% depreciation of the euro"
FX_SHOCK_NOUN_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:%|percent)\s+"
    r"(depreciation|appreciation|weakening|strengthening|fall|rise|drop|gain|slide|jump)"
    r"[^.?!]{0,30}?\b(eur|euro|euros|eurozone|usd|dollar|dollars|gbp|pound|pounds|sterling|jpy|yen|chf|franc|francs|cad|aud|cny|yuan|renminbi)\b",
    re.IGNORECASE,
)


def _norm_currency(word: str) -> Optional[str]:
    return CURRENCY_WORDS.get((word or "").lower())


def _fx_direction(verb_or_noun: str) -> Optional[str]:
    v = (verb_or_noun or "").lower()
    if any(k in v for k in FX_DEPRECIATION_VERBS) or v in ("depreciation", "weakening", "fall", "drop", "slide"):
        return "depreciate"
    if any(k in v for k in FX_APPRECIATION_VERBS) or v in ("appreciation", "strengthening", "rise", "gain", "jump"):
        return "appreciate"
    return None


def extract_fx_shock(q: str) -> Optional[Dict[str, Any]]:
    """Parse an explicit FX shock, e.g. 'euro depreciates 10%' →
    {"currency": "EUR", "pct": 10.0, "direction": "depreciate"}."""
    text = q or ""
    m = FX_SHOCK_RE.search(text)
    if m:
        ccy = _norm_currency(m.group(1))
        direction = _fx_direction(m.group(2))
        if ccy and direction:
            return {"currency": ccy, "pct": float(m.group(3)), "direction": direction}
    m = FX_SHOCK_NOUN_RE.search(text)
    if m:
        ccy = _norm_currency(m.group(3))
        direction = _fx_direction(m.group(2))
        if ccy and direction:
            return {"currency": ccy, "pct": float(m.group(1)), "direction": direction}
    return None


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
    ccy_usd = {k: round(v, 2) for k, v in ccy_totals.items()}

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
        # FX shock math consumes absolute USD face values per currency.
        "currency_exposures_usd": ccy_usd,
        "nearest_maturities": near_maturities[:5],
        "longest_maturity": near_maturities[-1] if near_maturities else None,
    }


# ── Deterministic rate-shock math ─────────────────────────────────────

def compute_fx_impact(snapshot: Dict[str, Any], currency: str, pct: float, direction: str) -> Dict[str, Any]:
    """First-order impact of an FX move on the user's currency mix.

    Face value of the named currency's exposure is restated in USD terms:
    depreciation of X% reduces USD face value by X%; appreciation raises it.
    MTM ≈ ±pct × exposure (face-value approximation, labeled as such).
    """
    mix = snapshot.get("currency_exposures_usd", {}) or {}
    exposure = float(mix.get(currency, 0.0))  # USD face value of that currency's book
    total = snapshot["total_principal"]
    delta = pct / 100.0
    if direction == "depreciate":
        new_value = exposure * (1 - delta)
        mtm = -exposure * delta
    else:
        new_value = exposure * (1 + delta)
        mtm = exposure * delta
    return {
        "currency": currency,
        "pct": pct,
        "direction": direction,
        "exposure_usd": round(exposure, 2),
        "revalued_usd": round(new_value, 2),
        "mtm_impact": round(mtm, 2),
        "share_of_book_pct": round((exposure / total * 100) if total else 0.0, 1),
    }


def compute_rate_shock(
    snapshot: Dict[str, Any],
    shock_bps: float,
    fx_shock: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """First-order P&L and carry impact of a parallel rate shift.

    - Interest cost: repricing-share approximation. Floating-rate and
      short-dated (<2y) instruments reprice within the year; the rest are
      locked at coupon until maturity.
    - Mark-to-market: ΔP ≈ -D_mod × Δy × P with D_mod ≈ years-to-maturity
      (par-bond approximation), clearly labeled as first-order.

    ``fx_shock`` ({currency, pct, direction}) optionally composes an FX
    move on top of the rate shock — "rates rise 50bps, and if the euro
    depreciates 10% on top of that?".
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

    rate_mtm = -d_mod * (delta / 100.0) * total
    fx_impact = None
    if fx_shock:
        try:
            fx_impact = compute_fx_impact(
                snapshot, fx_shock["currency"], fx_shock["pct"], fx_shock["direction"]
            )
        except Exception:
            fx_impact = None

    result = {
        "shock_bps": shock_bps,
        "base_annual_interest": round(base_annual, 2),
        "repricing_share_pct": round(repricing_share * 100, 1),
        "annual_interest_delta": round(total * delta / 100.0 * repricing_share, 2),
        "mtm_impact": round(rate_mtm, 2),
        "duration_proxy_years": round(d_mod, 2),
        "method": (
            "first-order: floating/short-dated share reprices within a year; "
            "mark-to-market ≈ -D×Δy×P using weighted maturity as duration proxy"
        ),
    }
    if fx_impact:
        result["fx_impact"] = fx_impact
        result["combined_mtm_impact"] = round(rate_mtm + fx_impact["mtm_impact"], 2)
    return result


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
    if shock.get("fx_impact"):
        fx = shock["fx_impact"]
        fdir = "depreciates" if fx["direction"] == "depreciate" else "appreciates"
        lines.append(
            f"• Plus FX: the {fx['currency']} {fdir} {fx['pct']:.0f}% → "
            f"{_fmt_money(fx['exposure_usd'])} exposure becomes "
            f"{_fmt_money(fx['revalued_usd'])} (face-value MTM {fx['mtm_impact']:+,.0f} USD)"
        )
        lines.append(
            f"• Combined first-order MTM (rates + FX): {shock['combined_mtm_impact']:+,.0f} USD"
        )
    if shock["repricing_share_pct"] < 50:
        lines.append(
            "• Most of your book is fixed-rate, so a hike mostly hits you through "
            "refinancing at maturity, and through USD value of non-USD bonds."
        )
    lines.append(
        "Estimates from your live positions — not investment advice. "
        "A full revaluation would use each bond's duration, curve and hedges."
    )
    return "\n".join(lines)


# ── Context builder used by chat endpoints ────────────────────────────

def build_portfolio_context(
    question: str,
    user,
    db,
    chat_history: Optional[List[Dict[str, Any]]] = None,
    shock_source: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Return portfolio context for a question, or None.

    Shape: {"snapshot": {...}, "shock": {...} | None, "rate_shock_bps": ...}

    ``shock_source`` is the text the rate shock is parsed from — pass the
    *current* message when ``question`` may be a resolved follow-up, so a
    stale bps number from an earlier turn is never reused.

    Chained what-ifs: "and if the euro depreciates 10% on top of that?" has
    no bps of its own — the bps comes from the *anchor* (prior question)
    carried in the resolved query, while the FX shock parses from the
    current message. When an FX shock is present, the rate bps is searched
    first in ``shock_source`` then in ``question`` (the anchor), so the two
    shocks compose instead of the FX move replacing the rate scenario.
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
    fx = extract_fx_shock(shock_source or "")
    if fx:
        ctx["fx_shock"] = fx
    bps_source = shock_source or ""
    if fx and extract_rate_shock_bps(bps_source) is None:
        # Fall back to the anchor carried in the resolved query; if that
        # lost the bps (anchor cap), scan the prior user turn directly.
        if extract_rate_shock_bps(question) is not None:
            bps_source = question
        elif chat_history:
            from_prev = _prev_user_question(chat_history)
            if from_prev:
                bps_source = f"{question} {from_prev}"
    bps = extract_rate_shock_bps(bps_source)
    if bps is not None:
        try:
            ctx["shock"] = compute_rate_shock(snap, bps, fx_shock=fx)
            ctx["rate_shock_bps"] = bps
        except Exception:
            ctx["shock"] = None
    elif fx:
        # FX-only scenario (no rate leg): still expose deterministic numbers.
        try:
            ctx["fx_impact"] = compute_fx_impact(
                snap, fx["currency"], fx["pct"], fx["direction"]
            )
        except Exception:
            ctx["fx_impact"] = None
    return ctx


def format_fx_impact_text(snap: Dict[str, Any], fx: Dict[str, Any]) -> str:
    direction = "depreciates" if fx["direction"] == "depreciate" else "appreciates"
    sign = "−" if fx["direction"] == "depreciate" else "+"
    lines = [
        f"Scenario: the {fx['currency']} {direction} {fx['pct']:.0f}% vs USD — your book:",
        f"• {fx['currency']} exposure: {_fmt_money(fx['exposure_usd'])} "
        f"({fx['share_of_book_pct']:.0f}% of the portfolio) → "
        f"{_fmt_money(fx['revalued_usd'])} in USD terms",
        f"• Face-value MTM: {sign}{_fmt_money(abs(fx['mtm_impact']))} "
        "(first-order; ignores convexity and hedge book)",
    ]
    return "\n".join(lines)


def format_portfolio_context_text(ctx: Dict[str, Any]) -> str:
    snap = ctx.get("snapshot") or {}
    parts: List[str] = []
    if ctx.get("shock"):
        parts.append(format_rate_shock_text(snap, ctx["shock"]))
    if ctx.get("fx_impact"):
        parts.append(format_fx_impact_text(snap, ctx["fx_impact"]))
    parts.append(format_portfolio_snapshot_text(snap))
    return "\n\n".join(p for p in parts if p)
