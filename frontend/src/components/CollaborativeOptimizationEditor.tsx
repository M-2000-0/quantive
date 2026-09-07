// ── Collaborative Optimization Editor ───────────────────────────────
// Real-time collaborative editing for optimization parameters with
// field locking, presence cursors, and change conflict resolution.

import { useState, useEffect, useCallback } from 'react';
import {
 getCollaboration,
 type TeamMember,
 type FieldLock } from '../lib/collaboration';
import { PencilLine, Zap, Lock } from 'lucide-react';

interface OptimizationParams {
 objective: 'minimize_cost' | 'minimize_risk' | 'maximize_return' | 'balanced';
 maxDuration: number;
 minYield: number;
 maxRisk: number;
 minCreditRating: string;
 currencyHedge: number;
 greenBondTarget: number;
 constraints: string[];
}

interface CollaborativeOptimizationEditorProps {
 /** Current optimization parameters */
 params: OptimizationParams;
 /** Callback when params change */
 onChange: (params: OptimizationParams) => void;
 /** Current user ID */
 currentUserId?: string;
 /** Session/portfolio ID for field locking */
 sessionId?: string;
}

const OBJECTIVE_OPTIONS = [
 { value: 'minimize_cost', label: 'Minimize Cost', icon: 'DollarSign', description: 'Reduce overall financing cost' },
 { value: 'minimize_risk', label: 'Minimize Risk', icon: 'Shield', description: 'Reduce portfolio risk exposure' },
 { value: 'maximize_return', label: 'Maximize Return', icon: 'TrendingUp', description: 'Maximize yield and returns' },
 { value: 'balanced', label: 'Balanced', icon: 'Scale', description: 'Balance cost, risk, and return' },
] as const;

const CREDIT_RATINGS = ['AAA', 'AA+', 'AA', 'AA-', 'A+', 'A', 'A-', 'BBB+', 'BBB', 'BBB-', 'BB+', 'BB'];

export default function CollaborativeOptimizationEditor({
 params,
 onChange,
 currentUserId = 'user-4',
 sessionId = 'session-opt-1' }: CollaborativeOptimizationEditorProps) {
 const [members, setMembers] = useState<TeamMember[]>([]);
 const [fieldLocks, setFieldLocks] = useState<Map<string, FieldLock>>(new Map());
 const [editingField, setEditingField] = useState<string | null>(null);
 const [conflictField, setConflictField] = useState<string | null>(null);
 const [recentChanges, setRecentChanges] = useState<Array<{
 userId: string;
 field: string;
 oldValue: unknown;
 newValue: unknown;
 timestamp: string;
 }>>([]);

 const collab = getCollaboration();

 useEffect(() => {
 setMembers(collab.getMembers());
 collab.startPresenceUpdates(10000);
 return () => collab.stopPresenceUpdates();
 }, [collab]);

 const getFieldLock = useCallback((field: string): { locked: boolean; by?: TeamMember } => {
 const result = collab.isFieldLocked(sessionId, field, currentUserId);
 if (result.locked && result.by) {
 const member = collab.getMember(result.by);
 return { locked: true, by: member };
 }
 return { locked: false };
 }, [collab, sessionId, currentUserId]);

 const handleFieldFocus = useCallback((field: string) => {
 const lockResult = getFieldLock(field);
 if (lockResult.locked) {
 setConflictField(field);
 setTimeout(() => setConflictField(null), 3000);
 return;
 }

 collab.lockField(sessionId, field, currentUserId);
 setEditingField(field);
 }, [collab, sessionId, currentUserId, getFieldLock]);

 const handleFieldBlur = useCallback((field: string) => {
 collab.unlockField(sessionId, field, currentUserId);
 setEditingField(null);
 }, [collab, sessionId, currentUserId]);

 const handleValueChange = useCallback((field: string, value: unknown) => {
 const oldValue = params[field as keyof OptimizationParams];
 if (oldValue === value) return;

 collab.recordChange(sessionId, {
 userId: currentUserId,
 field,
 oldValue,
 newValue: value,
 applied: true });

 setRecentChanges((prev) => [
 { userId: currentUserId, field, oldValue, newValue: value, timestamp: new Date().toISOString() },
 ...prev.slice(0, 9),
 ]);

 onChange({ ...params, [field]: value });
 }, [params, onChange, collab, sessionId, currentUserId]);

 const onlineMembers = members.filter((m) => m.status !== 'offline' && m.id !== currentUserId);
 const currentUser = collab.getMember(currentUserId);

 const lockIndicator = (field: string) => {
 const lockResult = getFieldLock(field);
 if (!lockResult.locked) return null;

 return (
 <div className="absolute -top-1 -right-1 flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-amber-100 border border-amber-300 text-[9px] font-bold text-amber-700 z-10">
 <span>{lockResult.by?.avatar}</span>
 <span>editing</span>
 </div>
 );
 };

 const presenceCursor = (field: string) => {
 const viewers = onlineMembers.filter(
 (m) => m.currentActivity?.page === 'Optimization' && m.currentActivity?.portfolioId === field,
 );
 if (viewers.length === 0) return null;

 return (
 <div className="flex items-center gap-0.5 ml-2">
 {viewers.slice(0, 3).map((m) => (
 <span key={m.id} className="text-xs" title={`${m.name} is viewing`}>
 {m.avatar}
 </span>
 ))}
 </div>
 );
 };

 return (
 <div className="glass rounded-2xl p-6 animate-glass-in">
 {/* Header with Presence */}
 <div className="flex items-center justify-between mb-6">
 <div>
 <h3 className="text-lg font-bold text-slate-900"> <Zap className="w-4 h-4 inline" /> Optimization Parameters</h3>
 <p className="text-xs text-slate-500 mt-0.5">Collaborative editing — changes sync in real time</p>
 </div>
 <div className="flex items-center gap-2">
 {/* Online Presence */}
 <div className="flex items-center -space-x-2">
 {currentUser && (
 <div className="relative z-10">
 <span className="text-lg" title={`You (${currentUser.name})`}>{currentUser.avatar}</span>
 <div className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-emerald-500 border-2 border-white" />
 </div>
 )}
 {onlineMembers.slice(0, 4).map((m) => (
 <div key={m.id} className="relative">
 <span className="text-lg" title={`${m.name} — ${m.status}`}>{m.avatar}</span>
 <div className={`absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-white ${
 m.status === 'online' ? 'bg-emerald-500' : m.status === 'away' ? 'bg-amber-500' : 'bg-red-500'
 }`} />
 </div>
 ))}
 </div>
 <span className="text-[10px] text-slate-500">
 {onlineMembers.length + 1} editing
 </span>
 </div>
 </div>

 {/* Conflict Toast */}
 {conflictField && (
 <div className="mb-4 p-3 rounded-xl bg-amber-50 border border-amber-200 flex items-center gap-2 animate-glass-in">
 <Lock className="w-5 h-5" />
 <span className="text-xs font-medium text-amber-800">
 This field is currently being edited by another team member. Please try again shortly.
 </span>
 </div>
 )}

 {/* Objective Selection */}
 <div className="mb-6">
 <label className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2 block">Optimization Objective</label>
 <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
 {OBJECTIVE_OPTIONS.map((opt) => (
 <button
 key={opt.value}
 onClick={() => handleValueChange('objective', opt.value)}
 className={`p-3 rounded-xl border text-left transition-all ${
 params.objective === opt.value
 ? 'border-blue-400 bg-blue-50/80 ring-2 ring-blue-500/20'
 : 'border-white/40 bg-white/30 hover:border-slate-200'
 }`}
 >
 <div className="text-lg mb-1">{opt.icon}</div>
 <div className={`text-xs font-bold ${params.objective === opt.value ? 'text-blue-900' : 'text-slate-900'}`}>
 {opt.label}
 </div>
 <div className="text-[10px] text-slate-500">{opt.description}</div>
 </button>
 ))}
 </div>
 </div>

 {/* Parameter Fields */}
 <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
 {/* Max Duration */}
 <div className="relative">
 {lockIndicator('maxDuration')}
 <label className="text-xs font-bold text-slate-500 mb-1 block">Max Duration (years)</label>
 <div className="flex items-center gap-3">
 <input
 type="range"
 min="1"
 max="15"
 value={params.maxDuration}
 onChange={(e) => handleValueChange('maxDuration', parseInt(e.target.value))}
 onFocus={() => handleFieldFocus('maxDuration')}
 onBlur={() => handleFieldBlur('maxDuration')}
 className="flex-1 h-2 rounded-full appearance-none bg-slate-200 cursor-pointer"
 />
 <span className="text-sm font-bold text-slate-900 w-8 text-right tabular-nums">{params.maxDuration}yr</span>
 </div>
 {presenceCursor('maxDuration')}
 </div>

 {/* Min Yield */}
 <div className="relative">
 {lockIndicator('minYield')}
 <label className="text-xs font-bold text-slate-500 mb-1 block">Min Yield (%)</label>
 <div className="flex items-center gap-3">
 <input
 type="range"
 min="0"
 max="10"
 step="0.5"
 value={params.minYield}
 onChange={(e) => handleValueChange('minYield', parseFloat(e.target.value))}
 onFocus={() => handleFieldFocus('minYield')}
 onBlur={() => handleFieldBlur('minYield')}
 className="flex-1 h-2 rounded-full appearance-none bg-slate-200 cursor-pointer"
 />
 <span className="text-sm font-bold text-slate-900 w-10 text-right tabular-nums">{params.minYield}%</span>
 </div>
 </div>

 {/* Max Risk */}
 <div className="relative">
 {lockIndicator('maxRisk')}
 <label className="text-xs font-bold text-slate-500 mb-1 block">Max Risk Score</label>
 <div className="flex items-center gap-3">
 <input
 type="range"
 min="0"
 max="100"
 value={params.maxRisk}
 onChange={(e) => handleValueChange('maxRisk', parseInt(e.target.value))}
 onFocus={() => handleFieldFocus('maxRisk')}
 onBlur={() => handleFieldBlur('maxRisk')}
 className="flex-1 h-2 rounded-full appearance-none bg-slate-200 cursor-pointer"
 />
 <span className="text-sm font-bold text-slate-900 w-8 text-right tabular-nums">{params.maxRisk}</span>
 </div>
 </div>

 {/* Credit Rating */}
 <div className="relative">
 {lockIndicator('minCreditRating')}
 <label className="text-xs font-bold text-slate-500 mb-1 block">Min Credit Rating</label>
 <select
 value={params.minCreditRating}
 onChange={(e) => handleValueChange('minCreditRating', e.target.value)}
 onFocus={() => handleFieldFocus('minCreditRating')}
 onBlur={() => handleFieldBlur('minCreditRating')}
 className="w-full px-3 py-2 text-sm rounded-xl border border-white/60 bg-white/40 backdrop-blur-md focus:outline-none focus:ring-2 focus:ring-blue-500/30"
 >
 {CREDIT_RATINGS.map((r) => (
 <option key={r} value={r}>{r}</option>
 ))}
 </select>
 </div>

 {/* Currency Hedge */}
 <div className="relative">
 {lockIndicator('currencyHedge')}
 <label className="text-xs font-bold text-slate-500 mb-1 block">FX Hedge Ratio (%)</label>
 <div className="flex items-center gap-3">
 <input
 type="range"
 min="0"
 max="100"
 value={params.currencyHedge}
 onChange={(e) => handleValueChange('currencyHedge', parseInt(e.target.value))}
 onFocus={() => handleFieldFocus('currencyHedge')}
 onBlur={() => handleFieldBlur('currencyHedge')}
 className="flex-1 h-2 rounded-full appearance-none bg-slate-200 cursor-pointer"
 />
 <span className="text-sm font-bold text-slate-900 w-8 text-right tabular-nums">{params.currencyHedge}%</span>
 </div>
 </div>

 {/* Green Bond Target */}
 <div className="relative">
 {lockIndicator('greenBondTarget')}
 <label className="text-xs font-bold text-slate-500 mb-1 block">Green Bond Target (%)</label>
 <div className="flex items-center gap-3">
 <input
 type="range"
 min="0"
 max="50"
 value={params.greenBondTarget}
 onChange={(e) => handleValueChange('greenBondTarget', parseInt(e.target.value))}
 onFocus={() => handleFieldFocus('greenBondTarget')}
 onBlur={() => handleFieldBlur('greenBondTarget')}
 className="flex-1 h-2 rounded-full appearance-none bg-slate-200 cursor-pointer"
 />
 <span className="text-sm font-bold text-slate-900 w-8 text-right tabular-nums">{params.greenBondTarget}%</span>
 </div>
 </div>
 </div>

 {/* Recent Changes */}
 {recentChanges.length > 0 && (
 <div className="pt-4 border-t border-white/20">
 <div className="text-xs font-bold text-slate-500 mb-2"> <PencilLine className="w-4 h-4 inline" /> Recent Changes</div>
 <div className="space-y-1">
 {recentChanges.slice(0, 3).map((change, idx) => {
 const member = collab.getMember(change.userId);
 return (
 <div key={idx} className="flex items-center gap-2 p-2 rounded-lg bg-white/20 text-[11px]">
 <span>{member?.avatar || '👤'}</span>
 <span className="font-medium text-slate-700">{member?.name || 'Unknown'}</span>
 <span className="text-slate-400">changed</span>
 <span className="font-medium text-slate-700">{change.field}</span>
 <span className="text-slate-400">from</span>
 <span className="font-mono text-slate-600">{String(change.oldValue)}</span>
 <span className="text-slate-400">to</span>
 <span className="font-mono text-blue-600">{String(change.newValue)}</span>
 <span className="text-slate-400 ml-auto">
 {new Date(change.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
 </span>
 </div>
 );
 })}
 </div>
 </div>
 )}
 </div>
 );
}
