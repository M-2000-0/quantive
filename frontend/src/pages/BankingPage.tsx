import { Link } from 'react-router-dom';

const FEATURES = [
  { tag: '0% FEE', title: '0% transaction fee', body: 'Card, transfer, invoice — no per-transaction cut. We earn from deposit interest, not fees.' },
  { tag: 'FREE', title: 'Free business accounts', body: 'No minimums, no monthly account fee. Open in minutes with KYB.' },
  { tag: 'FREE', title: 'Free ACH / bank transfers', body: 'Payroll, vendors, rent — unlimited standard transfers included.' },
  { tag: 'AI', title: 'Instant AI bookkeeping', body: 'Every transaction categorized the second it lands. Close-ready books.' },
  { tag: 'AI', title: 'AI tax categorization', body: 'Deductions auto-tagged, quarterly set-asides estimated, CPA-ready export.' },
  { tag: 'AI', title: 'AI cash-flow forecasting', body: '90-day runway, payroll alerts, yield-pocket suggestions.' },
  { tag: 'AI', title: 'AI CFO assistant', body: '"Can I hire in June?" — answered from real cash, ARM pipeline, Doorway income.' },
  { tag: 'OS', title: 'Multi-bank management', body: 'Connect existing accounts. See every balance in Quantive Finance.' },
  { tag: 'SAFE', title: 'Compliant by design', body: 'Partner bank, KYC/KYB, AML, audit trails, full reporting. No exceptions.' },
];

const MODEL = [
  { n: '01 — CORE', t: 'Net interest margin', d: 'Deposits held with our regulated partner bank generate interest. Quantive shares that income — the fee savings go to you.' },
  { n: '02 — PRO', t: 'Premium subscriptions', d: 'Quantive Pro ($49–$499/mo): advanced analytics, tax optimization, AI financial planning.' },
  { n: '03 — CAPITAL', t: 'Lending', d: 'Business loans, property financing via Open Doorway, revenue-based financing.' },
  { n: '04 — YIELD', t: 'Treasury products', d: 'Money-market style cash management and yield optimization for idle cash.' },
];

export default function BankingPage() {
  return (
    <div style={{ maxWidth: 1080, margin: '0 auto', padding: 24 }}>
      <nav aria-label="Banking" style={{ display: 'flex', gap: 12, margin: '12px 0', fontSize: 14 }}>
        <Link to="/">Quantive</Link>
        <Link to="/business">Businesses</Link>
        <Link to="/banking" aria-current="page"><strong>Banking (New)</strong></Link>
        <Link to="/terms">Terms</Link>
      </nav>

      <span className="badge">New — Quantive Banking · Built on Quantive Finance</span>
      <h1 style={{ fontSize: 44, letterSpacing: -2, lineHeight: 1.02, marginTop: 12 }}>
        Business banking with 0% transaction fees. AI CFO included.
      </h1>
      <p style={{ color: '#4b5563', maxWidth: 720, marginTop: 12 }}>
        Free business accounts. Free ACH. Instant bookkeeping, tax categorization, and
        cash-flow forecasting. <strong>We don&apos;t charge transaction fees — we earn money
        by using deposited funds</strong> held with a regulated banking partner.
      </p>
      <div style={{ display: 'flex', gap: 8, marginTop: 16, flexWrap: 'wrap' }}>
        <Link to="/register" className="qp-btn" style={{ textDecoration: 'none' }}>Open a free account →</Link>
        <a href="#model" className="qp-btn secondary" style={{ textDecoration: 'none' }}>How we make money</a>
      </div>
      <img src="/QBanking.jpeg" alt="Quantive Banking dashboard — $184,290 balance, $0 fees, +$42K forecast" style={{ width: '100%', borderRadius: 16, marginTop: 20, border: '1px solid #e5e7eb' }} />
      <p style={{ fontSize: 12, color: '#6b7280', marginTop: 12, maxWidth: 720 }}>
        Quantive Banking is a fintech product, not a bank. Banking services via a licensed
        partner bank, member FDIC. KYC/KYB, AML monitoring and reporting apply.
      </p>

      <section aria-label="Products" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', gap: 12, margin: '24px 0' }}>
        <div className="qp-card"><h2>Quantive Finance</h2><p className="qp-muted">Dashboard, AI CFO, Tax Assistant, payments, multi-bank.</p></div>
        <div className="qp-card" style={{ borderColor: '#2563eb' }}><h2>Quantive Banking ★</h2><p className="qp-muted">0% fees, free accounts, free ACH. Interest-powered, compliant.</p></div>
        <div className="qp-card"><h2>Open Doorway + ARM</h2><p className="qp-muted">Property marketplace + acquisition &amp; follow-up engine.</p></div>
      </section>

      <h2>Everything others charge for. $0.</h2>
      <section aria-label="Features" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', gap: 12, margin: '16px 0' }}>
        {FEATURES.map((f) => (
          <div key={f.title} className="qp-card">
            <span className="badge">{f.tag}</span>
            <h3 style={{ marginTop: 8 }}>{f.title}</h3>
            <p className="qp-muted">{f.body}</p>
          </div>
        ))}
      </section>

      <h2 id="model">How we make money without fees</h2>
      <section aria-label="Business model" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: 12, margin: '16px 0' }}>
        {MODEL.map((m) => (
          <div key={m.t} className="qp-card">
            <span className="badge">{m.n}</span>
            <h3 style={{ marginTop: 8 }}>{m.t}</h3>
            <p className="qp-muted">{m.d}</p>
          </div>
        ))}
      </section>

      <section aria-label="Pricing" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', gap: 12, margin: '16px 0' }}>
        <div className="qp-card"><h3>Banking — $0</h3><p className="qp-muted">Free account, 0% fees, free ACH, AI books + tax tags.</p></div>
        <div className="qp-card"><h3>Pro — $49–$149/mo</h3><p className="qp-muted">Forecasting, AI CFO, tax optimization, multi-bank.</p></div>
        <div className="qp-card"><h3>Scale — $499/mo</h3><p className="qp-muted">Lending access, yield pockets, Doorway + ARM, SLA.</p></div>
      </section>

      <section aria-label="Compliance" className="qp-card" style={{ margin: '16px 0' }}>
        <h2>Compliance — non-negotiable</h2>
        <p className="qp-muted">
          Holding or moving customer money means regulatory obligations everywhere.
          We use a licensed partner bank (BaaS), run KYC/KYB + AML, keep audit trails,
          and file required reports. Anyone promising &quot;no regulation, no reporting&quot;
          while holding your money is a red flag.
        </p>
      </section>

      <form onSubmit={(e) => e.preventDefault()} style={{ margin: '16px 0' }}>
        <label htmlFor="banking-email">Email address</label>
        <input id="banking-email" type="email" placeholder="you@company.com" />
        <button type="submit">Join waitlist</button>
      </form>
      <footer>© Quantive. All rights reserved. <Link to="/terms">Terms of Service</Link></footer>
    </div>
  );
}
