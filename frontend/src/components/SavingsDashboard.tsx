import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowUpRight,
  DollarSign,
  Loader2,
  Target,
  TrendingUp,
  Zap } from 'lucide-react';
import { api } from '../api';

// ── Types ──────────────────────────────────────────────────────────

interface SavingsSummary {
  total_estimated_annual_savings: number;
  total_baseline_annual_cost: number;
  savings_percentage: number;
  total_optimizations_completed: number;
  total_portfolios: number;
  total_instruments: number;
  best_optimization: {
    name: string;
    savings_percentage: number;
  };
  roi: {
    annual_savings: number;
    annual_cost: number;
    roi_percentage: number;
    payback_months: number | null;
  };
  by_portfolio: Array<{
    portfolio_name: string;
    baseline_annual_cost: number;
    estimated_annual_savings: number;
    savings_percentage: number;
    optimization_count: number;
  }>;
  generated_at: string;
}

interface Milestone {
  title: string;
  description: string;
  target: number;
  current: number;
  achieved: boolean;
  icon: string;
}

interface MilestonesResponse {
  milestones: Milestone[];
  achieved_count: number;
  total_milestones: number;
  total_estimated_savings: number;
}

// ── Helpers ─────────────────────────────────────────────────────────

function formatCurrency(value: number): string {
  if (value >= 1e12) return `$${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `$${(value / 1e3).toFixed(1)}K`;
  return `$${value.toFixed(0)}`;
}

function getProgressWidth(current: number, target: number): number {
  if (target <= 0) return 0;
  return Math.min(100, (current / target) * 100);
}

// ── Component ───────────────────────────────────────────────────────

export default function SavingsDashboard() {
  const [summary, setSummary] = useState<SavingsSummary | null>(null);
  const [milestones, setMilestones] = useState<MilestonesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryData, milestonesData] = await Promise.all([
        api.savings.summary() as unknown as Promise<SavingsSummary>,
        api.savings.milestones() as unknown as Promise<MilestonesResponse>,
      ]);
      setSummary(summaryData);
      setMilestones(milestonesData);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return (
      <div style={containerStyle}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 60 }}>
          <Loader2 size={24} style={{ animation: 'spin 1s linear infinite', color: '#6366f1' }} />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={containerStyle}>
        <div style={{ textAlign: 'center', padding: 40, color: '#dc2626' }}>{error}</div>
        <div style={{ textAlign: 'center', paddingBottom: 24 }}>
          <button
            type="button"
            onClick={() => void load()}
            style={{ padding: '8px 20px', borderRadius: 8, border: '1px solid #e5e7eb', background: '#fff', cursor: 'pointer', fontWeight: 500 }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const s = summary;
  const roi = s?.roi;

  return (
    <div className="savings-dashboard" style={containerStyle}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 22, fontWeight: 700, color: '#111827', display: 'flex', alignItems: 'center', gap: 8 }}>
          <DollarSign size={24} color="#10b981" />
          Savings Tracker
        </h2>
        <p style={{ color: '#6b7280', fontSize: 14, marginTop: 4 }}>
          Track your cumulative savings from debt optimization
        </p>
      </div>

      {/* Hero Stats */}
      <div className="qa-grid-3" style={{ display: 'grid', gap: 16, marginBottom: 24 }}>
        {/* Annual Savings */}
        <div style={{ ...statCardStyle, background: 'linear-gradient(135deg, #ecfdf5, #d1fae5)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <div style={{ width: 32, height: 32, borderRadius: 8, background: '#10b981', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <TrendingUp size={16} color="#fff" />
            </div>
            <span style={{ fontSize: 13, color: '#065f46', fontWeight: 500 }}>Annual Savings</span>
          </div>
          <div style={{ fontSize: 28, fontWeight: 700, color: '#064e3b' }}>
            {s ? formatCurrency(s.total_estimated_annual_savings) : '$0'}
          </div>
          <div style={{ fontSize: 12, color: '#059669', marginTop: 4 }}>
            {s?.savings_percentage.toFixed(1)}% of financing cost
          </div>
        </div>

        {/* ROI */}
        <div style={{ ...statCardStyle, background: 'linear-gradient(135deg, #eef2ff, #e0e7ff)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <div style={{ width: 32, height: 32, borderRadius: 8, background: '#6366f1', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Target size={16} color="#fff" />
            </div>
            <span style={{ fontSize: 13, color: '#3730a3', fontWeight: 500 }}>ROI on Quantive</span>
          </div>
          <div style={{ fontSize: 28, fontWeight: 700, color: '#312e81' }}>
            {roi ? `${roi.roi_percentage.toFixed(0)}x` : '—'}
          </div>
          <div style={{ fontSize: 12, color: '#4f46e5', marginTop: 4 }}>
            {roi?.payback_months
              ? `Payback in ${roi.payback_months} months`
              : 'Run optimizations to calculate ROI'}
          </div>
        </div>

        {/* Optimizations */}
        <div style={{ ...statCardStyle, background: 'linear-gradient(135deg, #eff6ff, #e0e7ff)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <div style={{ width: 32, height: 32, borderRadius: 8, background: '#3b82f6', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Zap size={16} color="#fff" />
            </div>
            <span style={{ fontSize: 13, color: '#1e40af', fontWeight: 500 }}>Optimizations Run</span>
          </div>
          <div style={{ fontSize: 28, fontWeight: 700, color: '#1e3a8a' }}>
            {s?.total_optimizations_completed ?? 0}
          </div>
          <div style={{ fontSize: 12, color: '#2563eb', marginTop: 4 }}>
            Best: {s?.best_optimization.savings_percentage.toFixed(1)}% savings
          </div>
        </div>
      </div>

      {/* Savings Breakdown by Portfolio */}
      {s && s.by_portfolio.length > 0 && (
        <div style={panelStyle}>
          <h3 style={panelTitleStyle}>Savings by Portfolio</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {s.by_portfolio.map((p) => (
              <div key={p.portfolio_name} style={portfolioRowStyle}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, color: '#111827', fontSize: 14 }}>{p.portfolio_name}</div>
                  <div style={{ fontSize: 12, color: '#6b7280', marginTop: 2 }}>
                    {p.optimization_count} optimization{p.optimization_count !== 1 ? 's' : ''} • Baseline: {formatCurrency(p.baseline_annual_cost)}/yr
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontWeight: 700, color: '#059669', fontSize: 16 }}>
                    {formatCurrency(p.estimated_annual_savings)}
                  </div>
                  <div style={{ fontSize: 12, color: '#10b981' }}>/year saved</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Milestones */}
      {milestones && (
        <div style={panelStyle}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={panelTitleStyle}>Milestones</h3>
            <span style={{ fontSize: 13, color: '#6b7280' }}>
              {milestones.achieved_count}/{milestones.total_milestones} achieved
            </span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {milestones.milestones.map((m) => (
              <div
                key={m.title}
                style={{
                  ...milestoneStyle,
                  borderLeftColor: m.achieved ? '#10b981' : '#e5e7eb',
                  background: m.achieved ? '#f0fdf4' : '#fff' }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                  <span style={{ fontSize: 20 }}>{m.icon}</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, color: '#111827', fontSize: 14 }}>{m.title}</div>
                    <div style={{ fontSize: 12, color: '#6b7280' }}>{m.description}</div>
                  </div>
                  {m.achieved && (
                    <span style={achievedBadgeStyle}>Achieved</span>
                  )}
                </div>
                <div style={progressBarBgStyle}>
                  <div
                    style={{
                      ...progressBarFillStyle,
                      width: `${getProgressWidth(m.current, m.target)}%`,
                      background: m.achieved ? '#10b981' : '#6366f1' }}
                  />
                </div>
                <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 4 }}>
                  {m.target >= 1_000_000
                    ? `${formatCurrency(m.current)} / ${formatCurrency(m.target)}`
                    : `${m.current} / ${m.target}`}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div style={{ display: 'flex', gap: 12, marginTop: 24 }}>
        <Link to="/optimizations/new" style={{ ...actionButtonStyle, textDecoration: 'none' }}>
          <Zap size={16} />
          Run New Optimization
        </Link>
        <Link to="/optimizations" style={{ ...secondaryActionStyle, textDecoration: 'none' }}>
          View All Optimizations
          <ArrowUpRight size={14} />
        </Link>
      </div>
    </div>
  );
}

// ── Styles ───────────────────────────────────────────────────────

const containerStyle: React.CSSProperties = {
  padding: 24,
  maxWidth: 960,
  margin: '0 auto' };

const statCardStyle: React.CSSProperties = {
  borderRadius: 12,
  padding: 20,
  border: '1px solid #f3f4f6' };

const panelStyle: React.CSSProperties = {
  background: '#fff',
  borderRadius: 12,
  padding: 20,
  border: '1px solid #e5e7eb',
  marginBottom: 16 };

const panelTitleStyle: React.CSSProperties = {
  fontSize: 16,
  fontWeight: 600,
  color: '#111827',
  marginBottom: 12 };

const portfolioRowStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: 12,
  background: '#f9fafb',
  borderRadius: 8 };

const milestoneStyle: React.CSSProperties = {
  padding: 14,
  borderRadius: 8,
  borderLeft: '3px solid #e5e7eb' };

const achievedBadgeStyle: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 600,
  color: '#059669',
  background: '#d1fae5',
  padding: '2px 8px',
  borderRadius: 99 };

const progressBarBgStyle: React.CSSProperties = {
  height: 6,
  background: '#e5e7eb',
  borderRadius: 3,
  overflow: 'hidden' };

const progressBarFillStyle: React.CSSProperties = {
  height: '100%',
  borderRadius: 3,
  transition: 'width 0.5s ease' };

const actionButtonStyle: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 8,
  padding: '10px 20px',
  borderRadius: 8,
  background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
  color: '#fff',
  fontSize: 14,
  fontWeight: 600,
  cursor: 'pointer' };

const secondaryActionStyle: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 6,
  padding: '10px 20px',
  borderRadius: 8,
  border: '1px solid #e5e7eb',
  background: '#fff',
  color: '#374151',
  fontSize: 14,
  fontWeight: 500,
  cursor: 'pointer' };
