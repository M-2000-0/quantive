import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  api,
  centsToUsd,
  type QuboFinding,
  type QuboOverview,
} from '../api';

type QuarterlyData = {
  quarters: Record<string, { deductions_cents: number; estimated_set_aside_cents: number }>;
  total_deductions_cents: number;
  estimated_annual_set_aside_cents: number;
  effective_rate: number;
  note: string;
};

function exportFindingsCsv(findings: QuboFinding[]) {
  const header = 'Date,Category,Title,Amount,Jurisdiction,Tax Year,Rule ID,Status,Requirements,Docs\n';
  const rows = findings.map((f) => {
    const date = f.created_at ? new Date(f.created_at).toISOString() : '';
    const title = `"${(f.title || '').replace(/"/g, '""')}"`;
    const reqs = `"${(f.requirements?.requirements ?? []).join('; ').replace(/"/g, '""')}"`;
    const docs = `"${(f.requirements?.docs ?? []).join('; ').replace(/"/g, '""')}"`;
    return `${date},${f.category},${title},${f.amount_cents},${f.jurisdiction},${f.tax_year},${f.rule_id},${f.status},${reqs},${docs}`;
  }).join('\n');
  const blob = new Blob([header + rows], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `qubo-findings-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function QuboWorkspacePage() {
  const [overview, setOverview] = useState<QuboOverview | null>(null);
  const [findings, setFindings] = useState<QuboFinding[]>([]);
  const [quarterly, setQuarterly] = useState<QuarterlyData | null>(null);
  const [filter, setFilter] = useState<string>('');
  const [jurisdiction, setJurisdiction] = useState('US');
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const load = useCallback(async (status = '') => {
    setLoading(true);
    setError('');
    try {
      const [ov, list] = await Promise.all([
        api.banking.qubo.overview(),
        api.banking.qubo.findings(status || undefined),
      ]);
      setOverview(ov);
      setFindings(list.findings);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load Qubo workspace');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(filter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  async function loadQuarterly() {
    try {
      const data = await api.banking.qubo.quarterlyEstimates();
      setQuarterly(data as unknown as QuarterlyData);
    } catch {
      // Silently fail — quarterly is optional
    }
  }

  async function handleScan() {
    setScanning(true);
    setError('');
    setNotice('');
    try {
      const res = await api.banking.qubo.scan(jurisdiction);
      setNotice(
        res.created > 0
          ? `Scan complete: ${res.created} new potential deduction${res.created === 1 ? '' : 's'} (${res.rules_version}).`
          : `Scan complete: nothing new — ${res.scanned_transactions} transactions checked (${res.rules_version}).`,
      );
      await load(filter);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Scan failed');
    } finally {
      setScanning(false);
    }
  }

  async function handleReview(id: string, status: 'accepted' | 'dismissed') {
    setError('');
    try {
      await api.banking.qubo.reviewFinding(id, status);
      await load(filter);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Review failed');
    }
  }

  function handleExport() {
    exportFindingsCsv(findings);
  }

  if (loading && !overview) return <div className="qp-card">Loading Qubo workspace…</div>;

  return (
    <div style={{ display: 'grid', gap: 12 }}>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <h1 style={{ margin: 0 }}>Qubo</h1>
        <span className="badge">tax deductions</span>
        {overview && <span className="badge">{overview.rules_version}</span>}
        <span style={{ flex: 1 }} />
        <Link to="/banking/app" className="qp-btn secondary" style={{ textDecoration: 'none' }}>← Banking</Link>
      </div>

      {error && <div className="qp-card" style={{ borderColor: '#f87171' }}>{error}</div>}
      {notice && <div className="qp-card" style={{ borderColor: '#34d399' }}>{notice}</div>}

      <section aria-label="Scan" className="qp-card" style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <label>Jurisdiction
          <select value={jurisdiction} onChange={(e) => setJurisdiction(e.target.value)} style={{ marginLeft: 8 }}>
            <option value="US">US</option>
            <option value="MX">MX</option>
            <option value="BD">BD</option>
            <option value="GEN">Other (generic)</option>
          </select>
        </label>
        <button className="qp-btn" onClick={() => void handleScan()} disabled={scanning}>
          {scanning ? 'Scanning ledger…' : 'Scan ledger for deductions →'}
        </button>
        <span className="qp-muted" style={{ fontSize: 12 }}>Findings are potentially relevant — never promised savings.</span>
      </section>

      {overview && (
        <section aria-label="Totals" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))', gap: 12 }}>
          <div className="qp-card">
            <span className="badge">Open findings</span>
            <div style={{ fontSize: 28, fontWeight: 750, marginTop: 8 }}>{overview.counts.new}</div>
          </div>
          <div className="qp-card">
            <span className="badge">May qualify (open)</span>
            <div style={{ fontSize: 28, fontWeight: 750, marginTop: 8 }}>{centsToUsd(overview.potential_new_cents)}</div>
          </div>
          <div className="qp-card">
            <span className="badge">Accepted</span>
            <div style={{ fontSize: 28, fontWeight: 750, marginTop: 8 }}>{overview.counts.accepted} · {centsToUsd(overview.accepted_cents)}</div>
          </div>
        </section>
      )}

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {['', 'new', 'accepted', 'dismissed'].map((s) => (
          <button
            key={s || 'all'}
            type="button"
            className={`qp-btn ${filter === s ? '' : 'secondary'}`}
            onClick={() => setFilter(s)}
          >
            {s || 'all'}
          </button>
        ))}
        <span style={{ flex: 1 }} />
        <button className="qp-btn secondary" onClick={() => void loadQuarterly()}>Quarterly estimates</button>
        <button className="qp-btn secondary" onClick={handleExport}>Export CSV</button>
      </div>

      {quarterly && (
        <section aria-label="Quarterly estimates" className="qp-card">
          <h2>Quarterly set-aside estimates</h2>
          <p className="qp-muted" style={{ fontSize: 12 }}>Based on {overview?.counts.accepted ?? 0} accepted deductions at {(quarterly.effective_rate * 100).toFixed(0)}% illustrative rate.</p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(140px,1fr))', gap: 8, marginTop: 8 }}>
            {Object.entries(quarterly.quarters).map(([q, data]) => (
              <div key={q} className="qp-card" style={{ textAlign: 'center' }}>
                <span className="badge">{q}</span>
                <div style={{ fontSize: 20, fontWeight: 700, marginTop: 6 }}>{centsToUsd(data.estimated_set_aside_cents)}</div>
                <div className="qp-muted" style={{ fontSize: 11 }}>{centsToUsd(data.deductions_cents)} deductions</div>
              </div>
            ))}
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8, padding: '8px 0', borderTop: '1px solid #f3f4f6' }}>
            <span style={{ fontWeight: 650 }}>Annual set-aside</span>
            <span style={{ fontWeight: 700 }}>{centsToUsd(quarterly.estimated_annual_set_aside_cents)}</span>
          </div>
          <p className="qp-muted" style={{ fontSize: 11 }}>{quarterly.note}</p>
        </section>
      )}

      <section aria-label="Findings" className="qp-card">
        <h2>Findings</h2>
        {findings.length === 0 && <p className="qp-muted">Nothing here. Run a scan to check your posted outflows against {overview?.rules_version ?? 'current'} rules.</p>}
        {findings.map((f) => (
          <div key={f.id} style={{ padding: '12px 0', borderBottom: '1px solid #f3f4f6' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
              <div style={{ fontWeight: 650 }}>{f.title}</div>
              <div style={{ fontWeight: 650 }}>{centsToUsd(f.amount_cents)}</div>
            </div>
            <div className="qp-muted" style={{ fontSize: 12, marginTop: 4 }}>{f.detail}</div>
            <div className="qp-muted" style={{ fontSize: 12, marginTop: 4 }}>
              Rule <strong>{f.rule_id}</strong> · {f.jurisdiction} {f.tax_year} · {f.category} · status: {f.status}
            </div>
            {(f.requirements?.requirements?.length > 0 || f.requirements?.docs?.length > 0) && (
              <div className="qp-muted" style={{ fontSize: 12, marginTop: 4 }}>
                Needs: {[...(f.requirements?.requirements ?? []), ...(f.requirements?.docs ?? [])].join('; ')}
              </div>
            )}
            {f.status === 'new' && (
              <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                <button className="qp-btn" onClick={() => void handleReview(f.id, 'accepted')}>Accept</button>
                <button className="qp-btn secondary" onClick={() => void handleReview(f.id, 'dismissed')}>Dismiss</button>
              </div>
            )}
          </div>
        ))}
      </section>
      {overview && <p className="qp-muted" style={{ fontSize: 11 }}>{overview.note}</p>}
    </div>
  );
}
