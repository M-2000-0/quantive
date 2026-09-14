import { Link } from 'react-router-dom';

// Terms of Service covering Quantive (gov/business), Qubo aggregation, and
// Quantive Personal tiers ($2k Starter / $5k Personal / $10k Sovereign).
export default function TermsPage() {
  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: 24 }}>
      <nav style={{ display: 'flex', gap: 12 }}>
        <Link to="/">← Home</Link>
        <Link to="/qubo">Qubo</Link>
        <Link to="/personal">Personal</Link>
      </nav>
      <h1>Terms of Service</h1>
      <p className="qp-muted">Last updated: 2026-09-12 · Quantive Enterprise (Quantive, Qubo, Quantive Personal)</p>

      <h2>1. Products, one enterprise, separate data</h2>
      <p>
        <strong>Quantive</strong> (government / business debt and portfolio platform),{' '}
        <strong>Qubo</strong> (AI tax assistant for businesses), and{' '}
        <strong>Quantive Personal</strong> (individual tax intelligence) are operated by the same
        enterprise with shared billing and authentication, but <strong>separate databases</strong>.
        Personal data never mixes with sovereign / institutional data.
      </p>

      <h2>2. Qubo &amp; Data — privacy contract</h2>
      <p>
        Qubo's job is your taxes. Separately, it operates an <strong>optional
        aggregate-trends program</strong>: nothing is contributed unless you explicitly opt in
        (in-app toggle); opt out anytime. Live brackets unlock only above minimum bucket
        sizes so no individual is identifiable.
      </p>
      <ul>
        <li><strong>Shared, when you opt in:</strong> age group, age bracket, and aggregated signals such as “people are investing or spending more in this type of thing.”</li>
        <li><strong>Never shared:</strong> names, contact details, conversations / message content, individual transactions, or any directly identifiable record.</li>
        <li>Recipients see <em>patterns, not people</em> — time-bucketed, de-identified aggregates only.</li>
      </ul>

      <h2>3. Quantive Personal plans</h2>
      <ul>
        <li>
          <strong>Starter — $2,000/yr:</strong> tax write-off detection only, with limits
          (up to 3 opportunities, 10 documents, 20 intelligence questions/month).
          No Gov-grade Quantive market access, no full annual report (summary only).
          Deliberately lean — useful for narrow needs, uncomfortable as a full system
          (you will feel its limits; that is intentional to protect the value of higher tiers).
        </li>
        <li>
          <strong>Personal — $5,000/yr:</strong> full tax intelligence — continuous profile,
          opportunity identification, document organization, personalized analysis, annual report.
        </li>
        <li>
          <strong>Sovereign — $10,000/yr:</strong> everything in Personal plus Gov-grade Quantive
          market access for individuals (aggregated Qubo trends + sovereign-mode insights, CPA-ready export).
        </li>
      </ul>
      <p className="qp-muted">
        Plans are annual access to the system — not per-message pricing. Limits are enforced
        server-side (opportunities, documents, monthly questions, Gov access).
      </p>

      <h2>4. Tax &amp; investment disclaimers</h2>
      <ul>
        <li>Quantive Personal surfaces <em>potentially relevant</em> opportunities — never guaranteed deductions, savings, or eligibility.</li>
        <li>Content is general information, not professional tax, legal, or investment advice. Verify against current rules or a qualified professional.</li>
        <li>Every material conclusion should trace to a versioned rule (jurisdiction × tax year) or be labeled needs-verification.</li>
      </ul>

      <h2>5. Acceptable use, security, deletion</h2>
      <ul>
        <li>One account per individual for Personal; do not share credentials or scrape aggregates to re-identify individuals.</li>
        <li>We log product-scoped audit events; you may inspect/correct profile facts and request deletion of Personal data (billing records retained as legally required).</li>
        <li>We may suspend accounts for abuse, unlawful use, or attempts to de-anonymize Qubo aggregates.</li>
      </ul>

      <h2>6. Billing</h2>
      <p>
        Shared Stripe-backed billing engine. Annual plans auto-renew unless canceled.
        Starter limits reset per documented windows; overages require upgrade, not overage fees.
      </p>

      <p className="qp-muted">Questions: contact support via the app. By using Quantive, Qubo, or Personal you agree to these terms.</p>
    </div>
  );
}
