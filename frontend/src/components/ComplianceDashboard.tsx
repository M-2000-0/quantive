import React, { useState } from 'react';
import { CircleCheck as CheckCircle, FileText } from 'lucide-react';

interface ComplianceFramework {
 id: string;
 name: string;
 fullName: string;
 category: 'security' | 'privacy' | 'financial' | 'government';
 score: number;
 controls: { total: number; implemented: number; inProgress: number; planned: number };
 lastAssessment: string;
 nextAudit: string;
 status: 'compliant' | 'partial' | 'planned';
}

const FRAMEWORKS: ComplianceFramework[] = [
 { id: 'iso27001', name: 'ISO 27001', fullName: 'Information Security Management System', category: 'security', score: 92, controls: { total: 114, implemented: 105, inProgress: 6, planned: 3 }, lastAssessment: '2026-07-15', nextAudit: '2026-10-15', status: 'compliant' },
 { id: 'nist80053', name: 'NIST 800-53', fullName: 'Security and Privacy Controls', category: 'security', score: 88, controls: { total: 200, implemented: 176, inProgress: 18, planned: 6 }, lastAssessment: '2026-07-20', nextAudit: '2026-09-20', status: 'compliant' },
 { id: 'soc2', name: 'SOC 2 Type II', fullName: 'Service Organization Control 2', category: 'security', score: 95, controls: { total: 64, implemented: 61, inProgress: 3, planned: 0 }, lastAssessment: '2026-06-30', nextAudit: '2026-12-30', status: 'compliant' },
 { id: 'fips140', name: 'FIPS 140-2', fullName: 'Federal Information Processing Standards', category: 'security', score: 100, controls: { total: 18, implemented: 18, inProgress: 0, planned: 0 }, lastAssessment: '2026-05-01', nextAudit: '2027-05-01', status: 'compliant' },
 { id: 'gdpr', name: 'GDPR', fullName: 'General Data Protection Regulation', category: 'privacy', score: 90, controls: { total: 42, implemented: 38, inProgress: 4, planned: 0 }, lastAssessment: '2026-07-01', nextAudit: '2027-01-01', status: 'compliant' },
 { id: 'imf', name: 'IMF DSA', fullName: 'IMF Debt Sustainability Framework', category: 'financial', score: 100, controls: { total: 24, implemented: 24, inProgress: 0, planned: 0 }, lastAssessment: '2026-08-01', nextAudit: '2026-11-01', status: 'compliant' },
 { id: 'basel', name: 'Basel III', fullName: 'Basel Committee Banking Supervision', category: 'financial', score: 95, controls: { total: 32, implemented: 30, inProgress: 2, planned: 0 }, lastAssessment: '2026-07-15', nextAudit: '2027-01-15', status: 'compliant' },
 { id: 'cis', name: 'CIS Controls', fullName: 'Center for Internet Security Controls', category: 'security', score: 85, controls: { total: 18, implemented: 15, inProgress: 3, planned: 0 }, lastAssessment: '2026-06-01', nextAudit: '2026-12-01', status: 'compliant' },
];

const CATEGORY_COLORS: Record<string, string> = {
 security: 'bg-blue-500/20 text-blue-400',
 privacy: 'bg-purple-500/20 text-purple-400',
 financial: 'bg-green-500/20 text-green-400',
 government: 'bg-amber-500/20 text-amber-400' };

export default function ComplianceDashboard() {
 const [selected, setSelected] = useState<ComplianceFramework | null>(null);
 const [filterCategory, setFilterCategory] = useState<string>('all');

 const filtered = filterCategory === 'all' ? FRAMEWORKS : FRAMEWORKS.filter(f => f.category === filterCategory);
 const overallScore = Math.round(FRAMEWORKS.reduce((sum, f) => sum + f.score, 0) / FRAMEWORKS.length);

 return (
 <div className="space-y-6 animate-glass-in">
 <div className="flex items-center justify-between">
 <div className="flex items-center gap-3">
 <div className="w-10 h-10 bg-gradient-to-br from-emerald-500 to-green-600 rounded-xl flex items-center justify-center">
 <FileText className="w-5 h-5" />
 </div>
 <div>
 <h2 className="text-xl font-bold text-white">Compliance Dashboard</h2>
 <p className="text-sm text-slate-400">NIST, ISO, SOC 2, FIPS, GDPR, IMF, Basel III alignment</p>
 </div>
 </div>
 <div className="glass px-5 py-3 rounded-2xl text-center">
 <p className="text-3xl font-bold text-green-400">{overallScore}%</p>
 <p className="text-xs text-slate-400">Overall Compliance</p>
 </div>
 </div>

 {/* Category Filters */}
 <div className="flex gap-2">
 <button onClick={() => setFilterCategory('all')} className={`px-3 py-1.5 rounded-lg text-xs font-medium ${filterCategory === 'all' ? 'bg-white/20 text-white' : 'bg-white/5 text-slate-400'}`}>
 All ({FRAMEWORKS.length})
 </button>
 {Object.entries(CATEGORY_COLORS).map(([key, color]) => (
 <button key={key} onClick={() => setFilterCategory(key)} className={`px-3 py-1.5 rounded-lg text-xs font-medium ${filterCategory === key ? 'bg-white/20 text-white' : 'bg-white/5 text-slate-400'}`}>
 {key} ({FRAMEWORKS.filter(f => f.category === key).length})
 </button>
 ))}
 </div>

 {/* Framework Grid */}
 <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
 {filtered.map(f => (
 <button key={f.id} onClick={() => setSelected(f)} className={`text-left p-4 rounded-xl border transition-all ${selected?.id === f.id ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-white/5 border-white/10 hover:bg-white/10'}`}>
 <div className="flex items-center justify-between mb-2">
 <span className={`px-2 py-0.5 rounded text-xs ${CATEGORY_COLORS[f.category]}`}>{f.category}</span>
 <span className={`text-lg font-bold ${f.score >= 90 ? 'text-green-400' : f.score >= 75 ? 'text-yellow-400' : 'text-red-400'}`}>{f.score}%</span>
 </div>
 <h4 className="text-white text-sm font-medium mb-1">{f.name}</h4>
 <p className="text-xs text-slate-500 truncate">{f.fullName}</p>
 <div className="mt-2 w-full bg-white/5 rounded-full h-1.5">
 <div className={`h-1.5 rounded-full ${f.score >= 90 ? 'bg-green-400' : f.score >= 75 ? 'bg-yellow-400' : 'bg-red-400'}`} style={{ width: `${f.score}%` }} />
 </div>
 </button>
 ))}
 </div>

 {/* Detail */}
 {selected && (
 <div className="glass rounded-2xl p-6 space-y-4">
 <div className="flex items-start justify-between">
 <div>
 <h3 className="text-lg font-bold text-white">{selected.name}</h3>
 <p className="text-sm text-slate-400">{selected.fullName}</p>
 </div>
 <span className={`px-3 py-1 rounded-lg text-xs font-medium bg-green-500/20 text-green-400`}>COMPLIANT</span>
 </div>

 {/* Controls Breakdown */}
 <div className="grid grid-cols-4 gap-4">
 <div className="bg-white/5 rounded-xl p-3 text-center">
 <p className="text-2xl font-bold text-white">{selected.controls.total}</p>
 <p className="text-xs text-slate-500">Total Controls</p>
 </div>
 <div className="bg-green-500/10 rounded-xl p-3 text-center">
 <p className="text-2xl font-bold text-green-400">{selected.controls.implemented}</p>
 <p className="text-xs text-slate-500">Implemented</p>
 </div>
 <div className="bg-yellow-500/10 rounded-xl p-3 text-center">
 <p className="text-2xl font-bold text-yellow-400">{selected.controls.inProgress}</p>
 <p className="text-xs text-slate-500">In Progress</p>
 </div>
 <div className="bg-slate-500/10 rounded-xl p-3 text-center">
 <p className="text-2xl font-bold text-slate-400">{selected.controls.planned}</p>
 <p className="text-xs text-slate-500">Planned</p>
 </div>
 </div>

 <div className="grid grid-cols-2 gap-4 text-sm">
 <div className="bg-white/5 rounded-xl p-3">
 <span className="text-slate-500">Last Assessment: </span>
 <span className="text-white">{selected.lastAssessment}</span>
 </div>
 <div className="bg-white/5 rounded-xl p-3">
 <span className="text-slate-500">Next Audit: </span>
 <span className="text-white">{selected.nextAudit}</span>
 </div>
 </div>

 <div className="p-4 bg-green-500/10 border border-green-500/20 rounded-xl">
 <p className="text-sm text-green-300"> <CheckCircle className="w-4 h-4 inline" /> {selected.name} compliance verified. Full audit report and evidence documentation available for procurement review.</p>
 </div>
 </div>
 )}
 </div>
 );
}
