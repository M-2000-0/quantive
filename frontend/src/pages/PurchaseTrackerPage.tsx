import { useCallback, useEffect, useMemo, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { api } from '../api';
import type { PurchaseRecord } from '../types';

const fmt = (n: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n);

export default function PurchaseTrackerPage() {
  const [purchases, setPurchases] = useState<PurchaseRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [currencyFilter, setCurrencyFilter] = useState('All');
  const [selected, setSelected] = useState<PurchaseRecord | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.intelligence.purchases();
      setPurchases(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load purchases');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const currencies = useMemo(() => {
    const set = new Set(purchases.map((p) => p.currency));
    return ['All', ...Array.from(set).sort()];
  }, [purchases]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return purchases.filter((p) => {
      if (currencyFilter !== 'All' && p.currency !== currencyFilter) return false;
      if (!q) return true;
      return `${p.instrument_name} ${p.issuer}`.toLowerCase().includes(q);
    });
  }, [purchases, query, currencyFilter]);

  const totalPrincipal = useMemo(() => filtered.reduce((s, p) => s + p.principal, 0), [filtered]);
  const totalPnl = useMemo(() => filtered.reduce((s, p) => s + p.unrealized_pnl, 0), [filtered]);

  function exportCsv() {
    const header = 'id,instrument,issuer,principal,coupon,ytm,maturity,days_to_maturity,pnl,currency';
    const rows = filtered.map((p) =>
      [p.id, `"${p.instrument_name}"`, `"${p.issuer}"`, p.principal, p.coupon, p.yield_to_maturity, p.maturity_date, p.days_to_maturity, p.unrealized_pnl, p.currency].join(','),
    );
    const blob = new Blob([[header, ...rows].join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'purchases.csv';
    a.click();
    URL.revokeObjectURL(url);
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
        <div style={{ textAlign: 'center', color: '#6b7280' }}>
          <Loader2 size={32} style={{ animation: 'spin 1s linear infinite', marginBottom: 12 }} />
          <p>Loading purchases...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
        <div style={{ textAlign: 'center', maxWidth: 400 }}>
          <p style={{ fontSize: 18, fontWeight: 600, marginBottom: 8, color: '#dc2626' }}>Failed to load</p>
          <p style={{ color: '#6b7280', marginBottom: 16 }}>{error}</p>
          <button type="button" onClick={() => void load()} style={{ padding: '8px 20px', borderRadius: 8, border: '1px solid #e5e7eb', background: '#fff', cursor: 'pointer', fontWeight: 500 }}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, margin: 0 }}>Purchase Tracker</h1>
        <p style={{ fontSize: 13, color: '#6b7280', margin: '4px 0 0' }}>
          Portfolio instruments with current pricing and unrealized P&L.
        </p>
      </div>

      {/* Summary */}
      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12, marginBottom: 24 }}>
        {[
          { value: `${filtered.length}`, label: 'Instruments' },
          { value: fmt(totalPrincipal), label: 'Total Principal' },
          { value: fmt(totalPnl), label: 'Unrealized P&L', tone: totalPnl >= 0 ? '#16a34a' : '#dc2626' },
        ].map(({ value, label, tone }) => (
          <article key={label} className="stat-card" style={{ borderTop: `3px solid ${tone ?? '#2563eb'}` }}>
            <div className="stat-value" style={{ fontSize: 18 }}>{value}</div>
            <div className="stat-label">{label}</div>
          </article>
        ))}
      </section>

      {/* Toolbar */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12, alignItems: 'center', flexWrap: 'wrap' }}>
        <input
          type="search"
          placeholder="Search purchases..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="glass-input"
          style={{ maxWidth: 280 }}
        />
        {currencies.map((c) => (
          <button
            key={c}
            type="button"
            onClick={() => setCurrencyFilter(c)}
            style={{
              padding: '5px 12px', borderRadius: 6, fontSize: 12, fontWeight: 500,
              border: `1px solid ${currencyFilter === c ? '#2563eb' : '#e5e7eb'}`,
              background: currencyFilter === c ? '#2563eb' : '#fff',
              color: currencyFilter === c ? '#fff' : '#374151',
              cursor: 'pointer',
            }}
          >
            {c}
          </button>
        ))}
        <span style={{ flex: 1 }} />
        <button type="button" onClick={exportCsv} style={{ padding: '5px 12px', borderRadius: 6, fontSize: 12, border: '1px solid #e5e7eb', background: '#fff', cursor: 'pointer' }}>
          Export CSV
        </button>
      </div>

      {/* Table */}
      <div style={{ overflowX: 'auto' }}>
        <table className="q-table" style={{ width: '100%' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left' }}>Instrument</th>
              <th style={{ textAlign: 'right' }}>Principal</th>
              <th style={{ textAlign: 'right' }}>Coupon</th>
              <th style={{ textAlign: 'right' }}>Price</th>
              <th style={{ textAlign: 'right' }}>YTM</th>
              <th style={{ textAlign: 'right' }}>Maturity</th>
              <th style={{ textAlign: 'right' }}>Days Left</th>
              <th style={{ textAlign: 'right' }}>P&L</th>
              <th style={{ textAlign: 'center' }}>Ccy</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((p) => (
              <tr key={p.id} onClick={() => setSelected(p)} style={{ cursor: 'pointer' }}>
                <td style={{ textAlign: 'left', fontWeight: 500 }}>{p.instrument_name}</td>
                <td style={{ textAlign: 'right' }}>{fmt(p.principal)}</td>
                <td style={{ textAlign: 'right' }}>{p.coupon.toFixed(1)}%</td>
                <td style={{ textAlign: 'right' }}>{p.purchase_price.toFixed(2)}</td>
                <td style={{ textAlign: 'right' }}>{p.yield_to_maturity.toFixed(2)}%</td>
                <td style={{ textAlign: 'right' }}>{p.maturity_date}</td>
                <td style={{ textAlign: 'right' }}>{p.days_to_maturity.toLocaleString()}</td>
                <td style={{ textAlign: 'right', color: p.unrealized_pnl >= 0 ? '#16a34a' : '#dc2626', fontWeight: 600 }}>
                  {fmt(p.unrealized_pnl)}
                </td>
                <td style={{ textAlign: 'center' }}>{p.currency}</td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={9} style={{ textAlign: 'center', padding: 32, color: '#9ca3af' }}>
                  No purchases match your search
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Detail Panel */}
      {selected && (
        <div className="panel" style={{ marginTop: 16, padding: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <h2 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>{selected.instrument_name}</h2>
              <p style={{ fontSize: 13, color: '#6b7280', margin: '4px 0 0' }}>
                {selected.issuer} · {selected.type} · {selected.currency}
              </p>
            </div>
            <button
              type="button"
              onClick={() => setSelected(null)}
              style={{ padding: '6px 12px', borderRadius: 6, border: '1px solid #e5e7eb', background: '#fff', cursor: 'pointer', fontSize: 12 }}
            >
              Close
            </button>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 16, marginTop: 16 }}>
            {[
              { label: 'Principal', value: fmt(selected.principal) },
              { label: 'Coupon Rate', value: `${selected.coupon.toFixed(1)}%` },
              { label: 'Purchase Price', value: selected.purchase_price.toFixed(2) },
              { label: 'Yield to Maturity', value: `${selected.yield_to_maturity.toFixed(2)}%` },
              { label: 'Maturity Date', value: selected.maturity_date },
              { label: 'Days to Maturity', value: selected.days_to_maturity.toLocaleString() },
              { label: 'Unrealized P&L', value: fmt(selected.unrealized_pnl), tone: selected.unrealized_pnl >= 0 ? '#16a34a' : '#dc2626' },
            ].map(({ label, value, tone }) => (
              <div key={label}>
                <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 2 }}>{label}</div>
                <div style={{ fontSize: 15, fontWeight: 600, color: tone ?? '#111827' }}>{value}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
