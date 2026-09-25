import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

interface Dashboard {
  total_certifications: number;
  certified: number;
  total_impact_assessments: number;
  validated: number;
  total_stress_tests: number;
  passed_tests: number;
  total_settlements: number;
  settled: number;
  total_disclosures: number;
  published: number;
  avg_compliance_score: number;
  avg_risk_score: number;
}

interface Certification {
  id: string;
  certification_name: string;
  certification_type: string;
  issuing_authority: string;
  jurisdiction: string;
  status: string;
  compliance_score: number;
  data_quality_score: number;
  data_lineage_verified: boolean;
  traceability_enabled: boolean;
  decision_logging_enabled: boolean;
  audit_trail_completeness: number;
}

interface ImpactAssessment {
  id: string;
  assessment_name: string;
  model_name: string;
  model_version: string;
  assessor_name: string;
  assessor_organization: string;
  impact_severity: string;
  risk_score: number;
  validation_status: string;
  independent_validator: string;
  kill_switch_enabled: boolean;
  human_oversight_required: boolean;
}

interface StressTest {
  id: string;
  test_name: string;
  test_type: string;
  scenario_name: string;
  shock_magnitude_pct: number;
  result: string;
  portfolio_impact_pct: number;
  max_drawdown_pct: number;
  flash_crash_threshold_bps: number;
  circuit_breaker_triggered: boolean;
}

interface Settlement {
  id: string;
  settlement_reference: string;
  settlement_network: string;
  origin_jurisdiction: string;
  destination_jurisdiction: string;
  origin_currency: string;
  destination_currency: string;
  amount_origin: number;
  amount_destination: number;
  exchange_rate: number;
  status: string;
  compliance_checks_passed: boolean;
  aml_screening_passed: boolean;
  blockchain_tx_hash: string;
}

interface Disclosure {
  id: string;
  title: string;
  disclosure_type: string;
  target_audience: string;
  status: string;
  version: string;
  language: string;
  publication_date: string;
  executive_summary: string;
}

const TABS = ['certifications', 'impact-assessments', 'stress-tests', 'settlements', 'disclosures'] as const;

export default function RegulatoryCompliancePage() {
  const [activeTab, setActiveTab] = useState<string>('certifications');
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [certifications, setCertifications] = useState<Certification[]>([]);
  const [impactAssessments, setImpactAssessments] = useState<ImpactAssessment[]>([]);
  const [stressTests, setStressTests] = useState<StressTest[]>([]);
  const [settlements, setSettlements] = useState<Settlement[]>([]);
  const [disclosures, setDisclosures] = useState<Disclosure[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [dashRes, certRes, impactRes, stressRes, settleRes, discRes] = await Promise.all([
        fetch('/api/regulatory/dashboard'),
        fetch('/api/regulatory/certifications'),
        fetch('/api/regulatory/impact-assessments'),
        fetch('/api/regulatory/stress-tests'),
        fetch('/api/regulatory/settlements'),
        fetch('/api/regulatory/disclosures'),
      ]);
      if (dashRes.ok) setDashboard(await dashRes.json());
      if (certRes.ok) { const d = await certRes.json(); setCertifications(d.certifications || []); }
      if (impactRes.ok) { const d = await impactRes.json(); setImpactAssessments(d.impact_assessments || []); }
      if (stressRes.ok) { const d = await stressRes.json(); setStressTests(d.stress_tests || []); }
      if (settleRes.ok) { const d = await settleRes.json(); setSettlements(d.settlements || []); }
      if (discRes.ok) { const d = await discRes.json(); setDisclosures(d.disclosures || []); }
    } catch {}
    setLoading(false);
  };

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      certified: '#22c55e', expired: '#ef4444', pending: '#e8e8ea', revoked: '#ef4444',
      validated: '#22c55e', failed: '#ef4444', in_review: '#38bdf8',
      passed: '#22c55e', failed_test: '#ef4444',
      settled: '#22c55e', pending_settlement: '#e8e8ea', failed_settlement: '#ef4444',
      published: '#22c55e', draft: '#6b7280', archived: '#9ca3af',
      high: '#ef4444', critical: '#ef4444', medium: '#38bdf8', low: '#22c55e',
    };
    return (
      <span style={{
        padding: '2px 8px', borderRadius: 4, fontSize: 12, fontWeight: 600,
        background: `${colors[status] || '#6b7280'}20`, color: colors[status] || '#6b7280',
      }}>
        {status.replace(/_/g, ' ')}
      </span>
    );
  };

  const getBooleanBadge = (value: boolean) => (
    <span style={{
      padding: '2px 8px', borderRadius: 4, fontSize: 12, fontWeight: 600,
      background: value ? '#22c55e20' : '#ef444420', color: value ? '#22c55e' : '#ef4444',
    }}>
      {value ? 'Yes' : 'No'}
    </span>
  );

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: 24 }}>
      <nav style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
        <Link to="/">← Home</Link>
        <Link to="/government">Government</Link>
        <Link to="/ai-governance">AI Governance</Link>
        <Link to="/exchange-integration">Exchange</Link>
        <Link to="/broker-integration">Broker</Link>
        <Link to="/cybersecurity-privacy">Cybersecurity</Link>
      </nav>

      <h1 style={{ color: '#e8e8ea', marginBottom: 4 }}>Regulatory Compliance</h1>
      <p style={{ color: '#9ca3af', marginBottom: 24 }}>
        Certifications, impact assessments, stress testing, settlement compliance, and regulatory disclosures.
      </p>

      {/* Dashboard Summary */}
      {dashboard && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 12, marginBottom: 24 }}>
          {[
            { label: 'Certifications', value: `${dashboard.certified}/${dashboard.total_certifications}`, color: '#22c55e', icon: '📜' },
            { label: 'Impact Assessments', value: `${dashboard.validated}/${dashboard.total_impact_assessments}`, color: '#3b82f6', icon: '📋' },
            { label: 'Stress Tests', value: `${dashboard.passed_tests}/${dashboard.total_stress_tests}`, color: dashboard.passed_tests >= dashboard.total_stress_tests ? '#22c55e' : '#38bdf8', icon: '🔬' },
            { label: 'Settlements', value: `${dashboard.settled}/${dashboard.total_settlements}`, color: '#e8e8ea', icon: '💰' },
            { label: 'Disclosures', value: `${dashboard.published}/${dashboard.total_disclosures}`, color: '#8b5cf6', icon: '📄' },
            { label: 'Avg Compliance', value: `${dashboard.avg_compliance_score.toFixed(1)}%`, color: dashboard.avg_compliance_score > 80 ? '#22c55e' : '#38bdf8', icon: '📊' },
          ].map((item) => (
            <div key={item.label} style={{
              padding: 16, background: '#111318', border: '1px solid #1f2937', borderRadius: 8, textAlign: 'center',
            }}>
              <div style={{ fontSize: 20, marginBottom: 4 }}>{item.icon}</div>
              <div style={{ color: item.color, fontSize: 24, fontWeight: 700 }}>{item.value}</div>
              <div style={{ color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>{item.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 20, borderBottom: '1px solid #1f2937', paddingBottom: 8 }}>
        {TABS.map((tab) => (
          <button key={tab} onClick={() => setActiveTab(tab)} style={{
            padding: '8px 16px', background: activeTab === tab ? '#e8e8ea' : 'transparent',
            color: activeTab === tab ? '#000' : '#9ca3af', border: 'none', borderRadius: 6,
            cursor: 'pointer', fontWeight: 600, textTransform: 'capitalize',
          }}>{tab.replace(/-/g, ' ')}</button>
        ))}
      </div>

      {/* Certifications */}
      {activeTab === 'certifications' && (
        <div style={{ background: '#111318', border: '1px solid #1f2937', borderRadius: 12, padding: 24 }}>
          <h3 style={{ color: '#e5e7eb', marginBottom: 8 }}>Certifications</h3>
          <p style={{ color: '#6b7280', marginBottom: 16, fontSize: 13 }}>
            Regulatory certifications, compliance scores, and audit trail completeness for AI systems.
          </p>
          {certifications.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: '#6b7280' }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>📜</div>
              <div>No certifications found.</div>
              <div style={{ fontSize: 13, marginTop: 8 }}>Add via <code>POST /api/regulatory/certifications</code></div>
            </div>
          ) : (
            <div style={{ display: 'grid', gap: 12 }}>
              {certifications.map((cert) => (
                <div key={cert.id} style={{
                  padding: 16, background: '#0d0f13', border: '1px solid #1f2937', borderRadius: 8,
                  display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12,
                }}>
                  <div>
                    <div style={{ color: '#e5e7eb', fontWeight: 600 }}>{cert.certification_name}</div>
                    <div style={{ color: '#6b7280', fontSize: 13 }}>{cert.certification_type}</div>
                    <div style={{ color: '#9ca3af', fontSize: 12, marginTop: 4 }}>{cert.issuing_authority} • {cert.jurisdiction}</div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 12 }}>
                    <div>
                      <span style={{ color: '#6b7280' }}>Compliance: </span>
                      <span style={{ color: cert.compliance_score > 80 ? '#22c55e' : '#ef4444', fontWeight: 600 }}>
                        {cert.compliance_score}%
                      </span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Data Quality: </span>
                      <span style={{ color: '#e8e8ea', fontWeight: 600 }}>{cert.data_quality_score}%</span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Audit Trail: </span>
                      <span style={{ color: '#e8e8ea', fontWeight: 600 }}>{cert.audit_trail_completeness}%</span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Lineage Verified: </span>
                      {getBooleanBadge(cert.data_lineage_verified)}
                    </div>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', justifyContent: 'space-between' }}>
                    {getStatusBadge(cert.status)}
                    <div style={{ display: 'flex', gap: 6 }}>
                      {getBooleanBadge(cert.traceability_enabled)}
                      {getBooleanBadge(cert.decision_logging_enabled)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Impact Assessments */}
      {activeTab === 'impact-assessments' && (
        <div style={{ background: '#111318', border: '1px solid #1f2937', borderRadius: 12, padding: 24 }}>
          <h3 style={{ color: '#e5e7eb', marginBottom: 8 }}>Impact Assessments</h3>
          <p style={{ color: '#6b7280', marginBottom: 16, fontSize: 13 }}>
            AI model impact evaluations, risk scoring, and independent validation status.
          </p>
          {impactAssessments.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: '#6b7280' }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>📋</div>
              <div>No impact assessments found.</div>
            </div>
          ) : (
            <div style={{ display: 'grid', gap: 12 }}>
              {impactAssessments.map((item) => (
                <div key={item.id} style={{
                  padding: 16, background: '#0d0f13', border: '1px solid #1f2937', borderRadius: 8,
                  display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12,
                }}>
                  <div>
                    <div style={{ color: '#e5e7eb', fontWeight: 600 }}>{item.assessment_name}</div>
                    <div style={{ color: '#6b7280', fontSize: 13 }}>{item.model_name} v{item.model_version}</div>
                    <div style={{ color: '#9ca3af', fontSize: 12, marginTop: 4 }}>
                      {item.assessor_name} • {item.assessor_organization}
                    </div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 12 }}>
                    <div>
                      <span style={{ color: '#6b7280' }}>Severity: </span>
                      {getStatusBadge(item.impact_severity)}
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Risk Score: </span>
                      <span style={{ color: item.risk_score > 70 ? '#ef4444' : item.risk_score > 40 ? '#38bdf8' : '#22c55e', fontWeight: 600 }}>
                        {item.risk_score}
                      </span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Validator: </span>
                      <span style={{ color: '#9ca3af' }}>{item.independent_validator}</span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Kill Switch: </span>
                      {getBooleanBadge(item.kill_switch_enabled)}
                    </div>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', justifyContent: 'space-between' }}>
                    {getStatusBadge(item.validation_status)}
                    <div style={{ fontSize: 12, color: '#6b7280' }}>
                      Human Oversight: {getBooleanBadge(item.human_oversight_required)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Stress Tests */}
      {activeTab === 'stress-tests' && (
        <div style={{ background: '#111318', border: '1px solid #1f2937', borderRadius: 12, padding: 24 }}>
          <h3 style={{ color: '#e5e7eb', marginBottom: 8 }}>Stress Tests</h3>
          <p style={{ color: '#6b7280', marginBottom: 16, fontSize: 13 }}>
            Portfolio stress testing, shock analysis, and circuit breaker validation.
          </p>
          {stressTests.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: '#6b7280' }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>🔬</div>
              <div>No stress tests found.</div>
            </div>
          ) : (
            <div style={{ display: 'grid', gap: 12 }}>
              {stressTests.map((test) => (
                <div key={test.id} style={{
                  padding: 16, background: '#0d0f13', border: '1px solid #1f2937', borderRadius: 8,
                  display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12,
                }}>
                  <div>
                    <div style={{ color: '#e5e7eb', fontWeight: 600 }}>{test.test_name}</div>
                    <div style={{ color: '#6b7280', fontSize: 13 }}>{test.test_type} • {test.scenario_name}</div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 12 }}>
                    <div>
                      <span style={{ color: '#6b7280' }}>Shock Magnitude: </span>
                      <span style={{ color: '#ef4444', fontWeight: 600 }}>{test.shock_magnitude_pct}%</span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Portfolio Impact: </span>
                      <span style={{ color: test.portfolio_impact_pct < 0 ? '#ef4444' : '#22c55e', fontWeight: 600 }}>
                        {test.portfolio_impact_pct}%
                      </span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Max Drawdown: </span>
                      <span style={{ color: '#ef4444', fontWeight: 600 }}>{test.max_drawdown_pct}%</span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Flash Crash: </span>
                      <span style={{ color: '#38bdf8', fontWeight: 600 }}>{test.flash_crash_threshold_bps} bps</span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', justifyContent: 'space-between' }}>
                    {getStatusBadge(test.result)}
                    <div style={{ fontSize: 12, color: '#6b7280' }}>
                      Circuit Breaker: {getBooleanBadge(test.circuit_breaker_triggered)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Settlements */}
      {activeTab === 'settlements' && (
        <div style={{ background: '#111318', border: '1px solid #1f2937', borderRadius: 12, padding: 24 }}>
          <h3 style={{ color: '#e5e7eb', marginBottom: 8 }}>Settlements</h3>
          <p style={{ color: '#6b7280', marginBottom: 16, fontSize: 13 }}>
            Cross-border settlement tracking, AML screening, and blockchain verification.
          </p>
          {settlements.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: '#6b7280' }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>💰</div>
              <div>No settlements found.</div>
            </div>
          ) : (
            <div style={{ display: 'grid', gap: 12 }}>
              {settlements.map((s) => (
                <div key={s.id} style={{
                  padding: 16, background: '#0d0f13', border: '1px solid #1f2937', borderRadius: 8,
                  display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12,
                }}>
                  <div>
                    <div style={{ color: '#e5e7eb', fontWeight: 600 }}>{s.settlement_reference}</div>
                    <div style={{ color: '#6b7280', fontSize: 13 }}>{s.settlement_network}</div>
                    <div style={{ color: '#9ca3af', fontSize: 12, marginTop: 4 }}>
                      {s.origin_jurisdiction} → {s.destination_jurisdiction}
                    </div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 12 }}>
                    <div>
                      <span style={{ color: '#6b7280' }}>Amount: </span>
                      <span style={{ color: '#e8e8ea', fontWeight: 600 }}>
                        {s.amount_origin.toLocaleString()} {s.origin_currency}
                      </span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Destination: </span>
                      <span style={{ color: '#e8e8ea', fontWeight: 600 }}>
                        {s.amount_destination.toLocaleString()} {s.destination_currency}
                      </span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Rate: </span>
                      <span style={{ color: '#9ca3af' }}>{s.exchange_rate}</span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>AML: </span>
                      {getBooleanBadge(s.aml_screening_passed)}
                    </div>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', justifyContent: 'space-between' }}>
                    {getStatusBadge(s.status)}
                    <div style={{ fontSize: 12, color: '#6b7280' }}>
                      Compliance: {getBooleanBadge(s.compliance_checks_passed)}
                    </div>
                    {s.blockchain_tx_hash && (
                      <div style={{ fontSize: 11, color: '#9ca3af', fontFamily: 'monospace', wordBreak: 'break-all', textAlign: 'right' }}>
                        Tx: {s.blockchain_tx_hash.slice(0, 16)}...
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Disclosures */}
      {activeTab === 'disclosures' && (
        <div style={{ background: '#111318', border: '1px solid #1f2937', borderRadius: 12, padding: 24 }}>
          <h3 style={{ color: '#e5e7eb', marginBottom: 8 }}>Disclosures</h3>
          <p style={{ color: '#6b7280', marginBottom: 16, fontSize: 13 }}>
            Regulatory disclosures, publication tracking, and executive summaries.
          </p>
          {disclosures.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: '#6b7280' }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>📄</div>
              <div>No disclosures found.</div>
            </div>
          ) : (
            <div style={{ display: 'grid', gap: 12 }}>
              {disclosures.map((d) => (
                <div key={d.id} style={{
                  padding: 16, background: '#0d0f13', border: '1px solid #1f2937', borderRadius: 8,
                  display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: 12,
                }}>
                  <div>
                    <div style={{ color: '#e5e7eb', fontWeight: 600 }}>{d.title}</div>
                    <div style={{ color: '#6b7280', fontSize: 13, marginTop: 4 }}>{d.executive_summary}</div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 12 }}>
                    <div>
                      <span style={{ color: '#6b7280' }}>Type: </span>
                      <span style={{ color: '#e8e8ea' }}>{d.disclosure_type}</span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Audience: </span>
                      <span style={{ color: '#9ca3af' }}>{d.target_audience}</span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Language: </span>
                      <span style={{ color: '#9ca3af' }}>{d.language}</span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Version: </span>
                      <span style={{ color: '#9ca3af' }}>{d.version}</span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', justifyContent: 'space-between' }}>
                    {getStatusBadge(d.status)}
                    {d.publication_date && (
                      <div style={{ fontSize: 12, color: '#9ca3af' }}>
                        Published: {new Date(d.publication_date).toLocaleDateString()}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
