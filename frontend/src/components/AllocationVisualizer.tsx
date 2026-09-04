// ── Allocation Visualizer Component ─────────────────────────────────
// Shows current vs target allocation side by side with drift
// indicators, allocation bar, and category breakdown.

import { useMemo } from 'react';
import { BarChart3 } from 'lucide-react';
import {
 TARGET_ALLOCATIONS,
 type RiskProfile,
 type AssetAllocation } from '../lib/allocationTarget';

interface AllocationVisualizerProps {
 allocations: AssetAllocation[];
 targetProfile: RiskProfile;
 /** Show as compact widget */
 compact?: boolean;
}

const CATEGORY_COLORS: Record<string, string> = {
 'Government Bonds': '#3b82f6',
 'Corporate Bonds (IG)': '#6366f1',
 'Corporate Bonds': '#6366f1',
 'Dividend Equities': '#10b981',
 'International Equity': '#8b5cf6',
 'International & EM': '#8b5cf6',
 'Small Cap Value': '#ec4899',
 'US Large Cap': '#10b981',
 'US Growth Equities': '#10b981',
 'US Value Equities': '#14b8a6',
 'REITs': '#f59e0b',
 'REITs & Commodities': '#f59e0b',
 'Alternatives': '#f59e0b',
 'Cash & Equivalents': '#64748b',
 'Cash': '#64748b',
 'Bonds': '#6366f1' };

export default function AllocationVisualizer({
 allocations,
 targetProfile,
 compact = false }: AllocationVisualizerProps) {
 const target = TARGET_ALLOCATIONS[targetProfile];
 const totalDrift = allocations.reduce((sum, a) => sum + Math.abs(a.drift), 0);
 const avgDrift = allocations.length > 0 ? totalDrift / allocations.length : 0;

 const getColor = (assetClass: string) =>
 CATEGORY_COLORS[assetClass] || '#94a3b8';

 if (compact) {
 return (
 <div className="glass rounded-xl p-4">
 <div className="flex items-center justify-between mb-3">
 <span className="text-xs font-bold text-slate-900">Allocation Overview</span>
 <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
 avgDrift < 2 ? 'bg-emerald-100 text-emerald-700' :
 avgDrift < 5 ? 'bg-amber-100 text-amber-700' :
 'bg-red-100 text-red-700'
 }`}>
 {avgDrift < 2 ? 'ON TARGET' : avgDrift < 5 ? 'MINOR DRIFT' : 'NEEDS REBALANCE'}
 </span>
 </div>

 {/* Stacked Bar */}
 <div className="flex h-6 rounded-lg overflow-hidden mb-2">
 {allocations.map((alloc) => (
 <div
 key={alloc.assetClass}
 className="relative group"
 style={{
 width: `${alloc.currentPct}%`,
 backgroundColor: getColor(alloc.assetClass) }}
 >
 {/* Target marker */}
 <div
 className="absolute top-0 bottom-0 w-0.5 bg-white/80"
 style={{ left: `${(alloc.targetPct / alloc.currentPct) * 100}%` }}
 />
 </div>
 ))}
 </div>

 {/* Legend */}
 <div className="flex flex-wrap gap-x-3 gap-y-1">
 {allocations.filter((a) => a.currentPct >= 3).map((alloc) => (
 <div key={alloc.assetClass} className="flex items-center gap-1">
 <div className="w-2 h-2 rounded-sm" style={{ backgroundColor: getColor(alloc.assetClass) }} />
 <span className="text-[10px] text-slate-600">
 {alloc.assetClass} {alloc.currentPct.toFixed(0)}%
 </span>
 </div>
 ))}
 </div>
 </div>
 );
 }

 return (
 <div className="glass rounded-2xl p-6 animate-glass-in">
 {/* Header */}
 <div className="flex items-center justify-between mb-4">
 <div>
 <h3 className="text-sm font-bold text-slate-900"> <BarChart3 className="w-4 h-4 inline" /> Allocation Analysis</h3>
 <p className="text-xs text-slate-500 mt-0.5">
 {target.label} profile — Current vs Target allocation
 </p>
 </div>
 <div className="flex items-center gap-2">
 <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
 avgDrift < 2 ? 'bg-emerald-100 text-emerald-700' :
 avgDrift < 5 ? 'bg-amber-100 text-amber-700' :
 'bg-red-100 text-red-700'
 }`}>
 Avg Drift: {avgDrift.toFixed(1)}%
 </span>
 </div>
 </div>

 {/* Allocation Comparison Bars */}
 <div className="space-y-4 mb-6">
 {/* Current Allocation */}
 <div>
 <div className="flex items-center justify-between mb-1.5">
 <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Current</span>
 </div>
 <div className="flex h-8 rounded-xl overflow-hidden">
 {allocations.map((alloc) => (
 <div
 key={alloc.assetClass}
 className="flex items-center justify-center text-[9px] font-bold text-white/90 transition-all"
 style={{
 width: `${alloc.currentPct}%`,
 backgroundColor: getColor(alloc.assetClass) }}
 title={`${alloc.assetClass}: ${alloc.currentPct.toFixed(1)}%`}
 >
 {alloc.currentPct >= 8 ? `${alloc.currentPct.toFixed(0)}%` : ''}
 </div>
 ))}
 </div>
 </div>

 {/* Target Allocation */}
 <div>
 <div className="flex items-center justify-between mb-1.5">
 <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Target ({target.label})</span>
 </div>
 <div className="flex h-8 rounded-xl overflow-hidden">
 {target.buckets.map((bucket) => (
 <div
 key={bucket.assetClass}
 className="flex items-center justify-center text-[9px] font-bold text-white/90 transition-all"
 style={{
 width: `${bucket.targetPct}%`,
 backgroundColor: getColor(bucket.assetClass) }}
 title={`${bucket.assetClass}: ${bucket.targetPct}%`}
 >
 {bucket.targetPct >= 8 ? `${bucket.targetPct}%` : ''}
 </div>
 ))}
 </div>
 </div>
 </div>

 {/* Detailed Comparison Table */}
 <div className="space-y-2">
 {allocations.map((alloc) => {
 const driftColor = Math.abs(alloc.drift) < 2 ? 'text-emerald-600' :
 Math.abs(alloc.drift) < 5 ? 'text-amber-600' :
 'text-red-600';

 return (
 <div key={alloc.assetClass} className="flex items-center gap-3 p-2 rounded-xl bg-white/30 border border-white/40">
 <div
 className="w-3 h-3 rounded-sm flex-shrink-0"
 style={{ backgroundColor: getColor(alloc.assetClass) }}
 />
 <div className="flex-1 min-w-0">
 <div className="text-xs font-medium text-slate-900">{alloc.assetClass}</div>
 <div className="text-[10px] text-slate-500 capitalize">{alloc.category.replace('_', ' ')}</div>
 </div>
 <div className="flex items-center gap-4">
 <div className="text-right w-12">
 <div className="text-xs font-bold text-slate-900">{alloc.currentPct.toFixed(1)}%</div>
 <div className="text-[9px] text-slate-400">current</div>
 </div>
 <div className="text-center w-8">
 <div className={`text-xs font-bold ${driftColor}`}>
 {alloc.drift > 0 ? '+' : ''}{alloc.drift.toFixed(1)}
 </div>
 <div className="text-[9px] text-slate-400">drift</div>
 </div>
 <div className="text-right w-12">
 <div className="text-xs font-bold text-slate-600">{alloc.targetPct.toFixed(1)}%</div>
 <div className="text-[9px] text-slate-400">target</div>
 </div>
 </div>
 </div>
 );
 })}
 </div>

 {/* Legend */}
 <div className="flex flex-wrap gap-x-4 gap-y-1.5 mt-4 pt-3 border-t border-white/20">
 {target.buckets.map((bucket) => (
 <div key={bucket.assetClass} className="flex items-center gap-1.5">
 <div className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: getColor(bucket.assetClass) }} />
 <span className="text-[10px] text-slate-600">{bucket.assetClass}</span>
 </div>
 ))}
 </div>
 </div>
 );
}
