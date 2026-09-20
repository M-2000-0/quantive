"""AI-powered market summary generator — combines data sources into natural language."""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger("quantive.ai.market_summary")


def generate_market_summary(
    yield_curve: dict | None = None,
    fx_rates: list[dict] | None = None,
    interest_rates: list[dict] | None = None,
    news_digest: dict | None = None,
    portfolio_context: dict | None = None,
) -> dict:
    """Generate a structured market summary from available data.

    Returns a dict with:
    - headline: one-line market summary
    - sections: detailed breakdowns by category
    - signals: key market signals
    - outlook: short-term outlook assessment
    """
    sections = []
    signals = []

    # ── Yield Curve Analysis ─────────────────────────────────────
    if yield_curve and yield_curve.get("points"):
        points = yield_curve["points"]
        spread = yield_curve.get("two_ten_spread_bps")
        if spread is not None:
            if spread < 0:
                sections.append({
                    "title": "Yield Curve",
                    "content": f"The yield curve is inverted with a 2Y-10Y spread of {spread:.0f} bps, "
                               f"suggesting recession risk and expectations of rate cuts.",
                    "severity": "warning",
                })
                signals.append({"type": "yield_curve_inversion", "direction": "negative", "spread_bps": spread})
            elif spread < 50:
                sections.append({
                    "title": "Yield Curve",
                    "content": f"The yield curve is flat with a 2Y-10Y spread of {spread:.0f} bps, "
                               f"indicating uncertainty about economic trajectory.",
                    "severity": "neutral",
                })
                signals.append({"type": "yield_curve_flat", "direction": "neutral", "spread_bps": spread})
            else:
                sections.append({
                    "title": "Yield Curve",
                    "content": f"The yield curve is steepening with a 2Y-10Y spread of {spread:.0f} bps, "
                               f"suggesting economic expansion or rising inflation expectations.",
                    "severity": "positive",
                })
                signals.append({"type": "yield_curve_steep", "direction": "positive", "spread_bps": spread})

    # ── FX Rates ─────────────────────────────────────────────────
    if fx_rates:
        usd_strength = sum(1 for r in fx_rates if r.get("change_pct", 0) > 0)
        usd_weakness = sum(1 for r in fx_rates if r.get("change_pct", 0) < 0)
        if usd_strength > usd_weakness:
            sections.append({
                "title": "Currency Markets",
                "content": f"The US Dollar is strengthening against {usd_strength} of {len(fx_rates)} tracked pairs.",
                "severity": "positive",
            })
            signals.append({"type": "usd_strength", "direction": "positive"})
        elif usd_weakness > usd_strength:
            sections.append({
                "title": "Currency Markets",
                "content": f"The US Dollar is weakening against {usd_weakness} of {len(fx_rates)} tracked pairs.",
                "severity": "negative",
            })
            signals.append({"type": "usd_weakness", "direction": "negative"})

    # ── Interest Rates ───────────────────────────────────────────
    if interest_rates:
        rising = sum(1 for r in interest_rates if r.get("change_bps", 0) > 0)
        falling = sum(1 for r in interest_rates if r.get("change_bps", 0) < 0)
        if rising > falling:
            sections.append({
                "title": "Interest Rates",
                "content": f"Benchmark rates are trending upward ({rising} rising, {falling} falling), "
                           f"suggesting tighter monetary policy.",
                "severity": "warning",
            })
            signals.append({"type": "rates_rising", "direction": "negative"})
        elif falling > rising:
            sections.append({
                "title": "Interest Rates",
                "content": f"Benchmark rates are trending downward ({falling} falling, {rising} rising), "
                           f"suggesting easing monetary policy.",
                "severity": "positive",
            })
            signals.append({"type": "rates_falling", "direction": "positive"})

    # ── News Sentiment ───────────────────────────────────────────
    if news_digest and news_digest.get("total_articles", 0) > 0:
        top_tickers = news_digest.get("top_tickers", [])
        categories = news_digest.get("categories", {})
        news_items = []
        for cat_articles in categories.values():
            for a in cat_articles[:2]:
                news_items.append(a.get("title", ""))
        if news_items:
            sections.append({
                "title": "News Highlights",
                "content": f"Top stories: {'; '.join(news_items[:3])}",
                "severity": "info",
            })
        if top_tickers:
            tickers_str = ", ".join(f"${t['ticker']}" for t in top_tickers[:5])
            sections.append({
                "title": "Market Attention",
                "content": f"Most discussed assets: {tickers_str}",
                "severity": "info",
            })

    # ── Portfolio Context ────────────────────────────────────────
    if portfolio_context:
        total_value = portfolio_context.get("total_value", 0)
        risk_score = portfolio_context.get("risk_score")
        if risk_score is not None:
            if risk_score > 70:
                sections.append({
                    "title": "Portfolio Risk",
                    "content": f"Portfolio risk score is elevated at {risk_score:.0f}/100. "
                               f"Consider reviewing allocation and hedging strategies.",
                    "severity": "warning",
                })
                signals.append({"type": "high_risk", "direction": "negative"})
            elif risk_score < 30:
                sections.append({
                    "title": "Portfolio Risk",
                    "content": f"Portfolio risk score is low at {risk_score:.0f}/100. "
                               f"Conservative positioning with limited downside exposure.",
                    "severity": "positive",
                })

    # ── Build Headline ───────────────────────────────────────────
    positive_signals = sum(1 for s in signals if s.get("direction") == "positive")
    negative_signals = sum(1 for s in signals if s.get("direction") == "negative")

    if negative_signals > positive_signals:
        headline = "Markets showing caution — multiple risk indicators elevated."
        outlook = "cautious"
    elif positive_signals > negative_signals:
        headline = "Markets constructive — positive signals outweigh risk factors."
        outlook = "positive"
    else:
        headline = "Markets mixed — balanced signals across asset classes."
        outlook = "neutral"

    return {
        "headline": headline,
        "sections": sections,
        "signals": signals,
        "outlook": outlook,
        "summary_text": _build_narrative(headline, sections),
    }


def _build_narrative(headline: str, sections: list[dict]) -> str:
    """Build a natural language narrative from structured sections."""
    parts = [headline, ""]
    for section in sections:
        parts.append(f"{section['title']}: {section['content']}")
    return "\n".join(parts)


def generate_llm_market_summary(
    yield_curve: dict | None = None,
    fx_rates: list[dict] | None = None,
    interest_rates: list[dict] | None = None,
    news_digest: dict | None = None,
    provider: str = "template",
    model: str = "template",
) -> Optional[str]:
    """Generate a market summary using rule-based analysis.

    External LLM providers removed — all analysis uses our own engine.
    """
    structured = generate_market_summary(yield_curve, fx_rates, interest_rates, news_digest)
    return structured["summary_text"]
