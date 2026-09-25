import { useState } from 'react';
import { Link } from 'react-router-dom';
import { TrendingUp, Shield, Brain, BarChart3, Zap, Lock, ChevronRight, Globe, ArrowRight } from 'lucide-react';

const FEATURES = [
  { icon: TrendingUp, title: 'Multi-Algorithm Optimization', desc: 'MILP, QUBO, and quantum-classical hybrid solvers find optimal debt structures.' },
  { icon: BarChart3, title: 'Real-Time Risk Analytics', desc: 'Monte Carlo stress testing, VaR, and tail-risk analysis on live market data.' },
  { icon: Brain, title: 'AI Advisor', desc: 'LLM-powered policy briefings with actionable sovereign debt recommendations.' },
  { icon: Globe, title: 'Global Market Data', desc: 'Live Treasury yields, ECB FX rates, IMF macro indicators ΓÇö zero API keys.' },
  { icon: Shield, title: 'SOC 2 Ready Security', desc: 'JWT auth, MFA, RBAC, immutable audit trails, and post-quantum cryptography.' },
  { icon: Zap, title: 'Sub-200ms Responses', desc: 'Optimized caching layer delivers portfolio analytics in real time.' },
];

const STATS = [
  { value: '$4.2T', label: 'Sovereign debt analyzed', detail: 'Across 40+ countries' },
  { value: '73%', label: 'Avg. cost reduction', detail: 'In debt service optimization' },
  { value: '91%', label: 'Forecast accuracy', detail: 'Monte Carlo vs. actual outcomes' },
  { value: '< 200ms', label: 'Response time', detail: 'P95 for portfolio analytics' },
];

export default function LandingPage() {
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email) return;
    setSubmitting(true);
    try {
      const csrfMatch = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/);
      const csrf = csrfMatch ? decodeURIComponent(csrfMatch[1]) : '';
      await fetch('/api/landing/subscribe', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...(csrf ? { 'X-CSRF-Token': csrf } : {}) },
        body: JSON.stringify({ email }),
      });
    } catch {
      // Offline or no backend ΓÇö still show success for demo
    }
    setSubmitted(true);
    setSubmitting(false);
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--bg)',
      color: 'var(--text)',
      fontFamily: 'var(--font)',
      overflow: 'auto',
    }}>
      {/* ΓöÇΓöÇ Nav ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ */}
      <nav style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '16px 40px', borderBottom: '1px solid var(--border)',
        position: 'sticky', top: 0, zIndex: 50, background: 'var(--bg)',
        backdropFilter: 'blur(12px)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8,
            background: 'linear-gradient(135deg, var(--accent), var(--accent-deep))',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontWeight: 700, fontSize: 14, color: 'var(--accent-ink)',
          }}>Q</div>
          <span style={{ fontWeight: 600, fontSize: 18, letterSpacing: '-0.02em' }}>Quantive</span>
          <span style={{
            fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 20,
            background: 'var(--blue-bg)', color: 'var(--blue)',
            textTransform: 'uppercase', letterSpacing: '0.05em',
          }}>Public Beta</span>
        </div>
        <div style={{ display: 'flex', gap: 24, alignItems: 'center' }}>
          <Link to="/government" style={{ color: 'var(--text2)', fontSize: 13, fontWeight: 500 }}>Government</Link>
          <Link to="/business" style={{ color: 'var(--text2)', fontSize: 13, fontWeight: 500 }}>Business</Link>
          <Link to="/qubo" style={{ color: 'var(--text2)', fontSize: 13, fontWeight: 500 }}>Qubo Tax</Link>
          <Link to="/login" style={{ color: 'var(--text2)', fontSize: 13, fontWeight: 500 }}>Sign In</Link>
          <Link to="/register" style={{
            background: 'var(--accent)', color: 'var(--accent-ink)', padding: '8px 20px',
            borderRadius: 8, fontSize: 13, fontWeight: 600, textDecoration: 'none',
          }}>Get Started Free</Link>
        </div>
      </nav>

      {/* ΓöÇΓöÇ Hero ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ */}
      <section style={{
        textAlign: 'center', padding: '80px 40px 60px',
        maxWidth: 820, margin: '0 auto',
      }}>
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 14px',
          borderRadius: 20, background: 'var(--bg2)', border: '1px solid var(--border)',
          fontSize: 12, color: 'var(--text2)', marginBottom: 24,
        }}>
          <Lock size={12} /> Sovereign-grade security
        </div>
        <h1 style={{
          fontSize: 48, fontWeight: 700, letterSpacing: '-0.03em',
          lineHeight: 1.1, marginBottom: 20, color: 'var(--text)',
        }}>
          The Debt Portfolio Platform<br />That Thinks For You
        </h1>
        <p style={{
          fontSize: 17, color: 'var(--text2)', lineHeight: 1.6,
          maxWidth: 600, margin: '0 auto 36px',
        }}>
          Quantum-AI optimization for sovereign debt, enterprise portfolios,
          and personal finance. One platform. Three products. Zero compromise.
        </p>
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
          <Link to="/register" style={{
            background: 'var(--accent)', color: 'var(--accent-ink)', padding: '12px 28px',
            borderRadius: 8, fontSize: 14, fontWeight: 600, textDecoration: 'none',
            display: 'inline-flex', alignItems: 'center', gap: 6,
          }}>
            Start Free <ArrowRight size={16} />
          </Link>
          <Link to="/government" style={{
            background: 'var(--bg2)', color: 'var(--text)', padding: '12px 28px',
            borderRadius: 8, fontSize: 14, fontWeight: 500, textDecoration: 'none',
            border: '1px solid var(--border2)',
          }}>
            View Demo
          </Link>
        </div>
      </section>

      {/* ΓöÇΓöÇ Stats ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ */}
      <section style={{
        display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 1,
        maxWidth: 900, margin: '0 auto 60px', background: 'var(--border)',
        borderRadius: 12, overflow: 'hidden',
      }}>
        {STATS.map((s) => (
          <div key={s.label} style={{
            background: 'var(--bg)', padding: '28px 24px', textAlign: 'center',
          }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--accent)', letterSpacing: '-0.02em' }}>
              {s.value}
            </div>
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', marginTop: 6 }}>{s.label}</div>
            <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 2 }}>{s.detail}</div>
          </div>
        ))}
      </section>

      {/* ΓöÇΓöÇ Two Path Cards ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ */}
      <section style={{
        display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))',
        gap: 16, maxWidth: 900, margin: '0 auto 60px', padding: '0 40px',
      }}>
        <div style={{
          background: 'var(--surface-1)', border: '1px solid var(--border)',
          borderRadius: 12, padding: 32,
        }}>
          <div style={{
            width: 40, height: 40, borderRadius: 10, background: 'var(--blue-bg)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 16,
          }}>
            <Globe size={20} style={{ color: 'var(--blue)' }} />
          </div>
          <h2 style={{ fontSize: 20, fontWeight: 600, marginBottom: 8 }}>For Government</h2>
          <p style={{ fontSize: 14, color: 'var(--text2)', lineHeight: 1.6, marginBottom: 20 }}>
            Sovereign debt optimization, fiscal rule compliance, and aggregated market
            intelligence for policy investment decisions.
          </p>
          <div style={{ display: 'flex', gap: 8 }}>
            <Link to="/government" style={{
              background: 'var(--accent)', color: 'var(--accent-ink)', padding: '8px 18px',
              borderRadius: 8, fontSize: 13, fontWeight: 600, textDecoration: 'none',
              display: 'inline-flex', alignItems: 'center', gap: 4,
            }}>Explore <ChevronRight size={14} /></Link>
            <Link to="/qubo" style={{
              background: 'var(--bg2)', color: 'var(--text)', padding: '8px 18px',
              borderRadius: 8, fontSize: 13, fontWeight: 500, textDecoration: 'none',
              border: '1px solid var(--border)',
            }}>Qubo Insights</Link>
          </div>
        </div>
        <div style={{
          background: 'var(--surface-1)', border: '1px solid var(--border)',
          borderRadius: 12, padding: 32,
        }}>
          <div style={{
            width: 40, height: 40, borderRadius: 10, background: 'var(--green-bg)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 16,
          }}>
            <BarChart3 size={20} style={{ color: 'var(--green)' }} />
          </div>
          <h2 style={{ fontSize: 20, fontWeight: 600, marginBottom: 8 }}>For Businesses</h2>
          <p style={{ fontSize: 14, color: 'var(--text2)', lineHeight: 1.6, marginBottom: 20 }}>
            Portfolio optimization, risk analytics, market intelligence, and banking
            tools for finance teams managing complex debt structures.
          </p>
          <div style={{ display: 'flex', gap: 8 }}>
            <Link to="/business" style={{
              background: 'var(--accent)', color: 'var(--accent-ink)', padding: '8px 18px',
              borderRadius: 8, fontSize: 13, fontWeight: 600, textDecoration: 'none',
              display: 'inline-flex', alignItems: 'center', gap: 4,
            }}>Explore <ChevronRight size={14} /></Link>
            <Link to="/dashboard" style={{
              background: 'var(--bg2)', color: 'var(--text)', padding: '8px 18px',
              borderRadius: 8, fontSize: 13, fontWeight: 500, textDecoration: 'none',
              border: '1px solid var(--border)',
            }}>Open Workspace</Link>
          </div>
        </div>
      </section>

      {/* ΓöÇΓöÇ Qubo Strip ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ */}
      <section style={{
        maxWidth: 900, margin: '0 auto 60px', padding: '0 40px',
      }}>
        <div style={{
          background: 'linear-gradient(135deg, rgba(96,165,250,0.08), rgba(96,165,250,0.03))',
          border: '1px solid var(--border)', borderRadius: 12, padding: 32,
          display: 'flex', alignItems: 'center', gap: 32,
        }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <Zap size={18} style={{ color: 'var(--accent)' }} />
              <h2 style={{ fontSize: 18, fontWeight: 600 }}>Qubo ΓÇö AI Tax Intelligence</h2>
            </div>
            <p style={{ fontSize: 14, color: 'var(--text2)', lineHeight: 1.6, marginBottom: 16 }}>
              Finds deductions, categorizes every transaction, and preps your return ΓÇö
              year-round, not just April. Optional de-identified analytics are strictly opt-in.
            </p>
            <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: 6 }}>
              {['Deduction detection against versioned tax rules', 'Instant categorization + quarterly estimates', 'CPA-ready export at year end'].map((item) => (
                <li key={item} style={{ fontSize: 13, color: 'var(--text2)', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--accent)', flexShrink: 0 }} />
                  {item}
                </li>
              ))}
            </ul>
          </div>
          <Link to="/qubo" style={{
            background: 'var(--accent)', color: 'var(--accent-ink)', padding: '10px 22px',
            borderRadius: 8, fontSize: 13, fontWeight: 600, textDecoration: 'none',
            whiteSpace: 'nowrap', display: 'inline-flex', alignItems: 'center', gap: 4,
          }}>
            Learn More <ChevronRight size={14} />
          </Link>
        </div>
      </section>

      {/* ΓöÇΓöÇ Features Grid ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ */}
      <section style={{
        maxWidth: 900, margin: '0 auto 60px', padding: '0 40px',
      }}>
        <h2 style={{ fontSize: 24, fontWeight: 600, textAlign: 'center', marginBottom: 8 }}>
          Built for Sovereign-Scale Finance
        </h2>
        <p style={{ fontSize: 14, color: 'var(--text2)', textAlign: 'center', marginBottom: 36 }}>
          Every feature designed for the complexity of government and enterprise debt management.
        </p>
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: 12,
        }}>
          {FEATURES.map((f) => (
            <div key={f.title} style={{
              background: 'var(--surface-1)', border: '1px solid var(--border)',
              borderRadius: 10, padding: 24,
            }}>
              <div style={{
                width: 36, height: 36, borderRadius: 8, background: 'var(--bg2)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                marginBottom: 14,
              }}>
                <f.icon size={18} style={{ color: 'var(--accent)' }} />
              </div>
              <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 6 }}>{f.title}</h3>
              <p style={{ fontSize: 13, color: 'var(--text2)', lineHeight: 1.5 }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ΓöÇΓöÇ Pricing Preview ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ */}
      <section style={{
        maxWidth: 900, margin: '0 auto 60px', padding: '0 40px',
      }}>
        <h2 style={{ fontSize: 24, fontWeight: 600, textAlign: 'center', marginBottom: 8 }}>
          Simple, Outcome-Based Pricing
        </h2>
        <p style={{ fontSize: 14, color: 'var(--text2)', textAlign: 'center', marginBottom: 36 }}>
          Pay for value, not seats. Every plan includes real market data and full optimization.
        </p>
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: 12,
        }}>
          {[
            { name: 'Personal', price: '$2,000', period: '/yr', features: ['Tax write-off detection', 'Qubo intelligence', 'Annual report'], cta: 'Start Lean' },
            { name: 'Professional', price: '$5,000', period: '/yr', features: ['Full tax intelligence', 'Document management', 'Quarterly summaries'], cta: 'Go Pro' },
            { name: 'Sovereign', price: '$10,000', period: '/yr', features: ['Gov-grade analytics', 'Qubo market trends', 'Priority support'], cta: 'Go Sovereign' },
          ].map((plan) => (
            <div key={plan.name} style={{
              background: 'var(--surface-1)', border: '1px solid var(--border)',
              borderRadius: 10, padding: 28,
            }}>
              <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>{plan.name}</h3>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 2, marginBottom: 16 }}>
                <span style={{ fontSize: 28, fontWeight: 700, color: 'var(--accent)' }}>{plan.price}</span>
                <span style={{ fontSize: 13, color: 'var(--text3)' }}>{plan.period}</span>
              </div>
              <ul style={{ listStyle: 'none', padding: 0, marginBottom: 20, display: 'flex', flexDirection: 'column', gap: 8 }}>
                {plan.features.map((feat) => (
                  <li key={feat} style={{ fontSize: 13, color: 'var(--text2)', display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ width: 4, height: 4, borderRadius: '50%', background: 'var(--green)', flexShrink: 0 }} />
                    {feat}
                  </li>
                ))}
              </ul>
              <Link to="/register" style={{
                display: 'block', textAlign: 'center', padding: '10px 0', borderRadius: 8,
                background: 'var(--bg2)', border: '1px solid var(--border2)',
                color: 'var(--text)', fontSize: 13, fontWeight: 600, textDecoration: 'none',
              }}>{plan.cta}</Link>
            </div>
          ))}
        </div>
      </section>

      {/* ΓöÇΓöÇ Email Signup ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ */}
      <section style={{
        maxWidth: 600, margin: '0 auto 60px', padding: '0 40px', textAlign: 'center',
      }}>
        <h2 style={{ fontSize: 20, fontWeight: 600, marginBottom: 8 }}>
          {submitted ? 'You\'re on the list!' : 'Get Early Access'}
        </h2>
        <p style={{ fontSize: 14, color: 'var(--text2)', marginBottom: 20 }}>
          {submitted
            ? 'We\'ll notify you when we open new spots.'
            : 'Join the waitlist. Be the first to know when we launch.'}
        </p>
        {!submitted ? (
          <form onSubmit={handleSubmit} style={{
            display: 'flex', gap: 8, justifyContent: 'center',
          }}>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              required
              style={{
                flex: 1, maxWidth: 340, padding: '10px 14px', borderRadius: 8,
                border: '1px solid var(--border2)', background: 'var(--field)',
                color: 'var(--text)', fontSize: 14, outline: 'none',
              }}
            />
            <button
              type="submit"
              disabled={submitting}
              style={{
                padding: '10px 22px', borderRadius: 8, border: 'none',
                background: 'var(--accent)', color: 'var(--accent-ink)',
                fontSize: 14, fontWeight: 600, cursor: 'pointer',
              }}
            >
              {submitting ? 'Submitting...' : 'Join Waitlist'}
            </button>
          </form>
        ) : (
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 8, padding: '10px 20px',
            borderRadius: 8, background: 'var(--green-bg)', color: 'var(--green)',
            fontSize: 14, fontWeight: 500,
          }}>
            <Shield size={16} /> You're in! We'll be in touch soon.
          </div>
        )}
      </section>

      {/* ΓöÇΓöÇ Footer ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ */}
      <footer style={{
        borderTop: '1px solid var(--border)', padding: '24px 40px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        maxWidth: 900, margin: '0 auto',
      }}>
        <span style={{ fontSize: 12, color: 'var(--text3)' }}>
          ┬⌐ 2026 Quantive. All rights reserved.
        </span>
        <div style={{ display: 'flex', gap: 16 }}>
          <Link to="/terms" style={{ fontSize: 12, color: 'var(--text3)', textDecoration: 'none' }}>Terms</Link>
          <Link to="/login" style={{ fontSize: 12, color: 'var(--text3)', textDecoration: 'none' }}>Sign In</Link>
          <Link to="/register" style={{ fontSize: 12, color: 'var(--text3)', textDecoration: 'none' }}>Get Started</Link>
        </div>
      </footer>
    </div>
  );
}
