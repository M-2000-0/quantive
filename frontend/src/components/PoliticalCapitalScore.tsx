import React from 'react';

interface PoliticalFactor {
 name: string;
 score: number;
 description: string;
 icon: string;
}

const FACTORS: PoliticalFactor[] = [
 { name: 'Implementation Complexity', score: 72, description: 'Moderate complexity. Requires coordination across 3 ministries.', icon: '🔧' },
 { name: 'Stakeholder Impact', score: 65, description: 'Affects 12 government departments and 3 external agencies.', icon: 'Users' },
 { name: 'Legislative Requirements', score: 85, description: 'No new legislation required. Uses existing Treasury authority.', icon: '📜' },
 { name: 'Public Visibility', score: 45, description: 'High public visibility. Media attention likely on debt management.', icon: '📺' },
 { name: 'Opposition Risk', score: 78, description: 'Low opposition risk. Bipartisan support for fiscal responsibility.', icon: '🗳️' },
 { name: 'Implementation Timeline', score: 68, description: '6-9 months for full implementation. Quick wins available.', icon: '⏱️' },
];

export default function PoliticalCapitalScore() {
 const overallScore = Math.round(FACTORS.reduce((sum, f) => sum + f.score, 0) / FACTORS.length);

 return (
 <div className="glass rounded-2xl p-6">
 <div className="flex items-center justify-between mb-6">
 <div className="flex items-center gap-3">
 <span className="text-2xl">🗳️</span>
 <h3 className="text-lg font-bold text-white">Political Capital Score</h3>
 </div>
 <div className={`text-4xl font-bold ${overallScore >= 70 ? 'text-green-400' : overallScore >= 50 ? 'text-yellow-400' : 'text-red-400'}`}>
 {overallScore}/100
 </div>
 </div>

 <p className="text-sm text-slate-400 mb-4">
 Measures political feasibility of the proposed strategy. Some optimizations are mathematically great but politically impossible.
 </p>

 <div className="space-y-3">
 {FACTORS.map((factor, i) => (
 <div key={i} className="flex items-center gap-4 p-3 bg-white/5 rounded-xl">
 <span className="text-lg">{factor.icon}</span>
 <div className="flex-1">
 <div className="flex items-center justify-between mb-1">
 <span className="text-sm text-white font-medium">{factor.name}</span>
 <span className={`text-sm font-bold ${
 factor.score >= 70 ? 'text-green-400' :
 factor.score >= 50 ? 'text-yellow-400' : 'text-red-400'
 }`}>
 {factor.score}/100
 </span>
 </div>
 <div className="w-full bg-white/10 rounded-full h-2 mb-1">
 <div
 className={`h-2 rounded-full ${
 factor.score >= 70 ? 'bg-green-400' :
 factor.score >= 50 ? 'bg-yellow-400' : 'bg-red-400'
 }`}
 style={{ width: `${factor.score}%` }}
 />
 </div>
 <p className="text-xs text-slate-500">{factor.description}</p>
 </div>
 </div>
 ))}
 </div>

 <div className={`mt-4 p-4 rounded-xl ${
 overallScore >= 70 ? 'bg-green-500/10 border border-green-500/20' :
 overallScore >= 50 ? 'bg-yellow-500/10 border border-yellow-500/20' :
 'bg-red-500/10 border border-red-500/20'
 }`}>
 <p className={`text-sm ${overallScore >= 70 ? 'text-green-300' : overallScore >= 50 ? 'text-yellow-300' : 'text-red-300'}`}>
 {overallScore >= 70 ? ' <CheckCircle className="w-4 h-4 inline" /> Politically feasible. Recommend proceeding with Minister briefing.' :
 overallScore >= 50 ? ' <AlertTriangle className="w-4 h-4 inline" /> Moderate political risk. Consider stakeholder consultation before proceeding.' :
 '🛑 High political risk. Requires extensive coalition building and communication strategy.'}
 </p>
 </div>
 </div>
 );
}
