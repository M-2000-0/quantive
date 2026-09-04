import React from 'react';
import { Globe } from 'lucide-react';

interface ResilienceDimension {
 name: string;
 score: number;
 trend: 'improving' | 'stable' | 'deteriorating';
 factors: string[];
}

const DIMENSIONS: ResilienceDimension[] = [
 { name: 'Fiscal Resilience', score: 72, trend: 'stable', factors: ['Debt sustainability moderate', 'Primary balance near zero', 'Revenue diversification adequate'] },
 { name: 'Economic Resilience', score: 65, trend: 'deteriorating', factors: ['GDP growth slowing', 'Inflation above target', 'Export concentration risk'] },
 { name: 'Political Resilience', score: 58, trend: 'deteriorating', factors: ['Election in 18 months', 'Opposition gaining', 'Policy uncertainty rising'] },
 { name: 'Social Resilience', score: 70, trend: 'stable', factors: ['Unemployment stable', 'Gini coefficient moderate', 'Social safety nets adequate'] },
 { name: 'External Resilience', score: 62, trend: 'deteriorating', factors: ['FX reserves declining', 'External debt rising', 'Geopolitical exposure'] },
 { name: 'Institutional Resilience', score: 78, trend: 'improving', factors: ['Central bank independence', 'Judicial independence', 'Anti-corruption framework'] },
 { name: 'Infrastructure Resilience', score: 55, trend: 'stable', factors: ['Energy security moderate', 'Digital infrastructure growing', 'Transport aging'] },
 { name: 'Climate Resilience', score: 48, trend: 'deteriorating', factors: ['Flood risk increasing', 'Agriculture vulnerable', 'Adaptation funding low'] },
];

const TREND_ICONS: Record<string, string> = { improving: 'TrendingUp', stable: '➡️', deteriorating: 'TrendingDown' };

export default function NationalResilience() {
 const overallScore = Math.round(DIMENSIONS.reduce((sum, d) => sum + d.score, 0) / DIMENSIONS.length);
 const deteriorating = DIMENSIONS.filter(d => d.trend === 'deteriorating').length;

 return (
 <div className="space-y-6 animate-glass-in">
 <div className="flex items-center gap-3">
 <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center">
 <Globe className="w-5 h-5" />
 </div>
 <div>
 <h2 className="text-xl font-bold text-white">National Resilience Score</h2>
 <p className="text-sm text-slate-400">Country score — not just debt, but resilience across 8 dimensions</p>
 </div>
 </div>

 {/* Overall Score */}
 <div className="glass rounded-2xl p-6 text-center">
 <div className="relative w-32 h-32 mx-auto mb-4">
 <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
 <circle cx="50" cy="50" r="45" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="8" />
 <circle cx="50" cy="50" r="45" fill="none" stroke={overallScore >= 70 ? '#10b981' : overallScore >= 50 ? '#eab308' : '#ef4444'} strokeWidth="8" strokeDasharray={`${overallScore * 2.83} 283`} strokeLinecap="round" />
 </svg>
 <div className="absolute inset-0 flex items-center justify-center">
 <span className="text-4xl font-bold text-white">{overallScore}</span>
 </div>
 </div>
 <p className="text-sm text-slate-400">National Resilience Score</p>
 <p className="text-xs text-red-400 mt-1">{deteriorating} dimensions deteriorating</p>
 </div>

 {/* Dimensions */}
 <div className="grid grid-cols-2 gap-4">
 {DIMENSIONS.map((d, i) => (
 <div key={i} className="glass rounded-xl p-4">
 <div className="flex items-center justify-between mb-2">
 <h4 className="text-white text-sm font-medium">{d.name}</h4>
 <div className="flex items-center gap-2">
 <span className="text-sm">{TREND_ICONS[d.trend]}</span>
 <span className={`text-lg font-bold ${d.score >= 65 ? 'text-green-400' : d.score >= 45 ? 'text-yellow-400' : 'text-red-400'}`}>{d.score}</span>
 </div>
 </div>
 <div className="w-full bg-white/5 rounded-full h-2 mb-2">
 <div className={`h-2 rounded-full ${d.score >= 65 ? 'bg-green-400' : d.score >= 45 ? 'bg-yellow-400' : 'bg-red-400'}`} style={{ width: `${d.score}%` }} />
 </div>
 <div className="space-y-1">
 {d.factors.map((f, j) => (
 <p key={j} className="text-xs text-slate-500">• {f}</p>
 ))}
 </div>
 </div>
 ))}
 </div>

 <div className="p-4 bg-blue-500/10 border border-blue-500/20 rounded-xl">
 <p className="text-sm text-blue-300"> <Globe className="w-4 h-4 inline" /> <strong>National Resilience:</strong> Countries don't fail because of money alone. They fail because of energy shortages, demographic collapse, political instability, and supply chain breakdowns. This score captures the full picture.</p>
 </div>
 </div>
 );
}
