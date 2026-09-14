import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  bankingApi,
  centsToUsd,
  dollarsToCents,
  type BankAccount,
  type BankTransfer,
} from '../api/banking';

export default function BankingTransfersPage() {
  const [accounts, setAccounts] = useState<BankAccount[]>([]);
  const [history, setHistory] = useState<BankTransfer[]>([]);
  const [fromId, setFromId] = useState('');
  const [mode, setMode] = useState<'internal' | 'external'>('internal');
  const [toId, setToId] = useState('');
  const [counterparty, setCounterparty] = useState('');
  const [amount, setAmount] = useState('');
  const [memo, setMemo] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [a, h] = await Promise.all([bankingApi.accounts(), bankingApi.transfers()]);
      setAccounts(a.accounts);
      setHistory(h.transfers);
      if (a.accounts.length > 0 && !fromId) setFromId(a.accounts[0].id);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load transfers');
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setNotice('');
    let cents: number;
    try {
      cents = dollarsToCents(amount);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid amount');
      return;
    }
    setSending(true);
    try {
      const transfer = await bankingApi.createTransfer({
        from_account_id: fromId,
        to_account_id: mode === 'internal' ? toId || null : null,
        counterparty: mode === 'external' ? counterparty : undefined,
        amount_cents: cents,
        memo: memo || undefined,
        idempotency_key: `web-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      });
      setNotice(`Moved ${centsToUsd(transfer.amount_cents)} with $0 fee.`);
      setAmount('');
      setMemo('');
      setCounterparty('');
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Transfer failed');
    } finally {
      setSending(false);
    }
  }

  if (loading) return <div className="qp-card">Loading transfers…</div>;

  return (
    <div style={{ display: 'grid', gap: 12, maxWidth: 720 }}>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <h1 style={{ margin: 0 }}>Move money</h1>
        <span className="badge">$0 fee, every time</span>
        <span style={{ flex: 1 }} />
        <Link to="/banking/app" className="qp-btn secondary" style={{ textDecoration: 'none' }}>← Dashboard</Link>
      </div>

      {error && <div className="qp-card" style={{ borderColor: '#f87171' }}>{error}</div>}
      {notice && <div className="qp-card" style={{ borderColor: '#34d399' }}>{notice}</div>}

      <form onSubmit={(e) => void handleSubmit(e)} className="qp-card" style={{ display: 'grid', gap: 10 }}>
        <label>From account
          <select value={fromId} onChange={(e) => setFromId(e.target.value)} style={{ display: 'block', width: '100%', marginTop: 4 }}>
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>{a.name} — {centsToUsd(a.balance_cents)}</option>
            ))}
          </select>
        </label>
        <div style={{ display: 'flex', gap: 8 }}>
          <button type="button" className={`qp-btn ${mode === 'internal' ? '' : 'secondary'}`} onClick={() => setMode('internal')}>Between my accounts</button>
          <button type="button" className={`qp-btn ${mode === 'external' ? '' : 'secondary'}`} onClick={() => setMode('external')}>To someone else</button>
        </div>
        {mode === 'internal' ? (
          <label>To account
            <select value={toId} onChange={(e) => setToId(e.target.value)} style={{ display: 'block', width: '100%', marginTop: 4 }}>
              <option value="">Select…</option>
              {accounts.filter((a) => a.id !== fromId).map((a) => (
                <option key={a.id} value={a.id}>{a.name} — {centsToUsd(a.balance_cents)}</option>
              ))}
            </select>
          </label>
        ) : (
          <label>Recipient
            <input value={counterparty} onChange={(e) => setCounterparty(e.target.value)} placeholder="Vendor Co" style={{ display: 'block', width: '100%', marginTop: 4 }} />
          </label>
        )}
        <label>Amount (USD)
          <input value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="1,250.00" inputMode="decimal" style={{ display: 'block', width: '100%', marginTop: 4 }} />
        </label>
        <label>Memo (optional)
          <input value={memo} onChange={(e) => setMemo(e.target.value)} placeholder="Invoice #1043" style={{ display: 'block', width: '100%', marginTop: 4 }} />
        </label>
        <button type="submit" className="qp-btn" disabled={sending || accounts.length === 0}>
          {sending ? 'Moving…' : 'Send with $0 fee'}
        </button>
      </form>

      <section aria-label="History" className="qp-card">
        <h2>History</h2>
        {history.length === 0 && <p className="qp-muted">No transfers yet.</p>}
        {history.map((t) => (
          <div key={t.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid #f3f4f6', fontSize: 13 }}>
            <div>
              <div style={{ fontWeight: 600 }}>{t.counterparty || 'Internal transfer'}</div>
              <div className="qp-muted" style={{ fontSize: 12 }}>{t.memo} · {t.status}</div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontWeight: 650 }}>{centsToUsd(t.amount_cents)}</div>
              <span className="badge" style={{ fontSize: 10 }}>$0 fee</span>
            </div>
          </div>
        ))}
      </section>
    </div>
  );
}
