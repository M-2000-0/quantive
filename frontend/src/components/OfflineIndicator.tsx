// ── Offline Indicator Component ────────────────────────────────────────
// Shows a persistent banner when all market data providers are down
// and only cached data is available.

import { useState, useEffect } from 'react';
import { getProviderStatus } from '../lib/marketProviders';
import { getCacheAge, clearCache } from '../lib/marketCache';

interface OfflineIndicatorProps {
  /** Whether data is currently being served from cache */
  isFromCache?: boolean;
  /** Cache key to check age for */
  cacheKey?: string;
  /** Callback to retry fetching fresh data */
  onRetry?: () => void;
  /** Callback to clear cache and retry */
  onClearCache?: () => void;
}

export default function OfflineIndicator({
  isFromCache = false,
  cacheKey,
  onRetry,
  onClearCache }: OfflineIndicatorProps) {
  const [providerStatus, setProviderStatus] = useState(() => getProviderStatus());
  const [cacheAge, setCacheAge] = useState<number | null>(null);
  const [isRetrying, setIsRetrying] = useState(false);

  const allProvidersDown = Object.values(providerStatus).every((p) => !p.ready);

  useEffect(() => {
    // Refresh provider status every 10 seconds
    const interval = setInterval(() => {
      setProviderStatus(getProviderStatus());
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!cacheKey) return;
    const interval = setInterval(() => {
      setCacheAge(getCacheAge(cacheKey));
    }, 5000);
    setCacheAge(getCacheAge(cacheKey));
    return () => clearInterval(interval);
  }, [cacheKey]);

  const handleRetry = async () => {
    setIsRetrying(true);
    onRetry?.();
    // Reset after 3 seconds
    setTimeout(() => setIsRetrying(false), 3000);
  };

  const handleClearCache = () => {
    clearCache(cacheKey);
    onClearCache?.();
    onRetry?.();
  };

  const formatAge = (ms: number): string => {
    if (ms < 1000) return 'just now';
    if (ms < 60000) return `${Math.floor(ms / 1000)}s ago`;
    if (ms < 3600000) return `${Math.floor(ms / 60000)}m ago`;
    return `${Math.floor(ms / 3600000)}h ago`;
  };

  // Only show when providers are down OR serving from cache
  if (!allProvidersDown && !isFromCache) return null;

  return (
    <div className="glass rounded-xl border border-amber-200/50 bg-amber-50/30 p-4 mb-4 animate-glass-in">
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <div className="text-2xl">{allProvidersDown ? '📡' : '💾'}</div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h3 className="text-sm font-bold text-amber-800">
                {allProvidersDown ? 'All Providers Unavailable' : 'Serving Cached Data'}
              </h3>
              {cacheAge !== null && (
                <span className="text-[10px] font-mono text-amber-600 bg-amber-100 px-2 py-0.5 rounded">
                  Cache age: {formatAge(cacheAge)}
                </span>
              )}
            </div>
            <p className="text-xs text-amber-700 mb-3">
              {allProvidersDown
                ? 'Market data providers (Yahoo, Polygon, Alpha Vantage) are unreachable. Showing cached data where available.'
                : 'Live data temporarily unavailable. Displaying cached data from the last successful fetch.'}
            </p>

            {/* Provider Status Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3">
              {Object.entries(providerStatus).map(([name, status]) => (
                <div
                  key={name}
                  className={`flex items-center gap-1.5 px-2 py-1 rounded-lg text-[10px] font-medium ${
                    status.ready
                      ? 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200'
                      : 'bg-red-50 text-red-700 ring-1 ring-red-200'
                  }`}
                >
                  <span>{status.ready ? 'CheckCircle' : 'XCircle'}</span>
                  <span className="capitalize">{name}</span>
                  <span className="text-slate-400 ml-auto">{status.remaining}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleRetry}
            disabled={isRetrying}
            className="px-3 py-1.5 text-xs font-medium rounded-lg bg-amber-600/14 text-amber-700 hover:bg-amber-600/20 transition-all disabled:opacity-50"
          >
            {isRetrying ? (
              <span className="flex items-center gap-1">
                <span className="animate-spin">⏳</span> Retrying...
              </span>
            ) : (
              '↻ Retry Now'
            )}
          </button>
          <button
            onClick={handleClearCache}
            className="px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-100 text-slate-600 hover:bg-slate-200 transition-all"
          >
            Clear Cache
          </button>
        </div>
      </div>
    </div>
  );
}
