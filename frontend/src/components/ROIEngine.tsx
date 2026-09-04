import React, { useState } from 'react';
import { DollarSign } from 'lucide-react';

interface ROIMetric {
  name: string;
  before: string;
  after: string;
  improvement: string;
  positive: boolean;
  category: 'cost' | 'risk' | 'structure' | 'compliance';
}

interface StrategyComparison {
  name: string;
  annualSavings: number;
  riskChange: number;
  maturityChange: number;
  costChange: number;
  politicalScore: number;
  feasibilityScore: number;
}

const BASELINE_METRICS: ROIMetric[] = [
  { name: 'Debt Service Cost', before: '$4.2B', after: '$3.8B', improvement: '$400M', positive: true, category: 'cost' },
  { name: 'Refinancing Risk', before: '32%', after: '18%', improvement: '-44%', positive: true, category: 'risk' },
  { name: 'FX Exposure', before: '41%', after: '23%', improvement: '-44%', positive: true, category: 'risk' },
  { name: 'Average Maturity', before: '4.2 yrs', after: '6.1 yrs', improvement: '+45%', positive: true, category: 'structure' },
  { name: 'Funding Cost', before: '7.3%', after: '6.7%', improvement: '-0.6%', positive: true, category: 'cost' },
  { name: 'Liquidity Coverage', before: '14.2%', after: '19.8%', improvement: '+39%', positive: true, category: 'risk' },
  { name: 'Green Bond Allocation', before: '8%', after: '15%', improvement: '+88%', positive: true, category: 'compliance' },
  { name: 'Weighted Avg Life', before: '5.1 yrs', after: '7.3 yrs', improvement: '+43%', positive: true, category: 'structure' },
];

const STRATEGIES: StrategyComparison[] = [
  { name: 'Strategy A: Staggered Issuance', annualSavings: 400, riskChange: -44, maturityChange: 45, costChange: -0.6, politicalScore: 85, feasibilityScore: 92 },
  { name: 'Strategy B: Aggressive Refinancing', annualSavings: 520, riskChange: -12, maturityChange: 28, costChange: -0.8, politicalScore: 70, feasibilityScore: 75 },
  { name: 'Strategy C: Green Pivot', annualSavings: 180, riskChange: -25, maturityChange: 35, costChange: -0.3, politicalScore: 95, feasibilityScore: 88 },
  { name: 'Strategy D: Conservative Hold', annualSavings: 85, riskChange: -8, maturityChange: 12, costChange: -0.1, politicalScore: 90, feasibilityScore: 95 },
];

const CATEGORY_COLORS: Record<string, string> = {
  cost: 'bg-green-500/20 text-green-400',
  risk: 'bg-blue-500/20 text-blue-400',
  structure: 'bg-purple-500/20 text-purple-400',
  compliance: 'bg-amber-500/20 text-amber-400' };

export default function ROIEngine() {
  const [metrics] = useState(BASELINE_METRICS);
  const [strategies] = useState(STRATEGIES);
  const [selectedStrategy, setSelectedStrategy] = useState(STRATEGIES[0]);
  const [showComparison, setShowComparison] = useState(false);

  const totalSavings = selectedStrategy.annualSavings;
  const tenYearImpact = totalSavings * 10 * 0.85; // accounting for compounding

  return (
    <div className="space-y-6 animate-glass-in">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-emerald-500 to-green-600 rounded-xl flex items-center justify-center">
            <DollarSign className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">ROI Engine</h2>
            <p className="text-sm text-slate-400">Automatic savings calculation for every optimization</p>
          </div>
        </div>
        <div className="flex gap-3">
          <div className="glass px-5 py-3 rounded-xl text-center">
            <p className="text-3xl font-bold text-green-400">${totalSavings}M</p>
            <p className="text-xs text-slate-400">Est. Annual Savings</p>
          </div>
          <div className="glass px-5 py-3 rounded-xl text-center">
            <p className="text-3xl font-bold text-emerald-400">${(tenYearImpact / 1000).toFixed(1)}B</p>
            <p className="text-xs text-slate-400">10-Year Impact</p>
          </div>
        </div>
      </div>

      {/* Key Savings Banner */}
      <div className="bg-gradient-to-r from-emerald-500/10 to-green-500/10 border border-emerald-500/20 rounded-2xl p-6">
        <div className="grid grid-cols-4 gap-6">
          <div className="text-center">
            <p className="text-4xl font-bold text-emerald-400">${totalSavings}M</p>
            <p className="text-sm text-slate-400 mt-1">Estimated Annual Savings</p>
          </div>
          <div className="text-center">
            <p className="text-4xl font-bold text-green-400">${(tenYearImpact / 1000).toFixed(1)}B</p>
            <p className="text-sm text-slate-400 mt-1">Estimated 10-Year Impact</p>
          </div>
          <div className="text-center">
            <p className="text-4xl font-bold text-blue-400">-0.6%</p>
            <p className="text-sm text-slate-400 mt-1">Funding Cost Reduction</p>
          </div>
          <div className="text-center">
            <p className="text-4xl font-bold text-purple-400">+45%</p>
            <p className="text-sm text-slate-400 mt-1">Maturity Extension</p>
          </div>
        </div>
      </div>

      {/* Metrics Table */}
      <div className="glass rounded-2xl p-6">
        <h3 className="text-sm font-medium text-slate-400 mb-4">OPTIMIZATION IMPACT</h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/10">
                <th className="text-left text-xs text-slate-500 py-3 px-4">Metric</th>
                <th className="text-left text-xs text-slate-500 py-3 px-4">Category</th>
                <th className="text-right text-xs text-slate-500 py-3 px-4">Before</th>
                <th className="text-right text-xs text-slate-500 py-3 px-4">After</th>
                <th className="text-right text-xs text-slate-500 py-3 px-4">Improvement</th>
              </tr>
            </thead>
            <tbody>
              {metrics.map((m, i) => (
                <tr key={i} className="border-b border-white/5 hover:bg-white/5">
                  <td className="py-3 px-4 text-white text-sm font-medium">{m.name}</td>
                  <td className="py-3 px-4">
                    <span className={`px-2 py-0.5 rounded text-xs ${CATEGORY_COLORS[m.category]}`}>
                      {m.category}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right text-slate-400 text-sm">{m.before}</td>
                  <td className="py-3 px-4 text-right text-white text-sm font-medium">{m.after}</td>
                  <td className={`py-3 px-4 text-right text-sm font-bold ${m.positive ? 'text-green-400' : 'text-red-400'}`}>
                    {m.improvement}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Strategy Comparison */}
      <div className="glass rounded-2xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium text-slate-400">STRATEGY COMPARISON</h3>
          <button
            onClick={() => setShowComparison(!showComparison)}
            className="px-3 py-1.5 bg-white/5 rounded-lg text-xs text-slate-400 hover:bg-white/10"
          >
            {showComparison ? 'Hide' : 'Show'} Details
          </button>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {strategies.map((s, i) => (
            <button
              key={i}
              onClick={() => setSelectedStrategy(s)}
              className={`text-left p-4 rounded-xl border transition-all ${
                selectedStrategy.name === s.name
                  ? 'bg-emerald-500/10 border-emerald-500/30'
                  : 'bg-white/5 border-white/10 hover:bg-white/10'
              }`}
            >
              <h4 className="text-white text-sm font-medium mb-3">{s.name}</h4>
              <div className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-500">Annual Savings</span>
                  <span className="text-green-400 font-medium">${s.annualSavings}M</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-slate-500">Risk Change</span>
                  <span className="text-blue-400 font-medium">{s.riskChange}%</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-slate-500">Political Score</span>
                  <span className="text-amber-400 font-medium">{s.politicalScore}/100</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-slate-500">Feasibility</span>
                  <span className="text-purple-400 font-medium">{s.feasibilityScore}/100</span>
                </div>
              </div>
              {selectedStrategy.name === s.name && (
                <div className="mt-3 pt-3 border-t border-white/10">
                  <p className="text-xs text-emerald-400 font-medium">✓ Selected</p>
                </div>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Projected 10-Year Impact */}
      <div className="glass rounded-2xl p-6">
        <h3 className="text-sm font-medium text-slate-400 mb-4">10-YEAR PROJECTED IMPACT</h3>
        <div className="grid grid-cols-5 gap-3">
          {[
            { year: '2027', savings: totalSavings * 0.3, cumulative: totalSavings * 0.3 },
            { year: '2028', savings: totalSavings * 0.7, cumulative: totalSavings * 1.0 },
            { year: '2029', savings: totalSavings * 0.9, cumulative: totalSavings * 1.9 },
            { year: '2030', savings: totalSavings, cumulative: totalSavings * 2.9 },
            { year: '2031', savings: totalSavings, cumulative: totalSavings * 3.9 },
            { year: '2032', savings: totalSavings, cumulative: totalSavings * 4.9 },
            { year: '2033', savings: totalSavings, cumulative: totalSavings * 5.9 },
            { year: '2034', savings: totalSavings, cumulative: totalSavings * 6.9 },
            { year: '2035', savings: totalSavings, cumulative: totalSavings * 7.9 },
            { year: '2036', savings: totalSavings, cumulative: totalSavings * 8.9 },
          ].map((y, i) => (
            <div key={i} className="text-center">
              <p className="text-xs text-slate-500 mb-1">{y.year}</p>
              <div className="relative h-24 flex items-end justify-center">
                <div
                  className="w-full bg-gradient-to-t from-emerald-500/40 to-emerald-400/20 rounded-t-lg transition-all"
                  style={{ height: `${(y.cumulative / tenYearImpact) * 100}%` }}
                />
              </div>
              <p className="text-xs text-white font-medium mt-1">${y.cumulative.toFixed(0)}M</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
