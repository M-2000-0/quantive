import React, { useState } from 'react';
import { Globe } from 'lucide-react';

interface ResidencyOption {
 region: string;
 country: string;
 flag: string;
 datacenter: string;
 encryptionKey: 'local' | 'hsm' | 'customer';
 status: 'active' | 'available' | 'planned';
 compliance: string[];
}

const REGIONS: ResidencyOption[] = [
 { region: 'Americas', country: 'United States', flag: '🇺🇸', datacenter: 'AWS GovCloud (US-East)', encryptionKey: 'hsm', status: 'active', compliance: ['FedRAMP', 'FIPS 140-2', 'SOC 2'] },
 { region: 'Americas', country: 'Brazil', flag: '🇧🇷', datacenter: 'São Paulo Region', encryptionKey: 'local', status: 'active', compliance: ['LGPD', 'ISO 27001'] },
 { region: 'Europe', country: 'Germany', flag: '🇩🇪', datacenter: 'Frankfurt (AWS)', encryptionKey: 'customer', status: 'active', compliance: ['GDPR', 'ISO 27001', 'BSI C5'] },
 { region: 'Europe', country: 'United Kingdom', flag: '🇬🇧', datacenter: 'London (Azure)', encryptionKey: 'hsm', status: 'active', compliance: ['UK GDPR', 'Cyber Essentials Plus'] },
 { region: 'Asia-Pacific', country: 'Singapore', flag: '🇸🇬', datacenter: 'Singapore (AWS)', encryptionKey: 'hsm', status: 'active', compliance: ['PDPA', 'MAS TRM'] },
 { region: 'Asia-Pacific', country: 'Japan', flag: '🇯🇵', datacenter: 'Tokyo (AWS)', encryptionKey: 'local', status: 'available', compliance: ['APPI', 'ISMAP'] },
 { region: 'Middle East', country: 'UAE', flag: '🇦🇪', datacenter: 'Abu Dhabi (Azure)', encryptionKey: 'local', status: 'available', compliance: ['NESA', 'PDPL'] },
 { region: 'Africa', country: 'South Africa', flag: '🇿🇦', datacenter: 'Cape Town (AWS)', encryptionKey: 'hsm', status: 'planned', compliance: ['POPIA'] },
];

export default function DataResidencyControls() {
 const [selected, setSelected] = useState<ResidencyOption | null>(null);

 return (
 <div className="space-y-6 animate-glass-in">
 <div className="flex items-center gap-3">
 <div className="w-10 h-10 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-xl flex items-center justify-center">
 <Globe className="w-5 h-5" />
 </div>
 <div>
 <h2 className="text-xl font-bold text-white">Data Residency Controls</h2>
 <p className="text-sm text-slate-400">In-country storage, local encryption keys, and sovereignty guarantees</p>
 </div>
 </div>

 {/* Key Guarantees */}
 <div className="glass rounded-2xl p-5">
 <h3 className="text-sm font-medium text-slate-400 mb-4">SOVEREIGNTY GUARANTEES</h3>
 <div className="grid grid-cols-4 gap-4">
 {[
 { icon: '🗄️', title: 'In-Country Storage', desc: 'Data never leaves selected jurisdiction' },
 { icon: 'Key', title: 'Local Encryption Keys', desc: 'Government-controlled HSM or key management' },
 { icon: '🚫', title: 'No Foreign Access', desc: 'No data sharing without explicit consent' },
 { icon: 'FileText', title: 'Audit-Ready', desc: 'Full data lineage and access logs' },
 ].map((g, i) => (
 <div key={i} className="bg-white/5 rounded-xl p-4 text-center">
 <span className="text-2xl mb-2 block">{g.icon}</span>
 <h4 className="text-white text-sm font-medium mb-1">{g.title}</h4>
 <p className="text-xs text-slate-500">{g.desc}</p>
 </div>
 ))}
 </div>
 </div>

 {/* Regions Grid */}
 <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
 {REGIONS.map((r, i) => (
 <button key={i} onClick={() => setSelected(r)} className={`text-left p-4 rounded-xl border transition-all ${selected?.country === r.country ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-white/5 border-white/10 hover:bg-white/10'}`}>
 <div className="flex items-center gap-2 mb-2">
 <span className="text-xl">{r.flag}</span>
 <span className="text-sm text-white font-medium">{r.country}</span>
 </div>
 <p className="text-xs text-slate-500 mb-2">{r.datacenter}</p>
 <div className="flex items-center gap-1 mb-2">
 <span className={`px-1.5 py-0.5 rounded text-xs ${
 r.encryptionKey === 'customer' ? 'bg-green-500/20 text-green-400' :
 r.encryptionKey === 'hsm' ? 'bg-blue-500/20 text-blue-400' :
 'bg-purple-500/20 text-purple-400'
 }`}>
 {r.encryptionKey === 'customer' ? ' <Key className="w-4 h-4 inline" /> Customer Keys' :
 r.encryptionKey === 'hsm' ? ' <Lock className="w-4 h-4 inline" /> HSM Keys' : ' <Building2 className="w-4 h-4 inline" /> Local Keys'}
 </span>
 </div>
 <span className={`px-2 py-0.5 rounded text-xs ${
 r.status === 'active' ? 'bg-green-500/20 text-green-400' :
 r.status === 'available' ? 'bg-yellow-500/20 text-yellow-400' :
 'bg-slate-500/20 text-slate-400'
 }`}>
 {r.status}
 </span>
 </button>
 ))}
 </div>

 {/* Detail */}
 {selected && (
 <div className="glass rounded-2xl p-6 space-y-4">
 <div className="flex items-center gap-3">
 <span className="text-3xl">{selected.flag}</span>
 <div>
 <h3 className="text-lg font-bold text-white">{selected.country}</h3>
 <p className="text-sm text-slate-400">{selected.datacenter}</p>
 </div>
 </div>
 <div>
 <h4 className="text-xs font-medium text-slate-500 mb-2">COMPLIANCE CERTIFICATIONS</h4>
 <div className="flex gap-2 flex-wrap">
 {selected.compliance.map((c, i) => (
 <span key={i} className="px-3 py-1 bg-green-500/10 text-green-400 rounded-lg text-xs">{c}</span>
 ))}
 </div>
 </div>
 </div>
 )}
 </div>
 );
}
