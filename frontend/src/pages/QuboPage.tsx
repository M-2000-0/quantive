import { Link } from 'react-router-dom';

// Qubo product landing: aggregated market data for government investment decisions.
// Privacy contract: only age group/bracket + aggregated investing/spending trends.
export default function QuboPage() {
  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: 24 }}>
      <nav style={{ display: 'flex', gap: 12 }}>
        <Link to="/">← Home</Link>
        <Link to="/terms">Terms</Link>
        <Link to="/government">Government</Link>
      </nav>
      <h1>Qubo</h1>
      <p style={{ color: '#4b5563' }}>
        Qubo compiles market activity into aggregated trends that help governments decide where to invest.
      </p>

      <div className="qp-card">
        <h3>What the government receives</h3>
        <ul>
          <li>Age group / age bracket aggregates</li>
          <li>“People are investing more in X” / “spending more on Y” trend signals</li>
          <li>Time-bucketed, de-identified aggregates for investment planning</li>
        </ul>
      </div>

      <div className="qp-card" style={{ marginTop: 12 }}>
        <h3>What the government never receives</h3>
        <ul>
          <li>Names or contact details</li>
          <li>Conversations or message content</li>
          <li>Individual transactions or identifiable records</li>
        </ul>
        <p className="qp-muted">
          Qubo shares <em>patterns</em>, not people. See <Link to="/terms">Terms of Service</Link> § Qubo &amp; Government Data.
        </p>
      </div>

      <div className="qp-card" style={{ marginTop: 12 }}>
        <h3>How it flows</h3>
        <ol className="qp-muted">
          <li>Individuals and businesses use Quantive / Quantive Personal.</li>
          <li>Qubo aggregates activity into age-bracket trend buckets.</li>
          <li>Government planners see only the aggregates to guide investment.</li>
        </ol>
      </div>
    </div>
  );
}
