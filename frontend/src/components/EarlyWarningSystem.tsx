import React, { useState } from 'react';
import { ChartColumn as BarChart3 } from 'lucide-react';

interface WarningSignal {
 id: string;
 name: string;
 category: 'debt_crisis' | 'liquidity' | 'maturity' | 'fx_stress' | 'rating' | 'contagion';
 indicator: string;
 currentValue: number;
 threshold: number;
 unit: string;
 direction: 'above_danger' | 'below_danger';
 status: 'normal' | 'watch' | 'warning' | 'critical';
 trend: 'improving' | 'stable' | 'deteriorating';
 description: string;
 lastUpdated: string;
}

const SIGNALS: WarningSignal[] = [
 { id: 'ws1', name: 'Debt-to-GDP Ratio', category: 'debt_crisis', indicator: 'Total Debt / GDP', currentValue: 68.2, threshold: 75, unit: '%', direction: 'above_danger', status: 'watch', trend: 'deteriorating', description: 'Approaching IMF warning threshold of 75%. Requires fiscal consolidation.', lastUpdated: '2026-08-24' },
 { id: 'ws2', name: 'Liquidity Coverage Ratio', category: 'liquidity', indicator: 'Liquid Assets / Short-term Debt', currentValue: 12.3, threshold: 15, unit: '%', direction: 'below_danger', status: 'warning', trend: 'deteriorating', description: 'Below minimum 15% threshold. Emergency funding may be required.', lastUpdated: '2026-08-24' },
 { id: 'ws3', name: 'Maturity Wall (12-month)', category: 'maturity', indicator: 'Debt Maturing / Total Debt', currentValue: 22.5, threshold: 20, unit: '%', direction: 'above_danger', status: 'warning', trend: 'stable', description: '$3.2B maturing in next 12 months. Refinancing risk elevated.', lastUpdated: '2026-08-24' },
 { id: 'ws4', name: 'FX Reserve Coverage', category: 'fx_stress', indicator: 'Reserves / Short-term External Debt', currentValue: 1.2, threshold: 1.5, unit: 'x', direction: 'below_danger', status: 'warning', trend: 'deteriorating', description: 'Reserves declining. Only 1.2x coverage of short-term external obligations.', lastUpdated: '2026-08-24' },
 { id: 'ws5', name: 'Credit Default Swap Spread', category: 'rating', indicator: '5Y Sovereign CDS', currentValue: 285, threshold: 350, unit: 'bps', direction: 'above_danger', status: 'watch', trend: 'deteriorating', description: 'Spread elevated but below danger zone. Monitor for further widening.', lastUpdated: '2026-08-24' },
 { id: 'ws6', name: 'Regional Contagion Index', category: 'contagion', indicator: 'Correlation with distressed peers', currentValue: 0.42, threshold: 0.6, unit: '', direction: 'above_danger', status: 'normal', trend: 'stable', description: 'Moderate correlation with regional sovereigns. No immediate contagion risk.', lastUpdated: '2026-08-24' },
 { id: 'ws7', name: 'Debt Service Ratio', category: 'debt_crisis', indicator: 'Interest + Principal / Revenue', currentValue: 22.1, threshold: 25, unit: '%', direction: 'above_danger', status: 'watch', trend: 'stable', description: 'Approaching 25% ceiling. Fiscal space narrowing.', lastUpdated: '2026-08-24' },
 { id: 'ws8', name: 'External Financing Needs', category: 'liquidity', indicator: 'Gross Financing / GDP', currentValue: 18.5, threshold: 20, unit: '%', direction: 'above_danger', status: 'watch', trend: 'deteriorating', description: 'Near 20% threshold. Market access conditions critical.', lastUpdated: '2026-08-24' },
];

const CATEGORY_INFO: Record<string, { icon: string; color: string }> = {
 debt_crisis: { icon: 'BarChart3', color: 'red' },
 liquidity: { icon: '💧', color: 'blue' },
 maturity: { icon: 'Clock', color: 'amber' },
 fx_stress: { icon: '💱', color: 'purple' },
 rating: { icon: '⭐', color: 'orange' },
 contagion: { icon: '🔗', color: 'cyan' } };

const STATUS_COLORS: Record<string, string> = {
 normal: 'bg-green-500/20 text-green-400',
 watch: 'bg-yellow-500/20 text-yellow-400',
 warning: 'bg-orange-500/20 text-orange-400',
 critical: 'bg-red-500/20 text-red-400' };

const TREND_ICONS: Record<string, string> = {
 improving: 'TrendingUp',
 stable: '➡️',
 deteriorating: 'TrendingDown' };

export default function EarlyWarningSystem() {
 const [signals, setSignals] = useState(SIGNALS);
 const [selectedCategory, setSelectedCategory] = useState<string>('all');
 const [selectedSignal, setSelectedSignal] = useState<WarningSignal | null>(null);

 const filteredSignals = selectedCategory === 'all' ? signals : signals.filter(s => s.category === selectedCategory);
 const criticalCount = signals.filter(s => s.status === 'critical').length;
 const warningCount = signals.filter(s => s.status === 'warning').length;
 const watchCount = signals.filter(s => s.status === 'watch').length;

 return (
 <div className="space-y-6 animate-glass-in">
 <div className="flex items-center justify-between">
 <div className="flex items-center gap-3">
 <div className="w-10 h-10 bg-gradient-to-br from-amber-500 to-orange-600 rounded-xl flex items-center justify-center">
 <span className="text-lg">🚨</span>
 </div>
 <div>
 <h2 className="text-xl font-bold text-white">Early Warning System</h2>
 <p className="text-sm text-slate-400">Predictive alerts before debt crises, liquidity shortages, and rating downgrades</p>
 </div>
 </div>
 <div className="flex gap-3">
 <div className="glass px-3 py-2 rounded-xl text-center">
 <p className="text-xl font-bold text-red-400">{criticalCount}</p>
 <p className="text-xs text-slate-400">Critical</p>
 </div>
 <div className="glass px-3 py-2 rounded-xl text-center">
 <p className="text-xl font-bold text-orange-400">{warningCount}</p>
 <p className="text-xs text-slate-400">Warning</p>
 </div>
 <div className="glass px-3 py-2 rounded-xl text-center">
 <p className="text-xl font-bold text-yellow-400">{watchCount}</p>
 <p className="text-xs text-slate-400">Watch</p>
 </div>
 </div>
 </div>

 {/* Category Filters */}
 <div className="flex gap-2 flex-wrap">
 <button
 onClick={() => setSelectedCategory('all')}
 className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
 selectedCategory === 'all' ? 'bg-white/20 text-white' : 'bg-white/5 text-slate-400 hover:bg-white/10'
 }`}
 >
 All ({signals.length})
 </button>
 {Object.entries(CATEGORY_INFO).map(([key, info]) => (
 <button
 key={key}
 onClick={() => setSelectedCategory(key)}
 className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
 selectedCategory === key ? 'bg-white/20 text-white' : 'bg-white/5 text-slate-400 hover:bg-white/10'
 }`}
 >
 {info.icon} {key.replace(/_/g, ' ')} ({signals.filter(s => s.category === key).length})
 </button>
 ))}
 </div>

 {/* Signal Grid */}
 <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
 {filteredSignals.map(signal => {
 const isDanger = signal.direction === 'above_danger'
 ? signal.currentValue >= signal.threshold
 : signal.currentValue <= signal.threshold;
 const proximity = signal.direction === 'above_danger'
 ? Math.min((signal.currentValue / signal.threshold) * 100, 150)
 : Math.min((signal.threshold / signal.currentValue) * 100, 150);

 return (
 <button
 key={signal.id}
 onClick={() => setSelectedSignal(signal)}
 className={`text-left glass rounded-xl p-4 transition-all ${
 selectedSignal?.id === signal.id ? 'ring-2 ring-amber-500/50' : 'hover:bg-white/5'
 } ${isDanger ? 'border-l-4 border-red-500' : ''}`}
 >
 <div className="flex items-start justify-between mb-3">
 <div className="flex items-center gap-2">
 <span className="text-lg">{CATEGORY_INFO[signal.category]?.icon}</span>
 <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[signal.status]}`}>
 {signal.status.toUpperCase()}
 </span>
 <span className="text-xs">{TREND_ICONS[signal.trend]}</span>
 </div>
 </div>

 <h4 className="text-white font-medium mb-1">{signal.name}</h4>
 <p className="text-xs text-slate-400 mb-3">{signal.indicator}</p>

 {/* Value vs Threshold */}
 <div className="flex items-center justify-between mb-2">
 <div className="text-left">
 <p className={`text-2xl font-bold ${isDanger ? 'text-red-400' : 'text-white'}`}>
 {signal.currentValue}{signal.unit}
 </p>
 <p className="text-xs text-slate-500">Current</p>
 </div>
 <div className="text-right">
 <p className="text-lg text-slate-400">{signal.threshold}{signal.unit}</p>
 <p className="text-xs text-slate-500">Threshold</p>
 </div>
 </div>

 {/* Proximity Bar */}
 <div className="w-full bg-white/5 rounded-full h-2 mb-2">
 <div
 className={`h-2 rounded-full transition-all ${
 proximity >= 100 ? 'bg-red-400' :
 proximity >= 80 ? 'bg-orange-400' :
 proximity >= 60 ? 'bg-yellow-400' : 'bg-green-400'
 }`}
 style={{ width: `${Math.min(proximity, 100)}%` }}
 />
 </div>

 <p className="text-xs text-slate-400 truncate">{signal.description}</p>
 </button>
 );
 })}
 </div>

 {/* Detail Panel */}
 {selectedSignal && (
 <div className="glass rounded-2xl p-6 space-y-4">
 <div className="flex items-center justify-between">
 <h3 className="text-lg font-bold text-white">{selectedSignal.name}</h3>
 <div className="flex items-center gap-2">
 <span className={`px-3 py-1 rounded-lg text-xs font-medium ${STATUS_COLORS[selectedSignal.status]}`}>
 {selectedSignal.status.toUpperCase()}
 </span>
 <span className="text-sm">{TREND_ICONS[selectedSignal.trend]} {selectedSignal.trend}</span>
 </div>
 </div>

 <p className="text-sm text-slate-300">{selectedSignal.description}</p>

 <div className="grid grid-cols-4 gap-4 text-center">
 <div className="bg-white/5 rounded-xl p-3">
 <p className="text-2xl font-bold text-white">{selectedSignal.currentValue}{selectedSignal.unit}</p>
 <p className="text-xs text-slate-500">Current</p>
 </div>
 <div className="bg-white/5 rounded-xl p-3">
 <p className="text-2xl font-bold text-slate-400">{selectedSignal.threshold}{selectedSignal.unit}</p>
 <p className="text-xs text-slate-500">Threshold</p>
 </div>
 <div className="bg-white/5 rounded-xl p-3">
 <p className="text-2xl font-bold text-white">{selectedSignal.trend}</p>
 <p className="text-xs text-slate-500">Trend</p>
 </div>
 <div className="bg-white/5 rounded-xl p-3">
 <p className="text-sm font-bold text-white">{selectedSignal.lastUpdated}</p>
 <p className="text-xs text-slate-500">Last Updated</p>
 </div>
 </div>

 <div className="flex gap-3">
 <button className="flex-1 py-3 bg-amber-500/20 border border-amber-500/30 rounded-xl text-amber-400 font-medium hover:bg-amber-500/30 transition-colors">
 <BarChart3 className="w-4 h-4 inline" /> View Historical Trend
 </button>
 <button className="flex-1 py-3 bg-white/5 border border-white/10 rounded-xl text-slate-400 hover:bg-white/10 transition-colors">
 📧 Set Alert Threshold
 </button>
 </div>
 </div>
 )}
 </div>
 );
}
