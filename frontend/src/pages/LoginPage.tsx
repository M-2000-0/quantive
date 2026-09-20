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
      {/* subtle background gradients like web */}
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
        width: '100%', maxWidth: 960,
        display: 'grid', gridTemplateColumns: '1.05fr 0.95fr',
        gap: 32, alignItems: 'center',
      }}>
        {/* Left — brand context */}
        <div style={{ padding: '12px 8px' }}>
          <a href="/" style={{ display: 'flex', alignItems: 'center', gap: 12, textDecoration: 'none', color: 'inherit', marginBottom: 28 }}>
            <div style={{
              width: 48, height: 48, borderRadius: 12, background: '#0A0A0B', border: '1px solid rgba(255,255,255,0.08)',
              display: 'grid', placeItems: 'center', overflow: 'hidden',
              boxShadow: '0 1px 0 rgba(255,255,255,0.06) inset, 0 6px 16px rgba(0,0,0,0.35)',
            }}>
              <img src="/quantive-logo.png" alt="Quantive" style={{ width: 40, height: 40, objectFit: 'contain', display: 'block' }} />
            </div>
            <div>
              <div style={{ fontSize: 18, fontWeight: 700, letterSpacing: '-0.03em', lineHeight: 1 }}>Quantive</div>
              <div style={{ fontSize: 11, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#8A8A90', fontWeight: 600, marginTop: 2 }}>Government • Sovereign</div>
            </div>
          </a>

          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 8, padding: '6px 10px', borderRadius: 100,
            border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.04)', backdropFilter: 'blur(8px)',
            fontSize: 12, color: '#8A8A90', letterSpacing: '-0.01em', marginBottom: 16,
          }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#F5F5F3', boxShadow: '0 0 0 4px rgba(255,255,255,0.08)', display: 'inline-block' }} />
            Decision support for public finance — Live
          </div>

          <h1 style={{
            fontFamily: "'Instrument Serif', serif",
            fontSize: 'clamp(32px, 4.2vw, 44px)', fontWeight: 400, lineHeight: 0.95, letterSpacing: '-0.04em',
            marginBottom: 12,
          }}>
            Welcome <em style={{ fontStyle: 'italic', color: '#C8C8CE', fontWeight: 400 }}>back.</em>
          </h1>
          <p style={{ fontSize: 14, lineHeight: 1.6, color: '#8A8A90', maxWidth: 420, marginBottom: 20 }}>
            Sign in to your sovereign workspace. Every recommendation shows its assumptions — audit-ready, fiscal-rule-aware.
          </p>

          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 11, color: '#5E5E66', fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>◆ SOC 2 Ready</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>◆ Encrypted</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>◆ Audit trails</span>
          </div>

          <div style={{
            marginTop: 28, borderRadius: 16, overflow: 'hidden', border: '1px solid rgba(255,255,255,0.08)',
            background: 'rgba(255,255,255,0.02)', padding: 12,
            display: 'flex', alignItems: 'center', gap: 12,
          }}>
            <img src="/landing-page-1.jpg" alt="Sovereign demo preview" style={{ width: 88, height: 64, objectFit: 'cover', borderRadius: 10, border: '1px solid rgba(255,255,255,0.08)', flexShrink: 0 }} onError={(e) => (e.currentTarget.style.display = 'none')} />
            <div>
              <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: '-0.01em' }}>Sovereign Demo Portfolio</div>
              <div style={{ fontSize: 12, color: '#8A8A90', marginTop: 2 }}><b style={{ color: '#F5F5F3' }}>$557.4B</b> under analysis • 12 • 6 ccys</div>
            </div>
          </div>
        </div>

        {/* Right — auth card */}
        <div style={{
          background: 'rgba(255,255,255,0.035)', border: '1px solid rgba(255,255,255,0.08)',
          borderRadius: 20, padding: 28,
          boxShadow: '0 1px 0 rgba(255,255,255,0.04) inset, 0 20px 50px rgba(0,0,0,0.38)',
          backdropFilter: 'blur(16px)',
        }}>
          <div style={{ marginBottom: 18 }}>
            <div style={{ fontFamily: "'Instrument Serif', serif", fontSize: 22, letterSpacing: '-0.03em', fontWeight: 400 }}>Sign in to your account</div>
            <div style={{ fontSize: 13, color: '#8A8A90', marginTop: 4 }}>Government Financial Optimization</div>
          </div>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <label htmlFor="login-email" style={{ fontSize: 12, fontWeight: 600, letterSpacing: '-0.01em', color: '#F5F5F3' }}>Email</label>
              <input
                id="login-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@treasury.gov"
                required
                style={{
                  padding: '11px 14px', borderRadius: 12,
                  border: '1px solid rgba(255,255,255,0.13)', background: 'rgba(255,255,255,0.05)',
                  color: '#F5F5F3', outline: 'none', fontSize: 14,
                  boxShadow: '0 1px 0 rgba(255,255,255,0.03) inset',
                }}
                onFocus={(e) => e.currentTarget.style.borderColor = 'rgba(255,255,255,0.22)'}
                onBlur={(e) => e.currentTarget.style.borderColor = 'rgba(255,255,255,0.13)'}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <label htmlFor="login-password" style={{ fontSize: 12, fontWeight: 600, letterSpacing: '-0.01em', color: '#F5F5F3' }}>Password</label>
              <input
                id="login-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                style={{
                  padding: '11px 14px', borderRadius: 12,
                  border: '1px solid rgba(255,255,255,0.13)', background: 'rgba(255,255,255,0.05)',
                  color: '#F5F5F3', outline: 'none', fontSize: 14,
                }}
                onFocus={(e) => e.currentTarget.style.borderColor = 'rgba(255,255,255,0.22)'}
                onBlur={(e) => e.currentTarget.style.borderColor = 'rgba(255,255,255,0.13)'}
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
                marginTop: 4, padding: '12px 16px', borderRadius: 100,
                background: '#F5F5F3', color: '#0A0A0B', border: 'none',
                fontWeight: 700, fontSize: 14, letterSpacing: '-0.02em',
                cursor: loading ? 'not-allowed' : 'pointer',
                boxShadow: '0 1px 0 rgba(255,255,255,0.9) inset, 0 8px 20px rgba(0,0,0,0.22)',
                opacity: loading ? 0.7 : 1,
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              }}
            >
              {loading ? 'Authenticating…' : 'Sign In →'}
            </button>

            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4, fontSize: 13, gap: 12 }}>
              <Link to="/forgot-password" style={{ color: '#8A8A90', textDecoration: 'none' }}>Forgot password?</Link>
              <Link to="/register" style={{ color: '#C8A951', fontWeight: 600, textDecoration: 'none' }}>Request access →</Link>
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
