"""News API — ingestion, search, and feed endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.models.news import NewsArticle, NewsSource
from app.security import get_current_user
from app.services.news_ingestion import run_ingestion_cycle

router = APIRouter(prefix="/api/news", tags=["news"])


# ── Pydantic Schemas ──────────────────────────────────────────────


class NewsSourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    source_type: str = Field(..., description="newsapi, gdelt, yahoo_rss, rss")
    url: str = Field("", max_length=2000)
    config_json: Optional[dict] = None


class NewsSourceResponse(BaseModel):
    id: str
    name: str
    source_type: str
    url: str
    is_active: bool
    last_fetched_at: Optional[str]
    fetch_error: Optional[str]
    article_count: int = 0
    created_at: str

    class Config:
        from_attributes = True


class NewsArticleResponse(BaseModel):
    id: str
    source_id: str
    title: str
    summary: str
    url: str
    author: Optional[str]
    published_at: Optional[str]
    tickers_json: Optional[list]
    sentiment_score: Optional[float]
    category: str
    tags_json: Optional[list]
    is_read: bool
    is_starred: bool
    created_at: str

    class Config:
        from_attributes = True


class DigestResponse(BaseModel):
    total_articles: int
    categories: dict
    top_tickers: list
    articles: list


# ── Source Management ─────────────────────────────────────────────


@router.get("/sources", response_model=list[NewsSourceResponse])
def list_sources(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List all news sources."""
    sources = db.query(NewsSource).filter(
        NewsSource.org_id == user.org_id
    ).order_by(NewsSource.name).all()
    result = []
    for s in sources:
        count = db.query(NewsArticle).filter(NewsArticle.source_id == s.id).count()
        resp = NewsSourceResponse.model_validate(s).model_dump(mode="json")
        resp["article_count"] = count
        result.append(resp)
    return result


@router.post("/sources", response_model=NewsSourceResponse, status_code=201)
def create_source(data: NewsSourceCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new news source."""
    source = NewsSource(
        org_id=user.org_id,
        name=data.name,
        source_type=data.source_type,
        url=data.url,
        config_json=data.config_json or {},
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    resp = NewsSourceResponse.model_validate(source).model_dump(mode="json")
    resp["article_count"] = 0
    return resp


@router.delete("/sources/{source_id}", status_code=204)
def delete_source(source_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a news source."""
    source = db.query(NewsSource).filter(
        NewsSource.id == source_id,
        NewsSource.org_id == user.org_id,
    ).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    db.delete(source)
    db.commit()


@router.post("/sources/{source_id}/toggle")
def toggle_source(source_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Toggle a news source active/inactive."""
    source = db.query(NewsSource).filter(
        NewsSource.id == source_id,
        NewsSource.org_id == user.org_id,
    ).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    source.is_active = not source.is_active
    db.commit()
    return {"is_active": source.is_active}


# ── Articles ──────────────────────────────────────────────────────


@router.get("/articles", response_model=list[NewsArticleResponse])
def list_articles(
    category: Optional[str] = Query(None),
    ticker: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    starred_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List news articles with filters."""
    q = db.query(NewsArticle).join(NewsSource).filter(
        NewsSource.org_id == user.org_id
    )
    if category:
        q = q.filter(NewsArticle.category == category)
    if ticker:
        q = q.filter(NewsArticle.tickers_json.contains([ticker.upper()]))
    if search:
        q = q.filter(
            or_(
                NewsArticle.title.ilike(f"%{search}%"),
                NewsArticle.summary.ilike(f"%{search}%"),
            )
        )
    if starred_only:
        q = q.filter(NewsArticle.is_starred == True)

    articles = q.order_by(desc(NewsArticle.published_at)).offset(offset).limit(limit).all()
    return [NewsArticleResponse.model_validate(a).model_dump(mode="json") for a in articles]


@router.get("/articles/{article_id}", response_model=NewsArticleResponse)
def get_article(article_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get a single article."""
    article = db.query(NewsArticle).join(NewsSource).filter(
        NewsArticle.id == article_id,
        NewsSource.org_id == user.org_id,
    ).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return NewsArticleResponse.model_validate(article).model_dump(mode="json")


@router.post("/articles/{article_id}/read")
def mark_read(article_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Mark an article as read."""
    article = db.query(NewsArticle).join(NewsSource).filter(
        NewsArticle.id == article_id,
        NewsSource.org_id == user.org_id,
    ).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    article.is_read = True
    db.commit()
    return {"ok": True}


@router.post("/articles/{article_id}/star")
def toggle_star(article_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Toggle star/unstar on an article."""
    article = db.query(NewsArticle).join(NewsSource).filter(
        NewsArticle.id == article_id,
        NewsSource.org_id == user.org_id,
    ).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    article.is_starred = not article.is_starred
    db.commit()
    return {"is_starred": article.is_starred}


# ── Digest & Ingestion ───────────────────────────────────────────


@router.get("/digest")
def get_digest(
    hours: int = Query(24, ge=1, le=168),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a digest of recent news grouped by category and ticker."""
    from datetime import datetime, timedelta, timezone

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    articles = db.query(NewsArticle).join(NewsSource).filter(
        NewsSource.org_id == user.org_id,
        NewsArticle.created_at >= cutoff,
    ).order_by(desc(NewsArticle.published_at)).limit(200).all()

    categories: dict[str, list] = {}
    ticker_counts: dict[str, int] = {}
    for a in articles:
        cat = a.category or "general"
        categories.setdefault(cat, []).append({
            "id": a.id,
            "title": a.title,
            "summary": a.summary[:200],
            "url": a.url,
            "source": a.source.name if a.source else "",
            "published_at": a.published_at,
            "tickers": a.tickers_json or [],
            "sentiment_score": a.sentiment_score,
        })
        for t in (a.tickers_json or []):
            ticker_counts[t] = ticker_counts.get(t, 0) + 1

    top_tickers = sorted(ticker_counts.items(), key=lambda x: -x[1])[:10]

    return {
        "total_articles": len(articles),
        "categories": {k: v[:10] for k, v in categories.items()},
        "top_tickers": [{"ticker": t, "count": c} for t, c in top_tickers],
        "period_hours": hours,
    }


@router.post("/ingest")
def trigger_ingestion(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually trigger news ingestion from all active sources."""
    results = run_ingestion_cycle(db, org_id=user.org_id)
    total_new = sum(r.get("new", 0) for r in results)
    total_dup = sum(r.get("duplicate", 0) for r in results)
    return {
        "sources_processed": len(results),
        "total_new": total_new,
        "total_duplicates": total_dup,
        "details": results,
    }


@router.get("/stats")
def get_stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get news ingestion statistics."""
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    day_ago = (now - timedelta(days=1)).isoformat()
    week_ago = (now - timedelta(days=7)).isoformat()

    total = db.query(NewsArticle).join(NewsSource).filter(
        NewsSource.org_id == user.org_id
    ).count()
    last_24h = db.query(NewsArticle).join(NewsSource).filter(
        NewsSource.org_id == user.org_id,
        NewsArticle.created_at >= day_ago,
    ).count()
    last_week = db.query(NewsArticle).join(NewsSource).filter(
        NewsSource.org_id == user.org_id,
        NewsArticle.created_at >= week_ago,
    ).count()
    sources = db.query(NewsSource).filter(
        NewsSource.org_id == user.org_id,
        NewsSource.is_active == True,
    ).count()

    return {
        "total_articles": total,
        "last_24h": last_24h,
        "last_week": last_week,
        "active_sources": sources,
    }
