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
    <div className="landing-page">
      <span className="badge">Now in Public Beta</span>
      <nav aria-label="Landing">
        <Link to="/login">Sign In</Link>
        <Link to="/register">Get Started Free</Link>
      </nav>
      <h1>The Debt Portfolio Platform That Thinks For You</h1>
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
      <footer>© Quantive. All rights reserved.</footer>
    </div>
  );
}
