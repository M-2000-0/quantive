// ── Auto-Draft Pipeline ────────────────────────────────────────────────
// Connects continuousOptimizer signals → SmartReportGenerator →
// ApprovalWorkflow into a single automated pipeline. When the
// continuous monitor detects a signal, this system auto-generates
// a recommendation, drafts a committee memo, and routes for approval.

import { getContinuousOptimizer, type OptimizationSignal } from './continuousOptimizer';
import { getDecisionJournal, type DecisionEntry, type Recommendation } from './decisionJournal';

// ── Pipeline Stages ──────────────────────────────────────────────────

export type PipelineStage =
  | 'signal_detected'
  | 'recommendation_generated'
  | 'memo_drafted'
  | 'routed_for_approval'
  | 'under_review'
  | 'approved'
  | 'rejected'
  | 'executed'
  | 'completed'
  | 'failed';

export interface PipelineRun {
  id: string;
  signalId: string;
  signal: OptimizationSignal;
  stage: PipelineStage;
  recommendation: Recommendation | null;
  memoDraft: MemoDraft | null;
  approvalId: string | null;
  createdAt: string;
  updatedAt: string;
  stageHistory: Array<{ stage: PipelineStage; timestamp: string; note?: string }>;
  error?: string;
}

export interface MemoDraft {
  title: string;
  summary: string;
  signalType: string;
  signalDescription: string;
  recommendedAction: string;
  estimatedSavings: number;
  riskAssessment: string;
  peerAlignment: string;
  urgency: 'immediate' | 'this_week' | 'this_quarter' | 'when_convenient';
  assignees: string[];
  deadline: string;
  sections: MemoSection[];
}

export interface MemoSection {
  heading: string;
  content: string;
  dataPoints?: Array<{ label: string; value: string }>;
}

export interface PipelineConfig {
  /** Auto-draft memos for signals above this severity */
  autoDraftSeverity: 'low' | 'medium' | 'high' | 'critical';
  /** Auto-route for approval (vs. holding for manual review) */
  autoRoute: boolean;
  /** Auto-execute after approval (vs. requiring manual execution) */
  autoExecute: boolean;
  /** Default assignees by signal type */
  defaultAssignees: Record<string, string[]>;
  /** Maximum pipeline runs per day */
  dailyLimit: number;
  /** Cooldown between runs for same signal type (minutes) */
  cooldownMinutes: number;
}

const DEFAULT_CONFIG: PipelineConfig = {
  autoDraftSeverity: 'medium',
  autoRoute: true,
  autoExecute: false,
  defaultAssignees: {
    refinance_opportunity: ['treasury_analyst', 'risk_officer'],
    duration_mismatch: ['portfolio_manager', 'risk_officer'],
    credit_deterioration: ['credit_analyst', 'compliance_officer'],
    spread_widening: ['risk_officer', 'portfolio_manager'],
    maturity_approaching: ['treasury_analyst', 'portfolio_manager'],
    cost_reduction: ['treasury_analyst', 'treasury_director'],
  },
  dailyLimit: 20,
  cooldownMinutes: 60,
};

// ── Urgency Mapping ──────────────────────────────────────────────────

const URGENCY_MAP: Record<string, MemoDraft['urgency']> = {
  critical: 'immediate',
  high: 'this_week',
  medium: 'this_quarter',
  low: 'when_convenient',
};

const SEVERITY_ORDER = ['low', 'medium', 'high', 'critical'];

function meetsSeverityThreshold(signalSeverity: string, threshold: string): boolean {
  return SEVERITY_ORDER.indexOf(signalSeverity) >= SEVERITY_ORDER.indexOf(threshold);
}

// ── Memo Draft Generator ─────────────────────────────────────────────

function generateMemoDraft(
  signal: OptimizationSignal,
  config: PipelineConfig,
): MemoDraft {
  const assignees = config.defaultAssignees[signal.type] || ['portfolio_manager'];
  const urgency = URGENCY_MAP[signal.severity] || 'this_quarter';

  const deadline = (() => {
    const now = new Date();
    switch (urgency) {
      case 'immediate':
        now.setHours(now.getHours() + 4);
        break;
      case 'this_week':
        now.setDate(now.getDate() + 3);
        break;
      case 'this_quarter':
        now.setDate(now.getDate() + 30);
        break;
      default:
        now.setDate(now.getDate() + 90);
    }
    return now.toISOString();
  })();

  const sections: MemoSection[] = [
    {
      heading: 'Signal Overview',
      content: signal.description,
      dataPoints: [
        { label: 'Signal Type', value: signal.type.replace(/_/g, ' ') },
        { label: 'Severity', value: signal.severity.toUpperCase() },
        { label: 'Confidence', value: `${signal.confidence}%` },
        { label: 'Affected Instruments', value: `${signal.affectedInstruments.length}` },
      ],
    },
    {
      heading: 'Market Context',
      content: `Current market conditions support this signal. ${signal.marketContext.fedFundsRate > 5 ? 'With elevated rates, ' : ''}Credit spreads are at ${signal.marketContext.creditSpreads}bps and VIX is at ${signal.marketContext.vix}.`,
      dataPoints: [
        { label: 'Fed Funds Rate', value: `${signal.marketContext.fedFundsRate}%` },
        { label: '10Y Treasury', value: `${signal.marketContext.treasury10Y}%` },
        { label: 'Credit Spreads', value: `${signal.marketContext.creditSpreads}bps` },
        { label: 'VIX', value: signal.marketContext.vix.toFixed(1) },
      ],
    },
    {
      heading: 'Affected Holdings',
      content: `This signal affects ${signal.affectedInstruments.length} instrument(s) in the portfolio.`,
      dataPoints: signal.affectedInstruments.map((inst) => ({
        label: inst.name,
        value: `$${(inst.principal / 1e6).toFixed(1)}M — ${inst.type}`,
      })),
    },
    {
      heading: 'Recommendation',
      content: getRecommendationText(signal),
      dataPoints: [
        { label: 'Estimated Savings', value: `$${(signal.estimatedSavings / 1e3).toFixed(0)}K/year` },
        { label: 'Risk Impact', value: signal.riskImpact >= 0 ? `+${signal.riskImpact} bps` : `${signal.riskImpact} bps` },
        { label: 'Priority', value: signal.priority >= 80 ? 'HIGH' : signal.priority >= 50 ? 'MEDIUM' : 'LOW' },
      ],
    },
    {
      heading: 'Peer Intelligence',
      content: `${signal.peerAlignment}% of similar portfolios have taken similar action in the past 30 days. This aligns with the current consensus trend.`,
      dataPoints: [
        { label: 'Peer Alignment', value: `${signal.peerAlignment}%` },
        { label: 'Consensus Trend', value: signal.trendDirection === 'increasing' ? '↗ Growing' : signal.trendDirection === 'decreasing' ? '↘ Declining' : '→ Stable' },
      ],
    },
    {
      heading: 'Risk Disclosure',
      content: 'This recommendation is generated by the continuous optimization engine based on current market conditions. Actual results may vary. This memo should be reviewed by qualified personnel before any action is taken. Past performance is not indicative of future results.',
    },
  ];

  return {
    title: `Auto-Draft: ${formatSignalType(signal.type)} — ${signal.severity.toUpperCase()} Priority`,
    summary: `The continuous optimization engine detected a ${signal.severity} priority ${signal.type.replace(/_/g, ' ')} signal affecting ${signal.affectedInstruments.length} holding(s) with estimated savings of $${(signal.estimatedSavings / 1e3).toFixed(0)}K/year. Recommended action: ${getShortRecommendation(signal)}.`,
    signalType: signal.type,
    signalDescription: signal.description,
    recommendedAction: getRecommendationText(signal),
    estimatedSavings: signal.estimatedSavings,
    riskAssessment: `Risk impact: ${signal.riskImpact >= 0 ? '+' : ''}${signal.riskImpact} bps. Confidence: ${signal.confidence}%.`,
    peerAlignment: `${signal.peerAlignment}% of similar portfolios aligned.`,
    urgency,
    assignees,
    deadline,
    sections,
  };
}

function getRecommendationText(signal: OptimizationSignal): string {
  switch (signal.type) {
    case 'refinance_opportunity':
      return `Consider refinancing ${signal.affectedInstruments.map((i) => i.name).join(', ')} to capture lower rates. Current rates are ${signal.marketContext.fedFundsRate}% with spreads at ${signal.marketContext.creditSpreads}bps, presenting a favorable refinancing window.`;
    case 'duration_mismatch':
      return `Portfolio duration is misaligned with the current yield curve. Consider adjusting maturities by ${signal.affectedInstruments.length > 1 ? 'staggering' : 'extending'} positions to better match liability profile.`;
    case 'credit_deterioration':
      return `Credit spreads on ${signal.affectedInstruments.map((i) => i.name).join(', ')} have widened. Consider reducing exposure or adding credit protection. Monitor for further deterioration.`;
    case 'spread_widening':
      return `Credit spread widening detected on portfolio holdings. Consider reviewing credit quality and potentially hedging with CDS or reducing high-yield allocation.`;
    case 'maturity_approaching':
      return `${signal.affectedInstruments.map((i) => i.name).join(', ')} approaching maturity. Plan reinvestment strategy to maintain yield and duration targets.`;
    case 'cost_reduction':
      return `Opportunity to reduce funding costs by ${signal.affectedInstruments.map((i) => i.name).join(', ')}. Consider alternative instruments or structures for better pricing.`;
    default:
      return `Review the affected holdings and consider the recommended adjustment based on current market conditions.`;
  }
}

function getShortRecommendation(signal: OptimizationSignal): string {
  switch (signal.type) {
    case 'refinance_opportunity': return 'refinance at current rates';
    case 'duration_mismatch': return 'adjust duration positioning';
    case 'credit_deterioration': return 'reduce credit exposure';
    case 'spread_widening': return 'hedge credit risk';
    case 'maturity_approaching': return 'plan reinvestment';
    case 'cost_reduction': return 'optimize funding costs';
    default: return 'review and adjust';
  }
}

function formatSignalType(type: string): string {
  return type.split('_').map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

// ── Pipeline Service ─────────────────────────────────────────────────

export class AutoDraftPipeline {
  private runs: Map<string, PipelineRun> = new Map();
  private config: PipelineConfig;
  private dailyRunCount: number = 0;
  private lastRunDates: Map<string, Date> = new Map();
  private listeners: Array<(run: PipelineRun) => void> = [];
  private runIdCounter: number = 0;

  constructor(config: Partial<PipelineConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /** Subscribe to pipeline run updates */
  subscribe(listener: (run: PipelineRun) => void): () => void {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== listener);
    };
  }

  private notify(run: PipelineRun) {
    this.listeners.forEach((l) => l(run));
  }

  /** Check cooldown for a signal type */
  private isOnCooldown(signalType: string): boolean {
    const lastRun = this.lastRunDates.get(signalType);
    if (!lastRun) return false;
    const elapsed = (Date.now() - lastRun.getTime()) / 60000;
    return elapsed < this.config.cooldownMinutes;
  }

  /** Process a signal through the pipeline */
  async processSignal(signal: OptimizationSignal): Promise<PipelineRun | null> {
    // Check severity threshold
    if (!meetsSeverityThreshold(signal.severity, this.config.autoDraftSeverity)) {
      return null;
    }

    // Check daily limit
    if (this.dailyRunCount >= this.config.dailyLimit) {
      return null;
    }

    // Check cooldown
    if (this.isOnCooldown(signal.type)) {
      return null;
    }

    const runId = `pipeline-${Date.now()}-${++this.runIdCounter}`;
    const now = new Date().toISOString();

    const run: PipelineRun = {
      id: runId,
      signalId: signal.id,
      signal,
      stage: 'signal_detected',
      recommendation: null,
      memoDraft: null,
      approvalId: null,
      createdAt: now,
      updatedAt: now,
      stageHistory: [{ stage: 'signal_detected', timestamp: now }],
    };

    this.runs.set(runId, run);
    this.dailyRunCount++;
    this.lastRunDates.set(signal.type, new Date());

    // Stage 1: Generate recommendation
    await this.advanceStage(run, 'recommendation_generated', () => {
      run.recommendation = generateRecommendation(signal);
    });

    // Stage 2: Draft memo
    await this.advanceStage(run, 'memo_drafted', () => {
      run.memoDraft = generateMemoDraft(signal, this.config);
    });

    // Stage 3: Route for approval (if auto-route enabled)
    if (this.config.autoRoute) {
      await this.advanceStage(run, 'routed_for_approval', () => {
        run.approvalId = `approval-${runId}`;
      });

      // Stage 4: Simulate approval routing (in production, this waits for real approval)
      await this.advanceStage(run, 'under_review', () => {
        // Approval workflow is now active
      });
    }

    return run;
  }

  private async advanceStage(
    run: PipelineRun,
    nextStage: PipelineStage,
    action: () => void,
  ): Promise<void> {
    // Simulate async processing delay
    await new Promise((resolve) => setTimeout(resolve, 50));
    action();
    run.stage = nextStage;
    run.updatedAt = new Date().toISOString();
    run.stageHistory.push({
      stage: nextStage,
      timestamp: run.updatedAt,
    });
    this.notify(run);
  }

  /** Approve a pipeline run */
  approve(runId: string, approver: string, notes?: string): PipelineRun | null {
    const run = this.runs.get(runId);
    if (!run || (run.stage !== 'under_review' && run.stage !== 'routed_for_approval')) {
      return null;
    }
    run.stage = 'approved';
    run.updatedAt = new Date().toISOString();
    run.stageHistory.push({
      stage: 'approved',
      timestamp: run.updatedAt,
      note: `Approved by ${approver}${notes ? `: ${notes}` : ''}`,
    });
    this.notify(run);

    // Record in decision journal
    const journal = getDecisionJournal();
    journal.addEntry({
      recommendation: run.recommendation!,
      marketSnapshot: run.signal.marketContext,
      status: 'approved',
    });

    return run;
  }

  /** Reject a pipeline run */
  reject(runId: string, rejector: string, reason: string): PipelineRun | null {
    const run = this.runs.get(runId);
    if (!run || (run.stage !== 'under_review' && run.stage !== 'routed_for_approval')) {
      return null;
    }
    run.stage = 'rejected';
    run.updatedAt = new Date().toISOString();
    run.stageHistory.push({
      stage: 'rejected',
      timestamp: run.updatedAt,
      note: `Rejected by ${rejector}: ${reason}`,
    });
    this.notify(run);
    return run;
  }

  /** Execute an approved pipeline run */
  execute(runId: string, executor: string): PipelineRun | null {
    const run = this.runs.get(runId);
    if (!run || run.stage !== 'approved') return null;
    run.stage = 'executed';
    run.updatedAt = new Date().toISOString();
    run.stageHistory.push({
      stage: 'executed',
      timestamp: run.updatedAt,
      note: `Executed by ${executor}`,
    });
    this.notify(run);
    return run;
  }

  /** Mark a pipeline run as completed */
  complete(runId: string): PipelineRun | null {
    const run = this.runs.get(runId);
    if (!run || run.stage !== 'executed') return null;
    run.stage = 'completed';
    run.updatedAt = new Date().toISOString();
    run.stageHistory.push({ stage: 'completed', timestamp: run.updatedAt });
    this.notify(run);
    return run;
  }

  /** Get all pipeline runs */
  getRuns(): PipelineRun[] {
    return Array.from(this.runs.values()).sort(
      (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
    );
  }

  /** Get pipeline runs by stage */
  getRunsByStage(stage: PipelineStage): PipelineRun[] {
    return this.getRuns().filter((r) => r.stage === stage);
  }

  /** Get pipeline statistics */
  getStats() {
    const runs = this.getRuns();
    const byStage = runs.reduce(
      (acc, run) => {
        acc[run.stage] = (acc[run.stage] || 0) + 1;
        return acc;
      },
      {} as Record<string, number>,
    );

    const totalSavings = runs
      .filter((r) => r.stage === 'completed' && r.memoDraft)
      .reduce((sum, r) => sum + (r.memoDraft?.estimatedSavings || 0), 0);

    return {
      totalRuns: runs.length,
      byStage,
      dailyRunCount: this.dailyRunCount,
      dailyLimit: this.config.dailyLimit,
      totalEstimatedSavings: totalSavings,
      approvalRate:
        (byStage['approved'] || 0) + (byStage['rejected'] || 0) > 0
          ? ((byStage['approved'] || 0) / ((byStage['approved'] || 0) + (byStage['rejected'] || 0))) * 100
          : 0,
    };
  }

  /** Update pipeline config */
  updateConfig(updates: Partial<PipelineConfig>) {
    this.config = { ...this.config, ...updates };
  }

  /** Reset daily counter (call at midnight) */
  resetDailyCounter() {
    this.dailyRunCount = 0;
  }
}

function generateRecommendation(signal: OptimizationSignal): Recommendation {
  return {
    type: signal.type === 'refinance_opportunity' ? 'refinance' :
          signal.type === 'duration_mismatch' ? 'duration_adjustment' :
          signal.type === 'credit_deterioration' || signal.type === 'spread_widening' ? 'credit_hedge' :
          signal.type === 'maturity_approaching' ? 'reinvestment' : 'cost_optimization',
    instruments: signal.affectedInstruments.map((i) => i.name),
    estimatedSavings: signal.estimatedSavings,
    confidence: signal.confidence,
    riskChange: signal.riskImpact,
    description: getRecommendationText(signal),
  };
}

// ── Singleton ────────────────────────────────────────────────────────

let _pipeline: AutoDraftPipeline | null = null;

export function getAutoDraftPipeline(config?: Partial<PipelineConfig>): AutoDraftPipeline {
  if (!_pipeline) {
    _pipeline = new AutoDraftPipeline(config);
  }
  return _pipeline;
}

// ── Mock Demo Pipeline Runs ──────────────────────────────────────────

export function generateDemoPipelineRuns(): PipelineRun[] {
  const optimizer = getContinuousOptimizer();
  const signals = optimizer.getSignals();
  const pipeline = getAutoDraftPipeline();
  const runs: PipelineRun[] = [];

  // Create demo runs from first 3 signals
  for (let i = 0; i < Math.min(3, signals.length); i++) {
    const signal = signals[i];
    const now = new Date();
    now.setHours(now.getHours() - (3 - i) * 4);
    const createdAt = now.toISOString();

    const recommendation = generateRecommendation(signal);
    const memoDraft = generateMemoDraft(signal, pipeline['config']);

    const stages: PipelineStage[] = i === 0
      ? ['signal_detected', 'recommendation_generated', 'memo_drafted', 'routed_for_approval', 'under_review', 'approved', 'executed', 'completed']
      : i === 1
      ? ['signal_detected', 'recommendation_generated', 'memo_drafted', 'routed_for_approval', 'under_review', 'approved']
      : ['signal_detected', 'recommendation_generated', 'memo_drafted', 'routed_for_approval', 'under_review'];

    const stageHistory = stages.map((stage, idx) => {
      const ts = new Date(now.getTime() + idx * 300000).toISOString();
      return { stage, timestamp: ts, note: idx === stages.length - 1 ? 'Latest update' : undefined };
    });

    const run: PipelineRun = {
      id: `pipeline-demo-${i + 1}`,
      signalId: signal.id,
      signal,
      stage: stages[stages.length - 1],
      recommendation,
      memoDraft,
      approvalId: i < 2 ? `approval-demo-${i + 1}` : null,
      createdAt,
      updatedAt: stageHistory[stageHistory.length - 1].timestamp,
      stageHistory,
    };

    runs.push(run);
  }

  return runs;
}
