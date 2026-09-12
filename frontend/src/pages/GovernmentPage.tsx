import { Link } from 'react-router-dom';

export default function GovernmentPage() {
  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: 24 }}>
      <nav style={{ display: 'flex', gap: 12 }}>
        <Link to="/">← Home</Link>
        <Link to="/qubo">Qubo</Link>
        <Link to="/terms">Terms</Link>
      </nav>
      <h1>Quantive for Government</h1>
      <p style={{ color: '#4b5563' }}>
        Sovereign debt optimization plus aggregated Qubo market trends — no individual data, ever.
      </p>
      <div className="qp-card">
        <h3>You get</h3>
        <ul>
          <li>Debt portfolio optimization, risk, and scenario tooling</li>
          <li>Qubo aggregates: age group / age bracket + investing vs spending trends</li>
          <li>Audit logging, RBAC, and residency controls</li>
        </ul>
        <div style={{ display: 'flex', gap: 8 }}>
          <Link to="/sovereign-mode" className="qp-btn" style={{ textDecoration: 'none' }}>Open Sovereign Mode</Link>
          <Link to="/pilots" className="qp-btn secondary" style={{ textDecoration: 'none' }}>Pilots</Link>
        </div>
      </div>
      <p className="qp-muted" style={{ marginTop: 12 }}>
        Individuals: Gov-grade insight without being the product — see{' '}
        <Link to="/personal">Personal Sovereign ($10k/yr)</Link>.
      </p>
    </div>
  );
}
