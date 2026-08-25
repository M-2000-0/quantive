"""TTL cache for market data to avoid hitting free APIs too often.

Free APIs have rate limits. This cache stores results with configurable TTL:
- FX rates: 5 minutes
- Yield curves: 1 hour (updated daily by source)
- Interest rates: 1 hour
- Economic indicators: 24 hours
"""
import threading
import time
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class CacheEntry:
    data: Any
    fetched_at: float
    ttl_seconds: int

    @property
    def is_expired(self) -> bool:
        return time.time() - self.fetched_at > self.ttl_seconds

    @property
    def age_seconds(self) -> float:
        return time.time() - self.fetched_at


class MarketDataCache:
    """Thread-safe TTL cache for market data."""

    def __init__(self):
        self._store: dict[str, CacheEntry] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """Get cached data if not expired."""
        with self._lock:
            entry = self._store.get(key)
            if entry and not entry.is_expired:
                return entry.data
            return None

    def set(self, key: str, data: Any, ttl_seconds: int):
        """Store data with TTL."""
        with self._lock:
            self._store[key] = CacheEntry(
                data=data,
                fetched_at=time.time(),
                ttl_seconds=ttl_seconds,
            )

    def invalidate(self, key: str):
        """Remove a specific cache entry."""
        with self._lock:
            self._store.pop(key, None)

    def clear(self):
        """Clear all cached data."""
        with self._lock:
            self._store.clear()

    def stats(self) -> dict:
        """Get cache statistics."""
        with self._lock:
            total = len(self._store)
            expired = sum(1 for e in self._store.values() if e.is_expired)
            return {
                "total_entries": total,
                "active_entries": total - expired,
                "expired_entries": expired,
                "keys": list(self._store.keys()),
            }


# TTL constants (seconds)
TTL_FX_RATES = 5 * 60          # 5 minutes — FX changes frequently
TTL_YIELD_CURVE = 60 * 60      # 1 hour — updated daily by Treasury
TTL_INTEREST_RATES = 60 * 60   # 1 hour
TTL_ECONOMIC_INDICATORS = 24 * 60 * 60  # 24 hours — slow-moving data
TTL_BOND_PRICES = 5 * 60       # 5 minutes


# Singleton
_cache: Optional[MarketDataCache] = None


def get_cache() -> MarketDataCache:
    global _cache
    if _cache is None:
        _cache = MarketDataCache()
    return _cache
