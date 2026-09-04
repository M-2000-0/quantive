import React, { useState } from 'react';

interface Solver {
 id: string;
 name: string;
 type: string;
 description: string;
 icon: string;
 strengths: string[];
 weaknesses: string[];
}

interface MatchResult {
 solver1: string;
 solver2: string;
 winner: string;
 metrics: {
 objectiveValue: number;
 solveTime: number;
 iterations: number;
 convergence: number;
 };
}

interface TournamentResult {
 round: string;
 matches: MatchResult[];
 champion: string;
 finalMetrics: {
 solver: string;
 objectiveValue: number;
 solveTime: number;
 convergence: number;
 }[];
}

const SOLVERS: Solver[] = [
 { id: 'milp', name: 'MILP', type: 'Mixed-Integer Linear Programming', description: 'Exact solver for linear objectives with integer constraints', icon: '📐', strengths: ['Guaranteed optimal', 'Handles discrete choices', 'Well-understood'], weaknesses: ['Slow for large problems', 'Scale limits'] },
 { id: 'sa', name: 'Simulated Annealing', type: 'Metaheuristic', description: 'Probabilistic technique for approximating global optima', icon: '🌡️', strengths: ['Escapes local optima', 'Flexible', 'Parallelizable'], weaknesses: ['No optimality guarantee', 'Parameter sensitive'] },
 { id: 'qubo', name: 'QUBO', type: 'Quadratic Unconstrained Binary Optimization', description: 'Quantum-ready formulation for combinatorial problems', icon: '⚛️', strengths: ['Quantum-ready', 'Combinatorial power', 'Hardware加速'], weaknesses: ['Problem reformulation needed', 'Limited maturity'] },
 { id: 'ga', name: 'Genetic Algorithm', type: 'Evolutionary Computation', description: 'Population-based search inspired by natural selection', icon: '🧬', strengths: ['Parallel search', 'Multi-objective', 'No derivatives needed'], weaknesses: ['Slow convergence', 'Premature convergence risk'] },
 { id: 'pso', name: 'Particle Swarm', type: 'Swarm Intelligence', description: 'Population-based optimization inspired by social behavior', icon: '🐝', strengths: ['Simple implementation', 'Fast convergence', 'Few parameters'], weaknesses: ['Early convergence', 'Continuous domains only'] },
 { id: 'cp', name: 'Constraint Programming', type: 'Declarative Approach', description: 'Focuses on feasibility and constraint satisfaction', icon: '🧩', strengths: ['Handles complex constraints', 'Flexible modeling', 'Good for scheduling'], weaknesses: ['Objective handling weak', 'Less mature for optimization'] },
];

const BRACKET_ROUNDS = [
 { name: 'Quarterfinals', matches: [[0, 1], [2, 3], [4, 5]] },
 { name: 'Semifinals', matches: [['W0', 'W1'], ['W2', 'W3']] },
 { name: 'Final', matches: [['W4', 'W5']] },
];

export default function SolverTournament() {
 const [isRunning, setIsRunning] = useState(false);
 const [currentRound, setCurrentRound] = useState(0);
 const [results, setResults] = useState<TournamentResult[]>([]);
 const [champion, setChampion] = useState<string | null>(null);

 const runTournament = () => {
 setIsRunning(true);
 setResults([]);
 setChampion(null);
 setCurrentRound(0);

 // Simulate tournament progression
 const allResults: TournamentResult[] = [];
 
 // Quarterfinals
 setTimeout(() => {
 const qfMatches: MatchResult[] = [
 { solver1: 'MILP', solver2: 'Simulated Annealing', winner: 'MILP', metrics: { objectiveValue: 4.82, solveTime: 12.3, iterations: 1500, convergence: 99.8 } },
 { solver1: 'QUBO', solver2: 'Genetic Algorithm', winner: 'Genetic Algorithm', metrics: { objectiveValue: 4.71, solveTime: 8.7, iterations: 2200, convergence: 97.2 } },
 { solver1: 'Particle Swarm', solver2: 'Constraint Programming', winner: 'Constraint Programming', metrics: { objectiveValue: 4.65, solveTime: 6.2, iterations: 800, convergence: 95.1 } },
 ];
 allResults.push({ round: 'Quarterfinals', matches: qfMatches, champion: '', finalMetrics: [] });
 setResults([...allResults]);
 setCurrentRound(1);
 }, 2000);

 // Semifinals
 setTimeout(() => {
 const sfMatches: MatchResult[] = [
 { solver1: 'MILP', solver2: 'Genetic Algorithm', winner: 'MILP', metrics: { objectiveValue: 4.82, solveTime: 12.3, iterations: 1500, convergence: 99.8 } },
 { solver1: 'Constraint Programming', solver2: 'MILP', winner: 'MILP', metrics: { objectiveValue: 4.85, solveTime: 11.8, iterations: 1600, convergence: 99.9 } },
 ];
 allResults.push({ round: 'Semifinals', matches: sfMatches, champion: '', finalMetrics: [] });
 setResults([...allResults]);
 setCurrentRound(2);
 }, 4000);

 // Final
 setTimeout(() => {
 const finalMatch: MatchResult = {
 solver1: 'MILP', solver2: 'Genetic Algorithm', winner: 'MILP',
 metrics: { objectiveValue: 4.82, solveTime: 12.3, iterations: 1500, convergence: 99.8 }
 };
 allResults.push({
 round: 'Final',
 matches: [finalMatch],
 champion: 'MILP',
 finalMetrics: [
 { solver: 'MILP', objectiveValue: 4.82, solveTime: 12.3, convergence: 99.8 },
 { solver: 'Genetic Algorithm', objectiveValue: 4.71, solveTime: 8.7, convergence: 97.2 },
 { solver: 'Constraint Programming', objectiveValue: 4.65, solveTime: 6.2, convergence: 95.1 },
 { solver: 'Simulated Annealing', objectiveValue: 4.58, solveTime: 5.1, convergence: 93.5 },
 { solver: 'QUBO', objectiveValue: 4.52, solveTime: 15.8, convergence: 91.2 },
 { solver: 'Particle Swarm', objectiveValue: 4.48, solveTime: 4.3, convergence: 89.7 },
 ]
 });
 setResults([...allResults]);
 setChampion('MILP');
 setIsRunning(false);
 }, 6000);
 };

 return (
 <div className="space-y-6 animate-glass-in">
 <div className="flex items-center gap-3">
 <div className="w-10 h-10 bg-gradient-to-br from-red-500 to-orange-600 rounded-xl flex items-center justify-center">
 <span className="text-lg">🏆</span>
 </div>
 <div>
 <h2 className="text-xl font-bold text-white">Solver Tournament</h2>
 <p className="text-sm text-slate-400">Run all solvers head-to-head and find the champion</p>
 </div>
 </div>

 {/* Solver Roster */}
 <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
 {SOLVERS.map(s => (
 <div key={s.id} className="glass rounded-xl p-3">
 <div className="flex items-center gap-2 mb-2">
 <span className="text-lg">{s.icon}</span>
 <div>
 <h4 className="text-white text-sm font-medium">{s.name}</h4>
 <p className="text-xs text-slate-500">{s.type}</p>
 </div>
 </div>
 <p className="text-xs text-slate-400 mb-2">{s.description}</p>
 <div className="flex flex-wrap gap-1">
 {s.strengths.slice(0, 2).map((str, i) => (
 <span key={i} className="px-1.5 py-0.5 bg-green-500/10 text-green-400 rounded text-xs">{str}</span>
 ))}
 </div>
 </div>
 ))}
 </div>

 {/* Run Tournament Button */}
 {!champion && (
 <button
 onClick={runTournament}
 disabled={isRunning}
 className="w-full py-4 bg-gradient-to-r from-red-500 to-orange-600 rounded-2xl text-white font-bold text-lg hover:opacity-90 transition-opacity disabled:opacity-50"
 >
 {isRunning ? ' <RefreshCw className="w-4 h-4 inline" /> Tournament in Progress...' : '🏆 Start Tournament'}
 </button>
 )}

 {/* Tournament Bracket */}
 {results.length > 0 && (
 <div className="space-y-4">
 {results.map((round, ri) => (
 <div key={ri} className="glass rounded-2xl p-5">
 <h3 className="text-sm font-medium text-orange-400 mb-4 flex items-center gap-2">
 <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${
 round.round === 'Final' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-white/10 text-slate-400'
 }`}>
 {ri + 1}
 </span>
 {round.round}
 </h3>

 <div className="space-y-3">
 {round.matches.map((m, mi) => (
 <div key={mi} className="bg-white/5 rounded-xl p-3">
 <div className="flex items-center justify-between">
 <div className={`flex-1 text-center ${m.winner === m.solver1 ? 'text-white font-medium' : 'text-slate-500'}`}>
 {m.solver1}
 </div>
 <div className="px-4">
 <span className="text-xs text-slate-500">VS</span>
 </div>
 <div className={`flex-1 text-center ${m.winner === m.solver2 ? 'text-white font-medium' : 'text-slate-500'}`}>
 {m.solver2}
 </div>
 </div>
 <div className="flex justify-center mt-2">
 <span className="px-2 py-0.5 bg-green-500/20 text-green-400 rounded text-xs">
 🏆 {m.winner} wins (obj: {m.metrics.objectiveValue.toFixed(2)}, {m.metrics.solveTime}s)
 </span>
 </div>
 </div>
 ))}
 </div>
 </div>
 ))}
 </div>
 )}

 {/* Champion */}
 {champion && (
 <div className="glass rounded-2xl p-6 border-2 border-yellow-500/30 text-center">
 <div className="text-6xl mb-4">🏆</div>
 <h3 className="text-2xl font-bold text-white mb-2">Champion: {champion}</h3>
 <p className="text-slate-400 mb-4">Best objective value with guaranteed convergence</p>
 
 <div className="grid grid-cols-3 gap-4 max-w-md mx-auto mb-6">
 <div>
 <p className="text-2xl font-bold text-yellow-400">4.82</p>
 <p className="text-xs text-slate-500">Objective Value</p>
 </div>
 <div>
 <p className="text-2xl font-bold text-blue-400">12.3s</p>
 <p className="text-xs text-slate-500">Solve Time</p>
 </div>
 <div>
 <p className="text-2xl font-bold text-green-400">99.8%</p>
 <p className="text-xs text-slate-500">Convergence</p>
 </div>
 </div>

 {/* Final Rankings */}
 <div className="text-left max-w-lg mx-auto">
 <h4 className="text-sm font-medium text-slate-400 mb-3">Final Rankings</h4>
 {results[results.length - 1]?.finalMetrics.map((fm, i) => (
 <div key={i} className={`flex items-center gap-3 py-2 ${i === 0 ? 'text-white' : 'text-slate-400'}`}>
 <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
 i === 0 ? 'bg-yellow-500/20 text-yellow-400' :
 i === 1 ? 'bg-slate-500/20 text-slate-300' :
 i === 2 ? 'bg-orange-500/20 text-orange-400' :
 'bg-white/10 text-slate-500'
 }`}>
 {i + 1}
 </span>
 <span className="flex-1 text-sm">{fm.solver}</span>
 <span className="text-xs">Obj: {fm.objectiveValue.toFixed(2)}</span>
 <span className="text-xs">Time: {fm.solveTime}s</span>
 <span className="text-xs">Conv: {fm.convergence}%</span>
 </div>
 ))}
 </div>

 <button className="mt-6 px-6 py-3 bg-yellow-500/20 border border-yellow-500/30 rounded-xl text-yellow-400 font-medium hover:bg-yellow-500/30 transition-colors">
 Use Champion for Production →
 </button>
 </div>
 )}
 </div>
 );
}
