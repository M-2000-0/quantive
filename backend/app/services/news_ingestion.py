"""News ingestion service — fetch, deduplicate, store, and query news articles."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.market_data.news_providers import (
    RawNewsArticle,
    create_provider,
)
from app.models.news import NewsArticle, NewsSource

logger = logging.getLogger("quantive.news.ingestion")

# Ticker classification into categories
CATEGORY_KEYWORDS = {
    "fx": ["forex", "currency", "exchange rate", "dollar", "euro", "yen", "gbp", "fx"],
    "rates": ["interest rate", "yield", "treasury", "bond", "sofr", "fed funds", "rate hike", "rate cut"],
    "macro": ["gdp", "inflation", "cpi", "unemployment", "fiscal", "monetary", "central bank", "imf", "world bank"],
    "equity": ["stock", "share", "equity", "s&p 500", "nasdaq", "dow", "earnings", "ipo"],
    "crypto": ["bitcoin", "ethereum", "crypto", "blockchain", "defi"],
    "geopolitical": ["war", "sanctions", "trade war", "tariff", "geopolitical", "conflict", "election"],
    "green": ["green bond", "esg", "sustainable", "climate", "carbon"],
}


def classify_article(article: RawNewsArticle) -> str:
    """Auto-classify article category from title + summary."""
    text = f"{article.title} {article.summary}".lower()
    scores: dict[str, int] = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        scores[cat] = sum(1 for kw in keywords if kw in text)
    if max(scores.values(), default=0) > 0:
        return max(scores, key=scores.get)
    return "general"


def ingest_articles(
    db: Session,
    source: NewsSource,
    articles: list[RawNewsArticle],
) -> dict:
    """Ingest articles from a provider into the database. Returns stats."""
    stats = {"fetched": len(articles), "new": 0, "duplicate": 0, "errors": 0}

    for raw in articles:
        try:
            exists = db.query(NewsArticle).filter(
                NewsArticle.ingestion_hash == raw.ingestion_hash
            ).first()
            if exists:
                stats["duplicate"] += 1
                continue

            category = classify_article(raw)
            published = _parse_date(raw.published_at)

            article = NewsArticle(
                source_id=source.id,
                title=raw.title[:500],
                summary=raw.summary[:2000],
                content=raw.content[:10000] if raw.content else "",
                url=raw.url[:2000],
                author=raw.author[:255] if raw.author else None,
                published_at=published,
                tickers_json=raw.tickers if raw.tickers else None,
                category=category,
                ingestion_hash=raw.ingestion_hash,
            )
            db.add(article)
            stats["new"] += 1
        except Exception as e:
            logger.warning(f"Error ingesting article '{raw.title[:50]}': {e}")
            stats["errors"] += 1

    source.last_fetched_at = datetime.now(timezone.utc).isoformat()
    source.fetch_error = None
    db.commit()
    return stats


def fetch_from_source(source: NewsSource) -> list[RawNewsArticle]:
    """Fetch articles from a configured news source."""
    config = source.config_json or {}
    provider = create_provider(
        source.source_type,
        api_key=config.get("api_key", ""),
        url=source.url,
        name=source.name,
    )
    if not provider:
        logger.warning(f"Unknown source type: {source.source_type}")
        return []

    query = config.get("query", "sovereign debt bonds interest rates")
    tickers = config.get("tickers", [])
    limit = config.get("limit", 50)

    return provider.fetch(query=query, tickers=tickers, limit=limit)


def run_ingestion_cycle(db: Session, org_id: Optional[str] = None) -> list[dict]:
    """Run a full ingestion cycle for all active sources. Returns per-source stats."""
    query = db.query(NewsSource).filter(NewsSource.is_active == True)
    if org_id:
        query = query.filter(NewsSource.org_id == org_id)

    sources = query.all()
    results = []

    for source in sources:
        try:
            raw_articles = fetch_from_source(source)
            stats = ingest_articles(db, source, raw_articles)
            stats["source"] = source.name
            stats["source_type"] = source.source_type
            results.append(stats)
            logger.info(f"Ingested {stats['new']} new articles from {source.name}")
        except Exception as e:
            logger.error(f"Ingestion failed for {source.name}: {e}")
            source.fetch_error = str(e)[:500]
            db.commit()
            results.append({"source": source.name, "error": str(e)})

    return results


def _parse_date(date_str: str) -> Optional[str]:
    """Best-effort date parsing for various formats."""
    if not date_str:
        return None
    formats = [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.isoformat()
        except ValueError:
            continue
    return date_str[:30]
