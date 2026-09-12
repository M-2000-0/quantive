import React, { useState, useEffect } from 'react';
import { TriangleAlert as AlertTriangle } from 'lucide-react';

interface CrisisAlert {
 id: string;
 severity: 'critical' | 'high' | 'medium' | 'low';
 title: string;
 description: string;
 timestamp: string;
 source: string;
 actionRequired: boolean;
 acknowledged: boolean;
}

interface LiquidityForecast {
 date: string;
 inflows: number;
 outflows: number;
 balance: number;
 threshold: number;
}

interface EmergencyPlan {
 id: string;
 name: string;
 status: 'draft' | 'ready' | 'activated' | 'completed';
 triggers: string[];
 actions: { step: number; action: string; responsible: string; deadline: string; status: 'pending' | 'in_progress' | 'completed' }[];
}

const MOCK_ALERTS: CrisisAlert[] = [
 { id: 'a1', severity: 'critical', title: 'Liquidity Buffer Below Threshold', description: 'Cash reserves dropped to 12.3%, below 15% minimum. Emergency funding required.', timestamp: '2026-08-24T02:15:00Z', source: 'Liquidity Monitor', actionRequired: true, acknowledged: false },
 { id: 'a2', severity: 'critical', title: 'Sovereign Spread Spike', description: '5Y CDS spread increased 45bps in 2 hours to 285bps. Market stress detected.', timestamp: '2026-08-24T01:45:00Z', source: 'Market Data', actionRequired: true, acknowledged: false },
 { id: 'a3', severity: 'high', title: 'Maturity Wall Alert', description: '$3.2B debt maturing in Q1 2027. Refinancing risk elevated if rates rise further.', timestamp: '2026-08-23T18:00:00Z', source: 'Maturity Tracker', actionRequired: true, acknowledged: true },
 { id: 'a4', severity: 'high', title: 'FX Reserve Depletion', description: 'Foreign exchange reserves declined 8% month-over-month. Intervention capacity limited.', timestamp: '2026-08-23T14:30:00Z', source: 'Reserve Monitor', actionRequired: true, acknowledged: false },
 { id: 'a5', severity: 'medium', title: 'Credit Rating Watch', description: 'Rating agency placed sovereign on negative outlook. Review expected within 60 days.', timestamp: '2026-08-22T10:00:00Z', source: 'Credit Monitor', actionRequired: false, acknowledged: true },
 { id: 'a6', severity: 'low', title: 'Coupon Payment Reminder', description: '$180M coupon payment due in 14 days. Ensure sufficient funding in payment account.', timestamp: '2026-08-20T09:00:00Z', source: 'Payment Calendar', actionRequired: false, acknowledged: true },
];

const MOCK_LIQUIDITY: LiquidityForecast[] = [
 { date: 'Aug 24', inflows: 450, outflows: 820, balance: 1230, threshold: 1500 },
 { date: 'Aug 25', inflows: 280, outflows: 350, balance: 1160, threshold: 1500 },
 { date: 'Aug 26', inflows: 120, outflows: 180, balance: 1100, threshold: 1500 },
 { date: 'Aug 27', inflows: 500, outflows: 200, balance: 1400, threshold: 1500 },
 { date: 'Aug 28', inflows: 350, outflows: 280, balance: 1470, threshold: 1500 },
 { date: 'Aug 29', inflows: 180, outflows: 150, balance: 1500, threshold: 1500 },
 { date: 'Aug 30', inflows: 90, outflows: 120, balance: 1470, threshold: 1500 },
];

const MOCK_PLANS: EmergencyPlan[] = [
 {
 id: 'ep1',
 name: 'Emergency Liquidity Injection',
 status: 'activated',
 triggers: ['Liquidity < 15%', 'Liquidity < 10%', 'Payment failure'],
 actions: [
 { step: 1, action: 'Activate emergency funding line', responsible: 'Treasury', deadline: 'T+1h', status: 'completed' },
 { step: 2, action: 'Issue short-term T-bills', responsible: 'Debt Office', deadline: 'T+4h', status: 'in_progress' },
 { step: 3, action: 'Draw from reserve fund', responsible: 'Minister', deadline: 'T+8h', status: 'pending' },
 { step: 4, action: 'Notify IMF/World Bank', responsible: 'Diplomatic', deadline: 'T+24h', status: 'pending' },
 ] },
 {
 id: 'ep2',
 name: 'Market Crash Response',
 status: 'ready',
 triggers: ['Spread > 500bps', 'FX crash > 10%', 'Capital flight indicators'],
 actions: [
 { step: 1, action: 'Activate FX intervention', responsible: 'Central Bank', deadline: 'T+30min', status: 'pending' },
 { step: 2, action: 'Implement capital controls', responsible: 'Minister', deadline: 'T+2h', status: 'pending' },
 { step: 3, action: 'Emergency press conference', responsible: 'PM Office', deadline: 'T+4h', status: 'pending' },
 { step: 4, action: 'Request IMF standby', responsible: 'Finance', deadline: 'T+48h', status: 'pending' },
 ] },
];

const SEVERITY_COLORS: Record<string, string> = {
 critical: 'bg-red-500/20 text-red-400 border-red-500/30',
 high: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
 medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
 low: 'bg-green-500/20 text-green-400 border-green-500/30' };

export default function CrisisCommandCenter() {
 const [alerts, setAlerts] = useState<CrisisAlert[]>(MOCK_ALERTS);
 const [plans] = useState<EmergencyPlan[]>(MOCK_PLANS);
 const [activeTab, setActiveTab] = useState<'alerts' | 'liquidity' | 'plans' | 'scenarios'>('alerts');
 const [showWarRoom, setShowWarRoom] = useState(true);
 const [pulse, setPulse] = useState(true);

 // Simulate pulsing alert
 useEffect(() => {
 const interval = setInterval(() => setPulse(p => !p), 1000);
 return () => clearInterval(interval);
 }, []);

 const criticalCount = alerts.filter(a => a.severity === 'critical' && !a.acknowledged).length;
 const unacknowledged = alerts.filter(a => !a.acknowledged).length;

 const acknowledgeAlert = (id: string) => {
 setAlerts(prev => prev.map(a => a.id === id ? { ...a, acknowledged: true } : a));
 };

 return (
 <div className={`space-y-6 animate-glass-in ${showWarRoom ? 'bg-red-950/20' : ''}`}>
 {/* War Room Banner */}
 {criticalCount > 0 && (
 <div className={`bg-red-500/20 border border-red-500/40 rounded-2xl p-4 flex items-center justify-between ${pulse ? 'bg-red-500/30' : 'bg-red-500/15'} transition-all duration-1000`}>
 <div className="flex items-center gap-3">
 <span className="text-2xl">🚨</span>
 <div>
 <h3 className="text-red-400 font-bold">CRISIS MODE ACTIVE</h3>
 <p className="text-xs text-red-300">{criticalCount} critical alerts require immediate attention</p>
 </div>
 </div>
 <div className="flex gap-2">
 <button
 onClick={() => setShowWarRoom(!showWarRoom)}
 className="px-4 py-2 bg-red-500/30 border border-red-500/40 rounded-xl text-red-300 text-sm font-medium hover:bg-red-500/40 transition-colors"
 >
 {showWarRoom ? 'Exit War Room' : 'Enter War Room'}
 </button>
 </div>
 </div>
 )}

 <div className="flex items-center justify-between">
 <div className="flex items-center gap-3">
 <div className="w-10 h-10 bg-gradient-to-br from-red-500 to-orange-600 rounded-xl flex items-center justify-center">
 <span className="text-lg">⚔️</span>
 </div>
 <div>
 <h2 className="text-xl font-bold text-white">Crisis Command Center</h2>
 <p className="text-sm text-slate-400">Emergency scenarios, liquidity forecasts, and response coordination</p>
 </div>
 </div>
 <div className="flex gap-3">
 <div className="glass px-4 py-2 rounded-xl text-center">
 <p className={`text-2xl font-bold ${criticalCount > 0 ? 'text-red-400' : 'text-green-400'}`}>{criticalCount}</p>
 <p className="text-xs text-slate-400">Critical</p>
 </div>
 <div className="glass px-4 py-2 rounded-xl text-center">
 <p className="text-2xl font-bold text-amber-400">{unacknowledged}</p>
 <p className="text-xs text-slate-400">Unread</p>
 </div>
 </div>
 </div>

 {/* Tabs */}
 <div className="flex gap-2">
 {(['alerts', 'liquidity', 'plans', 'scenarios'] as const).map(tab => (
 <button
 key={tab}
 onClick={() => setActiveTab(tab)}
 className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
 activeTab === tab
 ? 'bg-red-500/20 text-red-400 border border-red-500/30'
 : 'bg-white/5 text-slate-400 hover:bg-white/10 border border-transparent'
 }`}
 >
 {tab.charAt(0).toUpperCase() + tab.slice(1)}
 {tab === 'alerts' && unacknowledged > 0 && (
 <span className="ml-1 px-1.5 py-0.5 bg-red-500 text-white rounded-full text-xs">{unacknowledged}</span>
 )}
 </button>
 ))}
 </div>

 {/* Alerts */}
 {activeTab === 'alerts' && (
 <div className="space-y-3">
 {alerts.map(alert => (
 <div key={alert.id} className={`glass rounded-xl p-4 border ${SEVERITY_COLORS[alert.severity]} ${!alert.acknowledged ? 'ring-1 ring-red-500/30' : ''}`}>
 <div className="flex items-start justify-between">
 <div className="flex-1">
 <div className="flex items-center gap-2 mb-1">
 <span className="px-2 py-0.5 rounded text-xs font-bold uppercase">{alert.severity}</span>
 <span className="text-xs text-slate-500">{alert.source}</span>
 <span className="text-xs text-slate-500">{new Date(alert.timestamp).toLocaleString()}</span>
 </div>
 <h4 className="text-white font-medium mb-1">{alert.title}</h4>
 <p className="text-sm text-slate-400">{alert.description}</p>
 </div>
 <div className="flex items-center gap-2 ml-4">
 {!alert.acknowledged && (
 <button
 onClick={() => acknowledgeAlert(alert.id)}
 className="px-3 py-1.5 bg-white/10 rounded-lg text-xs text-white hover:bg-white/20 transition-colors"
 >
 Acknowledge
 </button>
 )}
 {alert.actionRequired && (
 <span className="px-2 py-1 bg-red-500/30 text-red-300 rounded text-xs font-medium">
 ACTION REQUIRED
 </span>
 )}
 </div>
 </div>
 </div>
 ))}
 </div>
 )}

 {/* Liquidity Forecast */}
 {activeTab === 'liquidity' && (
 <div className="glass rounded-2xl p-6">
 <h3 className="text-sm font-medium text-slate-400 mb-4">7-DAY LIQUIDITY FORECAST</h3>
 <div className="space-y-3">
 {MOCK_LIQUIDITY.map((day, i) => {
 const isBelowThreshold = day.balance < day.threshold;
 return (
 <div key={i} className={`flex items-center gap-4 p-3 rounded-xl ${isBelowThreshold ? 'bg-red-500/10 border border-red-500/20' : 'bg-white/5'}`}>
 <span className="text-white text-sm font-medium w-20">{day.date}</span>
 <div className="flex-1 grid grid-cols-3 gap-4">
 <div>
 <p className="text-xs text-slate-500">Inflows</p>
 <p className="text-green-400 text-sm">+${day.inflows}M</p>
 </div>
 <div>
 <p className="text-xs text-slate-500">Outflows</p>
 <p className="text-red-400 text-sm">-${day.outflows}M</p>
 </div>
 <div>
 <p className="text-xs text-slate-500">Balance</p>
 <p className={`text-sm font-medium ${isBelowThreshold ? 'text-red-400' : 'text-white'}`}>
 ${day.balance}M
 </p>
 </div>
 </div>
 {isBelowThreshold && (
 <span className="px-2 py-1 bg-red-500/20 text-red-400 rounded text-xs font-medium">
 <AlertTriangle className="w-4 h-4 inline" /> BELOW THRESHOLD
 </span>
 )}
 </div>
 );
 })}
 </div>
 <div className="mt-4 p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl">
 <p className="text-sm text-amber-400">
 <AlertTriangle className="w-4 h-4 inline" /> <strong>Warning:</strong> Liquidity balance will fall below $1.5B threshold on Aug 26. Recommend activating emergency funding.
 </p>
 </div>
 </div>
 )}

 {/* Emergency Plans */}
 {activeTab === 'plans' && (
 <div className="space-y-4">
 {plans.map(plan => (
 <div key={plan.id} className="glass rounded-2xl p-6">
 <div className="flex items-center justify-between mb-4">
 <h3 className="text-lg font-bold text-white">{plan.name}</h3>
 <span className={`px-3 py-1 rounded-lg text-xs font-medium ${
 plan.status === 'activated' ? 'bg-red-500/20 text-red-400' :
 plan.status === 'ready' ? 'bg-green-500/20 text-green-400' :
 'bg-slate-500/20 text-slate-400'
 }`}>
 {plan.status.toUpperCase()}
 </span>
 </div>

 <div className="mb-4">
 <p className="text-xs text-slate-500 mb-2">TRIGGER CONDITIONS:</p>
 <div className="flex gap-2 flex-wrap">
 {plan.triggers.map((t, i) => (
 <span key={i} className="px-2 py-1 bg-red-500/10 text-red-300 rounded text-xs">{t}</span>
 ))}
 </div>
 </div>

 <div className="space-y-2">
 <p className="text-xs text-slate-500 mb-2">RESPONSE ACTIONS:</p>
 {plan.actions.map((action, i) => (
 <div key={i} className={`flex items-center gap-3 p-3 rounded-xl ${
 action.status === 'completed' ? 'bg-green-500/10' :
 action.status === 'in_progress' ? 'bg-amber-500/10' : 'bg-white/5'
 }`}>
 <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
 action.status === 'completed' ? 'bg-green-500/20 text-green-400' :
 action.status === 'in_progress' ? 'bg-amber-500/20 text-amber-400' :
 'bg-white/10 text-slate-500'
 }`}>
 {action.step}
 </span>
 <div className="flex-1">
 <p className="text-sm text-white">{action.action}</p>
 <p className="text-xs text-slate-500">{action.responsible} • Deadline: {action.deadline}</p>
 </div>
 <span className={`text-xs ${
 action.status === 'completed' ? 'text-green-400' :
 action.status === 'in_progress' ? 'text-amber-400' : 'text-slate-500'
 }`}>
 {action.status === 'completed' ? 'CheckCircle' : action.status === 'in_progress' ? 'RefreshCw' : '⏳'}
 </span>
 </div>
 ))}
 </div>
 </div>
 ))}
 </div>
 )}

 {/* Emergency Scenarios */}
 {activeTab === 'scenarios' && (
 <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
 {[
 { name: 'Global Financial Crisis', icon: '💥', probability: '5%', impact: 'Catastrophic', description: 'Complete loss of market access, capital flight, currency collapse' },
 { name: 'Regional Sovereign Default', icon: '🏚️', probability: '8%', impact: 'Severe', description: 'Contagion from neighboring country default affecting spreads' },
 { name: 'Commodity Price Collapse', icon: 'TrendingDown', probability: '15%', impact: 'High', description: '60% drop in commodity export revenue over 6 months' },
 { name: 'Pandemic / Natural Disaster', icon: '🦠', probability: '3%', impact: 'Severe', description: 'Economic shutdown requiring emergency fiscal response' },
 { name: 'Trade War Escalation', icon: '⚔️', probability: '20%', impact: 'Moderate', description: 'Tariff increases affecting 30% of export volume' },
 { name: 'Currency Crisis', icon: '💱', probability: '12%', impact: 'High', description: 'Rapid depreciation exceeding 20% in 30 days' },
 ].map((scenario, i) => (
 <div key={i} className="glass rounded-xl p-4 hover:bg-white/5 transition-colors cursor-pointer">
 <div className="flex items-start gap-3">
 <span className="text-2xl">{scenario.icon}</span>
 <div className="flex-1">
 <div className="flex items-center justify-between mb-1">
 <h4 className="text-white font-medium">{scenario.name}</h4>
 <span className={`px-2 py-0.5 rounded text-xs ${
 scenario.impact === 'Catastrophic' ? 'bg-red-500/20 text-red-400' :
 scenario.impact === 'Severe' ? 'bg-orange-500/20 text-orange-400' :
 scenario.impact === 'High' ? 'bg-yellow-500/20 text-yellow-400' :
 'bg-blue-500/20 text-blue-400'
 }`}>
 {scenario.impact}
 </span>
 </div>
 <p className="text-xs text-slate-400 mb-2">{scenario.description}</p>
 <p className="text-xs text-slate-500">Probability: {scenario.probability}</p>
 </div>
 </div>
 </div>
 ))}
 </div>
 )}
 </div>
 );
}
