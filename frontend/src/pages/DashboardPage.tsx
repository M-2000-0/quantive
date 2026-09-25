import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowUpRight, ChevronRight, Loader2, Wallet } from 'lucide-react';
import { api } from '../api';
import type { DashboardSummary, DashboardTask } from '../types';
import AssetTracker from '../components/AssetTracker';
import DailyBriefing from '../components/DailyBriefing';
import FirstRunWizard from '../components/FirstRunWizard';
import MarketPulseWidget from '../components/MarketPulseWidget';
import SavingsDashboard from '../components/SavingsDashboard';
import WhatIfPanel from '../components/WhatIfPanel';

function formatCurrency(value: number): string {
  if (value >= 1e12) return `$${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `$${(value / 1e3).toFixed(1)}K`;
  return `$${value.toFixed(0)}`;
}

function riskColor(score: number): string {
  if (score >= 75) return 'red';
  if (score >= 50) return 'blue';
  return 'green';
}

function riskLabel(score: number): string {
  const c = riskColor(score);
  return c === 'red' ? 'High' : c === 'blue' ? 'Medium' : 'Low';
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [tasks, setTasks] = useState<DashboardTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastSync, setLastSync] = useState<Date | null>(null);
  const [marketFetchedAt, setMarketFetchedAt] = useState<Date | null>(null);
  const [marketStale, setMarketStale] = useState(false);
  const [showChartTable, setShowChartTable] = useState(false);
  const [seedingDemo, setSeedingDemo] = useState(false);
  const [params] = useSearchParams();
  const searchQuery = (params.get('q') ?? '').trim().toLowerCase();

  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch core data in parallel so one slow endpoint can't stall the other.
      const [summaryData, tasksData] = await Promise.all([
        api.dashboard.summary(),
        api.dashboard.tasks(),
      ]);
      if (!mountedRef.current) return;
      setSummary(summaryData);
      setTasks(Array.isArray(tasksData) ? tasksData : []);
      setLastSync(new Date());
      // Render the dashboard immediately — market freshness resolves separately
      // and must never block the page (a hung upstream feed previously left
      // the dashboard stuck on "Loading dashboard..." forever).
      setLoading(false);
      try {
        const snap = (await api.market.snapshot()) as unknown as Record<string, unknown>;
        if (!mountedRef.current) return;
        const raw = (snap['fetched_at'] ?? snap['snapshot_time']) as string | undefined;
        if (raw) {
          const dt = new Date(raw);
          setMarketFetchedAt(dt);
          setMarketStale(Date.now() - dt.getTime() > 60 * 60 * 1000);
        }
      } catch {
        // Market feed unavailable — dashboard still shows cached portfolio data
        if (mountedRef.current) setMarketStale(true);
      }
      return;
    } catch (e) {
      if (mountedRef.current) {
        setError(e instanceof Error ? e.message : 'Failed to load dashboard');
      }
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleSeedDemo() {
    setSeedingDemo(true);
    setError(null);
    try {
      await api.firstRun.createDemoPortfolio();
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Demo seed failed');
    } finally {
      setSeedingDemo(false);
    }
  }

  const filteredTasks = useMemo(() => {
    if (!searchQuery) return tasks;
    return tasks.filter((t) =>
      `${t.title} ${t.meta} ${t.status}`.toLowerCase().includes(searchQuery),
    );
  }, [tasks, searchQuery]);

  const stats = summary
    ? [
        { value: formatCurrency(summary.total_debt), label: 'Total debt', tone: 'blue' },
        { value: `${summary.weighted_coupon_pct.toFixed(1)}%`, label: 'Weighted coupon', tone: 'green' },
        { value: `${summary.instrument_count}`, label: 'Instruments', tone: 'slate' },
        { value: `${summary.risk_scores.overall.toFixed(0)} / 100`, label: 'Risk score', tone: riskColor(summary.risk_scores.overall) },
      ]
    : [
        { value: '—', label: 'Total debt', tone: 'blue' },
        { value: '—', label: 'Weighted coupon', tone: 'green' },
        { value: '—', label: 'Instruments', tone: 'slate' },
        { value: '—', label: 'Risk score', tone: 'slate' },
      ];

  const maxPrincipal = summary?.maturity_distribution.length
    ? Math.max(...summary.maturity_distribution.map((b) => b.total_principal))
    : 1;

  const displayTasks = filteredTasks.length > 0
    ? filteredTasks
    : tasks.length > 0 && searchQuery
      ? []
      : [{ title: 'No active tasks', meta: 'All clear', state: 'On track' } as unknown as DashboardTask];

  const keyMetrics = summary
    ? [
        { title: 'Avg maturity', value: `${summary.avg_maturity_years} yr`, trend: summary.avg_maturity_years > 5 ? 'Long-term' : 'Short-term' },
        { title: 'Portfolios', value: `${summary.portfolio_count}`, trend: summary.completed_optimizations > 0 ? `${summary.completed_optimizations} optimized` : 'No optimizations yet' },
        { title: 'Currencies', value: `${summary.currency_count}`, trend: summary.top_currencies[0]?.currency ? `Primary: ${summary.top_currencies[0].currency}` : 'N/A' },
      ]
    : [
        { title: 'Avg maturity', value: '—', trend: 'Loading...' },
        { title: 'Portfolios', value: '—', trend: 'Loading...' },
        { title: 'Currencies', value: '—', trend: 'Loading...' },
      ];

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
        <div style={{ textAlign: 'center', color: '#6b7280' }}>
          <Loader2 size={32} style={{ animation: 'spin 1s linear infinite', marginBottom: 12 }} />
          <p>Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
        <div style={{ textAlign: 'center', maxWidth: 400 }}>
          <p style={{ fontSize: 18, fontWeight: 600, marginBottom: 8, color: '#dc2626' }}>Failed to load dashboard</p>
          <p style={{ color: '#6b7280', marginBottom: 16 }}>{error}</p>
          <button
            type="button"
            onClick={() => void load()}
            style={{ padding: '8px 20px', borderRadius: 8, border: '1px solid #e5e7eb', background: '#fff', cursor: 'pointer', fontWeight: 500 }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      {marketStale && (
        <div role="status" style={{ marginBottom: 12, padding: '10px 14px', borderRadius: 10, background: 'var(--blue-bg)', border: '1px solid rgba(96, 165, 250, 0.25)', fontSize: 13, color: 'var(--text)' }}>
          Market data {marketFetchedAt ? `as of ${marketFetchedAt.toLocaleString()}` : 'unavailable'} — showing cached portfolio data.
        </div>
      )}
      {!marketStale && marketFetchedAt && (
        <div role="status" style={{ marginBottom: 12, fontSize: 12, color: '#6b7280' }}>
          Market data as of {marketFetchedAt.toLocaleString()}
        </div>
      )}
      {summary && summary.portfolio_count === 0 && (
        <section className="panel" aria-label="Get started" style={{ marginBottom: 16, borderColor: '#93c5fd', background: '#eff6ff' }}>
          <div className="panel-header">
            <h2>Start your first loop</h2>
          </div>
          <p style={{ fontSize: 13, color: '#1e40af', margin: '0 0 12px' }}>
            1. Add a portfolio &nbsp;→&nbsp; 2. Run an optimization &nbsp;→&nbsp; 3. Review risk.
            Load the demo portfolio or create your own — two minutes either way.
          </p>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button
              type="button"
              className="primary-button"
              onClick={() => void handleSeedDemo()}
              disabled={seedingDemo}
            >
              {seedingDemo ? 'Loading demo…' : 'Load demo portfolio →'}
            </button>
            <Link className="soft-button" to="/portfolios">Create portfolio</Link>
            <Link className="soft-button" to="/optimizations/new">Run optimization</Link>
          </div>
        </section>
      )}
      <section className="hero-card">
        <div>
          <p className="eyebrow">Good morning</p>
          <h1>Everything you need, with less noise.</h1>
          {lastSync && (
            <p style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>
              Last synced {lastSync.toLocaleTimeString()}
            </p>
          )}
        </div>

        <div className="hero-meta">
          <div className="meta-pill">
            <Wallet size={14} />
            {summary ? `${summary.portfolio_count} portfolio${summary.portfolio_count !== 1 ? 's' : ''} active` : 'No portfolios'}
          </div>
          <div className="meta-pill subtle">
            <ArrowUpRight size={14} />
            {summary?.active_optimizations
              ? `${summary.active_optimizations} optimization${summary.active_optimizations !== 1 ? 's' : ''} running`
              : 'Ready to optimize'}
          </div>
        </div>
      </section>

      <section className="stats-grid qa-grid-4">
        {stats.map(({ value, label, tone }) => (
          <article key={label} className={`stat-card ${tone}`}>
            <div className="stat-value">{value}</div>
            <div className="stat-label">{label}</div>
          </article>
        ))}
      </section>

      <section className="content-grid qa-grid-2">
        <article className="panel panel-large">
          <div className="panel-header">
            <h2>Maturity distribution</h2>
            <button className="soft-button" type="button" onClick={() => setShowChartTable((v) => !v)}>
              {showChartTable ? 'Show chart' : 'All years'} <ChevronRight size={14} />
            </button>
          </div>

          {summary?.maturity_distribution.length ? (
            showChartTable ? (
              <table className="q-table" aria-label="Maturity distribution data table">
                <thead>
                  <tr>
                    <th>Year</th>
                    <th>Instruments</th>
                    <th>Total principal</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.maturity_distribution.slice(0, 10).map((bucket) => (
                    <tr key={bucket.year}>
                      <td>{bucket.year}</td>
                      <td>{bucket.count}</td>
                      <td>{formatCurrency(bucket.total_principal)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="chart" role="list" aria-label="Maturity distribution chart. Activate View as table for exact values.">
                {summary.maturity_distribution.slice(0, 10).map((bucket) => (
                  <button
                    key={bucket.year}
                    type="button"
                    role="listitem"
                    className="bar-wrap"
                    title={`${bucket.year}: ${formatCurrency(bucket.total_principal)} (${bucket.count} instruments)`}
                    aria-label={`${bucket.year}: ${formatCurrency(bucket.total_principal)}, ${bucket.count} instruments`}
                    style={{ background: 'none', border: 'none', cursor: 'default', padding: 0 }}
                  >
                    <span
                      className="bar"
                      aria-hidden="true"
                      style={{ height: `${Math.max(4, (bucket.total_principal / maxPrincipal) * 100)}%` }}
                    />
                    <span className="bar-year" aria-hidden="true">{bucket.year}</span>
                  </button>
                ))}
              </div>
            )
          ) : (
            <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>
              No maturity data available
            </div>
          )}
        </article>

        <article className="panel" aria-live="polite">
          <div className="panel-header">
            <h2>Priority tasks</h2>
            <Link className="soft-button" to="/optimizations">View all</Link>
          </div>

          {searchQuery && (
            <p style={{ fontSize: 12, color: '#6b7280', marginBottom: 8 }}>
              {filteredTasks.length} result{filteredTasks.length === 1 ? '' : 's'} for “{params.get('q')}”{' '}
              <Link to="/dashboard">Clear</Link>
            </p>
          )}

          <div className="task-list">
            {displayTasks.length === 0 ? (
              <p style={{ padding: 16, color: '#6b7280', fontSize: 13 }}>
                No tasks match your search. <Link to="/dashboard">Clear search</Link>
              </p>
            ) : (
              displayTasks.map((task: DashboardTask & { state?: string }) => (
                <div key={task.id || task.title} className="task-item">
                  <div className="task-dot" />
                  <div className="task-copy">
                    <strong>{task.title}</strong>
                    <span>{task.meta}</span>
                  </div>
                  <span className="task-state">{task.state || task.status}</span>
                </div>
              ))
            )}
          </div>
        </article>
      </section>

      <section className="bottom-grid qa-grid-2">
        <article className="panel">
          <div className="panel-header">
            <h2>Key metrics</h2>
          </div>

          <div className="metric-list">
            {keyMetrics.map(({ title, value, trend }) => (
              <div key={title} className="metric-row">
                <span>{title}</span>
                <strong>{value}</strong>
                <em>{trend}</em>
              </div>
            ))}
          </div>
        </article>

        <article className="panel">
          <div className="panel-header">
            <h2>Risk breakdown</h2>
          </div>
          <p style={{ fontSize: 12, color: '#6b7280', marginBottom: 8 }}>
            Scores are out of 100 — higher means more risk. <Link to="/settings">Learn more</Link>
          </p>

          <div className="metric-list">
            {summary ? (
              <>
                <div className="metric-row">
                  <span>Refinancing</span>
                  <strong>{summary.risk_scores.refinancing_risk.toFixed(0)} / 100</strong>
                  <em style={{ color: riskColor(summary.risk_scores.refinancing_risk) === 'red' ? '#dc2626' : riskColor(summary.risk_scores.refinancing_risk) === 'blue' ? 'var(--blue)' : '#16a34a' }}>
                    {riskLabel(summary.risk_scores.refinancing_risk)}
                  </em>
                </div>
                <div className="metric-row">
                  <span>Currency</span>
                  <strong>{summary.risk_scores.currency_risk.toFixed(0)} / 100</strong>
                  <em style={{ color: riskColor(summary.risk_scores.currency_risk) === 'red' ? '#dc2626' : riskColor(summary.risk_scores.currency_risk) === 'blue' ? 'var(--blue)' : '#16a34a' }}>
                    {riskLabel(summary.risk_scores.currency_risk)}
                  </em>
                </div>
                <div className="metric-row">
                  <span>Interest rate</span>
                  <strong>{summary.risk_scores.interest_rate_risk.toFixed(0)} / 100</strong>
                  <em style={{ color: riskColor(summary.risk_scores.interest_rate_risk) === 'red' ? '#dc2626' : riskColor(summary.risk_scores.interest_rate_risk) === 'blue' ? 'var(--blue)' : '#16a34a' }}>
                    {riskLabel(summary.risk_scores.interest_rate_risk)}
                  </em>
                </div>
              </>
            ) : (
              <div style={{ padding: 16, textAlign: 'center', color: '#9ca3af' }}>No risk data</div>
            )}
          </div>
        </article>
      </section>

      <FirstRunWizard />

      <section style={{ marginTop: 24 }}>
        <WhatIfPanel />
      </section>

      <section className="qa-grid-2" style={{ display: 'grid', gap: 20, marginTop: 24 }}>
        <MarketPulseWidget />
        <DailyBriefing />
      </section>

      <section style={{ marginTop: 24 }}>
        <SavingsDashboard />
      </section>

      <section style={{ marginTop: 24 }}>
        <AssetTracker />
      </section>
    </div>
  );
}
