import { useState } from 'react';
import { Link } from 'react-router-dom';
import { personalApi } from '../api';

export default function IntelligencePage() {
  const [q, setQ] = useState('Can I deduct my home office?');
  const [res, setRes] = useState<any>(null);
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(false);

  const ask = async () => {
    setLoading(true); setErr('');
    try { setRes(await personalApi.ask(q)); }
    catch (e: any) { setErr(e.message || 'Failed — Starter allows 20 questions/month.'); }
    finally { setLoading(false); }
  };

  const cap = res?.asks_cap;
  const used = res?.asks_used_30d;

  return (
    <div>
      <h1>Quantive Intelligence</h1>
      <p className="qp-muted">Answers cite your profile and rules. Uncertainty is explicit. Not a CPA.</p>
      {err && (
        <div className="qp-warn">{err} <Link to="/personal/pricing">Upgrade for unlimited →</Link></div>
      )}
      <div className="qp-row">
        <input className="qp-input" value={q} onChange={(e) => setQ(e.target.value)} />
        <div style={{ marginTop: 8, display: 'flex', gap: 8, alignItems: 'center' }}>
          <button className="qp-btn" onClick={ask} disabled={loading}>{loading ? 'Thinking…' : 'Ask'}</button>
          {typeof cap === 'number' && cap >= 0 && <span className="qp-muted">{used ?? 0}/{cap} this month</span>}
        </div>
      </div>
      {res && (
        <div className="qp-card" style={{ marginTop: 12 }}>
          <span className="qp-pill">{res.confidence}</span>
          <span className="qp-muted"> · {res.tier}</span>
          <h4>What I know</h4>
          <ul>{(res.what_i_know || []).map((x: string) => <li key={x} className="qp-muted">{x}</li>)}</ul>
          <h4>What I need</h4>
          <ul>{(res.what_i_need || []).map((x: string) => <li key={x} className="qp-muted">{x}</li>)}</ul>
          {res.gov_note && <p className="qp-muted">{res.gov_note}</p>}
          <p><strong>Next:</strong> {res.next_step}</p>
          <p className="qp-muted">{res.disclaimer}</p>
        </div>
      )}
    </div>
  );
}
