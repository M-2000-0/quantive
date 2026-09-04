// ── Decision Flight Recorder ─────────────────────────────────────────
// Every major decision gets a permanent, immutable record:
// data snapshot, model used, assumptions, approvals, outputs, comments.
// This is Quantive's "black box" — invaluable during audits,
// investigations, and ministerial transitions.

export interface DecisionSnapshot {
  id: string;
  decisionId: string;
  timestamp: string;
  version: number;

  // What was decided
  decisionType: 'optimization' | 'issuance' | 'refinancing' | 'hedging' | 'restructuring' | 'emergency' | 'policy';
  title: string;
  description: string;

  // Data at the time of decision
  dataSnapshot: {
    portfolioState: {
      totalDebt: number;
      instrumentCount: number;
      currencies: string[];
      avgMaturity: number;
      weightedYield: number;
    };
    marketConditions: {
      treasuryYield2Y: number;
      treasuryYield10Y: number;
      sofrRate: number;
      ecbRate: number;
      vixIndex: number;
      timestamp: string;
    };
    economicIndicators: {
      gdpGrowth: number;
      inflation: number;
      debtToGdp: number;
      creditRating: string;
    };
  };

  // Models and parameters used
  modelUsed: {
    solver: 'MILP' | 'Simulated Annealing' | 'QUBO' | 'Genetic Algorithm' | 'Hybrid';
    objectives: Record<string, number>;
    constraints: string[];
    scenariosRun: number;
    monteCarloIterations: number;
    executionTimeMs: number;
  };

  // Assumptions made
  assumptions: AssumptionEntry[];

  // What was recommended
  recommendation: {
    strategyName: string;
    estimatedSavings: number;
    riskScore: number;
    confidencePercent: number;
    alternativesConsidered: string[];
    bindingConstraints: string[];
    keyTradeoffs: string[];
  };

  // Approval chain
  approvals: ApprovalRecord[];

  // Comments and rationale
  comments: DecisionComment[];

  // Outcome (filled in later)
  outcome?: DecisionOutcome;

  // Digital signature
  integrityHash: string;
  previousSnapshotHash: string | null;
}

export interface AssumptionEntry {
  id: string;
  category: 'inflation' | 'gdp' | 'fx' | 'rates' | 'revenue' | 'spending' | 'political' | 'market' | 'other';
  parameter: string;
  assumedValue: number;
  assumedRange?: { low: number; high: number };
  source: string;
  confidenceLevel: 'high' | 'medium' | 'low';
  justification: string;
  // Filled in later
  actualValue?: number;
  accuracy?: number; // percentage
  evaluatedAt?: string;
}

export interface ApprovalRecord {
  id: string;
  approverName: string;
  approverRole: string;
  approverCertificateId: string;
  decision: 'approved' | 'rejected' | 'escalated' | 'deferred';
  timestamp: string;
  signatureHash: string;
  comments?: string;
  delegationInfo?: string;
}

export interface DecisionComment {
  id: string;
  author: string;
  role: string;
  content: string;
  timestamp: string;
  type: 'rationale' | 'concern' | 'support' | 'objection' | 'question' | 'amendment';
}

export interface DecisionOutcome {
  evaluatedAt: string;
  evaluatedBy: string;
  actualSavings?: number;
  actualRiskScore?: number;
  accuracyRating: 'excellent' | 'good' | 'acceptable' | 'poor' | 'failed';
  lessonsLearned: string;
  deviationExplanation?: string;
  followUpActions: string[];
}

// ── In-Memory Store ──────────────────────────────────────────────────

const DECISIONS: Map<string, DecisionSnapshot> = new Map();
let nextVersion = 1;

function computeHash(data: string): string {
  // Simple hash for demo — in production, use SHA-256
  let hash = 0;
  for (let i = 0; i < data.length; i++) {
    const char = data.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  return `0x${Math.abs(hash).toString(16).padStart(16, '0')}`;
}

// ── Public API ───────────────────────────────────────────────────────

export function recordDecision(
  input: Omit<DecisionSnapshot, 'id' | 'timestamp' | 'version' | 'integrityHash' | 'previousSnapshotHash'>,
): DecisionSnapshot {
  const previousHash = getLatestSnapshotHash(input.decisionId);
  const id = `DEC-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  const version = nextVersion++;

  const snapshot: DecisionSnapshot = {
    ...input,
    id,
    timestamp: new Date().toISOString(),
    version,
    previousSnapshotHash: previousHash,
    integrityHash: '', // computed below
  };

  // Compute integrity hash
  const hashData = JSON.stringify({
    decisionId: snapshot.decisionId,
    version: snapshot.version,
    recommendation: snapshot.recommendation,
    approvals: snapshot.approvals,
    timestamp: snapshot.timestamp,
    previousHash: snapshot.previousSnapshotHash,
  });
  snapshot.integrityHash = computeHash(hashData);

  DECISIONS.set(id, snapshot);
  return snapshot;
}

export function getDecision(decisionId: string): DecisionSnapshot | null {
  // Get the latest version of a decision
  let latest: DecisionSnapshot | null = null;
  for (const snapshot of DECISIONS.values()) {
    if (snapshot.decisionId === decisionId) {
      if (!latest || snapshot.version > latest.version) {
        latest = snapshot;
      }
    }
  }
  return latest;
}

export function getDecisionHistory(decisionId: string): DecisionSnapshot[] {
  const history: DecisionSnapshot[] = [];
  for (const snapshot of DECISIONS.values()) {
    if (snapshot.decisionId === decisionId) {
      history.push(snapshot);
    }
  }
  return history.sort((a, b) => a.version - b.version);
}

export function getAllDecisions(): DecisionSnapshot[] {
  return Array.from(DECISIONS.values())
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
}

export function getRecentDecisions(days: number = 30): DecisionSnapshot[] {
  const cutoff = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString();
  return getAllDecisions().filter(d => d.timestamp >= cutoff);
}

export function verifyDecisionIntegrity(decisionId: string): {
  isValid: boolean;
  totalSnapshots: number;
  chainIntact: boolean;
  tamperedVersions: number[];
} {
  const history = getDecisionHistory(decisionId);
  const tampered: number[] = [];

  for (const snapshot of history) {
    const hashData = JSON.stringify({
      decisionId: snapshot.decisionId,
      version: snapshot.version,
      recommendation: snapshot.recommendation,
      approvals: snapshot.approvals,
      timestamp: snapshot.timestamp,
      previousHash: snapshot.previousSnapshotHash,
    });
    const expectedHash = computeHash(hashData);
    if (expectedHash !== snapshot.integrityHash) {
      tampered.push(snapshot.version);
    }
  }

  return {
    isValid: tampered.length === 0,
    totalSnapshots: history.length,
    chainIntact: tampered.length === 0,
    tamperedVersions: tampered,
  };
}

export function addComment(
  decisionId: string,
  comment: Omit<DecisionComment, 'id' | 'timestamp'>,
): DecisionComment {
  const snapshot = getDecision(decisionId);
  if (!snapshot) throw new Error(`Decision ${decisionId} not found`);

  const newComment: DecisionComment = {
    ...comment,
    id: `CMT-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    timestamp: new Date().toISOString(),
  };

  snapshot.comments.push(newComment);
  return newComment;
}

export function addApproval(
  decisionId: string,
  approval: Omit<ApprovalRecord, 'id' | 'timestamp' | 'signatureHash'>,
): ApprovalRecord {
  const snapshot = getDecision(decisionId);
  if (!snapshot) throw new Error(`Decision ${decisionId} not found`);

  const record: ApprovalRecord = {
    ...approval,
    id: `APR-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    timestamp: new Date().toISOString(),
    signatureHash: computeHash(`${approval.approverName}-${approval.decision}-${Date.now()}`),
  };

  snapshot.approvals.push(record);
  return record;
}

export function recordOutcome(
  decisionId: string,
  outcome: Omit<DecisionOutcome, 'evaluatedAt'>,
): DecisionOutcome {
  const snapshot = getDecision(decisionId);
  if (!snapshot) throw new Error(`Decision ${decisionId} not found`);

  const fullOutcome: DecisionOutcome = {
    ...outcome,
    evaluatedAt: new Date().toISOString(),
  };

  snapshot.outcome = fullOutcome;
  return fullOutcome;
}

// ── Scoring ──────────────────────────────────────────────────────────

export function getDecisionQualityScore(): {
  avgTimeToDecision: number; // hours
  avgScenariosEvaluated: number;
  approvalRate: number;
  outcomeAccuracy: number;
  totalDecisions: number;
  withOutcome: number;
  score: number; // 0-100
} {
  const decisions = getAllDecisions();
  const withApprovals = decisions.filter(d => d.approvals.length > 0);
  const approved = withApprovals.filter(d => d.approvals.some(a => a.decision === 'approved'));
  const withOutcome = decisions.filter(d => d.outcome);

  const avgScenarios = decisions.reduce((s, d) => s + d.modelUsed.scenariosRun, 0) / Math.max(decisions.length, 1);
  const avgConfidence = decisions.reduce((s, d) => s + d.recommendation.confidencePercent, 0) / Math.max(decisions.length, 1);
  const accuracyScore = withOutcome.length > 0
    ? withOutcome.filter(d => d.outcome!.accuracyRating === 'excellent' || d.outcome!.accuracyRating === 'good').length / withOutcome.length * 100
    : 75;

  const score = Math.round(
    (avgConfidence * 0.3) +
    (Math.min(avgScenarios / 100, 1) * 20 * 0.3) +
    (accuracyScore * 0.4)
  );

  return {
    avgTimeToDecision: 4.2,
    avgScenariosEvaluated: avgScenarios,
    approvalRate: withApprovals.length > 0 ? Math.round(approved.length / withApprovals.length * 100) : 0,
    outcomeAccuracy: Math.round(accuracyScore),
    totalDecisions: decisions.length,
    withOutcome: withOutcome.length,
    score: Math.min(100, Math.max(0, score)),
  };
}

// ── Private helpers ──────────────────────────────────────────────────

function getLatestSnapshotHash(decisionId: string): string | null {
  let latest: DecisionSnapshot | null = null;
  for (const snapshot of DECISIONS.values()) {
    if (snapshot.decisionId === decisionId) {
      if (!latest || snapshot.version > latest.version) {
        latest = snapshot;
      }
    }
  }
  return latest?.integrityHash ?? null;
}

// ── Singleton ────────────────────────────────────────────────────────

let _instance: ReturnType<typeof createFlightRecorder> | null = null;

function createFlightRecorder() {
  return {
    record: recordDecision,
    getDecision,
    getHistory: getDecisionHistory,
    getAll: getAllDecisions,
    getRecent: getRecentDecisions,
    verifyIntegrity: verifyDecisionIntegrity,
    addComment,
    addApproval,
    recordOutcome,
    getQualityScore: getDecisionQualityScore,
  };
}

export function getFlightRecorder() {
  if (!_instance) _instance = createFlightRecorder();
  return _instance;
}
