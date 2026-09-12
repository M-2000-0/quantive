import { useCallback, useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { api } from '../api';
import type { Portfolio, RiskSummary } from '../types';
import RiskDashboard from '../components/RiskDashboard';

function formatCurrency(value: number): string {
  if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `$${(value / 1e3).toFixed(1)}K`;
  return `$${value.toFixed(0)}`;
}

export default function RiskDashboardPage() {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [selectedId, setSelectedId] = useState<string>('');
  const [summary, setSummary] = useState<RiskSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadPortfolios = useCallback(async () => {
    const res = (await api.portfolios.list({ page_size: 20 })) as unknown as
      | Portfolio[]
      | { data: Portfolio[] };
    const list = Array.isArray(res) ? res : (res.data ?? []);
    setPortfolios(list);
    if (list.length > 0 && !selectedId) setSelectedId(list[0].id);
    return list;
  }, [selectedId]);

  const loadSummary = useCallback(async (portfolioId: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.portfolios.riskSummary(portfolioId);
      setSummary(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load risk summary');
      setSummary(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadPortfolios().catch((e: Error) => {
      setError(e.message);
      setLoading(false);
    });
  }, [loadPortfolios]);

  useEffect(() => {
    if (selectedId) void loadSummary(selectedId);
  }, [selectedId, loadSummary]);

  const topDrivers = summary
    ? Object.entries(summary.risk_score.components)
        .sort((a, b) => b[1].score * b[1].weight - a[1].score * a[1].weight)
        .slice(0, 3)
    : [];

  const var95 = summary?.var_analysis.find((v) => v.confidence >= 0.949 && v.confidence <= 0.951)
    ?? summary?.var_analysis[0];
  const var99 = summary?.var_analysis.find((v) => v.confidence >= 0.989);

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, margin: 0 }}>Risk Dashboard</h1>
        <p style={{ fontSize: 13, color: '#6b7280', margin: '4px 0 0' }}>
          Portfolio risk score, value-at-risk, and top drivers — in plain English.
        </p>
      </div>

      {/* ── MVP: portfolio-driven risk explanation ── */}
      <section className="panel" style={{ padding: 20, marginBottom: 20 }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 16, flexWrap: 'wrap' }}>
          <label htmlFor="risk-portfolio" style={{ fontSize: 13, fontWeight: 600 }}>Portfolio</label>
          <select
            id="risk-portfolio"
            value={selectedId}
            onChange={(e) => setSelectedId(e.target.value)}
            style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 13 }}
          >
            {portfolios.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          {portfolios.length === 0 && !loading && (
            <span style={{ fontSize: 13, color: '#6b7280' }}>No portfolios yet — create one to see risk.</span>
          )}
        </div>

        {loading ? (
          <div style={{ padding: 24, textAlign: 'center', color: '#6b7280' }}>
            <Loader2 size={24} style={{ animation: 'spin 1s linear infinite' }} />
            <p>Loading risk summary...</p>
          </div>
        ) : error ? (
          <div style={{ textAlign: 'center', padding: 16 }}>
            <p style={{ color: '#dc2626', marginBottom: 8 }}>{error}</p>
            <button type="button" onClick={() => selectedId && void loadSummary(selectedId)} style={{ padding: '8px 20px', borderRadius: 8, border: '1px solid #e5e7eb', background: '#fff', cursor: 'pointer' }}>
              Retry
            </button>
          </div>
        ) : summary ? (
          <div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12, marginBottom: 16 }}>
              <div style={{ padding: 16, borderRadius: 12, background: '#f8fafc', border: '1px solid #e5e7eb' }}>
                <div style={{ fontSize: 12, color: '#6b7280' }}>Risk score</div>
                <div style={{ fontSize: 28, fontWeight: 700 }}>{summary.risk_score.score.toFixed(1)} / 10</div>
                <div style={{ fontSize: 12, fontWeight: 600 }}>{summary.risk_score.label}</div>
              </div>
              <div style={{ padding: 16, borderRadius: 12, background: '#f8fafc', border: '1px solid #e5e7eb' }}>
                <div style={{ fontSize: 12, color: '#6b7280' }}>VaR 95% (1yr)</div>
                <div style={{ fontSize: 20, fontWeight: 700 }}>
                  {var95 ? formatCurrency(var95.var_amount) : '—'}
                </div>
                <div style={{ fontSize: 12, color: '#6b7280' }}>
                  {var95 ? `${(var95.var_pct * 100).toFixed(1)}% of portfolio` : 'No VaR data'}
                </div>
              </div>
              <div style={{ padding: 16, borderRadius: 12, background: '#f8fafc', border: '1px solid #e5e7eb' }}>
                <div style={{ fontSize: 12, color: '#6b7280' }}>CVaR 99% (tail loss)</div>
                <div style={{ fontSize: 20, fontWeight: 700 }}>
                  {var99 ? formatCurrency(var99.cvar_amount) : var95 ? formatCurrency(var95.cvar_amount) : '—'}
                </div>
                <div style={{ fontSize: 12, color: '#6b7280' }}>Expected loss beyond VaR</div>
              </div>
            </div>

            <h3 style={{ fontSize: 14, fontWeight: 700, margin: '0 0 8px' }}>Top 3 risk drivers</h3>
            {topDrivers.length === 0 ? (
              <p style={{ fontSize: 13, color: '#6b7280' }}>No driver breakdown available.</p>
            ) : (
              <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13 }}>
                {topDrivers.map(([name, c]) => (
                  <li key={name} style={{ marginBottom: 4 }}>
                    <strong style={{ textTransform: 'capitalize' }}>{name.replace(/_/g, ' ')}</strong>
                    {' — '}{c.description}
                  </li>
                ))}
              </ul>
            )}

            {summary.risk_score.recommendations.length > 0 && (
              <>
                <h3 style={{ fontSize: 14, fontWeight: 700, margin: '16px 0 8px' }}>What to do next</h3>
                <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13 }}>
                  {summary.risk_score.recommendations.slice(0, 3).map((r, i) => (
                    <li key={i} style={{ marginBottom: 4 }}>{r}</li>
                  ))}
                </ul>
              </>
            )}
          </div>
        ) : null}
      </section>

      <RiskDashboard />
    </div>
  );
}
