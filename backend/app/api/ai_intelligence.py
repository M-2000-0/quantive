"""AI Intelligence API — market summaries, news summaries, stock explanations, signal conflicts."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import get_current_user
from app.services.market_summary import generate_market_summary, generate_llm_market_summary
from app.services.news_summarizer import summarize_articles, summarize_single_article
from app.services.stock_explainer import explain_stock
from app.services.signal_conflict import detect_conflicts

router = APIRouter(prefix="/api/ai", tags=["ai-intelligence"])


# ── Market Summary ────────────────────────────────────────────────


@router.get("/market-summary")
def get_market_summary(
    use_llm: bool = Query(False),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate an AI market summary from current data."""
    from app.market_data.engine import get_market_engine

    engine = get_market_engine()
    yield_curve = None
    fx_rates = None
    interest_rates = None

    try:
        yc = engine.get_yield_curve("US")
        if yc:
            yield_curve = {
                "points": [{"maturity_months": p.maturity_months, "rate_pct": p.rate_pct} for p in yc.points],
                "two_ten_spread_bps": yc.two_ten_spread_bps,
            }
    except Exception:
        pass

    try:
        fx = engine.get_fx_rates("USD")
        if fx:
            fx_rates = [{"pair": r.pair, "rate": r.rate} for r in fx]
    except Exception:
        pass

    try:
        rates = engine.get_benchmark_rates()
        if rates:
            interest_rates = [{"name": r.name, "rate_pct": r.rate_pct} for r in rates]
    except Exception:
        pass

    if use_llm:
        summary = generate_llm_market_summary(yield_curve, fx_rates, interest_rates)
        return {"summary": summary, "type": "llm"}
    else:
        return generate_market_summary(yield_curve, fx_rates, interest_rates)


# ── News Summary ──────────────────────────────────────────────────


@router.get("/news-summary")
def get_news_summary(
    hours: int = Query(24, ge=1, le=168),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate an AI news digest from recent articles."""
    from datetime import datetime, timedelta, timezone
    from app.models.news import NewsArticle, NewsSource

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    articles = db.query(NewsArticle).join(NewsSource).filter(
        NewsSource.org_id == user.org_id,
        NewsArticle.created_at >= cutoff,
    ).order_by(NewsArticle.created_at.desc()).limit(100).all()

    article_dicts = [{
        "title": a.title,
        "summary": a.summary,
        "category": a.category,
        "tickers_json": a.tickers_json,
        "sentiment_score": a.sentiment_score,
    } for a in articles]

    return summarize_articles(article_dicts)


@router.get("/news-summary/{article_id}")
def get_article_summary(article_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Generate a summary for a single article."""
    from app.models.news import NewsArticle, NewsSource

    article = db.query(NewsArticle).join(NewsSource).filter(
        NewsArticle.id == article_id,
        NewsSource.org_id == user.org_id,
    ).first()
    if not article:
        return {"error": "Article not found"}

    return {
        "summary": summarize_single_article({
            "title": article.title,
            "summary": article.summary,
            "content": article.content,
            "category": article.category,
            "tickers_json": article.tickers_json,
        })
    }


# ── Stock Explanation ─────────────────────────────────────────────


@router.get("/explain-stock/{symbol}")
def get_stock_explanation(symbol: str, user: User = Depends(get_current_user)):
    """Generate an AI explanation for a stock."""
    from app.api.trading_intelligence import _fetch_stock_data, _generate_signal

    symbol = symbol.upper()

    try:
        stock_data = _fetch_stock_data(symbol)
        technical = _generate_signal(symbol, stock_data) if stock_data else None
    except Exception:
        stock_data = None
        technical = None

    return explain_stock(
        symbol=symbol,
        price_data=stock_data,
        technical_signals=technical,
    )


# ── Signal Conflict Detection ────────────────────────────────────


@router.get("/signal-conflicts/{symbol}")
def get_signal_conflicts(symbol: str, user: User = Depends(get_current_user)):
    """Detect conflicting technical signals for a stock."""
    from app.api.trading_intelligence import _fetch_stock_data, _generate_signal

    symbol = symbol.upper()

    try:
        stock_data = _fetch_stock_data(symbol)
        if not stock_data:
            return {"error": "Unable to fetch stock data"}
        signals = _generate_signal(symbol, stock_data)
    except Exception:
        return {"error": "Unable to generate signals"}

    return detect_conflicts(
        rsi_signal=signals.get("rsi_signal"),
        macd_signal=signals.get("macd_signal"),
        moving_avg_signal=signals.get("moving_avg_signal"),
        bollinger_signal=signals.get("bollinger_signal"),
        composite_score=signals.get("composite_score", 0),
    )


# ── Model Performance ────────────────────────────────────────────


@router.get("/model-performance")
def get_model_performance(
    model_name: Optional[str] = Query(None),
    hours: int = Query(168, ge=1, le=720),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get model performance metrics and drift tracking."""
    from app.services.model_monitor import get_model_performance as get_perf
    return get_perf(db, model_name=model_name, hours=hours)


@router.get("/drift-alerts")
def get_drift_alerts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Check for model drift alerts."""
    from app.services.model_monitor import check_drift_alerts
    return {"alerts": check_drift_alerts(db)}
