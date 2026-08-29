import { Link } from 'react-router-dom';
import { useState } from 'react';

const FEATURES = [
  {
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5" />
      </svg>
    ),
    title: 'Multi-Algorithm Optimization',
    desc: 'Solve debt restructuring, hedging, and refinancing simultaneously with explainable AI.',
  },
  {
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    title: 'Real-Time Risk Analytics',
    desc: 'VaR analysis, stress testing, and scenario modeling with live market data feeds.',
  },
  {
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
      </svg>
    ),
    title: 'AI Advisor',
    desc: 'Ask natural language questions about your portfolio. Get actionable recommendations with full explainability.',
  },
  {
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418" />
      </svg>
    ),
    title: 'ESG & Rating Simulation',
    desc: 'Integrate ESG scoring with bond rating impact simulation across S&P and Moody\'s methodologies.',
  },
  {
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
      </svg>
    ),
    title: 'Interactive Dashboards',
    desc: 'What-if playground, maturity ladders, peer comparisons — all in a Liquid Glass interface.',
  },
  {
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
      </svg>
    ),
    title: 'SOC 2 Ready Security',
    desc: 'Enterprise-grade security with MFA, RBAC, audit logging, and encryption at rest.',
  },
];

const STATS = [
  { value: '$3.2B', label: 'Market size by 2028' },
  { value: '73%', label: 'CFOs still use Excel' },
  { value: '91%', label: 'Want AI-assisted decisions' },
  { value: '< 15ms', label: 'Health endpoint' },
];

export default function LandingPage() {
  const [email, setEmail] = useState('');

  return (
    <div className="min-h-screen" style={{ background: '#0a0b0e' }}>
      {/* Ambient background glow */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute top-[-20%] left-[-10%] w-[700px] h-[700px] rounded-full opacity-30" style={{ background: 'radial-gradient(circle, rgba(200,169,81,0.12) 0%, transparent 70%)' }} />
        <div className="absolute bottom-[-15%] right-[-10%] w-[600px] h-[600px] rounded-full opacity-20" style={{ background: 'radial-gradient(circle, rgba(100,120,200,0.15) 0%, transparent 70%)' }} />
        <div className="absolute top-[40%] left-[50%] w-[800px] h-[500px] rounded-full opacity-10 -translate-x-1/2" style={{ background: 'radial-gradient(circle, rgba(140,100,200,0.1) 0%, transparent 60%)' }} />
      </div>

      <div className="relative z-10">
        {/* Nav */}
        <nav className="liquid-glass liquid-glass--subtle mx-4 lg:mx-8 mt-4 px-6 py-3 flex items-center justify-between" style={{ borderRadius: '16px' }}>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center text-white font-bold text-sm" style={{ background: 'linear-gradient(135deg, #c8a951, #a08a3e)', boxShadow: '0 4px 16px rgba(200,169,81,0.3)' }}>
              Q
            </div>
            <span className="text-base font-bold tracking-tight" style={{ color: '#e8eaed' }}>Quantive</span>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/login" className="text-sm font-medium transition-colors" style={{ color: '#8590a0' }}>
              Sign In
            </Link>
            <Link
              to="/register"
              className="glass-btn glass-btn-primary text-sm"
            >
              Get Started Free
            </Link>
          </div>
        </nav>

        <main>
          {/* Hero */}
          <section className="relative overflow-hidden px-6 lg:px-12 pt-20 pb-28">
            <div className="relative max-w-4xl mx-auto text-center">
              <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full mb-8" style={{ background: 'rgba(200,169,81,0.08)', border: '1px solid rgba(200,169,81,0.2)', color: '#c8a951', fontSize: '13px', fontWeight: 600 }}>
                <span className="w-2 h-2 rounded-full animate-pulse" style={{ background: '#c8a951' }} />
                Now in Public Beta
              </div>

              <h1 className="text-4xl sm:text-5xl lg:text-7xl font-extrabold tracking-tight leading-[1.05]" style={{ color: '#e8eaed' }}>
                The Debt Portfolio Platform
                <br />
                <span style={{ background: 'linear-gradient(135deg, #c8a951, #f5e6c8, #c8a951)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                  That Thinks For You
                </span>
              </h1>

              <p className="mt-6 text-lg max-w-2xl mx-auto leading-relaxed" style={{ color: '#8590a0' }}>
                Optimize sovereign debt portfolios with AI-powered recommendations, real-time risk analytics,
                and ESG integration — all in a Liquid Glass interface.
              </p>

              <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mt-10">
                <Link
                  to="/register"
                  className="glass-btn glass-btn-primary text-base px-8 py-3.5"
                >
                  Start Optimizing Free
                  <svg className="ml-2 h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                  </svg>
                </Link>
                <a href="#features" className="glass-btn text-base px-8 py-3.5" style={{ color: '#8590a0' }}>
                  See Features
                </a>
              </div>
            </div>
          </section>

          {/* Stats — liquid glass cards */}
          <section className="px-6 lg:px-12 pb-20">
            <div className="max-w-4xl mx-auto grid grid-cols-2 lg:grid-cols-4 gap-4">
              {STATS.map((stat) => (
                <div key={stat.label} className="liquid-glass p-6 text-center" style={{ borderRadius: '20px' }}>
                  <div className="liquid-glass-tint" />
                  <div className="liquid-glass-shine" />
                  <div className="liquid-glass-content">
                    <div className="text-2xl font-extrabold" style={{ color: '#c8a951' }}>{stat.value}</div>
                    <div className="text-xs mt-1.5" style={{ color: '#8590a0' }}>{stat.label}</div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Features — liquid glass cards */}
          <section id="features" className="px-6 lg:px-12 pb-24">
            <div className="max-w-5xl mx-auto">
              <h2 className="text-3xl font-extrabold text-center tracking-tight" style={{ color: '#e8eaed' }}>
                Everything you need to optimize
              </h2>
              <p className="text-center mt-3 max-w-xl mx-auto" style={{ color: '#5f6672', fontSize: '15px' }}>
                From portfolio creation to optimization execution — Quantive handles the full workflow.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 mt-12">
                {FEATURES.map((f) => (
                  <div
                    key={f.title}
                    className="liquid-glass p-6 group"
                    style={{ borderRadius: '20px' }}
                  >
                    <div className="liquid-glass-tint" />
                    <div className="liquid-glass-shine" />
                    <div className="liquid-glass-content relative z-10">
                      <div className="w-10 h-10 rounded-xl flex items-center justify-center mb-4 transition-transform group-hover:scale-110" style={{ background: 'rgba(200,169,81,0.1)', color: '#c8a951' }}>
                        {f.icon}
                      </div>
                      <h3 className="text-base font-bold" style={{ color: '#e8eaed' }}>{f.title}</h3>
                      <p className="text-sm mt-2 leading-relaxed" style={{ color: '#8590a0' }}>{f.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* CTA — liquid glass */}
          <section className="px-6 lg:px-12 pb-24">
            <div className="max-w-3xl mx-auto text-center liquid-glass liquid-glass--vivid p-10" style={{ borderRadius: '28px' }}>
              <div className="liquid-glass-tint" />
              <div className="liquid-glass-shine" />
              <div className="liquid-glass-content relative z-10">
                <h2 className="text-2xl font-extrabold" style={{ color: '#e8eaed' }}>Ready to optimize your debt portfolio?</h2>
                <p className="mt-3" style={{ color: '#8590a0' }}>
                  Join the beta. Free for portfolios under $500M.
                </p>
                <form
                  className="mt-6 flex flex-col sm:flex-row items-center justify-center gap-3"
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (email) {
                      window.location.href = `/register?email=${encodeURIComponent(email)}`;
                    }
                  }}
                >
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@company.com"
                    className="glass-input w-full sm:w-72"
                    aria-label="Email address"
                  />
                  <button type="submit" className="glass-btn glass-btn-primary w-full sm:w-auto">
                    Get Early Access
                  </button>
                </form>
              </div>
            </div>
          </section>

          {/* Footer */}
          <footer className="px-6 lg:px-12 py-8" style={{ borderTop: '1px solid rgba(255,255,255,0.04)' }}>
            <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-xs" style={{ color: '#5f6672' }}>
              <span>&copy; {new Date().getFullYear()} Quantive. All rights reserved.</span>
              <div className="flex items-center gap-4">
                <a href="#" className="hover:text-white/60 transition-colors">Privacy</a>
                <a href="#" className="hover:text-white/60 transition-colors">Terms</a>
                <a href="#" className="hover:text-white/60 transition-colors">Security</a>
                <a href="#" className="hover:text-white/60 transition-colors">Status</a>
              </div>
            </div>
          </footer>
        </main>
      </div>
    </div>
  );
}
