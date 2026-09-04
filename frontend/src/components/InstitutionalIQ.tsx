import { useState } from 'react';
import Card, { CardHeader } from './ui/Card';
import Badge from './ui/Badge';

interface DimensionScore {
  name: string;
  score: number;
  weight: number;
  description: string;
  benchmark: number;
  trend: 'improving' | 'stable' | 'declining';
  recommendations: string[];
}

const DIMENSIONS: DimensionScore[] = [
  {
    name: 'Documentation Quality', score: 78, weight: 20,
    description: 'Completeness and quality of policy documents, procedures, and institutional knowledge.',
    benchmark: 82, trend: 'improving',
    recommendations: ['Standardize decision documentation templates', 'Implement version control for all policy documents'] },
  {
    name: 'Process Quality', score: 65, weight: 25,
    description: 'Efficiency and effectiveness of approval workflows, review cycles, and operational procedures.',
    benchmark: 75, trend: 'stable',
    recommendations: ['Automate routine approvals', 'Reduce approval chain length for low-risk decisions'] },
  {
    name: 'Data Quality', score: 88, weight: 20,
    description: 'Accuracy, timeliness, and completeness of market data and internal portfolio data.',
    benchmark: 90, trend: 'improving',
    recommendations: ['Add real-time data validation', 'Implement cross-source reconciliation'] },
  {
    name: 'Approval Quality', score: 72, weight: 15,
    description: 'Quality of governance, segregation of duties, and decision accountability.',
    benchmark: 80, trend: 'declining',
    recommendations: ['Strengthen four-eyes principle enforcement', 'Add time-bound escalation paths'] },
  {
    name: 'Innovation Adoption', score: 58, weight: 10,
    description: 'Rate of adoption of new tools, methodologies, and analytical frameworks.',
    benchmark: 70, trend: 'stable',
    recommendations: ['Pilot scenario analysis tools', 'Train staff on optimization methodologies'] },
  {
    name: 'Risk Management', score: 82, weight: 10,
    description: 'Quality of risk identification, measurement, and mitigation processes.',
    benchmark: 85, trend: 'improving',
    recommendations: ['Implement stress testing framework', 'Add early warning indicators'] },
];

const TREND_CONFIG: Record<string, { label: string; icon: string; color: string }> = {
  improving: { label: 'Improving', icon: '↗', color: 'text-emerald-600' },
  stable: { label: 'Stable', icon: '→', color: 'text-slate-500' },
  declining: { label: 'Declining', icon: '↘', color: 'text-red-600' } };

export default function InstitutionalIQ() {
  const [expanded, setExpanded] = useState<string | null>(null);
  const overallScore = Math.round(DIMENSIONS.reduce((s, d) => s + d.score * d.weight, 0) / 100);
  const overallBenchmark = Math.round(DIMENSIONS.reduce((s, d) => s + d.benchmark * d.weight, 0) / 100);

  return (
    <div className="space-y-6">
      {/* Overall score */}
      <Card>
        <div className="p-6 text-center">
          <p className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Ministry Maturity Score</p>
          <div className="relative inline-flex items-center justify-center w-32 h-32 mb-4">
            <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
              <circle cx="60" cy="60" r="50" fill="none" stroke="#e2e8f0" strokeWidth="8" />
              <circle cx="60" cy="60" r="50" fill="none" stroke={overallScore >= 80 ? '#10b981' : overallScore >= 60 ? '#f59e0b' : '#ef4444'} strokeWidth="8" strokeDasharray={`${overallScore * 3.14} 314`} strokeLinecap="round" />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-3xl font-bold text-slate-900">{overallScore}</span>
              <span className="text-[10px] text-slate-400">/ 100</span>
            </div>
          </div>
          <p className="text-sm text-slate-500">
            Benchmark average: <span className="font-bold text-slate-700">{overallBenchmark}</span>
            {overallScore >= overallBenchmark
              ? <span className="text-emerald-600 ml-1">(+{overallScore - overallBenchmark} above benchmark)</span>
              : <span className="text-red-600 ml-1">({overallScore - overallBenchmark} below benchmark)</span>
            }
          </p>
        </div>
      </Card>

      {/* Dimension scores */}
      <div className="space-y-3">
        {DIMENSIONS.map((dim) => {
          const trend = TREND_CONFIG[dim.trend];
          return (
            <Card key={dim.name} padding={false}>
              <div
                className="px-6 py-4 cursor-pointer hover:bg-white/30 transition-colors"
                onClick={() => setExpanded(expanded === dim.name ? null : dim.name)}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-bold text-slate-900">{dim.name}</h3>
                      <span className={`text-xs font-bold ${trend.color}`}>{trend.icon} {trend.label}</span>
                    </div>
                    <p className="text-[11px] text-slate-500 mt-0.5">{dim.description}</p>
                  </div>
                  <div className="flex items-center gap-3 ml-4">
                    <div className="text-right">
                      <p className="text-lg font-bold text-slate-900 tabular-nums">{dim.score}</p>
                      <p className="text-[10px] text-slate-400">/ 100</p>
                    </div>
                  </div>
                </div>
                {/* Score bar */}
                <div className="flex items-center gap-3">
                  <div className="flex-1 h-2.5 bg-white/50 backdrop-blur-sm border border-white/40 rounded-full p-0.5">
                    <div
                      className={`h-full rounded-full transition-all ${dim.score >= 80 ? 'bg-gradient-to-r from-emerald-500 to-teal-500' : dim.score >= 60 ? 'bg-gradient-to-r from-amber-500 to-orange-500' : 'bg-gradient-to-r from-red-500 to-rose-500'}`}
                      style={{ width: `${dim.score}%` }}
                    />
                  </div>
                  <span className="text-[10px] text-slate-400 w-20 text-right">
                    Benchmark: {dim.benchmark}
                  </span>
                </div>

                {expanded === dim.name && (
                  <div className="mt-4 pt-4 border-t border-white/40">
                    <p className="text-[10px] font-bold text-slate-400 uppercase mb-2">Recommendations</p>
                    <div className="space-y-1">
                      {dim.recommendations.map((r, i) => (
                        <div key={i} className="flex items-start gap-2 text-xs text-slate-600">
                          <span className="text-blue-500 mt-0.5">→</span>{r}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
