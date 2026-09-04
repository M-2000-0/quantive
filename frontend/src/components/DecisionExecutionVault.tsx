import React, { useState } from 'react';
import { Landmark } from 'lucide-react';

interface DecisionPackage {
 id: string;
 title: string;
 date: string;
 status: 'active' | 'archived' | 'disputed';
 hash: string;
 totalSavings: string;
 approvers: { name: string; role: string; timestamp: string; certificate: string }[];
 assumptions: string[];
 alternativesConsidered: string[];
 risks: string[];
 optimizationResults: { metric: string; before: string; after: string; improvement: string }[];
}

const DECISIONS: DecisionPackage[] = [
 {
 id: 'dp-001',
 title: '$2.4B 2027 Maturity Refinancing',
 date: '2026-08-24',
 status: 'active',
 hash: '0xa3f2c8d1e5b4f6a7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1',
 totalSavings: '$180M annually',
 approvers: [
 { name: 'Sarah Chen', role: 'Senior Analyst', timestamp: '2026-08-24T09:00:00Z', certificate: 'GOV-CERT-7842' },
 { name: 'James Morrison', role: 'Manager', timestamp: '2026-08-24T09:15:00Z', certificate: 'GOV-CERT-5523' },
 { name: 'Dr. Amara Okafor', role: 'Director', timestamp: '2026-08-24T10:00:00Z', certificate: 'GOV-CERT-3291' },
 ],
 assumptions: ['Interest rates remain at 4.0-4.5%', 'No credit rating change', 'Market conditions stable'],
 alternativesConsidered: ['Lump-sum issuance ($2.4B 10Y)', 'Green bond framework ($800M green + $1.6B conventional)'],
 risks: ['Rates may rise 50bps', 'Spread widening possible'],
 optimizationResults: [
 { metric: 'Debt Service Cost', before: '$4.2B', after: '$4.02B', improvement: '-$180M' },
 { metric: 'Average Maturity', before: '4.2 yrs', after: '5.8 yrs', improvement: '+38%' },
 { metric: 'Refinancing Risk', before: '32%', after: '22%', improvement: '-31%' },
 ] },
 {
 id: 'dp-002',
 title: 'Emergency $800M T-Bill Issuance',
 date: '2026-08-23',
 status: 'archived',
 hash: '0xb4e3d2c1a5f6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2',
 totalSavings: 'Liquidity preserved',
 approvers: [
 { name: 'Emergency Duty Officer', role: 'Analyst', timestamp: '2026-08-23T02:15:00Z', certificate: 'GOV-CERT-9901' },
 { name: 'Night Shift Director', role: 'Director', timestamp: '2026-08-23T02:30:00Z', certificate: 'GOV-CERT-9902' },
 { name: 'Dr. Amara Okafor', role: 'Director', timestamp: '2026-08-23T06:00:00Z', certificate: 'GOV-CERT-3291' },
 { name: 'Minister Office', role: 'Minister', timestamp: '2026-08-23T10:00:00Z', certificate: 'GOV-CERT-0001' },
 ],
 assumptions: ['Emergency protocol activated', 'Liquidity below 15% threshold'],
 alternativesConsidered: ['Draw from reserve fund', 'Request IMF standby'],
 risks: ['Emergency rate premium', 'Reputational risk'],
 optimizationResults: [
 { metric: 'Liquidity Buffer', before: '12.3%', after: '18.5%', improvement: '+6.2pp' },
 ] },
];

export default function DecisionExecutionVault() {
 const [decisions] = useState(DECISIONS);
 const [selected, setSelected] = useState<DecisionPackage | null>(null);

 return (
 <div className="space-y-6 animate-glass-in">
 <div className="flex items-center gap-3">
 <div className="w-10 h-10 bg-gradient-to-br from-slate-500 to-gray-600 rounded-xl flex items-center justify-center">
 <Landmark className="w-5 h-5" />
 </div>
 <div>
 <h2 className="text-xl font-bold text-white">Decision Execution Vault</h2>
 <p className="text-sm text-slate-400">Every decision package — hash, signatures, assumptions, alternatives</p>
 </div>
 </div>

 <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
 {/* Decision List */}
 <div className="space-y-3">
 {decisions.map(d => (
 <button
 key={d.id}
 onClick={() => setSelected(d)}
 className={`w-full text-left glass rounded-xl p-4 transition-all ${
 selected?.id === d.id ? 'ring-2 ring-slate-500/50' : 'hover:bg-white/5'
 }`}
 >
 <div className="flex items-center justify-between mb-2">
 <span className={`px-2 py-0.5 rounded text-xs font-medium ${
 d.status === 'active' ? 'bg-green-500/20 text-green-400' :
 d.status === 'archived' ? 'bg-slate-500/20 text-slate-400' :
 'bg-red-500/20 text-red-400'
 }`}>
 {d.status}
 </span>
 <span className="text-xs text-slate-500">{d.date}</span>
 </div>
 <h4 className="text-white text-sm font-medium mb-1">{d.title}</h4>
 <p className="text-xs text-slate-400">{d.totalSavings}</p>
 <p className="text-xs text-green-400 font-mono mt-1 truncate">Hash: {d.hash.slice(0, 18)}...</p>
 </button>
 ))}
 </div>

 {/* Detail Panel */}
 <div className="lg:col-span-2">
 {selected ? (
 <div className="glass rounded-2xl p-6 space-y-5">
 <div className="flex items-start justify-between">
 <div>
 <h3 className="text-lg font-bold text-white">{selected.title}</h3>
 <p className="text-sm text-slate-400">{selected.date} • {selected.totalSavings}</p>
 </div>
 <span className="px-3 py-1 bg-slate-500/20 text-slate-400 rounded-lg text-xs font-mono">
 {selected.hash.slice(0, 24)}...
 </span>
 </div>

 {/* Approver Chain */}
 <div>
 <h4 className="text-xs font-medium text-slate-500 mb-3">APPROVER CHAIN</h4>
 <div className="space-y-2">
 {selected.approvers.map((a, i) => (
 <div key={i} className="flex items-center gap-3 p-3 bg-green-500/5 rounded-xl border border-green-500/10">
 <span className="w-6 h-6 bg-green-500/20 text-green-400 rounded-full flex items-center justify-center text-xs font-bold">
 {i + 1}
 </span>
 <div className="flex-1">
 <p className="text-sm text-white font-medium">{a.name}</p>
 <p className="text-xs text-slate-500">{a.role}</p>
 </div>
 <div className="text-right text-xs">
 <p className="text-green-400"> <Lock className="w-4 h-4 inline" /> {a.certificate}</p>
 <p className="text-slate-500">{a.timestamp.split('T')[1].slice(0, 5)}</p>
 </div>
 </div>
 ))}
 </div>
 </div>

 {/* Assumptions */}
 <div>
 <h4 className="text-xs font-medium text-slate-500 mb-2">ASSUMPTIONS</h4>
 <div className="flex flex-wrap gap-2">
 {selected.assumptions.map((a, i) => (
 <span key={i} className="px-2 py-1 bg-white/5 rounded text-xs text-slate-300">{a}</span>
 ))}
 </div>
 </div>

 {/* Alternatives */}
 <div>
 <h4 className="text-xs font-medium text-slate-500 mb-2">ALTERNATIVES CONSIDERED</h4>
 <div className="space-y-1">
 {selected.alternativesConsidered.map((a, i) => (
 <p key={i} className="text-sm text-slate-300">• {a}</p>
 ))}
 </div>
 </div>

 {/* Optimization Results */}
 <div>
 <h4 className="text-xs font-medium text-slate-500 mb-2">OPTIMIZATION RESULTS</h4>
 <div className="space-y-2">
 {selected.optimizationResults.map((r, i) => (
 <div key={i} className="flex items-center gap-4 p-3 bg-white/5 rounded-xl text-sm">
 <span className="text-white flex-1">{r.metric}</span>
 <span className="text-slate-400">{r.before}</span>
 <span className="text-slate-500">→</span>
 <span className="text-white font-medium">{r.after}</span>
 <span className="text-green-400 font-medium">{r.improvement}</span>
 </div>
 ))}
 </div>
 </div>

 {/* Immutable Record */}
 <div className="p-4 bg-slate-500/10 border border-slate-500/20 rounded-xl">
 <p className="text-sm text-slate-300">
 <Lock className="w-4 h-4 inline" /> <strong>Immutable Record:</strong> This decision package is cryptographically signed and stored in the execution vault. An auditor can verify at any time: Who approved this, why it was approved, what data was used, and what alternatives existed.
 </p>
 </div>
 </div>
 ) : (
 <div className="glass rounded-2xl p-12 text-center">
 <div className="text-4xl mb-4"> <Landmark className="w-4 h-4 inline" /> </div>
 <h3 className="text-white font-bold mb-2">Select a Decision Package</h3>
 <p className="text-sm text-slate-400">Click any decision to view its complete audit trail and immutable record</p>
 </div>
 )}
 </div>
 </div>
 </div>
 );
}
