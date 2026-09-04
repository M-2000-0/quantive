// ── Portfolio Health Score Component ─────────────────────────────────
// Shows a single-number health summary with dimension breakdown
// (diversification, alignment, risk fit, yield quality, liquidity).

import { useState } from 'react';
import { calculateHealthScore, type RiskProfile, type HealthScore } from '../lib/allocationTarget';

interface PortfolioHealthScoreProps {
  allocations: Array<{ assetClass: string; category: string; targetPct: number; currentPct: number; drift: number }>;
  targetProfile: RiskProfile;
  portfolioMetrics: {
    totalPrincipal: number;
    avgYield: number;
    avgDuration: number;
    riskScore: number;
    unrealizedPnl: number;
    instrumentCount: number;
  };
}

export default function PortfolioHealthScore({
  allocations,
  targetProfile,
  portfolioMetrics }: PortfolioHealthScoreProps) {
  const [expanded, setExpanded] = useState(false);

  const health = calculateHealthScore(allocations as any, targetProfile, portfolioMetrics);

  const gradeColor = (grade: string) => {
    if (grade.startsWith('A')) return 'from-emerald-500 to-green-500';
    if (grade.startsWith('B')) return 'from-blue-500 to-cyan-500';
    if (grade.startsWith('C')) return 'from-amber-500 to-yellow-500';
    return 'from-red-500 to-orange-500';
  };

  const statusIcon = (status: string) => {
    switch (status) {
      case 'excellent': return '🟢';
      case 'good': return '🔵';
      case 'fair': return '🟡';
      default: return '🔴';
    }
  };

  const statusColor = (status: string) => {
    switch (status) {
      case 'excellent': return 'bg-emerald-500';
      case 'good': return 'bg-blue-500';
      case 'fair': return 'bg-amber-500';
      default: return 'bg-red-500';
    }
  };

  return (
    <div className="glass rounded-2xl p-5 animate-glass-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-bold text-slate-900">🏥 Portfolio Health</h3>
          <p className="text-xs text-slate-500 mt-0.5">Overall score based on your {targetProfile} profile</p>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs font-medium text-blue-600 hover:text-blue-700"
        >
          {expanded ? 'Collapse' : 'Details →'}
        </button>
      </div>

      {/* Score Ring */}
      <div className="flex items-center gap-6 mb-4">
        <div className="relative w-24 h-24 flex-shrink-0">
          <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
            {/* Background ring */}
            <circle
              cx="50" cy="50" r="42"
              fill="none" stroke="currentColor" strokeWidth="8"
              className="text-slate-100"
            />
            {/* Score ring */}
            <circle
              cx="50" cy="50" r="42"
              fill="none" strokeWidth="8" strokeLinecap="round"
              stroke="url(#healthGradient)"
              strokeDasharray={`${(health.overall / 100) * 264} 264`}
              className="transition-all duration-1000"
            />
            <defs>
              <linearGradient id="healthGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" className={`${gradeColor(health.grade)} stop-color`} stopColor={health.grade.startsWith('A') ? '#10b981' : health.grade.startsWith('B') ? '#3b82f6' : health.grade.startsWith('C') ? '#f59e0b' : '#ef4444'} />
                <stop offset="100%" className={`${gradeColor(health.grade)} stop-color`} stopColor={health.grade.startsWith('A') ? '#22c55e' : health.grade.startsWith('B') ? '#06b6d4' : health.grade.startsWith('C') ? '#eab308' : '#f97316'} />
              </linearGradient>
            </defs>
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-2xl font-black text-slate-900">{health.overall}</span>
            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded bg-gradient-to-r ${gradeColor(health.grade)} text-white`}>
              {health.grade}
            </span>
          </div>
        </div>

        {/* Dimension Summary */}
        <div className="flex-1 space-y-1.5">
          {health.dimensions.map((dim) => (
            <div key={dim.name} className="flex items-center gap-2">
              <span className="text-[10px]">{statusIcon(dim.status)}</span>
              <span className="text-[11px] text-slate-600 flex-1">{dim.name}</span>
              <div className="w-16 h-1.5 rounded-full bg-slate-100 overflow-hidden">
                <div
                  className={`h-full rounded-full ${statusColor(dim.status)}`}
                  style={{ width: `${dim.score}%` }}
                />
              </div>
              <span className="text-[10px] font-bold text-slate-700 w-6 text-right">{dim.score}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div className="space-y-4 pt-4 border-t border-white/20">
          {/* Dimension Breakdown */}
          <div className="space-y-3">
            {health.dimensions.map((dim) => (
              <div key={dim.name} className="p-3 rounded-xl bg-white/30 border border-white/40">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm">{statusIcon(dim.status)}</span>
                    <span className="text-xs font-bold text-slate-900">{dim.name}</span>
                    <span className="text-[10px] text-slate-400">({dim.weight}% weight)</span>
                  </div>
                  <span className="text-sm font-bold text-slate-900">{dim.score}/100</span>
                </div>
                <p className="text-[11px] text-slate-500 mb-2">{dim.description}</p>
                <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                  <div
                    className={`h-full rounded-full ${statusColor(dim.status)} transition-all`}
                    style={{ width: `${dim.score}%` }}
                  />
                </div>
              </div>
            ))}
          </div>

          {/* Recommendations */}
          {health.recommendations.length > 0 && (
            <div>
              <div className="text-xs font-bold text-slate-500 mb-2">Recommendations</div>
              <div className="space-y-1.5">
                {health.recommendations.map((rec, idx) => (
                  <div key={idx} className="flex items-start gap-2 p-2 rounded-lg bg-blue-50/50 border border-blue-200/50">
                    <span className="text-xs text-blue-500 mt-0.5">•</span>
                    <span className="text-xs text-blue-800">{rec}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
