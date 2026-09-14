import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api';

export default function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await api.auth.login({ email, password });
      // Check if user has data; if not, show onboarding wizard
      try {
        const status = await api.firstRun.quickStartData() as { onboarding: { onboarding_complete: boolean } };
        if (!status.onboarding.onboarding_complete) {
          localStorage.removeItem('quantive_wizard_dismissed');
        }
      } catch {
        // If status check fails, clear dismiss to be safe
        localStorage.removeItem('quantive_wizard_dismissed');
      }
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed. Verify credentials and try again.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="liquid-orb" aria-hidden="true" />
      <div className="liquid-orb" aria-hidden="true" />
      <div className="liquid-orb" aria-hidden="true" />
      <div className="auth-card">
        <div className="brand-name">Quantive</div>
        <p>Government Financial Optimization</p>
        <h1>Sign in to your account</h1>
        <form onSubmit={handleSubmit}>
          <label htmlFor="login-email">Email</label>
          <input
            id="login-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <label htmlFor="login-password">Password</label>
          <input
            id="login-password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          {error && <p role="alert">{error}</p>}
          <button type="submit" disabled={loading}>
            {loading ? 'Authenticating...' : 'Sign In'}
          </button>
        </form>
        <Link to="/register">Request access</Link>
      </div>
    </div>
  );
}
