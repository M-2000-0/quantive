import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowDownRight,
  ArrowUpRight,
  AlertTriangle,
  CheckCircle,
  Clock,
  ExternalLink,
  Loader2,
  Minus,
  TrendingDown,
  TrendingUp } from 'lucide-react';
import { api } from '../api';

// ── Types ──────────────────────────────────────────────────────────

interface YieldCurveData {
  status: string;
  shape: string;
  signal: string;
  spread_bps: number;
  rate_2y: number;
  rate_10y: number;
  rate_30y: number;
  description: string;
}

interface FxRate {
  currency: string;
  name: string;
  rate: number;
  trend: string;
}

interface InterestRateData {
  environment: string;
  signal: string;
  avg_rate_pct: number;
  description: string;
  key_rates: Array<{ name: string; rate_pct: number }>;
}

interface RefinancingWindow {
  id: string;
  title: string;
  description: string;
  urgency: string;
  estimated_savings_pct: number;
  window_days: number;
  action: string;
}

interface MarketPulse {
  overall_signal: string;
  summary: string;
  yield_curve: YieldCurveData;
  fx_rates: FxRate[];
  interest_rates: InterestRateData;
  refinancing_windows: RefinancingWindow[];
  window_count: number;
  urgent_window_count: number;
  fetched_at: string;
}

// ── Helpers ─────────────────────────────────────────────────────────

function signalColor(signal: string): string {
  switch (signal) {
    case 'positive': return '#10b981';
    case 'cautious': return '#f59e0b';
    case 'warning': return '#ef4444';
    default: return '#6b7280';
  }
}

function signalBg(signal: string): string {
  switch (signal) {
    case 'positive': return '#ecfdf5';
    case 'cautious': return '#fffbeb';
    case 'warning': return '#fef2f2';
    default: return '#f9fafb';
  }
}

function signalLabel(signal: string): string {
  switch (signal) {
    case 'positive': return 'Favorable';
    case 'cautious': return 'Mixed';
    case 'warning': return 'Caution';
    default: return 'Neutral';
  }
}

function urgencyColor(urgency: string): string {
  switch (urgency) {
    case 'high': return '#ef4444';
    case 'medium': return '#f59e0b';
    default: return '#6b7280';
  }
}

// ── Component ───────────────────────────────────────────────────────

export default function MarketPulseWidget() {
  const [pulse, setPulse] = useState<MarketPulse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await api.marketPulse.get() as MarketPulse;
        if (!cancelled) setPulse(data);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => { cancelled = true; };
  }, []);

  const handleRefresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.marketPulse.get() as MarketPulse;
      setPulse(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to refresh');
    } finally {
      setLoading(false);
    }
  }, []);

  if (loading && !pulse) {
    return (
      <div style={containerStyle}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 40 }}>
          <Loader2 size={20} style={{ animation: 'spin 1s linear infinite', color: '#6366f1' }} />
        </div>
      </div>
    );
  }

  if (error && !pulse) {
    return (
      <div style={containerStyle}>
        <div style={{ textAlign: 'center', padding: 20, color: '#dc2626', fontSize: 13 }}>{error}</div>
        <div style={{ textAlign: 'center', paddingBottom: 16 }}>
          <button
            type="button"
            onClick={() => void handleRefresh()}
            style={{ padding: '6px 16px', borderRadius: 8, border: '1px solid #e5e7eb', background: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 500 }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!pulse) return null;

  return (
    <div className="market-pulse-widget" style={containerStyle}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, color: '#111827', margin: 0 }}>Market Pulse</h3>
          <span
            style={{
              fontSize: 11,
              fontWeight: 600,
              padding: '2px 8px',
              borderRadius: 99,
              background: signalBg(pulse.overall_signal),
              color: signalColor(pulse.overall_signal) }}
          >
            {signalLabel(pulse.overall_signal)}
          </span>
        </div>
        <button
          type="button"
          onClick={handleRefresh}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#6b7280', fontSize: 12 }}
        >
          ↻ Refresh
        </button>
      </div>

      {/* Summary */}
      <p style={{ fontSize: 13, color: '#6b7280', marginBottom: 16, lineHeight: 1.5 }}>
        {pulse.summary}
      </p>

      {/* Yield Curve */}
      <div style={sectionStyle}>
        <div style={sectionHeaderStyle}>
          <span style={sectionTitleStyle}>Yield Curve</span>
          <YieldCurveBadge shape={pulse.yield_curve.shape} />
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 8 }}>
          <MiniStat label="2Y" value={`${pulse.yield_curve.rate_2y}%`} />
          <MiniStat label="10Y" value={`${pulse.yield_curve.rate_10y}%`} />
          <MiniStat label="Spread" value={`${pulse.yield_curve.spread_bps}bps`} />
        </div>
        <p style={{ fontSize: 11, color: '#9ca3af', lineHeight: 1.4 }}>
          {pulse.yield_curve.description}
        </p>
      </div>

      {/* FX Rates */}
      <div style={sectionStyle}>
        <div style={sectionHeaderStyle}>
          <span style={sectionTitleStyle}>FX Rates</span>
          <span style={{ fontSize: 11, color: '#9ca3af' }}>vs USD</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
          {pulse.fx_rates.slice(0, 6).map((fx) => (
            <div key={fx.currency} style={fxRowStyle}>
              <span style={{ fontWeight: 600, color: '#374151', fontSize: 12 }}>{fx.currency}</span>
              <span style={{ fontSize: 12, color: '#6b7280' }}>{fx.rate.toFixed(2)}</span>
              <TrendIcon trend={fx.trend} />
            </div>
          ))}
        </div>
      </div>

      {/* Interest Rates */}
      <div style={sectionStyle}>
        <div style={sectionHeaderStyle}>
          <span style={sectionTitleStyle}>Central Bank Rates</span>
          <span
            style={{
              fontSize: 10,
              fontWeight: 600,
              padding: '2px 6px',
              borderRadius: 4,
              background: signalBg(pulse.interest_rates.signal),
              color: signalColor(pulse.interest_rates.signal),
              textTransform: 'uppercase' }}
          >
            {pulse.interest_rates.environment}
          </span>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {pulse.interest_rates.key_rates.slice(0, 4).map((r) => (
            <span key={r.name} style={ratePillStyle}>
              {r.name}: {r.rate_pct}%
            </span>
          ))}
        </div>
      </div>

      {/* Refinancing Windows */}
      {pulse.refinancing_windows.length > 0 && (
        <div style={{ ...sectionStyle, background: '#fffbeb', border: '1px solid #fde68a' }}>
          <div style={sectionHeaderStyle}>
            <span style={{ ...sectionTitleStyle, color: '#92400e' }}>Refinancing Windows</span>
            {pulse.urgent_window_count > 0 && (
              <span style={{ fontSize: 11, fontWeight: 600, color: '#dc2626' }}>
                {pulse.urgent_window_count} urgent
              </span>
            )}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {pulse.refinancing_windows.map((w) => (
              <div key={w.id} style={windowCardStyle}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, color: '#111827', fontSize: 13 }}>{w.title}</span>
                  <span style={{ fontSize: 10, color: urgencyColor(w.urgency), fontWeight: 600, textTransform: 'uppercase' }}>
                    {w.urgency}
                  </span>
                </div>
                <p style={{ fontSize: 12, color: '#6b7280', lineHeight: 1.4, margin: 0 }}>
                  {w.description}
                </p>
                <div style={{ display: 'flex', gap: 12, marginTop: 6, fontSize: 11, color: '#92400e' }}>
                  <span>Savings: ~{w.estimated_savings_pct}%</span>
                  <span>Window: {w.window_days} days</span>
                </div>
                <Link
                  to="/optimizations/new"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 4,
                    marginTop: 8,
                    fontSize: 12,
                    fontWeight: 600,
                    color: '#6366f1',
                    textDecoration: 'none' }}
                >
                  {w.action} →
                </Link>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Footer */}
      <div style={{ marginTop: 12, fontSize: 11, color: '#9ca3af', textAlign: 'center' }}>
        Last updated: {new Date(pulse.fetched_at).toLocaleTimeString()}
      </div>
    </div>
  );
}

// ── Sub-components ───────────────────────────────────────────────

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ fontSize: 10, color: '#9ca3af', marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 14, fontWeight: 700, color: '#111827' }}>{value}</div>
    </div>
  );
}

function YieldCurveBadge({ shape }: { shape: string }) {
  const colors: Record<string, { bg: string; fg: string }> = {
    inverted: { bg: '#fef2f2', fg: '#dc2626' },
    flat: { bg: '#fffbeb', fg: '#d97706' },
    normal: { bg: '#ecfdf5', fg: '#059669' },
    steep: { bg: '#eef2ff', fg: '#4f46e5' },
    unknown: { bg: '#f9fafb', fg: '#6b7280' } };
  const c = colors[shape] || colors.unknown;
  return (
    <span style={{ fontSize: 10, fontWeight: 600, padding: '2px 6px', borderRadius: 4, background: c.bg, color: c.fg, textTransform: 'uppercase' }}>
      {shape}
    </span>
  );
}

function TrendIcon({ trend }: { trend: string }) {
  switch (trend) {
    case 'strengthening':
      return <TrendingUp size={12} color="#10b981" />;
    case 'weakening':
      return <TrendingDown size={12} color="#ef4444" />;
    case 'volatile':
      return <AlertTriangle size={12} color="#f59e0b" />;
    default:
      return <Minus size={12} color="#9ca3af" />;
  }
}

// ── Styles ───────────────────────────────────────────────────────

const containerStyle: React.CSSProperties = {
  background: '#fff',
  borderRadius: 12,
  padding: 20,
  border: '1px solid #e5e7eb' };

const sectionStyle: React.CSSProperties = {
  padding: 12,
  background: '#f9fafb',
  borderRadius: 8,
  marginBottom: 10 };

const sectionHeaderStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: 8 };

const sectionTitleStyle: React.CSSProperties = {
  fontSize: 13,
  fontWeight: 600,
  color: '#374151' };

const fxRowStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '4px 8px',
  background: '#fff',
  borderRadius: 6 };

const ratePillStyle: React.CSSProperties = {
  fontSize: 11,
  padding: '3px 8px',
  borderRadius: 6,
  background: '#fff',
  color: '#374151',
  border: '1px solid #e5e7eb' };

const windowCardStyle: React.CSSProperties = {
  background: '#fff',
  padding: 12,
  borderRadius: 8,
  border: '1px solid #fde68a' };
