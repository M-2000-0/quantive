import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

interface Dashboard {
  validations: { total: number; passed: number; failed: number; pending: number; signed_off: number };
  vendors: { total: number; critical: number; active: number; dd_complete: number; avg_risk_score: number; avg_uptime_pct: number };
  recent_validations: { id: string; name: string; type: string; status: string; model: string }[];
  high_risk_vendors: { id: string; name: string; category: string; risk_score: number; criticality: string }[];
}

interface Validation {
  id: string; validation_name: string; validation_type: string; status: string;
  model_name: string; model_version: string;
  out_of_sample_sharpe: number | null; sharpe_degradation_pct: number | null;
  max_drawdown_pct: number | null; is_champion: boolean; is_challenger: boolean;
  sign_off_by: string | null; sign_off_date: string | null;
  next_validation_date: string | null;
}

interface Vendor {
  id: string; vendor_name: string; vendor_category: string; status: string;
  criticality: string; due_diligence_completed: boolean; due_diligence_score: number;
  soc2_type_ii: boolean; iso27001_certified: boolean;
  actual_uptime_pct: number | null; sla_breaches_ytd: number;
  overall_risk_score: number; security_risk_score: number;
  incidents_ytd: number; next_review_date: string | null;
}

const BG = '#08090c';
const CARD = '#111318';
const BORDER = '#23272e';
const TEXT = '#e5e7eb';
const DIM = '#9ca3af';
const ACCENT = '#e8e8ea';
const GREEN = '#22c55e';
const RED = '#ef4444';
const SKY = '#38bdf8';
const BLUE = '#3b82f6';
const PURPLE = '#a855f7';
const CYAN = '#06b6d4';

function badge(status: string) {
  const m: Record<string, { bg: string; c: string }> = {
    passed: { bg: '#22c55e20', c: GREEN }, active: { bg: '#22c55e20', c: GREEN }, onboarded: { bg: '#22c55e20', c: GREEN },
    failed: { bg: '#ef444420', c: RED }, terminated: { bg: '#ef444420', c: RED },
    pending: { bg: '#38bdf820', c: SKY }, in_progress: { bg: '#38bdf820', c: SKY }, under_review: { bg: '#38bdf820', c: SKY },
    conditional: { bg: '#3b82f620', c: BLUE }, exempted: { bg: '#6b728020', c: DIM },
  };
  const s = m[status] || { bg: '#6b728020', c: DIM };
  return <span style={{ padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600, background: s.bg, color: s.c, textTransform: 'capitalize' as const }}>{status.replace(/_/g, ' ')}</span>;
}

function critBadge(c: string) {
  const m: Record<string, string> = { critical: RED, high: SKY, medium: ACCENT, low: GREEN };
  return <span style={{ padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600, background: `${m[c] || DIM}20`, color: m[c] || DIM, textTransform: 'capitalize' as const }}>{c}</span>;
}

function boolDot(v: boolean) {
  return <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: 4, background: v ? GREEN : RED }} />;
}

export default function ValidationVendorPage() {
  const [tab, setTab] = useState('dashboard');
  const [dash, setDash] = useState<Dashboard | null>(null);
  const [validations, setValidations] = useState<Validation[]>([]);
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const org = 'a81db73c-1719-4fe5-982c-7bf4cfa1408b';
    Promise.all([
      fetch(`/api/validation/dashboard?org_id=${org}`).then(r => r.json()),
      fetch(`/api/validation/independent?org_id=${org}`).then(r => r.json()),
      fetch(`/api/validation/vendors?org_id=${org}`).then(r => r.json()),
    ]).then(([d, v, ve]) => {
      setDash(d);
      setValidations(v.validations || []);
      setVendors(ve.vendors || []);
      setLoading(false);
    });
  }, []);

  const tabs = [
    { key: 'dashboard', label: 'Overview' },
    { key: 'validations', label: 'Independent Validation' },
    { key: 'vendors', label: 'Vendor Risk' },
  ];

  return (
    <div style={{ padding: 24, background: BG, minHeight: '100vh', fontFamily: "'Inter', -apple-system, sans-serif" }}>
      <div style={{ maxWidth: 1400, margin: '0 auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 700, color: TEXT, margin: 0 }}>
              <span style={{ color: ACCENT }}>{'✅'}</span> Independent Validation & Vendor Risk
            </h1>
            <p style={{ fontSize: 13, color: DIM, margin: '4px 0 0 0' }}>
              Model backtesting, champion/challenger testing, third-party due diligence, SLA monitoring
            </p>
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            {[
              { to: '/cybersecurity-privacy', label: 'Cybersecurity' },
              { to: '/regulatory-compliance', label: 'Regulatory' },
              { to: '/exchange-due-diligence', label: 'Due Diligence' },
            ].map(l => (
              <Link key={l.to} to={l.to} style={{ padding: '6px 12px', borderRadius: 6, fontSize: 12, fontWeight: 500, background: CARD, border: `1px solid ${BORDER}`, color: DIM, textDecoration: 'none' }}>{l.label}</Link>
            ))}
          </div>
        </div>

        {dash && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 12, marginBottom: 24 }}>
            {[
              { label: 'Validations Passed', value: dash.validations.passed, color: GREEN },
              { label: 'Validations Failed', value: dash.validations.failed, color: RED },
              { label: 'Pending Review', value: dash.validations.pending, color: SKY },
              { label: 'Critical Vendors', value: dash.vendors.critical, color: RED },
              { label: 'Avg Risk Score', value: `${dash.vendors.avg_risk_score}`, color: ACCENT },
              { label: 'Avg Uptime', value: `${dash.vendors.avg_uptime_pct}%`, color: GREEN },
            ].map((m, i) => (
              <div key={i} style={{ padding: '14px 16px', borderRadius: 8, background: CARD, border: `1px solid ${BORDER}` }}>
                <div style={{ fontSize: 11, color: DIM, marginBottom: 6 }}>{m.label}</div>
                <div style={{ fontSize: 22, fontWeight: 700, color: m.color }}>{m.value}</div>
              </div>
            ))}
          </div>
        )}

        <div style={{ display: 'flex', gap: 4, marginBottom: 20, background: CARD, borderRadius: 8, padding: 4, border: `1px solid ${BORDER}` }}>
          {tabs.map(t => (
            <button key={t.key} onClick={() => setTab(t.key)} style={{ padding: '8px 16px', borderRadius: 6, border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 600, background: tab === t.key ? '#e8e8ea20' : 'transparent', color: tab === t.key ? ACCENT : DIM }}>{t.label}</button>
          ))}
        </div>

        {loading ? (
          <div style={{ padding: 60, textAlign: 'center', color: DIM, fontSize: 14 }}>Loading...</div>
        ) : (
          <>
            {tab === 'dashboard' && dash && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <div style={{ padding: 20, borderRadius: 8, background: CARD, border: `1px solid ${BORDER}` }}>
                  <h3 style={{ fontSize: 14, fontWeight: 600, color: TEXT, margin: '0 0 12px 0' }}>Recent Validations</h3>
                  {dash.recent_validations.map(v => (
                    <div key={v.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: `1px solid ${BORDER}` }}>
                      <div>
                        <div style={{ fontSize: 12, fontWeight: 600, color: TEXT }}>{v.name}</div>
                        <div style={{ fontSize: 11, color: DIM }}>{v.model} &middot; {v.type.replace(/_/g, ' ')}</div>
                      </div>
                      {badge(v.status)}
                    </div>
                  ))}
                </div>
                <div style={{ padding: 20, borderRadius: 8, background: CARD, border: `1px solid ${BORDER}` }}>
                  <h3 style={{ fontSize: 14, fontWeight: 600, color: TEXT, margin: '0 0 12px 0' }}>High Risk Vendors</h3>
                  {dash.high_risk_vendors.map(v => (
                    <div key={v.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: `1px solid ${BORDER}` }}>
                      <div>
                        <div style={{ fontSize: 12, fontWeight: 600, color: TEXT }}>{v.name}</div>
                        <div style={{ fontSize: 11, color: DIM }}>{v.category.replace(/_/g, ' ')}</div>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <div style={{ fontSize: 16, fontWeight: 700, color: v.risk_score >= 70 ? RED : v.risk_score >= 40 ? SKY : GREEN }}>{v.risk_score}</div>
                        {critBadge(v.criticality)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {tab === 'validations' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {validations.length === 0 ? (
                  <div style={{ padding: 60, textAlign: 'center', color: DIM, fontSize: 14, background: CARD, borderRadius: 8, border: `1px solid ${BORDER}` }}>No validations</div>
                ) : validations.map(v => (
                  <div key={v.id} style={{ padding: '16px 20px', borderRadius: 8, background: CARD, border: `1px solid ${BORDER}`, display: 'grid', gridTemplateColumns: '1.5fr 1fr 1fr 1fr 1fr', gap: 16, alignItems: 'center' }}>
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 600, color: TEXT }}>{v.validation_name}</div>
                      <div style={{ fontSize: 11, color: DIM }}>{v.model_name} v{v.model_version}</div>
                      <div style={{ marginTop: 4, display: 'flex', gap: 6 }}>{badge(v.validation_type)} {badge(v.status)}
                        {v.is_champion && <span style={{ padding: '2px 6px', borderRadius: 3, fontSize: 10, background: '#22c55e18', color: GREEN }}>CHAMPION</span>}
                        {v.is_challenger && <span style={{ padding: '2px 6px', borderRadius: 3, fontSize: 10, background: '#38bdf818', color: SKY }}>CHALLENGER</span>}
                      </div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 10, color: DIM }}>OOS Sharpe</div>
                      <div style={{ fontSize: 18, fontWeight: 700, color: v.out_of_sample_sharpe && v.out_of_sample_sharpe >= 1.0 ? GREEN : SKY }}>
                        {v.out_of_sample_sharpe ? v.out_of_sample_sharpe.toFixed(2) : '--'}
                      </div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 10, color: DIM }}>Degradation</div>
                      <div style={{ fontSize: 18, fontWeight: 700, color: v.sharpe_degradation_pct && v.sharpe_degradation_pct <= 20 ? GREEN : RED }}>
                        {v.sharpe_degradation_pct ? `${v.sharpe_degradation_pct.toFixed(1)}%` : '--'}
                      </div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 10, color: DIM }}>Max DD</div>
                      <div style={{ fontSize: 18, fontWeight: 700, color: v.max_drawdown_pct && v.max_drawdown_pct <= 15 ? GREEN : RED }}>
                        {v.max_drawdown_pct ? `${v.max_drawdown_pct.toFixed(1)}%` : '--'}
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      {v.sign_off_by ? (
                        <>
                          <div style={{ fontSize: 11, color: GREEN }}>Signed off by {v.sign_off_by}</div>
                          <div style={{ fontSize: 10, color: DIM }}>{v.sign_off_date}</div>
                        </>
                      ) : (
                        <div style={{ fontSize: 11, color: SKY }}>Awaiting sign-off</div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {tab === 'vendors' && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 }}>
                {vendors.length === 0 ? (
                  <div style={{ gridColumn: '1 / -1', padding: 60, textAlign: 'center', color: DIM, fontSize: 14, background: CARD, borderRadius: 8, border: `1px solid ${BORDER}` }}>No vendors</div>
                ) : vendors.map(v => (
                  <div key={v.id} style={{ padding: '16px 20px', borderRadius: 8, background: CARD, border: `1px solid ${BORDER}` }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 600, color: TEXT }}>{v.vendor_name}</div>
                        <div style={{ fontSize: 11, color: BLUE, textTransform: 'capitalize' as const }}>{v.vendor_category.replace(/_/g, ' ')}</div>
                      </div>
                      <div style={{ display: 'flex', gap: 6 }}>{badge(v.status)} {critBadge(v.criticality)}</div>
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 12 }}>
                      <div style={{ padding: 8, borderRadius: 6, background: '#08090c', textAlign: 'center' }}>
                        <div style={{ fontSize: 10, color: DIM }}>Risk Score</div>
                        <div style={{ fontSize: 18, fontWeight: 700, color: v.overall_risk_score >= 70 ? RED : v.overall_risk_score >= 40 ? SKY : GREEN }}>{v.overall_risk_score}</div>
                      </div>
                      <div style={{ padding: 8, borderRadius: 6, background: '#08090c', textAlign: 'center' }}>
                        <div style={{ fontSize: 10, color: DIM }}>Uptime</div>
                        <div style={{ fontSize: 18, fontWeight: 700, color: v.actual_uptime_pct && v.actual_uptime_pct >= 99.9 ? GREEN : RED }}>{v.actual_uptime_pct ? `${v.actual_uptime_pct}%` : '--'}</div>
                      </div>
                      <div style={{ padding: 8, borderRadius: 6, background: '#08090c', textAlign: 'center' }}>
                        <div style={{ fontSize: 10, color: DIM }}>SLA Breaches</div>
                        <div style={{ fontSize: 18, fontWeight: 700, color: v.sla_breaches_ytd > 0 ? RED : GREEN }}>{v.sla_breaches_ytd}</div>
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                      {[
                        { label: 'DD', val: v.due_diligence_completed },
                        { label: 'SOC 2', val: v.soc2_type_ii },
                        { label: 'ISO 27001', val: v.iso27001_certified },
                      ].map(f => (
                        <span key={f.label} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: DIM }}>{f.label} {boolDot(f.val)}</span>
                      ))}
                      <span style={{ fontSize: 11, color: DIM }}>Incidents: <span style={{ color: v.incidents_ytd > 0 ? RED : GREEN, fontWeight: 600 }}>{v.incidents_ytd}</span></span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
