import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { personalApi } from '../personal/api';

// Qubo product page: AI tax assistant for business + optional aggregate
// contribution (explicit opt-in, logged in). Full data practices in Terms.
interface Trend { segment: string; signal: string; direction: string }
interface PublicTrends {
  is_live: boolean; as_of: string; contributors_total: number;
  trends: Trend[]; note?: string; privacy: string; min_bucket?: number;
}

const API_BASE =
  typeof window !== 'undefined' && (window as any).electronAPI?.isElectron
    ? 'http://127.0.0.1:8000/api'
    : '/api';

export default function QuboPage() {
  const [data, setData] = useState<PublicTrends | null>(null);
  const [err, setErr] = useState('');
  const [status, setStatus] = useState<{ opt_in: boolean; age_bracket: string | null; brackets: string[] } | null>(null);
  const [bracket, setBracket] = useState('');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState('');

  const load = () => {
    setErr('');
    fetch(`${API_BASE}/qubo/trends`, { credentials: 'include' })
      .then((r) => { if (!r.ok) throw new Error(`Trends unavailable (${r.status})`); return r.json(); })
      .then(setData)
      .catch((e) => setErr(e.message || 'Failed to load trends'));
  };

  useEffect(() => {
    load();
    personalApi.quboStatus()
      .then((s) => { setStatus(s); if (s.age_bracket) setBracket(s.age_bracket); })
      .catch(() => setStatus(null)); // not logged in — contribute CTA stays login-gated
  }, []);

  const save = async (opt_in: boolean) => {
    if (!bracket && opt_in) { setSaved('Pick your age bracket first.'); return; }
    setSaving(true); setSaved('');
    try {
      const out = await personalApi.quboConsent(opt_in, bracket || undefined);
      setStatus((s) => ({ opt_in: out.opt_in, age_bracket: out.age_bracket, brackets: s?.brackets ?? [] }));
      setSaved(out.opt_in ? 'You’re contributing aggregates. Thank you — patterns, not people.' : 'Opted out. Your facts no longer count toward aggregates.');
      load(); // refresh contributor count
    } catch (e: any) {
      setSaved(e.message || 'Could not save preference.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: 24 }}>
      <nav style={{ display: 'flex', gap: 12 }}>
        <Link to="/">← Home</Link>
        <Link to="/terms">Terms</Link>
        <Link to="/government">Government</Link>
      </nav>
      <h1>Qubo</h1>
      <p style={{ color: '#4b5563' }}>
        Qubo is Quantive's AI tax assistant for businesses — it categorizes spending,
        surfaces deductions, and keeps your books close-ready year-round.
      </p>
      <p style={{ color: '#4b5563' }}>
        Separately, you may <em>opt in</em> below to contribute de-identified aggregates
        that help governments decide where to invest. Nothing is shared unless you say so —
        see <Link to="/terms">Terms of Service</Link> § Qubo &amp; Data.
      </p>

      {/* ── Live trends ─────────────────────────────────────────── */}
      <div className="qp-card">
        <h3>Live trends</h3>
        {!data && !err && <p className="qp-muted">Loading trends…</p>}
        {err && (
          <div>
            <div className="qp-warn">⚠️ {err}</div>
            <button className="qp-btn secondary" onClick={load} style={{ marginTop: 8 }}>Retry</button>
          </div>
        )}
        {data && (
          <div>
            <p className="qp-muted">
              {data.is_live
                ? `● Live · ${data.contributors_total} contributors · as of ${new Date(data.as_of).toLocaleString()}`
                : `○ Illustrative preview · ${data.contributors_total} contributors so far — live brackets unlock at ${data.min_bucket ?? 5}+ per age group`}
            </p>
            <ul>
              {data.trends.map((t) => (
                <li key={t.segment}><strong>{t.segment}</strong> — {t.signal} <span className="qp-muted">({t.direction})</span></li>
              ))}
            </ul>
            {!data.is_live && data.note && <p className="qp-muted">{data.note}</p>}
            <p className="qp-muted">{data.privacy}</p>
          </div>
        )}
      </div>

      {/* ── Contribute (opt-in) ─────────────────────────────────── */}
      <div className="qp-card" style={{ marginTop: 12 }}>
        <h3>Contribute your bracket (optional, reversible)</h3>
        {status === null && (
          <p className="qp-muted">
            <Link to="/login">Sign in</Link> and complete <Link to="/personal/onboarding">Personal onboarding</Link> to
            contribute your age-bracket aggregates. Qubo never sees your name, conversations, or individual records.
          </p>
        )}
        {status !== null && (
          <div>
            <p className="qp-muted">
              Status: <strong>{status.opt_in ? 'contributing' : 'not contributing'}</strong>
              {status.age_bracket ? ` · bracket ${status.age_bracket}` : ' · no bracket set'}
            </p>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
              <select value={bracket} onChange={(e) => setBracket(e.target.value)} aria-label="Age bracket">
                <option value="">Select age bracket…</option>
                {(status.brackets ?? []).map((b) => <option key={b} value={b}>{b}</option>)}
              </select>
              <button className="qp-btn" disabled={saving} onClick={() => save(true)}>
                {saving ? 'Saving…' : 'Opt in'}
              </button>
              <button className="qp-btn secondary" disabled={saving} onClick={() => save(false)}>Opt out</button>
            </div>
            {saved && <p className="qp-muted" role="status" style={{ marginTop: 8 }}>{saved}</p>}
          </div>
        )}
      </div>

      <div className="qp-card" style={{ marginTop: 12 }}>
        <h3>What the government receives</h3>
        <ul>
          <li>Age group / age bracket aggregates</li>
          <li>“People are investing more in X” / “spending more on Y” trend signals</li>
          <li>Time-bucketed, de-identified aggregates for investment planning</li>
        </ul>
      </div>

      <div className="qp-card" style={{ marginTop: 12 }}>
        <h3>What the government never receives</h3>
        <ul>
          <li>Names or contact details</li>
          <li>Conversations or message content</li>
          <li>Individual transactions or identifiable records</li>
        </ul>
        <p className="qp-muted">
          Qubo shares <em>patterns</em>, not people. See <Link to="/terms">Terms of Service</Link> § Qubo &amp; Government Data.
        </p>
      </div>

      <div className="qp-card" style={{ marginTop: 12 }}>
        <h3>How it flows</h3>
        <ol className="qp-muted">
          <li>Individuals and businesses use Quantive / Quantive Personal.</li>
          <li>Qubo aggregates activity into age-bracket trend buckets.</li>
          <li>Government planners see only the aggregates to guide investment.</li>
        </ol>
      </div>
    </div>
  );
}
