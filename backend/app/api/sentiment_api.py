"""Per-asset news sentiment for the market monitor.

Endpoints:
  GET /api/v1/market-monitor/sentiment            — Sentiment for all tracked assets
  GET /api/v1/market-monitor/sentiment/{symbol}   — Sentiment detail for one asset
  POST /api/v1/market-monitor/sentiment/backfill  — Rescore articles missing sentiment
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db

logger = logging.getLogger("quantive.sentiment")

router = APIRouter(prefix="/market-monitor/sentiment", tags=["market-sentiment"])


def _recent_scores_by_ticker(db: Session, days: int = 3) -> dict[str, list[float]]:
    """Map ticker -> list of recent article sentiment scores."""
    from app.models.news import NewsArticle

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    articles = (
        db.query(
            NewsArticle.tickers_json,
            NewsArticle.sentiment_score,
            NewsArticle.published_at,
        )
        .filter(NewsArticle.sentiment_score.isnot(None))
        .order_by(desc(NewsArticle.published_at))
        .limit(2000)
        .all()
    )

    by_ticker: dict[str, list[float]] = {}
    for tickers, score, published in articles:
        if not tickers or score is None:
            continue
        # Recency filter (published_at stored as ISO string)
        try:
            if published and str(published) < cutoff:
                continue
        except Exception:
            pass
        for t in tickers[:5]:
            t = (t or "").upper()
            if t:
                by_ticker.setdefault(t, []).append(float(score))
    return by_ticker


@router.get("")
@router.get("/")
def get_all_sentiment(
    db: Session = Depends(get_db),
    asset_class: Optional[str] = None,
    days: int = 3,
):
    """News sentiment for every tracked asset that has recent coverage."""
    from app.services.sentiment_analyzer import aggregate_sentiment

    try:
        from app.api.market_monitor_api import _asset_store
        assets = list(_asset_store.values())
    except Exception:
        assets = []

    if asset_class:
        assets = [a for a in assets if a.get("asset_class") == asset_class]

    by_ticker = _recent_scores_by_ticker(db, days=days)

    results = []
    for a in assets:
        symbol = (a.get("symbol") or "").upper()
        # Strip exchange prefixes used in stores (e.g. CRYPTO:BTC, FX:EURUSD)
        base = symbol.split(":")[-1]
        scores = by_ticker.get(base) or by_ticker.get(symbol) or []
        agg = aggregate_sentiment(scores)
        if agg["count"] == 0:
            continue
        results.append({
            "symbol": base,
            "name": a.get("name", base),
            "asset_class": a.get("asset_class", "stock"),
            "current_price": a.get("current_price"),
            "day_change_pct": a.get("day_change_pct"),
            **agg,
        })

    # Sort: most negative first is most actionable for risk, but default to
    # strongest absolute sentiment so users see conviction either way
    results.sort(key=lambda r: abs(r.get("mean") or 0), reverse=True)

    return {
        "sentiment": results,
        "total": len(results),
        "coverage_note": (
            "Sentiment from financial news headlines over the last "
            f"{days} days. Score ranges -1.0 (very negative) to +1.0 (very positive)."
        ),
    }


@router.get("/divergence")
def get_sentiment_divergence(
    db: Session = Depends(get_db),
    days: int = 3,
):
    """Assets where news tone and price action disagree.

    Bearish divergence: positive coverage while price falls (hype without
    delivery). Bullish divergence: negative coverage while price rises
    (market ignoring bad news). Alignment is not flagged.
    """
    from app.services.sentiment_divergence import compute_divergences

    try:
        from app.api.market_monitor_api import _asset_store
        assets = list(_asset_store.values())
    except Exception:
        assets = []

    if not assets:
        return {
            "divergences": [],
            "total": 0,
            "note": "No tracked assets. Run market data ingestion first.",
        }

    by_ticker = _recent_scores_by_ticker(db, days=days)
    from app.services.sentiment_analyzer import aggregate_sentiment

    sentiment_by_symbol = {
        sym: aggregate_sentiment(scores) for sym, scores in by_ticker.items()
    }

    flags = compute_divergences(assets, sentiment_by_symbol)

    return {
        "divergences": flags,
        "total": len(flags),
        "bearish_count": sum(1 for f in flags if f["divergence_type"] == "bearish_divergence"),
        "bullish_count": sum(1 for f in flags if f["divergence_type"] == "bullish_divergence"),
        "window_days": days,
    }


@router.get("/{symbol}")
def get_symbol_sentiment(symbol: str, db: Session = Depends(get_db), days: int = 7):
    """Sentiment detail for a single asset, including recent headline evidence."""
    from app.models.news import NewsArticle
    from app.services.sentiment_analyzer import aggregate_sentiment, analyze_sentiment

    sym = symbol.upper().split(":")[-1]

    articles = (
        db.query(NewsArticle)
        .filter(NewsArticle.sentiment_score.isnot(None))
        .order_by(desc(NewsArticle.published_at))
        .limit(1000)
        .all()
    )

    matched = []
    for art in articles:
        tickers = [t.upper() for t in (art.tickers_json or [])]
        if sym in tickers:
            matched.append(art)

    scores = [float(a.sentiment_score) for a in matched if a.sentiment_score is not None]
    agg = aggregate_sentiment(scores)

    headlines = []
    for art in matched[:8]:
        # Re-derive evidence for display
        ev = analyze_sentiment(art.title or "")
        headlines.append({
            "title": art.title,
            "published_at": str(art.published_at) if art.published_at else None,
            "sentiment_score": float(art.sentiment_score),
            "label": ev["label"],
            "positive_matches": ev["positive_matches"],
            "negative_matches": ev["negative_matches"],
        })

    return {
        "symbol": sym,
        **agg,
        "headlines": headlines,
        "coverage_note": "Sentiment from financial news headlines. Score -1.0 to +1.0.",
    }


@router.post("/backfill")
def trigger_backfill(db: Session = Depends(get_db)):
    """Rescore all articles missing a sentiment score (idempotent)."""
    from app.services.news_ingestion import backfill_sentiment
    n = backfill_sentiment(db, limit=2000)
    return {"backfilled": n}
