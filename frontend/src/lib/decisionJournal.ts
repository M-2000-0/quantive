// ── Decision Journal Types ───────────────────────────────────────────
// Types and utilities only — no mock data. Data comes from API.

export type DecisionStatus =
  | 'draft' | 'submitted' | 'under_review' | 'approved' | 'rejected'
  | 'executed' | 'recommended' | 'completed' | 'expired';

export interface DecisionResolution {
  status: DecisionStatus;
  decidedBy?: string;
  decidedAt?: string;
  reason?: string;
  overrideNotes?: string;
  notes?: string;
}

export interface Recommendation {
  id: string;
  title?: string;
  action: string;
  ticker?: string;
  amount?: number;
  rationale: string;
  confidence: number;
  riskLevel: 'low' | 'medium' | 'high';
  description?: string;
  type?: string;
  instruments?: string[];
  estimatedSavings?: number;
  riskImpact?: string;
  riskChange?: number;
  impactScore?: number;
  timeframe?: string;
}

export interface DecisionLearnings {
  marketRegime: string;
  confidenceCalibration: number;
  whatWorked: string;
  whatFailed: string;
}

export interface DecisionEntry {
  id: string;
  title: string;
  description: string;
  status: DecisionStatus;
  recommendation: Recommendation;
  decision: DecisionResolution;
  timestamp: string;
  createdAt: string;
  updatedAt: string;
  assignedTo?: string;
  tags: string[];
  marketSnapshot?: Record<string, any>;
  outcome?: {
    actualReturn?: number;
    benchmarkReturn?: number;
    actualSavings?: number;
    actualRiskChange?: number;
    riskChange?: number;
    rating?: string;
    measuredAt?: string;
    notes?: string;
  };
  learnings?: DecisionLearnings;
}

class DecisionJournalStore {
  private entries: DecisionEntry[] = [];

  getAll(): DecisionEntry[] {
    return this.entries;
  }

  getById(id: string): DecisionEntry | undefined {
    return this.entries.find(e => e.id === id);
  }

  add(entry: DecisionEntry): void {
    this.entries.unshift(entry);
  }

  /** Record a partial entry (pipelines only know part of the story). */
  addEntry(entry: Partial<DecisionEntry>): DecisionEntry {
    const now = new Date().toISOString();
    const full: DecisionEntry = {
      id: `dec-${Date.now()}`,
      title: entry.title || 'Journal entry',
      description: entry.description || '',
      status: entry.status || 'draft',
      recommendation: entry.recommendation || {
        id: `rec-${Date.now()}`,
        action: 'review',
        rationale: '',
        confidence: 0,
        riskLevel: 'medium',
      },
      decision: entry.decision || { status: entry.status || 'draft' },
      timestamp: entry.timestamp || now,
      createdAt: now,
      updatedAt: now,
      assignedTo: entry.assignedTo,
      tags: entry.tags || [],
      marketSnapshot: entry.marketSnapshot,
      outcome: entry.outcome,
      learnings: entry.learnings,
    };
    this.entries.unshift(full);
    return full;
  }

  update(id: string, updates: Partial<DecisionEntry>): void {
    const idx = this.entries.findIndex(e => e.id === id);
    if (idx >= 0) {
      this.entries[idx] = { ...this.entries[idx], ...updates, updatedAt: new Date().toISOString() };
    }
  }
}

const store = new DecisionJournalStore();

export function getDecisionJournal(): DecisionJournalStore {
  return store;
}
