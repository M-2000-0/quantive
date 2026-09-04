import React from 'react';
import { FileText, PencilLine, Target, TriangleAlert as AlertTriangle } from 'lucide-react';

export default function MinisterHandover() {
 return (
 <div className="space-y-6 animate-glass-in">
 <div className="flex items-center gap-3">
 <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-violet-600 rounded-xl flex items-center justify-center">
 <FileText className="w-5 h-5" />
 </div>
 <div>
 <h2 className="text-xl font-bold text-white">Executive Handover Brief</h2>
 <p className="text-sm text-slate-400">Automatic briefing when a minister arrives or departs</p>
 </div>
 </div>

 {/* Handover Document */}
 <div className="glass rounded-2xl p-6 space-y-6">
 <div className="border-b border-white/10 pb-4">
 <h3 className="text-lg font-bold text-white mb-1">Minister of Finance — Executive Handover</h3>
 <p className="text-sm text-slate-400">Generated: August 24, 2026 • Classification: CONFIDENTIAL</p>
 </div>

 {/* Current Risks */}
 <div>
 <h4 className="text-sm font-medium text-red-400 mb-3"> <AlertTriangle className="w-4 h-4 inline" /> CURRENT RISKS</h4>
 <div className="space-y-2">
 {[
 { risk: 'Liquidity buffer at 14.2% (below 15% target)', severity: 'high' },
 { risk: 'FX exposure at 41% (above recommended 25%)', severity: 'high' },
 { risk: '2027 maturity wall: $3.2B due', severity: 'medium' },
 { risk: 'Rating agency review in Q4 2026', severity: 'medium' },
 ].map((r, i) => (
 <div key={i} className={`flex items-center gap-3 p-3 rounded-xl ${r.severity === 'high' ? 'bg-red-500/10' : 'bg-yellow-500/10'}`}>
 <span className={`w-2 h-2 rounded-full ${r.severity === 'high' ? 'bg-red-400' : 'bg-yellow-400'}`} />
 <p className="text-sm text-white">{r.risk}</p>
 </div>
 ))}
 </div>
 </div>

 {/* Upcoming Maturities */}
 <div>
 <h4 className="text-sm font-medium text-amber-400 mb-3">📅 UPCOMING MATURITIES</h4>
 <div className="space-y-2">
 {[
 { date: 'Q1 2027', amount: '$3.2B', type: 'Sovereign Bond', status: 'Refinancing planned' },
 { date: 'Q3 2027', amount: '$1.8B', type: 'T-Bill', status: 'Rolling' },
 { date: 'Q1 2028', amount: '$2.1B', type: 'Sovereign Bond', status: 'Strategy pending' },
 ].map((m, i) => (
 <div key={i} className="flex items-center gap-4 p-3 bg-white/5 rounded-xl text-sm">
 <span className="text-white font-medium w-20">{m.date}</span>
 <span className="text-white w-20">{m.amount}</span>
 <span className="text-slate-400 flex-1">{m.type}</span>
 <span className="text-xs text-slate-500">{m.status}</span>
 </div>
 ))}
 </div>
 </div>

 {/* Active Strategies */}
 <div>
 <h4 className="text-sm font-medium text-green-400 mb-3"> <Target className="w-4 h-4 inline" /> ACTIVE STRATEGIES</h4>
 <div className="space-y-2">
 {[
 { name: 'Staggered 2027 Refinancing', savings: '$180M/yr', status: 'In progress' },
 { name: '60% FX Hedge Program', savings: '$85M/yr', status: 'Active' },
 { name: 'Green Bond Framework Update', savings: 'ESG compliance', status: 'Awaiting approval' },
 ].map((s, i) => (
 <div key={i} className="flex items-center gap-4 p-3 bg-white/5 rounded-xl text-sm">
 <span className="text-white font-medium flex-1">{s.name}</span>
 <span className="text-green-400">{s.savings}</span>
 <span className="text-xs text-slate-500">{s.status}</span>
 </div>
 ))}
 </div>
 </div>

 {/* Key Assumptions */}
 <div>
 <h4 className="text-sm font-medium text-blue-400 mb-3"> <PencilLine className="w-4 h-4 inline" /> KEY ASSUMPTIONS</h4>
 <div className="space-y-1">
 {[
 'Interest rates remain 4.0-4.5% through 2027',
 'No credit rating change expected',
 'IMF program on track for Q4 review',
 'Political stability maintained through election',
 ].map((a, i) => (
 <p key={i} className="text-sm text-slate-300">• {a}</p>
 ))}
 </div>
 </div>

 {/* Unresolved Issues */}
 <div>
 <h4 className="text-sm font-medium text-purple-400 mb-3">❓ UNRESOLVED ISSUES</h4>
 <div className="space-y-2">
 {[
 { issue: 'Counterparty concentration in Deutsche Bank', urgency: 'High', owner: 'Risk Team' },
 { issue: 'ESG framework update pending Minister sign-off', urgency: 'Medium', owner: 'Policy Team' },
 ].map((u, i) => (
 <div key={i} className="flex items-center gap-4 p-3 bg-white/5 rounded-xl text-sm">
 <span className="text-white flex-1">{u.issue}</span>
 <span className={`px-2 py-0.5 rounded text-xs ${u.urgency === 'High' ? 'bg-red-500/20 text-red-400' : 'bg-yellow-500/20 text-yellow-400'}`}>{u.urgency}</span>
 <span className="text-xs text-slate-500">{u.owner}</span>
 </div>
 ))}
 </div>
 </div>

 <div className="p-4 bg-indigo-500/10 border border-indigo-500/20 rounded-xl">
 <p className="text-sm text-indigo-300"> <FileText className="w-4 h-4 inline" /> <strong>Handover Protection:</strong> This brief is auto-generated from the institutional memory system. It ensures no critical context is lost during ministerial transitions.</p>
 </div>
 </div>
 </div>
 );
}
