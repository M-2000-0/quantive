import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { personalApi } from '../api';

const CATS = ['income', 'housing', 'medical', 'education', 'retirement', 'business', 'investments', 'other'];

export default function DocumentsPage() {
  const [data, setData] = useState<{ categories: Record<string, number>; total?: number; cap?: number | null; documents: any[] }>({ categories: {}, documents: [] });
  const [name, setName] = useState('');
  const [cat, setCat] = useState('income');
  const [err, setErr] = useState('');
  const load = async () => {
    try { setData(await personalApi.documents()); }
    catch (e: any) { setErr(e.message); }
  };
  useEffect(() => { load().catch(() => {}); }, []);

  const capped = typeof data.cap === 'number' && (data.cap as number) >= 0;

  return (
    <div>
      <h1>Document Center</h1>
      <p className="qp-muted">Organize what you have. Quantive never invents extracted content.
        {capped && <> · {data.total ?? 0}/{data.cap} used. <Link to="/personal/pricing">Unlimited with Personal →</Link></>}
      </p>
      {err && <div className="qp-warn">{err}</div>}
      <div className="qp-grid">
        {CATS.map((c) => (
          <div key={c} className="qp-card"><h3>{c}</h3><div className="big">{data.categories[c] || 0}</div></div>
        ))}
      </div>
      <div className="qp-row">
        <h4>Register a document (metadata only)</h4>
        <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
          <input className="qp-input" placeholder="filename.pdf" value={name} onChange={(e) => setName(e.target.value)} />
          <select className="qp-select" value={cat} onChange={(e) => setCat(e.target.value)} style={{ maxWidth: 180 }}>
            {CATS.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <button className="qp-btn" onClick={async () => {
            if (!name.trim()) return;
            setErr('');
            try {
              await personalApi.registerDoc(name.trim(), cat);
              setName(''); load();
            } catch (e: any) { setErr(e.message || 'Limit reached'); }
          }}>Add</button>
        </div>
        {capped && (data.total ?? 0) >= (data.cap as number) && (
          <p className="qp-muted" style={{ marginTop: 8 }}>Starter document limit reached. Upgrade keeps everything — nothing is deleted.</p>
        )}
      </div>
      <div className="qp-list" style={{ marginTop: 12 }}>
        {data.documents.map((d: any) => (
          <div key={d.id} className="qp-row"><h4>{d.filename}</h4><p>{d.category} · {d.status} · {d.review_status}</p></div>
        ))}
      </div>
    </div>
  );
}
