import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { personalApi, type PersonalScore, type PersonalOpp, type PersonalTask } from '../api';

export default function PersonalDashboard() {
  const [score, setScore] = useState<PersonalScore | null>(null);
  const [opps, setOpps] = useState<PersonalOpp[]>([]);
  const [tasks, setTasks] = useState<PersonalTask[]>([]);
  const [err, setErr] = useState('');

  useEffect(() => {
    (async () => {
      try {
        const [s, o, t] = await Promise.all([
          personalApi.score(), personalApi.opportunities(), personalApi.tasks(),
        ]);
        setScore(s); setOpps(o); setTasks(t.filter((x) => x.status === 'open'));
      } catch (e: any) { setErr(e.message || 'Failed to load'); }
    })();
  }, []);

  if (err) return <div className="qp-warn">{err}</div>;
  if (!score) return <p className="qp-muted">Loading your tax intelligence…</p>;

  const starter = score.tier === 'personal_2k' || score.tier === 'none';
  const oppCap = (score.limits || {}).personal_opportunities;
  const docCap = (score.limits || {}).personal_documents;

  return (
    <div className="qp-hero">
      <h1>Good morning.</h1>
      <p>{score.message}</p>
      <p className="qp-muted">Plan: <strong>{score.tier}</strong>
        {starter && <> · <Link to="/personal/pricing">Starter is lean — compare plans →</Link></>}
        {score.gov_access && <> · <Link to="/personal/gov">Sovereign view →</Link></>}
      </p>
      {starter && (
        <div className="qp-warn" style={{ marginTop: 8 }}>
          Starter ($2k/yr) covers tax write-offs only — up to {oppCap ?? 3} opportunities, {docCap ?? 10} documents,
          20 questions/month, no Gov-grade access. Useful, deliberately limited.
        </div>
      )}
      <div className="qp-grid">
        <div className="qp-card"><h3>Tax Intelligence Score</h3><div className="big">{score.score}/100</div><p className="qp-muted">Completeness {score.completeness}% — readiness, not savings.</p></div>
        <div className="qp-card"><h3>Actions</h3><div className="big">{score.open_actions}</div><p className="qp-muted">Open tasks</p></div>
        <div className="qp-card"><h3>Opportunities</h3><div className="big">{score.opportunities}</div><p className="qp-muted">Potentially relevant{typeof oppCap === 'number' && oppCap >= 0 ? ` (plan shows ${oppCap})` : ''}</p></div>
        <div className="qp-card"><h3>Doc gaps</h3><div className="big">{score.doc_gaps}</div><p className="qp-muted">{score.docs_total ?? 0} docs{typeof docCap === 'number' && docCap >= 0 ? ` / ${docCap}` : ''}</p></div>
      </div>
      <h3>Opportunities</h3>
      <div className="qp-list">
        {opps.slice(0, 4).map((o) => (
          <div key={o.id} className="qp-row">
            <h4>{o.title}</h4>
            <span className="qp-pill">{o.relevance}</span>
            <span className="qp-muted">Potentially relevant — not guaranteed</span>
            <p>{o.why}</p>
          </div>
        ))}
        {starter && score.opportunities > opps.length && (
          <div className="qp-row" style={{ opacity: 0.75 }}>
            <h4>🔒 {score.opportunities - opps.length} more detected</h4>
            <p className="qp-muted">Starter shows {opps.length}. Personal unlocks all + full report.</p>
            <Link to="/personal/pricing" className="qp-btn secondary" style={{ textDecoration: 'none' }}>Compare plans</Link>
          </div>
        )}
        {opps.length === 0 && <p className="qp-muted">Complete onboarding to surface opportunities. <Link to="/personal/onboarding">Start →</Link></p>}
      </div>
      {!score.gov_access && (
        <div className="qp-row" style={{ marginTop: 12 }}>
          <h4>Gov-grade market access — Sovereign only</h4>
          <p className="qp-muted">Aggregated Qubo bracket trends (no individual data). $10k/yr.</p>
          <Link to="/personal/gov">Preview locked view →</Link>
        </div>
      )}
      <h3 style={{ marginTop: 20 }}>What needs you</h3>
      <div className="qp-list">
        {tasks.slice(0, 5).map((t) => (
          <div key={t.id} className="qp-row"><h4>{t.title}</h4><p>{t.reason}</p></div>
        ))}
      </div>
    </div>
  );
}
