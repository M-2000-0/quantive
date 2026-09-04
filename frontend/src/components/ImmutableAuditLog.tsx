import React, { useState } from 'react';

interface AuditEntry {
 id: string;
 timestamp: string;
 user: string;
 role: string;
 action: string;
 category: 'data_access' | 'modification' | 'approval' | 'export' | 'login' | 'system' | 'security';
 details: string;
 hash: string;
 previousHash: string;
 certificateId: string;
 ipAddress: string;
 deviceFingerprint: string;
 integrity: 'verified' | 'tampered';
 version?: number;
 affectedRecords?: string[];
}

const MOCK_ENTRIES: AuditEntry[] = [
 {
 id: 'ae-001',
 timestamp: '2026-08-24T14:02:31Z',
 user: 'Sarah Chen',
 role: 'Senior Analyst',
 action: 'Approved optimization strategy',
 category: 'approval',
 details: 'Approved Strategy A: Staggered Issuance ($2.4B 2027 refinancing)',
 hash: 'a3f2c8d1e5b4f6a7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1',
 previousHash: 'b4e3d2c1a5f6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2',
 certificateId: 'GOV-CERT-2026-7842',
 ipAddress: '192.168.1.45',
 deviceFingerprint: 'MBP-2024-SARAH',
 integrity: 'verified',
 version: 3,
 affectedRecords: ['opt-847', 'strategy-a'] },
 {
 id: 'ae-002',
 timestamp: '2026-08-24T13:45:12Z',
 user: 'Dr. Amara Okafor',
 role: 'Director',
 action: 'Modified optimization assumptions',
 category: 'modification',
 details: 'Changed interest rate assumption from 4.2% to 4.5% for 2028 projections',
 hash: 'b4e3d2c1a5f6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2',
 previousHash: 'c5f4e3d2b6a7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3',
 certificateId: 'GOV-CERT-2026-3291',
 ipAddress: '192.168.1.22',
 deviceFingerprint: 'DELL-AMARA-OFFICE',
 integrity: 'verified',
 version: 5,
 affectedRecords: ['assumption-rate-2028'] },
 {
 id: 'ae-003',
 timestamp: '2026-08-24T12:30:00Z',
 user: 'System',
 role: 'Automated',
 action: 'Anomaly detected',
 category: 'security',
 details: 'User James Morrison approved $400M transaction (normal range: $5M-$50M). Workflow frozen pending review.',
 hash: 'c5f4e3d2b6a7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3',
 previousHash: 'd6a5b4c3d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4',
 certificateId: 'GOV-SYS-AUTO',
 ipAddress: '10.0.0.1',
 deviceFingerprint: 'SYSTEM-AUTO',
 integrity: 'verified' },
 {
 id: 'ae-004',
 timestamp: '2026-08-24T11:15:45Z',
 user: 'James Morrison',
 role: 'Senior Analyst',
 action: 'Exported portfolio data',
 category: 'export',
 details: 'Exported 847 instruments (CSV format) to external USB device',
 hash: 'd6a5b4c3d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4',
 previousHash: 'e7b6c5d4e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5',
 certificateId: 'GOV-CERT-2026-5523',
 ipAddress: '192.168.1.67',
 deviceFingerprint: 'MBP-2024-JAMES',
 integrity: 'verified' },
 {
 id: 'ae-005',
 timestamp: '2026-08-24T10:00:00Z',
 user: 'Minister Office',
 role: 'Minister',
 action: 'Approved emergency issuance',
 category: 'approval',
 details: 'Emergency approval for $800M short-term T-bill issuance under crisis protocol',
 hash: 'e7b6c5d4e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5',
 previousHash: 'f8c7d6e5f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6',
 certificateId: 'GOV-CERT-2026-0001',
 ipAddress: '10.0.1.1',
 deviceFingerprint: 'HSM-MINISTER-OFFICE',
 integrity: 'verified',
 version: 1,
 affectedRecords: ['emergency-tbill-800m'] },
 {
 id: 'ae-006',
 timestamp: '2026-08-24T09:30:15Z',
 user: 'Unknown',
 role: 'Unknown',
 action: 'Failed login attempt',
 category: 'security',
 details: 'Failed login for user admin@treasury.gov from IP 203.0.113.42 (Singapore). Account locked after 3 failed attempts.',
 hash: 'f8c7d6e5f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6',
 previousHash: 'a9d8e7f6a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7',
 certificateId: 'N/A',
 ipAddress: '203.0.113.42',
 deviceFingerprint: 'UNKNOWN',
 integrity: 'verified' },
];

const CATEGORY_INFO: Record<string, { icon: string; color: string }> = {
 data_access: { icon: '👁️', color: 'blue' },
 modification: { icon: '✏️', color: 'amber' },
 approval: { icon: 'CheckCircle', color: 'green' },
 export: { icon: 'Upload', color: 'purple' },
 login: { icon: 'Key', color: 'cyan' },
 system: { icon: 'Settings', color: 'slate' },
 security: { icon: '🚨', color: 'red' } };

export default function ImmutableAuditLog() {
 const [entries] = useState([]);
 const [selectedEntry, setSelectedEntry] = useState<AuditEntry | null>(null);
 const [filterCategory, setFilterCategory] = useState<string>('all');

 const filtered = filterCategory === 'all' ? entries : entries.filter(e => e.category === filterCategory);

 return (
 <div className="space-y-6 animate-glass-in">
 <div className="flex items-center justify-between">
 <div className="flex items-center gap-3">
 <div className="w-10 h-10 bg-gradient-to-br from-red-500 to-rose-600 rounded-xl flex items-center justify-center">
 <span className="text-lg">🔐</span>
 </div>
 <div>
 <h2 className="text-xl font-bold text-white">Immutable Audit Log</h2>
 <p className="text-sm text-slate-400">Cryptographically signed, tamper-proof record of every action</p>
 </div>
 </div>
 <div className="flex gap-2 items-center">
 <span className="px-3 py-1 bg-green-500/20 text-green-400 rounded-lg text-xs font-medium">
 <Lock className="w-4 h-4 inline" /> Chain Integrity: VERIFIED
 </span>
 <span className="px-3 py-1 bg-white/5 text-slate-400 rounded-lg text-xs">
 {entries.length} entries
 </span>
 </div>
 </div>

 {/* Blockchain Visualization */}
 <div className="glass rounded-2xl p-4">
 <h3 className="text-xs font-medium text-slate-500 mb-3">AUDIT CHAIN INTEGRITY</h3>
 <div className="flex items-center gap-1 overflow-x-auto pb-2">
 {entries.slice(0, 6).map((entry, i) => (
 <React.Fragment key={entry.id}>
 <div
 className={`flex-shrink-0 px-3 py-2 rounded-lg border cursor-pointer transition-all ${
 selectedEntry?.id === entry.id
 ? 'bg-green-500/10 border-green-500/30'
 : 'bg-white/5 border-white/10 hover:bg-white/10'
 }`}
 onClick={() => setSelectedEntry(entry)}
 >
 <p className="text-xs text-slate-400">{entry.timestamp.split('T')[1].slice(0, 5)}</p>
 <p className="text-xs text-white truncate max-w-[100px]">{entry.user}</p>
 <span className={`text-xs ${CATEGORY_INFO[entry.category]?.color === 'red' ? 'text-red-400' : 'text-green-400'}`}>
 {entry.integrity === 'verified' ? '✓' : '✗'}
 </span>
 </div>
 {i < entries.length - 1 && (
 <span className="text-slate-500 flex-shrink-0">→</span>
 )}
 </React.Fragment>
 ))}
 </div>
 </div>

 {/* Filter */}
 <div className="flex gap-2 flex-wrap">
 <button
 onClick={() => setFilterCategory('all')}
 className={`px-3 py-1.5 rounded-lg text-xs font-medium ${filterCategory === 'all' ? 'bg-white/20 text-white' : 'bg-white/5 text-slate-400'}`}
 >
 All ({entries.length})
 </button>
 {Object.entries(CATEGORY_INFO).map(([key, info]) => (
 <button
 key={key}
 onClick={() => setFilterCategory(key)}
 className={`px-3 py-1.5 rounded-lg text-xs font-medium ${filterCategory === key ? 'bg-white/20 text-white' : 'bg-white/5 text-slate-400'}`}
 >
 {info.icon} {key.replace(/_/g, ' ')} ({entries.filter(e => e.category === key).length})
 </button>
 ))}
 </div>

 <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
 {/* Entry List */}
 <div className="space-y-2">
 {filtered.map(entry => (
 <button
 key={entry.id}
 onClick={() => setSelectedEntry(entry)}
 className={`w-full text-left glass rounded-xl p-3 transition-all ${
 selectedEntry?.id === entry.id ? 'ring-2 ring-red-500/50' : 'hover:bg-white/5'
 }`}
 >
 <div className="flex items-center justify-between mb-1">
 <div className="flex items-center gap-2">
 <span>{CATEGORY_INFO[entry.category]?.icon}</span>
 <span className="text-xs text-slate-500">{entry.timestamp.split('T')[1].slice(0, 8)}</span>
 </div>
 <span className="text-xs text-green-400">✓</span>
 </div>
 <p className="text-sm text-white font-medium truncate">{entry.action}</p>
 <p className="text-xs text-slate-400">{entry.user} ({entry.role})</p>
 </button>
 ))}
 </div>

 {/* Detail Panel */}
 <div className="lg:col-span-2">
 {selectedEntry ? (
 <div className="glass rounded-2xl p-6 space-y-4">
 <div className="flex items-start justify-between">
 <div>
 <h3 className="text-lg font-bold text-white">{selectedEntry.action}</h3>
 <p className="text-sm text-slate-400 mt-1">{selectedEntry.details}</p>
 </div>
 <span className={`px-3 py-1 rounded-lg text-xs font-medium ${
 selectedEntry.integrity === 'verified' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
 }`}>
 {selectedEntry.integrity === 'verified' ? ' <Lock className="w-4 h-4 inline" /> VERIFIED' : ' <AlertTriangle className="w-4 h-4 inline" /> TAMPERED'}
 </span>
 </div>

 {/* Cryptographic Proof */}
 <div className="bg-white/5 rounded-xl p-4 space-y-2">
 <h4 className="text-xs font-medium text-slate-500">CRYPTOGRAPHIC PROOF</h4>
 <div className="grid grid-cols-2 gap-3 text-xs">
 <div>
 <span className="text-slate-500">Hash: </span>
 <span className="text-green-400 font-mono break-all">{selectedEntry.hash.slice(0, 32)}...</span>
 </div>
 <div>
 <span className="text-slate-500">Prev Hash: </span>
 <span className="text-slate-400 font-mono break-all">{selectedEntry.previousHash.slice(0, 32)}...</span>
 </div>
 <div>
 <span className="text-slate-500">Certificate: </span>
 <span className="text-white">{selectedEntry.certificateId}</span>
 </div>
 <div>
 <span className="text-slate-500">Version: </span>
 <span className="text-white">v{selectedEntry.version || 1}</span>
 </div>
 </div>
 </div>

 {/* User & Device */}
 <div className="grid grid-cols-2 gap-4">
 <div className="bg-white/5 rounded-xl p-4">
 <h4 className="text-xs font-medium text-slate-500 mb-2">USER</h4>
 <p className="text-white text-sm font-medium">{selectedEntry.user}</p>
 <p className="text-xs text-slate-400">{selectedEntry.role}</p>
 <p className="text-xs text-slate-500 mt-1">IP: {selectedEntry.ipAddress}</p>
 </div>
 <div className="bg-white/5 rounded-xl p-4">
 <h4 className="text-xs font-medium text-slate-500 mb-2">DEVICE</h4>
 <p className="text-white text-sm font-medium">{selectedEntry.deviceFingerprint}</p>
 <p className="text-xs text-slate-400">Timestamp: {selectedEntry.timestamp}</p>
 </div>
 </div>

 {/* Affected Records */}
 {selectedEntry.affectedRecords && (
 <div className="bg-white/5 rounded-xl p-4">
 <h4 className="text-xs font-medium text-slate-500 mb-2">AFFECTED RECORDS</h4>
 <div className="flex gap-2 flex-wrap">
 {selectedEntry.affectedRecords.map((r, i) => (
 <span key={i} className="px-2 py-1 bg-white/10 rounded text-xs text-white font-mono">{r}</span>
 ))}
 </div>
 </div>
 )}

 {/* Non-Repudiation Statement */}
 <div className="p-4 bg-green-500/10 border border-green-500/20 rounded-xl">
 <p className="text-sm text-green-300">
 <Lock className="w-4 h-4 inline" /> <strong>Non-Repudiation:</strong> {selectedEntry.user} approved this action using Government Certificate {selectedEntry.certificateId} at {selectedEntry.timestamp}. This record is cryptographically signed and immutable. Any tampering would break the hash chain and be immediately detectable.
 </p>
 </div>
 </div>
 ) : (
 <div className="glass rounded-2xl p-12 text-center">
 <div className="text-4xl mb-4">🔐</div>
 <h3 className="text-white font-bold mb-2">Select an Entry</h3>
 <p className="text-sm text-slate-400">Click any audit entry to view its cryptographic proof and non-repudiation details</p>
 </div>
 )}
 </div>
 </div>
 </div>
 );
}
