// ── Market Data Cache Service ─────────────────────────────────────────
// Provides localStorage + in-memory caching with TTL for offline fallback.

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  ttl: number;
}

const MEMORY_CACHE = new Map<string, CacheEntry<unknown>>();
const PREFIX = 'quantive_market_cache_';

export function setCache<T>(key: string, data: T, ttlMs: number = 30000): void {
  const entry: CacheEntry<T> = { data, timestamp: Date.now(), ttl: ttlMs };
  MEMORY_CACHE.set(key, entry);
  try {
    localStorage.setItem(PREFIX + key, JSON.stringify(entry));
  } catch {
    // localStorage full or unavailable — memory cache still works
  }
}

export function getCache<T>(key: string): T | null {
  // Try memory cache first (fastest)
  const memEntry = MEMORY_CACHE.get(key) as CacheEntry<T> | undefined;
  if (memEntry && Date.now() - memEntry.timestamp < memEntry.ttl) {
    return memEntry.data;
  }

  // Fallback to localStorage
  try {
    const raw = localStorage.getItem(PREFIX + key);
    if (raw) {
      const entry: CacheEntry<T> = JSON.parse(raw);
      if (Date.now() - entry.timestamp < entry.ttl) {
        MEMORY_CACHE.set(key, entry); // warm memory cache
        return entry.data;
      }
      localStorage.removeItem(PREFIX + key);
    }
  } catch {
    // corrupted cache entry
  }

  return null;
}

export function getCacheAge(key: string): number | null {
  const entry = MEMORY_CACHE.get(key);
  if (!entry) {
    try {
      const raw = localStorage.getItem(PREFIX + key);
      if (raw) {
        const parsed: CacheEntry<unknown> = JSON.parse(raw);
        return Date.now() - parsed.timestamp;
      }
    } catch {
      // ignore
    }
    return null;
  }
  return Date.now() - entry.timestamp;
}

export function clearCache(key?: string): void {
  if (key) {
    MEMORY_CACHE.delete(key);
    try { localStorage.removeItem(PREFIX + key); } catch { /* ignore */ }
  } else {
    MEMORY_CACHE.clear();
    try {
      const keys = Object.keys(localStorage).filter((k) => k.startsWith(PREFIX));
      keys.forEach((k) => localStorage.removeItem(k));
    } catch {
      // ignore
    }
  }
}

export function isCacheStale(key: string, maxAgeMs: number = 10000): boolean {
  const age = getCacheAge(key);
  return age === null || age > maxAgeMs;
}
