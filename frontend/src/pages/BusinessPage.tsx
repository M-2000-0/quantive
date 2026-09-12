import { Link } from 'react-router-dom';

export default function BusinessPage() {
  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: 24 }}>
      <nav style={{ display: 'flex', gap: 12 }}>
        <Link to="/">← Home</Link>
        <Link to="/pricing">Pricing</Link>
        <Link to="/terms">Terms</Link>
      </nav>
      <h1>Quantive for Businesses</h1>
      <p style={{ color: '#4b5563' }}>
        Portfolios, optimizations, risk, and market intelligence for teams. Separate data from government and Personal products.
      </p>
      <div className="qp-card">
        <h3>You get</h3>
        <ul>
          <li>Unlimited portfolios and instruments (Pro/Enterprise)</li>
          <li>Optimizations, VaR, stress testing, AI advisor</li>
          <li>Exports, webhooks, SSO, audit logging</li>
        </ul>
        <div style={{ display: 'flex', gap: 8 }}>
          <Link to="/dashboard" className="qp-btn" style={{ textDecoration: 'none' }}>Open workspace</Link>
          <Link to="/pricing" className="qp-btn secondary" style={{ textDecoration: 'none' }}>See pricing</Link>
        </div>
      </div>
    </div>
  );
}
