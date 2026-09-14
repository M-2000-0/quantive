import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { api, centsToUsd, type BankAccount, type BankTransaction } from '../api';

const CATEGORIES = [
  'payroll', 'rent', 'software', 'utilities', 'travel',
  'invoice', 'customer', 'tax', 'transfer', 'other',
];

export default function BankTransactionPage() {
  const { id } = useParams<{ id: string }>();
  const [account, setAccount] = useState<BankAccount | null>(null);
  const [txn, setTxn] = useState<BankTransaction | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [category, setCategory] = useState('');
  const [taxTag, setTaxTag] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveNotice, setSaveNotice] = useState('');

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError('');
    try {
      // We need to find which account this transaction belongs to.
      // Fetch all accounts, then search each for the transaction.
      const { accounts } = await api.banking.accounts();
      for (const acct of accounts) {
        try {
          const { transactions } = await api.banking.accountTxns(acct.id, 100);
          const found = transactions.find((t) => t.id === id);
          if (found) {
            setAccount(acct);
            setTxn(found);
            setCategory(found.category);
            setTaxTag(found.tax_tag);
            break;
          }
        } catch {
          // try next account
        }
      }
      if (!txn) {
        setError('Transaction not found');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load transaction');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleSave() {
    if (!id) return;
    setSaving(true);
    setSaveNotice('');
    try {
      const updated = await api.banking.categorize(id, { category, tax_tag: taxTag });
      setTxn(updated);
      setSaveNotice('Saved');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save');
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '40vh' }}>
        <Loader2 size={24} style={{ animation: 'spin 1s linear infinite', color: '#6b7280' }} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="qp-card" style={{ maxWidth: 480, textAlign: 'center' }}>
        <p style={{ color: '#dc2626', marginBottom: 8 }}>{error}</p>
        <Link to="/banking/app" className="qp-btn secondary" style={{ textDecoration: 'none' }}>← Back to dashboard</Link>
      </div>
    );
  }

  if (!txn) return null;

  const sign = txn.direction === 'in' ? '+' : '−';

  return (
    <div style={{ maxWidth: 560 }}>
      <Link to="/banking/app" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 13, color: '#6b7280', textDecoration: 'none', marginBottom: 16 }}>
        <ArrowLeft size={14} /> Back to dashboard
      </Link>

      <div className="qp-card" style={{ marginBottom: 12 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>{txn.counterparty || txn.txn_type}</h1>
            <p className="qp-muted" style={{ fontSize: 13, marginTop: 4 }}>
              {account?.name} · {account?.account_type}
            </p>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 24, fontWeight: 750, color: txn.direction === 'in' ? '#16a34a' : '#dc2626' }}>
              {sign}{centsToUsd(txn.amount_cents)}
            </div>
            <span className="badge" style={{ fontSize: 11 }}>$0 fee</span>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, fontSize: 13 }}>
          <div>
            <div className="qp-muted" style={{ fontSize: 11, textTransform: 'uppercase' }}>Status</div>
            <div style={{ fontWeight: 600 }}>{txn.status}</div>
          </div>
          <div>
            <div className="qp-muted" style={{ fontSize: 11, textTransform: 'uppercase' }}>Type</div>
            <div style={{ fontWeight: 600 }}>{txn.txn_type}</div>
          </div>
          <div>
            <div className="qp-muted" style={{ fontSize: 11, textTransform: 'uppercase' }}>Date</div>
            <div style={{ fontWeight: 600 }}>{txn.created_at ? new Date(txn.created_at).toLocaleString() : '—'}</div>
          </div>
          <div>
            <div className="qp-muted" style={{ fontSize: 11, textTransform: 'uppercase' }}>Transaction ID</div>
            <div style={{ fontWeight: 600, fontSize: 12, fontFamily: 'monospace' }}>{txn.id.slice(0, 8)}…</div>
          </div>
        </div>

        {txn.memo && (
          <div style={{ marginTop: 12, padding: '10px 14px', borderRadius: 8, background: '#f9fafb', fontSize: 13 }}>
            <span className="qp-muted">Memo: </span>{txn.memo}
          </div>
        )}
      </div>

      <div className="qp-card">
        <h2 style={{ fontSize: 15, fontWeight: 700, margin: '0 0 12px' }}>Categorization</h2>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div>
            <label htmlFor="txn-category" style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Category</label>
            <select
              id="txn-category"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              style={{ width: '100%', padding: '8px 10px', borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 13 }}
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="txn-tax-tag" style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Tax tag</label>
            <input
              id="txn-tax-tag"
              type="text"
              value={taxTag}
              onChange={(e) => setTaxTag(e.target.value)}
              placeholder="e.g. office-expense"
              style={{ width: '100%', padding: '8px 10px', borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 13 }}
            />
          </div>
        </div>

        <div style={{ display: 'flex', gap: 8, marginTop: 12, alignItems: 'center' }}>
          <button
            type="button"
            className="qp-btn"
            onClick={() => void handleSave()}
            disabled={saving}
          >
            {saving ? 'Saving…' : 'Save'}
          </button>
          {saveNotice && <span style={{ fontSize: 12, color: '#16a34a' }}>{saveNotice}</span>}
        </div>
      </div>
    </div>
  );
}
