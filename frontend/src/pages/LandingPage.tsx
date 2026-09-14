import { Link } from 'react-router-dom';

const FEATURES = [
  'Multi-Algorithm Optimization',
  'Real-Time Risk Analytics',
  'AI Advisor',
  'ESG & Rating Simulation',
  'Interactive Dashboards',
  'SOC 2 Ready Security',
];

export default function LandingPage() {
  return (
    <div className="landing-page" style={{ maxWidth: 1080, margin: '0 auto', padding: 24 }}>
      <span className="badge">Now in Public Beta</span>
      <nav aria-label="Landing" style={{ display: 'flex', gap: 12, margin: '12px 0' }}>
        <Link to="/login">Sign In</Link>
        <Link to="/register">Get Started Free</Link>
        <Link to="/banking">Banking (New)</Link>
        <Link to="/terms">Terms</Link>
        <Link to="/qubo">Qubo</Link>
      </nav>

      <h1>The Debt Portfolio Platform That Thinks For You</h1>
      <p style={{ color: '#4b5563', maxWidth: 720 }}>
        Quantive serves governments, businesses, and individuals — one enterprise,
        separate products, separate data.
      </p>

      {/* ── Two entry buttons ─────────────────────────────────── */}
      <section aria-label="Choose your path" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', gap: 12, margin: '20px 0' }}>
        <div className="qp-card">
          <h2>For Government</h2>
          <p className="qp-muted">Sovereign debt optimization + aggregated Qubo market trends for policy investment.</p>
          <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
            <Link to="/government" className="qp-btn" style={{ textDecoration: 'none' }}>Government</Link>
            <Link to="/qubo" className="qp-btn secondary" style={{ textDecoration: 'none' }}>How Qubo works</Link>
          </div>
        </div>
        <div className="qp-card">
          <h2>For Businesses</h2>
          <p className="qp-muted">Portfolios, risk, optimizations, and market intelligence for teams.</p>
          <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
            <Link to="/business" className="qp-btn" style={{ textDecoration: 'none' }}>Businesses</Link>
            <Link to="/dashboard" className="qp-btn secondary" style={{ textDecoration: 'none' }}>Open workspace</Link>
          </div>
        </div>
      </section>

      {/* ── Qubo strip ────────────────────────────────────────── */}
      <section aria-label="Qubo" className="qp-card" style={{ margin: '16px 0' }}>
        <h2>Qubo — AI tax intelligence for business</h2>
        <p className="qp-muted">
          Qubo finds deductions, categorizes every transaction, and preps your return —
          year-round, not just April. Optional de-identified analytics are strictly
          opt-in — see the <Link to="/terms">Terms</Link>.
        </p>
        <ul className="qp-muted">
          <li>Deduction detection against versioned tax rules</li>
          <li>Instant categorization + quarterly estimates</li>
          <li>CPA-ready export at year end</li>
        </ul>
        <Link to="/qubo" className="qp-btn secondary" style={{ textDecoration: 'none' }}>Qubo landing →</Link>
      </section>

      {/* ── Personal plans strip ──────────────────────────────── */}
      <section aria-label="Personal plans" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', gap: 12, margin: '16px 0' }}>
        <div className="qp-card">
          <h3>Starter — $2,000/yr</h3>
          <p className="qp-muted">Tax write-offs with limits. Useful, deliberately lean — no Gov Quantive.</p>
          <Link to="/personal">Start lean →</Link>
        </div>
        <div className="qp-card">
          <h3>Personal — $5,000/yr</h3>
          <p className="qp-muted">Full tax intelligence: profile, opportunities, docs, annual report.</p>
          <Link to="/personal">Go Personal →</Link>
        </div>
        <div className="qp-card">
          <h3>Sovereign — $10,000/yr</h3>
          <p className="qp-muted">Gov-grade Quantive for individuals, powered by Qubo trends.</p>
          <Link to="/personal">Go Sovereign →</Link>
        </div>
      </section>

      <section aria-label="Features">
        {FEATURES.map((f) => (
          <div key={f}>{f}</div>
        ))}
      </section>
      <section aria-label="Stats">
        <span>$3.2B</span>
        <span>73%</span>
        <span>91%</span>
        <span>{'< 200ms'}</span>
      </section>
      <form onSubmit={(e) => e.preventDefault()}>
        <label htmlFor="landing-email">Email address</label>
        <input id="landing-email" type="email" />
        <button type="submit">Get Early Access</button>
      </form>
      <footer>© Quantive. All rights reserved. <Link to="/terms">Terms of Service</Link></footer>
    </div>
  );
}
