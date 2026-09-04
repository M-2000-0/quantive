import React, { useState } from 'react';
import { FileText, Scale } from 'lucide-react';

interface EvidencePackage {
 id: string;
 decision: string;
 date: string;
 hashChain: string;
 approvers: string[];
 dataSnapshots: string[];
 assumptions: string[];
 alternatives: string[];
 verificationStatus: 'verified' | 'pending';
 retentionPeriod: string;
}

const PACKAGES: EvidencePackage[] = [
 {
 id: 'ev-001',
 decision: '$2.4B 2027 Maturity Refinancing',
 date: '2026-08-24',
 hashChain: '0xa3f2c8...9a0b1',
 approvers: ['Sarah Chen', 'James Morrison', 'Dr. Amara Okafor'],
 dataSnapshots: ['Market rates at time of decision', 'Portfolio composition', 'Risk analysis output'],
 assumptions: ['Interest rate forecast: 4.0-4.5%', 'No rating change expected', 'Market stability assumed'],
 alternatives: ['Lump-sum 10Y issuance', 'Green bond framework', 'Conservative hold'],
 verificationStatus: 'verified',
 retentionPeriod: '25 years' },
 {
 id: 'ev-002',
 decision: 'Emergency $800M T-Bill Issuance',
 date: '2026-08-23',
 hashChain: '0xb4e3d2...a0b1c2',
 approvers: ['Emergency Duty Officer', 'Night Shift Director', 'Dr. Amara Okafor', 'Minister Office'],
 dataSnapshots: ['Liquidity snapshot at crisis moment', 'Market conditions', 'Emergency protocol activation'],
 assumptions: ['Emergency protocol triggered', 'Liquidity below 15% threshold'],
 alternatives: ['Draw from reserve fund', 'Request IMF standby'],
 verificationStatus: 'verified',
 retentionPeriod: '25 years' },
];

export default function LegalChainOfEvidence() {
 const [selected, setSelected] = useState<EvidencePackage | null>(null);

 return (
 <div className="space-y-6 animate-glass-in">
 <div className="flex items-center gap-3">
 <div className="w-10 h-10 bg-gradient-to-br from-slate-600 to-gray-700 rounded-xl flex items-center justify-center">
 <Scale className="w-5 h-5" />
 </div>
 <div>
 <h2 className="text-xl font-bold text-white">Legal Chain of Evidence</h2>
 <p className="text-sm text-slate-400">Cryptographic proof for parliamentary investigations and audits</p>
 </div>
 </div>

 {/* Retention Guarantee */}
 <div className="glass rounded-2xl p-5 border-l-4 border-slate-500">
 <div className="flex items-center gap-3 mb-3">
 <span className="text-2xl">📜</span>
 <div>
 <h3 className="text-white font-medium">25-Year Retention Guarantee</h3>
 <p className="text-sm text-slate-400">All decision packages retained with cryptographic integrity for 25 years</p>
 </div>
 </div>
 <div className="grid grid-cols-4 gap-4 text-center">
 <div>
 <p className="text-2xl font-bold text-white">{PACKAGES.length}</p>
 <p className="text-xs text-slate-500">Evidence Packages</p>
 </div>
 <div>
 <p className="text-2xl font-bold text-green-400">100%</p>
 <p className="text-xs text-slate-500">Verification Rate</p>
 </div>
 <div>
 <p className="text-2xl font-bold text-white">25yr</p>
 <p className="text-xs text-slate-500">Retention Period</p>
 </div>
 <div>
 <p className="text-2xl font-bold text-white">SHA-256</p>
 <p className="text-xs text-slate-500">Hash Algorithm</p>
 </div>
 </div>
 </div>

 {/* Evidence List */}
 <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
 <div className="space-y-3">
 {PACKAGES.map(p => (
 <button key={p.id} onClick={() => setSelected(p)} className={`w-full text-left glass rounded-xl p-4 transition-all ${selected?.id === p.id ? 'ring-2 ring-slate-500/50' : 'hover:bg-white/5'}`}>
 <div className="flex items-center justify-between mb-2">
 <span className="text-xs text-slate-500">{p.date}</span>
 <span className="px-2 py-0.5 bg-green-500/20 text-green-400 rounded text-xs">✓ Verified</span>
 </div>
 <h4 className="text-white text-sm font-medium">{p.decision}</h4>
 <p className="text-xs text-slate-400 mt-1">Approvers: {p.approvers.length}</p>
 <p className="text-xs text-green-400 font-mono mt-1">Hash: {p.hashChain}</p>
 </button>
 ))}
 </div>

 <div className="lg:col-span-2">
 {selected ? (
 <div className="glass rounded-2xl p-6 space-y-5">
 <h3 className="text-lg font-bold text-white">{selected.decision}</h3>

 {/* Hash Chain */}
 <div className="bg-white/5 rounded-xl p-4">
 <h4 className="text-xs font-medium text-slate-500 mb-2">CRYPTOGRAPHIC HASH</h4>
 <p className="text-green-400 font-mono text-sm break-all">{selected.hashChain}</p>
 </div>

 {/* Approvers */}
 <div>
 <h4 className="text-xs font-medium text-slate-500 mb-2">APPROVERS (with certificates)</h4>
 <div className="space-y-1">
 {selected.approvers.map((a, i) => (
 <div key={i} className="flex items-center gap-2 text-sm text-slate-300">
 <span className="text-green-400">✓</span> {a}
 <span className="text-xs text-slate-500 font-mono">GOV-CERT-{2026}-{1000 + i}</span>
 </div>
 ))}
 </div>
 </div>

 {/* Data Snapshots */}
 <div>
 <h4 className="text-xs font-medium text-slate-500 mb-2">DATA SNAPSHOTS</h4>
 <div className="space-y-1">
 {selected.dataSnapshots.map((d, i) => (
 <div key={i} className="flex items-center gap-2 text-sm text-slate-300">
 <FileText className="w-5 h-5" /> {d}
 </div>
 ))}
 </div>
 </div>

 {/* Assumptions & Alternatives */}
 <div className="grid grid-cols-2 gap-4">
 <div className="bg-white/5 rounded-xl p-4">
 <h4 className="text-xs font-medium text-slate-500 mb-2">ASSUMPTIONS</h4>
 {selected.assumptions.map((a, i) => (
 <p key={i} className="text-xs text-slate-300">• {a}</p>
 ))}
 </div>
 <div className="bg-white/5 rounded-xl p-4">
 <h4 className="text-xs font-medium text-slate-500 mb-2">ALTERNATIVES CONSIDERED</h4>
 {selected.alternatives.map((a, i) => (
 <p key={i} className="text-xs text-slate-300">• {a}</p>
 ))}
 </div>
 </div>

 <div className="p-4 bg-slate-500/10 border border-slate-500/20 rounded-xl">
 <p className="text-sm text-slate-300"> <Scale className="w-4 h-4 inline" /> <strong>Legal Standing:</strong> This evidence package is cryptographically signed, timestamped, and stored in an immutable vault. It can be independently verified by any third party using the public hash chain. Retained for {selected.retentionPeriod}.</p>
 </div>
 </div>
 ) : (
 <div className="glass rounded-2xl p-12 text-center">
 <div className="text-4xl mb-4"> <Scale className="w-4 h-4 inline" /> </div>
 <h3 className="text-white font-bold mb-2">Select an Evidence Package</h3>
 <p className="text-sm text-slate-400">Click any decision to view its complete legal evidence chain</p>
 </div>
 )}
 </div>
 </div>
 </div>
 );
}
