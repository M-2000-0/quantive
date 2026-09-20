import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

interface Dashboard {
  pre_trade_controls: { total: number; active: number; breached: number };
  simulations: { total: number; completed: number };
  surveillance: { total: number; open: number; critical: number };
  proof_of_reserves: { total: number; verified: number };
  decision_logs: { total: number; human_reviewed: number; with_shap: number };
}

interface PreTradeControl {
  id: string;
  control_name: string;
  control_type: string;
  status: string;
  max_value: number;
  currency: string;
  warning_threshold_pct: number;
  reject_on_breach: boolean;
  total_checks: number;
  total_breaches: number;
  self_trade_enabled: boolean;
}

interface Simulation {
  id: string;
  environment_name: string;
  exchange_venue: string;
  status: string;
  starting_capital: number;
  simulated_latency_ms: number;
  total_trades: number;
  total_pnl: number;
  sharpe_ratio: number;
  max_drawdown_pct: number;
  win_rate_pct: number;
  kill_switch_triggered: boolean;
}

interface SurveillanceAlert {
  id: string;
  alert_type: string;
  severity: string;
  status: string;
  title: string;
  description: string;
  instrument_identifier: string;
  confidence_score: number;
  price_at_detection: number;
  volume_at_detection: number;
  assigned_to: string;
  detected_at: string;
}

interface ProofOfReserve {
  id: string;
  reserve_name: string;
  custodian_name: string;
  jurisdiction: string;
  total_reserves: number;
  total_liabilities: number;
  reserve_ratio_pct: number;
  status: string;
  chain: string;
  zero_knowledge_proof: boolean;
  attestation_service: string;
}

interface DecisionLog {
  id: string;
  decision_type: string;
  decision_id: string;
  instrument_identifier: string;
  action: string;
  side: string;
  quantity: number;
  price: number;
  total_value: number;
  model_name: string;
  confidence_score: number;
  explanation_text: string;
  shap_values: Record<string, number>;
  pre_trade_checks_passed: boolean;
  human_review_required: boolean;
  human_reviewed: boolean;
  event_hash: string;
  tamper_evident: boolean;
  decision_timestamp: string;
}

const TABS = ['pre-trade-controls', 'simulations', 'surveillance', 'proof-of-reserve', 'decision-logs'] as const;

export default function ExchangeDueDiligencePage() {
  const [activeTab, setActiveTab] = useState<string>('pre-trade-controls');
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [preTradeControls, setPreTradeControls] = useState<PreTradeControl[]>([]);
  const [simulations, setSimulations] = useState<Simulation[]>([]);
  const [surveillanceAlerts, setSurveillanceAlerts] = useState<SurveillanceAlert[]>([]);
  const [proofOfReserves, setProofOfReserves] = useState<ProofOfReserve[]>([]);
  const [decisionLogs, setDecisionLogs] = useState<DecisionLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [dashRes, preRes, simRes, survRes, porRes, dlRes] = await Promise.all([
        fetch('/api/due-diligence/dashboard'),
        fetch('/api/due-diligence/pre-trade-controls'),
        fetch('/api/due-diligence/simulations'),
        fetch('/api/due-diligence/surveillance'),
        fetch('/api/due-diligence/proof-of-reserve'),
        fetch('/api/due-diligence/decision-logs'),
      ]);
      if (dashRes.ok) setDashboard(await dashRes.json());
      if (preRes.ok) { const d = await preRes.json(); setPreTradeControls(d.pre_trade_controls || []); }
      if (simRes.ok) { const d = await simRes.json(); setSimulations(d.simulations || []); }
      if (survRes.ok) { const d = await survRes.json(); setSurveillanceAlerts(d.surveillance || []); }
      if (porRes.ok) { const d = await porRes.json(); setProofOfReserves(d.proof_of_reserves || []); }
      if (dlRes.ok) { const d = await dlRes.json(); setDecisionLogs(d.decision_logs || []); }
    } catch {}
    setLoading(false);
  };

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      active: '#22c55e', inactive: '#6b7280', breached: '#ef4444', healthy: '#22c55e',
      warning: '#f59e0b', critical: '#ef4444', completed: '#22c55e', running: '#3b82f6',
      killed: '#ef4444', open: '#f59e0b', investigating: '#3b82f6', closed: '#6b7280',
      verified: '#22c55e', unverified: '#ef4444', pending: '#c8a951', failed: '#ef4444',
      approved: '#22c55e', rejected: '#ef4444', high: '#ef4444', medium: '#f59e0b', low: '#22c55e',
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
        <Link to="/regulatory-compliance">Regulatory Compliance</Link>
        <Link to="/cybersecurity-privacy">Cybersecurity & Privacy</Link>
      </nav>

      <h1 style={{ color: '#c8a951', marginBottom: 4 }}>Exchange Due Diligence</h1>
      <p style={{ color: '#9ca3af', marginBottom: 24 }}>
        Pre-trade controls, simulation testing, market surveillance, proof of reserves, and decision audit logs.
      </p>

      {/* Dashboard Summary */}
      {dashboard && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12, marginBottom: 24 }}>
          {[
            { label: 'Pre-Trade', value: `${dashboard.pre_trade_controls.active}/${dashboard.pre_trade_controls.total}`, sub: `${dashboard.pre_trade_controls.breached} breached`, color: '#c8a951', icon: '🛡️' },
            { label: 'Simulations', value: `${dashboard.simulations.completed}/${dashboard.simulations.total}`, sub: 'completed', color: '#3b82f6', icon: '🧪' },
            { label: 'Surveillance', value: `${dashboard.surveillance.open}/${dashboard.surveillance.total}`, sub: `${dashboard.surveillance.critical} critical`, color: dashboard.surveillance.critical > 0 ? '#ef4444' : '#22c55e', icon: '👁️' },
            { label: 'Proof of Reserve', value: `${dashboard.proof_of_reserves.verified}/${dashboard.proof_of_reserves.total}`, sub: 'verified', color: '#22c55e', icon: '⛓️' },
            { label: 'Decision Logs', value: `${dashboard.decision_logs.human_reviewed}/${dashboard.decision_logs.total}`, sub: `${dashboard.decision_logs.with_shap} SHAP`, color: '#8b5cf6', icon: '📝' },
          ].map((item) => (
            <div key={item.label} style={{
              padding: 16, background: '#111318', border: '1px solid #1f2937', borderRadius: 8, textAlign: 'center',
            }}>
              <div style={{ fontSize: 20, marginBottom: 4 }}>{item.icon}</div>
              <div style={{ color: item.color, fontSize: 24, fontWeight: 700 }}>{item.value}</div>
              <div style={{ color: '#6b7280', fontSize: 11, textTransform: 'uppercase' }}>{item.label}</div>
              <div style={{ color: '#9ca3af', fontSize: 10, marginTop: 2 }}>{item.sub}</div>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 20, borderBottom: '1px solid #1f2937', paddingBottom: 8 }}>
        {TABS.map((tab) => (
          <button key={tab} onClick={() => setActiveTab(tab)} style={{
            padding: '8px 16px', background: activeTab === tab ? '#c8a951' : 'transparent',
            color: activeTab === tab ? '#000' : '#9ca3af', border: 'none', borderRadius: 6,
            cursor: 'pointer', fontWeight: 600, textTransform: 'capitalize',
          }}>{tab.replace(/-/g, ' ')}</button>
        ))}
      </div>

      {/* Pre-Trade Controls */}
      {activeTab === 'pre-trade-controls' && (
        <div style={{ background: '#111318', border: '1px solid #1f2937', borderRadius: 12, padding: 24 }}>
          <h3 style={{ color: '#e5e7eb', marginBottom: 8 }}>Pre-Trade Controls</h3>
          <p style={{ color: '#6b7280', marginBottom: 16, fontSize: 13 }}>
            Trade validation controls, breach tracking, and self-trade prevention configuration.
          </p>
          {preTradeControls.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: '#6b7280' }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>🛡️</div>
              <div>No pre-trade controls found.</div>
              <div style={{ fontSize: 13, marginTop: 8 }}>Add via <code>POST /api/due-diligence/pre-trade-controls</code></div>
            </div>
          ) : (
            <div style={{ display: 'grid', gap: 12 }}>
              {preTradeControls.map((ctrl) => (
                <div key={ctrl.id} style={{
                  padding: 16, background: '#0d0f13', border: '1px solid #1f2937', borderRadius: 8,
                  display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12,
                }}>
                  <div>
                    <div style={{ color: '#e5e7eb', fontWeight: 600 }}>{ctrl.control_name}</div>
                    <div style={{ color: '#6b7280', fontSize: 13 }}>{ctrl.control_type}</div>
                    <div style={{ color: '#9ca3af', fontSize: 12, marginTop: 4 }}>
                      Max: {ctrl.max_value.toLocaleString()} {ctrl.currency}
                    </div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 12 }}>
                    <div>
                      <span style={{ color: '#6b7280' }}>Checks: </span>
                      <span style={{ color: '#c8a951', fontWeight: 600 }}>{ctrl.total_checks.toLocaleString()}</span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Breaches: </span>
                      <span style={{ color: ctrl.total_breaches > 0 ? '#ef4444' : '#22c55e', fontWeight: 600 }}>
                        {ctrl.total_breaches.toLocaleString()}
                      </span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Warning @ </span>
                      <span style={{ color: '#f59e0b', fontWeight: 600 }}>{ctrl.warning_threshold_pct}%</span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Reject on Breach: </span>
                      {getBooleanBadge(ctrl.reject_on_breach)}
                    </div>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', justifyContent: 'space-between' }}>
                    {getStatusBadge(ctrl.status)}
                    <div style={{ fontSize: 12, color: '#6b7280' }}>
                      Self-Trade: {getBooleanBadge(ctrl.self_trade_enabled)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Simulations */}
      {activeTab === 'simulations' && (
        <div style={{ background: '#111318', border: '1px solid #1f2937', borderRadius: 12, padding: 24 }}>
          <h3 style={{ color: '#e5e7eb', marginBottom: 8 }}>Simulations</h3>
          <p style={{ color: '#6b7280', marginBottom: 16, fontSize: 13 }}>
            Paper trading environments, PnL tracking, risk metrics, and kill switch validation.
          </p>
          {simulations.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: '#6b7280' }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>🧪</div>
              <div>No simulations found.</div>
            </div>
          ) : (
            <div style={{ display: 'grid', gap: 12 }}>
              {simulations.map((sim) => (
                <div key={sim.id} style={{
                  padding: 16, background: '#0d0f13', border: '1px solid #1f2937', borderRadius: 8,
                  display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12,
                }}>
                  <div>
                    <div style={{ color: '#e5e7eb', fontWeight: 600 }}>{sim.environment_name}</div>
                    <div style={{ color: '#6b7280', fontSize: 13 }}>{sim.exchange_venue}</div>
                    <div style={{ color: '#9ca3af', fontSize: 12, marginTop: 4 }}>
                      Capital: ${sim.starting_capital.toLocaleString()} • Latency: {sim.simulated_latency_ms}ms
                    </div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 12 }}>
                    <div>
                      <span style={{ color: '#6b7280' }}>Trades: </span>
                      <span style={{ color: '#c8a951', fontWeight: 600 }}>{sim.total_trades.toLocaleString()}</span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>PnL: </span>
                      <span style={{ color: sim.total_pnl >= 0 ? '#22c55e' : '#ef4444', fontWeight: 600 }}>
                        ${sim.total_pnl.toLocaleString()}
                      </span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Sharpe: </span>
                      <span style={{ color: '#3b82f6', fontWeight: 600 }}>{sim.sharpe_ratio.toFixed(2)}</span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Max Drawdown: </span>
                      <span style={{ color: '#ef4444', fontWeight: 600 }}>{sim.max_drawdown_pct}%</span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Win Rate: </span>
                      <span style={{ color: sim.win_rate_pct > 50 ? '#22c55e' : '#f59e0b', fontWeight: 600 }}>
                        {sim.win_rate_pct}%
                      </span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Kill Switch: </span>
                      {getBooleanBadge(sim.kill_switch_triggered)}
                    </div>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', justifyContent: 'center' }}>
                    {getStatusBadge(sim.status)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Surveillance */}
      {activeTab === 'surveillance' && (
        <div style={{ background: '#111318', border: '1px solid #1f2937', borderRadius: 12, padding: 24 }}>
          <h3 style={{ color: '#e5e7eb', marginBottom: 8 }}>Market Surveillance</h3>
          <p style={{ color: '#6b7280', marginBottom: 16, fontSize: 13 }}>
            Real-time alert monitoring, anomaly detection, and incident assignment tracking.
          </p>
          {surveillanceAlerts.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: '#6b7280' }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>👁️</div>
              <div>No surveillance alerts found.</div>
            </div>
          ) : (
            <div style={{ display: 'grid', gap: 12 }}>
              {surveillanceAlerts.map((alert) => (
                <div key={alert.id} style={{
                  padding: 16, background: '#0d0f13', border: '1px solid #1f2937', borderRadius: 8,
                  display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12,
                }}>
                  <div>
                    <div style={{ color: '#e5e7eb', fontWeight: 600 }}>{alert.title}</div>
                    <div style={{ color: '#6b7280', fontSize: 13 }}>{alert.alert_type} • {alert.instrument_identifier}</div>
                    <div style={{ color: '#9ca3af', fontSize: 12, marginTop: 4 }}>{alert.description}</div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 12 }}>
                    <div>
                      <span style={{ color: '#6b7280' }}>Confidence: </span>
                      <span style={{ color: alert.confidence_score > 0.8 ? '#22c55e' : '#f59e0b', fontWeight: 600 }}>
                        {(alert.confidence_score * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Price: </span>
                      <span style={{ color: '#c8a951', fontWeight: 600 }}>${alert.price_at_detection.toLocaleString()}</span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Volume: </span>
                      <span style={{ color: '#c8a951', fontWeight: 600 }}>{alert.volume_at_detection.toLocaleString()}</span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Assigned: </span>
                      <span style={{ color: '#9ca3af' }}>{alert.assigned_to}</span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', gap: 6 }}>
                      {getStatusBadge(alert.severity)}
                      {getStatusBadge(alert.status)}
                    </div>
                    {alert.detected_at && (
                      <div style={{ fontSize: 11, color: '#9ca3af' }}>
                        {new Date(alert.detected_at).toLocaleString()}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Proof of Reserve */}
      {activeTab === 'proof-of-reserve' && (
        <div style={{ background: '#111318', border: '1px solid #1f2937', borderRadius: 12, padding: 24 }}>
          <h3 style={{ color: '#e5e7eb', marginBottom: 8 }}>Proof of Reserve</h3>
          <p style={{ color: '#6b7280', marginBottom: 16, fontSize: 13 }}>
            Custodial reserve verification, liability matching, and cryptographic attestation status.
          </p>
          {proofOfReserves.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: '#6b7280' }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>⛓️</div>
              <div>No proof of reserves found.</div>
            </div>
          ) : (
            <div style={{ display: 'grid', gap: 12 }}>
              {proofOfReserves.map((por) => (
                <div key={por.id} style={{
                  padding: 16, background: '#0d0f13', border: '1px solid #1f2937', borderRadius: 8,
                  display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12,
                }}>
                  <div>
                    <div style={{ color: '#e5e7eb', fontWeight: 600 }}>{por.reserve_name}</div>
                    <div style={{ color: '#6b7280', fontSize: 13 }}>{por.custodian_name}</div>
                    <div style={{ color: '#9ca3af', fontSize: 12, marginTop: 4 }}>
                      {por.jurisdiction} • {por.chain}
                    </div>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 12 }}>
                    <div>
                      <span style={{ color: '#6b7280' }}>Reserves: </span>
                      <span style={{ color: '#22c55e', fontWeight: 600 }}>${por.total_reserves.toLocaleString()}</span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Liabilities: </span>
                      <span style={{ color: '#ef4444', fontWeight: 600 }}>${por.total_liabilities.toLocaleString()}</span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Ratio: </span>
                      <span style={{ color: por.reserve_ratio_pct >= 100 ? '#22c55e' : '#ef4444', fontWeight: 600 }}>
                        {por.reserve_ratio_pct}%
                      </span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>ZK Proof: </span>
                      {getBooleanBadge(por.zero_knowledge_proof)}
                    </div>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', justifyContent: 'space-between' }}>
                    {getStatusBadge(por.status)}
                    <div style={{ fontSize: 12, color: '#6b7280' }}>
                      {por.attestation_service}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Decision Logs */}
      {activeTab === 'decision-logs' && (
        <div style={{ background: '#111318', border: '1px solid #1f2937', borderRadius: 12, padding: 24 }}>
          <h3 style={{ color: '#e5e7eb', marginBottom: 8 }}>Decision Logs</h3>
          <p style={{ color: '#6b7280', marginBottom: 16, fontSize: 13 }}>
            Full audit trail of AI trading decisions, SHAP explanations, and tamper-evident record keeping.
          </p>
          {decisionLogs.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: '#6b7280' }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>📝</div>
              <div>No decision logs found.</div>
            </div>
          ) : (
            <div style={{ display: 'grid', gap: 12 }}>
              {decisionLogs.map((log) => (
                <div key={log.id} style={{
                  padding: 16, background: '#0d0f13', border: '1px solid #1f2937', borderRadius: 8,
                  display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12,
                }}>
                  <div>
                    <div style={{ color: '#e5e7eb', fontWeight: 600 }}>{log.instrument_identifier}</div>
                    <div style={{ color: '#6b7280', fontSize: 13 }}>{log.decision_type} • {log.action} {log.side}</div>
                    <div style={{ color: '#9ca3af', fontSize: 12, marginTop: 4 }}>
                      {log.model_name} • {new Date(log.decision_timestamp).toLocaleString()}
                    </div>
                    {log.explanation_text && (
                      <div style={{ color: '#9ca3af', fontSize: 11, marginTop: 6, fontStyle: 'italic' }}>
                        "{log.explanation_text}"
                      </div>
                    )}
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 12 }}>
                    <div>
                      <span style={{ color: '#6b7280' }}>Qty: </span>
                      <span style={{ color: '#c8a951', fontWeight: 600 }}>{log.quantity.toLocaleString()}</span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Price: </span>
                      <span style={{ color: '#c8a951', fontWeight: 600 }}>${log.price.toLocaleString()}</span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Value: </span>
                      <span style={{ color: '#c8a951', fontWeight: 600 }}>${log.total_value.toLocaleString()}</span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Confidence: </span>
                      <span style={{ color: log.confidence_score > 0.8 ? '#22c55e' : '#f59e0b', fontWeight: 600 }}>
                        {(log.confidence_score * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Pre-Trade OK: </span>
                      {getBooleanBadge(log.pre_trade_checks_passed)}
                    </div>
                    <div>
                      <span style={{ color: '#6b7280' }}>Human Review: </span>
                      {getBooleanBadge(log.human_review_required)}
                    </div>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', gap: 6 }}>
                      {log.human_reviewed ? getStatusBadge('approved') : getStatusBadge('pending')}
                      {getBooleanBadge(log.tamper_evident)}
                    </div>
                    {log.event_hash && (
                      <div style={{ fontSize: 10, color: '#6b7280', fontFamily: 'monospace', wordBreak: 'break-all', textAlign: 'right', maxWidth: 180 }}>
                        {log.event_hash.slice(0, 24)}...
                      </div>
                    )}
                    {log.shap_values && Object.keys(log.shap_values).length > 0 && (
                      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', justifyContent: 'flex-end', marginTop: 4 }}>
                        {Object.entries(log.shap_values).slice(0, 3).map(([k, v]) => (
                          <span key={k} style={{
                            padding: '1px 6px', borderRadius: 3, fontSize: 10,
                            background: v > 0 ? '#22c55e20' : '#ef444420', color: v > 0 ? '#22c55e' : '#ef4444',
                          }}>
                            {k}: {v > 0 ? '+' : ''}{v.toFixed(3)}
                          </span>
                        ))}
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
