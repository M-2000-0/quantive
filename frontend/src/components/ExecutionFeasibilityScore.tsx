import React from 'react';
import { Rocket } from 'lucide-react';

interface FeasibilityFactor {
  name: string;
  score: number;
  description: string;
  details: string;
}

const FACTORS: FeasibilityFactor[] = [
  { name: 'Market Capacity', score: 85, description: 'Deep market with strong demand', details: 'Current market can absorb $5B+ in single issuance. Recent comparable deals fully allocated.' },
  { name: 'Investor Demand', score: 78, description: 'Strong demand from institutional investors', details: '2.3x oversubscription on last 3 issuances. Strong bid from Asian and European accounts.' },
  { name: 'Auction Feasibility', score: 92, description: 'Excellent auction conditions', details: 'Competitive bidding expected. No competing sovereign issuances in window.' },
  { name: 'Regulatory Compliance', score: 95, description: 'Full compliance with all requirements', details: 'Meets IMF guidelines, domestic debt management office policies, and ESG frameworks.' },
  { name: 'Operational Readiness', score: 70, description: 'Moderate operational complexity', details: 'Requires coordination with 3 international banks. Settlement timeline: T+2.' },
  { name: 'Timing Window', score: 65, description: 'Acceptable timing, some uncertainty', details: 'Central bank meeting in 2 weeks may affect rates. Recommend pre-meeting execution.' },
];

export default function ExecutionFeasibilityScore() {
  const overallScore = Math.round(FACTORS.reduce((sum, f) => sum + f.score, 0) / FACTORS.length);

  return (
    <div className="glass rounded-2xl p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Rocket className="w-5 h-5" />
          <h3 className="text-lg font-bold text-white">Execution Feasibility Score</h3>
        </div>
        <div className={`text-4xl font-bold ${overallScore >= 75 ? 'text-green-400' : overallScore >= 55 ? 'text-yellow-400' : 'text-red-400'}`}>
          {overallScore}/100
        </div>
      </div>

      <p className="text-sm text-slate-400 mb-4">
        Many models produce solutions that cannot actually be issued. This score measures real-world execution feasibility.
      </p>

      <div className="grid grid-cols-2 gap-4">
        {FACTORS.map((factor, i) => (
          <div key={i} className="bg-white/5 rounded-xl p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-white font-medium">{factor.name}</span>
              <span className={`text-lg font-bold ${
                factor.score >= 75 ? 'text-green-400' :
                factor.score >= 55 ? 'text-yellow-400' : 'text-red-400'
              }`}>
                {factor.score}
              </span>
            </div>
            <div className="w-full bg-white/10 rounded-full h-2 mb-2">
              <div
                className={`h-2 rounded-full ${
                  factor.score >= 75 ? 'bg-green-400' :
                  factor.score >= 55 ? 'bg-yellow-400' : 'bg-red-400'
                }`}
                style={{ width: `${factor.score}%` }}
              />
            </div>
            <p className="text-xs text-slate-400 mb-1">{factor.description}</p>
            <p className="text-xs text-slate-500">{factor.details}</p>
          </div>
        ))}
      </div>

      {/* Optimization vs Feasibility Comparison */}
      <div className="mt-4 grid grid-cols-2 gap-4">
        <div className="bg-emerald-500/10 rounded-xl p-4 text-center">
          <p className="text-sm text-slate-400 mb-1">Optimization Score</p>
          <p className="text-3xl font-bold text-emerald-400">97/100</p>
          <p className="text-xs text-slate-500 mt-1">Mathematically optimal</p>
        </div>
        <div className={`rounded-xl p-4 text-center ${
          overallScore >= 75 ? 'bg-green-500/10' :
          overallScore >= 55 ? 'bg-yellow-500/10' : 'bg-red-500/10'
        }`}>
          <p className="text-sm text-slate-400 mb-1">Execution Feasibility</p>
          <p className={`text-3xl font-bold ${overallScore >= 75 ? 'text-green-400' : overallScore >= 55 ? 'text-yellow-400' : 'text-red-400'}`}>
            {overallScore}/100
          </p>
          <p className="text-xs text-slate-500 mt-1">Real-world executable</p>
        </div>
      </div>
    </div>
  );
}
