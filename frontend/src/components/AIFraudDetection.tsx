import React, { useState } from 'react';
import { CheckCircle } from 'lucide-react';

interface FraudAlert {
 id: string;
 severity: 'critical' | 'high' | 'medium' | 'low';
 type: 'unusual_approval' | 'unusual_login' | 'unusual_ip' | 'unusual_transaction' | 'beneficiary_change' | 'data_export' | 'privilege_escalation';
 user: string;
 description: string;
 timestamp: string;
 baseline: string;
 actual: string;
 riskScore: number;
 status: 'active' | 'investigating' | 'resolved' | 'false_positive';
}

const ALERTS: FraudAlert[] = [
 { id: 'fa-001', severity: 'critical', type: 'unusual_approval', user: 'James Morrison', description: 'Approved $400M transaction (normal range: $5M-$50M)', timestamp: '2026-08-24T12:30:00Z', baseline: '$5M-$50M', actual: '$400M', riskScore: 95, status: 'active' },
 { id: 'fa-002', severity: 'high', type: 'unusual_login', user: 'Dr. Amara Okafor', description: 'Login from unusual location: Singapore (normally London)', timestamp: '2026-08-24T08:15:00Z', baseline: 'London, UK', actual: 'Singapore', riskScore: 82, status: 'investigating' },
 { id: 'fa-003', severity: 'high', type: 'unusual_ip', user: 'Sarah Chen', description: 'Access from known TOR exit node', timestamp: '2026-08-24T03:45:00Z', baseline: 'Corporate network', actual: 'TOR exit node', riskScore: 88, status: 'active' },
 { id: 'fa-004', severity: 'medium', type: 'data_export', user: 'James Morrison', description: 'Mass export: 847 instruments to USB device', timestamp: '2026-08-24T11:15:00Z', baseline: '0-5 exports/month', actual: '847 records', riskScore: 72, status: 'investigating' },
 { id: 'fa-005', severity: 'medium', type: 'beneficiary_change', user: 'Treasury Ops', description: 'Bank account change request for $2.4B payment', timestamp: '2026-08-24T14:00:00Z', baseline: 'No changes', actual: 'New beneficiary', riskScore: 78, status: 'active' },
 { id: 'fa-006', severity: 'low', type: 'privilege_escalation', user: 'System', description: 'User role changed from Analyst to Manager without HR approval', timestamp: '2026-08-24T10:00:00Z', baseline: 'Analyst', actual: 'Manager', riskScore: 65, status: 'resolved' },
];

const TYPE_INFO: Record<string, { icon: string; color: string }> = {
 unusual_approval: { icon: 'CheckCircle', color: 'red' },
 unusual_login: { icon: 'Key', color: 'amber' },
 unusual_ip: { icon: 'Globe', color: 'purple' },
 unusual_transaction: { icon: 'DollarSign', color: 'red' },
 beneficiary_change: { icon: 'Landmark', color: 'orange' },
 data_export: { icon: 'Upload', color: 'yellow' },
 privilege_escalation: { icon: '⬆️', color: 'blue' } };

const SEVERITY_COLORS: Record<string, string> = {
 critical: 'bg-red-500/20 text-red-400',
 high: 'bg-orange-500/20 text-orange-400',
 medium: 'bg-yellow-500/20 text-yellow-400',
 low: 'bg-green-500/20 text-green-400' };

export default function AIFraudDetection() {
 const [alerts] = useState(ALERTS);
 const [selectedAlert, setSelectedAlert] = useState<FraudAlert | null>(null);

 const criticalCount = alerts.filter(a => a.severity === 'critical' && a.status === 'active').length;
 const activeCount = alerts.filter(a => a.status === 'active').length;

 return (
 <div className="space-y-6 animate-glass-in">
 <div className="flex items-center justify-between">
 <div className="flex items-center gap-3">
 <div className="w-10 h-10 bg-gradient-to-br from-red-500 to-orange-600 rounded-xl flex items-center justify-center">
 <span className="text-lg">🤖</span>
 </div>
 <div>
 <h2 className="text-xl font-bold text-white">AI Fraud Detection</h2>
 <p className="text-sm text-slate-400">Real-time monitoring of unusual patterns and insider threats</p>
 </div>
 </div>
 <div className="flex gap-3">
 <div className="glass px-4 py-2 rounded-xl text-center">
 <p className="text-2xl font-bold text-red-400">{criticalCount}</p>
 <p className="text-xs text-slate-400">Critical</p>
 </div>
 <div className="glass px-4 py-2 rounded-xl text-center">
 <p className="text-2xl font-bold text-amber-400">{activeCount}</p>
 <p className="text-xs text-slate-400">Active</p>
 </div>
 </div>
 </div>

 {/* Alert List */}
 <div className="space-y-3">
 {alerts.map(alert => (
 <button
 key={alert.id}
 onClick={() => setSelectedAlert(alert)}
 className={`w-full text-left glass rounded-xl p-4 transition-all ${
 selectedAlert?.id === alert.id ? 'ring-2 ring-red-500/50' : 'hover:bg-white/5'
 } ${alert.severity === 'critical' && alert.status === 'active' ? 'border-l-4 border-red-500' : ''}`}
 >
 <div className="flex items-start gap-4">
 <span className="text-lg">{TYPE_INFO[alert.type]?.icon}</span>
 <div className="flex-1">
 <div className="flex items-center gap-2 mb-1">
 <span className={`px-2 py-0.5 rounded text-xs font-medium ${SEVERITY_COLORS[alert.severity]}`}>
 {alert.severity.toUpperCase()}
 </span>
 <span className="text-xs text-slate-500">{alert.user}</span>
 <span className="text-xs text-slate-500">{alert.timestamp.split('T')[1].slice(0, 5)}</span>
 </div>
 <p className="text-white text-sm font-medium">{alert.description}</p>
 <div className="flex items-center gap-4 mt-2 text-xs">
 <span className="text-slate-500">Baseline: {alert.baseline}</span>
 <span className="text-slate-500">Actual: <span className="text-white">{alert.actual}</span></span>
 </div>
 </div>
 <div className="text-right">
 <div className={`text-2xl font-bold ${
 alert.riskScore >= 80 ? 'text-red-400' :
 alert.riskScore >= 60 ? 'text-orange-400' :
 alert.riskScore >= 40 ? 'text-yellow-400' : 'text-green-400'
 }`}>
 {alert.riskScore}
 </div>
 <p className="text-xs text-slate-500">Risk Score</p>
 <span className={`px-2 py-0.5 rounded text-xs mt-1 inline-block ${
 alert.status === 'active' ? 'bg-red-500/20 text-red-400' :
 alert.status === 'investigating' ? 'bg-yellow-500/20 text-yellow-400' :
 alert.status === 'resolved' ? 'bg-green-500/20 text-green-400' :
 'bg-slate-500/20 text-slate-400'
 }`}>
 {alert.status}
 </span>
 </div>
 </div>
 </button>
 ))}
 </div>

 {/* Detail Panel */}
 {selectedAlert && (
 <div className="glass rounded-2xl p-6 space-y-4">
 <div className="flex items-start justify-between">
 <h3 className="text-lg font-bold text-white">{selectedAlert.description}</h3>
 <span className={`px-3 py-1 rounded-lg text-sm font-bold ${
 selectedAlert.riskScore >= 80 ? 'bg-red-500/20 text-red-400' :
 selectedAlert.riskScore >= 60 ? 'bg-orange-500/20 text-orange-400' :
 'bg-yellow-500/20 text-yellow-400'
 }`}>
 Risk: {selectedAlert.riskScore}/100
 </span>
 </div>

 <div className="grid grid-cols-2 gap-4">
 <div className="bg-white/5 rounded-xl p-4">
 <h4 className="text-xs text-slate-500 mb-1">USER</h4>
 <p className="text-white font-medium">{selectedAlert.user}</p>
 </div>
 <div className="bg-white/5 rounded-xl p-4">
 <h4 className="text-xs text-slate-500 mb-1">TIMESTAMP</h4>
 <p className="text-white font-medium">{selectedAlert.timestamp}</p>
 </div>
 </div>

 <div className="grid grid-cols-2 gap-4">
 <div className="bg-white/5 rounded-xl p-4">
 <h4 className="text-xs text-slate-500 mb-1">EXPECTED (BASELINE)</h4>
 <p className="text-green-400 font-medium">{selectedAlert.baseline}</p>
 </div>
 <div className="bg-red-500/10 rounded-xl p-4">
 <h4 className="text-xs text-slate-500 mb-1">ACTUAL</h4>
 <p className="text-red-400 font-medium">{selectedAlert.actual}</p>
 </div>
 </div>

 <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl">
 <p className="text-sm text-red-300">
 🚨 <strong>AI Analysis:</strong> This activity deviates {selectedAlert.riskScore}% from the user's established baseline pattern. The system has automatically {selectedAlert.severity === 'critical' ? 'frozen the workflow' : 'flagged for review'}.
 </p>
 </div>

 <div className="flex gap-3">
 <button className="flex-1 py-3 bg-red-500/20 text-red-400 rounded-xl font-medium hover:bg-red-500/30 transition-colors">
 🚨 Escalate to Security
 </button>
 <button className="flex-1 py-3 bg-white/5 text-slate-400 rounded-xl hover:bg-white/10 transition-colors">
 <CheckCircle className="w-4 h-4 inline" /> Mark False Positive
 </button>
 </div>
 </div>
 )}
 </div>
 );
}
