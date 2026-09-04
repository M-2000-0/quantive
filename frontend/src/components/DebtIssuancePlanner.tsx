import React, { useState } from 'react';
import { Upload } from 'lucide-react';

interface IssuanceRecommendation {
 id: string;
 name: string;
 bondType: string;
 maturity: string;
 size: string;
 currency: string;
 timing: string;
 estimatedYield: string;
 confidence: number;
 rationale: string;
 risks: string[];
 marketConditions: string;
}

const RECOMMENDATIONS: IssuanceRecommendation[] = [
 {
 id: 'ir1',
 name: 'Conservative Refinancing',
 bondType: 'Fixed Rate Bond',
 maturity: '5 Years',
 size: '$2.0B',
 currency: 'USD',
 timing: 'Q4 2026',
 estimatedYield: '4.15%',
 confidence: 88,
 rationale: 'Lock in rates before potential Fed tightening. 5Y tenor balances cost and duration. Strong investor demand for USD sovereign paper.',
 risks: ['Rates may drop further if recession materializes', 'Concentration in single currency'],
 marketConditions: 'Favorable. 5Y Treasury at 4.08%, spreads tightened 15bps this month.' },
 {
 id: 'ir2',
 name: 'Green Bond Issuance',
 bondType: 'Green Bond',
 maturity: '10 Years',
 size: '$1.5B',
 currency: 'EUR',
 timing: 'Q1 2027',
 estimatedYield: '3.85%',
 confidence: 82,
 rationale: 'First green bond under updated framework. ESG demand strong in Europe. Greenium of 5-8bps expected. Builds ESG credibility.',
 risks: ['Framework must be finalized', 'Greenium may be smaller than projected', 'EUR rates volatile'],
 marketConditions: 'Strong ESG demand. European green bond market growing 25% YoY.' },
 {
 id: 'ir3',
 name: 'Ultra-Long Duration',
 bondType: 'Fixed Rate Bond',
 maturity: '30 Years',
 size: '$1.0B',
 currency: 'GBP',
 timing: 'Q2 2027',
 estimatedYield: '4.85%',
 confidence: 75,
 rationale: 'Extend average maturity and lock in long-term rates. UK pension funds actively seeking long-duration sovereign paper.',
 risks: ['Higher cost than shorter maturities', 'Interest rate risk if rates decline', 'Limited investor base for 30Y'],
 marketConditions: 'UK gilt market stable. 30Y at 4.72%. Pension fund demand steady.' },
];

const MARKET_INDICATORS = [
 { name: 'US 5Y Treasury', value: '4.08%', change: '-2bps', trend: 'down' },
 { name: 'US 10Y Treasury', value: '4.22%', change: '+1bps', trend: 'up' },
 { name: 'EUR 10Y Bund', value: '2.85%', change: '-3bps', trend: 'down' },
 { name: 'GBP 10Y Gilt', value: '3.92%', change: '0bps', trend: 'stable' },
 { name: 'Sovereign Spread (5Y)', value: '145bps', change: '-8bps', trend: 'down' },
 { name: 'CDS 5Y', value: '125bps', change: '-5bps', trend: 'down' },
];

export default function DebtIssuancePlanner() {
 const [selected, setSelected] = useState<IssuanceRecommendation | null>(null);

 return (
 <div className="space-y-6 animate-glass-in">
 <div className="flex items-center gap-3">
 <div className="w-10 h-10 bg-gradient-to-br from-green-500 to-emerald-600 rounded-xl flex items-center justify-center">
 <Upload className="w-5 h-5" />
 </div>
 <div>
 <h2 className="text-xl font-bold text-white">Debt Issuance Planner</h2>
 <p className="text-sm text-slate-400">AI-recommended bond issuances based on market conditions</p>
 </div>
 </div>

 {/* Market Conditions */}
 <div className="glass rounded-2xl p-5">
 <h3 className="text-sm font-medium text-slate-400 mb-3">CURRENT MARKET CONDITIONS</h3>
 <div className="grid grid-cols-3 lg:grid-cols-6 gap-3">
 {MARKET_INDICATORS.map((ind, i) => (
 <div key={i} className="bg-white/5 rounded-xl p-3 text-center">
 <p className="text-xs text-slate-500 mb-1">{ind.name}</p>
 <p className="text-lg font-bold text-white">{ind.value}</p>
 <p className={`text-xs ${ind.trend === 'down' ? 'text-green-400' : ind.trend === 'up' ? 'text-red-400' : 'text-slate-400'}`}>
 {ind.change}
 </p>
 </div>
 ))}
 </div>
 </div>

 {/* Recommendations */}
 <div className="space-y-4">
 <h3 className="text-sm font-medium text-slate-400">AI RECOMMENDATIONS</h3>
 {RECOMMENDATIONS.map(rec => (
 <button
 key={rec.id}
 onClick={() => setSelected(selected?.id === rec.id ? null : rec)}
 className={`w-full text-left glass rounded-2xl p-5 transition-all ${
 selected?.id === rec.id ? 'ring-2 ring-green-500/50' : 'hover:bg-white/5'
 }`}
 >
 <div className="flex items-start justify-between mb-3">
 <div>
 <h4 className="text-lg font-bold text-white">{rec.name}</h4>
 <p className="text-sm text-slate-400">{rec.bondType} • {rec.maturity} • {rec.size} {rec.currency}</p>
 </div>
 <div className="text-right">
 <span className={`px-3 py-1 rounded-lg text-xs font-medium ${
 rec.confidence >= 85 ? 'bg-green-500/20 text-green-400' :
 rec.confidence >= 70 ? 'bg-yellow-500/20 text-yellow-400' :
 'bg-red-500/20 text-red-400'
 }`}>
 {rec.confidence}% confidence
 </span>
 </div>
 </div>

 <div className="grid grid-cols-4 gap-4 mb-3">
 <div className="bg-white/5 rounded-xl p-2 text-center">
 <p className="text-xs text-slate-500">Timing</p>
 <p className="text-sm font-medium text-white">{rec.timing}</p>
 </div>
 <div className="bg-white/5 rounded-xl p-2 text-center">
 <p className="text-xs text-slate-500">Est. Yield</p>
 <p className="text-sm font-medium text-green-400">{rec.estimatedYield}</p>
 </div>
 <div className="bg-white/5 rounded-xl p-2 text-center">
 <p className="text-xs text-slate-500">Size</p>
 <p className="text-sm font-medium text-white">{rec.size}</p>
 </div>
 <div className="bg-white/5 rounded-xl p-2 text-center">
 <p className="text-xs text-slate-500">Currency</p>
 <p className="text-sm font-medium text-white">{rec.currency}</p>
 </div>
 </div>

 {selected?.id === rec.id && (
 <div className="space-y-3 mt-4 pt-4 border-t border-white/10">
 <div>
 <p className="text-xs text-slate-500 mb-1">RATIONALE</p>
 <p className="text-sm text-slate-300">{rec.rationale}</p>
 </div>
 <div>
 <p className="text-xs text-slate-500 mb-1">MARKET CONDITIONS</p>
 <p className="text-sm text-slate-300">{rec.marketConditions}</p>
 </div>
 <div>
 <p className="text-xs text-slate-500 mb-1">RISKS</p>
 <div className="flex flex-wrap gap-2">
 {rec.risks.map((r, i) => (
 <span key={i} className="px-2 py-1 bg-red-500/10 text-red-300 rounded text-xs">{r}</span>
 ))}
 </div>
 </div>
 <button className="w-full py-3 bg-green-500/20 border border-green-500/30 rounded-xl text-green-400 font-medium hover:bg-green-500/30 transition-colors">
 <Upload className="w-4 h-4 inline" /> Initiate Issuance Process
 </button>
 </div>
 )}
 </button>
 ))}
 </div>
 </div>
 );
}
