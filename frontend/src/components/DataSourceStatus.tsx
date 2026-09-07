import { useState, useCallback } from 'react';
import { api } from '../api';
import Card, { CardHeader } from './ui/Card';
import Badge from './ui/Badge';
import Button from './ui/Button';

interface SourceInfo {
  name: string;
  provider: string;
  url: string;
  status: string;
  latency_ms: number | null;
  last_value: string | null;
  error: string | null;
  tested_at: string;
}

interface HealthResponse {
  status: string;
  summary: {
    live: number;
    fallback: number;
    error: number;
    total: number;
    avg_latency_ms: number;
  };
  sources: SourceInfo[];
}

const STATUS_CONFIG: Record<string, { label: string; color: string; dot: string; bg: string }> = {
  live: { label: 'LIVE', color: 'text-emerald-700', dot: 'bg-emerald-500', bg: 'bg-emerald-500/12 border-emerald-500/20' },
  fallback: { label: 'FALLBACK', color: 'text-amber-700', dot: 'bg-amber-500', bg: 'bg-amber-500/12 border-amber-500/20' },
  error: { label: 'ERROR', color: 'text-red-700', dot: 'bg-red-500', bg: 'bg-red-500/12 border-red-500/20' } };

function SourceCard({ source, onTest, testing }: { source: SourceInfo; onTest: (name: string) => void; testing: string | null }) {
  const config = STATUS_CONFIG[source.status] || STATUS_CONFIG.error;
  const isTestingThis = testing === source.name;

  return (
    <div className="bg-white/50 backdrop-blur-xl border border-white/60 rounded-2xl p-4 hover:shadow-lg transition-all">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`w-2 h-2 rounded-full ${config.dot} ${source.status === 'live' ? 'animate-pulse' : ''}`} />
            <h4 className="text-sm font-bold text-slate-900 truncate">{source.provider}</h4>
          </div>
          <p className="text-[11px] text-slate-500 truncate">{source.url}</p>
        </div>
        <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold border ${config.bg} ${config.color}`}>
          {config.label}
        </span>
      </div>

      {/* Last value */}
      {source.last_value && (
        <div className="mb-3 bg-slate-50/80 rounded-lg px-3 py-2">
          <p className="text-[11px] text-slate-500">Last Value</p>
          <p className="text-sm font-bold text-slate-900 tabular-nums">{source.last_value}</p>
        </div>
      )}

      {/* Error */}
      {source.error && (
        <div className="mb-3 bg-red-50/80 rounded-lg px-3 py-2">
          <p className="text-[11px] text-red-500 font-medium">Error</p>
          <p className="text-xs text-red-700 truncate">{source.error}</p>
        </div>
      )}

      {/* Latency + test */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {source.latency_ms !== null && (
            <span className="text-[11px] text-slate-400 tabular-nums">
              {source.latency_ms}ms
            </span>
          )}
          {source.tested_at && (
            <span className="text-[10px] text-slate-400">
              {new Date(source.tested_at).toLocaleTimeString()}
            </span>
          )}
        </div>
        <button
          onClick={() => onTest(source.name)}
          disabled={isTestingThis}
          className="text-[11px] font-medium text-blue-600 hover:text-blue-800 disabled:text-slate-400 transition-colors"
        >
          {isTestingThis ? (
            <span className="flex items-center gap-1">
              <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Testing...
            </span>
          ) : (
            'Test Now'
          )}
        </button>
      </div>
    </div>
  );
}

export default function DataSourceStatus() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const runHealthCheck = useCallback(async () => {
    setLoading(true);
    try {
      const result = await api.marketHealth.checkAll();
      setHealth(result);
      setLastChecked(new Date());
    } catch {
      // Silently handle — user can retry
    } finally {
      setLoading(false);
    }
  }, []);

  const testSingleSource = useCallback(async (sourceName: string) => {
    setTesting(sourceName);
    try {
      const result = await api.marketHealth.checkSource(sourceName);
      setHealth((prev) => {
        if (!prev) return null;
        return {
          ...prev,
          sources: prev.sources.map((s) => (s.name === sourceName ? result : s)),
          summary: {
            ...prev.summary,
            live: prev.sources.filter((s) => (s.name === sourceName ? result : s).status === 'live').length,
            fallback: prev.sources.filter((s) => (s.name === sourceName ? result : s).status === 'fallback').length,
            error: prev.sources.filter((s) => (s.name === sourceName ? result : s).status === 'error').length } };
      });
    } catch {
      // Silently handle
    } finally {
      setTesting(null);
    }
  }, []);

  return (
    <Card padding={false}>
      <div className="px-6 py-4 border-b border-white/40 bg-white/20 backdrop-blur-xl flex items-center justify-between rounded-t-[20px]">
        <div>
          <CardHeader
            title="Data Source Health"
            subtitle={
              health
                ? `${health.summary.live} live · ${health.summary.fallback} fallback · ${health.summary.error} error · Avg ${health.summary.avg_latency_ms}ms`
                : 'Click to ping all market data sources'
            }
          />
        </div>
        <div className="flex items-center gap-2">
          {lastChecked && (
            <span className="text-[11px] text-slate-400">
              Checked {lastChecked.toLocaleTimeString()}
            </span>
          )}
          <Button
            variant={health ? 'secondary' : 'primary'}
            size="sm"
            onClick={runHealthCheck}
            disabled={loading}
          >
            {loading ? (
              <span className="flex items-center gap-1.5">
                <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Testing...
              </span>
            ) : health ? (
              '↻ Re-test All'
            ) : (
              '▶ Test All Sources'
            )}
          </Button>
        </div>
      </div>

      {health && (
        <div className="p-6">
          {/* Summary bar */}
          <div className="flex items-center gap-4 mb-5">
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              <span className="text-xs font-medium text-slate-600">{health.summary.live} Live</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-amber-500" />
              <span className="text-xs font-medium text-slate-600">{health.summary.fallback} Fallback</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-red-500" />
              <span className="text-xs font-medium text-slate-600">{health.summary.error} Error</span>
            </div>
            <div className="ml-auto flex items-center gap-2">
              <span className="text-xs text-slate-400">Avg Latency</span>
              <Badge variant={health.summary.avg_latency_ms < 500 ? 'success' : health.summary.avg_latency_ms < 2000 ? 'warning' : 'danger'}>
                {health.summary.avg_latency_ms}ms
              </Badge>
            </div>
          </div>

          {/* Source cards grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {health.sources.map((source) => (
              <SourceCard
                key={source.name}
                source={source}
                onTest={testSingleSource}
                testing={testing}
              />
            ))}
          </div>
        </div>
      )}

      {!health && !loading && (
        <div className="p-8 text-center">
          <p className="text-sm text-slate-400 mb-3">No health check data yet</p>
          <p className="text-xs text-slate-400">Click "Test All Sources" to ping each data provider and see live vs fallback status</p>
        </div>
      )}
    </Card>
  );
}
