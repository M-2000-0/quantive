import React, { useState } from 'react';

interface RatingAgency {
  name: string;
  logo: string;
  currentRating: string;
  outlook: string;
  currentProbability: number;
  postOptimizationProbability: number;
  factors: { name: string; score: number; weight: number }[];
}

const AGENCIES: RatingAgency[] = [
  {
    name: "Moody's",
    logo: 'Building2',
    currentRating: 'Baa2',
    outlook: 'Stable',
    currentProbability: 18,
    postOptimizationProbability: 6,
    factors: [
      { name: 'Institutional Strength', score: 65, weight: 20 },
      { name: 'Economic Strength', score: 58, weight: 20 },
      { name: 'Fiscal Strength', score: 42, weight: 20 },
      { name: 'Susceptibility to Event Risk', score: 55, weight: 20 },
      { name: 'Debt Affordability', score: 68, weight: 20 },
    ] },
  {
    name: 'S&P',
    logo: 'BarChart3',
    currentRating: 'BBB+',
    outlook: 'Negative',
    currentProbability: 22,
    postOptimizationProbability: 8,
    factors: [
      { name: 'Institutional Assessment', score: 60, weight: 25 },
      { name: 'Economic Assessment', score: 55, weight: 25 },
      { name: 'External Assessment', score: 50, weight: 25 },
      { name: 'Fiscal Assessment', score: 38, weight: 25 },
    ] },
  {
    name: 'Fitch',
    logo: '⭐',
    currentRating: 'BBB+',
    outlook: 'Stable',
    currentProbability: 15,
    postOptimizationProbability: 5,
    factors: [
      { name: 'Structural Features', score: 62, weight: 15 },
      { name: 'Macro Performance', score: 58, weight: 20 },
      { name: 'Public Finance', score: 45, weight: 25 },
      { name: 'Debt Profile', score: 50, weight: 25 },
      { name: 'External Finance', score: 55, weight: 15 },
    ] },
];

export default function RatingAgencySimulator() {
  const [selectedAgency, setSelectedAgency] = useState(AGENCIES[0]);

  return (
    <div className="space-y-6 animate-glass-in">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-gradient-to-br from-amber-500 to-yellow-600 rounded-xl flex items-center justify-center">
          <span className="text-lg">⭐</span>
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">Rating Agency Simulator</h2>
          <p className="text-sm text-slate-400">Estimate rating impact from Moody's, S&P, and Fitch</p>
        </div>
      </div>

      {/* Agency Selector */}
      <div className="grid grid-cols-3 gap-4">
        {AGENCIES.map(agency => (
          <button
            key={agency.name}
            onClick={() => setSelectedAgency(agency)}
            className={`text-left p-5 rounded-2xl border transition-all ${
              selectedAgency.name === agency.name
                ? 'bg-amber-500/10 border-amber-500/30'
                : 'bg-white/5 border-white/10 hover:bg-white/10'
            }`}
          >
            <div className="flex items-center gap-3 mb-3">
              <span className="text-2xl">{agency.logo}</span>
              <div>
                <h4 className="text-white font-bold">{agency.name}</h4>
                <p className="text-xs text-slate-400">Rating: {agency.currentRating}</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <p className="text-xs text-slate-500">Current Risk</p>
                <p className={`text-lg font-bold ${agency.currentProbability >= 20 ? 'text-red-400' : 'text-yellow-400'}`}>
                  {agency.currentProbability}%
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Post-Optimization</p>
                <p className="text-lg font-bold text-green-400">
                  {agency.postOptimizationProbability}%
                </p>
              </div>
            </div>
            <div className="mt-3">
              <p className="text-xs text-slate-500 mb-1">Outlook: <span className={`${
                agency.outlook === 'Stable' ? 'text-green-400' :
                agency.outlook === 'Negative' ? 'text-red-400' : 'text-yellow-400'
              }`}>{agency.outlook}</span></p>
            </div>
          </button>
        ))}
      </div>

      {/* Detailed View */}
      <div className="glass rounded-2xl p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <span className="text-3xl">{selectedAgency.logo}</span>
            <div>
              <h3 className="text-lg font-bold text-white">{selectedAgency.name}</h3>
              <p className="text-sm text-slate-400">Current Rating: {selectedAgency.currentRating} ({selectedAgency.outlook})</p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-sm text-slate-400">Downgrade Probability</p>
            <div className="flex items-center gap-3">
              <span className="text-xl font-bold text-red-400">{selectedAgency.currentProbability}%</span>
              <span className="text-slate-500">→</span>
              <span className="text-xl font-bold text-green-400">{selectedAgency.postOptimizationProbability}%</span>
            </div>
            <p className="text-xs text-green-400">-{selectedAgency.currentProbability - selectedAgency.postOptimizationProbability}pp reduction</p>
          </div>
        </div>

        {/* Factor Scores */}
        <h4 className="text-sm font-medium text-slate-400 mb-4">RATING FACTORS</h4>
        <div className="space-y-3">
          {selectedAgency.factors.map((factor, i) => (
            <div key={i} className="flex items-center gap-4">
              <span className="text-sm text-white w-48">{factor.name}</span>
              <div className="flex-1 bg-white/5 rounded-full h-3">
                <div
                  className={`h-3 rounded-full ${
                    factor.score >= 65 ? 'bg-green-400' :
                    factor.score >= 50 ? 'bg-yellow-400' :
                    factor.score >= 35 ? 'bg-orange-400' : 'bg-red-400'
                  }`}
                  style={{ width: `${factor.score}%` }}
                />
              </div>
              <span className="text-sm font-medium text-white w-12 text-right">{factor.score}</span>
              <span className="text-xs text-slate-500 w-16 text-right">Wt: {factor.weight}%</span>
            </div>
          ))}
        </div>

        {/* Rating Improvement Impact */}
        <div className="mt-6 grid grid-cols-3 gap-4">
          <div className="bg-green-500/10 rounded-xl p-4 text-center">
            <p className="text-3xl font-bold text-green-400">
              -{selectedAgency.currentProbability - selectedAgency.postOptimizationProbability}pp
            </p>
            <p className="text-xs text-slate-400 mt-1">Downgrade Risk Reduction</p>
          </div>
          <div className="bg-blue-500/10 rounded-xl p-4 text-center">
            <p className="text-3xl font-bold text-blue-400">$180M</p>
            <p className="text-xs text-slate-400 mt-1">Est. Annual Spread Savings</p>
          </div>
          <div className="bg-purple-500/10 rounded-xl p-4 text-center">
            <p className="text-3xl font-bold text-purple-400">A- to A</p>
            <p className="text-xs text-slate-400 mt-1">Potential Upgrade Path</p>
          </div>
        </div>
      </div>
    </div>
  );
}
