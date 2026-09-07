// ── Collaboration Types ──────────────────────────────────────────────
// Types and utilities only — no mock data. Data comes from API.

export type UserRole =
  | 'admin' | 'analyst' | 'viewer' | 'approver'
  | 'portfolio_manager' | 'risk_officer' | 'compliance_officer'
  | 'treasury_director' | 'treasury_analyst';

export type MemberStatus = 'online' | 'offline' | 'away';

export interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  avatar?: string;
  isOnline: boolean;
  status: MemberStatus;
  currentActivity?: {
    page?: string;
    portfolioId?: string;
    activity?: string;
    since?: string;
  };
  lastSeen?: string;
}

export interface FieldLock {
  field: string;
  lockedBy: string;
  lockedAt: string;
  expiresAt: string;
}

export interface ApprovalChain {
  id: string;
  title: string;
  steps: ApprovalStep[];
  currentStep: number;
  status: 'pending' | 'active' | 'completed' | 'rejected' | 'approved';
}

export interface ApprovalStep {
  id: string;
  assignee: string;
  assigneeId?: string;
  roleName: UserRole;
  status: 'pending' | 'active' | 'approved' | 'rejected';
  notes?: string;
  completedAt?: string;
}

export const ROLE_CONFIG: Record<UserRole, { label: string; color: string; permissions: string[] }> = {
  admin: { label: 'Admin', color: 'text-purple-600', permissions: ['all'] },
  analyst: { label: 'Analyst', color: 'text-blue-600', permissions: ['edit', 'submit', 'view'] },
  viewer: { label: 'Viewer', color: 'text-slate-600', permissions: ['view'] },
  approver: { label: 'Approver', color: 'text-emerald-600', permissions: ['approve', 'view'] },
  portfolio_manager: { label: 'Portfolio Manager', color: 'text-indigo-600', permissions: ['edit', 'submit', 'view'] },
  risk_officer: { label: 'Risk Officer', color: 'text-orange-600', permissions: ['review', 'view'] },
  compliance_officer: { label: 'Compliance Officer', color: 'text-teal-600', permissions: ['review', 'approve', 'view'] },
  treasury_director: { label: 'Treasury Director', color: 'text-violet-600', permissions: ['approve', 'view'] },
  treasury_analyst: { label: 'Treasury Analyst', color: 'text-sky-600', permissions: ['edit', 'view'] },
};

type CollabEvent = 'presence_changed' | 'chain_updated' | 'chain_created' | 'chain_rejected';
type CollabListener = (event: CollabEvent | string, data?: unknown) => void;

class CollaborationService {
  private members: TeamMember[] = [];
  private chains: ApprovalChain[] = [];
  private listeners = new Set<CollabListener>();
  private presenceTimer: number | null = null;
  private chainSeq = 0;

  constructor() {
    this.members = [
      { id: 'user-1', name: 'Treasury Analyst', email: 'analyst@treasury.gov', role: 'treasury_analyst', isOnline: true, status: 'online', currentActivity: { page: 'Optimization' } },
      { id: 'user-2', name: 'Risk Officer', email: 'risk@treasury.gov', role: 'risk_officer', isOnline: true, status: 'online' },
      { id: 'user-3', name: 'Portfolio Manager', email: 'pm@treasury.gov', role: 'portfolio_manager', isOnline: false, status: 'offline' },
    ];
    this.chains = [
      {
        id: 'chain-seed-1',
        title: 'Q1 Refinancing Approval',
        currentStep: 0,
        status: 'active',
        steps: [
          { id: 'chain-seed-1-s1', assignee: 'Treasury Analyst', assigneeId: 'user-1', roleName: 'treasury_analyst', status: 'active' },
          { id: 'chain-seed-1-s2', assignee: 'Risk Officer', assigneeId: 'user-2', roleName: 'risk_officer', status: 'pending' },
        ],
      },
    ];
  }

  getMembers(): TeamMember[] {
    return this.members;
  }

  getMember(id: string): TeamMember | undefined {
    return this.members.find((m) => m.id === id);
  }

  getOnlineMembers(): TeamMember[] {
    return this.members.filter(m => m.isOnline);
  }

  getMembersByRole(role: UserRole): TeamMember[] {
    return this.members.filter(m => m.role === role);
  }

  getTeamPeerSummary(): {
    totalMembers: number;
    onlineMembers: number;
    roleActivity: Array<{ role: UserRole; label: string; count: number }>;
  } {
    const byRole = new Map<UserRole, number>();
    for (const m of this.members) {
      byRole.set(m.role, (byRole.get(m.role) || 0) + 1);
    }
    return {
      totalMembers: this.members.length,
      onlineMembers: this.members.filter(m => m.isOnline).length,
      roleActivity: [...byRole.entries()].map(([role, count]) => ({
        role,
        label: ROLE_CONFIG[role].label,
        count,
      })),
    };
  }

  createApprovalChain(
    title: string,
    steps: Array<{ roleName: UserRole; assignee?: string; assigneeId?: string }>,
  ): ApprovalChain {
    this.chainSeq += 1;
    const chain: ApprovalChain = {
      id: `chain-${Date.now()}-${this.chainSeq}`,
      title,
      currentStep: 0,
      status: 'active',
      steps: steps.map((s, i) => ({
        id: `step-${Date.now()}-${this.chainSeq}-${i}`,
        assignee: s.assignee || ROLE_CONFIG[s.roleName].label,
        assigneeId: s.assigneeId,
        roleName: s.roleName,
        status: i === 0 ? 'active' : 'pending',
      })),
    };
    this.chains.unshift(chain);
    this.emit('chain_created', chain);
    return chain;
  }

  approveStep(chainId: string, stepId: string, _userId: string, notes?: string): boolean {
    const chain = this.chains.find(c => c.id === chainId);
    if (!chain) return false;
    const idx = chain.steps.findIndex(s => s.id === stepId);
    if (idx < 0) return false;
    // Mutate in place so existing step references observe the change.
    chain.steps[idx].status = 'approved';
    if (notes !== undefined) chain.steps[idx].notes = notes;
    chain.steps[idx].completedAt = new Date().toISOString();
    const next = chain.steps[idx + 1];
    if (next) {
      next.status = 'active';
      chain.currentStep = idx + 1;
    } else {
      chain.status = 'approved';
    }
    this.emit('chain_updated', chain);
    return true;
  }

  getFieldLocks(): FieldLock[] {
    return [];
  }

  getApprovalChains(): ApprovalChain[] {
    return this.chains;
  }

  startPresenceUpdates(intervalMs: number): void {
    this.stopPresenceUpdates();
    this.presenceTimer = window.setInterval(() => {
      this.emit('presence_changed');
    }, intervalMs);
  }

  stopPresenceUpdates(): void {
    if (this.presenceTimer !== null) {
      window.clearInterval(this.presenceTimer);
      this.presenceTimer = null;
    }
  }

  subscribe(listener: CollabListener): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  isFieldLocked(
    _sessionId: string,
    field: string,
    _userId: string,
  ): { locked: boolean; by?: string } {
    const lock = this.getFieldLocks().find((l) => l.field === field);
    return lock ? { locked: true, by: lock.lockedBy } : { locked: false };
  }

  lockField(_sessionId: string, field: string, userId: string): void {
    void field;
    void userId;
  }

  unlockField(_sessionId: string, field: string, userId: string): void {
    void field;
    void userId;
  }

  recordChange(
    _sessionId: string,
    change: { userId: string; field: string; oldValue: unknown; newValue?: unknown; applied?: boolean },
  ): void {
    void change;
  }

  private emit(event: CollabEvent, data?: unknown): void {
    this.listeners.forEach((l) => l(event, data));
  }
}

const service = new CollaborationService();

export function getCollaboration(): CollaborationService {
  return service;
}
