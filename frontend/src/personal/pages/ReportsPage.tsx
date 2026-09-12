import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { personalApi, type PersonalBilling } from '../api';

export default function ReportsPage() {
  const [rep, setRep] = useState<any>(null);
  const [bill, setBill] = useState<PersonalBilling | null>(null);
  const [msg, setMsg] = useState('');
  useEffect(() => {
    personalApi.report().then(setRep).catch((e) => setMsg(e.message));
    personalApi.billing().then(setBill).catch(() => {});
  }, []);

  if (!rep) return <p className="qp-muted">{msg || 'Preparing your report…'}</p>;
  return (
    <div>
      <h1>Your Quantive Tax Intelligence Report</h1>
      <p className="qp-muted">2026 tax year — readiness and gaps. No savings claimed. Tier: <strong>{rep.tier}</strong>
        {rep.summary_only && <> · <strong>summary only</strong> <Link to="/personal/pricing">Unlock full report →</Link></>}
      </p>
      {rep.summary_only && (
        <div className="qp-warn">Starter includes a summary only — full annual intelligence report requires Personal ($5k) or Sovereign ($10k).</div>
      )}
      <div className="qp-grid">
        <div className="qp-card"><h3>Completeness</h3><div className="big">{rep.profile_completeness}%</div></div>
        <div className="qp-card"><h3>Opportunities</h3><div className="big">{rep.potential_opportunities}</div></div>
        <div className="qp-card"><h3>Doc issues</h3><div className="big">{rep.documentation_issues}</div></div>
        <div className="qp-card"><h3>Need review</h3><div className="big">{rep.items_requiring_review}</div></div>
      </div>
      <div className="qp-row">
        <h4>Questions for your CPA</h4>
        <ul>{(rep.cpa_questions || []).map((x: string) => <li key={x}>{x}</li>)}</ul>
      </div>
      {rep.gov_brief && (
        <div className="qp-row" style={{ marginTop: 12 }}>
          <h4>Sovereign brief</h4>
          <p>{rep.gov_brief}</p>
          <Link to="/personal/gov">Open Sovereign view →</Link>
        </div>
      )}
      {bill && (
        <div style={{ marginTop: 12 }}>
          <div className="qp-row">
            <h4>Current: {bill.tier} ({bill.status}){bill.gov_access ? ' · Gov access on' : ''}</h4>
            <p className="qp-muted">Starter feels lean on purpose — 3 opportunities, 10 docs, 20 questions/mo, no Gov Quantive. <Link to="/personal/pricing">Compare plans →</Link></p>
          </div>
          <div className="qp-grid" style={{ marginTop: 12 }}>
            {(bill.plans || []).map((p) => (
              <div key={p.tier} className="qp-card">
                <h3>{p.name} — ${p.price_yearly}/yr</h3>
                <ul className="qp-muted">{p.features.map((f) => <li key={f}>{f}</li>)}</ul>
                {p.tier === 'personal_2k' && <p className="qp-muted">Tax write-offs only, with limits. Useful but incomplete.</p>}
                {p.tier === 'personal_10k' && <p className="qp-muted">Gov-grade Quantive for individuals (Qubo trends).</p>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
