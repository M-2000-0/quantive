// ── Weekly Consensus Trend Component ───────────────────────────────────
// Shows how consensus indicators have shifted over the past 12 weeks
// with sparklines, trend arrows, and week-over-week changes.

import { useMemo, useState } from 'react';
import { getCategoryIcon } from '../lib/peerIntelligence';
import { TrendingUp } from 'lucide-react';

interface WeeklyTrend {
 id: string;
 category: string;
 title: string;
 weeklyData: number[]; // 12 weeks of consensus percentages
 current: number;
 twelveWeekAgo: number;
 trend: 'up' | 'down' | 'flat';
 weeklyChanges: number[]; // week-over-week deltas
}

const MOCK_WEEKLY_TRENDS: WeeklyTrend[] = [
 {
 id: 'trend-001',
 category: 'duration',
 title: 'Extending Duration',
 weeklyData: [52, 54, 56, 58, 60, 62, 64, 66, 68, 70, 72, 73],
 current: 73,
 twelveWeekAgo: 52,
 trend: 'up',
 weeklyChanges: [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1] },
 {
 id: 'trend-002',
 category: 'hedging',
 title: 'Adding FX Hedges',
 weeklyData: [48, 49, 50, 51, 52, 53, 55, 56, 57, 58, 60, 61],
 current: 61,
 twelveWeekAgo: 48,
 trend: 'up',
 weeklyChanges: [1, 1, 1, 1, 1, 2, 1, 1, 1, 2, 1] },
 {
 id: 'trend-003',
 category: 'allocation',
 title: 'Green Bond Allocation',
 weeklyData: [30, 31, 32, 33, 34, 36, 37, 38, 40, 41, 43, 45],
 current: 45,
 twelveWeekAgo: 30,
 trend: 'up',
 weeklyChanges: [1, 1, 1, 1, 2, 1, 1, 2, 1, 2, 2] },
 {
 id: 'trend-004',
 category: 'credit',
 title: 'Reducing HY Exposure',
 weeklyData: [40, 42, 43, 45, 46, 48, 50, 52, 53, 55, 57, 58],
 current: 58,
 twelveWeekAgo: 40,
 trend: 'up',
 weeklyChanges: [2, 1, 2, 1, 2, 2, 2, 1, 2, 2, 1] },
 {
 id: 'trend-005',
 category: 'refinancing',
 title: 'Front-Loading Refinancing',
 weeklyData: [40, 41, 41, 42, 42, 42, 43, 42, 42, 43, 42, 42],
 current: 42,
 twelveWeekAgo: 40,
 trend: 'flat',
 weeklyChanges: [1, 0, 1, 0, 0, 1, -1, 0, 1, -1, 0] },
 {
 id: 'trend-006',
 category: 'risk',
 title: 'Increasing Cash Reserves',
 weeklyData: [28, 29, 30, 31, 32, 33, 34, 35, 35, 36, 37, 38],
 current: 38,
 twelveWeekAgo: 28,
 trend: 'up',
 weeklyChanges: [1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1] },
];

function Sparkline({ data, color = '#3b82f6', height = 32 }: { data: number[]; color?: string; height?: number }) {
 const min = Math.min(...data);
 const max = Math.max(...data);
 const range = max - min || 1;

 const points = data.map((v, i) => {
 const x = (i / (data.length - 1)) * 100;
 const y = height - ((v - min) / range) * (height - 4) - 2;
 return `${x},${y}`;
 }).join(' ');

 return (
 <svg width="100%" height={height} viewBox={`0 0 100 ${height}`} preserveAspectRatio="none">
 {/* Gradient fill */}
 <defs>
 <linearGradient id={`grad-${color.replace('#', '')}`} x1="0%" y1="0%" x2="0%" y2="100%">
 <stop offset="0%" stopColor={color} stopOpacity="0.3" />
 <stop offset="100%" stopColor={color} stopOpacity="0.05" />
 </linearGradient>
 </defs>
 <polygon
 points={`0,${height} ${points} 100,${height}`}
 fill={`url(#grad-${color.replace('#', '')})`}
 />
 <polyline
 points={points}
 fill="none"
 stroke={color}
 strokeWidth="2"
 strokeLinecap="round"
 strokeLinejoin="round"
 />
 {/* Current value dot */}
 <circle
 cx="100"
 cy={height - ((data[data.length - 1] - min) / range) * (height - 4) - 2}
 r="3"
 fill={color}
 stroke="white"
 strokeWidth="1.5"
 />
 </svg>
 );
}

export default function WeeklyConsensusTrend() {
 const [selectedTrend, setSelectedTrend] = useState<string | null>(null);

 const overallTrend = useMemo(() => {
 const avgChange = [].reduce((sum, t) => sum + (t.current - t.twelveWeekAgo), 0) / 0;
 return avgChange;
 }, []);

 return (
 <div className="space-y-4 animate-glass-in">
 {/* Header */}
 <div className="flex items-center justify-between">
 <div>
 <h2 className="text-2xl font-bold tracking-tight text-slate-900">Weekly Consensus Trends</h2>
 <p className="text-sm text-slate-600 mt-1">12-week trajectory of peer consensus indicators</p>
 </div>
 <div className="glass px-3 py-1.5 rounded-xl text-xs font-medium text-slate-600">
 📅 Last 12 weeks • Updated weekly
 </div>
 </div>

 {/* Overall Summary */}
 <div className="glass rounded-2xl p-4 flex items-center gap-4">
 <div className="text-3xl"> <TrendingUp className="w-4 h-4 inline" /> </div>
 <div>
 <div className="text-sm font-semibold text-slate-900">
 Consensus momentum: <span className="text-emerald-600">+{overallTrend.toFixed(0)}% average</span> over 12 weeks
 </div>
 <div className="text-xs text-slate-500 mt-0.5">
 {[].filter((t) => t.trend === 'up').length} of {0} indicators trending up
 </div>
 </div>
 </div>

 {/* Trend Cards */}
 <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
 {[].map((trend) => {
 const totalChange = trend.current - trend.twelveWeekAgo;
 const isSelected = selectedTrend === trend.id;
 const trendColor = trend.trend === 'up' ? '#10b981' : trend.trend === 'down' ? '#ef4444' : '#6b7280';

 return (
 <div
 key={trend.id}
 className={`glass rounded-2xl p-4 cursor-pointer transition-all ${
 isSelected ? 'ring-2 ring-blue-400 shadow-lg' : 'hover:shadow-md'
 }`}
 onClick={() => setSelectedTrend(isSelected ? null : trend.id)}
 >
 {/* Title Row */}
 <div className="flex items-center justify-between mb-3">
 <div className="flex items-center gap-2">
 <span className="text-lg">{getCategoryIcon(trend.category as 'duration' | 'allocation' | 'hedging' | 'credit' | 'refinancing' | 'risk')}</span>
 <div>
 <h3 className="text-sm font-semibold text-slate-900">{trend.title}</h3>
 <span className="text-[10px] text-slate-500 capitalize">{trend.category}</span>
 </div>
 </div>
 <div className="text-right">
 <div className="text-xl font-bold text-slate-900">{trend.current}%</div>
 <div className={`text-[10px] font-bold ${totalChange > 0 ? 'text-emerald-600' : totalChange < 0 ? 'text-red-600' : 'text-slate-500'}`}>
 {totalChange > 0 ? '+' : ''}{totalChange}% (12wk)
 </div>
 </div>
 </div>

 {/* Sparkline */}
 <div className="mb-2">
 <Sparkline data={trend.weeklyData} color={trendColor} height={40} />
 </div>

 {/* Week labels */}
 <div className="flex justify-between text-[9px] text-slate-400 mb-2">
 <span>12wk ago</span>
 <span>Current</span>
 </div>

 {/* Trend Arrow */}
 <div className="flex items-center justify-between">
 <div className="flex items-center gap-1">
 <span className={`text-lg ${
 trend.trend === 'up' ? 'text-emerald-500' :
 trend.trend === 'down' ? 'text-red-500' :
 'text-slate-400'
 }`}>
 {trend.trend === 'up' ? '↗️' : trend.trend === 'down' ? '↘️' : '→'}
 </span>
 <span className={`text-xs font-bold ${
 trend.trend === 'up' ? 'text-emerald-600' :
 trend.trend === 'down' ? 'text-red-600' :
 'text-slate-500'
 }`}>
 {trend.trend === 'up' ? 'Increasing' : trend.trend === 'down' ? 'Decreasing' : 'Stable'}
 </span>
 </div>
 <span className="text-[10px] text-slate-400">
 {trend.twelveWeekAgo}% → {trend.current}%
 </span>
 </div>

 {/* Expanded: Weekly Changes */}
 {isSelected && (
 <div className="mt-3 pt-3 border-t border-white/20 animate-glass-in">
 <h4 className="text-[10px] font-bold text-slate-700 uppercase tracking-widest mb-2">Weekly Changes</h4>
 <div className="flex gap-1">
 {trend.weeklyChanges.map((change, i) => (
 <div
 key={i}
 className={`flex-1 h-6 rounded text-[9px] font-bold flex items-center justify-center ${
 change > 0 ? 'bg-emerald-100 text-emerald-700' :
 change < 0 ? 'bg-red-100 text-red-700' :
 'bg-slate-100 text-slate-500'
 }`}
 >
 {change > 0 ? '+' : ''}{change}%
 </div>
 ))}
 </div>
 <div className="flex justify-between text-[8px] text-slate-400 mt-1">
 <span>W1</span>
 <span>W6</span>
 <span>W12</span>
 </div>
 </div>
 )}
 </div>
 );
 })}
 </div>
 </div>
 );
}
