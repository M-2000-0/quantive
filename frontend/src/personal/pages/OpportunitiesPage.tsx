import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { personalApi, type PersonalOpp } from '../api';

export default function OpportunitiesPage() {
  const [opps, setOpps] = useState<PersonalOpp[]>([]);
  const [score, setScore] = useState<any>(null);
  const [err, setErr] = useState('');
  const load = async () => {
    setErr('');
    try {
      const [o, s] = await Promise.all([personalApi.opportunities(), personalApi.score()]);
      setOpps(o); setScore(s);
    } catch (e: any) { setErr(e.message || 'Failed'); }
  };
  useEffect(() => { load().catch(() => {}); }, []);

  const order = (r: string) => (r === 'high' ? 0 : r === 'medium' ? 1 : 2);
  const sorted = [...opps].sort((a, b) => order(a.relevance) - order(b.relevance));
  const cap = score?.limits?.personal_opportunities;
  const capped = typeof cap === 'number' && cap >= 0;

  return (
    <div>
      <h1>Opportunities</h1>
      <p className="qp-muted">Potentially relevant — never guaranteed. Each item says why and what&apos;s needed.</p>
      {err && <div className="qp-warn">{err}</div>}
      {capped && (
        <p className="qp-muted">Starter shows {opps.length}{score ? ` of ${score.opportunities} detected` : ''}. <Link to="/personal/pricing">Unlock all →</Link></p>
      )}
      <div className="qp-list">
        {sorted.map((o) => (
          <div key={o.id} className="qp-row">
            <span className="qp-pill">{o.relevance} priority</span>
            <span className="qp-muted">{o.status}</span>
            <h4>{o.title}</h4>
            <p><strong>Why?</strong> {o.why}</p>
            {(o.needs_info?.length > 0 || o.needs_docs?.length > 0) && (
              <p><strong>Needs:</strong> {[...(o.needs_info || []), ...(o.needs_docs || [])].join(' · ')}</p>
            )}
            {o.next_action && <p><strong>Next:</strong> {o.next_action}</p>}
            {o.rule_refs?.length > 0 && <p className="qp-muted">Rules: {o.rule_refs.join(', ')}</p>}
            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <button className="qp-btn secondary" onClick={async () => { await personalApi.reviewOpp(o.id, 'reviewed'); load(); }}>Review</button>
              <button className="qp-btn secondary" onClick={async () => { await personalApi.reviewOpp(o.id, 'not_applicable'); load(); }}>Not applicable</button>
              <button className="qp-btn secondary" onClick={async () => { await personalApi.reviewOpp(o.id, 'dismiss'); load(); }}>Dismiss</button>
            </div>
          </div>
        ))}
        {sorted.length === 0 && !err && <p className="qp-muted">No opportunities yet.</p>}
      </div>
    </div>
  );
}
