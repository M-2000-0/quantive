"""News and content ingestion models."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class NewsSource(Base):
    """Configurable news data source."""
    __tablename__ = "news_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # newsapi, gdelt, rss, yahoo_rss
    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    config_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_fetched_at: Mapped[datetime | None] = mapped_column(String(30), nullable=True)
    fetch_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    articles: Mapped[list["NewsArticle"]] = relationship(back_populates="source", cascade="all, delete-orphan")


class NewsArticle(Base):
    """Individual ingested news article."""
    __tablename__ = "news_articles"
    __table_args__ = (
        Index("ix_news_articles_published", "published_at"),
        Index("ix_news_articles_source", "source_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    source_id: Mapped[str] = mapped_column(String(36), ForeignKey("news_sources.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(String(30), nullable=True)
    tickers_json: Mapped[list | None] = mapped_column(JSON, nullable=True)  # ["AAPL", "MSFT"]
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # -1.0 to 1.0
    category: Mapped[str] = mapped_column(String(100), default="general")  # macro, equity, fx, rates, crypto, geopolitical
    tags_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    ingestion_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)  # content hash for dedup
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    source: Mapped["NewsSource"] = relationship(back_populates="articles")
