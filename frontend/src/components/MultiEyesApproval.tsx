import React, { useState } from 'react';
import { Users } from 'lucide-react';

interface ApprovalRequirement {
 name: string;
 eyes: number;
 roles: string[];
 threshold: string;
 description: string;
 status: 'active' | 'pending' | 'completed';
 approvals: { role: string; user: string; timestamp: string; signed: boolean }[];
}

interface TransactionLimit {
 role: string;
 maxAuthority: string;
 canCreate: boolean;
 canApprove: boolean;
 canExecute: boolean;
 canModify: boolean;
}

const APPROVAL_TIERS: ApprovalRequirement[] = [
 {
 name: 'Standard Changes',
 eyes: 4,
 roles: ['Analyst', 'Manager'],
 threshold: '< $10M',
 description: 'Small optimization adjustments and parameter changes',
 status: 'completed',
 approvals: [
 { role: 'Analyst', user: 'Sarah Chen', timestamp: '2026-08-24T09:00:00Z', signed: true },
 { role: 'Manager', user: 'James Morrison', timestamp: '2026-08-24T09:15:00Z', signed: true },
 ] },
 {
 name: 'Material Changes',
 eyes: 6,
 roles: ['Analyst', 'Director', 'Minister'],
 threshold: '$10M - $100M',
 description: 'Significant strategy changes and portfolio reallocations',
 status: 'pending',
 approvals: [
 { role: 'Analyst', user: 'Sarah Chen', timestamp: '2026-08-24T10:00:00Z', signed: true },
 { role: 'Director', user: 'Dr. Amara Okafor', timestamp: '2026-08-24T10:30:00Z', signed: true },
 { role: 'Minister', user: 'Hon. Minister', timestamp: '', signed: false },
 ] },
 {
 name: 'Sovereign Issuances',
 eyes: 8,
 roles: ['Analyst', 'Director', 'Treasury', 'Minister', 'Cabinet'],
 threshold: '> $100M',
 description: 'Large-scale debt issuances and sovereign transactions',
 status: 'pending',
 approvals: [
 { role: 'Analyst', user: 'Sarah Chen', timestamp: '2026-08-24T09:00:00Z', signed: true },
 { role: 'Director', user: 'Dr. Amara Okafor', timestamp: '2026-08-24T09:30:00Z', signed: true },
 { role: 'Treasury', user: 'Deputy Minister', timestamp: '2026-08-24T10:00:00Z', signed: true },
 { role: 'Minister', user: 'Hon. Minister', timestamp: '', signed: false },
 { role: 'Cabinet', user: 'Cabinet Secretary', timestamp: '', signed: false },
 ] },
];

const ROLE_LIMITS: TransactionLimit[] = [
 { role: 'Analyst', maxAuthority: '$0', canCreate: true, canApprove: false, canExecute: false, canModify: false },
 { role: 'Senior Analyst', maxAuthority: '$5M', canCreate: true, canApprove: false, canExecute: false, canModify: true },
 { role: 'Manager', maxAuthority: '$10M', canCreate: true, canApprove: true, canExecute: false, canModify: true },
 { role: 'Director', maxAuthority: '$50M', canCreate: false, canApprove: true, canExecute: false, canModify: false },
 { role: 'Deputy Minister', maxAuthority: '$100M', canCreate: false, canApprove: true, canExecute: false, canModify: false },
 { role: 'Minister', maxAuthority: 'Unlimited', canCreate: false, canApprove: true, canExecute: false, canModify: false },
 { role: 'Treasury Ops', maxAuthority: 'N/A', canCreate: false, canApprove: false, canExecute: true, canModify: false },
];

export default function MultiEyesApproval() {
 const [selectedTier, setSelectedTier] = useState(APPROVAL_TIERS[1]);

 return (
 <div className="space-y-6 animate-glass-in">
 <div className="flex items-center gap-3">
 <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-xl flex items-center justify-center">
 <Users className="w-5 h-5" />
 </div>
 <div>
 <h2 className="text-xl font-bold text-white">Multi-Eyes Approval Controls</h2>
 <p className="text-sm text-slate-400">Four-Eyes, Six-Eyes, and Eight-Eyes principles for sovereign governance</p>
 </div>
 </div>

 {/* Approval Tiers */}
 <div className="grid grid-cols-3 gap-4">
 {APPROVAL_TIERS.map((tier, i) => (
 <button
 key={i}
 onClick={() => setSelectedTier(tier)}
 className={`text-left p-5 rounded-2xl border transition-all ${
 selectedTier.name === tier.name
 ? 'bg-purple-500/10 border-purple-500/30'
 : 'bg-white/5 border-white/10 hover:bg-white/10'
 }`}
 >
 <div className="flex items-center justify-between mb-3">
 <span className={`text-3xl font-bold ${
 tier.eyes === 4 ? 'text-blue-400' :
 tier.eyes === 6 ? 'text-purple-400' : 'text-amber-400'
 }`}>
 {tier.eyes}
 </span>
 <span className={`px-2 py-0.5 rounded text-xs font-medium ${
 tier.status === 'completed' ? 'bg-green-500/20 text-green-400' :
 tier.status === 'pending' ? 'bg-yellow-500/20 text-yellow-400' :
 'bg-slate-500/20 text-slate-400'
 }`}>
 {tier.status}
 </span>
 </div>
 <h4 className="text-white font-medium mb-1">{tier.name}</h4>
 <p className="text-xs text-slate-400 mb-2">Threshold: {tier.threshold}</p>
 <p className="text-xs text-slate-500">{tier.description}</p>
 <div className="mt-3 flex flex-wrap gap-1">
 {tier.roles.map((r, j) => (
 <span key={j} className="px-1.5 py-0.5 bg-white/10 rounded text-xs text-slate-400">{r}</span>
 ))}
 </div>
 </button>
 ))}
 </div>

 {/* Selected Tier Details */}
 <div className="glass rounded-2xl p-6">
 <h3 className="text-sm font-medium text-slate-400 mb-4">APPROVAL CHAIN: {selectedTier.name.toUpperCase()}</h3>
 <div className="space-y-3">
 {selectedTier.approvals.map((approval, i) => (
 <div key={i} className={`flex items-center gap-4 p-4 rounded-xl border ${
 approval.signed ? 'bg-green-500/5 border-green-500/20' : 'bg-white/5 border-white/10'
 }`}>
 <span className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
 approval.signed ? 'bg-green-500/20 text-green-400' : 'bg-white/10 text-slate-500'
 }`}>
 {i + 1}
 </span>
 <div className="flex-1">
 <div className="flex items-center gap-2">
 <span className="px-2 py-0.5 bg-white/10 rounded text-xs text-slate-400">{approval.role}</span>
 </div>
 <p className="text-white text-sm font-medium mt-1">{approval.user}</p>
 </div>
 {approval.signed ? (
 <div className="text-right">
 <span className="text-green-400 text-sm">✓ Signed</span>
 <p className="text-xs text-slate-500">{approval.timestamp.split('T')[1].slice(0, 5)}</p>
 </div>
 ) : (
 <span className="px-3 py-1.5 bg-yellow-500/20 text-yellow-400 rounded-lg text-xs font-medium">
 ⏳ PENDING
 </span>
 )}
 </div>
 ))}
 </div>
 <div className="mt-4 p-3 bg-white/5 rounded-xl">
 <p className="text-xs text-slate-400">
 Progress: {selectedTier.approvals.filter(a => a.signed).length}/{selectedTier.approvals.length} approvals required
 </p>
 </div>
 </div>

 {/* Segregation of Duties */}
 <div className="glass rounded-2xl p-6">
 <h3 className="text-sm font-medium text-slate-400 mb-4">SEGREGATION OF DUTIES</h3>
 <div className="overflow-x-auto">
 <table className="w-full">
 <thead>
 <tr className="border-b border-white/10">
 <th className="text-left text-xs text-slate-500 py-3 px-4">Role</th>
 <th className="text-center text-xs text-slate-500 py-3 px-4">Max Authority</th>
 <th className="text-center text-xs text-slate-500 py-3 px-4">Create</th>
 <th className="text-center text-xs text-slate-500 py-3 px-4">Approve</th>
 <th className="text-center text-xs text-slate-500 py-3 px-4">Execute</th>
 <th className="text-center text-xs text-slate-500 py-3 px-4">Modify</th>
 </tr>
 </thead>
 <tbody>
 {ROLE_LIMITS.map((limit, i) => (
 <tr key={i} className="border-b border-white/5 hover:bg-white/5">
 <td className="py-3 px-4 text-white text-sm font-medium">{limit.role}</td>
 <td className="py-3 px-4 text-center text-sm text-white">{limit.maxAuthority}</td>
 <td className="py-3 px-4 text-center">
 <span className={limit.canCreate ? 'text-green-400' : 'text-red-400'}>
 {limit.canCreate ? '✓' : '✗'}
 </span>
 </td>
 <td className="py-3 px-4 text-center">
 <span className={limit.canApprove ? 'text-green-400' : 'text-red-400'}>
 {limit.canApprove ? '✓' : '✗'}
 </span>
 </td>
 <td className="py-3 px-4 text-center">
 <span className={limit.canExecute ? 'text-green-400' : 'text-red-400'}>
 {limit.canExecute ? '✓' : '✗'}
 </span>
 </td>
 <td className="py-3 px-4 text-center">
 <span className={limit.canModify ? 'text-green-400' : 'text-red-400'}>
 {limit.canModify ? '✓' : '✗'}
 </span>
 </td>
 </tr>
 ))}
 </tbody>
 </table>
 </div>
 <div className="mt-4 p-3 bg-purple-500/10 border border-purple-500/20 rounded-xl">
 <p className="text-sm text-purple-300">
 <Lock className="w-4 h-4 inline" /> <strong>Dual Control:</strong> Creator can never approve their own work. Every transaction requires separate creation and approval roles.
 </p>
 </div>
 </div>
 </div>
 );
}
