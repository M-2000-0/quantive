"""AI-powered stock explanation generator — produces 'why this stock' narratives."""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger("quantive.ai.stock_explainer")


def explain_stock(
    symbol: str,
    price_data: dict | None = None,
    technical_signals: dict | None = None,
    sector_context: dict | None = None,
    news_context: list[dict] | None = None,
) -> dict:
    """Generate a comprehensive stock explanation.

    Returns structured explanation with:
    - headline: one-line summary
    - technical_analysis: signal breakdown
    - fundamental_context: sector/market context
    - risk_factors: key risks
    - confidence: explanation confidence score
    """
    factors = []
    risk_factors = []
    confidence = 0.5

    # ── Technical Signal Analysis ────────────────────────────────
    if technical_signals:
        rsi = technical_signals.get("rsi")
        macd = technical_signals.get("macd_signal")
        moving_avg = technical_signals.get("moving_avg_signal")
        bollinger = technical_signals.get("bollinger_signal")
        composite_score = technical_signals.get("composite_score", 0)

        if rsi is not None:
            if rsi < 30:
                factors.append(f"RSI at {rsi:.0f} indicates oversold conditions — potential buying opportunity.")
                confidence += 0.1
            elif rsi > 70:
                factors.append(f"RSI at {rsi:.0f} indicates overbought conditions — potential pullback risk.")
                risk_factors.append("Overbought RSI suggests limited near-term upside")
                confidence += 0.1
            else:
                factors.append(f"RSI at {rsi:.0f} is in neutral territory.")

        if macd:
            if macd == "bullish":
                factors.append("MACD shows bullish crossover — momentum shifting upward.")
                confidence += 0.1
            elif macd == "bearish":
                factors.append("MACD shows bearish crossover — momentum shifting downward.")
                risk_factors.append("Bearish MACD crossover")
                confidence += 0.1

        if moving_avg:
            if moving_avg == "bullish":
                factors.append("Price is above key moving averages — uptrend intact.")
                confidence += 0.05
            elif moving_avg == "bearish":
                factors.append("Price is below key moving averages — downtrend in effect.")
                risk_factors.append("Below key moving averages")
                confidence += 0.05

        if bollinger:
            if bollinger == "oversold":
                factors.append("Price near lower Bollinger Band — potential mean reversion opportunity.")
            elif bollinger == "overbought":
                factors.append("Price near upper Bollinger Band — potential for reversion to mean.")
                risk_factors.append("Near upper Bollinger Band")

        if composite_score:
            if composite_score > 50:
                factors.append(f"Composite signal score of {composite_score:.0f}/100 favors bullish positioning.")
            elif composite_score < -50:
                factors.append(f"Composite signal score of {composite_score:.0f}/100 favors bearish positioning.")
                risk_factors.append("Negative composite signal")
            else:
                factors.append(f"Composite signal score of {composite_score:.0f}/100 is neutral.")

    # ── Price Context ────────────────────────────────────────────
    if price_data:
        change_pct = price_data.get("change_pct", 0)
        if abs(change_pct) > 5:
            direction = "gained" if change_pct > 0 else "lost"
            factors.append(f"Stock has {direction} {abs(change_pct):.1f}% — significant move.")
            if change_pct < -5:
                risk_factors.append("Sharp recent decline")
        elif abs(change_pct) > 2:
            direction = "up" if change_pct > 0 else "down"
            factors.append(f"Stock is {direction} {abs(change_pct):.1f}% today.")

        market_cap = price_data.get("market_cap")
        if market_cap:
            if market_cap > 1e12:
                factors.append("Large-cap stock with high liquidity and institutional ownership.")
                confidence += 0.05
            elif market_cap > 1e9:
                factors.append("Mid-cap stock with moderate growth potential.")
            else:
                factors.append("Small-cap stock with higher volatility and growth potential.")
                risk_factors.append("Small-cap volatility")

    # ── Sector Context ───────────────────────────────────────────
    if sector_context:
        sector_momentum = sector_context.get("momentum")
        sector_pe = sector_context.get("sector_pe")
        if sector_momentum == "outperforming":
            factors.append("Sector is outperforming the broader market — tailwind for the stock.")
            confidence += 0.05
        elif sector_momentum == "underperforming":
            factors.append("Sector is underperforming the broader market — headwind for the stock.")
            risk_factors.append("Sector headwinds")
        if sector_pe:
            factors.append(f"Sector average P/E is {sector_pe:.1f}x — provides valuation context.")

    # ── News Context ─────────────────────────────────────────────
    if news_context:
        recent_news = [n for n in news_context[:3] if n.get("title")]
        if recent_news:
            headlines = "; ".join(n["title"][:80] for n in recent_news)
            factors.append(f"Recent news: {headlines}")

    # ── Build Narrative ──────────────────────────────────────────
    if not factors:
        factors.append("Limited data available for comprehensive analysis.")
        confidence = 0.3

    headline = _generate_headline(symbol, factors, technical_signals)
    methodology = _build_methodology(factors, technical_signals)

    return {
        "symbol": symbol,
        "headline": headline,
        "factors": factors,
        "risk_factors": risk_factors,
        "technical_analysis": technical_signals or {},
        "confidence": min(confidence, 1.0),
        "methodology": methodology,
        "data_sources": ["Technical indicators", "Price data", "Sector analysis"],
    }


def _generate_headline(symbol: str, factors: list[str], signals: dict | None) -> str:
    """Generate a one-line headline from the analysis."""
    if signals:
        score = signals.get("composite_score", 0)
        if score > 50:
            return f"{symbol}: Technical indicators suggest bullish momentum with {len(factors)} supporting factors."
        elif score < -50:
            return f"{symbol}: Technical indicators suggest bearish pressure with {len(factors)} risk factors identified."
    return f"{symbol}: Analysis reveals {len(factors)} key factors for investment consideration."


def _build_methodology(factors: list[str], signals: dict | None) -> str:
    """Build methodology description."""
    parts = ["Analysis based on:"]
    if signals:
        parts.append("- Technical indicators (RSI, MACD, Moving Averages, Bollinger Bands)")
    parts.append("- Price action and momentum analysis")
    parts.append("- Sector context and relative performance")
    return "\n".join(parts)
