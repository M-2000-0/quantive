import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { personalApi } from '../api';

interface GovData {
  trends: { segment: string; signal: string; direction: string }[];
  how_to_use: string; privacy: string;
  is_live?: boolean; as_of?: string; contributors_total?: number;
  your_bracket?: string; note?: string;
}

export default function GovInsightsPage() {
  const [data, setData] = useState<GovData | null>(null);
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
      <p className="qp-muted">
        {data.is_live
          ? `● Live aggregates · ${data.contributors_total ?? 0} contributors${data.as_of ? ` · as of ${new Date(data.as_of).toLocaleString()}` : ''}`
          : `○ Illustrative preview${typeof data.contributors_total === 'number' ? ` · ${data.contributors_total} contributors so far` : ''} — live brackets unlock as opt-ins grow`}
        {data.your_bracket && data.your_bracket !== 'unknown' ? ` · your bracket ${data.your_bracket}` : ''}
      </p>
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
      {data.note ? <p className="qp-muted" style={{ marginTop: 8 }}>{data.note}</p> : null}
      <p className="qp-muted" style={{ marginTop: 12 }}>{data.privacy}</p>
      <p className="qp-muted" style={{ marginTop: 8 }}>
        Want your bracket counted? <Link to="/qubo">Manage Qubo contribution →</Link>
      </p>
    </div>
  );
}
