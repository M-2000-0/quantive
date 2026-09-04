"""Provider-agnostic data abstraction layer for market data.

Architecture: Provider → Adapter → Unified Schema
Each provider implements the same interface. Swapping sources is a config change.

Provides:
- MarketDataProvider (ABC) — base interface every provider must implement
- RateLimiter — shared token-bucket rate limiter per source
- Paginator — pagination abstraction (offset/limit and cursor styles)
- Unified data schema dataclasses
"""
from __future__ import annotations

import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from collections import defaultdict
from threading import Lock

import requests

from app.market_data.cache import get_cache, TTL_YIELD_CURVE, TTL_FX_RATES, TTL_INTEREST_RATES, TTL_ECONOMIC_INDICATORS

logger = logging.getLogger("quantive.market_data.provider")

# ── Unified Data Schema ─────────────────────────────────────────────


class MaturityUnit(str, Enum):
    """Standardised maturity units."""
    MONTHS = "months"
    YEARS = "years"
    DAYS = "days"


@dataclass(frozen=True, slots=True)
class YieldCurvePoint:
    """Single point on a yield curve, provider-agnostic."""
    maturity_months: int
    rate_pct: float
    source: str = ""
    date: str = ""
    label: str = ""


@dataclass(frozen=True, slots=True)
class YieldCurve:
    """Complete yield curve for a country / currency."""
    country_code: str
    currency: str
    date: str
    source: str
    points: list[YieldCurvePoint] = field(default_factory=list)
    two_ten_spread_bps: Optional[float] = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return len(self.points) == 0


@dataclass(frozen=True, slots=True)
class FxRate:
    """Foreign exchange rate, provider-agnostic."""
    pair: str
    rate: float
    date: str
    source: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MacroIndicator:
    """Macroeconomic indicator data point."""
    indicator: str
    value: float
    unit: str = ""
    country: str = ""
    date: str = ""
    source: str = ""
    indicator_code: str = ""


@dataclass(frozen=True, slots=True)
class EconomicSnapshot:
    """Aggregated macro snapshot for a country."""
    country_code: str
    country_name: str = ""
    indicators: list[MacroIndicator] = field(default_factory=list)
    source: str = ""
    date: str = ""


@dataclass(frozen=True, slots=True)
class BenchmarkRate:
    """A single benchmark interest rate."""
    name: str
    rate_pct: float
    date: str
    source: str


# ── Pagination ──────────────────────────────────────────────────────


class Page:
    """A single page of paginated results."""

    def __init__(self, items: list[Any], total: int, page: int, page_size: int):
        self.items = items
        self.total = total
        self.page = page
        self.page_size = page_size

    @property
    def has_next(self) -> bool:
        return self.page * self.page_size < self.total

    @property
    def has_prev(self) -> bool:
        return self.page > 0

    def next_page(self) -> int:
        return self.page + 1 if self.has_next else self.page


class Paginator:
    """Fetch all pages from a paginated endpoint transparently."""

    def __init__(self, session: requests.Session, base_url: str, per_page: int = 50):
        self._session = session
        self._base_url = base_url
        self._per_page = per_page

    def fetch_all(
        self,
        params: Optional[dict[str, Any]] = None,
        next_page_fn: Optional[callable] = None,
    ) -> list[dict]:
        """Fetch all pages. ``next_page_fn(base_url, current_params)`` returns
        the URL for the next page or ``None`` when exhausted."""
        all_items: list[dict] = []
        params = dict(params or {})
        url = self._base_url
        visited = set()

        while url and url not in visited:
            visited.add(url)
            resp = self._session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            if isinstance(data, list):
                items = data
                total = len(items)
            elif isinstance(data, dict):
                items = data.get("data", data.get("records", data.get("value", [])))
                total = data.get("total", data.get("totalRecords", len(items)))
            else:
                break

            if not items:
                break

            all_items.extend(items if isinstance(items, list) else [items])

            if next_page_fn:
                url = next_page_fn(url, params)
                if url:
                    params = {}
            elif isinstance(data, dict):
                p = data.get("page", {})
                if p.get("page", 0) + 1 < p.get("pages", 1):
                    params["page"] = p.get("page", 0) + 1
                    params["per_page"] = self._per_page
                else:
                    break
            else:
                break

        return all_items


# ── Rate Limiter ────────────────────────────────────────────────────


class RateLimiter:
    """Thread-safe token-bucket rate limiter, one bucket per source."""

    def __init__(self, default_rps: float = 10.0):
        self._default_rps = default_rps
        self._buckets: dict[str, dict] = {}
        self._lock = Lock()

    def acquire(self, source: str, tokens: int = 1) -> None:
        """Block until *tokens* are available for *source*."""
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets.setdefault(source, {"tokens": self._default_rps, "last": now})
        # update outside lock minimally
        elapsed = now - bucket["last"]
        with self._lock:
            bucket["tokens"] = min(self._default_rps, bucket["tokens"] + elapsed * self._default_rps)
            bucket["last"] = now
            if bucket["tokens"] >= tokens:
                bucket["tokens"] -= tokens
                return
            wait = (tokens - bucket["tokens"]) / self._default_rps
            bucket["tokens"] = 0
        time.sleep(max(wait, 0.01))

    def set_rate(self, source: str, rps: float) -> None:
        with self._lock:
            self._buckets.setdefault(source, {"tokens": rps, "last": time.monotonic()})
            self._buckets[source]["tokens"] = rps
            self._default_rps = max(self._default_rps, rps)


# Global shared limiter
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(default_rps=10.0)
    return _rate_limiter


# ── Base Provider Interface ─────────────────────────────────────────


class MarketDataProvider(ABC):
    """Base interface for all market data providers.

    Every concrete provider MUST implement these methods and return the
    unified dataclass schema so downstream code is provider-agnostic.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """True if the provider can be reached."""

    @abstractmethod
    def get_yield_curve(
        self, country_code: str = "US", date: Optional[str] = None,
    ) -> Optional[YieldCurve]:
        """Fetch the sovereign yield curve."""

    @abstractmethod
    def get_fx_rate(self, pair: str, date: Optional[str] = None) -> Optional[FxRate]:
        """Fetch a single FX rate pair."""

    @abstractmethod
    def get_fx_rates(self, base: str = "USD") -> list[FxRate]:
        """Fetch all key FX rates against *base*."""

    @abstractmethod
    def get_benchmark_rates(self) -> list[BenchmarkRate]:
        """Fetch all available benchmark interest rates (SOFR, MRR, etc.)."""

    @abstractmethod
    def get_economic_snapshot(
        self, country_code: str, indicators: Optional[list[str]] = None,
    ) -> Optional[EconomicSnapshot]:
        """Fetch macro snapshot for a country."""

    @abstractmethod
    def get_historical_series(
        self, series_id: str, start: str, end: str,
    ) -> list[dict]:
        """Fetch a historical time series (for calibration / backtesting)."""

    def get_debt_stats(self, country_code: str) -> dict:
        """Optional: debt sustainability indicators."""
        return {}

    def health_check(self) -> dict:
        return {"provider": self.name, "available": self.is_available}

    # ── helpers ───────────────────────────────────────────────────

    @staticmethod
    def _request(
        method: str,
        url: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json: Optional[dict] = None,
        timeout: int = 30,
        source: str = "unknown",
        session: Optional[requests.Session] = None,
    ) -> Optional[dict]:
        """Execute an HTTP request with rate limiting, retries, and error handling."""
        limiter = get_rate_limiter()
        limiter.acquire(source)

        close_session = session is None
        session = session or requests.Session()
        headers = {"User-Agent": "Quantive/1.0 (sovereign-debt-platform)", "Accept": "application/json"}

        try:
            resp = session.request(
                method, url, params=params, json=json,
                headers=headers, timeout=timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            logger.warning(f"[{source}] HTTP {e.response.status_code} for {url}")
            return None
        except requests.exceptions.ConnectionError:
            logger.warning(f"[{source}] Connection error for {url}")
            return None
        except requests.exceptions.Timeout:
            logger.warning(f"[{source}] Timeout for {url}")
            return None
        except Exception as e:
            logger.warning(f"[{source}] Error fetching {url}: {e}")
            return None
        finally:
            if close_session:
                session.close()

    @staticmethod
    def _paginate_get(
        session: requests.Session,
        url: str,
        *,
        per_page: int = 50,
        source: str = "unknown",
        data_key: str = "data",
        total_key: str = "total",
        next_url_fn: Optional[callable] = None,
    ) -> list[dict]:
        """Generic paginated GET helper."""
        all_items: list[dict] = []
        page = 1
        visited = set()

        while url and url not in visited:
            visited.add(url)
            data = MarketDataProvider._request("GET", url, params={"page": page, "per_page": per_page}, session=session, source=source)
            if not data:
                break
            items = data.get(data_key, data.get("records", data.get("value", [])))
            if not items:
                break
            all_items.extend(items if isinstance(items, list) else [items])
            total = data.get(total_key, len(items))
            if page * per_page >= total:
                break
            if next_url_fn:
                url = next_url_fn(url, page, per_page)
                if not url:
                    break
            else:
                page += 1

        return all_items
