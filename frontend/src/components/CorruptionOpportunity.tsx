import React from 'react';
import { Search } from 'lucide-react';

interface Vulnerability {
 area: string;
 risk: 'high' | 'medium' | 'low';
 weakness: string;
 recommendation: string;
 currentStatus: 'mitigated' | 'partial' | 'open';
}

const VULNERABILITIES: Vulnerability[] = [
 { area: 'Approval Workflow', risk: 'low', weakness: 'Single approver for decisions >$100M', recommendation: 'Implemented Six-Eyes principle', currentStatus: 'mitigated' },
 { area: 'Bank Account Changes', risk: 'medium', weakness: 'Beneficiary changes require only 1 approval', recommendation: 'Require dual approval + 48h waiting period', currentStatus: 'partial' },
 { area: 'Data Export', risk: 'medium', weakness: 'Mass exports not restricted', recommendation: 'Implement daily export limits and approval', currentStatus: 'partial' },
 { area: 'Manual Overrides', risk: 'high', weakness: 'System allows manual override of optimization results', recommendation: 'Require documented justification + secondary review', currentStatus: 'open' },
 { area: 'User Provisioning', risk: 'low', weakness: 'Role changes require HR approval', recommendation: 'Implemented with audit trail', currentStatus: 'mitigated' },
 { area: 'Audit Log Access', risk: 'low', weakness: 'Logs are immutable and cryptographically signed', recommendation: 'No changes needed', currentStatus: 'mitigated' },
 { area: 'External Vendor Access', risk: 'medium', weakness: 'Third-party consultants have broad access', recommendation: 'Implement time-limited, scope-limited access', currentStatus: 'open' },
 { area: 'Report Generation', risk: 'low', weakness: 'All reports watermarked and tracked', recommendation: 'No changes needed', currentStatus: 'mitigated' },
];

const RISK_COLORS: Record<string, string> = { high: 'bg-red-500/20 text-red-400', medium: 'bg-yellow-500/20 text-yellow-400', low: 'bg-green-500/20 text-green-400' };
const STATUS_COLORS: Record<string, string> = { mitigated: 'bg-green-500/20 text-green-400', partial: 'bg-yellow-500/20 text-yellow-400', open: 'bg-red-500/20 text-red-400' };

export default function CorruptionOpportunity() {
 return (
 <div className="space-y-6 animate-glass-in">
 <div className="flex items-center gap-3">
 <div className="w-10 h-10 bg-gradient-to-br from-red-500 to-rose-600 rounded-xl flex items-center justify-center">
 <Search className="w-5 h-5" />
 </div>
 <div>
 <h2 className="text-xl font-bold text-white">Corruption Opportunity Detection</h2>
 <p className="text-sm text-slate-400">Where COULD corruption occur? Not detection — prevention.</p>
 </div>
 </div>

 {/* Summary */}
 <div className="grid grid-cols-3 gap-4">
 <div className="glass rounded-xl p-4 text-center">
 <p className="text-2xl font-bold text-green-400">{VULNERABILITIES.filter(v => v.currentStatus === 'mitigated').length}</p>
 <p className="text-xs text-slate-400">Mitigated</p>
 </div>
 <div className="glass rounded-xl p-4 text-center">
 <p className="text-2xl font-bold text-yellow-400">{VULNERABILITIES.filter(v => v.currentStatus === 'partial').length}</p>
 <p className="text-xs text-slate-400">Partial</p>
 </div>
 <div className="glass rounded-xl p-4 text-center">
 <p className="text-2xl font-bold text-red-400">{VULNERABILITIES.filter(v => v.currentStatus === 'open').length}</p>
 <p className="text-xs text-slate-400">Open</p>
 </div>
 </div>

 {/* Vulnerabilities */}
 <div className="glass rounded-2xl p-6">
 <h3 className="text-sm font-medium text-slate-400 mb-4">STRUCTURAL VULNERABILITIES</h3>
 <div className="space-y-3">
 {VULNERABILITIES.sort((a, b) => a.risk === 'high' ? -1 : 1).map((v, i) => (
 <div key={i} className={`flex items-center gap-4 p-4 rounded-xl border ${v.currentStatus === 'open' ? 'bg-red-500/5 border-red-500/20' : v.currentStatus === 'partial' ? 'bg-yellow-500/5 border-yellow-500/20' : 'bg-white/5 border-white/10'}`}>
 <span className={`px-2 py-0.5 rounded text-xs font-medium ${RISK_COLORS[v.risk]}`}>{v.risk.toUpperCase()}</span>
 <div className="flex-1">
 <div className="flex items-center gap-2 mb-1">
 <h4 className="text-white text-sm font-medium">{v.area}</h4>
 <span className={`px-2 py-0.5 rounded text-xs ${STATUS_COLORS[v.currentStatus]}`}>{v.currentStatus}</span>
 </div>
 <p className="text-xs text-slate-400 mb-1">Weakness: {v.weakness}</p>
 <p className="text-xs text-slate-500">Recommendation: {v.recommendation}</p>
 </div>
 </div>
 ))}
 </div>
 </div>

 <div className="p-4 bg-indigo-500/10 border border-indigo-500/20 rounded-xl">
 <p className="text-sm text-indigo-300"> <Search className="w-4 h-4 inline" /> <strong>Philosophy:</strong> This is not corruption detection. This is corruption opportunity mapping. By identifying structural weaknesses before they're exploited, we prevent corruption rather than investigate it after the fact.</p>
 </div>
 </div>
 );
}
