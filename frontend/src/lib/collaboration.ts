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
  currentActivity?: string;
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

  getMembers(): TeamMember[] {
    return this.members;
  }

  getMember(id: string): TeamMember | undefined {
    return this.members.find((m) => m.id === id);
  }

  getOnlineMembers(): TeamMember[] {
    return this.members.filter((m) => m.isOnline);
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

  private emit(event: CollabEvent, data?: unknown): void {
    this.listeners.forEach((l) => l(event, data));
  }
}

const service = new CollaborationService();

export function getCollaboration(): CollaborationService {
  return service;
}
