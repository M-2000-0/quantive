import React, { useState } from 'react';
import { Lightbulb, PencilLine, Search } from 'lucide-react';

interface ConstraintBinding {
 name: string;
 status: 'binding' | 'near-binding' | 'slack';
 utilization: number;
 limit: string;
 current: string;
 impact: string;
}

interface ObjectiveContribution {
 name: string;
 weight: number;
 contribution: number;
 dominant: boolean;
}

interface ScenarioImpact {
 name: string;
 probability: number;
 portfolioImpact: number;
 driver: string;
}

interface ExplanationData {
 allocation: {
 instrument: string;
 amount: number;
 percentage: number;
 reason: string;
 alternativesConsidered: number;
 rankingPosition: number;
 }[];
 constraints: ConstraintBinding[];
 objectives: ObjectiveContribution[];
 scenarios: ScenarioImpact[];
 summary: string;
}

const MOCK_DATA: ExplanationData = {
 allocation: [
 { instrument: 'US Treasury 10Y', amount: 180, percentage: 18, reason: 'Lowest duration risk per unit of yield; avoids 2027 maturity wall', alternativesConsidered: 12, rankingPosition: 1 },
 { instrument: 'German Bund 5Y', amount: 120, percentage: 12, reason: 'EUR diversification with negative correlation to USD positions', alternativesConsidered: 8, rankingPosition: 2 },
 { instrument: 'Green Bond AAA', amount: 95, percentage: 9.5, reason: 'Meets ESG target at premium of only 5bps vs conventional', alternativesConsidered: 6, rankingPosition: 1 },
 { instrument: 'JGB 3Y', amount: 85, percentage: 8.5, reason: 'Short duration anchor; JPY hedge at 0.8% cost is favorable', alternativesConsidered: 10, rankingPosition: 3 },
 { instrument: 'UK Gilt 7Y', amount: 70, percentage: 7, reason: 'Sterling income matches GBP liability profile', alternativesConsidered: 7, rankingPosition: 2 },
 ],
 constraints: [
 { name: 'FX Exposure (USD)', status: 'binding', utilization: 100, limit: '≤ 35%', current: '35.0%', impact: 'Reduced USD allocation by $47M vs unconstrained optimum' },
 { name: 'Credit Quality', status: 'near-binding', utilization: 92, limit: '≥ BBB+', current: 'BBB+ (2.1 notches above)', impact: 'Excluded 4 high-yield instruments from feasible set' },
 { name: 'Duration Target', status: 'slack', utilization: 78, limit: '4.5 – 5.5 years', current: '5.1 years', impact: 'Within range; room to extend if rates rise' },
 { name: 'Green Bond Minimum', status: 'binding', utilization: 100, limit: '≥ 10%', current: '10.0%', impact: 'Forced $5M into green bond market at premium' },
 { name: 'Liquidity Buffer', status: 'slack', utilization: 65, limit: '≥ 15% in <1Y maturities', current: '22%', impact: 'Excess liquidity available for reallocation' },
 ],
 objectives: [
 { name: 'Minimize Cost', weight: 0.4, contribution: 0.38, dominant: false },
 { name: 'Minimize Duration Risk', weight: 0.3, contribution: 0.42, dominant: true },
 { name: 'Maximize Liquidity', weight: 0.2, contribution: 0.15, dominant: false },
 { name: 'Maximize ESG Score', weight: 0.1, contribution: 0.05, dominant: false },
 ],
 scenarios: [
 { name: 'Rates +200bps', probability: 25, portfolioImpact: -3.2, driver: 'Duration exposure dominates; 10Y Treasury loses most value' },
 { name: 'Rates -100bps', probability: 30, portfolioImpact: +2.1, driver: 'Long-duration positions gain; reinvestment risk on short end' },
 { name: 'Credit Spread Widening', probability: 15, portfolioImpact: -1.8, driver: 'Green bond and corporate positions affected; Bunds shelter' },
 { name: 'Currency Shock (USD -10%)', probability: 10, portfolioImpact: +0.9, driver: 'Diversified FX positions provide natural hedge' },
 ],
 summary: 'This allocation was chosen because it dominates the efficient frontier for your risk-adjusted return objective. The two binding constraints — FX exposure at 35% and green bond minimum at 10% — forced deviations from the unconstrained optimum of approximately $52M. Duration risk minimization was the dominant objective, contributing 42% of the total objective value despite only 30% weight, because the feasible set was shaped by constraints to favor shorter-duration instruments.'
};

interface AllocationReason {
  instrument: string;
  amount: number;
  percentage: number;
  reason: string;
  rankingPosition: number;
  alternativesConsidered: number;
}

interface ConstraintInfo {
  name: string;
  status: 'binding' | 'near-binding' | 'ok';
  impact: string;
  current: string;
  limit: string;
  utilization: number;
}

interface ObjectiveInfo {
  name: string;
  weight: number;
  contribution: number;
  dominant: boolean;
}

interface ScenarioInfo {
  name: string;
  probability: number;
  portfolioImpact: number;
  driver: string;
}

interface ExplainabilityData {
  summary: string;
  allocation: AllocationReason[];
  constraints: ConstraintInfo[];
  objectives: ObjectiveInfo[];
  scenarios: ScenarioInfo[];
}

const MOCK_EXPLANATION: ExplainabilityData = {
  summary: 'Duration was extended to lock in yields before expected rate cuts, funded by trimming short-dated bills.',
  allocation: [
    { instrument: 'US Treasury 10Y', amount: 120, percentage: 34, reason: 'Locks in 4.3% yield with strong liquidity.', rankingPosition: 1, alternativesConsidered: 5 },
    { instrument: 'EU Green Bond 15Y', amount: 80, percentage: 22, reason: 'Adds duration plus ESG alignment.', rankingPosition: 2, alternativesConsidered: 4 },
  ],
  constraints: [
    { name: 'Single-issuer limit', status: 'near-binding', impact: 'Caps Treasury exposure at 40%.', current: '34%', limit: '40%', utilization: 85 },
    { name: 'Liquidity floor', status: 'ok', impact: 'No action needed.', current: '8%', limit: '5%', utilization: 40 },
  ],
  objectives: [
    { name: 'Minimize cost', weight: 0.5, contribution: 0.34, dominant: true },
    { name: 'Limit risk', weight: 0.3, contribution: 0.18, dominant: false },
  ],
  scenarios: [
    { name: 'Base case', probability: 0.6, portfolioImpact: 1.2, driver: 'Gradual rate cuts' },
    { name: 'Rate shock', probability: 0.15, portfolioImpact: -2.4, driver: 'Inflation surprise' },
  ] };

export default function ExplainabilityEngine() {
 const [activeTab, setActiveTab] = useState<'overview' | 'constraints' | 'objectives' | 'scenarios'>('overview');
 const data = MOCK_EXPLANATION;

 const tabs = [
 { id: 'overview' as const, label: 'Allocation Why', icon: 'Target' },
 { id: 'constraints' as const, label: 'Constraints', icon: 'Lock' },
 { id: 'objectives' as const, label: 'Objectives', icon: 'Scale' },
 { id: 'scenarios' as const, label: 'Scenarios', icon: '🌊' },
 ];

 return (
 <div className="space-y-6 animate-glass-in">
 <div className="flex items-center gap-3">
 <div className="w-10 h-10 bg-gradient-to-br from-amber-500 to-orange-600 rounded-xl flex items-center justify-center">
 <Search className="w-5 h-5" />
 </div>
 <div>
 <h2 className="text-xl font-bold text-white">Explainability Engine</h2>
 <p className="text-sm text-slate-400">Every optimization shows its work</p>
 </div>
 </div>

 {/* Summary */}
 <div className="glass rounded-2xl p-5">
 <h3 className="text-sm font-medium text-amber-400 mb-2"> <PencilLine className="w-4 h-4 inline" /> Plain English Summary</h3>
 <p className="text-slate-300 leading-relaxed text-sm">{data.summary}</p>
 </div>

 {/* Tabs */}
 <div className="flex gap-2">
 {tabs.map(tab => (
 <button
 key={tab.id}
 onClick={() => setActiveTab(tab.id)}
 className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
 activeTab === tab.id
 ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
 : 'bg-white/5 text-slate-400 hover:bg-white/10 border border-transparent'
 }`}
 >
 {tab.icon} {tab.label}
 </button>
 ))}
 </div>

 {/* Overview - Allocation Reasons */}
 {activeTab === 'overview' && (
 <div className="space-y-3">
 {data.allocation.map((a, i) => (
 <div key={i} className="glass rounded-xl p-4">
 <div className="flex items-start justify-between mb-2">
 <div>
 <h4 className="text-white font-medium">{a.instrument}</h4>
 <p className="text-xs text-slate-400">${a.amount}M ({a.percentage}%)</p>
 </div>
 <div className="flex items-center gap-2">
 <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded text-xs">
 Rank #{a.rankingPosition} of {a.alternativesConsidered}
 </span>
 </div>
 </div>
 <p className="text-sm text-slate-300 bg-white/5 rounded-lg p-3 border-l-2 border-amber-500">
 <Lightbulb className="w-4 h-4 inline" /> {a.reason}
 </p>
 </div>
 ))}
 </div>
 )}

 {/* Constraints */}
 {activeTab === 'constraints' && (
 <div className="space-y-3">
 {data.constraints.map((c, i) => (
 <div key={i} className="glass rounded-xl p-4">
 <div className="flex items-center justify-between mb-2">
 <div className="flex items-center gap-2">
 <span className={`w-2 h-2 rounded-full ${
 c.status === 'binding' ? 'bg-red-400' :
 c.status === 'near-binding' ? 'bg-yellow-400' : 'bg-green-400'
 }`} />
 <h4 className="text-white font-medium">{c.name}</h4>
 </div>
 <span className={`px-2 py-0.5 rounded text-xs font-medium ${
 c.status === 'binding' ? 'bg-red-500/20 text-red-400' :
 c.status === 'near-binding' ? 'bg-yellow-500/20 text-yellow-400' :
 'bg-green-500/20 text-green-400'
 }`}>
 {c.status}
 </span>
 </div>
 <div className="grid grid-cols-3 gap-3 mb-2 text-xs">
 <div>
 <span className="text-slate-500">Limit:</span>
 <span className="text-white ml-1">{c.limit}</span>
 </div>
 <div>
 <span className="text-slate-500">Current:</span>
 <span className="text-white ml-1">{c.current}</span>
 </div>
 <div>
 <span className="text-slate-500">Utilization:</span>
 <span className="text-white ml-1">{c.utilization}%</span>
 </div>
 </div>
 <div className="w-full bg-white/5 rounded-full h-1.5 mb-2">
 <div
 className={`h-1.5 rounded-full ${
 c.utilization >= 100 ? 'bg-red-400' :
 c.utilization >= 85 ? 'bg-yellow-400' : 'bg-green-400'
 }`}
 style={{ width: `${Math.min(c.utilization, 100)}%` }}
 />
 </div>
 <p className="text-xs text-slate-400">Impact: {c.impact}</p>
 </div>
 ))}
 </div>
 )}

 {/* Objectives */}
 {activeTab === 'objectives' && (
 <div className="space-y-3">
 <div className="glass rounded-xl p-4">
 <h3 className="text-sm font-medium text-slate-400 mb-3">Objective Contribution Analysis</h3>
 <div className="space-y-4">
 {data.objectives.map((o, i) => (
 <div key={i}>
 <div className="flex items-center justify-between mb-1">
 <div className="flex items-center gap-2">
 <span className="text-white text-sm">{o.name}</span>
 {o.dominant && (
 <span className="px-1.5 py-0.5 bg-amber-500/20 text-amber-400 rounded text-xs">
 DOMINANT
 </span>
 )}
 </div>
 <span className="text-xs text-slate-400">
 Weight: {(o.weight * 100).toFixed(0)}% → Contribution: {(o.contribution * 100).toFixed(0)}%
 </span>
 </div>
 <div className="flex gap-1 items-center">
 <div className="flex-1 bg-white/5 rounded-full h-2">
 <div
 className={`h-2 rounded-full ${o.dominant ? 'bg-amber-400' : 'bg-slate-500'}`}
 style={{ width: `${o.contribution * 100}%` }}
 />
 </div>
 <span className="text-xs text-slate-500 w-12 text-right">
 {((o.contribution / o.weight) * 100).toFixed(0)}% efficiency
 </span>
 </div>
 </div>
 ))}
 </div>
 </div>
 <div className="glass rounded-xl p-4 border-l-2 border-amber-500">
 <p className="text-sm text-slate-300">
 <strong className="text-amber-400">Key Insight:</strong> Duration risk minimization contributed 42% of total objective value despite only 30% weight. This is because the binding FX and green bond constraints reshaped the feasible set to favor shorter-duration instruments, making duration reduction "cheaper" than cost reduction in the constrained space.
 </p>
 </div>
 </div>
 )}

 {/* Scenarios */}
 {activeTab === 'scenarios' && (
 <div className="space-y-3">
 {data.scenarios.map((s, i) => (
 <div key={i} className="glass rounded-xl p-4">
 <div className="flex items-center justify-between mb-2">
 <h4 className="text-white font-medium">{s.name}</h4>
 <div className="flex items-center gap-3">
 <span className="text-xs text-slate-400">P = {(s.probability * 100).toFixed(0)}%</span>
 <span className={`px-2 py-0.5 rounded text-xs font-medium ${
 s.portfolioImpact >= 0 ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
 }`}>
 {s.portfolioImpact >= 0 ? '+' : ''}{s.portfolioImpact.toFixed(1)}%
 </span>
 </div>
 </div>
 <p className="text-sm text-slate-400">Driver: {s.driver}</p>
 <div className="mt-2 flex items-center gap-2">
 <div className="flex-1 bg-white/5 rounded-full h-1.5">
 <div
 className={`h-1.5 rounded-full ${s.portfolioImpact >= 0 ? 'bg-green-400' : 'bg-red-400'}`}
 style={{ width: `${Math.abs(s.portfolioImpact) * 20}%` }}
 />
 </div>
 </div>
 </div>
 ))}
 <div className="glass rounded-xl p-4 border-l-2 border-blue-500">
 <p className="text-sm text-slate-300">
 <strong className="text-blue-400">Scenarios that mattered most:</strong> Rate rises (+200bps) and credit spread widening together account for 85% of downside risk. The allocation mitigates these through short-duration positioning and high-quality credit bias.
 </p>
 </div>
 </div>
 )}
 </div>
 );
}
