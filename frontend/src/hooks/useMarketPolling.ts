// ── useMarketPolling Hook ─────────────────────────────────────────────
// Provides 3-second auto-refresh polling with stale data detection,
// browser tab visibility handling, and error recovery.

import { useState, useEffect, useCallback, useRef } from 'react';
import { isDataStale } from '../lib/marketValidation';
import { setCache, getCache, getCacheAge } from '../lib/marketCache';

interface PollingOptions {
  /** Polling interval in milliseconds (default: 3000) */
  intervalMs?: number;
  /** Maximum data age before marking as stale (default: 10000) */
  staleThresholdMs?: number;
  /** Cache key for storing results (default: auto-generated) */
  cacheKey?: string;
  /** Cache TTL in milliseconds (default: 30000) */
  cacheTtlMs?: number;
  /** Whether to pause polling when tab is hidden (default: true) */
  pauseOnHidden?: boolean;
  /** Whether polling is enabled (default: true) */
  enabled?: boolean;
  /** Maximum consecutive failures before stopping (default: 5) */
  maxFailures?: number;
}

interface PollingState<T> {
  data: T | null;
  error: Error | null;
  isLoading: boolean;
  isStale: boolean;
  lastUpdated: number | null;
  provider: string;
  failureCount: number;
}

interface PollingActions {
  refresh: () => Promise<void>;
  pause: () => void;
  resume: () => void;
  clearError: () => void;
}

type UseMarketPollingResult<T> = PollingState<T> & PollingActions;

export function useMarketPolling<T>(
  fetchFn: () => Promise<T & { provider?: string }>,
  options: PollingOptions = {}
): UseMarketPollingResult<T> {
  const {
    intervalMs = 3000,
    staleThresholdMs = 10000,
    cacheKey,
    cacheTtlMs = 30000,
    pauseOnHidden = true,
    enabled = true,
    maxFailures = 5,
  } = options;

  const [state, setState] = useState<PollingState<T>>({
    data: null,
    error: null,
    isLoading: true,
    isStale: true,
    lastUpdated: null,
    provider: '',
    failureCount: 0,
  });

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const isPausedRef = useRef(false);
  const mountedRef = useRef(true);

  const doFetch = useCallback(async () => {
    if (!mountedRef.current) return;

    try {
      const result = await fetchFn();
      if (!mountedRef.current) return;

      const provider = (result as Record<string, unknown>).provider as string || 'unknown';

      setState((prev) => ({
        ...prev,
        data: result,
        error: null,
        isLoading: false,
        isStale: false,
        lastUpdated: Date.now(),
        provider,
        failureCount: 0,
      }));

      // Cache the result
      if (cacheKey) {
        setCache(cacheKey, result, cacheTtlMs);
      }
    } catch (err) {
      if (!mountedRef.current) return;

      setState((prev) => {
        const newFailureCount = prev.failureCount + 1;
        return {
          ...prev,
          error: err instanceof Error ? err : new Error(String(err)),
          isLoading: false,
          failureCount: newFailureCount,
        };
      });
    }
  }, [fetchFn, cacheKey, cacheTtlMs]);

  const refresh = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true }));
    await doFetch();
  }, [doFetch]);

  const pause = useCallback(() => {
    isPausedRef.current = true;
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const resume = useCallback(() => {
    isPausedRef.current = false;
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    // Immediate fetch on resume
    doFetch();
    timerRef.current = setInterval(doFetch, intervalMs);
  }, [doFetch, intervalMs]);

  const clearError = useCallback(() => {
    setState((prev) => ({ ...prev, error: null }));
  }, []);

  // Initial fetch and polling setup
  useEffect(() => {
    mountedRef.current = true;

    if (!enabled) return;

    // Load from cache first
    if (cacheKey) {
      const cached = getCache<T>(cacheKey);
      if (cached) {
        const age = getCacheAge(cacheKey);
        setState((prev) => ({
          ...prev,
          data: cached,
          isLoading: false,
          isStale: age !== null && age > staleThresholdMs,
          lastUpdated: age !== null ? Date.now() - age : null,
          provider: 'cache',
        }));
      }
    }

    // Initial fetch
    doFetch();

    // Start polling
    timerRef.current = setInterval(doFetch, intervalMs);

    return () => {
      mountedRef.current = false;
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [enabled, doFetch, intervalMs, cacheKey, staleThresholdMs]);

  // Browser tab visibility handling
  useEffect(() => {
    if (!pauseOnHidden || !enabled) return;

    const handleVisibilityChange = () => {
      if (document.hidden) {
        pause();
      } else {
        resume();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [pauseOnHidden, enabled, pause, resume]);

  // Stale data check
  useEffect(() => {
    const checkStale = setInterval(() => {
      setState((prev) => {
        if (prev.lastUpdated && isDataStale(prev.lastUpdated, staleThresholdMs)) {
          if (!prev.isStale) return { ...prev, isStale: true };
        }
        return prev;
      });
    }, 5000);

    return () => clearInterval(checkStale);
  }, [staleThresholdMs]);

  return {
    ...state,
    refresh,
    pause,
    resume,
    clearError,
  };
}

/**
 * Convenience hook for polling multiple market data sources simultaneously.
 * Uses a single useMarketPolling call with a combined fetcher to avoid
 * violating React's Rules of Hooks.
 */
export function useMarketDataBundle<T extends Record<string, unknown>>(
  fetchers: Record<keyof T, () => Promise<unknown>>,
  options: PollingOptions = {}
): Record<keyof T, UseMarketPollingResult<unknown>> & { overallError: Error | null } {
  const keys = Object.keys(fetchers) as Array<keyof T>;

  const combinedFetcher = useCallback(async () => {
    const results = await Promise.allSettled(
      keys.map((key) => fetchers[key]())
    );
    const combined = {} as Record<string, unknown>;
    const errors: Error[] = [];
    results.forEach((r, i) => {
      if (r.status === 'fulfilled') {
        combined[String(keys[i])] = r.value;
      } else {
        errors.push(r.reason instanceof Error ? r.reason : new Error(String(r.reason)));
      }
    });
    return { ...combined, _bundleErrors: errors } as T & { _bundleErrors: Error[]; provider?: string };
  }, [keys, fetchers]);

  const bundleResult = useMarketPolling(combinedFetcher, options);

  const results = {} as Record<keyof T, UseMarketPollingResult<unknown>>;
  const errors: Error[] = bundleResult.data
    ? ((bundleResult.data as unknown as { _bundleErrors: Error[] })._bundleErrors || [])
    : [];
  if (bundleResult.error) errors.push(bundleResult.error);

  for (const key of keys) {
    results[key] = {
      data: bundleResult.data ? (bundleResult.data as unknown as Record<string, unknown>)[String(key)] as unknown ?? null : null,
      error: bundleResult.error,
      isLoading: bundleResult.isLoading,
      isStale: bundleResult.isStale,
      lastUpdated: bundleResult.lastUpdated,
      provider: bundleResult.provider,
      failureCount: bundleResult.failureCount,
      refresh: bundleResult.refresh,
      pause: bundleResult.pause,
      resume: bundleResult.resume,
      clearError: bundleResult.clearError,
    };
  }

  return {
    ...results,
    overallError: errors.length > 0 ? errors[0] : null,
  };
}
