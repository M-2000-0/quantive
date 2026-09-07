import { useMemo, useState } from 'react';
import {
  MOCK_PURCHASES,
  formatCurrency,
  getTotalPrincipal,
  getTotalUnrealizedPnl,
  type Purchase,
} from '../lib/purchaseData';

export default function PurchaseTrackerPage() {
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('All');
  const [selected, setSelected] = useState<Purchase | null>(null);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return MOCK_PURCHASES.filter((p) => {
      if (statusFilter !== 'All' && p.currency !== statusFilter) return false;
      if (!q) return true;
      return `${p.instrumentName} ${p.issuer}`.toLowerCase().includes(q);
    });
  }, [query, statusFilter]);

  function exportCsv() {
    const header = 'id,instrument,issuer,principal,currency';
    const rows = filtered.map((p) =>
      [p.id, `"${p.instrumentName}"`, `"${p.issuer}"`, p.principal, p.currency].join(','),
    );
    const blob = new Blob([[header, ...rows].join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'purchases.csv';
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div>
      <h1>Purchase Tracker</h1>
      <button type="button" aria-pressed="false">
        ▶ Auto
      </button>
      <div style={{ display: 'flex', gap: 12, margin: '12px 0' }}>
        <div className="panel">
          <div className="data-label">Total Principal</div>
          <div className="data-value">{formatCurrency(getTotalPrincipal(MOCK_PURCHASES))}</div>
        </div>
        <div className="panel">
          <div className="data-label">Unrealized P&L</div>
          <div className="data-value">{formatCurrency(getTotalUnrealizedPnl(MOCK_PURCHASES))}</div>
        </div>
      </div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <input
          type="search"
          placeholder="Search purchases..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="glass-input"
          style={{ maxWidth: 280 }}
        />
        {['All', 'USD', 'EUR', 'GBP', 'AUD'].map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setStatusFilter(s)}
            className="soft-button"
            aria-pressed={statusFilter === s}
          >
            {s}
          </button>
        ))}
        <span style={{ flex: 1 }} />
        <button type="button" className="soft-button" onClick={exportCsv}>
          Export CSV
        </button>
        <button type="button" className="soft-button">
          + Add Purchase
        </button>
      </div>
      <table className="q-table">
        <thead>
          <tr>
            <th>Instrument</th>
            <th>Issuer</th>
            <th>Principal</th>
            <th>Currency</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((p) => (
            <tr key={p.id} onClick={() => setSelected(p)} style={{ cursor: 'pointer' }}>
              <td>{p.instrumentName}</td>
              <td>{p.issuer}</td>
              <td>{formatCurrency(p.principal)}</td>
              <td>{p.currency}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {selected && (
        <div className="panel animate-glass-in" style={{ marginTop: 16 }}>
          <h2>{selected.instrumentName}</h2>
          <p>
            {selected.issuer} • {formatCurrency(selected.principal)} {selected.currency}
          </p>
          <button type="button" className="soft-button" onClick={() => setSelected(null)}>
            Close
          </button>
        </div>
      )}
    </div>
  );
}
