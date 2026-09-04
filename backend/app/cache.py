"""Caching layer with Redis support and in-memory fallback.

Provides:
- TTL-based caching with get/set/delete
- Cache invalidation by pattern
- Decorator for caching function results
- Stats tracking
"""
import functools
import hashlib
import json
import logging
import os
import threading
import time
from typing import Any, Callable, Optional

logger = logging.getLogger("quantive.cache")


# ── Cache Backend Interface ─────────────────────────────────────────────

class CacheBackend:
    """Base cache backend interface."""

    def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        raise NotImplementedError

    def delete(self, key: str) -> bool:
        raise NotImplementedError

    def clear(self, pattern: Optional[str] = None) -> int:
        raise NotImplementedError

    def stats(self) -> dict:
        raise NotImplementedError


# ── In-Memory Cache (Development) ──────────────────────────────────────

class InMemoryCache(CacheBackend):
    """Thread-safe in-memory cache with TTL support."""

    def __init__(self):
        self._store: dict[str, tuple[Any, float]] = {}  # key -> (value, expiry)
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None
            value, expiry = entry
            if expiry and time.time() > expiry:
                del self._store[key]
                self._misses += 1
                return None
            self._hits += 1
            return value

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        with self._lock:
            expiry = time.time() + ttl_seconds if ttl_seconds > 0 else 0
            self._store[key] = (value, expiry)

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def clear(self, pattern: Optional[str] = None) -> int:
        with self._lock:
            if pattern is None:
                count = len(self._store)
                self._store.clear()
                return count
            import fnmatch
            keys_to_delete = [k for k in self._store if fnmatch.fnmatch(k, pattern)]
            for k in keys_to_delete:
                del self._store[k]
            return len(keys_to_delete)

    def stats(self) -> dict:
        with self._lock:
            total = self._hits + self._misses
            return {
                "backend": "memory",
                "entries": len(self._store),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": f"{self._hits / total * 100:.1f}%" if total > 0 else "N/A",
            }

    def cleanup_expired(self) -> int:
        """Remove expired entries."""
        now = time.time()
        with self._lock:
            expired = [k for k, (_, exp) in self._store.items() if exp and now > exp]
            for k in expired:
                del self._store[k]
            return len(expired)


# ── Redis Cache (Production) ───────────────────────────────────────────

class RedisCache(CacheBackend):
    """Redis-backed cache for production use."""

    def __init__(self, url: str = "redis://localhost:6379/0", prefix: str = "quantive:"):
        import redis
        self._client = redis.from_url(url, decode_responses=True)
        self._prefix = prefix
        self._hits = 0
        self._misses = 0

    def _key(self, key: str) -> str:
        return f"{self._prefix}{key}"

    def get(self, key: str) -> Optional[Any]:
        raw = self._client.get(self._key(key))
        if raw is None:
            self._misses += 1
            return None
        self._hits += 1
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        serialized = json.dumps(value, default=str)
        if ttl_seconds > 0:
            self._client.setex(self._key(key), ttl_seconds, serialized)
        else:
            self._client.set(self._key(key), serialized)

    def delete(self, key: str) -> bool:
        return bool(self._client.delete(self._key(key)))

    def clear(self, pattern: Optional[str] = None) -> int:
        if pattern is None:
            keys = self._client.keys(f"{self._prefix}*")
        else:
            keys = self._client.keys(self._key(pattern))
        if keys:
            return self._client.delete(*keys)
        return 0

    def stats(self) -> dict:
        total = self._hits + self._misses
        info = self._client.info("memory")
        return {
            "backend": "redis",
            "memory_used": info.get("used_memory_human", "N/A"),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{self._hits / total * 100:.1f}%" if total > 0 else "N/A",
        }


# ── Singleton ───────────────────────────────────────────────────────────

_cache: Optional[CacheBackend] = None


def get_cache() -> CacheBackend:
    """Get the cache backend (Redis in production, in-memory in dev)."""
    global _cache
    if _cache is None:
        redis_url = os.environ.get("REDIS_URL")
        if redis_url:
            try:
                _cache = RedisCache(redis_url)
                logger.info("Using Redis cache backend")
            except Exception as e:
                logger.warning(f"Redis connection failed, falling back to in-memory: {e}")
                _cache = InMemoryCache()
        else:
            _cache = InMemoryCache()
            logger.info("Using in-memory cache backend (set REDIS_URL for production)")
    return _cache


# ── Cache Decorator ─────────────────────────────────────────────────────

def cached(ttl_seconds: int = 300, key_prefix: str = ""):
    """Decorator to cache function results.

    Usage:
        @cached(ttl_seconds=60, key_prefix="portfolio")
        def get_portfolio_analytics(portfolio_id: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache()

            # Build cache key from function name + args
            key_data = f"{key_prefix or func.__name__}:{args}:{sorted(kwargs.items())}"
            cache_key = hashlib.sha256(key_data.encode()).hexdigest()

            # Try cache
            result = cache.get(cache_key)
            if result is not None:
                return result

            # Compute and cache
            result = func(*args, **kwargs)
            if result is not None:
                cache.set(cache_key, result, ttl_seconds=ttl_seconds)
            return result

        wrapper.invalidate = lambda *a, **kw: get_cache().delete(
            hashlib.sha256(f"{key_prefix or func.__name__}:{a}:{sorted(kw.items())}".encode()).hexdigest()
        )
        wrapper.cache_clear = lambda: get_cache().clear(f"{key_prefix or func.__name__}*")
        return wrapper

    return decorator


# ── Convenience Functions ───────────────────────────────────────────────

def cache_market_data(key: str, data: Any, ttl: int = 300) -> None:
    """Cache market data (yield curves, FX rates, etc.)."""
    get_cache().set(f"market:{key}", data, ttl_seconds=ttl)


def get_cached_market_data(key: str) -> Optional[Any]:
    """Get cached market data."""
    return get_cache().get(f"market:{key}")


def invalidate_portfolio_cache(portfolio_id: str) -> None:
    """Invalidate all cache entries for a portfolio."""
    cache = get_cache()
    cache.clear(f"portfolio:{portfolio_id}*")
    cache.clear(f"analytics:{portfolio_id}*")
    cache.clear(f"risk:{portfolio_id}*")


def cache_optimization_result(job_id: str, result: Any, ttl: int = 600) -> None:
    """Cache optimization results for 10 minutes."""
    get_cache().set(f"optimization:{job_id}", result, ttl_seconds=ttl)


def get_cached_optimization(job_id: str) -> Optional[Any]:
    """Get cached optimization result."""
    return get_cache().get(f"optimization:{job_id}")
