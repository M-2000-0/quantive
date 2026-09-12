import { useEffect, useState } from 'react';
import { personalApi, type PersonalBilling } from '../api';

export default function PricingPage() {
  const [bill, setBill] = useState<PersonalBilling | null>(null);
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState('');

  useEffect(() => {
    const qs = new URLSearchParams(window.location.search);
    if (qs.get('checkout') === 'success') setMsg('Checkout completed — your plan updates after webhook fulfillment.');
    if (qs.get('checkout') === 'cancelled') setMsg('Checkout cancelled — no charge made.');
    personalApi.billing().then(setBill).catch((e) => setMsg(e.message));
  }, []);

  const buy = async (tier: string) => {
    setBusy(tier); setMsg('');
    try {
      const s = await personalApi.checkout(tier, 'yearly');
      if (s.checkout_url) window.location.href = s.checkout_url;
      else setMsg(`Subscribed to ${tier} (dev mode). Refresh to see limits update.`);
      const b = await personalApi.billing().catch(() => null);
      if (b) setBill(b);
    } catch (e: any) {
      setMsg(e.message || 'Checkout failed');
    } finally {
      setBusy('');
    }
  };

  const plans = bill?.plans || [];
  return (
    <div>
      <h1>Choose your plan</h1>
      <p className="qp-muted">Annual access — not per-message. Current: <strong>{bill?.tier || '…'}</strong> ({bill?.status || ''})</p>
      {msg && <div className="qp-warn" style={{ marginTop: 8 }}>{msg}</div>}
      <div className="qp-grid" style={{ gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', marginTop: 12 }}>
        {plans.map((p) => {
          const current = bill?.tier === p.tier;
          return (
            <div key={p.tier} className="qp-card" style={current ? { borderColor: '#4f46e5', borderWidth: 2 } : {}}>
              <h3>{p.name} — ${p.price_yearly}/yr</h3>
              <ul className="qp-muted">{p.features.map((f) => <li key={f}>{f}</li>)}</ul>
              {p.tier === 'personal_2k' && <p className="qp-muted">Tax write-offs only, with limits. Useful but incomplete — you will feel the edges.</p>}
              {p.tier === 'personal_10k' && <p className="qp-muted">Gov-grade Quantive for individuals (Qubo aggregates only).</p>}
              <button className={current ? 'qp-btn secondary' : 'qp-btn'} disabled={current || !!busy} onClick={() => buy(p.tier)}>
                {current ? 'Current plan' : busy === p.tier ? 'Redirecting…' : `Choose ${p.name}`}
              </button>
            </div>
          );
        })}
      </div>
      {plans.length === 0 && <p className="qp-muted">Loading plans…</p>}
    </div>
  );
}
