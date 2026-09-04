import React, { useState } from 'react';

interface PoliticalFactor {
  name: string;
  score: number;
  weight: number;
  description: string;
  icon: string;
}

interface PoliticalStrategy {
  name: string;
  savings: number;
  factors: PoliticalFactor[];
  overallScore: number;
  recommendation: string;
}

const STRATEGIES: PoliticalStrategy[] = [
  {
    name: 'Staggered Issuance',
    savings: 400,
    factors: [
      { name: 'Public Resistance', score: 85, weight: 25, description: 'Low visibility. Technical decision.', icon: 'Users' },
      { name: 'Legislative Complexity', score: 90, weight: 20, description: 'No legislation required.', icon: '📜' },
      { name: 'Election Timing', score: 75, weight: 20, description: '18 months to next election.', icon: '🗳️' },
      { name: 'Stakeholder Opposition', score: 80, weight: 20, description: 'Banks support. Opposition neutral.', icon: '🤝' },
      { name: 'Bureaucratic Feasibility', score: 85, weight: 15, description: 'Standard treasury process.', icon: 'Settings' },
    ],
    overallScore: 83,
    recommendation: 'Politically feasible. Proceed with standard approval chain.' },
  {
    name: 'Austerity Program',
    savings: 800,
    factors: [
      { name: 'Public Resistance', score: 15, weight: 25, description: 'Extreme public opposition expected.', icon: 'Users' },
      { name: 'Legislative Complexity', score: 25, weight: 20, description: 'Requires parliamentary approval.', icon: '📜' },
      { name: 'Election Timing', score: 10, weight: 20, description: '18 months to election. Political suicide.', icon: '🗳️' },
      { name: 'Stakeholder Opposition', score: 20, weight: 20, description: 'Unions, civil society strongly opposed.', icon: '🤝' },
      { name: 'Bureaucratic Feasibility', score: 60, weight: 15, description: 'Complex implementation.', icon: 'Settings' },
    ],
    overallScore: 25,
    recommendation: 'Politically impossible. Mathematically optimal but implementation probability: 0%.' },
  {
    name: 'Green Bond Pivot',
    savings: 180,
    factors: [
      { name: 'Public Resistance', score: 90, weight: 25, description: 'Positive public narrative.', icon: 'Users' },
      { name: 'Legislative Complexity', score: 85, weight: 20, description: 'Framework update only.', icon: '📜' },
      { name: 'Election Timing', score: 95, weight: 20, description: 'Strong ESG story for elections.', icon: '🗳️' },
      { name: 'Stakeholder Opposition', score: 88, weight: 20, description: 'ESG investors support.', icon: '🤝' },
      { name: 'Bureaucratic Feasibility', score: 80, weight: 15, description: 'Moderate complexity.', icon: 'Settings' },
    ],
    overallScore: 89,
    recommendation: 'Highly recommended. Strong political upside with ESG narrative.' },
];

export default function PoliticalFeasibility() {
  const [selected, setSelected] = useState(STRATEGIES[0]);

  return (
    <div className="space-y-6 animate-glass-in">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-gradient-to-br from-amber-500 to-orange-600 rounded-xl flex items-center justify-center">
          <span className="text-lg">🗳️</span>
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">Political Feasibility Engine</h2>
          <p className="text-sm text-slate-400">Mathematics × Politics × Public Opinion × Elections</p>
        </div>
      </div>

      {/* Strategy Cards */}
      <div className="grid grid-cols-3 gap-4">
        {STRATEGIES.map((s, i) => (
          <button key={i} onClick={() => setSelected(s)} className={`text-left p-5 rounded-2xl border transition-all ${selected.name === s.name ? 'bg-amber-500/10 border-amber-500/30' : 'bg-white/5 border-white/10 hover:bg-white/10'}`}>
            <div className="flex items-center justify-between mb-3">
              <span className="text-3xl font-bold ${s.overallScore >= 70 ? 'text-green-400' : s.overallScore >= 40 ? 'text-yellow-400' : 'text-red-400'}">{s.overallScore}</span>
              <span className="text-xs text-slate-400">${s.savings}M savings</span>
            </div>
            <h4 className="text-white font-medium mb-2">{s.name}</h4>
            <p className="text-xs text-slate-400">{s.recommendation}</p>
          </button>
        ))}
      </div>

      {/* Detail */}
      <div className="glass rounded-2xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-bold text-white">{selected.name}</h3>
          <span className={`text-4xl font-bold ${selected.overallScore >= 70 ? 'text-green-400' : selected.overallScore >= 40 ? 'text-yellow-400' : 'text-red-400'}`}>{selected.overallScore}/100</span>
        </div>

        <div className="space-y-3">
          {selected.factors.map((f, i) => (
            <div key={i} className="flex items-center gap-4 p-3 bg-white/5 rounded-xl">
              <span className="text-lg">{f.icon}</span>
              <div className="flex-1">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-white">{f.name}</span>
                  <span className={`text-sm font-bold ${f.score >= 70 ? 'text-green-400' : f.score >= 40 ? 'text-yellow-400' : 'text-red-400'}`}>{f.score}/100</span>
                </div>
                <div className="w-full bg-white/10 rounded-full h-2 mb-1">
                  <div className={`h-2 rounded-full ${f.score >= 70 ? 'bg-green-400' : f.score >= 40 ? 'bg-yellow-400' : 'bg-red-400'}`} style={{ width: `${f.score}%` }} />
                </div>
                <p className="text-xs text-slate-500">{f.description}</p>
              </div>
              <span className="text-xs text-slate-500">Wt: {f.weight}%</span>
            </div>
          ))}
        </div>

        <div className={`p-4 rounded-xl ${selected.overallScore >= 70 ? 'bg-green-500/10 border border-green-500/20' : selected.overallScore >= 40 ? 'bg-yellow-500/10 border border-yellow-500/20' : 'bg-red-500/10 border border-red-500/20'}`}>
          <p className={`text-sm ${selected.overallScore >= 70 ? 'text-green-300' : selected.overallScore >= 40 ? 'text-yellow-300' : 'text-red-300'}`}>{selected.recommendation}</p>
        </div>
      </div>
    </div>
  );
}
