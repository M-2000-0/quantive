import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

interface GovernanceDashboard {
  model_cards: { total: number; deployed: number };
  algorithm_register: { total: number };
  backtesting: { total_runs: number; accuracy: number };
  bias_reports: { total: number };
  decisions: { pending: number; total: number };
  data_lineage: { total_records: number };
  governance_score: number;
}

interface ModelCard {
  id: string;
  model_name: string;
  model_version: string;
  model_type: string;
  category: string;
  status: string;
  intended_use: string;
  owner: string;
  accuracy_metrics: Record<string, number> | null;
  human_oversight_required: boolean;
  created_at: string | null;
  next_review_date: string | null;
}

interface Decision {
  id: string;
  decision_type: string;
  description: string;
  urgency: string;
  confidence_score: number;
  status: string;
  assigned_to: string | null;
  human_decision: string | null;
  decided_by: string | null;
  created_at: string | null;
  review_deadline: string | null;
}

const TABS = ['overview', 'model-cards', 'decisions', 'backtesting', 'bias', 'lineage'] as const;

export default function AIGovernancePage() {
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [dashboard, setDashboard] = useState<GovernanceDashboard | null>(null);
  const [modelCards, setModelCards] = useState<ModelCard[]>([]);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [dashRes, cardsRes, decRes] = await Promise.all([
        fetch('/api/ai-governance/dashboard'),
        fetch('/api/ai-governance/model-cards'),
        fetch('/api/ai-governance/decisions'),
      ]);
      if (dashRes.ok) setDashboard(await dashRes.json());
      if (cardsRes.ok) { const d = await cardsRes.json(); setModelCards(d.model_cards || []); }
      if (decRes.ok) { const d = await decRes.json(); setDecisions(d.decisions || []); }
    } catch {}
    setLoading(false);
  };

  const approveDecision = async (decisionId: string) => {
    const csrfMatch = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/);
    const csrf = csrfMatch ? decodeURIComponent(csrfMatch[1]) : '';
    await fetch(`/api/ai-governance/decisions/${decisionId}/act`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...(csrf ? { 'X-CSRF-Token': csrf } : {}) },
      body: JSON.stringify({
        human_decision: 'approved',
        decision_rationale: 'Reviewed and approved by authorized decision-maker',
      }),
    });
    loadData();
  };

  const rejectDecision = async (decisionId: string) => {
    const csrfMatch = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/);
    const csrf = csrfMatch ? decodeURIComponent(csrfMatch[1]) : '';
    await fetch(`/api/ai-governance/decisions/${decisionId}/act`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...(csrf ? { 'X-CSRF-Token': csrf } : {}) },
      body: JSON.stringify({
        human_decision: 'rejected',
        decision_rationale: 'Rejected — requires revised analysis',
      }),
    });
    loadData();
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return '#22c55e';
    if (score >= 0.6) return '#e8e8ea';
    return '#ef4444';
  };

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      deployed: '#22c55e', validated: '#3b82f6', draft: '#6b7280',
      pending_review: '#e8e8ea', approved: '#22c55e', rejected: '#ef4444',
      modified: '#38bdf8', under_review: '#3b82f6',
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
        <Link to="/pfm-import">PFM Import</Link>
      </nav>

      <h1 style={{ color: '#e8e8ea', marginBottom: 4 }}>AI Governance Framework</h1>
      <p style={{ color: '#9ca3af', marginBottom: 24 }}>
        Model cards, algorithm register, validation, bias detection, and human-in-the-loop governance.
      </p>

      {/* Governance Score */}
      {dashboard && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 24, marginBottom: 24,
          padding: 20, background: '#111318', border: '1px solid #1f2937', borderRadius: 12,
        }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 48, fontWeight: 800, color: getScoreColor(dashboard.governance_score) }}>
              {Math.round(dashboard.governance_score * 100)}
            </div>
            <div style={{ color: '#6b7280', fontSize: 12, textTransform: 'uppercase' }}>Governance Score</div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 16, flex: 1 }}>
            {[
              { label: 'Model Cards', value: dashboard.model_cards.total, sub: `${dashboard.model_cards.deployed} deployed` },
              { label: 'Algorithms', value: dashboard.algorithm_register.total, sub: 'registered' },
              { label: 'Backtests', value: dashboard.backtesting.total_runs, sub: `${(dashboard.backtesting.accuracy * 100).toFixed(1)}% accuracy` },
              { label: 'Bias Reports', value: dashboard.bias_reports.total, sub: 'completed' },
              { label: 'Decisions', value: dashboard.decisions.total, sub: `${dashboard.decisions.pending} pending` },
              { label: 'Lineage', value: dashboard.data_lineage.total_records, sub: 'tracked' },
            ].map((item) => (
              <div key={item.label} style={{ textAlign: 'center' }}>
                <div style={{ color: '#e5e7eb', fontSize: 20, fontWeight: 700 }}>{item.value}</div>
                <div style={{ color: '#6b7280', fontSize: 11 }}>{item.label}</div>
                <div style={{ color: '#9ca3af', fontSize: 10 }}>{item.sub}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 20, borderBottom: '1px solid #1f2937', paddingBottom: 8 }}>
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '8px 16px', background: activeTab === tab ? '#e8e8ea' : 'transparent',
              color: activeTab === tab ? '#000' : '#9ca3af', border: 'none', borderRadius: 6,
              cursor: 'pointer', fontWeight: 600, textTransform: 'capitalize',
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
          {[
            { title: 'Model Cards', desc: 'Document every AI model — purpose, assumptions, limitations, validation results', icon: '📋', link: '/ai-governance/model-cards' },
            { title: 'Algorithm Register', desc: 'Public registry of all algorithms with risk levels, oversight, and decision authority', icon: '📚', link: '/ai-governance/algorithm-register' },
            { title: 'Crisis Backtesting', desc: 'Test models against Argentina 2001, Greece 2012, Sri Lanka 2022, and more', icon: '🔬', link: '/ai-governance/backtesting' },
            { title: 'Bias Detection', desc: 'Monitor data quality, demographic parity, calibration across groups', icon: '⚖️', link: '/ai-governance/bias' },
            { title: 'Human-in-the-Loop', desc: 'Every AI recommendation requires human approval before execution', icon: '👤', link: '/ai-governance/decisions' },
            { title: 'Data Lineage', desc: 'Track every data point from source through transformation to output', icon: '🔗', link: '/ai-governance/lineage' },
          ].map((card) => (
            <div key={card.title} style={{
              padding: 20, background: '#111318', border: '1px solid #1f2937', borderRadius: 12, cursor: 'pointer',
            }} onClick={() => setActiveTab(card.title.toLowerCase().replace(/ /g, '-').replace('human-in-the-loop', 'decisions').replace('crisis-backtesting', 'backtesting').replace('algorithm-register', 'model-cards').replace('bias-detection', 'bias').replace('data-lineage', 'lineage'))}>
              <div style={{ fontSize: 28, marginBottom: 8 }}>{card.icon}</div>
              <div style={{ color: '#e5e7eb', fontSize: 16, fontWeight: 600, marginBottom: 4 }}>{card.title}</div>
              <div style={{ color: '#6b7280', fontSize: 13 }}>{card.desc}</div>
            </div>
          ))}
        </div>
      )}

      {/* Model Cards Tab */}
      {activeTab === 'model-cards' && (
        <div style={{ background: '#111318', border: '1px solid #1f2937', borderRadius: 12, padding: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ color: '#e5e7eb', margin: 0 }}>Model Cards</h3>
            <div style={{ color: '#6b7280', fontSize: 13 }}>
              Each AI model must have a documented card with purpose, assumptions, limitations, and validation results.
            </div>
          </div>
          {modelCards.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: '#6b7280' }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>📋</div>
              <div>No model cards registered yet.</div>
              <div style={{ fontSize: 13, marginTop: 8 }}>Create one via <code>POST /api/ai-governance/model-cards</code></div>
            </div>
          ) : (
            <div style={{ display: 'grid', gap: 12 }}>
              {modelCards.map((card) => (
                <div key={card.id} style={{
                  padding: 16, background: '#0d0f13', border: '1px solid #1f2937', borderRadius: 8,
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                }}>
                  <div>
                    <div style={{ color: '#e5e7eb', fontWeight: 600 }}>{card.model_name} <span style={{ color: '#6b7280' }}>v{card.model_version}</span></div>
                    <div style={{ color: '#6b7280', fontSize: 13, marginTop: 4 }}>{card.intended_use}</div>
                    <div style={{ color: '#9ca3af', fontSize: 12, marginTop: 4 }}>
                      Owner: {card.owner} • Type: {card.model_type} • Category: {card.category}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    {getStatusBadge(card.status)}
                    {card.human_oversight_required && (
                      <span style={{ color: '#e8e8ea', fontSize: 12 }}>👤 HITL</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Decisions Tab (HITL) */}
      {activeTab === 'decisions' && (
        <div style={{ background: '#111318', border: '1px solid #1f2937', borderRadius: 12, padding: 24 }}>
          <h3 style={{ color: '#e5e7eb', marginBottom: 8 }}>Human-in-the-Loop Decisions</h3>
          <p style={{ color: '#6b7280', marginBottom: 16, fontSize: 13 }}>
            Every AI recommendation requires explicit human approval before execution. No autonomous decisions.
          </p>
          {decisions.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: '#6b7280' }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>👤</div>
              <div>No pending decisions.</div>
            </div>
          ) : (
            <div style={{ display: 'grid', gap: 12 }}>
              {decisions.map((dec) => (
                <div key={dec.id} style={{
                  padding: 16, background: '#0d0f13', border: '1px solid #1f2937', borderRadius: 8,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 4 }}>
                        {getStatusBadge(dec.status)}
                        {dec.urgency === 'urgent' && <span style={{ color: '#ef4444', fontSize: 12, fontWeight: 600 }}>URGENT</span>}
                      </div>
                      <div style={{ color: '#e5e7eb', fontWeight: 600, marginBottom: 4 }}>{dec.description}</div>
                      <div style={{ color: '#6b7280', fontSize: 13 }}>
                        Type: {dec.decision_type} • Confidence: {(dec.confidence_score * 100).toFixed(1)}% • Assigned: {dec.assigned_to || 'Unassigned'}
                      </div>
                      {dec.review_deadline && (
                        <div style={{ color: '#9ca3af', fontSize: 12, marginTop: 4 }}>
                          Deadline: {new Date(dec.review_deadline).toLocaleString()}
                        </div>
                      )}
                    </div>
                    {dec.status === 'pending_review' && (
                      <div style={{ display: 'flex', gap: 8 }}>
                        <button
                          onClick={() => approveDecision(dec.id)}
                          style={{
                            padding: '6px 16px', background: '#22c55e', color: '#000', border: 'none',
                            borderRadius: 6, cursor: 'pointer', fontWeight: 600, fontSize: 13,
                          }}
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => rejectDecision(dec.id)}
                          style={{
                            padding: '6px 16px', background: '#ef4444', color: '#fff', border: 'none',
                            borderRadius: 6, cursor: 'pointer', fontWeight: 600, fontSize: 13,
                          }}
                        >
                          Reject
                        </button>
                      </div>
                    )}
                    {dec.human_decision && (
                      <div style={{ textAlign: 'right' }}>
                        <div style={{ color: dec.human_decision === 'approved' ? '#22c55e' : '#ef4444', fontWeight: 600 }}>
                          {dec.human_decision}
                        </div>
                        <div style={{ color: '#6b7280', fontSize: 12 }}>by {dec.decided_by}</div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Backtesting Tab */}
      {activeTab === 'backtesting' && (
        <div style={{ background: '#111318', border: '1px solid #1f2937', borderRadius: 12, padding: 24 }}>
          <h3 style={{ color: '#e5e7eb', marginBottom: 8 }}>Historical Crisis Backtesting</h3>
          <p style={{ color: '#6b7280', marginBottom: 16, fontSize: 13 }}>
            Test models against real sovereign debt crises. Must predict crises correctly before deployment.
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
            {[
              { name: 'Argentina 2001', type: 'default', gdp: '150%', haircuts: '66%' },
              { name: 'Greece 2012', type: 'restructuring', gdp: '170%', haircuts: '53%' },
              { name: 'Sri Lanka 2022', type: 'default', gdp: '114%', haircuts: '30%' },
              { name: 'Argentina 2020', type: 'restructuring', gdp: '103%', haircuts: '35%' },
              { name: 'Ecuador 2008', type: 'default', gdp: '26%', haircuts: '65%' },
              { name: 'Pakistan 1999', type: 'default', gdp: '100%', haircuts: 'N/A' },
            ].map((crisis) => (
              <div key={crisis.name} style={{
                padding: 16, background: '#0d0f13', border: '1px solid #1f2937', borderRadius: 8,
              }}>
                <div style={{ color: '#e5e7eb', fontWeight: 600 }}>{crisis.name}</div>
                <div style={{ color: '#6b7280', fontSize: 13, marginTop: 4 }}>
                  Type: {crisis.type}<br />
                  Debt/GDP: {crisis.gdp}<br />
                  Haircuts: {crisis.haircuts}
                </div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 16, color: '#6b7280', fontSize: 13 }}>
            Run backtests via <code>POST /api/ai-governance/backtest</code> with a model card ID.
          </div>
        </div>
      )}

      {/* Bias Tab */}
      {activeTab === 'bias' && (
        <div style={{ background: '#111318', border: '1px solid #1f2937', borderRadius: 12, padding: 24 }}>
          <h3 style={{ color: '#e5e7eb', marginBottom: 8 }}>Bias Detection & Data Quality</h3>
          <p style={{ color: '#6b7280', marginBottom: 16, fontSize: 13 }}>
            Systematic monitoring of data completeness, accuracy, consistency, and timeliness across all inputs.
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
            {[
              { label: 'Completeness', desc: 'Are all required fields populated?', icon: '📊' },
              { label: 'Accuracy', desc: 'Does data match ground truth?', icon: '✅' },
              { label: 'Consistency', desc: 'Is data consistent across sources?', icon: '🔄' },
              { label: 'Timeliness', desc: 'Is data current and fresh?', icon: '⏰' },
            ].map((metric) => (
              <div key={metric.label} style={{
                padding: 16, background: '#0d0f13', border: '1px solid #1f2937', borderRadius: 8, textAlign: 'center',
              }}>
                <div style={{ fontSize: 24, marginBottom: 8 }}>{metric.icon}</div>
                <div style={{ color: '#e5e7eb', fontWeight: 600, marginBottom: 4 }}>{metric.label}</div>
                <div style={{ color: '#6b7280', fontSize: 12 }}>{metric.desc}</div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 16, color: '#6b7280', fontSize: 13 }}>
            Create bias reports via <code>POST /api/ai-governance/bias-reports</code>.
          </div>
        </div>
      )}

      {/* Lineage Tab */}
      {activeTab === 'lineage' && (
        <div style={{ background: '#111318', border: '1px solid #1f2937', borderRadius: 12, padding: 24 }}>
          <h3 style={{ color: '#e5e7eb', marginBottom: 8 }}>Data Lineage</h3>
          <p style={{ color: '#6b7280', marginBottom: 16, fontSize: 13 }}>
            Track every data point from source (IFMIS, Treasury.gov, ECB) through every transformation to final output.
          </p>
          <div style={{
            padding: 20, background: '#0d0f13', border: '1px solid #1f2937', borderRadius: 8,
            fontFamily: 'monospace', color: '#e8e8ea', fontSize: 13,
          }}>
            <div>Source → Import → Clean → Normalize → Merge → Model Input → AI Output → Decision</div>
            <div style={{ color: '#6b7280', marginTop: 8 }}>
              Each arrow is tracked with timestamps, record counts, and quality scores.
            </div>
          </div>
          <div style={{ marginTop: 16, color: '#6b7280', fontSize: 13 }}>
            View lineage via <code>GET /api/ai-governance/lineage</code>.
          </div>
        </div>
      )}
    </div>
  );
}
