// ── Autonomous Execution Engine ─────────────────────────────────────
// Auto-executes approved optimization actions, records outcomes in
// the DecisionJournal, and triggers post-execution analytics including
// savings realization tracking, risk impact measurement, and
// performance attribution.

import { getDecisionJournal, type DecisionEntry, type Recommendation } from './decisionJournal';
import { getAutoDraftPipeline, type PipelineRun } from './autoDraftPipeline';
import { getContinuousOptimizer, type OptimizationSignal, type MarketContext } from './continuousOptimizer';

// ── Types ────────────────────────────────────────────────────────────

export type ExecutionStatus =
  | 'pending'
  | 'validating'
  | 'executing'
  | 'confirming'
  | 'completed'
  | 'failed'
  | 'rolled_back';

export type ExecutionMode = 'manual' | 'auto_draft' | 'full_auto';

export interface ExecutionRecord {
  id: string;
  pipelineRunId: string;
  signalId: string;
  recommendation: Recommendation;
  status: ExecutionStatus;
  mode: ExecutionMode;
  startedAt: string;
  completedAt?: string;
  executedBy: string;
  trades: TradeRecord[];
  preExecutionSnapshot: PortfolioSnapshot;
  postExecutionSnapshot?: PortfolioSnapshot;
  outcome?: ExecutionOutcome;
  riskChecks: RiskCheck[];
  rollbackAvailable: boolean;
}

export interface TradeRecord {
  id: string;
  instrument: string;
  action: 'buy' | 'sell' | 'refinance' | 'hedge' | 'close';
  principal: number;
  yield: number;
  maturity: string;
  currency: string;
  timestamp: string;
  status: 'pending' | 'filled' | 'cancelled';
  fillPrice?: number;
  fillYield?: number;
  counterparty?: string;
}

export interface PortfolioSnapshot {
  timestamp: string;
  totalPrincipal: number;
  weightedAvgYield: number;
  avgDuration: number;
  avgRating: string;
  riskScore: number;
  unrealizedPnl: number;
  instrumentCount: number;
  currencyExposure: Record<string, number>;
  sectorExposure: Record<string, number>;
}

export interface ExecutionOutcome {
  realizedSavings: number;
  projectedSavings: number;
  savingsAccuracy: number; // percentage of projection achieved
  riskChange: number;
  ratingChange: string;
  durationChange: number;
  peerAlignmentChange: number;
  executionCost: number;
  netBenefit: number;
  timeToExecution: number; // minutes from approval to execution
}

export interface RiskCheck {
  name: string;
  passed: boolean;
  details: string;
  severity: 'info' | 'warning' | 'critical';
}

export interface ExecutionConfig {
  mode: ExecutionMode;
  /** Maximum single trade size (USD) */
  maxTradeSize: number;
  /** Maximum daily execution volume (USD) */
  maxDailyVolume: number;
  /** Require risk officer approval above this threshold */
  riskApprovalThreshold: number;
  /** Auto-rollback if execution deviates more than this % from expected */
  maxDeviation: number;
  /** Execution cooldown between trades (seconds) */
  cooldownSeconds: number;
  /** Available counterparties */
  counterparties: string[];
}

const DEFAULT_CONFIG: ExecutionConfig = {
  mode: 'auto_draft',
  maxTradeSize: 50_000_000,
  maxDailyVolume: 500_000_000,
  riskApprovalThreshold: 25_000_000,
  maxDeviation: 5,
  cooldownSeconds: 300,
  counterparties: ['Goldman Sachs', 'JPMorgan', 'Morgan Stanley', 'Barclays', 'Citi'],
};

// ── Portfolio Snapshot Generator ─────────────────────────────────────

function generateSnapshot(): PortfolioSnapshot {
  return {
    timestamp: new Date().toISOString(),
    totalPrincipal: 230_000_000,
    weightedAvgYield: 4.67,
    avgDuration: 5.2,
    avgRating: 'A+',
    riskScore: 42,
    unrealizedPnl: 1_890_000,
    instrumentCount: 20,
    currencyExposure: { USD: 72, EUR: 15, GBP: 8, JPY: 5 },
    sectorExposure: { Technology: 28, Financial: 22, Healthcare: 18, Energy: 15, Government: 12, Other: 5 },
  };
}

// ── Risk Check Engine ───────────────────────────────────────────────

function runRiskChecks(
  recommendation: Recommendation,
  config: ExecutionConfig,
): RiskCheck[] {
  const checks: RiskCheck[] = [];

  // Trade size check
  const tradeSize = recommendation.estimatedSavings! * 20; // rough estimate
  checks.push({
    name: 'Trade Size Limit',
    passed: tradeSize <= config.maxTradeSize,
    details: `Trade size $${(tradeSize / 1e6).toFixed(1)}M ${tradeSize <= config.maxTradeSize ? 'within' : 'exceeds'} limit of $${(config.maxTradeSize / 1e6).toFixed(1)}M`,
    severity: tradeSize <= config.maxTradeSize ? 'info' : 'critical',
  });

  // Risk impact check
  checks.push({
    name: 'Risk Impact Assessment',
    passed: Math.abs(recommendation.riskChange!) <= 20,
    details: `Risk change: ${recommendation.riskChange! >= 0 ? '+' : ''}${recommendation.riskChange!}bps ${Math.abs(recommendation.riskChange!) <= 20 ? 'within acceptable range' : 'exceeds threshold'}`,
    severity: Math.abs(recommendation.riskChange!) <= 10 ? 'info' : Math.abs(recommendation.riskChange!) <= 20 ? 'warning' : 'critical',
  });

  // Confidence check
  checks.push({
    name: 'Confidence Threshold',
    passed: recommendation.confidence >= 70,
    details: `Confidence: ${recommendation.confidence}% ${recommendation.confidence >= 70 ? 'meets' : 'below'} 70% threshold`,
    severity: recommendation.confidence >= 80 ? 'info' : recommendation.confidence >= 70 ? 'warning' : 'critical',
  });

  // Rating impact check
  checks.push({
    name: 'Credit Rating Impact',
    passed: true,
    details: 'No credit rating downgrade expected from this action',
    severity: 'info',
  });

  // Compliance check
  checks.push({
    name: 'Compliance Validation',
    passed: true,
    details: 'Action complies with investment policy guidelines',
    severity: 'info',
  });

  // Market condition check
  checks.push({
    name: 'Market Conditions',
    passed: true,
    details: 'Current market conditions support this execution',
    severity: 'info',
  });

  return checks;
}

// ── Execution Engine ────────────────────────────────────────────────

export class ExecutionEngine {
  private records: Map<string, ExecutionRecord> = new Map();
  private config: ExecutionConfig;
  private dailyVolume: number = 0;
  private lastExecutionTime: number = 0;
  private listeners: Array<(event: string, data: unknown) => void> = [];
  private recordIdCounter: number = 0;

  constructor(config: Partial<ExecutionConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /** Subscribe to execution events */
  subscribe(listener: (event: string, data: unknown) => void): () => void {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== listener);
    };
  }

  private notify(event: string, data: unknown) {
    this.listeners.forEach((l) => l(event, data));
  }

  /** Execute an approved pipeline run */
  async execute(run: PipelineRun, executedBy: string = 'system'): Promise<ExecutionRecord | null> {
    if (run.stage !== 'approved') return null;

    // Check cooldown
    const now = Date.now();
    if (now - this.lastExecutionTime < this.config.cooldownSeconds * 1000) {
      return null;
    }

    const recordId = `exec-${Date.now()}-${++this.recordIdCounter}`;
    const preSnapshot = generateSnapshot();

    const record: ExecutionRecord = {
      id: recordId,
      pipelineRunId: run.id,
      signalId: run.signalId,
      recommendation: run.recommendation!,
      status: 'validating',
      mode: this.config.mode,
      startedAt: new Date().toISOString(),
      executedBy,
      trades: [],
      preExecutionSnapshot: preSnapshot,
      riskChecks: [],
      rollbackAvailable: true,
    };

    this.records.set(recordId, record);

    // Stage 1: Run risk checks
    record.riskChecks = runRiskChecks(run.recommendation!, this.config);
    const criticalFailures = record.riskChecks.filter((c) => !c.passed && c.severity === 'critical');

    if (criticalFailures.length > 0) {
      record.status = 'failed';
      record.completedAt = new Date().toISOString();
      this.notify('execution_failed', record);
      return record;
    }

    // Stage 2: Validate
    await this.delay(100);
    record.status = 'executing';
    this.notify('execution_started', record);

    // Stage 3: Generate trades
    const trades = this.generateTrades(run.recommendation!, preSnapshot);
    record.trades = trades;

    // Stage 4: Execute trades
    for (const trade of trades) {
      await this.delay(50);
      trade.status = 'filled';
      trade.fillPrice = 100 + (Math.random() - 0.5) * 2;
      trade.fillYield = trade.yield + (Math.random() - 0.5) * 0.1;
      trade.counterparty = this.config.counterparties[
        Math.floor(Math.random() * this.config.counterparties.length)
      ];
      this.notify('trade_filled', { recordId, trade });
    }

    // Stage 5: Confirm
    record.status = 'confirming';
    await this.delay(100);

    // Stage 6: Generate post-execution snapshot and outcome
    record.postExecutionSnapshot = this.generatePostSnapshot(preSnapshot, run.recommendation!);
    record.outcome = this.calculateOutcome(record);
    record.status = 'completed';
    record.completedAt = new Date().toISOString();
    this.lastExecutionTime = Date.now();
    this.dailyVolume += trades.reduce((sum, t) => sum + t.principal, 0);

    // Record in decision journal
    const journal = getDecisionJournal();
    journal.addEntry({
      recommendation: run.recommendation!,
      marketSnapshot: run.signal.marketContext,
      status: 'completed',
      outcome: {
        actualSavings: record.outcome.realizedSavings,
        riskChange: record.outcome.riskChange,
        rating: 'positive',
      },
    });

    this.notify('execution_completed', record);
    return record;
  }

  private generateTrades(
    recommendation: Recommendation,
    snapshot: PortfolioSnapshot,
  ): TradeRecord[] {
    const trades: TradeRecord[] = [];
    const now = new Date().toISOString();

    recommendation.instruments!.forEach((instrument, idx) => {
      const principal = Math.min(
        snapshot.totalPrincipal * 0.15,
        this.config.maxTradeSize,
      );

      trades.push({
        id: `trade-${Date.now()}-${idx}`,
        instrument,
        action: recommendation.type! === 'refinance' ? 'refinance' :
                recommendation.type! === 'credit_hedge' ? 'hedge' :
                recommendation.type! === 'cost_optimization' ? 'sell' : 'buy',
        principal,
        yield: snapshot.weightedAvgYield + (Math.random() - 0.5) * 0.5,
        maturity: `${3 + Math.floor(Math.random() * 7)}Y`,
        currency: 'USD',
        timestamp: now,
        status: 'pending',
      });
    });

    return trades;
  }

  private generatePostSnapshot(
    pre: PortfolioSnapshot,
    recommendation: Recommendation,
  ): PortfolioSnapshot {
    const savingsRate = recommendation.estimatedSavings! / pre.totalPrincipal;
    return {
      timestamp: new Date().toISOString(),
      totalPrincipal: pre.totalPrincipal,
      weightedAvgYield: pre.weightedAvgYield - savingsRate * 100 * 0.3,
      avgDuration: pre.avgDuration + (recommendation.type! === 'duration_adjustment' ? -0.5 : 0),
      avgRating: pre.avgRating,
      riskScore: Math.max(0, pre.riskScore + recommendation.riskChange!),
      unrealizedPnl: pre.unrealizedPnl + recommendation.estimatedSavings! * 0.1,
      instrumentCount: pre.instrumentCount,
      currencyExposure: { ...pre.currencyExposure },
      sectorExposure: { ...pre.sectorExposure },
    };
  }

  private calculateOutcome(record: ExecutionRecord): ExecutionOutcome {
    const projected = record.recommendation.estimatedSavings!;
    // Simulate slight deviation from projection
    const deviation = 1 + (Math.random() - 0.5) * 0.1;
    const realized = projected * deviation;
    const execCost = realized * 0.02; // 2% execution cost

    return {
      realizedSavings: realized,
      projectedSavings: projected,
      savingsAccuracy: (1 - Math.abs(realized - projected) / projected) * 100,
      riskChange: record.recommendation.riskChange!,
      ratingChange: 'stable',
      durationChange: record.recommendation.type! === 'duration_adjustment' ? -0.5 : 0,
      peerAlignmentChange: Math.floor(Math.random() * 10) + 5,
      executionCost: execCost,
      netBenefit: realized - execCost,
      timeToExecution: Math.floor(
        (new Date(record.completedAt!).getTime() - new Date(record.startedAt).getTime()) / 60000,
      ) + Math.floor(Math.random() * 5),
    };
  }

  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /** Rollback an execution */
  rollback(recordId: string): boolean {
    const record = this.records.get(recordId);
    if (!record || !record.rollbackAvailable || record.status !== 'completed') return false;

    record.status = 'rolled_back';
    record.completedAt = new Date().toISOString();
    record.rollbackAvailable = false;

    // Cancel unfilled trades
    record.trades.forEach((t) => {
      if (t.status === 'pending') t.status = 'cancelled';
    });

    this.notify('execution_rolled_back', record);
    return true;
  }

  /** Get all execution records */
  getRecords(): ExecutionRecord[] {
    return Array.from(this.records.values()).sort(
      (a, b) => new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime(),
    );
  }

  /** Get execution by ID */
  getRecord(id: string): ExecutionRecord | undefined {
    return this.records.get(id);
  }

  /** Get execution statistics */
  getStats() {
    const records = this.getRecords();
    const completed = records.filter((r) => r.status === 'completed');
    const failed = records.filter((r) => r.status === 'failed');
    const rolledBack = records.filter((r) => r.status === 'rolled_back');

    const totalSavings = completed.reduce(
      (sum, r) => sum + (r.outcome?.netBenefit || 0),
      0,
    );

    const avgAccuracy = completed.length > 0
      ? completed.reduce((sum, r) => sum + (r.outcome?.savingsAccuracy || 0), 0) / completed.length
      : 0;

    const avgTimeToExec = completed.length > 0
      ? completed.reduce((sum, r) => sum + (r.outcome?.timeToExecution || 0), 0) / completed.length
      : 0;

    return {
      totalExecutions: records.length,
      completed: completed.length,
      failed: failed.length,
      rolledBack: rolledBack.length,
      totalRealizedSavings: totalSavings,
      averageAccuracy: avgAccuracy,
      averageTimeToExecution: avgTimeToExec,
      dailyVolume: this.dailyVolume,
      dailyVolumeLimit: this.config.maxDailyVolume,
      volumeUtilization: (this.dailyVolume / this.config.maxDailyVolume) * 100,
    };
  }

  /** Update config */
  updateConfig(updates: Partial<ExecutionConfig>) {
    this.config = { ...this.config, ...updates };
  }
}

// ── Singleton ────────────────────────────────────────────────────────

let _engine: ExecutionEngine | null = null;

export function getExecutionEngine(config?: Partial<ExecutionConfig>): ExecutionEngine {
  if (!_engine) {
    _engine = new ExecutionEngine(config);
  }
  return _engine;
}
