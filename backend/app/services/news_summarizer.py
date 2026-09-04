"""AI-powered news summarizer — generates digests and article summaries."""
from __future__ import annotations

import logging
from collections import Counter
from typing import Optional

logger = logging.getLogger("quantive.ai.news_summarizer")


def summarize_articles(articles: list[dict], max_articles: int = 20) -> dict:
    """Generate a digest from a list of news articles.

    Returns structured digest with categories, key themes, and narrative.
    """
    if not articles:
        return {
            "total": 0,
            "headline": "No recent news to summarize.",
            "categories": {},
            "top_tickers": [],
            "key_themes": [],
            "narrative": "No news articles available for analysis.",
        }

    # ── Category Breakdown ───────────────────────────────────────
    categories: dict[str, list[dict]] = {}
    all_tickers: list[str] = []
    for article in articles[:max_articles]:
        cat = article.get("category", "general")
        categories.setdefault(cat, []).append(article)
        for t in (article.get("tickers_json") or []):
            all_tickers.append(t)

    # ── Top Tickers ──────────────────────────────────────────────
    ticker_counts = Counter(all_tickers).most_common(10)

    # ── Key Themes Extraction ────────────────────────────────────
    themes = _extract_themes(articles)

    # ── Sentiment Aggregation ────────────────────────────────────
    sentiments = [a.get("sentiment_score", 0) for a in articles if a.get("sentiment_score") is not None]
    avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
    positive_count = sum(1 for s in sentiments if s > 0.2)
    negative_count = sum(1 for s in sentiments if s < -0.2)

    # ── Headline Generation ──────────────────────────────────────
    if avg_sentiment > 0.2:
        tone = "positive"
        headline = f"Markets buoyed by {len(articles)} articles — sentiment predominantly positive."
    elif avg_sentiment < -0.2:
        tone = "negative"
        headline = f"Cautious tone across {len(articles)} articles — sentiment predominantly negative."
    else:
        tone = "neutral"
        headline = f"Mixed sentiment across {len(articles)} articles — no clear directional bias."

    # ── Narrative ────────────────────────────────────────────────
    narrative_parts = [headline, ""]
    for cat, arts in categories.items():
        top = arts[0] if arts else {}
        narrative_parts.append(f"{cat.upper()}: {top.get('title', 'No headline')}")

    if ticker_counts:
        tickers_str = ", ".join(f"${t}" for t, _ in ticker_counts[:5])
        narrative_parts.append(f"\nMost discussed: {tickers_str}")

    return {
        "total": len(articles),
        "headline": headline,
        "tone": tone,
        "categories": {k: v[:5] for k, v in categories.items()},
        "top_tickers": [{"ticker": t, "count": c} for t, c in ticker_counts],
        "key_themes": themes,
        "sentiment": {
            "average": round(avg_sentiment, 3),
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": len(sentiments) - positive_count - negative_count,
        },
        "narrative": "\n".join(narrative_parts),
    }


def summarize_single_article(article: dict) -> str:
    """Generate a summary for a single article using extractive approach."""
    title = article.get("title", "")
    summary = article.get("summary", "")
    content = article.get("content", "")
    category = article.get("category", "general")
    tickers = article.get("tickers_json") or []

    parts = []
    if title:
        parts.append(f"**{title}**")
    if category != "general":
        parts.append(f"Category: {category}")
    if tickers:
        parts.append(f"Related: {', '.join(f'${t}' for t in tickers[:5])}")
    if summary:
        parts.append(f"\n{summary[:500]}")
    elif content:
        parts.append(f"\n{content[:500]}")

    return "\n".join(parts) if parts else "No summary available."


def _extract_themes(articles: list[dict]) -> list[dict]:
    """Extract key themes from article titles and summaries."""
    THEME_KEYWORDS = {
        "rate_decision": ["rate", "hike", "cut", "federal reserve", "ecb", "monetary policy"],
        "inflation": ["inflation", "cpi", "price", "deflation"],
        "recession": ["recession", "downturn", "slowdown", "contraction"],
        "geopolitical": ["war", "sanctions", "trade", "tariff", "geopolitical"],
        "debt": ["debt", "bond", "issuance", "sovereign", "borrowing"],
        "currency": ["dollar", "euro", "yen", "currency", "forex", "fx"],
        "earnings": ["earnings", "revenue", "profit", "quarterly"],
        "green_finance": ["green", "esg", "sustainable", "climate", "carbon"],
    }

    theme_counts: dict[str, int] = {}
    for article in articles:
        text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
        for theme, keywords in THEME_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                theme_counts[theme] = theme_counts.get(theme, 0) + 1

    themes = sorted(theme_counts.items(), key=lambda x: -x[1])
    return [{"theme": t, "count": c} for t, c in themes[:5]]
