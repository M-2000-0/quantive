import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { ArrowLeft, ArrowUpDown, ChevronDown, Filter, Loader2, Play } from 'lucide-react';
import { api } from '../api';
import type { DebtInstrument } from '../types';

interface PortfolioDetail {
  id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
  summary: {
    total_principal: number;
    instrument_count: number;
    currency_count: number;
    avg_maturity_years: number;
    weighted_coupon_pct: number;
    weighted_spread_bps: number;
    callable_count: number;
  };
  instruments: DebtInstrument[];
  maturity_distribution: Array<{ year: number; count: number; total_principal: number }>;
  currency_breakdown: Array<{ currency: string; total_principal: number; percentage: number; instrument_count: number }>;
}

function formatCurrency(value: number): string {
  if (value >= 1e12) return `$${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `$${(value / 1e3).toFixed(1)}K`;
  return `$${value.toFixed(0)}`;
}

function riskColor(score: number): string {
  if (score >= 75) return '#dc2626';
  if (score >= 50) return '#d97706';
  return '#16a34a';
}

type SortField = 'name' | 'maturity_date' | 'principal_outstanding' | 'coupon_rate' | 'spread_bps';
type SortOrder = 'asc' | 'desc';

export default function PortfolioDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [params] = useSearchParams();
  const [detail, setDetail] = useState<PortfolioDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortField, setSortField] = useState<SortField>('maturity_date');
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc');
  const [currencyFilter, setCurrencyFilter] = useState<string>('');
  const [showCurrencyDropdown, setShowCurrencyDropdown] = useState(false);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const qs = new URLSearchParams();
      if (sortField) qs.set('sort_by', sortField);
      qs.set('sort_order', sortOrder);
      if (currencyFilter) qs.set('currency', currencyFilter);
      const data = await api.request<PortfolioDetail>(`/portfolio-detail/${id}?${qs.toString()}`);
      setDetail(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load portfolio');
    } finally {
      setLoading(false);
    }
  }, [id, sortField, sortOrder, currencyFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  const currencies = useMemo(() => {
    if (!detail) return [];
    return detail.currency_breakdown.map((c) => c.currency);
  }, [detail]);

  const maxPrincipal = detail?.maturity_distribution.length
    ? Math.max(...detail.maturity_distribution.map((b) => b.total_principal))
    : 1;

  function toggleSort(field: SortField) {
    if (sortField === field) {
      setSortOrder((o) => (o === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
        <div style={{ textAlign: 'center', color: '#6b7280' }}>
          <Loader2 size={32} style={{ animation: 'spin 1s linear infinite', marginBottom: 12 }} />
          <p>Loading portfolio...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
        <div style={{ textAlign: 'center', maxWidth: 400 }}>
          <p style={{ fontSize: 18, fontWeight: 600, marginBottom: 8, color: '#dc2626' }}>Failed to load portfolio</p>
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

  if (!detail) return null;

  const s = detail.summary;

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <Link to="/dashboard" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 13, color: '#6b7280', textDecoration: 'none', marginBottom: 12 }}>
          <ArrowLeft size={14} /> Back to dashboard
        </Link>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 700, margin: 0 }}>{detail.name}</h1>
            {detail.description && (
              <p style={{ fontSize: 13, color: '#6b7280', margin: '4px 0 0' }}>{detail.description}</p>
            )}
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <a
            href={api.exports.portfolioExcel(detail.id)}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              padding: '8px 16px', borderRadius: 8, border: '1px solid #e5e7eb',
              background: '#fff', color: '#374151', fontSize: 13, fontWeight: 600,
              textDecoration: 'none', cursor: 'pointer',
            }}
          >
            Export Excel
          </a>
          <Link
            to={`/optimizations/new?portfolio=${detail.id}`}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              padding: '8px 16px', borderRadius: 8, border: 'none',
              background: '#2563eb', color: '#fff', fontSize: 13, fontWeight: 600,
              textDecoration: 'none', cursor: 'pointer',
            }}
          >
            <Play size={14} /> Run Optimization
          </Link>
          </div>
        </div>
      </div>

      {/* Summary Stats */}
      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 12, marginBottom: 24 }}>
        {[
          { value: formatCurrency(s.total_principal), label: 'Total principal', tone: '#2563eb' },
          { value: `${s.instrument_count}`, label: 'Instruments', tone: '#6b7280' },
          { value: `${s.currency_count}`, label: 'Currencies', tone: '#6b7280' },
          { value: `${s.avg_maturity_years} yr`, label: 'Avg maturity', tone: '#6b7280' },
          { value: `${s.weighted_coupon_pct.toFixed(2)}%`, label: 'Wtd coupon', tone: '#16a34a' },
          { value: `${s.weighted_spread_bps.toFixed(0)} bps`, label: 'Wtd spread', tone: '#6b7280' },
          { value: `${s.callable_count}`, label: 'Callable', tone: '#d97706' },
        ].map(({ value, label, tone }) => (
          <article key={label} className="stat-card" style={{ borderTop: `3px solid ${tone}` }}>
            <div className="stat-value" style={{ fontSize: 20 }}>{value}</div>
            <div className="stat-label">{label}</div>
          </article>
        ))}
      </section>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 24 }}>
        {/* Maturity Distribution */}
        <article className="panel">
          <div className="panel-header">
            <h2>Maturity ladder</h2>
          </div>
          {detail.maturity_distribution.length > 0 ? (
            <div className="chart" role="list" aria-label="Maturity distribution chart">
              {detail.maturity_distribution.slice(0, 12).map((bucket) => (
                <button
                  key={bucket.year}
                  type="button"
                  role="listitem"
                  className="bar-wrap"
                  title={`${bucket.year}: ${formatCurrency(bucket.total_principal)} (${bucket.count} instruments)`}
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
          ) : (
            <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>No maturity data</div>
          )}
        </article>

        {/* Currency Breakdown */}
        <article className="panel">
          <div className="panel-header">
            <h2>Currency breakdown</h2>
          </div>
          {detail.currency_breakdown.length > 0 ? (
            <div className="metric-list">
              {detail.currency_breakdown.map((c) => (
                <div key={c.currency} className="metric-row">
                  <span>{c.currency}</span>
                  <strong>{formatCurrency(c.total_principal)}</strong>
                  <em>{c.percentage.toFixed(1)}% ({c.instrument_count})</em>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ padding: 32, textAlign: 'center', color: '#9ca3af' }}>No currency data</div>
          )}
        </article>
      </div>

      {/* Instrument Table */}
      <article className="panel">
        <div className="panel-header">
          <h2>Instruments ({detail.instruments.length})</h2>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            {/* Currency filter */}
            <div style={{ position: 'relative' }}>
              <button
                type="button"
                className="soft-button"
                onClick={() => setShowCurrencyDropdown((v) => !v)}
                style={{ display: 'flex', alignItems: 'center', gap: 4 }}
              >
                <Filter size={14} />
                {currencyFilter || 'All currencies'}
                <ChevronDown size={12} />
              </button>
              {showCurrencyDropdown && (
                <div style={{
                  position: 'absolute', top: '100%', right: 0, zIndex: 10,
                  background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8,
                  boxShadow: '0 4px 12px rgba(0,0,0,0.1)', minWidth: 150, padding: 4,
                }}>
                  <button
                    type="button"
                    onClick={() => { setCurrencyFilter(''); setShowCurrencyDropdown(false); }}
                    style={{
                      display: 'block', width: '100%', textAlign: 'left', padding: '6px 10px',
                      borderRadius: 6, border: 'none', background: !currencyFilter ? '#f3f4f6' : 'transparent',
                      cursor: 'pointer', fontSize: 13,
                    }}
                  >
                    All currencies
                  </button>
                  {currencies.map((c) => (
                    <button
                      key={c}
                      type="button"
                      onClick={() => { setCurrencyFilter(c); setShowCurrencyDropdown(false); }}
                      style={{
                        display: 'block', width: '100%', textAlign: 'left', padding: '6px 10px',
                        borderRadius: 6, border: 'none', background: currencyFilter === c ? '#f3f4f6' : 'transparent',
                        cursor: 'pointer', fontSize: 13,
                      }}
                    >
                      {c}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="q-table" aria-label="Instruments table">
            <thead>
              <tr>
                <th>
                  <button type="button" onClick={() => toggleSort('name')} style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontWeight: 600, fontSize: 12 }}>
                    Name <ArrowUpDown size={12} />
                  </button>
                </th>
                <th>Type</th>
                <th>Currency</th>
                <th>
                  <button type="button" onClick={() => toggleSort('principal_outstanding')} style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontWeight: 600, fontSize: 12 }}>
                    Principal <ArrowUpDown size={12} />
                  </button>
                </th>
                <th>
                  <button type="button" onClick={() => toggleSort('coupon_rate')} style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontWeight: 600, fontSize: 12 }}>
                    Coupon <ArrowUpDown size={12} />
                  </button>
                </th>
                <th>
                  <button type="button" onClick={() => toggleSort('maturity_date')} style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontWeight: 600, fontSize: 12 }}>
                    Maturity <ArrowUpDown size={12} />
                  </button>
                </th>
                <th>
                  <button type="button" onClick={() => toggleSort('spread_bps')} style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontWeight: 600, fontSize: 12 }}>
                    Spread <ArrowUpDown size={12} />
                  </button>
                </th>
                <th>Callable</th>
              </tr>
            </thead>
            <tbody>
              {detail.instruments.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', padding: 32, color: '#9ca3af' }}>
                    No instruments found
                  </td>
                </tr>
              ) : (
                detail.instruments.map((inst) => (
                  <tr key={inst.id}>
                    <td style={{ fontWeight: 500 }}>{inst.name}</td>
                    <td>{inst.instrument_type}</td>
                    <td>{inst.currency}</td>
                    <td>{formatCurrency(inst.principal_outstanding)}</td>
                    <td>{inst.coupon_rate.toFixed(2)}%</td>
                    <td>{inst.maturity_date}</td>
                    <td>{inst.spread_bps.toFixed(0)} bps</td>
                    <td>{inst.is_callable ? 'Yes' : 'No'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </article>
    </div>
  );
}
