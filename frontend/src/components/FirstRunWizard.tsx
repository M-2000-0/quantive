import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  CheckCircle,
  FileSpreadsheet,
  Loader2,
  Rocket,
  Sparkles,
  TrendingUp,
  Wallet,
  X } from 'lucide-react';
import { api } from '../api';

const WIZARD_DISMISS_KEY = 'quantive_wizard_dismissed';

// ── Types ──────────────────────────────────────────────────────────

interface OnboardingStatus {
  has_portfolios: boolean;
  has_instruments: boolean;
  has_optimizations: boolean;
  onboarding_complete: boolean;
  current_step: string;
  portfolio_count: number;
  instrument_count: number;
  optimization_count: number;
}

interface QuickStartData {
  onboarding: OnboardingStatus;
  market: {
    yield_curve: { rates: Record<string, number>; status?: string };
    fx_rates: Record<string, unknown>;
    interest_rates: Record<string, unknown>;
  };
  demo_instruments_count: number;
  demo_total_debt: number;
  demo_currencies: string[];
}

interface DemoPortfolioResult {
  status: string;
  portfolio_id: string;
  portfolio_name: string;
  instruments_created: number;
  total_debt: number;
  currencies: string[];
  message: string;
}

interface QuickOptimizeResult {
  status: string;
  job_id: string;
  portfolio_id: string;
  portfolio_name: string;
  estimated_time_seconds: number;
  message: string;
}

interface SavingsOpportunity {
  opportunity: {
    title: string;
    subtitle: string;
    annual_savings_usd: number;
    savings_percentage: number;
    confidence_pct: number;
    strategy_name: string;
    description: string;
    action_label: string;
    action_url: string;
  } | null;
  actual_savings: {
    completed_optimizations: number;
    savings_percentage: number;
  };
  portfolio_summary: {
    total_debt: number;
    weighted_coupon: number;
    instrument_count: number;
    currencies: string[];
  };
}

// ── Helpers ─────────────────────────────────────────────────────────

function formatCurrency(value: number): string {
  if (value >= 1e12) return `$${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `$${(value / 1e3).toFixed(1)}K`;
  return `$${value.toFixed(0)}`;
}

// ── Component ───────────────────────────────────────────────────────

export default function FirstRunWizard() {
  const [step, setStep] = useState<'loading' | 'welcome' | 'creating' | 'ready' | 'optimizing' | 'results' | 'done'>('loading');
  const [quickStartData, setQuickStartData] = useState<QuickStartData | null>(null);
  const [demoResult, setDemoResult] = useState<DemoPortfolioResult | null>(null);
  const [optimizeResult, setOptimizeResult] = useState<QuickOptimizeResult | null>(null);
  const [savings, setSavings] = useState<SavingsOpportunity | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<number | null>(null);
  const timeoutRef = useRef<number | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current !== null) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
    if (timeoutRef.current !== null) {
      window.clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  // Stop polling if the wizard unmounts mid-run
  useEffect(() => () => stopPolling(), [stopPolling]);

  // Skip wizard — persist so it stays dismissed
  const handleSkip = useCallback(() => {
    stopPolling();
    try {
      localStorage.setItem(WIZARD_DISMISS_KEY, 'true');
    } catch {
      /* storage unavailable */
    }
    setStep('done');
  }, [stopPolling]);

  // Load initial data
  useEffect(() => {
    let cancelled = false;
    try {
      if (localStorage.getItem(WIZARD_DISMISS_KEY) === 'true') {
        setStep('done');
        return () => { cancelled = true; };
      }
    } catch {
      /* ignore */
    }
    async function load() {
      try {
        const data = await api.firstRun.quickStartData() as unknown as QuickStartData;
        if (cancelled) return;
        setQuickStartData(data);

        const onboarding = data.onboarding;
        if (onboarding.onboarding_complete) {
          setStep('done');
        } else if (onboarding.has_portfolios && onboarding.has_instruments) {
          setStep('ready');
        } else {
          setStep('welcome');
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : 'Failed to load');
          setStep('welcome');
        }
      }
    }
    void load();
    return () => { cancelled = true; };
  }, []);

  // Create demo portfolio
  const handleCreateDemo = useCallback(async () => {
    setStep('creating');
    setError(null);
    try {
      const result = await api.firstRun.createDemoPortfolio() as unknown as DemoPortfolioResult;
      setDemoResult(result);
      setStep('ready');

      // Also fetch savings opportunity
      const savingsData = await api.firstRun.savingsOpportunity(result.portfolio_id) as unknown as SavingsOpportunity;
      setSavings(savingsData);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create demo portfolio');
      setStep('welcome');
    }
  }, []);

  // Run quick optimization
  const handleQuickOptimize = useCallback(async () => {
    setStep('optimizing');
    setError(null);
    try {
      const portfolioId = demoResult?.portfolio_id;
      const result = await api.firstRun.quickOptimize(portfolioId) as unknown as QuickOptimizeResult;
      setOptimizeResult(result);
      setStep('results');

      // Poll for completion — timers are tracked so they can be
      // cancelled on dismiss/unmount instead of leaking.
      stopPolling();
      pollRef.current = window.setInterval(async () => {
        try {
          const status = await api.optimizations.get(result.job_id) as { status: string };
          if (status.status === 'completed') {
            stopPolling();
            // Fetch savings opportunity after completion
            const savingsData = await api.firstRun.savingsOpportunity(result.portfolio_id) as unknown as SavingsOpportunity;
            setSavings(savingsData);
            setStep('done');
          }
        } catch {
          // ignore poll errors
        }
      }, 3000);

      // Stop polling after 2 minutes
      timeoutRef.current = window.setTimeout(() => stopPolling(), 120000);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start optimization');
      setStep('ready');
    }
  }, [demoResult, stopPolling]);

  if (step === 'done') return null;

  // ── Loading ──────────────────────────────────────────────────

  if (step === 'loading') {
    return (
      <div className="wizard-overlay" style={containerStyle}>
        <div role="dialog" aria-modal="true" aria-label="Preparing your experience" style={cardStyle}>
          <Loader2 size={32} style={{ animation: 'spin 1s linear infinite', color: '#6366f1' }} />
          <p style={{ color: '#6b7280', marginTop: 12 }}>Preparing your experience...</p>
        </div>
      </div>
    );
  }

  // ── Welcome Step ─────────────────────────────────────────────

  if (step === 'welcome') {
    return (
      <div className="wizard-overlay" style={containerStyle}>
        <div role="dialog" aria-modal="true" aria-label="Welcome to Quantive" style={{ ...cardStyle, maxWidth: 640 }}>
          <button type="button" onClick={handleSkip} aria-label="Dismiss setup guide" style={dismissButtonStyle}>
            <X size={18} />
          </button>
          <div style={{ textAlign: 'center', marginBottom: 32 }}>
            <div style={logoStyle}>
              <Sparkles size={24} color="#fff" />
            </div>
            <h1 style={{ fontSize: 28, fontWeight: 700, color: '#111827', marginTop: 16, marginBottom: 8 }}>
              Welcome to Quantive
            </h1>
            <p style={{ color: '#6b7280', fontSize: 16, lineHeight: 1.6 }}>
              The sovereign debt optimization engine that helps governments
              save millions in financing costs.
            </p>
          </div>

          <div className="qa-grid-3" style={{ display: 'grid', gap: 16, marginBottom: 32 }}>
            <div style={featureCardStyle}>
              <Wallet size={24} color="#6366f1" />
              <h3 style={{ fontSize: 14, fontWeight: 600, color: '#374151', marginTop: 8 }}>Model Portfolio</h3>
              <p style={{ fontSize: 12, color: '#9ca3af', marginTop: 4 }}>12 instruments across 5 currencies</p>
            </div>
            <div style={featureCardStyle}>
              <TrendingUp size={24} color="#10b981" />
              <h3 style={{ fontSize: 14, fontWeight: 600, color: '#374151', marginTop: 8 }}>Optimize Strategy</h3>
              <p style={{ fontSize: 12, color: '#9ca3af', marginTop: 4 }}>Multiple solver backends, 1K scenarios</p>
            </div>
            <div style={featureCardStyle}>
              <FileSpreadsheet size={24} color="#f59e0b" />
              <h3 style={{ fontSize: 14, fontWeight: 600, color: '#374151', marginTop: 8 }}>See Savings</h3>
              <p style={{ fontSize: 12, color: '#9ca3af', marginTop: 4 }}>Concrete dollar impact in minutes</p>
            </div>
          </div>

          {error && (
            <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8, padding: 12, marginBottom: 16, color: '#dc2626', fontSize: 14 }}>
              {error}
            </div>
          )}

          <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
            <button
              type="button"
              onClick={handleCreateDemo}
              style={primaryButtonStyle}
            >
              <Rocket size={16} />
              Get Started — Create Demo Portfolio
            </button>
            <button
              type="button"
              onClick={handleSkip}
              style={ghostButtonStyle}
            >
              I'll set up my own portfolio
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Creating Portfolio ───────────────────────────────────────

  if (step === 'creating') {
    return (
      <div className="wizard-overlay" style={containerStyle}>
        <div role="dialog" aria-modal="true" aria-label="Creating your demo portfolio" style={cardStyle}>
          <Loader2 size={32} style={{ animation: 'spin 1s linear infinite', color: '#6366f1' }} />
          <h2 style={{ fontSize: 20, fontWeight: 600, color: '#111827', marginTop: 16 }}>Creating your demo portfolio</h2>
          <p style={{ color: '#6b7280', marginTop: 8 }}>Generating 12 sovereign debt instruments...</p>
        </div>
      </div>
    );
  }

  // ── Ready to Optimize ────────────────────────────────────────

  if (step === 'ready') {
    return (
      <div className="wizard-overlay" style={containerStyle}>
        <div role="dialog" aria-modal="true" aria-label="Portfolio ready" style={{ ...cardStyle, maxWidth: 600 }}>
          <button type="button" onClick={handleSkip} aria-label="Dismiss setup guide" style={dismissButtonStyle}>
            <X size={18} />
          </button>
          <div style={{ textAlign: 'center' }}>
            <div style={{ ...checkCircleStyle, background: '#ecfdf5' }}>
              <CheckCircle size={32} color="#10b981" />
            </div>
            <h2 style={{ fontSize: 22, fontWeight: 700, color: '#111827', marginTop: 16, marginBottom: 8 }}>
              Portfolio Ready!
            </h2>
            <p style={{ color: '#6b7280', fontSize: 15, lineHeight: 1.6 }}>
              {demoResult?.message || 'Your portfolio is ready for optimization.'}
            </p>
          </div>

          {demoResult && (
            <div className="qa-grid-3" style={summaryGridStyle}>
              <div style={summaryItemStyle}>
                <span style={summaryLabelStyle}>Total Debt</span>
                <span style={summaryValueStyle}>{formatCurrency(demoResult.total_debt)}</span>
              </div>
              <div style={summaryItemStyle}>
                <span style={summaryLabelStyle}>Instruments</span>
                <span style={summaryValueStyle}>{demoResult.instruments_created}</span>
              </div>
              <div style={summaryItemStyle}>
                <span style={summaryLabelStyle}>Currencies</span>
                <span style={summaryValueStyle}>{demoResult.currencies.join(', ')}</span>
              </div>
            </div>
          )}

          {/* Savings Opportunity Card */}
          {savings?.opportunity && (
            <div style={savingsCardStyle}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <TrendingUp size={18} color="#10b981" />
                <span style={{ fontSize: 13, fontWeight: 600, color: '#065f46' }}>Savings Opportunity Detected</span>
              </div>
              <h3 style={{ fontSize: 20, fontWeight: 700, color: '#064e3b', marginBottom: 4 }}>
                {savings.opportunity.title}
              </h3>
              <p style={{ fontSize: 13, color: '#047857', marginBottom: 8 }}>
                {savings.opportunity.description}
              </p>
              <div style={{ display: 'flex', gap: 16, fontSize: 12, color: '#059669' }}>
                <span>Confidence: {savings.opportunity.confidence_pct}%</span>
                <span>Strategy: {savings.opportunity.strategy_name}</span>
              </div>
            </div>
          )}

          {error && (
            <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8, padding: 12, marginBottom: 16, color: '#dc2626', fontSize: 14 }}>
              {error}
            </div>
          )}

          <div style={{ display: 'flex', gap: 12, justifyContent: 'center', marginTop: 24 }}>
            <button
              type="button"
              onClick={handleQuickOptimize}
              style={primaryButtonStyle}
            >
              <Sparkles size={16} />
              Run First Optimization
            </button>
            <button
              type="button"
              onClick={handleSkip}
              style={ghostButtonStyle}
            >
              Skip for now
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Optimizing ───────────────────────────────────────────────

  if (step === 'optimizing') {
    return (
      <div className="wizard-overlay" style={containerStyle}>
        <div role="dialog" aria-modal="true" aria-label="Running optimization" style={cardStyle}>
          <div style={{ textAlign: 'center' }}>
            <div style={spinnerPulseStyle}>
              <Loader2 size={40} style={{ animation: 'spin 1.5s linear infinite', color: '#6366f1' }} />
            </div>
            <h2 style={{ fontSize: 22, fontWeight: 700, color: '#111827', marginTop: 20, marginBottom: 8 }}>
              Running Optimization
            </h2>
            <p style={{ color: '#6b7280', fontSize: 15, marginBottom: 24 }}>
              {optimizeResult?.message || 'Analyzing portfolio across 1,000 Monte Carlo scenarios...'}
            </p>

            <div style={progressStepsStyle}>
              <ProgressStep label="Scenarios" active={true} done={false} />
              <ProgressStep label="Solving" active={false} done={false} />
              <ProgressStep label="Benchmarking" active={false} done={false} />
              <ProgressStep label="Stress Test" active={false} done={false} />
              <ProgressStep label="Results" active={false} done={false} />
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ── Results ──────────────────────────────────────────────────

  if (step === 'results') {
    return (
      <div className="wizard-overlay" style={containerStyle}>
        <div role="dialog" aria-modal="true" aria-label="Optimization complete" style={{ ...cardStyle, maxWidth: 640 }}>
          <button type="button" onClick={handleSkip} aria-label="Dismiss setup guide" style={dismissButtonStyle}>
            <X size={18} />
          </button>
          <div style={{ textAlign: 'center' }}>
            <div style={{ ...checkCircleStyle, background: '#ecfdf5' }}>
              <CheckCircle size={32} color="#10b981" />
            </div>
            <h2 style={{ fontSize: 22, fontWeight: 700, color: '#111827', marginTop: 16, marginBottom: 8 }}>
              Optimization Complete!
            </h2>
            <p style={{ color: '#6b7280', fontSize: 15 }}>
              Your first optimization is done. Here's what we found.
            </p>
          </div>

          {/* Results Summary */}
          {savings?.opportunity && (
            <div style={savingsCardStyle}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <TrendingUp size={18} color="#10b981" />
                <span style={{ fontSize: 13, fontWeight: 600, color: '#065f46' }}>Optimization Results</span>
              </div>
              <h3 style={{ fontSize: 24, fontWeight: 700, color: '#064e3b', marginBottom: 8 }}>
                {savings.opportunity.title}
              </h3>
              <p style={{ fontSize: 14, color: '#047857', marginBottom: 12, lineHeight: 1.6 }}>
                {savings.opportunity.description}
              </p>
              <div className="qa-grid-3" style={{ display: 'grid', gap: 12, marginTop: 12 }}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 20, fontWeight: 700, color: '#065f46' }}>
                    {formatCurrency(savings.opportunity.annual_savings_usd)}
                  </div>
                  <div style={{ fontSize: 11, color: '#059669' }}>Annual Savings</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 20, fontWeight: 700, color: '#065f46' }}>
                    {savings.opportunity.confidence_pct}%
                  </div>
                  <div style={{ fontSize: 11, color: '#059669' }}>Confidence</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 20, fontWeight: 700, color: '#065f46' }}>
                    {formatCurrency(savings.opportunity.annual_savings_usd * 5)}
                  </div>
                  <div style={{ fontSize: 11, color: '#059669' }}>5-Year Savings</div>
                </div>
              </div>
            </div>
          )}

          <div style={{ display: 'flex', gap: 12, justifyContent: 'center', marginTop: 24 }}>
            <Link
              to="/optimizations"
              style={{ ...primaryButtonStyle, textDecoration: 'none' }}
            >
              View Full Results
            </Link>
            <Link
              to="/dashboard"
              style={{ ...ghostButtonStyle, textDecoration: 'none' }}
            >
              Go to Dashboard
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return null;
}

// ── Progress Step ────────────────────────────────────────────────

function ProgressStep({ label, active, done }: { label: string; active: boolean; done: boolean }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
      <div
        style={{
          width: 24,
          height: 24,
          borderRadius: '50%',
          background: done ? '#10b981' : active ? '#6366f1' : '#e5e7eb',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center' }}
      >
        {done ? (
          <CheckCircle size={14} color="#fff" />
        ) : active ? (
          <Loader2 size={12} color="#fff" style={{ animation: 'spin 1s linear infinite' }} />
        ) : null}
      </div>
      <span style={{ fontSize: 10, color: active ? '#6366f1' : '#9ca3af', fontWeight: active ? 600 : 400 }}>
        {label}
      </span>
    </div>
  );
}

// ── Styles ───────────────────────────────────────────────────────

const containerStyle: React.CSSProperties = {
  position: 'fixed',
  inset: 0,
  zIndex: 100,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  background: 'rgba(17, 24, 39, 0.55)',
  padding: 24,
  overflowY: 'auto' };

const cardStyle: React.CSSProperties = {
  position: 'relative',
  background: '#fff',
  borderRadius: 16,
  padding: 40,
  boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
  width: '100%',
  maxWidth: 560,
  maxHeight: '90vh',
  overflowY: 'auto' };

const dismissButtonStyle: React.CSSProperties = {
  position: 'absolute',
  top: 12,
  right: 12,
  background: 'transparent',
  border: 'none',
  cursor: 'pointer',
  color: '#9ca3af',
  display: 'flex',
  padding: 4 };

const featureCardStyle: React.CSSProperties = {
  background: '#f9fafb',
  borderRadius: 12,
  padding: 16,
  textAlign: 'center',
  border: '1px solid #f3f4f6' };

const logoStyle: React.CSSProperties = {
  width: 48,
  height: 48,
  borderRadius: 12,
  background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center' };

const primaryButtonStyle: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 8,
  padding: '12px 24px',
  borderRadius: 10,
  border: 'none',
  background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
  color: '#fff',
  fontSize: 15,
  fontWeight: 600,
  cursor: 'pointer',
  transition: 'all 0.2s' };

const ghostButtonStyle: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 8,
  padding: '12px 24px',
  borderRadius: 10,
  border: '1px solid #e5e7eb',
  background: '#fff',
  color: '#6b7280',
  fontSize: 14,
  fontWeight: 500,
  cursor: 'pointer',
  transition: 'all 0.2s' };

const checkCircleStyle: React.CSSProperties = {
  width: 56,
  height: 56,
  borderRadius: '50%',
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center' };

const summaryGridStyle: React.CSSProperties = {
  display: 'grid',
  gap: 12,
  marginTop: 24,
  padding: 16,
  background: '#f9fafb',
  borderRadius: 12 };

const summaryItemStyle: React.CSSProperties = {
  textAlign: 'center' };

const summaryLabelStyle: React.CSSProperties = {
  display: 'block',
  fontSize: 12,
  color: '#9ca3af',
  marginBottom: 4 };

const summaryValueStyle: React.CSSProperties = {
  fontSize: 18,
  fontWeight: 700,
  color: '#111827' };

const savingsCardStyle: React.CSSProperties = {
  background: '#ecfdf5',
  border: '1px solid #a7f3d0',
  borderRadius: 12,
  padding: 20,
  marginTop: 24 };

const spinnerPulseStyle: React.CSSProperties = {
  width: 64,
  height: 64,
  borderRadius: '50%',
  background: '#eef2ff',
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  animation: 'pulse 2s ease-in-out infinite' };

const progressStepsStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'center',
  gap: 24,
  marginTop: 32 };
