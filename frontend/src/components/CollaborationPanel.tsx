// ── Collaboration Panel Component ────────────────────────────────────
// Shows real-time team presence, active approval chains, recent
// activity, and role-based routing status.

import { useState, useEffect } from 'react';
import {
  getCollaboration,
  type TeamMember,
  type ApprovalChain,
  type UserRole,
  ROLE_CONFIG } from '../lib/collaboration';

interface CollaborationPanelProps {
  /** Compact mode for sidebar embedding */
  compact?: boolean;
  /** Show only online members */
  onlineOnly?: boolean;
}

export default function CollaborationPanel({
  compact = false,
  onlineOnly = false }: CollaborationPanelProps) {
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [chains, setChains] = useState<ApprovalChain[]>([]);
  const [activeTab, setActiveTab] = useState<'presence' | 'chains' | 'activity'>('presence');
  const collab = getCollaboration();

  useEffect(() => {
    setMembers(collab.getMembers());
    setChains(collab.getApprovalChains());

    // Start presence simulation
    collab.startPresenceUpdates(10000);

    const unsub = collab.subscribe((event, data) => {
      if (event === 'presence_changed') {
        setMembers([...collab.getMembers()]);
      }
      if (event === 'chain_updated' || event === 'chain_created' || event === 'chain_rejected') {
        setChains([...collab.getApprovalChains()]);
      }
    });

    return () => {
      unsub();
      collab.stopPresenceUpdates();
    };
  }, [collab]);

  const filteredMembers = onlineOnly
    ? members.filter((m) => m.status !== 'offline')
    : members;

  const activeChains = chains.filter((c) => c.status === 'active');
  const recentChains = chains.filter((c) => c.status === 'approved' || c.status === 'rejected');

  const statusColor = (status: string) => {
    switch (status) {
      case 'online': return 'bg-emerald-500';
      case 'away': return 'bg-amber-500';
      case 'busy': return 'bg-red-500';
      default: return 'bg-slate-300';
    }
  };

  const statusLabel = (status: string) => {
    switch (status) {
      case 'online': return 'Online';
      case 'away': return 'Away';
      case 'busy': return 'Busy';
      default: return 'Offline';
    }
  };

  const chainStatusColor = (status: string) => {
    switch (status) {
      case 'approved': return 'bg-emerald-100 text-emerald-700';
      case 'rejected': return 'bg-red-100 text-red-700';
      case 'active': return 'bg-blue-100 text-blue-700';
      default: return 'bg-slate-100 text-slate-600';
    }
  };

  if (compact) {
    return (
      <div className="space-y-2">
        {/* Online Avatars */}
        <div className="flex items-center gap-1">
          {members.filter((m) => m.status === 'online').slice(0, 5).map((m) => (
            <div key={m.id} className="relative" title={`${m.name} — ${ROLE_CONFIG[m.role].label}`}>
              <span className="text-lg">{m.avatar}</span>
              <div className={`absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-white ${statusColor(m.status)}`} />
            </div>
          ))}
          {members.filter((m) => m.status === 'online').length > 5 && (
            <span className="text-xs text-slate-500 font-medium">
              +{members.filter((m) => m.status === 'online').length - 5}
            </span>
          )}
        </div>
        {activeChains.length > 0 && (
          <div className="text-[10px] text-amber-600 font-medium">
            ⏳ {activeChains.length} approval{activeChains.length > 1 ? 's' : ''} pending
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="glass rounded-2xl overflow-hidden">
      {/* Tabs */}
      <div className="flex border-b border-white/20">
        {[
          { id: 'presence' as const, label: `Team (${filteredMembers.length})`, icon: 'Users' },
          { id: 'chains' as const, label: `Approvals (${activeChains.length})`, icon: '🔗' },
          { id: 'activity' as const, label: 'Activity', icon: 'FileText' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 px-3 py-3 text-xs font-medium transition-all ${
              activeTab === tab.id
                ? 'text-blue-700 border-b-2 border-blue-500 bg-blue-50/30'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Presence Tab */}
      {activeTab === 'presence' && (
        <div className="p-3 space-y-1 max-h-80 overflow-y-auto">
          {filteredMembers.map((member) => (
            <div
              key={member.id}
              className="flex items-center gap-3 p-2 rounded-xl hover:bg-white/30 transition-colors"
            >
              <div className="relative">
                <span className="text-xl">{member.avatar}</span>
                <div className={`absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-white ${statusColor(member.status)}`} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="text-sm font-medium text-slate-900">{member.name}</span>
                  <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                    member.role === 'portfolio_manager' ? 'bg-emerald-100 text-emerald-700' :
                    member.role === 'risk_officer' ? 'bg-amber-100 text-amber-700' :
                    member.role === 'compliance_officer' ? 'bg-red-100 text-red-700' :
                    member.role === 'treasury_director' ? 'bg-blue-100 text-blue-700' :
                    member.role === 'treasury_analyst' ? 'bg-cyan-100 text-cyan-700' :
                    'bg-orange-100 text-orange-700'
                  }`}>
                    {ROLE_CONFIG[member.role].label}
                  </span>
                </div>
                <div className="flex items-center gap-1 mt-0.5">
                  <span className={`w-1.5 h-1.5 rounded-full ${statusColor(member.status)}`} />
                  <span className="text-[10px] text-slate-500">{statusLabel(member.status)}</span>
                  {member.currentActivity && (
                    <span className="text-[10px] text-slate-400">
                      · {member.currentActivity.page}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Approvals Tab */}
      {activeTab === 'chains' && (
        <div className="p-3 space-y-3 max-h-80 overflow-y-auto">
          {activeChains.length > 0 ? (
            activeChains.map((chain) => (
              <div key={chain.id} className="p-3 rounded-xl bg-white/30 border border-white/40">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold text-slate-900 truncate">{chain.title}</span>
                  <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${chainStatusColor(chain.status)}`}>
                    {chain.status.toUpperCase()}
                  </span>
                </div>
                {/* Step Progress */}
                <div className="flex items-center gap-1 mb-2">
                  {chain.steps.map((step, idx) => (
                    <div
                      key={step.id}
                      className={`h-1.5 flex-1 rounded-full ${
                        step.status === 'approved' ? 'bg-emerald-500' :
                        step.status === 'active' ? 'bg-blue-500' :
                        step.status === 'rejected' ? 'bg-red-500' :
                        'bg-slate-200'
                      }`}
                    />
                  ))}
                </div>
                {/* Current Step Info */}
                <div className="text-[10px] text-slate-500">
                  Step {chain.currentStep + 1}/{chain.steps.length}:
                  <span className="ml-1 font-medium text-slate-700">
                    {ROLE_CONFIG[chain.steps[chain.currentStep]?.roleName]?.label || 'Unknown'}
                  </span>
                  {chain.steps[chain.currentStep]?.assigneeId && (
                    <span className="ml-1">
                      ({collab.getMember(chain.steps[chain.currentStep].assigneeId!)?.name || 'Unknown'})
                    </span>
                  )}
                </div>
              </div>
            ))
          ) : (
            <div className="p-4 text-center text-xs text-slate-500">
              No active approval chains
            </div>
          )}

          {/* Recent Completed */}
          {recentChains.length > 0 && (
            <>
              <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 px-1">
                Recently Completed
              </div>
              {recentChains.slice(0, 3).map((chain) => (
                <div key={chain.id} className="flex items-center justify-between p-2 rounded-lg bg-white/20">
                  <span className="text-xs text-slate-600 truncate">{chain.title}</span>
                  <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${chainStatusColor(chain.status)}`}>
                    {chain.status.toUpperCase()}
                  </span>
                </div>
              ))}
            </>
          )}
        </div>
      )}

      {/* Activity Tab */}
      {activeTab === 'activity' && (
        <div className="p-3 space-y-2 max-h-80 overflow-y-auto">
          {members
            .filter((m) => m.currentActivity)
            .sort((a, b) => new Date(b.currentActivity!.since).getTime() - new Date(a.currentActivity!.since).getTime())
            .map((member) => {
              const elapsed = Math.floor((Date.now() - new Date(member.currentActivity!.since).getTime()) / 60000);
              return (
                <div key={member.id} className="flex items-center gap-3 p-2 rounded-xl bg-white/20">
                  <span className="text-lg">{member.avatar}</span>
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-medium text-slate-900">{member.name}</div>
                    <div className="text-[10px] text-slate-500">
                      Viewing <span className="font-medium text-slate-700">{member.currentActivity!.page}</span>
                      {member.currentActivity!.portfolioId && (
                        <span className="text-slate-400"> · {member.currentActivity!.portfolioId}</span>
                      )}
                    </div>
                  </div>
                  <span className="text-[10px] text-slate-400">{elapsed}m ago</span>
                </div>
              );
            })}
          {members.filter((m) => m.currentActivity).length === 0 && (
            <div className="p-4 text-center text-xs text-slate-500">
              No active sessions
            </div>
          )}
        </div>
      )}

      {/* Role Summary Footer */}
      {!compact && (
        <div className="px-3 py-2 border-t border-white/20 bg-white/20">
          <div className="flex flex-wrap gap-2">
            {Object.entries(ROLE_CONFIG).map(([role, config]) => {
              const count = members.filter((m) => m.role === role).length;
              if (count === 0) return null;
              const online = members.filter((m) => m.role === role && m.status === 'online').length;
              return (
                <span key={role} className={`px-1.5 py-0.5 rounded text-[9px] font-bold bg-${config.color}-100 text-${config.color}-700`}>
                  {config.label}: {online}/{count}
                </span>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
