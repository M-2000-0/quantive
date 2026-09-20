import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

interface Dashboard {
  monitoring: { total: number; active: number };
  cybersecurity: { total: number; compliant: number; total_vulnerabilities: number; remediated: number };
  privacy: { total: number; compliant: number };
  interoperability: { total: number; supported: number };
  scores: { security: number; privacy: number; compatibility: number };
}

interface Monitor {
  id: string; monitor_name: string; status: string;
  target_model_name: string; sampling_interval_seconds: number;
  accuracy_threshold: number; latency_threshold_ms: number;
  drift_threshold_pct: number; current_accuracy: number | null;
  current_latency_ms: number | null; current_drift_pct: number | null;
  total_signals_captured: number; total_alerts_fired: number;
}

interface Control {
  id: string; control_name: string; control_type: string; status: string;
  encryption_algorithm: string; key_length_bits: number | null;
  adversarial_robustness_score: number | null;
  model_integrity_verification: boolean; security_score: number;
  vulnerabilities_found: number; vulnerabilities_remediated: number;
}

interface Policy {
  id: string; policy_name: string; framework: string;
  data_classification: string; is_compliant: boolean;
  encryption_required: boolean; anonymization_required: boolean;
  data_retention_days: number; right_to_erasure: boolean;
  breach_notification_hours: number; dpia_completed: boolean;
  privacy_score: number;
}

interface Standard {
  id: string; standard_name: string; framework: string; status: string;
  jurisdictions: string[]; asset_types: string[];
  aml_kyc_standard: string; settlement_systems: string[];
  compatibility_score: number; messages_processed: number;
  error_rate_pct: number;
}

const PAGE_BG = '#08090c';
const CARD_BG = '#111318';
const CARD_BORDER = '#23272e';
const TEXT = '#e5e7eb';
const TEXT_DIM = '#9ca3af';
const GOLD = '#c8a951';
const GREEN = '#22c55e';
const RED = '#ef4444';
const YELLOW = '#f59e0b';
const BLUE = '#3b82f6';
const PURPLE = '#a855f7';
const CYAN = '#06b6d4';

function getStatusBadge(status: string) {
  const map: Record<string, { bg: string; color: string }> = {
    active: { bg: '#22c55e20', color: GREEN },
    compliant: { bg: '#22c55e20', color: GREEN },
    supported: { bg: '#22c55e20', color: GREEN },
    paused: { bg: '#f59e0b20', color: YELLOW },
    in_progress: { bg: '#f59e0b20', color: YELLOW },
    partial: { bg: '#f59e0b20', color: YELLOW },
    non_compliant: { bg: '#ef444420', color: RED },
    error: { bg: '#ef444420', color: RED },
    planned: { bg: '#3b82f620', color: BLUE },
    not_supported: { bg: '#ef444420', color: RED },
  };
  const s = map[status] || { bg: '#6b728020', color: '#9ca3af' };
  return (
    <span style={{ padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600, background: s.bg, color: s.color, textTransform: 'capitalize' as const }}>
      {status.replace(/_/g, ' ')}
    </span>
  );
}

function getBooleanBadge(val: boolean) {
  return val ? (
    <span style={{ padding: '2px 6px', borderRadius: 3, fontSize: 10, background: '#22c55e18', color: GREEN }}>ON</span>
  ) : (
    <span style={{ padding: '2px 6px', borderRadius: 3, fontSize: 10, background: '#ef444418', color: RED }}>OFF</span>
  );
}

export default function CybersecurityPrivacyPage() {
  const [tab, setTab] = useState('monitoring');
  const [dash, setDash] = useState<Dashboard | null>(null);
  const [monitors, setMonitors] = useState<Monitor[]>([]);
  const [controls, setControls] = useState<Control[]>([]);
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [standards, setStandards] = useState<Standard[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const org = 'a81db73c-1719-4fe5-982c-7bf4cfa1408b';
    Promise.all([
      fetch(`/api/security/dashboard?org_id=${org}`).then(r => r.json()),
      fetch(`/api/security/monitoring?org_id=${org}`).then(r => r.json()),
      fetch(`/api/security/cybersecurity?org_id=${org}`).then(r => r.json()),
      fetch(`/api/security/privacy?org_id=${org}`).then(r => r.json()),
      fetch(`/api/security/interoperability?org_id=${org}`).then(r => r.json()),
    ]).then(([d, m, c, p, i]) => {
      setDash(d);
      setMonitors(m.monitoring || []);
      setControls(c.controls || []);
      setPolicies(p.policies || []);
      setStandards(i.standards || []);
      setLoading(false);
    });
  }, []);

  const tabs = [
    { key: 'monitoring', label: 'Regulatory Monitoring' },
    { key: 'cybersecurity', label: 'Cybersecurity' },
    { key: 'privacy', label: 'Data Privacy' },
    { key: 'interoperability', label: 'Interoperability' },
  ];

  return (
    <div style={{ padding: 24, background: PAGE_BG, minHeight: '100vh', fontFamily: "'Inter', -apple-system, sans-serif" }}>
      <div style={{ maxWidth: 1400, margin: '0 auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 700, color: TEXT, margin: 0 }}>
              <span style={{ color: GOLD }}>{'🛡️'}</span> Cybersecurity, Privacy & Interoperability
            </h1>
            <p style={{ fontSize: 13, color: TEXT_DIM, margin: '4px 0 0 0' }}>
              Real-time regulatory monitoring, AI-specific cybersecurity, GDPR compliance, cross-framework interoperability
            </p>
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            {[
              { to: '/regulatory-compliance', label: 'Regulatory' },
              { to: '/exchange-due-diligence', label: 'Due Diligence' },
              { to: '/exchange-integration', label: 'Exchanges' },
              { to: '/validation-vendor-risk', label: 'Validation & Vendors' },
            ].map(link => (
              <Link key={link.to} to={link.to} style={{
                padding: '6px 12px', borderRadius: 6, fontSize: 12, fontWeight: 500,
                background: CARD_BG, border: `1px solid ${CARD_BORDER}`, color: TEXT_DIM, textDecoration: 'none',
              }}>{link.label}</Link>
            ))}
          </div>
        </div>

        {dash && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 12, marginBottom: 24 }}>
            {[
              { label: 'Active Monitors', value: dash.monitoring.active, color: GREEN },
              { label: 'Security Score', value: `${dash.scores.security}%`, color: GOLD },
              { label: 'Compliant Controls', value: dash.cybersecurity.compliant, color: GREEN },
              { label: 'Privacy Score', value: `${dash.scores.privacy}%`, color: CYAN },
              { label: 'Supported Standards', value: dash.interoperability.supported, color: BLUE },
              { label: 'Vulnerabilities Fixed', value: dash.cybersecurity.remediated, color: GREEN },
            ].map((m, i) => (
              <div key={i} style={{ padding: '14px 16px', borderRadius: 8, background: CARD_BG, border: `1px solid ${CARD_BORDER}` }}>
                <div style={{ fontSize: 11, color: TEXT_DIM, marginBottom: 6 }}>{m.label}</div>
                <div style={{ fontSize: 22, fontWeight: 700, color: m.color }}>{m.value}</div>
              </div>
            ))}
          </div>
        )}

        <div style={{ display: 'flex', gap: 4, marginBottom: 20, background: CARD_BG, borderRadius: 8, padding: 4, border: `1px solid ${CARD_BORDER}` }}>
          {tabs.map(t => (
            <button key={t.key} onClick={() => setTab(t.key)} style={{
              padding: '8px 16px', borderRadius: 6, border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 600,
              background: tab === t.key ? '#c8a95120' : 'transparent',
              color: tab === t.key ? GOLD : TEXT_DIM,
              transition: 'all 0.15s',
            }}>{t.label}</button>
          ))}
        </div>

        {loading ? (
          <div style={{ padding: 60, textAlign: 'center', color: TEXT_DIM, fontSize: 14 }}>Loading...</div>
        ) : (
          <>
            {tab === 'monitoring' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {monitors.length === 0 ? (
                  <div style={{ padding: 60, textAlign: 'center', color: TEXT_DIM, fontSize: 14, background: CARD_BG, borderRadius: 8, border: `1px solid ${CARD_BORDER}` }}>
                    No regulatory monitors configured
                  </div>
                ) : monitors.map(m => (
                  <div key={m.id} style={{ padding: '16px 20px', borderRadius: 8, background: CARD_BG, border: `1px solid ${CARD_BORDER}`, display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr 1fr', gap: 16, alignItems: 'center' }}>
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 600, color: TEXT, marginBottom: 4 }}>{m.monitor_name}</div>
                      <div style={{ fontSize: 11, color: TEXT_DIM }}>{m.target_model_name}</div>
                      <div style={{ marginTop: 4 }}>{getStatusBadge(m.status)}</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 10, color: TEXT_DIM, marginBottom: 2 }}>Accuracy</div>
                      <div style={{ fontSize: 18, fontWeight: 700, color: m.current_accuracy && m.current_accuracy >= m.accuracy_threshold ? GREEN : RED }}>
                        {m.current_accuracy ? `${(m.current_accuracy * 100).toFixed(1)}%` : '--'}
                      </div>
                      <div style={{ fontSize: 10, color: TEXT_DIM }}>thresh: {(m.accuracy_threshold * 100).toFixed(0)}%</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 10, color: TEXT_DIM, marginBottom: 2 }}>Latency</div>
                      <div style={{ fontSize: 18, fontWeight: 700, color: m.current_latency_ms && m.current_latency_ms <= m.latency_threshold_ms ? GREEN : RED }}>
                        {m.current_latency_ms ? `${m.current_latency_ms.toFixed(0)}ms` : '--'}
                      </div>
                      <div style={{ fontSize: 10, color: TEXT_DIM }}>thresh: {m.latency_threshold_ms}ms</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 10, color: TEXT_DIM, marginBottom: 2 }}>Drift</div>
                      <div style={{ fontSize: 18, fontWeight: 700, color: m.current_drift_pct && m.current_drift_pct <= m.drift_threshold_pct ? GREEN : RED }}>
                        {m.current_drift_pct ? `${m.current_drift_pct.toFixed(2)}%` : '--'}
                      </div>
                      <div style={{ fontSize: 10, color: TEXT_DIM }}>thresh: {m.drift_threshold_pct}%</div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: 11, color: TEXT_DIM }}>Signals: <span style={{ color: GOLD, fontWeight: 600 }}>{m.total_signals_captured}</span></div>
                      <div style={{ fontSize: 11, color: TEXT_DIM }}>Alerts: <span style={{ color: m.total_alerts_fired > 0 ? RED : GREEN, fontWeight: 600 }}>{m.total_alerts_fired}</span></div>
                      <div style={{ fontSize: 11, color: TEXT_DIM }}>Interval: {m.sampling_interval_seconds}s</div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {tab === 'cybersecurity' && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
                {controls.length === 0 ? (
                  <div style={{ gridColumn: '1 / -1', padding: 60, textAlign: 'center', color: TEXT_DIM, fontSize: 14, background: CARD_BG, borderRadius: 8, border: `1px solid ${CARD_BORDER}` }}>
                    No cybersecurity controls configured
                  </div>
                ) : controls.map(c => (
                  <div key={c.id} style={{ padding: '16px 20px', borderRadius: 8, background: CARD_BG, border: `1px solid ${CARD_BORDER}` }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 600, color: TEXT }}>{c.control_name}</div>
                        <div style={{ fontSize: 11, color: TEXT_DIM, textTransform: 'capitalize' as const }}>{c.control_type.replace(/_/g, ' ')}</div>
                      </div>
                      {getStatusBadge(c.status)}
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 12 }}>
                      <div style={{ padding: 8, borderRadius: 6, background: '#08090c' }}>
                        <div style={{ fontSize: 10, color: TEXT_DIM }}>Security Score</div>
                        <div style={{ fontSize: 18, fontWeight: 700, color: c.security_score >= 80 ? GREEN : c.security_score >= 60 ? YELLOW : RED }}>{c.security_score}%</div>
                      </div>
                      <div style={{ padding: 8, borderRadius: 6, background: '#08090c' }}>
                        <div style={{ fontSize: 10, color: TEXT_DIM }}>Adversarial</div>
                        <div style={{ fontSize: 18, fontWeight: 700, color: c.adversarial_robustness_score && c.adversarial_robustness_score >= 80 ? GREEN : YELLOW }}>
                          {c.adversarial_robustness_score ? `${c.adversarial_robustness_score}%` : '--'}
                        </div>
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
                      <span style={{ fontSize: 11, color: TEXT_DIM }}>Model Integrity: {getBooleanBadge(c.model_integrity_verification)}</span>
                      <span style={{ fontSize: 11, color: TEXT_DIM }}>Vulns: <span style={{ color: c.vulnerabilities_found > 0 ? RED : GREEN, fontWeight: 600 }}>{c.vulnerabilities_found}</span></span>
                    </div>
                    {c.encryption_algorithm && (
                      <div style={{ fontSize: 11, color: TEXT_DIM }}>
                        Encryption: {c.encryption_algorithm} ({c.key_length_bits}bit)
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {tab === 'privacy' && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 }}>
                {policies.length === 0 ? (
                  <div style={{ gridColumn: '1 / -1', padding: 60, textAlign: 'center', color: TEXT_DIM, fontSize: 14, background: CARD_BG, borderRadius: 8, border: `1px solid ${CARD_BORDER}` }}>
                    No privacy policies configured
                  </div>
                ) : policies.map(p => (
                  <div key={p.id} style={{ padding: '16px 20px', borderRadius: 8, background: CARD_BG, border: `1px solid ${CARD_BORDER}` }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 600, color: TEXT }}>{p.policy_name}</div>
                        <div style={{ fontSize: 11, color: GOLD, textTransform: 'uppercase' as const, fontWeight: 600 }}>{p.framework}</div>
                      </div>
                      <div style={{ display: 'flex', gap: 6 }}>
                        {p.is_compliant ? getStatusBadge('compliant') : getStatusBadge('non_compliant')}
                      </div>
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 12 }}>
                      <div style={{ padding: 8, borderRadius: 6, background: '#08090c' }}>
                        <div style={{ fontSize: 10, color: TEXT_DIM }}>Privacy Score</div>
                        <div style={{ fontSize: 18, fontWeight: 700, color: p.privacy_score >= 80 ? GREEN : YELLOW }}>{p.privacy_score}%</div>
                      </div>
                      <div style={{ padding: 8, borderRadius: 6, background: '#08090c' }}>
                        <div style={{ fontSize: 10, color: TEXT_DIM }}>Classification</div>
                        <div style={{ fontSize: 14, fontWeight: 600, color: TEXT, textTransform: 'capitalize' as const }}>{p.data_classification}</div>
                      </div>
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                      {[
                        { label: 'Encryption', val: p.encryption_required },
                        { label: 'Anonymize', val: p.anonymization_required },
                        { label: 'Right to Erasure', val: p.right_to_erasure },
                        { label: 'DPIA', val: p.dpia_completed },
                      ].map(f => (
                        <span key={f.label} style={{ padding: '3px 8px', borderRadius: 4, fontSize: 10, background: f.val ? '#22c55e18' : '#ef444418', color: f.val ? GREEN : RED }}>
                          {f.label}
                        </span>
                      ))}
                    </div>
                    <div style={{ marginTop: 8, fontSize: 11, color: TEXT_DIM }}>
                      Breach notification: {p.breach_notification_hours}h | Retention: {p.data_retention_days}d
                    </div>
                  </div>
                ))}
              </div>
            )}

            {tab === 'interoperability' && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 }}>
                {standards.length === 0 ? (
                  <div style={{ gridColumn: '1 / -1', padding: 60, textAlign: 'center', color: TEXT_DIM, fontSize: 14, background: CARD_BG, borderRadius: 8, border: `1px solid ${CARD_BORDER}` }}>
                    No interoperability standards configured
                  </div>
                ) : standards.map(s => (
                  <div key={s.id} style={{ padding: '16px 20px', borderRadius: 8, background: CARD_BG, border: `1px solid ${CARD_BORDER}` }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 600, color: TEXT }}>{s.standard_name}</div>
                        <div style={{ fontSize: 11, color: BLUE, textTransform: 'uppercase' as const, fontWeight: 600 }}>{s.framework}</div>
                      </div>
                      {getStatusBadge(s.status)}
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginBottom: 12 }}>
                      <div style={{ padding: 8, borderRadius: 6, background: '#08090c', textAlign: 'center' }}>
                        <div style={{ fontSize: 10, color: TEXT_DIM }}>Compatibility</div>
                        <div style={{ fontSize: 18, fontWeight: 700, color: s.compatibility_score >= 80 ? GREEN : YELLOW }}>{s.compatibility_score}%</div>
                      </div>
                      <div style={{ padding: 8, borderRadius: 6, background: '#08090c', textAlign: 'center' }}>
                        <div style={{ fontSize: 10, color: TEXT_DIM }}>Messages</div>
                        <div style={{ fontSize: 18, fontWeight: 700, color: GOLD }}>{s.messages_processed}</div>
                      </div>
                      <div style={{ padding: 8, borderRadius: 6, background: '#08090c', textAlign: 'center' }}>
                        <div style={{ fontSize: 10, color: TEXT_DIM }}>Error Rate</div>
                        <div style={{ fontSize: 18, fontWeight: 700, color: s.error_rate_pct < 1 ? GREEN : RED }}>{s.error_rate_pct}%</div>
                      </div>
                    </div>
                    {s.aml_kyc_standard && (
                      <div style={{ fontSize: 11, color: TEXT_DIM, marginBottom: 4 }}>AML/KYC: {s.aml_kyc_standard}</div>
                    )}
                    {s.jurisdictions && s.jurisdictions.length > 0 && (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6 }}>
                        {s.jurisdictions.map(j => (
                          <span key={j} style={{ padding: '2px 6px', borderRadius: 3, fontSize: 10, background: '#3b82f618', color: BLUE }}>{j}</span>
                        ))}
                      </div>
                    )}
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
