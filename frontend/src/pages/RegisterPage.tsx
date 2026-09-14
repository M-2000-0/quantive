import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api';

export default function RegisterPage() {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [orgName, setOrgName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await api.auth.register({ email, password, name, org_name: orgName });
      // Clear wizard dismiss so onboarding wizard always shows for new users
      try { localStorage.removeItem('quantive_wizard_dismissed'); } catch { /* noop */ }
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed. Please try again.');
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
        <h1>Create your account</h1>
        <form onSubmit={handleSubmit}>
          <label htmlFor="reg-name">Full Name</label>
          <input id="reg-name" type="text" value={name} onChange={(e) => setName(e.target.value)} required />
          <label htmlFor="reg-email">Email address</label>
          <input id="reg-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <label htmlFor="reg-password">Password</label>
          <input id="reg-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          <label htmlFor="reg-org">Organization</label>
          <input id="reg-org" type="text" value={orgName} onChange={(e) => setOrgName(e.target.value)} />
          {error && <p role="alert">{error}</p>}
          <button type="submit" disabled={loading}>
            {loading ? 'Creating account...' : 'Create account'}
          </button>
        </form>
        <Link to="/login">Sign In</Link>
      </div>
    </div>
  );
}
