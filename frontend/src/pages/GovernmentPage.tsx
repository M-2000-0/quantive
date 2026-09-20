import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

const API = import.meta.env.VITE_API_URL || '';

interface DSAResult {
  risk_rating: string;
  risk_color: string;
  risk_label: string;
  indicators: Record<string, number>;
  recommendations: Array<{ priority: string; area: string; recommendation: string; rationale: string }>;
  projections: Array<{ year: number; debt_gdp: number }>;
}

export default function GovernmentPage() {
  const [tab, setTab] = useState<'dashboard' | 'dsa' | 'stress' | 'maturity' | 'fiscal' | 'audit'>('dashboard');
  const [dsaResult, setDsaResult] = useState<DSAResult | null>(null);
  const [stressResult, setStressResult] = useState<any>(null);
  const [maturity, setMaturity] = useState<any>(null);
  const [fiscal, setFiscal] = useState<any>(null);
  const [auditLog, setAuditLog] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  // DSA form
  const [dsaForm, setDsaForm] = useState({
    debt_stock: 50000, gdp_nominal: 100000, exports: 25000, revenue: 30000,
    debt_service: 4000, interest_payments: 2500, principal_repayments: 1500,
    gross_financing_needs: 8000, country_type: 'mac',
  });

  // Stress test form
  const [baseline, setBaseline] = useState({
    debt_stock: 50000, gdp: 100000, exports: 25000, revenue: 30000,
    interest_rate: 0.05, baseline_gdp_growth: 0.03, primary_balance: 500, fx_rate: 1,
  });
  const [scenarioId, setScenarioId] = useState('rate_shock_mild');
  const [scenarios, setScenarios] = useState<any[]>([]);

  const tabs = [
    { id: 'dashboard' as const, label: 'Overview' },
    { id: 'dsa' as const, label: 'Debt Sustainability' },
    { id: 'stress' as const, label: 'Stress Testing' },
    { id: 'maturity' as const, label: 'Maturity Profile' },
    { id: 'fiscal' as const, label: 'Fiscal Framework' },
    { id: 'audit' as const, label: 'Audit Trail' },
  ];

  // Load data
  const runDSA = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/gov/dsa/analyze`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(dsaForm),
      });
      if (res.ok) setDsaResult(await res.json());
    } catch {}
    setLoading(false);
  };

  const loadScenarios = async () => {
    try {
      const res = await fetch(`${API}/api/gov/stress/scenarios`);
      if (res.ok) { const d = await res.json(); setScenarios(d.scenarios || []); }
    } catch {}
  };

  const runStress = async () => {
    setLoading(true);
    try {
      const scenario = scenarios.find((s: any) => s.id === scenarioId);
      const res = await fetch(`${API}/api/gov/stress/run`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ baseline, shocks: scenario?.shocks || {} }),
      });
      if (res.ok) setStressResult(await res.json());
    } catch {}
    setLoading(false);
  };

  const loadMaturity = async () => {
    try {
      const res = await fetch(`${API}/api/gov/maturity/profile`);
      if (res.ok) setMaturity(await res.json());
    } catch {}
  };

  const loadFiscal = async () => {
    try {
      const res = await fetch(`${API}/api/gov/fiscal/dashboard/2025`);
      if (res.ok) setFiscal(await res.json());
    } catch {}
  };

  const loadAudit = async () => {
    try {
      const res = await fetch(`${API}/api/gov/audit/log?limit=50`);
      if (res.ok) { const d = await res.json(); setAuditLog(d.entries || []); }
    } catch {}
  };

  useEffect(() => {
    if (tab === 'stress') loadScenarios();
    if (tab === 'maturity') loadMaturity();
    if (tab === 'fiscal') loadFiscal();
    if (tab === 'audit') loadAudit();
  }, [tab]);

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: 24 }}>
      <nav style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
        <Link to="/" style={{ color: '#c8a951' }}>← Home</Link>
        <Link to="/government" style={{ color: '#c8a951' }}>Government</Link>
      </nav>

      <h1 style={{ color: '#c8a951', fontSize: 24, marginBottom: 8 }}>Sovereign Debt Management</h1>
      <p style={{ color: '#64748b', marginBottom: 24 }}>IMF-compliant DSA, stress testing, maturity analysis, fiscal framework</p>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 0, borderBottom: '1px solid #1e293b', marginBottom: 24 }}>
        {tabs.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)} style={{
            background: 'none', border: 'none', color: tab === t.id ? '#c8a951' : '#64748b',
            padding: '10px 16px', cursor: 'pointer', fontSize: 13, fontWeight: 600,
            borderBottom: tab === t.id ? '2px solid #c8a951' : '2px solid transparent',
          }}>{t.label}</button>
        ))}
      </div>

      {/* Dashboard Overview */}
      {tab === 'dashboard' && (
        <div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 24 }}>
            {[
              { title: 'Debt/GDP', value: dsaResult ? `${dsaResult.indicators?.debt_gdp}%` : '—', color: dsaResult?.risk_color || '#64748b' },
              { title: 'Risk Rating', value: dsaResult?.risk_label || 'Run DSA', color: dsaResult?.risk_color || '#64748b' },
              { title: 'Stress Test', value: stressResult?.severity_label || 'Run Test', color: stressResult?.severity_color || '#64748b' },
              { title: 'Avg Maturity', value: maturity?.avg_maturity_years ? `${maturity.avg_maturity_years}yr` : '—', color: '#c8a951' },
              { title: 'Fiscal Balance', value: fiscal?.budget?.fiscal_balance_gdp_pct ? `${fiscal.budget.fiscal_balance_gdp_pct}% GDP` : '—', color: fiscal?.budget?.fiscal_balance_gdp_pct >= 0 ? '#22c55e' : '#ef4444' },
              { title: 'Audit Events', value: auditLog.length || '—', color: '#64748b' },
            ].map((card, i) => (
              <div key={i} style={{ background: '#12131a', border: '1px solid #1e293b', borderRadius: 8, padding: 16 }}>
                <div style={{ color: '#94a3b8', fontSize: 11, marginBottom: 4 }}>{card.title}</div>
                <div style={{ color: card.color, fontSize: 20, fontWeight: 700 }}>{card.value}</div>
              </div>
            ))}
          </div>

          {dsaResult?.recommendations && dsaResult.recommendations.length > 0 && (
            <div style={{ background: '#12131a', border: '1px solid #1e293b', borderRadius: 8, padding: 16 }}>
              <h3 style={{ color: '#e2e8f0', fontSize: 14, marginBottom: 12 }}>Policy Recommendations</h3>
              {dsaResult.recommendations.map((rec, i) => (
                <div key={i} style={{ padding: '8px 12px', background: '#08090c', borderRadius: 6, marginBottom: 8, borderLeft: `3px solid ${rec.priority === 'critical' ? '#ef4444' : rec.priority === 'high' ? '#f59e0b' : '#60a5fa'}` }}>
                  <div style={{ color: '#e2e8f0', fontSize: 13, fontWeight: 600 }}>{rec.recommendation}</div>
                  <div style={{ color: '#94a3b8', fontSize: 12, marginTop: 2 }}>{rec.rationale}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* DSA Tab */}
      {tab === 'dsa' && (
        <div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 16, background: '#12131a', border: '1px solid #1e293b', borderRadius: 8, padding: 16 }}>
            {[
              { label: 'Debt Stock ($M)', key: 'debt_stock' },
              { label: 'GDP ($M)', key: 'gdp_nominal' },
              { label: 'Exports ($M)', key: 'exports' },
              { label: 'Revenue ($M)', key: 'revenue' },
              { label: 'Debt Service ($M)', key: 'debt_service' },
              { label: 'Interest ($M)', key: 'interest_payments' },
              { label: 'Principal ($M)', key: 'principal_repayments' },
              { label: 'GFN ($M)', key: 'gross_financing_needs' },
            ].map(f => (
              <div key={f.key}>
                <label style={{ color: '#94a3b8', fontSize: 11, display: 'block', marginBottom: 2 }}>{f.label}</label>
                <input type="number" value={(dsaForm as any)[f.key]} onChange={e => setDsaForm({ ...dsaForm, [f.key]: +e.target.value })}
                  style={{ width: '100%', padding: '6px 8px', background: '#08090c', border: '1px solid #1e293b', borderRadius: 4, color: '#e2e8f0', fontSize: 13 }} />
              </div>
            ))}
          </div>
          <button onClick={runDSA} disabled={loading} style={{ padding: '8px 24px', background: '#c8a951', color: '#08090c', border: 'none', borderRadius: 6, fontWeight: 600, cursor: 'pointer', marginBottom: 24 }}>
            {loading ? 'Computing...' : 'Run DSA Analysis'}
          </button>

          {dsaResult && (
            <>
              <div style={{ background: '#12131a', border: `2px solid ${dsaResult.risk_color}`, borderRadius: 8, padding: 20, marginBottom: 24 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h3 style={{ color: '#e2e8f0', fontSize: 16, margin: 0 }}>Risk Assessment</h3>
                  <span style={{ color: dsaResult.risk_color, fontSize: 20, fontWeight: 700 }}>{dsaResult.risk_label}</span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginTop: 16 }}>
                  {Object.entries(dsaResult.indicators).map(([k, v]) => (
                    <div key={k} style={{ textAlign: 'center' }}>
                      <div style={{ color: '#94a3b8', fontSize: 11, textTransform: 'uppercase' }}>{k.replace(/_/g, ' ')}</div>
                      <div style={{ color: '#e2e8f0', fontSize: 18, fontWeight: 700 }}>{v}%</div>
                    </div>
                  ))}
                </div>
              </div>

              {dsaResult.projections && (
                <div style={{ background: '#12131a', border: '1px solid #1e293b', borderRadius: 8, padding: 16 }}>
                  <h3 style={{ color: '#e2e8f0', fontSize: 14, marginBottom: 12 }}>Debt/GDP Projections (10-year)</h3>
                  <div style={{ display: 'flex', gap: 4, alignItems: 'flex-end', height: 200 }}>
                    {dsaResult.projections.map((p: any, i: number) => (
                      <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                        <div style={{ color: '#94a3b8', fontSize: 10, marginBottom: 4 }}>{p.debt_gdp}%</div>
                        <div style={{
                          width: '100%', height: Math.min(p.debt_gdp * 1.5, 180),
                          background: p.debt_gdp > 70 ? '#ef4444' : p.debt_gdp > 55 ? '#f59e0b' : '#22c55e',
                          borderRadius: 4,
                        }} />
                        <div style={{ color: '#64748b', fontSize: 10, marginTop: 4 }}>Y{i}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Stress Testing Tab */}
      {tab === 'stress' && (
        <div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
            <div style={{ background: '#12131a', border: '1px solid #1e293b', borderRadius: 8, padding: 16 }}>
              <h3 style={{ color: '#e2e8f0', fontSize: 14, marginBottom: 12 }}>Baseline Parameters</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8 }}>
                {[
                  { label: 'Debt ($M)', key: 'debt_stock' },
                  { label: 'GDP ($M)', key: 'gdp' },
                  { label: 'Rate', key: 'interest_rate', step: 0.001 },
                  { label: 'Growth', key: 'baseline_gdp_growth', step: 0.001 },
                ].map(f => (
                  <div key={f.key}>
                    <label style={{ color: '#94a3b8', fontSize: 11 }}>{f.label}</label>
                    <input type="number" step={f.step || 1} value={(baseline as any)[f.key]} onChange={e => setBaseline({ ...baseline, [f.key]: +e.target.value })}
                      style={{ width: '100%', padding: '6px 8px', background: '#08090c', border: '1px solid #1e293b', borderRadius: 4, color: '#e2e8f0', fontSize: 13 }} />
                  </div>
                ))}
              </div>
            </div>
            <div style={{ background: '#12131a', border: '1px solid #1e293b', borderRadius: 8, padding: 16 }}>
              <h3 style={{ color: '#e2e8f0', fontSize: 14, marginBottom: 12 }}>Scenario</h3>
              <select value={scenarioId} onChange={e => setScenarioId(e.target.value)}
                style={{ width: '100%', padding: '8px', background: '#08090c', border: '1px solid #1e293b', borderRadius: 4, color: '#e2e8f0', fontSize: 13, marginBottom: 12 }}>
                {scenarios.map((s: any) => <option key={s.id} value={s.id}>{s.name} ({s.severity})</option>)}
              </select>
              <button onClick={runStress} disabled={loading} style={{ width: '100%', padding: '10px', background: '#c8a951', color: '#08090c', border: 'none', borderRadius: 6, fontWeight: 600, cursor: 'pointer' }}>
                {loading ? 'Running...' : 'Run Stress Test'}
              </button>
            </div>
          </div>

          {stressResult && (
            <div style={{ background: '#12131a', border: `2px solid ${stressResult.severity_color}`, borderRadius: 8, padding: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
                <h3 style={{ color: '#e2e8f0', fontSize: 14, margin: 0 }}>Result</h3>
                <span style={{ color: stressResult.severity_color, fontWeight: 700 }}>{stressResult.severity_label}</span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 16 }}>
                <div><span style={{ color: '#94a3b8', fontSize: 11 }}>Initial Debt/GDP</span><div style={{ color: '#e2e8f0', fontSize: 18, fontWeight: 700 }}>{stressResult.initial_debt_gdp}%</div></div>
                <div><span style={{ color: '#94a3b8', fontSize: 11 }}>Final Debt/GDP</span><div style={{ color: stressResult.severity_color, fontSize: 18, fontWeight: 700 }}>{stressResult.final_debt_gdp}%</div></div>
                <div><span style={{ color: '#94a3b8', fontSize: 11 }}>Debt Path</span><div style={{ color: '#e2e8f0', fontSize: 18, fontWeight: 700, textTransform: 'capitalize' }}>{stressResult.debt_path}</div></div>
              </div>
              {stressResult.projections && (
                <div style={{ display: 'flex', gap: 4, alignItems: 'flex-end', height: 150 }}>
                  {stressResult.projections.filter((_: any, i: number) => i % 2 === 0).map((p: any, i: number) => (
                    <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                      <div style={{ width: '100%', height: Math.min(p.debt_gdp * 1.2, 140), background: p.debt_gdp > 70 ? '#ef4444' : p.debt_gdp > 55 ? '#f59e0b' : '#22c55e', borderRadius: 4 }} />
                      <div style={{ color: '#64748b', fontSize: 10, marginTop: 4 }}>Y{p.year}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Maturity Tab */}
      {tab === 'maturity' && maturity && (
        <div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 24 }}>
            {[
              { label: 'Total Outstanding', value: `$${(maturity.total_outstanding / 1000).toFixed(1)}B` },
              { label: 'Avg Maturity', value: `${maturity.avg_maturity_years}yr` },
              { label: 'Weighted Coupon', value: `${maturity.weighted_avg_coupon_pct}%` },
              { label: 'Annual Interest', value: `$${(maturity.annual_interest_estimate / 1000).toFixed(1)}B` },
            ].map((c, i) => (
              <div key={i} style={{ background: '#12131a', border: '1px solid #1e293b', borderRadius: 8, padding: 16 }}>
                <div style={{ color: '#94a3b8', fontSize: 11 }}>{c.label}</div>
                <div style={{ color: '#c8a951', fontSize: 20, fontWeight: 700 }}>{c.value}</div>
              </div>
            ))}
          </div>

          {/* Maturity Buckets */}
          <div style={{ background: '#12131a', border: '1px solid #1e293b', borderRadius: 8, padding: 16, marginBottom: 24 }}>
            <h3 style={{ color: '#e2e8f0', fontSize: 14, marginBottom: 12 }}>Maturity Profile</h3>
            <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end', height: 200 }}>
              {Object.entries(maturity.buckets || {}).map(([k, v]: [string, any]) => (
                <div key={k} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                  <div style={{ color: '#94a3b8', fontSize: 10, marginBottom: 4 }}>{v.pct_of_total}%</div>
                  <div style={{ width: '100%', height: Math.max(v.pct_of_total * 1.8, 4), background: k === '0-1Y' || k === '1-2Y' ? '#ef4444' : k === '2-3Y' || k === '3-5Y' ? '#f59e0b' : '#22c55e', borderRadius: 4 }} />
                  <div style={{ color: '#64748b', fontSize: 10, marginTop: 4 }}>{k}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Concentration Alerts */}
          {maturity.concentration_risk?.alerts?.length > 0 && (
            <div style={{ background: '#12131a', border: '1px solid #ef4444', borderRadius: 8, padding: 16 }}>
              <h3 style={{ color: '#ef4444', fontSize: 14, marginBottom: 8 }}>Concentration Risk Alerts</h3>
              {maturity.concentration_risk.alerts.map((a: string, i: number) => (
                <div key={i} style={{ color: '#e2e8f0', fontSize: 13, padding: '4px 0' }}>⚠ {a}</div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Fiscal Tab */}
      {tab === 'fiscal' && fiscal && !fiscal.error && (
        <div style={{ background: '#12131a', border: '1px solid #1e293b', borderRadius: 8, padding: 16 }}>
          <h3 style={{ color: '#e2e8f0', fontSize: 14, marginBottom: 16 }}>FY {fiscal.fiscal_year}</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
            <div>
              <h4 style={{ color: '#94a3b8', fontSize: 12, marginBottom: 8 }}>Revenue</h4>
              {Object.entries(fiscal.budget?.revenue_breakdown || {}).map(([k, v]: [string, any]) => (
                <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', borderBottom: '1px solid #1e293b', fontSize: 13 }}>
                  <span style={{ color: '#94a3b8' }}>{k.replace(/_/g, ' ')}</span>
                  <span style={{ color: '#22c55e' }}>${(v / 1000).toFixed(1)}B</span>
                </div>
              ))}
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', fontWeight: 700, fontSize: 14 }}>
                <span style={{ color: '#e2e8f0' }}>Total</span>
                <span style={{ color: '#22c55e' }}>${(fiscal.budget?.total_revenue / 1000).toFixed(1)}B</span>
              </div>
            </div>
            <div>
              <h4 style={{ color: '#94a3b8', fontSize: 12, marginBottom: 8 }}>Expenditure</h4>
              {Object.entries(fiscal.budget?.expenditure_breakdown || {}).map(([k, v]: [string, any]) => (
                <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', borderBottom: '1px solid #1e293b', fontSize: 13 }}>
                  <span style={{ color: '#94a3b8' }}>{k.replace(/_/g, ' ')}</span>
                  <span style={{ color: '#ef4444' }}>${(v / 1000).toFixed(1)}B</span>
                </div>
              ))}
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', fontWeight: 700, fontSize: 14 }}>
                <span style={{ color: '#e2e8f0' }}>Total</span>
                <span style={{ color: '#ef4444' }}>${(fiscal.budget?.total_expenditure / 1000).toFixed(1)}B</span>
              </div>
            </div>
            <div>
              <h4 style={{ color: '#94a3b8', fontSize: 12, marginBottom: 8 }}>Fiscal Balance</h4>
              <div style={{ fontSize: 24, fontWeight: 700, color: fiscal.budget?.fiscal_balance >= 0 ? '#22c55e' : '#ef4444', marginBottom: 8 }}>
                {fiscal.budget?.fiscal_balance >= 0 ? '+' : ''}{fiscal.budget?.fiscal_balance_gdp_pct}% GDP
              </div>
              <div style={{ fontSize: 13, color: '#94a3b8' }}>
                Revenue: {fiscal.budget?.revenue_gdp_pct}% GDP<br />
                Expenditure: {fiscal.budget?.expenditure_gdp_pct}% GDP
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Audit Tab */}
      {tab === 'audit' && (
        <div>
          <div style={{ background: '#12131a', border: '1px solid #1e293b', borderRadius: 8, padding: 16 }}>
            <h3 style={{ color: '#e2e8f0', fontSize: 14, marginBottom: 12 }}>Audit Log ({auditLog.length} events)</h3>
            {auditLog.length === 0 ? (
              <p style={{ color: '#64748b', textAlign: 'center', padding: 24 }}>No audit events yet. Events will appear as users interact with the system.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {auditLog.map((entry, i) => (
                  <div key={i} style={{ display: 'grid', gridTemplateColumns: '180px 100px 1fr 200px', gap: 12, padding: '8px 12px', background: '#08090c', borderRadius: 4, fontSize: 12 }}>
                    <span style={{ color: '#94a3b8' }}>{new Date(entry.timestamp).toLocaleString()}</span>
                    <span style={{ color: entry.action.includes('delete') ? '#ef4444' : entry.action.includes('create') ? '#22c55e' : '#60a5fa', fontWeight: 600 }}>{entry.action}</span>
                    <span style={{ color: '#e2e8f0' }}>{entry.resource}</span>
                    <span style={{ color: '#64748b' }}>by {entry.user_id}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
