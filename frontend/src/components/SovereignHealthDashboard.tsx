import React from 'react';
import { TriangleAlert as AlertTriangle } from 'lucide-react';

interface HealthMetric {
  name: string;
  score: number;
  trend: 'improving' | 'stable' | 'deteriorating';
  description: string;
  color: string;
}

const METRICS: HealthMetric[] = [
  { name: 'Debt Sustainability', score: 68, trend: 'stable', description: 'Moderate risk. Trajectory requires monitoring.', color: 'emerald' },
  { name: 'Liquidity', score: 55, trend: 'deteriorating', description: 'Below target. Buffer needs replenishment.', color: 'blue' },
  { name: 'Refinancing Risk', score: 62, trend: 'improving', description: 'Improving with proposed maturity extension.', color: 'purple' },
  { name: 'FX Risk', score: 48, trend: 'deteriorating', description: 'Elevated exposure. Hedging recommended.', color: 'amber' },
  { name: 'Market Access', score: 75, trend: 'stable', description: 'Good market access. Spreads manageable.', color: 'cyan' },
  { name: 'Fiscal Flexibility', score: 58, trend: 'deteriorating', description: 'Limited fiscal space for countercyclical policy.', color: 'rose' },
];

const TREND_ICONS: Record<string, string> = {
  improving: 'TrendingUp',
  stable: '➡️',
  deteriorating: 'TrendingDown' };

export default function SovereignHealthDashboard() {
  const overallScore = Math.round(METRICS.reduce((sum, m) => sum + m.score, 0) / METRICS.length);
  const deteriorating = METRICS.filter(m => m.trend === 'deteriorating').length;

  return (
    <div className="space-y-6 animate-glass-in">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-blue-600 rounded-xl flex items-center justify-center">
            <span className="text-lg">🏥</span>
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Sovereign Health Dashboard</h2>
            <p className="text-sm text-slate-400">Country credit score — debt sustainability, liquidity, and risk assessment</p>
          </div>
        </div>
        <div className="glass px-6 py-4 rounded-2xl text-center">
          <div className="relative w-20 h-20 mx-auto">
            <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
              <circle cx="50" cy="50" r="45" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="8" />
              <circle
                cx="50" cy="50" r="45" fill="none"
                stroke={overallScore >= 70 ? '#10b981' : overallScore >= 50 ? '#eab308' : '#ef4444'}
                strokeWidth="8"
                strokeDasharray={`${overallScore * 2.83} 283`}
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-2xl font-bold text-white">{overallScore}</span>
            </div>
          </div>
          <p className="text-xs text-slate-400 mt-2">Overall Score</p>
        </div>
      </div>

      {/* Deteriorating Alert */}
      {deteriorating > 0 && (
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-2xl p-4 flex items-center gap-3">
          <AlertTriangle className="w-5 h-5" />
          <div>
            <p className="text-sm text-amber-300 font-medium">
              {deteriorating} metric{deteriorating > 1 ? 's' : ''} deteriorating
            </p>
            <p className="text-xs text-amber-400/70">Monitor closely and consider corrective action</p>
          </div>
        </div>
      )}

      {/* Health Metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        {METRICS.map((metric, i) => (
          <div key={i} className="glass rounded-2xl p-5">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-white font-medium">{metric.name}</h4>
              <span className="text-sm">{TREND_ICONS[metric.trend]}</span>
            </div>
            <div className="relative w-16 h-16 mx-auto mb-3">
              <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
                <circle cx="50" cy="50" r="42" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="6" />
                <circle
                  cx="50" cy="50" r="42" fill="none"
                  stroke={metric.score >= 65 ? '#10b981' : metric.score >= 45 ? '#eab308' : '#ef4444'}
                  strokeWidth="6"
                  strokeDasharray={`${metric.score * 2.64} 264`}
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className={`text-lg font-bold ${
                  metric.score >= 65 ? 'text-green-400' :
                  metric.score >= 45 ? 'text-yellow-400' : 'text-red-400'
                }`}>
                  {metric.score}
                </span>
              </div>
            </div>
            <p className="text-xs text-slate-400 text-center">{metric.description}</p>
          </div>
        ))}
      </div>

      {/* Summary */}
      <div className="glass rounded-2xl p-6">
        <h3 className="text-sm font-medium text-slate-400 mb-3">HEALTH SUMMARY</h3>
        <div className="grid grid-cols-4 gap-4 text-center">
          <div>
            <p className="text-2xl font-bold text-white">{overallScore}</p>
            <p className="text-xs text-slate-500">Overall</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-green-400">{METRICS.filter(m => m.trend === 'improving').length}</p>
            <p className="text-xs text-slate-500">Improving</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-yellow-400">{METRICS.filter(m => m.trend === 'stable').length}</p>
            <p className="text-xs text-slate-500">Stable</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-red-400">{deteriorating}</p>
            <p className="text-xs text-slate-500">Deteriorating</p>
          </div>
        </div>
      </div>
    </div>
  );
}
