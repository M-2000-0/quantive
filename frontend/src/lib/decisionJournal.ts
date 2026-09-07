// ── Decision Journal Types ───────────────────────────────────────────
// Types and utilities only — no mock data. Data comes from API.

export type DecisionStatus =
  | 'draft' | 'submitted' | 'under_review' | 'approved' | 'rejected'
  | 'executed' | 'recommended' | 'completed' | 'expired';

export interface DecisionResolution {
  status: DecisionStatus;
  decidedBy?: string;
  decidedAt?: number | string;
  reason?: string;
  overrideNotes?: string;
  notes?: string;
}

export interface Recommendation {
  id?: string;
  title?: string;
  action?: string;
  ticker?: string;
  amount?: number;
  rationale?: string;
  confidence: number;
  riskLevel?: 'low' | 'medium' | 'high';
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
  portfolioId?: string;
  recommendation: Recommendation;
  decision: DecisionResolution;
  timestamp: number | string;
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
    measuredAt?: number | string;
    notes?: string;
  };
  learnings?: DecisionLearnings;
}

class DecisionJournalStore {
  protected entries: DecisionEntry[] = [];

  getAll(): DecisionEntry[] {
    return this.entries;
  }

  getAllEntries(): DecisionEntry[] {
    return this.entries;
  }

  getById(id: string): DecisionEntry | undefined {
    return this.entries.find(e => e.id === id);
  }

  getEntriesForPortfolio(portfolioId: string): DecisionEntry[] {
    return this.entries.filter(e => e.portfolioId === portfolioId);
  }

  getEntriesByStatus(status: DecisionStatus): DecisionEntry[] {
    return this.entries.filter(e => e.decision.status === status);
  }

  add(entry: DecisionEntry): void {
    this.entries.unshift(entry);
  }

  /** Record a partial entry (pipelines only know part of the story). */
  addEntry(entry: Partial<DecisionEntry> & { recommendation: Recommendation }): DecisionEntry {
    return this.recordDecision(entry);
  }

  recordDecision(entry: Partial<DecisionEntry> & { recommendation: Recommendation }): DecisionEntry {
    const now = new Date().toISOString();
    const full: DecisionEntry = {
      id: `dec-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
      title: entry.title || entry.recommendation.title || 'Journal entry',
      description: entry.description || entry.recommendation.description || '',
      status: entry.status || entry.decision?.status || 'draft',
      portfolioId: entry.portfolioId,
      recommendation: entry.recommendation,
      decision: entry.decision || { status: entry.status || 'draft' },
      timestamp: entry.timestamp || Date.now(),
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

  updateDecisionStatus(id: string, status: DecisionStatus, decidedBy?: string, notes?: string): void {
    const idx = this.entries.findIndex(e => e.id === id);
    if (idx >= 0) {
      this.entries[idx] = {
        ...this.entries[idx],
        decision: {
          ...this.entries[idx].decision,
          status,
          decidedBy: decidedBy ?? this.entries[idx].decision.decidedBy,
          decidedAt: Date.now(),
          notes: notes ?? this.entries[idx].decision.notes,
        },
        updatedAt: new Date().toISOString(),
      };
    }
  }

  recordOutcome(id: string, outcome: NonNullable<DecisionEntry['outcome']>): void {
    const idx = this.entries.findIndex(e => e.id === id);
    if (idx >= 0) {
      this.entries[idx] = {
        ...this.entries[idx],
        outcome: { ...this.entries[idx].outcome, ...outcome },
        updatedAt: new Date().toISOString(),
      };
    }
  }

  getSummary(): {
    totalDecisions: number;
    approvedRate: number;
    avgConfidence: number;
    topDecisionTypes: Array<{ type: string; count: number }>;
    marketRegimePerformance: Record<string, number>;
  } {
    const total = this.entries.length;
    const approved = this.entries.filter(e =>
      ['approved', 'executed', 'completed'].includes(e.decision.status),
    ).length;
    const avgConfidence = total > 0
      ? this.entries.reduce((s, e) => s + (e.recommendation.confidence || 0), 0) / total
      : 0;
    const byType = new Map<string, number>();
    for (const e of this.entries) {
      const t = e.recommendation.type || 'unknown';
      byType.set(t, (byType.get(t) || 0) + 1);
    }
    return {
      totalDecisions: total,
      approvedRate: total > 0 ? approved / total : 0,
      avgConfidence,
      topDecisionTypes: [...byType.entries()]
        .map(([type, count]) => ({ type, count }))
        .sort((a, b) => b.count - a.count),
      marketRegimePerformance: {},
    };
  }

  update(id: string, updates: Partial<DecisionEntry>): void {
    const idx = this.entries.findIndex(e => e.id === id);
    if (idx >= 0) {
      this.entries[idx] = { ...this.entries[idx], ...updates, updatedAt: new Date().toISOString() };
    }
  }
}

function seedDecision(id: string, portfolioId: string, status: DecisionStatus): DecisionEntry {
  const now = new Date().toISOString();
  return {
    id,
    title: 'Seed decision',
    description: 'Seeded demo decision',
    status,
    portfolioId,
    recommendation: {
      type: 'refinance_opportunity',
      title: 'Seed recommendation',
      description: 'Seed',
      instruments: ['Seed Bond'],
      estimatedSavings: 100000,
      riskImpact: 'Low',
      confidence: 80,
    },
    decision: { status },
    timestamp: Date.now(),
    createdAt: now,
    updatedAt: now,
    tags: [],
  };
}

export class DecisionJournal extends DecisionJournalStore {
  constructor() {
    super();
    this.entries = [
      seedDecision('dec-seed-1', 'demo-pf-001', 'completed'),
      seedDecision('dec-seed-2', 'demo-pf-001', 'recommended'),
      seedDecision('dec-seed-3', 'demo-pf-002', 'approved'),
    ];
  }
}

const store = new DecisionJournalStore();

export function getDecisionJournal(): DecisionJournalStore {
  return store;
}
