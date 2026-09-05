"""Finance-tuned headline sentiment analysis.

Lexicon-based scorer designed for financial news headlines and summaries.
No external dependencies — deterministic, fast, and auditable.

Score range: -1.0 (very negative) to +1.0 (very positive).

Handles:
- Finance-specific vocabulary (upgrades/downgrades, beats/misses, guidance)
- Negation ("not profitable", "fails to beat")
- Intensity modifiers ("sharply higher", "slightly beats")
- Bear/bull idioms common in market headlines
"""
import re

# ── Lexicon ─────────────────────────────────────────────────────────
# term -> (base_score, part)  part: 'verb'|'noun'|'adj' (informational only)

POSITIVE_TERMS = {
    "surge": 2.0, "surges": 2.0, "surged": 2.0, "soar": 2.5, "soars": 2.5,
    "soared": 2.5, "jump": 1.5, "jumps": 1.5, "jumped": 1.5, "rally": 2.0,
    "rallies": 2.0, "rallied": 2.0, "climb": 1.0, "climbs": 1.0, "climbed": 1.0,
    "gain": 1.0, "gains": 1.0, "gained": 1.0, "rise": 1.0, "rises": 1.0,
    "rose": 1.0, "rising": 1.0, "advance": 1.0, "advances": 1.0, "beat": 1.5,
    "beats": 1.5, "outperform": 1.5, "outperforms": 1.5, "upgrade": 1.5,
    "upgrades": 1.5, "upgraded": 1.5, "bullish": 2.0, "record": 1.0,
    "record-high": 2.0, "profit": 1.0, "profits": 1.0, "profitable": 1.0,
    "growth": 1.0, "strong": 1.0, "stronger": 1.2, "boost": 1.2, "boosts": 1.2,
    "boosted": 1.2, "win": 1.0, "wins": 1.0, "breakthrough": 1.5,
    "expansion": 1.0, "expands": 1.0, "dividend": 0.8, "buyback": 1.0,
    "partnership": 0.8, "approval": 1.2, "approved": 1.2, "breakout": 1.5,
    "optimism": 1.5, "optimistic": 1.5, "recovery": 1.2, "rebound": 1.2,
    "rebounds": 1.2, "rebounding": 1.2, "momentum": 0.8, "tops": 1.0,
    "exceeds": 1.2, "exceeded": 1.2, "robust": 1.0, "upside": 1.2,
    "raises": 0.8, "raised": 0.8, "hike": 0.5,  # rate hike is positive for banks; context-dependent
    "accelerates": 1.0, "accelerating": 1.0, "buy": 0.8, "accumulate": 0.8,
    "upgraded-to-buy": 1.8, "best": 1.0, "all-time-high": 2.0, "highs": 0.8,
}

NEGATIVE_TERMS = {
    "plunge": 2.5, "plunges": 2.5, "plunged": 2.5, "slump": 2.0, "slumps": 2.0,
    "slumped": 2.0, "crash": 2.5, "crashes": 2.5, "crashed": 2.5, "tumble": 1.8,
    "tumbles": 1.8, "tumbled": 1.8, "fall": 1.0, "falls": 1.0, "fell": 1.0,
    "falling": 1.0, "drop": 1.2, "drops": 1.2, "dropped": 1.2, "decline": 1.2,
    "declines": 1.2, "declined": 1.2, "miss": 1.5, "misses": 1.5, "missed": 1.5,
    "downgrade": 1.8, "downgrades": 1.8, "downgraded": 1.8, "bearish": 2.0,
    "loss": 1.5, "losses": 1.5, "weak": 1.2, "weaker": 1.4, "weakness": 1.2,
    "cut": 1.0, "cuts": 1.0, "layoff": 1.5, "layoffs": 1.5, "bankruptcy": 2.5,
    "bankrupt": 2.5, "fraud": 2.5, "probe": 1.2, "investigation": 1.5,
    "lawsuit": 1.5, "sued": 1.5, "recall": 1.5, "warning": 1.5, "warns": 1.5,
    "warned": 1.5, "shortfall": 1.5, "slowing": 1.2, "slowdown": 1.5,
    "recession": 2.0, "crisis": 2.0, "default": 2.0, "downside": 1.2,
    "selloff": 2.0, "sell-off": 2.0, "sell-off-continues": 2.2, "sinks": 1.8,
    "sank": 1.8, "slide": 1.5, "slides": 1.5, "slid": 1.5, "underperform": 1.5,
    "underperforms": 1.5, "overvalued": 1.5, "bubble": 1.8, "concerns": 1.0,
    "concern": 1.0, "risk": 0.8, "risks": 0.8, "fears": 1.5, "fear": 1.5,
    "downturn": 1.8, "headwinds": 1.2, "headwind": 1.2, "pressure": 0.8,
    "pressures": 0.8, "worse": 1.2, "worst": 1.5, "disappointing": 1.5,
    "disappoints": 1.5, "disappointed": 1.5, "halt": 1.2, "halts": 1.2,
    "suspension": 1.2, "delisting": 2.0, "dilution": 1.2, "dilutes": 1.2,
    "guidance-cut": 1.8, "lowers": 1.0, "lowered": 1.0, "sell": 0.8,
    "underweight": 1.2, "cuts-outlook": 1.8,
}

INTENSIFIERS = {
    "sharply": 1.5, "significantly": 1.4, "massively": 1.6, "heavily": 1.4,
    "dramatically": 1.6, "strongly": 1.4, "slightly": 0.6, "marginally": 0.5,
    "modestly": 0.7, "somewhat": 0.7, "briefly": 0.8, "shares": 1.0,
    "stock": 1.0, "deeply": 1.5, "badly": 1.4, "highly": 1.3,
}

NEGATORS = {"not", "no", "never", "fails", "fail", "failed", "without",
            "denies", "denied", "halts", "refuses", "avoids", "missing",
            "lacks", "lack", "unable"}

# Multi-word patterns that override token scoring (checked first)
PHRASES = {
    "beats expectations": 2.0, "misses expectations": -2.0,
    "beats estimates": 1.8, "misses estimates": -1.8,
    "all-time high": 2.0, "record high": 1.8, "record low": -1.8,
    "guidance raise": 1.5, "raises guidance": 1.6, "raised guidance": 1.6,
    "cuts guidance": -1.8, "guidance cut": -1.8, "lowers guidance": -1.6,
    "beats on": 1.5, "misses on": -1.5,
    "rate cut": 1.0, "rate hike": -0.5,  # equities: cuts cheer, hikes pressure
    "buy rating": 1.5, "sell rating": -1.5, "hold rating": 0.0,
    "price target raised": 1.5, "price target cut": -1.5,
    "short squeeze": 1.8, "insider buying": 1.2, "insider selling": -1.2,
    "going concern": -2.2, "chapter 11": -2.5,
}

_TOKEN_RE = re.compile(r"[a-z][a-z\-']+")

_WORD_BOUNDARY = True  # match terms as whole words


def _match_term(text_lower: str, term: str) -> bool:
    """Whole-word match for a term (handles hyphens)."""
    pattern = r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])"
    return re.search(pattern, text_lower) is not None


def analyze_sentiment(text: str) -> dict:
    """Score a headline/summary. Returns score, label, and matched evidence.

    Returns:
        {
          "score": float (-1.0..1.0),
          "label": "positive" | "negative" | "neutral",
          "positive_matches": [...],
          "negative_matches": [...],
        }
    """
    if not text:
        return {"score": 0.0, "label": "neutral", "positive_matches": [], "negative_matches": []}

    lower = text.lower()
    tokens = _TOKEN_RE.findall(lower)

    # Phrase matches first (strongest signal, counted once each)
    pos_score = 0.0
    neg_score = 0.0
    pos_hits = []
    neg_hits = []

    for phrase, val in PHRASES.items():
        if _match_term(lower, phrase):
            if val > 0:
                pos_score += val
                pos_hits.append(phrase)
            else:
                neg_score += abs(val)
                neg_hits.append(phrase)

    # Token-level scan with negation and intensifier handling
    for i, tok in enumerate(tokens):
        base = None
        polarity = 0
        if tok in POSITIVE_TERMS:
            base = POSITIVE_TERMS[tok]
            polarity = 1
        elif tok in NEGATIVE_TERMS:
            base = NEGATIVE_TERMS[tok]
            polarity = -1
        if base is None:
            continue

        # Look back up to 3 tokens for negators/intensifiers
        window = tokens[max(0, i - 3):i]
        negated = any(n in window for n in NEGATORS)
        intensifier = 1.0
        for w in window:
            if w in INTENSIFIERS:
                intensifier = max(intensifier, INTENSIFIERS[w])

        # Apply polarity sign: negative terms contribute negatively
        val = base * intensifier
        if polarity == -1:
            val = -val

        if negated:
            if polarity == 1:
                # "fails to beat" → positive term flips negative
                val = -val * 0.8
            else:
                # "not plunging" → negative term flips mildly positive
                val = abs(val) * 0.5

        if val > 0:
            pos_score += val
            pos_hits.append(tok)
        elif val < 0:
            neg_score += abs(val)
            neg_hits.append(tok)

    # Normalize to -1..1 using a soft saturating function
    raw = pos_score - neg_score
    score = raw / (abs(raw) + 3.0)  # saturates: raw=3 → 0.5, raw=6 → 0.67, raw=12 → 0.8

    if score > 0.15:
        label = "positive"
    elif score < -0.15:
        label = "negative"
    else:
        label = "neutral"

    return {
        "score": round(score, 3),
        "label": label,
        "positive_matches": list(dict.fromkeys(pos_hits))[:6],
        "negative_matches": list(dict.fromkeys(neg_hits))[:6],
    }


def score_headline(title: str, summary: str = "") -> float:
    """Convenience: just the score, weighting the title more heavily."""
    t = analyze_sentiment(title or "")
    s = analyze_sentiment(summary or "") if summary else {"score": 0.0}
    # Title counts double — headlines carry the editorial stance
    combined = (t["score"] * 2.0 + s["score"]) / 3.0
    return round(max(-1.0, min(1.0, combined)), 3)


def aggregate_sentiment(scores: list[float]) -> dict:
    """Aggregate a list of article scores into a summary.

    Returns mean score, label, and coverage stats.
    """
    if not scores:
        return {"mean": None, "label": "no_coverage", "count": 0,
                "positive": 0, "negative": 0, "neutral": 0}

    n = len(scores)
    pos = sum(1 for s in scores if s > 0.15)
    neg = sum(1 for s in scores if s < -0.15)
    neu = n - pos - neg
    mean = sum(scores) / n

    if mean > 0.15:
        label = "positive"
    elif mean < -0.15:
        label = "negative"
    else:
        label = "mixed"

    return {
        "mean": round(mean, 3),
        "label": label,
        "count": n,
        "positive": pos,
        "negative": neg,
        "neutral": neu,
    }
