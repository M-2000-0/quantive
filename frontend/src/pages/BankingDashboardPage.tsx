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

const ACCOUNT_TYPES = [
  { value: 'operating', label: 'Operating', desc: 'Day-to-day transactions, payroll, vendor payments' },
  { value: 'reserve', label: 'Reserve', desc: 'Emergency fund, cash buffer, short-term savings' },
  { value: 'yield', label: 'Yield', desc: 'Interest-bearing, idle cash optimization' },
] as const;

function OpenAccountModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [name, setName] = useState('');
  const [accountType, setAccountType] = useState('operating');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      await api.banking.openAccount({ name: name.trim(), account_type: accountType });
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to open account');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(17,24,39,0.55)', padding: 24 }}>
      <div role="dialog" aria-modal="true" aria-label="Open new account" style={{ background: '#fff', borderRadius: 16, padding: 32, width: '100%', maxWidth: 480, maxHeight: '90vh', overflowY: 'auto', boxShadow: '0 4px 24px rgba(0,0,0,0.08)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>Open new account</h2>
          <button type="button" onClick={onClose} aria-label="Close" style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#9ca3af', fontSize: 18 }}>✕</button>
        </div>

        <form onSubmit={(e) => void handleSubmit(e)}>
          <label htmlFor="acct-name" style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 6 }}>Account name</label>
          <input
            id="acct-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Operating Account"
            required
            style={{ width: '100%', padding: '10px 12px', borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 14, marginBottom: 16, boxSizing: 'border-box' }}
          />

          <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Account type</label>
          <div style={{ display: 'grid', gap: 8, marginBottom: 20 }}>
            {ACCOUNT_TYPES.map((t) => (
              <label
                key={t.value}
                style={{
                  display: 'flex', alignItems: 'flex-start', gap: 10, padding: '12px 14px', borderRadius: 10, cursor: 'pointer',
                  border: `2px solid ${accountType === t.value ? '#2563eb' : '#e5e7eb'}`,
                  background: accountType === t.value ? 'rgba(37,99,235,0.04)' : '#fff',
                }}
              >
                <input
                  type="radio"
                  name="account_type"
                  value={t.value}
                  checked={accountType === t.value}
                  onChange={() => setAccountType(t.value)}
                  style={{ marginTop: 2 }}
                />
                <div>
                  <div style={{ fontSize: 14, fontWeight: 600 }}>{t.label}</div>
                  <div style={{ fontSize: 12, color: '#6b7280', marginTop: 2 }}>{t.desc}</div>
                </div>
              </label>
            ))}
          </div>

          {error && (
            <div style={{ padding: '10px 14px', borderRadius: 8, background: 'rgba(220,38,38,0.05)', border: '1px solid rgba(220,38,38,0.15)', marginBottom: 16, color: '#991b1b', fontSize: 13 }}>
              {error}
            </div>
          )}

          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <button type="button" onClick={onClose} style={{ padding: '10px 20px', borderRadius: 8, border: '1px solid #e5e7eb', background: '#fff', cursor: 'pointer', fontSize: 14, fontWeight: 500 }}>
              Cancel
            </button>
            <button type="submit" disabled={submitting || !name.trim()} style={{ padding: '10px 20px', borderRadius: 8, border: 'none', background: '#2563eb', color: '#fff', cursor: 'pointer', fontSize: 14, fontWeight: 600, opacity: submitting || !name.trim() ? 0.6 : 1 }}>
              {submitting ? 'Opening…' : 'Open account'}
            </button>
          </div>
        </form>
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
  const [showOpenAccount, setShowOpenAccount] = useState(false);

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
        <div style={{ display: 'flex', gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
          <button className="qp-btn" onClick={() => setShowOpenAccount(true)}>Open account</button>
          <button className="qp-btn secondary" onClick={() => void handleSeed()} disabled={seeding}>
            {seeding ? 'Loading…' : 'Load demo data'}
          </button>
          <Link to="/banking/onboarding" className="qp-btn secondary" style={{ textDecoration: 'none' }}>Complete onboarding →</Link>
        </div>
        {showOpenAccount && <OpenAccountModal onClose={() => setShowOpenAccount(false)} onCreated={() => { setShowOpenAccount(false); void load(); }} />}
      </div>
    );
  }

  return (
    <div style={{ display: 'grid', gap: 12 }}>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <h1 style={{ margin: 0 }}>Banking</h1>
        <span className="badge">0% transaction fees</span>
        <span style={{ flex: 1 }} />
        <button className="qp-btn secondary" onClick={() => setShowOpenAccount(true)}>Open account</button>
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
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <h2 style={{ margin: 0 }}>Accounts</h2>
          <button className="qp-btn secondary" style={{ fontSize: 12, padding: '4px 12px' }} onClick={() => setShowOpenAccount(true)}>+ New</button>
        </div>
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

      {showOpenAccount && <OpenAccountModal onClose={() => setShowOpenAccount(false)} onCreated={() => { setShowOpenAccount(false); void load(); }} />}
    </div>
  );
}
