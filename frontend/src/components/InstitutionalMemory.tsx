import React, { useState } from 'react';
import { Building2 } from 'lucide-react';

interface MemoryEntry {
 id: string;
 title: string;
 date: string;
 administration: string;
 minister: string;
 decision: string;
 assumptions: string[];
 alternatives: string[];
 outcome: 'success' | 'partial' | 'failure' | 'pending';
 outcomeNote: string;
 lessonsLearned: string[];
 tags: string[];
}

const ENTRIES: MemoryEntry[] = [
 {
 id: 'mem-001',
 title: '2027 Maturity Wall Strategy',
 date: '2026-08-24',
 administration: 'Current',
 minister: 'Hon. Minister',
 decision: 'Refinance $2.4B via staggered 5Y/10Y/15Y issuances',
 assumptions: ['Rates stable at 4.0-4.5%', 'No credit event', 'Market conditions favorable'],
 alternatives: ['Lump-sum 10Y', 'Green bond pivot', 'Conservative hold'],
 outcome: 'pending',
 outcomeNote: 'Awaiting execution',
 lessonsLearned: [],
 tags: ['refinancing', 'maturity', 'issuance'] },
 {
 id: 'mem-002',
 title: 'Emergency Liquidity Response 2025',
 date: '2025-11-15',
 administration: 'Previous',
 minister: 'Dr. K. Mensah',
 decision: 'Activated emergency T-bill issuance ($800M) during market stress',
 assumptions: ['Liquidity crisis genuine', 'Market access available', 'No contagion'],
 alternatives: ['IMF standby', 'Reserve drawdown', 'Bilateral swap'],
 outcome: 'success',
 outcomeNote: 'Successfully stabilized liquidity within 48 hours. Cost: $12M premium.',
 lessonsLearned: [
 'Emergency protocol worked as designed',
 'Pre-positioned T-bill program saved 2 weeks',
 'Bilateral swap lines were critical fallback',
 ],
 tags: ['emergency', 'liquidity', 'crisis'] },
 {
 id: 'mem-003',
 title: 'FX Hedging Program 2024',
 date: '2024-06-01',
 administration: 'Previous',
 minister: 'Dr. K. Mensah',
 decision: 'Implemented 60% rolling forward hedge on USD exposure',
 assumptions: ['USD/EUR range 1.05-1.15', 'No major currency shock', 'Counterparty quality maintained'],
 alternatives: ['Full hedge (80%+)', 'Options-based', 'Natural hedge'],
 outcome: 'success',
 outcomeNote: 'Saved $85M vs unhedged position. Hedge ratio optimal.',
 lessonsLearned: [
 '60% hedge was right balance of cost and protection',
 'Rolling forward worked better than static',
 'Counterparty diversification important',
 ],
 tags: ['fx', 'hedging', 'currency'] },
];

export default function InstitutionalMemory() {
 const [entries] = useState(ENTRIES);
 const [selected, setSelected] = useState<MemoryEntry | null>(null);
 const [searchTerm, setSearchTerm] = useState('');

 const filtered = entries.filter(e =>
 e.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
 e.tags.some(t => t.includes(searchTerm.toLowerCase()))
 );

 const OUTCOME_COLORS: Record<string, string> = {
 success: 'bg-green-500/20 text-green-400',
 partial: 'bg-yellow-500/20 text-yellow-400',
 failure: 'bg-red-500/20 text-red-400',
 pending: 'bg-slate-500/20 text-slate-400' };

 return (
 <div className="space-y-6 animate-glass-in">
 <div className="flex items-center gap-3">
 <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-violet-600 rounded-xl flex items-center justify-center">
 <Building2 className="w-5 h-5" />
 </div>
 <div>
 <h2 className="text-xl font-bold text-white">Institutional Memory System</h2>
 <p className="text-sm text-slate-400">National memory — preserve decisions, assumptions, and reasoning across administrations</p>
 </div>
 </div>

 {/* Search */}
 <input
 type="text"
 value={searchTerm}
 onChange={(e) => setSearchTerm(e.target.value)}
 placeholder="Search decisions by title, tag, or keyword..."
 className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500/50"
 />

 {/* Stats */}
 <div className="grid grid-cols-4 gap-4">
 <div className="glass rounded-xl p-4 text-center">
 <p className="text-2xl font-bold text-white">{entries.length}</p>
 <p className="text-xs text-slate-400">Decision Records</p>
 </div>
 <div className="glass rounded-xl p-4 text-center">
 <p className="text-2xl font-bold text-green-400">{entries.filter(e => e.outcome === 'success').length}</p>
 <p className="text-xs text-slate-400">Successful</p>
 </div>
 <div className="glass rounded-xl p-4 text-center">
 <p className="text-2xl font-bold text-slate-400">{entries.filter(e => e.outcome === 'pending').length}</p>
 <p className="text-xs text-slate-400">Pending</p>
 </div>
 <div className="glass rounded-xl p-4 text-center">
 <p className="text-2xl font-bold text-white">2</p>
 <p className="text-xs text-slate-400">Administrations</p>
 </div>
 </div>

 <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
 {/* Entries */}
 <div className="space-y-3">
 {filtered.map(entry => (
 <button key={entry.id} onClick={() => setSelected(entry)} className={`w-full text-left glass rounded-xl p-4 transition-all ${selected?.id === entry.id ? 'ring-2 ring-indigo-500/50' : 'hover:bg-white/5'}`}>
 <div className="flex items-center justify-between mb-2">
 <span className="text-xs text-slate-500">{entry.date}</span>
 <span className={`px-2 py-0.5 rounded text-xs ${OUTCOME_COLORS[entry.outcome]}`}>{entry.outcome}</span>
 </div>
 <h4 className="text-white text-sm font-medium mb-1">{entry.title}</h4>
 <p className="text-xs text-slate-400">{entry.administration} • {entry.minister}</p>
 <div className="flex gap-1 mt-2 flex-wrap">
 {entry.tags.map((t, i) => (
 <span key={i} className="px-1.5 py-0.5 bg-white/10 rounded text-xs text-slate-400">{t}</span>
 ))}
 </div>
 </button>
 ))}
 </div>

 {/* Detail */}
 <div className="lg:col-span-2">
 {selected ? (
 <div className="glass rounded-2xl p-6 space-y-4">
 <div className="flex items-start justify-between">
 <div>
 <h3 className="text-lg font-bold text-white">{selected.title}</h3>
 <p className="text-sm text-slate-400">{selected.administration} • {selected.minister} • {selected.date}</p>
 </div>
 <span className={`px-3 py-1 rounded-lg text-xs font-medium ${OUTCOME_COLORS[selected.outcome]}`}>{selected.outcome.toUpperCase()}</span>
 </div>

 {/* Decision */}
 <div className="bg-white/5 rounded-xl p-4">
 <h4 className="text-xs text-slate-500 mb-1">DECISION</h4>
 <p className="text-sm text-white">{selected.decision}</p>
 </div>

 {/* Assumptions */}
 <div className="bg-white/5 rounded-xl p-4">
 <h4 className="text-xs text-slate-500 mb-2">ASSUMPTIONS AT TIME OF DECISION</h4>
 <div className="space-y-1">
 {selected.assumptions.map((a, i) => (
 <p key={i} className="text-sm text-slate-300">• {a}</p>
 ))}
 </div>
 </div>

 {/* Alternatives */}
 <div className="bg-white/5 rounded-xl p-4">
 <h4 className="text-xs text-slate-500 mb-2">ALTERNATIVES CONSIDERED</h4>
 <div className="flex gap-2 flex-wrap">
 {selected.alternatives.map((a, i) => (
 <span key={i} className="px-2 py-1 bg-white/10 rounded text-xs text-slate-300">{a}</span>
 ))}
 </div>
 </div>

 {/* Outcome */}
 <div className={`rounded-xl p-4 ${selected.outcome === 'success' ? 'bg-green-500/10' : selected.outcome === 'failure' ? 'bg-red-500/10' : 'bg-white/5'}`}>
 <h4 className="text-xs text-slate-500 mb-1">OUTCOME</h4>
 <p className="text-sm text-white">{selected.outcomeNote}</p>
 </div>

 {/* Lessons Learned */}
 {selected.lessonsLearned.length > 0 && (
 <div className="bg-indigo-500/10 rounded-xl p-4">
 <h4 className="text-xs text-indigo-400 mb-2">LESSONS LEARNED</h4>
 <div className="space-y-1">
 {selected.lessonsLearned.map((l, i) => (
 <p key={i} className="text-sm text-indigo-300">• {l}</p>
 ))}
 </div>
 </div>
 )}

 <div className="p-4 bg-indigo-500/10 border border-indigo-500/20 rounded-xl">
 <p className="text-sm text-indigo-300"> <Building2 className="w-4 h-4 inline" /> <strong>Institutional Memory:</strong> This record preserves the complete decision context. Future officials can understand not just what was decided, but why, under what conditions, and what was learned.</p>
 </div>
 </div>
 ) : (
 <div className="glass rounded-2xl p-12 text-center">
 <div className="text-4xl mb-4"> <Building2 className="w-4 h-4 inline" /> </div>
 <h3 className="text-white font-bold mb-2">Select a Decision Record</h3>
 <p className="text-sm text-slate-400">Click any entry to view the complete institutional memory</p>
 </div>
 )}
 </div>
 </div>
 </div>
 );
}
