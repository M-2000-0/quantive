import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { personalApi } from '../api';

export default function GovInsightsPage() {
  const [data, setData] = useState<{ trends: { segment: string; signal: string; direction: string }[]; how_to_use: string; privacy: string } | null>(null);
  const [err, setErr] = useState('');

  useEffect(() => {
    personalApi.govInsights().then(setData).catch((e) => setErr(e.message || 'Locked'));
  }, []);

  if (err) {
    return (
      <div>
        <h1>Sovereign view</h1>
        <div className="qp-warn">🔒 {err}</div>
        <p className="qp-muted">Gov-grade Quantive market access requires <strong>Sovereign ($10k/yr)</strong> — aggregates only, never individual data.</p>
        <Link to="/personal/pricing" className="qp-btn" style={{ textDecoration: 'none' }}>See Sovereign →</Link>
      </div>
    );
  }
  if (!data) return <p className="qp-muted">Loading Gov-grade trends…</p>;
  return (
    <div>
      <h1>Sovereign view</h1>
      <p className="qp-muted">{data.how_to_use}</p>
      <div className="qp-list">
        {data.trends.map((t) => (
          <div key={t.segment} className="qp-row">
            <span className="qp-pill">{t.segment}</span>
            <h4>{t.signal}</h4>
            <p className="qp-muted">trend: {t.direction}</p>
          </div>
        ))}
      </div>
      <p className="qp-muted" style={{ marginTop: 12 }}>{data.privacy}</p>
    </div>
  );
}
