import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  api,
  centsToUsd,
  type BankingInsight,
  type BankingOverview,
  type BankTransaction,
} from '../api';

function TxnRow({ txn }: { txn: BankTransaction }) {
  const sign = txn.direction === 'in' ? '+' : '−';
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid #f3f4f6', fontSize: 13 }}>
      <div>
        <div style={{ fontWeight: 600 }}>{txn.counterparty || txn.txn_type}</div>
        <div className="qp-muted" style={{ fontSize: 12 }}>
          {txn.memo} · {txn.category} · {txn.status}
        </div>
      </div>
      <div style={{ textAlign: 'right' }}>
        <div style={{ fontWeight: 650 }}>{sign}{centsToUsd(txn.amount_cents).replace('$', '$')}</div>
        <span className="badge" style={{ fontSize: 10 }}>$0 fee</span>
      </div>
    </div>
  );
}

export default function BankingDashboardPage() {
  const [overview, setOverview] = useState<BankingOverview | null>(null);
  const [insights, setInsights] = useState<BankingInsight[]>([]);
  const [disclaimer, setDisclaimer] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [seeding, setSeeding] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [ov, ins] = await Promise.all([api.banking.overview(), api.banking.insights()]);
      setOverview(ov);
      setInsights(ins.insights);
      setDisclaimer(ins.disclaimer);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load banking overview');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleSeed() {
    setSeeding(true);
    setError('');
    try {
      await api.banking.seed();
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Seed failed');
    } finally {
      setSeeding(false);
    }
  }

  if (loading) return <div className="qp-card">Loading banking dashboard…</div>;
  if (error) return <div className="qp-card"><p>Couldn't load banking data: {error}</p><button className="qp-btn" onClick={() => void load()}>Retry</button></div>;
  if (!overview) return null;

  if (overview.accounts.length === 0) {
    return (
      <div className="qp-card" style={{ maxWidth: 560 }}>
        <h1>No accounts yet</h1>
        <p className="qp-muted">Open your first free business account — no minimums, no fees — or load demo data matching the Banking story.</p>
        <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
          <button className="qp-btn" onClick={() => void handleSeed()} disabled={seeding}>
            {seeding ? 'Loading…' : 'Load demo data'}
          </button>
          <Link to="/banking/onboarding" className="qp-btn secondary" style={{ textDecoration: 'none' }}>Complete onboarding →</Link>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'grid', gap: 12 }}>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <h1 style={{ margin: 0 }}>Banking</h1>
        <span className="badge">0% transaction fees</span>
        <span style={{ flex: 1 }} />
        <Link to="/banking/transfers" className="qp-btn" style={{ textDecoration: 'none' }}>Move money →</Link>
        <Link to="/banking/onboarding" className="qp-btn secondary" style={{ textDecoration: 'none' }}>Onboarding</Link>
      </div>

      <section aria-label="Balances" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: 12 }}>
        <div className="qp-card">
          <span className="badge">Available balance</span>
          <div style={{ fontSize: 28, fontWeight: 750, marginTop: 8 }}>{centsToUsd(overview.total_balance_cents)}</div>
        </div>
        <div className="qp-card">
          <span className="badge">Fees paid (30d)</span>
          <div style={{ fontSize: 28, fontWeight: 750, marginTop: 8 }}>{centsToUsd(overview.fees_paid_30d_cents)}</div>
          <p className="qp-muted" style={{ fontSize: 12 }}>on {centsToUsd(overview.moved_30d_cents)} moved</p>
        </div>
        <div className="qp-card">
          <span className="badge">Forecast (90d)</span>
          <div style={{ fontSize: 28, fontWeight: 750, marginTop: 8 }}>
            {overview.projected_net_90d_cents >= 0 ? '+' : '−'}{centsToUsd(Math.abs(overview.projected_net_90d_cents))}
          </div>
          <p className="qp-muted" style={{ fontSize: 12 }}>{overview.forecast_basis}</p>
        </div>
      </section>

      <section aria-label="Accounts" className="qp-card">
        <h2>Accounts</h2>
        {overview.accounts.map((a) => (
          <div key={a.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid #f3f4f6', fontSize: 14 }}>
            <span><strong>{a.name}</strong> <span className="qp-muted">· {a.account_type} · {a.status}</span></span>
            <strong>{centsToUsd(a.balance_cents)}</strong>
          </div>
        ))}
      </section>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(300px,1fr))', gap: 12 }}>
        <section aria-label="Recent movement" className="qp-card">
          <h2>Recent movement — $0 fees</h2>
          {overview.recent.map((t) => <TxnRow key={t.id} txn={t} />)}
        </section>
        <section aria-label="AI CFO" className="qp-card">
          <h2>AI CFO assistant</h2>
          {insights.map((c) => (
            <div key={c.id} style={{ padding: '10px 12px', borderRadius: 10, background: c.severity === 'warn' ? '#fef3c7' : '#f0fdf4', marginBottom: 8 }}>
              <div style={{ fontWeight: 650, fontSize: 13 }}>{c.title}</div>
              <div className="qp-muted" style={{ fontSize: 12, marginTop: 4 }}>{c.body}</div>
            </div>
          ))}
          <p className="qp-muted" style={{ fontSize: 11 }}>{disclaimer}</p>
        </section>
      </div>
    </div>
  );
}
