"""News data providers — NewsAPI, GDELT, Yahoo Finance RSS, generic RSS."""
from __future__ import annotations

import hashlib
import logging
import re
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import requests

logger = logging.getLogger("quantive.news.providers")


@dataclass
class RawNewsArticle:
    """Provider-agnostic news article before storage."""
    title: str
    summary: str
    content: str
    url: str
    author: str
    published_at: str
    source_name: str
    tickers: list[str] = field(default_factory=list)
    category: str = "general"
    image_url: str = ""

    @property
    def ingestion_hash(self) -> str:
        raw = f"{self.title}|{self.url}".encode()
        return hashlib.sha256(raw).hexdigest()


TICKER_RE = re.compile(r"\b([A-Z]{1,5})\b")


def extract_tickers(text: str, known_tickers: set[str] | None = None) -> list[str]:
    """Extract probable stock tickers from text. Filters common English words."""
    STOP_WORDS = {
        "THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL", "CAN", "HER",
        "WAS", "ONE", "OUR", "OUT", "HAS", "HIS", "HOW", "ITS", "MAY", "NEW",
        "NOW", "OLD", "SEE", "WAY", "WHO", "AGO", "DID", "GET", "HIM", "LET",
        "SAY", "SHE", "TOO", "USE", "CEO", "CFO", "CTO", "IPO", "ETF", "GDP",
        "IMF", "ECB", "FED", "USD", "EUR", "GBP", "JPY", "API", "SQL", "DOM",
        "URL", "PDF", "USD", "UK", "US", "EU", "AI", "FSB", "SPV", "SOE",
        "BIS", "OPEC", "WTO", "WHO", "UN", "OECD", "G7", "G20", "BRICS",
    }
    words = TICKER_RE.findall(text.upper())
    tickers = []
    for w in words:
        if w in STOP_WORDS:
            continue
        if known_tickers and w in known_tickers:
            tickers.append(w)
        elif len(w) <= 5 and w.isalpha():
            tickers.append(w)
    return list(dict.fromkeys(tickers))[:5]


class NewsProvider(ABC):
    """Base interface for news data providers."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def fetch(
        self,
        query: str = "",
        tickers: list[str] | None = None,
        category: str = "",
        limit: int = 50,
    ) -> list[RawNewsArticle]: ...

    def health_check(self) -> dict:
        return {"provider": self.name, "available": True}


# ── NewsAPI (newsapi.org) ─────────────────────────────────────────


class NewsAPIProvider(NewsProvider):
    """NewsAPI.org provider — 100 req/day free tier."""

    BASE_URL = "https://newsapi.org/v2"

    def __init__(self, api_key: str):
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "newsapi"

    def fetch(
        self,
        query: str = "sovereign debt OR bonds OR interest rates",
        tickers: list[str] | None = None,
        category: str = "",
        limit: int = 50,
    ) -> list[RawNewsArticle]:
        articles: list[RawNewsArticle] = []
        params = {
            "q": query,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": min(limit, 100),
            "apiKey": self._api_key,
        }
        if category:
            params["category"] = category

        try:
            resp = requests.get(
                f"{self.BASE_URL}/everything",
                params=params,
                timeout=30,
                headers={"User-Agent": "Quantive/1.0"},
            )
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("articles", []):
                articles.append(RawNewsArticle(
                    title=item.get("title", ""),
                    summary=item.get("description", ""),
                    content=item.get("content", ""),
                    url=item.get("url", ""),
                    author=item.get("author", ""),
                    published_at=item.get("publishedAt", ""),
                    source_name=item.get("source", {}).get("name", "NewsAPI"),
                    tickers=extract_tickers(f"{item.get('title', '')} {item.get('description', '')}"),
                ))
        except Exception as e:
            logger.warning(f"[NewsAPI] Error: {e}")

        return articles


# ── GDELT (Global Database of Events, Language, and Tone) ─────────


class GDELTProvider(NewsProvider):
    """GDELT Project — free, unlimited, global news coverage."""

    BASE_URL = "https://api.gdelt.org/api/v2"

    @property
    def name(self) -> str:
        return "gdelt"

    def fetch(
        self,
        query: str = "sovereign debt bonds",
        tickers: list[str] | None = None,
        category: str = "",
        limit: int = 50,
    ) -> list[RawNewsArticle]:
        articles: list[RawNewsArticle] = []
        params = {
            "query": query,
            "mode": "artlist",
            "maxrecords": min(limit, 250),
            "format": "json",
            "sort": "DateDesc",
        }

        try:
            resp = requests.get(
                f"{self.BASE_URL}/doc",
                params=params,
                timeout=30,
                headers={"User-Agent": "Quantive/1.0"},
            )
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("articles", []):
                articles.append(RawNewsArticle(
                    title=item.get("title", ""),
                    summary=item.get("seendate", ""),
                    content=item.get("socialimage", ""),
                    url=item.get("url", ""),
                    author=item.get("domain", ""),
                    published_at=item.get("seendate", ""),
                    source_name=item.get("domain", "GDELT"),
                    tickers=extract_tickers(item.get("title", "")),
                    category="general",
                ))
        except Exception as e:
            logger.warning(f"[GDELT] Error: {e}")

        return articles


# ── Yahoo Finance RSS ─────────────────────────────────────────────


class YahooRSSProvider(NewsProvider):
    """Yahoo Finance RSS feed — free, no API key."""

    FEEDS = {
        "general": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=%s&region=US&lang=en-US",
        "market": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC&region=US&lang=en-US",
    }

    @property
    def name(self) -> str:
        return "yahoo_rss"

    def fetch(
        self,
        query: str = "",
        tickers: list[str] | None = None,
        category: str = "general",
        limit: int = 50,
    ) -> list[RawNewsArticle]:
        articles: list[RawNewsArticle] = []

        # Yahoo RSS accepts ONE symbol per request — multi-symbol URLs return
        # zero items. Fetch each symbol separately, deduping by URL.
        symbols = tickers or ["^GSPC"]
        feed_template = self.FEEDS.get(category, self.FEEDS["general"])

        ns = {"media": "http://search.yahoo.com/mrss/"}
        seen_urls: set[str] = set()

        for sym in symbols[:5]:
            if len(articles) >= limit:
                break
            url = feed_template % sym
            try:
                resp = requests.get(url, timeout=15, headers={"User-Agent": "Quantive/1.0"})
                resp.raise_for_status()
                root = ET.fromstring(resp.content)

                for item in root.findall(".//item"):
                    if len(articles) >= limit:
                        break
                    title = item.findtext("title", "")
                    link = item.findtext("link", "")
                    if not title or (link and link in seen_urls):
                        continue
                    if link:
                        seen_urls.add(link)
                    desc = item.findtext("description", "")
                    pub_date = item.findtext("pubDate", "")
                    media_thumb = item.find("media:thumbnail", ns)
                    image_url = media_thumb.get("url", "") if media_thumb is not None else ""

                    # Tag articles with the queried symbol first so sentiment
                    # attribution works even if extract_tickers misses it
                    auto_tickers = extract_tickers(f"{title} {desc}")
                    tagged = ([sym] if sym not in ("^GSPC",) else []) + [
                        t for t in auto_tickers if t != sym
                    ]

                    articles.append(RawNewsArticle(
                        title=title,
                        summary=desc,
                        content="",
                        url=link,
                        author="Yahoo Finance",
                        published_at=pub_date,
                        source_name="Yahoo Finance",
                        tickers=tagged[:5],
                        category=category,
                        image_url=image_url,
                    ))
            except Exception as e:
                logger.warning(f"[YahooRSS] Error fetching {sym}: {e}")

        return articles


# ── Generic RSS ───────────────────────────────────────────────────


class GenericRSSProvider(NewsProvider):
    """Generic RSS/Atom feed parser — works with any standard feed."""

    @property
    def name(self) -> str:
        return "generic_rss"

    def __init__(self, feed_url: str, feed_name: str = "RSS"):
        self._feed_url = feed_url
        self._feed_name = feed_name

    def fetch(
        self,
        query: str = "",
        tickers: list[str] | None = None,
        category: str = "general",
        limit: int = 50,
    ) -> list[RawNewsArticle]:
        articles: list[RawNewsArticle] = []

        try:
            resp = requests.get(self._feed_url, timeout=30, headers={"User-Agent": "Quantive/1.0"})
            resp.raise_for_status()
            root = ET.fromstring(resp.content)

            items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
            for item in items[:limit]:
                title = item.findtext("title") or item.findtext("{http://www.w3.org/2005/Atom}title") or ""
                link = item.findtext("link") or ""
                if not link:
                    link_el = item.find("{http://www.w3.org/2005/Atom}link")
                    link = link_el.get("href", "") if link_el is not None else ""
                desc = item.findtext("description") or item.findtext("{http://www.w3.org/2005/Atom}summary") or ""
                pub_date = item.findtext("pubDate") or item.findtext("{http://www.w3.org/2005/Atom}updated") or ""

                articles.append(RawNewsArticle(
                    title=title,
                    summary=desc[:500],
                    content="",
                    url=link,
                    author=self._feed_name,
                    published_at=pub_date,
                    source_name=self._feed_name,
                    tickers=extract_tickers(f"{title} {desc}"),
                    category=category,
                ))
        except Exception as e:
            logger.warning(f"[GenericRSS:{self._feed_name}] Error: {e}")

        return articles


# ── Provider Factory ──────────────────────────────────────────────


def create_provider(source_type: str, **kwargs) -> Optional[NewsProvider]:
    """Factory: create a provider from source type string."""
    providers = {
        "newsapi": lambda: NewsAPIProvider(api_key=kwargs.get("api_key", "")),
        "gdelt": lambda: GDELTProvider(),
        "yahoo_rss": lambda: YahooRSSProvider(),
        "rss": lambda: GenericRSSProvider(
            feed_url=kwargs.get("url", ""),
            feed_name=kwargs.get("name", "RSS"),
        ),
    }
    factory = providers.get(source_type)
    return factory() if factory else None
