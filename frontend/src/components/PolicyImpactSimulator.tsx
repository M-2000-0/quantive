import React, { useState } from 'react';
import { Building2, CircleCheck as CheckCircle, FileText, Lightbulb, TriangleAlert as AlertTriangle } from 'lucide-react';

interface ImpactDimension {
 id: string;
 name: string;
 icon: string;
 category: 'economic' | 'social' | 'political';
 currentValue: number;
 simulatedValue: number;
 unit: string;
 direction: 'higher_better' | 'lower_better';
}

interface PolicyScenario {
 id: string;
 name: string;
 description: string;
 icon: string;
 dimensions: Omit<ImpactDimension, 'currentValue' | 'simulatedValue'>[];
}

const POLICY_SCENARIOS: PolicyScenario[] = [
 {
 id: 'refinance',
 name: 'Refinance $5B Maturity',
 description: 'Issue new 10Y bonds to refinance maturing 2027 debt at current rates',
 icon: 'DollarSign',
 dimensions: [
 { id: 'inflation', name: 'Inflation Impact', icon: 'TrendingUp', category: 'economic', unit: '%', direction: 'lower_better' },
 { id: 'unemployment', name: 'Employment Effect', icon: 'Users', category: 'social', unit: '%', direction: 'lower_better' },
 { id: 'gdp', name: 'GDP Growth', icon: 'BarChart3', category: 'economic', unit: '%', direction: 'higher_better' },
 { id: 'currency', name: 'Currency Stability', icon: '💱', category: 'economic', unit: 'index', direction: 'higher_better' },
 { id: 'election', name: 'Public Approval', icon: '🗳️', category: 'political', unit: '%', direction: 'higher_better' },
 { id: 'spending', name: 'Public Spending', icon: 'Building2', category: 'social', unit: '$B', direction: 'lower_better' },
 { id: 'debt_gdp', name: 'Debt-to-GDP', icon: 'TrendingDown', category: 'economic', unit: '%', direction: 'lower_better' },
 { id: 'credit_rating', name: 'Credit Rating', icon: '⭐', category: 'economic', unit: 'notch', direction: 'higher_better' },
 ] },
 {
 id: 'austerity',
 name: 'Fiscal Consolidation',
 description: 'Reduce government spending by 8% over 2 years to lower deficit',
 icon: '✂️',
 dimensions: [
 { id: 'inflation', name: 'Inflation Impact', icon: 'TrendingUp', category: 'economic', unit: '%', direction: 'lower_better' },
 { id: 'unemployment', name: 'Employment Effect', icon: 'Users', category: 'social', unit: '%', direction: 'lower_better' },
 { id: 'gdp', name: 'GDP Growth', icon: 'BarChart3', category: 'economic', unit: '%', direction: 'higher_better' },
 { id: 'currency', name: 'Currency Stability', icon: '💱', category: 'economic', unit: 'index', direction: 'higher_better' },
 { id: 'election', name: 'Public Approval', icon: '🗳️', category: 'political', unit: '%', direction: 'higher_better' },
 { id: 'spending', name: 'Public Spending', icon: 'Building2', category: 'social', unit: '$B', direction: 'lower_better' },
 { id: 'debt_gdp', name: 'Debt-to-GDP', icon: 'TrendingDown', category: 'economic', unit: '%', direction: 'lower_better' },
 { id: 'credit_rating', name: 'Credit Rating', icon: '⭐', category: 'economic', unit: 'notch', direction: 'higher_better' },
 ] },
 {
 id: 'stimulus',
 name: 'Infrastructure Stimulus',
 description: 'Borrow $8B for infrastructure projects to boost growth',
 icon: 'Building',
 dimensions: [
 { id: 'inflation', name: 'Inflation Impact', icon: 'TrendingUp', category: 'economic', unit: '%', direction: 'lower_better' },
 { id: 'unemployment', name: 'Employment Effect', icon: 'Users', category: 'social', unit: '%', direction: 'lower_better' },
 { id: 'gdp', name: 'GDP Growth', icon: 'BarChart3', category: 'economic', unit: '%', direction: 'higher_better' },
 { id: 'currency', name: 'Currency Stability', icon: '💱', category: 'economic', unit: 'index', direction: 'higher_better' },
 { id: 'election', name: 'Public Approval', icon: '🗳️', category: 'political', unit: '%', direction: 'higher_better' },
 { id: 'spending', name: 'Public Spending', icon: 'Building2', category: 'social', unit: '$B', direction: 'lower_better' },
 { id: 'debt_gdp', name: 'Debt-to-GDP', icon: 'TrendingDown', category: 'economic', unit: '%', direction: 'lower_better' },
 { id: 'credit_rating', name: 'Credit Rating', icon: '⭐', category: 'economic', unit: 'notch', direction: 'higher_better' },
 ] },
 {
 id: 'hedge',
 name: 'FX Hedging Program',
 description: 'Hedge 60% of foreign currency exposure at current forward rates',
 icon: 'Shield',
 dimensions: [
 { id: 'inflation', name: 'Inflation Impact', icon: 'TrendingUp', category: 'economic', unit: '%', direction: 'lower_better' },
 { id: 'unemployment', name: 'Employment Effect', icon: 'Users', category: 'social', unit: '%', direction: 'lower_better' },
 { id: 'gdp', name: 'GDP Growth', icon: 'BarChart3', category: 'economic', unit: '%', direction: 'higher_better' },
 { id: 'currency', name: 'Currency Stability', icon: '💱', category: 'economic', unit: 'index', direction: 'higher_better' },
 { id: 'election', name: 'Public Approval', icon: '🗳️', category: 'political', unit: '%', direction: 'higher_better' },
 { id: 'spending', name: 'Public Spending', icon: 'Building2', category: 'social', unit: '$B', direction: 'lower_better' },
 { id: 'debt_gdp', name: 'Debt-to-GDP', icon: 'TrendingDown', category: 'economic', unit: '%', direction: 'lower_better' },
 { id: 'credit_rating', name: 'Credit Rating', icon: '⭐', category: 'economic', unit: 'notch', direction: 'higher_better' },
 ] },
];

const MOCK_IMPACTS: Record<string, Record<string, { current: number; simulated: number }>> = {
 refinance: {
 inflation: { current: 3.2, simulated: 3.1 },
 unemployment: { current: 5.8, simulated: 5.7 },
 gdp: { current: 2.1, simulated: 2.3 },
 currency: { current: 72, simulated: 74 },
 election: { current: 48, simulated: 51 },
 spending: { current: 42.5, simulated: 41.8 },
 debt_gdp: { current: 68.2, simulated: 67.5 },
 credit_rating: { current: 3, simulated: 3.5 } },
 austerity: {
 inflation: { current: 3.2, simulated: 2.8 },
 unemployment: { current: 5.8, simulated: 6.4 },
 gdp: { current: 2.1, simulated: 1.4 },
 currency: { current: 72, simulated: 76 },
 election: { current: 48, simulated: 38 },
 spending: { current: 42.5, simulated: 39.1 },
 debt_gdp: { current: 68.2, simulated: 64.8 },
 credit_rating: { current: 3, simulated: 3.8 } },
 stimulus: {
 inflation: { current: 3.2, simulated: 3.6 },
 unemployment: { current: 5.8, simulated: 5.1 },
 gdp: { current: 2.1, simulated: 2.8 },
 currency: { current: 72, simulated: 68 },
 election: { current: 48, simulated: 55 },
 spending: { current: 42.5, simulated: 46.2 },
 debt_gdp: { current: 68.2, simulated: 72.1 },
 credit_rating: { current: 3, simulated: 2.5 } },
 hedge: {
 inflation: { current: 3.2, simulated: 3.2 },
 unemployment: { current: 5.8, simulated: 5.8 },
 gdp: { current: 2.1, simulated: 2.1 },
 currency: { current: 72, simulated: 78 },
 election: { current: 48, simulated: 49 },
 spending: { current: 42.5, simulated: 42.8 },
 debt_gdp: { current: 68.2, simulated: 68.0 },
 credit_rating: { current: 3, simulated: 3.2 } } };

const CATEGORY_COLORS: Record<string, string> = {
 economic: 'bg-blue-500/20 text-blue-400',
 social: 'bg-purple-500/20 text-purple-400',
 political: 'bg-amber-500/20 text-amber-400' };

export default function PolicyImpactSimulator() {
 const [selectedScenario, setSelectedScenario] = useState(POLICY_SCENARIOS[0]);
 const [impacts, setImpacts] = useState<Record<string, Record<string, { current: number; simulated: number }>>>(MOCK_IMPACTS);
 const [isSimulating, setIsSimulating] = useState(false);
 const [hasSimulated, setHasSimulated] = useState(false);

 const runSimulation = () => {
 setIsSimulating(true);
 setTimeout(() => {
 setHasSimulated(true);
 setIsSimulating(false);
 }, 2000);
 };

 const getImpact = (dimensionId: string) => {
 return impacts[selectedScenario.id]?.[dimensionId] || { current: 0, simulated: 0 };
 };

 const getChange = (dimensionId: string, direction: 'higher_better' | 'lower_better') => {
 const impact = getImpact(dimensionId);
 const change = impact.simulated - impact.current;
 const isPositive = direction === 'higher_better' ? change > 0 : change < 0;
 return { change, isPositive, formatted: `${change > 0 ? '+' : ''}${change.toFixed(1)}` };
 };

 const overallScore = selectedScenario.dimensions.reduce((acc, d) => {
 const { isPositive } = getImpact(d.id).simulated > getImpact(d.id).current
 ? { isPositive: d.direction === 'higher_better' }
 : { isPositive: d.direction === 'lower_better' };
 return acc + (isPositive ? 1 : 0);
 }, 0);

 return (
 <div className="space-y-6 animate-glass-in">
 <div className="flex items-center gap-3">
 <div className="w-10 h-10 bg-gradient-to-br from-rose-500 to-pink-600 rounded-xl flex items-center justify-center">
 <Building2 className="w-5 h-5" />
 </div>
 <div>
 <h2 className="text-xl font-bold text-white">Policy Impact Simulator</h2>
 <p className="text-sm text-slate-400">Model political, economic, and social consequences of debt decisions</p>
 </div>
 </div>

 {/* Scenario Selection */}
 <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
 {POLICY_SCENARIOS.map(s => (
 <button
 key={s.id}
 onClick={() => { setSelectedScenario(s); setHasSimulated(false); }}
 className={`text-left p-4 rounded-xl border transition-all ${
 selectedScenario.id === s.id
 ? 'bg-rose-500/10 border-rose-500/30'
 : 'bg-white/5 border-white/10 hover:bg-white/10'
 }`}
 >
 <span className="text-2xl mb-2 block">{s.icon}</span>
 <h4 className="text-white text-sm font-medium mb-1">{s.name}</h4>
 <p className="text-xs text-slate-400">{s.description}</p>
 </button>
 ))}
 </div>

 {/* Run Button */}
 {!hasSimulated && (
 <button
 onClick={runSimulation}
 disabled={isSimulating}
 className="w-full py-4 bg-gradient-to-r from-rose-500 to-pink-600 rounded-2xl text-white font-bold text-lg hover:opacity-90 transition-opacity disabled:opacity-50"
 >
 {isSimulating ? ' <RefreshCw className="w-4 h-4 inline" /> Simulating Policy Impact...' : ` <Building2 className="w-4 h-4 inline" /> Simulate ${selectedScenario.name}`}
 </button>
 )}

 {/* Simulation Progress */}
 {isSimulating && (
 <div className="glass rounded-2xl p-8 text-center">
 <div className="animate-spin w-10 h-10 border-2 border-rose-400 border-t-transparent rounded-full mx-auto mb-4" />
 <p className="text-white font-medium mb-2">Running Policy Impact Model...</p>
 <p className="text-sm text-slate-400">Analyzing economic, social, and political dimensions</p>
 <div className="mt-4 flex justify-center gap-2">
 {['Economic', 'Social', 'Political'].map((cat, i) => (
 <span key={cat} className="px-3 py-1 bg-white/5 rounded-lg text-xs text-slate-400 animate-pulse" style={{ animationDelay: `${i * 0.3}s` }}>
 {cat}...
 </span>
 ))}
 </div>
 </div>
 )}

 {/* Results */}
 {hasSimulated && !isSimulating && (
 <div className="space-y-6">
 {/* Overall Score */}
 <div className="glass rounded-2xl p-6">
 <div className="flex items-center justify-between mb-4">
 <h3 className="text-sm font-medium text-slate-400">OVERALL POLICY ASSESSMENT</h3>
 <span className={`px-3 py-1 rounded-lg text-sm font-bold ${
 overallScore >= 6 ? 'bg-green-500/20 text-green-400' :
 overallScore >= 4 ? 'bg-yellow-500/20 text-yellow-400' :
 'bg-red-500/20 text-red-400'
 }`}>
 {overallScore}/{selectedScenario.dimensions.length} Positive
 </span>
 </div>
 <div className="grid grid-cols-3 gap-4 text-center">
 {[
 { label: 'Economic', score: selectedScenario.dimensions.filter(d => d.category === 'economic').filter(d => getChange(d.id, d.direction).isPositive).length, total: selectedScenario.dimensions.filter(d => d.category === 'economic').length, color: 'blue' },
 { label: 'Social', score: selectedScenario.dimensions.filter(d => d.category === 'social').filter(d => getChange(d.id, d.direction).isPositive).length, total: selectedScenario.dimensions.filter(d => d.category === 'social').length, color: 'purple' },
 { label: 'Political', score: selectedScenario.dimensions.filter(d => d.category === 'political').filter(d => getChange(d.id, d.direction).isPositive).length, total: selectedScenario.dimensions.filter(d => d.category === 'political').length, color: 'amber' },
 ].map(cat => (
 <div key={cat.label} className="bg-white/5 rounded-xl p-4">
 <p className="text-3xl font-bold text-white">{cat.score}/{cat.total}</p>
 <p className={`text-xs text-${cat.color}-400`}>{cat.label}</p>
 </div>
 ))}
 </div>
 </div>

 {/* Impact Grid */}
 <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
 {selectedScenario.dimensions.map(d => {
 const impact = getImpact(d.id);
 const { change, isPositive, formatted } = getChange(d.id, d.direction);
 const magnitude = Math.abs(change);
 const barWidth = Math.min(magnitude * 20, 100);

 return (
 <div key={d.id} className="glass rounded-xl p-4">
 <div className="flex items-center justify-between mb-3">
 <div className="flex items-center gap-2">
 <span className="text-lg">{d.icon}</span>
 <div>
 <h4 className="text-white text-sm font-medium">{d.name}</h4>
 <span className={`px-2 py-0.5 rounded text-xs ${CATEGORY_COLORS[d.category]}`}>
 {d.category}
 </span>
 </div>
 </div>
 <div className="text-right">
 <span className={`text-lg font-bold ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
 {formatted}{d.unit === '%' ? 'pp' : ` ${d.unit}`}
 </span>
 </div>
 </div>

 {/* Before/After */}
 <div className="flex items-center gap-3 mb-2">
 <div className="flex-1">
 <p className="text-xs text-slate-500 mb-1">Current</p>
 <p className="text-white text-sm font-medium">{impact.current} {d.unit}</p>
 </div>
 <div className="text-slate-500">→</div>
 <div className="flex-1 text-right">
 <p className="text-xs text-slate-500 mb-1">Simulated</p>
 <p className={`text-sm font-medium ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
 {impact.simulated} {d.unit}
 </p>
 </div>
 </div>

 {/* Impact bar */}
 <div className="w-full bg-white/5 rounded-full h-2">
 <div
 className={`h-2 rounded-full transition-all duration-1000 ${isPositive ? 'bg-green-400' : 'bg-red-400'}`}
 style={{ width: `${barWidth}%` }}
 />
 </div>
 </div>
 );
 })}
 </div>

 {/* Political Analysis */}
 <div className="glass rounded-2xl p-6 border-l-2 border-amber-500">
 <h3 className="text-sm font-medium text-amber-400 mb-3">🗳️ Political Analysis</h3>
 <div className="space-y-2 text-sm text-slate-300">
 <p>• <strong>Public Approval:</strong> {getChange('election', 'higher_better').isPositive ? 'Increases' : 'Decreases'} by {Math.abs(getImpact('election').simulated - getImpact('election').current).toFixed(1)}pp — {getChange('election', 'higher_better').isPositive ? 'favorable for upcoming elections' : 'may face electoral headwinds'}</p>
 <p>• <strong>Spending Perception:</strong> {getChange('spending', 'lower_better').isPositive ? 'Fiscal discipline signal' : 'Increased spending may draw scrutiny'}</p>
 <p>• <strong>Credit Standing:</strong> {getChange('credit_rating', 'higher_better').isPositive ? 'Rating agencies likely to view favorably' : 'May trigger review from rating agencies'}</p>
 </div>
 </div>

 {/* Recommendations */}
 <div className="glass rounded-2xl p-6">
 <h3 className="text-sm font-medium text-slate-400 mb-3"> <FileText className="w-4 h-4 inline" /> RECOMMENDATIONS</h3>
 <div className="space-y-2">
 {overallScore >= 6 && (
 <div className="flex items-center gap-3 p-3 bg-green-500/10 rounded-xl">
 <CheckCircle className="w-5 h-5" />
 <p className="text-sm text-green-300">This policy has strong cross-dimensional support. Recommend proceeding with implementation.</p>
 </div>
 )}
 {overallScore < 4 && (
 <div className="flex items-center gap-3 p-3 bg-red-500/10 rounded-xl">
 <AlertTriangle className="w-5 h-5" />
 <p className="text-sm text-red-300">Significant trade-offs detected. Consider phased implementation or alternative approach.</p>
 </div>
 )}
 <div className="flex items-center gap-3 p-3 bg-white/5 rounded-xl">
 <Lightbulb className="w-5 h-5" />
 <p className="text-sm text-slate-300">Run additional scenarios to compare alternatives and build consensus before final decision.</p>
 </div>
 </div>
 </div>

 {/* Reset */}
 <button
 onClick={() => { setHasSimulated(false); }}
 className="w-full py-3 bg-white/5 border border-white/10 rounded-xl text-slate-400 hover:bg-white/10 transition-colors"
 >
 ← Try Another Scenario
 </button>
 </div>
 )}
 </div>
 );
}
