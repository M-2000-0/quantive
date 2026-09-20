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
      try {
        const status = await api.firstRun.quickStartData() as { portfolios: Array<{ id: string }> };
        if (!status.portfolios || status.portfolios.length === 0) {
          localStorage.removeItem('quantive_wizard_dismissed');
        }
      } catch {
        localStorage.removeItem('quantive_wizard_dismissed');
      }
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed. Verify credentials and try again.');
    } finally {
      setLoading(false);
    }
  }

  function fillDemo() {
    setEmail('patricio');
    setPassword('QuantumComp');
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: '#0A0A0B',
      color: '#F5F5F3',
      display: 'grid',
      placeItems: 'center',
      padding: '24px',
      position: 'relative',
      overflow: 'hidden',
      fontFamily: 'Inter, system-ui, sans-serif',
    }}>
      <div aria-hidden="true" style={{
        position: 'fixed', inset: 0, zIndex: 0, pointerEvents: 'none',
        background: 'radial-gradient(700px 360px at 10% -4%, rgba(77,141,255,0.09), transparent 65%), radial-gradient(760px 400px at 90% 6%, rgba(255,255,255,0.045), transparent 60%)',
      }} />
      <div aria-hidden="true" style={{
        position: 'fixed', inset: 0, zIndex: 0, pointerEvents: 'none',
        background: 'radial-gradient(600px 300px at 28% 22%, rgba(77,141,255,0.11), transparent 70%)',
        opacity: 0.6,
      }} />

      <div style={{
        position: 'relative', zIndex: 1,
        width: '100%', maxWidth: 980,
        display: 'grid', gridTemplateColumns: '1.05fr 0.95fr',
        gap: 40, alignItems: 'center',
      }}>
        {/* Left — brand context - clean, logo as hero */}
        <div style={{ padding: '8px 4px', display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', marginLeft: 30 }}>
          <img src="/quantive-logo.png" alt="Quantive" style={{ width: 180, height: 180, objectFit: 'contain', display: 'block', filter: 'drop-shadow(0 16px 40px rgba(0,0,0,0.5))', marginBottom: 24 }} />

          <h1 style={{
            fontFamily: "'Instrument Serif', serif",
            fontSize: 'clamp(36px, 4.5vw, 48px)', fontWeight: 400, lineHeight: 0.95, letterSpacing: '-0.04em',
            marginBottom: 12, textAlign: 'center',
          }}>
            Welcome <em style={{ fontStyle: 'italic', color: '#C8C8CE', fontWeight: 400 }}>back.</em>
          </h1>
          <p style={{ fontSize: 14, lineHeight: 1.6, color: '#8A8A90', maxWidth: 420, marginBottom: 16, textAlign: 'center' }}>
            Sign in to your sovereign workspace. Every recommendation shows its assumptions. Audit-ready, fiscal-rule-aware.
          </p>

          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 11, color: '#5E5E66', fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase', justifyContent: 'center' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>◆ SOC 2 READY</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>◆ ENCRYPTED</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>◆ AUDIT TRAILS</span>
          </div>
        </div>

        {/* Right — auth card - improved hierarchy & contrast */}
        <div style={{
          background: 'rgba(255,255,255,0.035)', border: '1px solid rgba(255,255,255,0.08)',
          borderRadius: 20, padding: 28,
          boxShadow: '0 1px 0 rgba(255,255,255,0.04) inset, 0 20px 50px rgba(0,0,0,0.38)',
          backdropFilter: 'blur(16px)',
        }}>
          <div style={{ marginBottom: 20 }}>
            <h2 style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.02em', lineHeight: 1 }}>Sign In</h2>
            <p style={{ fontSize: 13, color: '#8A8A90', marginTop: 4 }}>Government Financial Optimization</p>
          </div>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <label htmlFor="login-email" style={{ fontSize: 12, fontWeight: 600, letterSpacing: '-0.01em', color: '#E8E8EA' }}>Email</label>
              <input
                id="login-email"
                type="text"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="e.g. paris@quantiveglobal.com"
                required
                autoComplete="username"
                style={{
                  padding: '12px 14px', borderRadius: 12,
                  border: '1px solid rgba(255,255,255,0.14)', background: 'rgba(255,255,255,0.07)',
                  color: '#F5F5F3', outline: 'none', fontSize: 14,
                  boxShadow: '0 1px 0 rgba(255,255,255,0.04) inset',
                  transition: 'border-color 0.15s, box-shadow 0.15s, background 0.15s',
                }}
                onFocus={(e) => { e.currentTarget.style.borderColor = '#F5F5F3'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(255,255,255,0.08)'; e.currentTarget.style.background = 'rgba(255,255,255,0.09)'; }}
                onBlur={(e) => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.14)'; e.currentTarget.style.boxShadow = '0 1px 0 rgba(255,255,255,0.04) inset'; e.currentTarget.style.background = 'rgba(255,255,255,0.07)'; }}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <label htmlFor="login-password" style={{ fontSize: 12, fontWeight: 600, letterSpacing: '-0.01em', color: '#E8E8EA' }}>Password</label>
                <Link to="/forgot-password" style={{ fontSize: 12, color: '#8A8A90', textDecoration: 'none' }}>Forgot password?</Link>
              </div>
              <input
                id="login-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                placeholder="••••••••"
                style={{
                  padding: '12px 14px', borderRadius: 12,
                  border: '1px solid rgba(255,255,255,0.14)', background: 'rgba(255,255,255,0.07)',
                  color: '#F5F5F3', outline: 'none', fontSize: 14,
                  transition: 'border-color 0.15s, box-shadow 0.15s, background 0.15s',
                }}
                onFocus={(e) => { e.currentTarget.style.borderColor = '#F5F5F3'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(255,255,255,0.08)'; e.currentTarget.style.background = 'rgba(255,255,255,0.09)'; }}
                onBlur={(e) => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.14)'; e.currentTarget.style.boxShadow = 'none'; e.currentTarget.style.background = 'rgba(255,255,255,0.07)'; }}
              />
            </div>

            {error && (
              <div role="alert" style={{
                padding: '10px 12px', borderRadius: 12,
                background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.18)',
                color: '#FCA5A5', fontSize: 13, lineHeight: 1.5,
              }}>
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              style={{
                marginTop: 2, padding: '13px 16px', borderRadius: 12,
                background: '#F5F5F3', color: '#0A0A0B', border: 'none',
                fontWeight: 700, fontSize: 14, letterSpacing: '-0.01em',
                cursor: loading ? 'not-allowed' : 'pointer',
                boxShadow: '0 1px 0 rgba(255,255,255,0.9) inset, 0 8px 20px rgba(0,0,0,0.18)',
                opacity: loading ? 0.7 : 1,
                width: '100%',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                transition: 'background 0.15s, transform 0.1s, box-shadow 0.15s',
              }}
              onMouseEnter={(e) => !loading && (e.currentTarget.style.background = '#FFFFFF')}
              onMouseLeave={(e) => !loading && (e.currentTarget.style.background = '#F5F5F3')}
              onMouseDown={(e) => !loading && (e.currentTarget.style.transform = 'scale(0.99)')}
              onMouseUp={(e) => !loading && (e.currentTarget.style.transform = 'scale(1)')}
            >
              {loading ? 'Authenticating…' : 'Sign In →'}
            </button>

            <button
              type="button"
              onClick={fillDemo}
              style={{
                padding: '8px 12px', borderRadius: 100,
                background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.08)',
                color: '#8A8A90', fontSize: 12, fontWeight: 600, letterSpacing: '-0.01em',
                cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                transition: 'background 0.15s, border-color 0.15s, color 0.15s',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.09)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.14)'; e.currentTarget.style.color = '#F5F5F3'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)'; e.currentTarget.style.color = '#8A8A90'; }}
            >
              Fill demo credentials
            </button>

            <div style={{ display: 'flex', justifyContent: 'center', marginTop: 2, fontSize: 12, color: '#5E5E66' }}>
              <span>Need an account? <Link to="/register" style={{ color: '#C8A951', fontWeight: 700, textDecoration: 'none' }}>Request access →</Link></span>
            </div>
          </form>

          <div style={{ marginTop: 18, paddingTop: 14, borderTop: '1px solid rgba(255,255,255,0.08)', display: 'flex', justifyContent: 'space-between', gap: 12, fontSize: 11, color: '#5E5E66' }}>
            <span>© 2026 Quantive</span>
            <span style={{ display: 'flex', gap: 12 }}>
              <Link to="/terms" style={{ color: '#8A8A90', textDecoration: 'none' }}>Terms</Link>
              <a href="/" style={{ color: '#8A8A90', textDecoration: 'none' }}>Back to home</a>
            </span>
          </div>
        </div>
      </div>

      <style>{`@media (max-width: 900px) { div[style*="gridTemplateColumns: 1.05fr"] { grid-template-columns: 1fr !important; } }`}</style>
    </div>
  );
}
