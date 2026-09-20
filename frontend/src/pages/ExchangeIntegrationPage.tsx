import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

interface ExchangeDashboard {
  connections: { total: number; active: number };
  compliance: { rules: number; open_violations: number };
  counterparties: { total: number };
  orders: { pending: number; total: number };
  regulatory_reports: { total: number };
  ethical_firewall: { active_cooling_off: number };
}

interface Connection {
  id: string;
  exchange_name: string;
  exchange_type: string;
  exchange_id: string;
  status: string;
  regulatory_status: string;
  compliance_score: number | null;
}

interface Order {
  id: string;
  order_reference: string;
  order_type: string;
  side: string;
  instrument_type: string;
  instrument_identifier: string;
  quantity: number;
  total_value: number;
  currency: string;
  status: string;
  created_at: string | null;
}

const TABS = ['overview', 'connections', 'compliance', 'orders', 'counterparties', 'ccp', 'capacity', 'audit', 'reports', 'firewall'] as const;

export default function ExchangeIntegrationPage() {
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [dashboard, setDashboard] = useState<ExchangeDashboard | null>(null);
  const [connections, setConnections] = useState<Connection[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [dashRes, connRes, ordRes] = await Promise.all([
        fetch('/api/exchange/dashboard'),
        fetch('/api/exchange/connections'),
        fetch('/api/exchange/orders'),
      ]);
      if (dashRes.ok) setDashboard(await dashRes.json());
      if (connRes.ok) { const d = await connRes.json(); setConnections(d.connections || []); }
      if (ordRes.ok) { const d = await ordRes.json(); setOrders(d.orders || []); }
    } catch {}
    setLoading(false);
  };

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      connected: '#22c55e', connecting: '#c8a951', disconnected: '#6b7280',
      suspended: '#ef4444', error: '#ef4444',
      approved: '#22c55e', conditional: '#f59e0b', restricted: '#ef4444', rejected: '#ef4444',
      pending_approval: '#c8a951', submitted: '#3b82f6', filled: '#22c55e',
      pending_review: '#c8a951', submitted_draft: '#6b7280',
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

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: 24 }}>
      <nav style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
        <Link to="/">← Home</Link>
        <Link to="/government">Government</Link>
        <Link to="/ai-governance">AI Governance</Link>
        <Link to="/regulatory-compliance">Regulatory Compliance</Link>
      </nav>

      <h1 style={{ color: '#c8a951', marginBottom: 4 }}>Exchange & Broker Integration</h1>
      <p style={{ color: '#9ca3af', marginBottom: 24 }}>
        RegTech compliance, risk controls, counterparty due diligence, and interoperability for government-exchange partnerships.
      </p>

      {/* Dashboard Summary */}
      {dashboard && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 12, marginBottom: 24 }}>
          {[
            { label: 'Connections', value: `${dashboard.connections.active}/${dashboard.connections.total}`, color: '#22c55e', icon: '🔗' },
            { label: 'Compliance Rules', value: dashboard.compliance.rules, color: '#3b82f6', icon: '📋' },
            { label: 'Open Violations', value: dashboard.compliance.open_violations, color: dashboard.compliance.open_violations > 0 ? '#ef4444' : '#22c55e', icon: '⚠️' },
            { label: 'Counterparties', value: dashboard.counterparties.total, color: '#c8a951', icon: '🏦' },
            { label: 'Pending Orders', value: dashboard.orders.pending, color: '#f59e0b', icon: '📊' },
            { label: 'Firewall Active', value: dashboard.ethical_firewall.active_cooling_off, color: '#8b5cf6', icon: '🛡️' },
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
            padding: '8px 16px', background: activeTab === tab ? '#c8a951' : 'transparent',
            color: activeTab === tab ? '#000' : '#9ca3af', border: 'none', borderRadius: 6,
            cursor: 'pointer', fontWeight: 600, textTransform: 'capitalize',
          }}>{tab}</button>
        ))}
      </div>

      {/* Overview */}
      {activeTab === 'overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
          {[
            { title: 'RegTech Compliance', desc: 'Automated monitoring against SEC, FCA, CFTC, MiFID II rules with real-time violation detection', icon: '📋' },
            { title: 'Exchange Connectivity', desc: 'API integration with NYSE, LSE, Binance, Bloomberg — order routing, settlement, CCP compatibility', icon: '🔗' },
            { title: 'Counterparty Risk', desc: 'Credit, operational, market, liquidity, regulatory risk scoring with due diligence tracking', icon: '🏦' },
            { title: 'Trade Lifecycle', desc: 'Pre-trade compliance → HITL approval → execution → post-trade reporting → settlement', icon: '📊' },
            { title: 'Risk Allocation', desc: 'Transparent framework defining government vs counterparty risk sharing for every partnership', icon: '⚖️' },
            { title: 'Ethical Firewall', desc: 'Conflict-of-interest detection, cooling-off periods, and recusal tracking for officials', icon: '🛡️' },
          ].map((card) => (
            <div key={card.title} style={{
              padding: 20, background: '#111318', border: '1px solid #1f2937', borderRadius: 12,
            }}>
              <div style={{ fontSize: 28, marginBottom: 8 }}>{card.icon}</div>
              <div style={{ color: '#e5e7eb', fontSize: 16, fontWeight: 600, marginBottom: 4 }}>{card.title}</div>
              <div style={{ color: '#6b7280', fontSize: 13 }}>{card.desc}</div>
            </div>
          ))}
        </div>
      )}

      {/* Connections */}
      {activeTab === 'connections' && (
        <div style={{ background: '#111318', border: '1px solid #1f2937', borderRadius: 12, padding: 24 }}>
          <h3 style={{ color: '#e5e7eb', marginBottom: 16 }}>Exchange Connections</h3>
          {connections.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: '#6b7280' }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>🔗</div>
              <div>No exchange connections configured.</div>
              <div style={{ fontSize: 13, marginTop: 8 }}>Connect via <code>POST /api/exchange/connections</code></div>
            </div>
          ) : (
            <div style={{ display: 'grid', gap: 12 }}>
              {connections.map((conn) => (
                <div key={conn.id} style={{
                  padding: 16, background: '#0d0f13', border: '1px solid #1f2937', borderRadius: 8,
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                }}>
                  <div>
                    <div style={{ color: '#e5e7eb', fontWeight: 600 }}>{conn.exchange_name}</div>
                    <div style={{ color: '#6b7280', fontSize: 13 }}>Type: {conn.exchange_type} • ID: {conn.exchange_id}</div>
                  </div>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    {getStatusBadge(conn.status)}
                    {getStatusBadge(conn.regulatory_status)}
                    {conn.compliance_score != null && (
                      <span style={{ color: conn.compliance_score > 80 ? '#22c55e' : '#ef4444', fontSize: 13, fontWeight: 600 }}>
                        {conn.compliance_score.toFixed(0)}%
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Compliance */}
      {activeTab === 'compliance' && (
        <div style={{ background: '#111318', border: '1px solid #1f2937', borderRadius: 12, padding: 24 }}>
          <h3 style={{ color: '#e5e7eb', marginBottom: 8 }}>Regulatory Compliance Engine</h3>
          <p style={{ color: '#6b7280', marginBottom: 16, fontSize: 13 }}>
            Automated monitoring against SEC, FCA, CFTC, ESMA, and other regulatory frameworks.
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 16 }}>
            {[
              { name: 'SEC Rule 17a-4', desc: 'Recordkeeping', jurisdiction: 'US', status: 'active' },
              { name: 'MiFID II Article 26', desc: 'Transaction Reporting', jurisdiction: 'EU', status: 'active' },
              { name: 'CFTC Rule 1.31', desc: 'Books & Records', jurisdiction: 'US', status: 'active' },
              { name: 'FCA COBS', desc: 'Conduct of Business', jurisdiction: 'UK', status: 'pending' },
            ].map((rule) => (
              <div key={rule.name} style={{
                padding: 12, background: '#0d0f13', border: '1px solid #1f2937', borderRadius: 8,
              }}>
                <div style={{ color: '#e5e7eb', fontWeight: 600, fontSize: 13 }}>{rule.name}</div>
                <div style={{ color: '#6b7280', fontSize: 12 }}>{rule.desc}</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8 }}>
                  <span style={{ color: '#9ca3af', fontSize: 11 }}>{rule.jurisdiction}</span>
                  {getStatusBadge(rule.status)}
                </div>
              </div>
            ))}
          </div>
          <div style={{ color: '#6b7280', fontSize: 13 }}>
            Configure rules via <code>POST /api/exchange/compliance/rules</code> • Run checks via <code>POST /api/exchange/compliance/check</code>
          </div>
        </div>
      )}

      {/* Orders */}
      {activeTab === 'orders' && (
        <div style={{ background: '#111318', border: '1px solid #1f2937', borderRadius: 12, padding: 24 }}>
          <h3 style={{ color: '#e5e7eb', marginBottom: 8 }}>Trade Order Lifecycle</h3>
          <p style={{ color: '#6b7280', marginBottom: 16, fontSize: 13 }}>
            Every trade requires: Pre-trade compliance → Human approval → Execution → Post-trade reporting → Settlement
          </p>
          {orders.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: '#6b7280' }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>📊</div>
              <div>No trade orders yet.</div>
            </div>
          ) : (
            <div style={{ display: 'grid', gap: 8 }}>
              {orders.map((ord) => (
                <div key={ord.id} style={{
                  padding: 12, background: '#0d0f13', border: '1px solid #1f2937', borderRadius: 8,
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                }}>
                  <div>
                    <div style={{ color: '#e5e7eb', fontWeight: 600, fontSize: 13 }}>{ord.order_reference}</div>
                    <div style={{ color: '#6b7280', fontSize: 12 }}>
                      {ord.side.toUpperCase()} {ord.instrument_identifier} • {ord.quantity} @ {ord.total_value.toLocaleString()} {ord.currency}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    {getStatusBadge(ord.status)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Counterparties */}
      {activeTab === 'counterparties' && (
        <div style={{ background: '#111318', border: '1px solid #1f2937', borderRadius: 12, padding: 24 }}>
          <h3 style={{ color: '#e5e7eb', marginBottom: 8 }}>Counterparty Risk Assessment</h3>
          <p style={{ color: '#6b7280', marginBottom: 16, fontSize: 13 }}>
            Credit, operational, market, liquidity, and regulatory risk scoring for every exchange and broker.
          </p>
          <div style={{
            padding: 20, background: '#0d0f13', border: '1px solid #1f2937', borderRadius: 8, marginBottom: 16,
          }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 16, textAlign: 'center' }}>
              {[
                { label: 'Credit Risk', weight: '25%', icon: '💳' },
                { label: 'Operational Risk', weight: '20%', icon: '⚙️' },
                { label: 'Market Risk', weight: '15%', icon: '📈' },
                { label: 'Liquidity Risk', weight: '20%', icon: '💧' },
                { label: 'Regulatory Risk', weight: '20%', icon: '📋' },
              ].map((r) => (
                <div key={r.label}>
                  <div style={{ fontSize: 20, marginBottom: 4 }}>{r.icon}</div>
                  <div style={{ color: '#e5e7eb', fontWeight: 600, fontSize: 13 }}>{r.label}</div>
                  <div style={{ color: '#6b7280', fontSize: 11 }}>Weight: {r.weight}</div>
                </div>
              ))}
            </div>
          </div>
          <div style={{ color: '#6b7280', fontSize: 13 }}>
            Assess counterparties via <code>POST /api/exchange/counterparty/assess</code>
          </div>
        </div>
      )}

      {/* Reports */}
      {activeTab === 'reports' && (
        <div style={{ background: '#111318', border: '1px solid #1f2937', borderRadius: 12, padding: 24 }}>
          <h3 style={{ color: '#e5e7eb', marginBottom: 8 }}>Regulatory Reporting</h3>
          <p style={{ color: '#6b7280', marginBottom: 16, fontSize: 13 }}>
            Machine-readable reports submitted to SEC, FCA, CFTC, ESMA with validation and audit trail.
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
            {[
              { authority: 'SEC', requirement: 'Rule 13h-1 Large Trader Reporting', format: 'XML' },
              { authority: 'FCA', requirement: 'MiFID II Transaction Reporting', format: 'XML' },
              { authority: 'CFTC', requirement: 'Part 43 Real-Time Reporting', format: 'JSON' },
            ].map((r) => (
              <div key={r.requirement} style={{
                padding: 16, background: '#0d0f13', border: '1px solid #1f2937', borderRadius: 8,
              }}>
                <div style={{ color: '#c8a951', fontWeight: 600 }}>{r.authority}</div>
                <div style={{ color: '#e5e7eb', fontSize: 13, marginTop: 4 }}>{r.requirement}</div>
                <div style={{ color: '#6b7280', fontSize: 12, marginTop: 4 }}>Format: {r.format}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Firewall */}
      {activeTab === 'firewall' && (
        <div style={{ background: '#111318', border: '1px solid #1f2937', borderRadius: 12, padding: 24 }}>
          <h3 style={{ color: '#e5e7eb', marginBottom: 8 }}>Ethical Firewall</h3>
          <p style={{ color: '#6b7280', marginBottom: 16, fontSize: 13 }}>
            Conflict-of-interest detection, cooling-off periods, and recusal tracking for government officials.
          </p>
          <div style={{
            padding: 20, background: '#0d0f13', border: '1px solid #1f2937', borderRadius: 8,
          }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
              {[
                { title: 'Employment Conflicts', desc: 'Former officials joining exchanges they regulated', icon: '👤' },
                { title: 'Investment Conflicts', desc: 'Personal holdings in counterparties', icon: '💰' },
                { title: 'Advisory Conflicts', desc: 'Serving on exchange advisory boards', icon: '📝' },
              ].map((c) => (
                <div key={c.title} style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 24, marginBottom: 8 }}>{c.icon}</div>
                  <div style={{ color: '#e5e7eb', fontWeight: 600, fontSize: 13 }}>{c.title}</div>
                  <div style={{ color: '#6b7280', fontSize: 12 }}>{c.desc}</div>
                </div>
              ))}
            </div>
          </div>
          <div style={{ marginTop: 16, color: '#6b7280', fontSize: 13 }}>
            Register conflicts via <code>POST /api/exchange/ethical-firewall</code>
          </div>
        </div>
      )}

      {/* CCP Clearing */}
      {activeTab === 'ccp' && (
        <div style={{ background: '#111318', border: '1px solid #1f2937', borderRadius: 12, padding: 24 }}>
          <h3 style={{ color: '#e5e7eb', marginBottom: 8 }}>CCP Clearing & Smart Contracts</h3>
          <p style={{ color: '#6b7280', marginBottom: 16, fontSize: 13 }}>
            Central counterparty compatibility, margin requirements, and smart contract templates for automated settlement.
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 16, marginBottom: 16 }}>
            <div style={{ padding: 16, background: '#0d0f13', border: '1px solid #1f2937', borderRadius: 8 }}>
              <div style={{ color: '#c8a951', fontWeight: 600, marginBottom: 8 }}>CCP Clearing Members</div>
              <div style={{ color: '#6b7280', fontSize: 13 }}>
                Register CCP memberships (LCH, CME Clearing, ICE Clear) with margin requirements, default fund contributions, and portability settings.
              </div>
              <div style={{ marginTop: 8, color: '#9ca3af', fontSize: 12 }}>
                <code>POST /api/exchange/ccp/membership</code>
              </div>
            </div>
            <div style={{ padding: 16, background: '#0d0f13', border: '1px solid #1f2937', borderRadius: 8 }}>
              <div style={{ color: '#c8a951', fontWeight: 600, marginBottom: 8 }}>Smart Contract Templates</div>
              <div style={{ color: '#6b7280', fontSize: 13 }}>
                Pre-built templates for bond issuance, FX swaps, repos with embedded risk controls and human approval gates.
              </div>
              <div style={{ marginTop: 8, color: '#9ca3af', fontSize: 12 }}>
                <code>POST /api/exchange/smart-contracts</code>
              </div>
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
            {[
              { label: 'LCH', type: 'Derivatives CCP', status: 'available' },
              { label: 'CME Clearing', type: 'Futures CCP', status: 'available' },
              { label: 'ICE Clear', type: 'Commodities CCP', status: 'available' },
              { label: 'DTCC', type: 'OTC Derivatives', status: 'available' },
            ].map((ccp) => (
              <div key={ccp.label} style={{ padding: 12, background: '#0d0f13', border: '1px solid #1f2937', borderRadius: 8, textAlign: 'center' }}>
                <div style={{ color: '#e5e7eb', fontWeight: 600 }}>{ccp.label}</div>
                <div style={{ color: '#6b7280', fontSize: 12 }}>{ccp.type}</div>
                {getStatusBadge(ccp.status)}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Institutional Capacity */}
      {activeTab === 'capacity' && (
        <div style={{ background: '#111318', border: '1px solid #1f2937', borderRadius: 12, padding: 24 }}>
          <h3 style={{ color: '#e5e7eb', marginBottom: 8 }}>Institutional Capacity Assessment</h3>
          <p style={{ color: '#6b7280', marginBottom: 16, fontSize: 13 }}>
            Assess government readiness for exchange partnerships across 5 dimensions.
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12, marginBottom: 16 }}>
            {[
              { label: 'Human Resources', weight: '20%', icon: '👥', desc: 'Staff count, qualifications, training' },
              { label: 'Technology', weight: '25%', icon: '💻', desc: 'IFMIS, API readiness, uptime' },
              { label: 'Process Maturity', weight: '20%', icon: '📋', desc: 'Procedures, ISO compliance' },
              { label: 'Governance', weight: '20%', icon: '🏛️', desc: 'Oversight, audit trail, policies' },
              { label: 'Data Quality', weight: '15%', icon: '📊', desc: 'Completeness, accuracy, timeliness' },
            ].map((dim) => (
              <div key={dim.label} style={{ padding: 12, background: '#0d0f13', border: '1px solid #1f2937', borderRadius: 8, textAlign: 'center' }}>
                <div style={{ fontSize: 24, marginBottom: 4 }}>{dim.icon}</div>
                <div style={{ color: '#e5e7eb', fontWeight: 600, fontSize: 13 }}>{dim.label}</div>
                <div style={{ color: '#6b7280', fontSize: 11 }}>{dim.desc}</div>
                <div style={{ color: '#c8a951', fontSize: 11, marginTop: 4 }}>Weight: {dim.weight}</div>
              </div>
            ))}
          </div>
          <div style={{ padding: 16, background: '#0d0f13', border: '1px solid #1f2937', borderRadius: 8 }}>
            <div style={{ color: '#e5e7eb', fontWeight: 600, marginBottom: 8 }}>Exchange Readiness Rating</div>
            <div style={{ display: 'flex', gap: 12 }}>
              {[
                { rating: 'Excellent', score: '80-100', color: '#22c55e', status: 'Ready' },
                { rating: 'Good', score: '65-79', color: '#3b82f6', status: 'Ready' },
                { rating: 'Adequate', score: '50-64', color: '#f59e0b', status: 'Conditional' },
                { rating: 'Weak', score: '35-49', color: '#ef4444', status: 'Not Ready' },
                { rating: 'Inadequate', score: '0-34', color: '#ef4444', status: 'Not Ready' },
              ].map((r) => (
                <div key={r.rating} style={{ flex: 1, textAlign: 'center', padding: 8, background: '#111318', borderRadius: 6 }}>
                  <div style={{ color: r.color, fontWeight: 600, fontSize: 13 }}>{r.rating}</div>
                  <div style={{ color: '#6b7280', fontSize: 11 }}>{r.score}</div>
                  <div style={{ color: r.color, fontSize: 11 }}>{r.status}</div>
                </div>
              ))}
            </div>
          </div>
          <div style={{ marginTop: 16, color: '#6b7280', fontSize: 13 }}>
            Run assessment via <code>POST /api/exchange/capacity/assess</code>
          </div>
        </div>
      )}

      {/* Algorithm Audit Trail */}
      {activeTab === 'audit' && (
        <div style={{ background: '#111318', border: '1px solid #1f2937', borderRadius: 12, padding: 24 }}>
          <h3 style={{ color: '#e5e7eb', marginBottom: 8 }}>Algorithm Audit Trail</h3>
          <p style={{ color: '#6b7280', marginBottom: 16, fontSize: 13 }}>
            Immutable, cryptographically chained audit log of every algorithm decision — required for exchange due diligence.
          </p>
          <div style={{
            padding: 20, background: '#0d0f13', border: '1px solid #1f2937', borderRadius: 8, marginBottom: 16,
          }}>
            <div style={{ color: '#c8a951', fontFamily: 'monospace', fontSize: 13, wordBreak: 'break-all' }}>
              Event Chain: event_001 → SHA-256 → event_002 → SHA-256 → event_003 → ...
            </div>
            <div style={{ color: '#6b7280', fontSize: 12, marginTop: 8 }}>
              Each event hash includes: input data, model version, output, timestamp, and previous event hash.
              Tampering with any record breaks the chain — cryptographically verifiable.
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
            {[
              { label: 'Predictions', desc: 'Every model prediction recorded', icon: '🔮' },
              { label: 'Recommendations', desc: 'All AI recommendations with explanations', icon: '💡' },
              { label: 'Risk Alerts', desc: 'Every risk alert with confidence scores', icon: '⚠️' },
              { label: 'Human Reviews', desc: 'Every human override with rationale', icon: '👤' },
            ].map((item) => (
              <div key={item.label} style={{ padding: 12, background: '#111318', border: '1px solid #1f2937', borderRadius: 8, textAlign: 'center' }}>
                <div style={{ fontSize: 24, marginBottom: 4 }}>{item.icon}</div>
                <div style={{ color: '#e5e7eb', fontWeight: 600, fontSize: 13 }}>{item.label}</div>
                <div style={{ color: '#6b7280', fontSize: 11 }}>{item.desc}</div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 16, color: '#6b7280', fontSize: 13 }}>
            Record events via <code>POST /api/exchange/algorithm-audit</code> • View via <code>GET /api/exchange/algorithm-audit</code>
          </div>
        </div>
      )}
    </div>
  );
}
