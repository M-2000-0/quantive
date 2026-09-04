import React, { useState } from 'react';
import { Search, TriangleAlert as AlertTriangle } from 'lucide-react';

interface EmployeeRisk {
 id: string;
 name: string;
 role: string;
 department: string;
 riskScore: number;
 factors: {
 privilegeLevel: number;
 unusualBehavior: number;
 failedLogins: number;
 exportActivity: number;
 permissionChanges: number;
 loginAnomalies: number;
 };
 lastActivity: string;
 status: 'normal' | 'elevated' | 'high' | 'critical';
 trend: 'improving' | 'stable' | 'worsening';
}

const EMPLOYEES: EmployeeRisk[] = [
 {
 id: 'er-001', name: 'James Morrison', role: 'Senior Analyst', department: 'Debt Management',
 riskScore: 87,
 factors: { privilegeLevel: 65, unusualBehavior: 92, failedLogins: 45, exportActivity: 88, permissionChanges: 30, loginAnomalies: 78 },
 lastActivity: '2026-08-24T12:30:00Z', status: 'critical', trend: 'worsening' },
 {
 id: 'er-002', name: 'Dr. Amara Okafor', role: 'Director', department: 'Policy',
 riskScore: 42,
 factors: { privilegeLevel: 85, unusualBehavior: 25, failedLogins: 10, exportActivity: 30, permissionChanges: 15, loginAnomalies: 20 },
 lastActivity: '2026-08-24T10:00:00Z', status: 'normal', trend: 'stable' },
 {
 id: 'er-003', name: 'Sarah Chen', role: 'Senior Analyst', department: 'Analytics',
 riskScore: 55,
 factors: { privilegeLevel: 60, unusualBehavior: 45, failedLogins: 20, exportActivity: 72, permissionChanges: 10, loginAnomalies: 35 },
 lastActivity: '2026-08-24T09:00:00Z', status: 'elevated', trend: 'stable' },
 {
 id: 'er-004', name: 'Michael Torres', role: 'Treasury Ops', department: 'Operations',
 riskScore: 38,
 factors: { privilegeLevel: 70, unusualBehavior: 15, failedLogins: 5, exportActivity: 20, permissionChanges: 8, loginAnomalies: 12 },
 lastActivity: '2026-08-24T11:00:00Z', status: 'normal', trend: 'improving' },
 {
 id: 'er-005', name: 'Lisa Wang', role: 'Analyst', department: 'Risk',
 riskScore: 28,
 factors: { privilegeLevel: 40, unusualBehavior: 10, failedLogins: 5, exportActivity: 15, permissionChanges: 5, loginAnomalies: 8 },
 lastActivity: '2026-08-24T08:00:00Z', status: 'normal', trend: 'improving' },
];

const STATUS_COLORS: Record<string, string> = {
 normal: 'bg-green-500/20 text-green-400',
 elevated: 'bg-yellow-500/20 text-yellow-400',
 high: 'bg-orange-500/20 text-orange-400',
 critical: 'bg-red-500/20 text-red-400' };

const TREND_ICONS: Record<string, string> = {
 improving: 'TrendingUp',
 stable: '➡️',
 worsening: 'TrendingDown' };

export default function InsiderRiskDashboard() {
 const [employees] = useState(EMPLOYEES);
 const [selected, setSelected] = useState<EmployeeRisk | null>(null);

 const criticalCount = employees.filter(e => e.status === 'critical').length;

 return (
 <div className="space-y-6 animate-glass-in">
 <div className="flex items-center justify-between">
 <div className="flex items-center gap-3">
 <div className="w-10 h-10 bg-gradient-to-br from-amber-500 to-orange-600 rounded-xl flex items-center justify-center">
 <span className="text-lg">🕵️</span>
 </div>
 <div>
 <h2 className="text-xl font-bold text-white">Insider Risk Dashboard</h2>
 <p className="text-sm text-slate-400">Employee risk scoring based on behavior, privilege, and activity</p>
 </div>
 </div>
 {criticalCount > 0 && (
 <span className="px-3 py-1 bg-red-500/20 text-red-400 rounded-lg text-sm font-medium">
 🚨 {criticalCount} Critical Risk{criticalCount > 1 ? 's' : ''}
 </span>
 )}
 </div>

 <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
 {/* Employee List */}
 <div className="space-y-3">
 {employees.sort((a, b) => b.riskScore - a.riskScore).map(emp => (
 <button
 key={emp.id}
 onClick={() => setSelected(emp)}
 className={`w-full text-left glass rounded-xl p-4 transition-all ${
 selected?.id === emp.id ? 'ring-2 ring-amber-500/50' : 'hover:bg-white/5'
 } ${emp.status === 'critical' ? 'border-l-4 border-red-500' : ''}`}
 >
 <div className="flex items-center justify-between mb-2">
 <div>
 <h4 className="text-white font-medium">{emp.name}</h4>
 <p className="text-xs text-slate-400">{emp.role} • {emp.department}</p>
 </div>
 <div className="text-right">
 <div className={`text-2xl font-bold ${
 emp.riskScore >= 75 ? 'text-red-400' :
 emp.riskScore >= 50 ? 'text-orange-400' :
 emp.riskScore >= 30 ? 'text-yellow-400' : 'text-green-400'
 }`}>
 {emp.riskScore}
 </div>
 <span className="text-xs text-slate-500">Risk Score</span>
 </div>
 </div>
 <div className="flex items-center gap-2">
 <span className={`px-2 py-0.5 rounded text-xs ${STATUS_COLORS[emp.status]}`}>
 {emp.status}
 </span>
 <span className="text-xs">{TREND_ICONS[emp.trend]}</span>
 </div>
 </button>
 ))}
 </div>

 {/* Detail Panel */}
 <div className="lg:col-span-2">
 {selected ? (
 <div className="glass rounded-2xl p-6 space-y-5">
 <div className="flex items-center justify-between">
 <div>
 <h3 className="text-lg font-bold text-white">{selected.name}</h3>
 <p className="text-sm text-slate-400">{selected.role} • {selected.department}</p>
 </div>
 <div className={`text-4xl font-bold ${
 selected.riskScore >= 75 ? 'text-red-400' :
 selected.riskScore >= 50 ? 'text-orange-400' :
 'text-yellow-400'
 }`}>
 {selected.riskScore}/100
 </div>
 </div>

 {/* Risk Factors */}
 <div className="space-y-3">
 <h4 className="text-sm font-medium text-slate-400">RISK FACTORS</h4>
 {Object.entries(selected.factors).map(([key, value]) => (
 <div key={key} className="flex items-center gap-4">
 <span className="text-sm text-white w-48 capitalize">{key.replace(/([A-Z])/g, ' $1')}</span>
 <div className="flex-1 bg-white/5 rounded-full h-2">
 <div
 className={`h-2 rounded-full ${
 value >= 75 ? 'bg-red-400' :
 value >= 50 ? 'bg-orange-400' :
 value >= 25 ? 'bg-yellow-400' : 'bg-green-400'
 }`}
 style={{ width: `${value}%` }}
 />
 </div>
 <span className={`text-sm font-medium w-10 text-right ${
 value >= 75 ? 'text-red-400' :
 value >= 50 ? 'text-orange-400' :
 value >= 25 ? 'text-yellow-400' : 'text-green-400'
 }`}>
 {value}
 </span>
 </div>
 ))}
 </div>

 {/* AI Assessment */}
 <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl">
 <p className="text-sm text-red-300">
 🚨 <strong>AI Assessment:</strong> {selected.name} has an elevated insider risk score of {selected.riskScore}/100.
 Key concerns: {selected.factors.unusualBehavior >= 75 ? 'unusual behavior patterns, ' : ''}
 {selected.factors.exportActivity >= 75 ? 'excessive data exports, ' : ''}
 {selected.factors.loginAnomalies >= 75 ? 'login anomalies, ' : ''}
 {selected.factors.privilegeLevel >= 75 ? 'elevated privileges. ' : ''}
 Recommend enhanced monitoring and access review.
 </p>
 </div>

 <div className="flex gap-3">
 <button className="flex-1 py-3 bg-amber-500/20 text-amber-400 rounded-xl font-medium hover:bg-amber-500/30 transition-colors">
 <Search className="w-4 h-4 inline" /> Review Activity Logs
 </button>
 <button className="flex-1 py-3 bg-red-500/20 text-red-400 rounded-xl font-medium hover:bg-red-500/30 transition-colors">
 <AlertTriangle className="w-4 h-4 inline" /> Restrict Access
 </button>
 </div>
 </div>
 ) : (
 <div className="glass rounded-2xl p-12 text-center">
 <div className="text-4xl mb-4">🕵️</div>
 <h3 className="text-white font-bold mb-2">Select an Employee</h3>
 <p className="text-sm text-slate-400">Click any employee to view their risk profile and recommended actions</p>
 </div>
 )}
 </div>
 </div>
 </div>
 );
}
