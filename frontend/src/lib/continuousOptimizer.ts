// ── Continuous Optimization Monitor ───────────────────────────────────
// Re-evaluates portfolio positions whenever market data changes.
// Replaces one-shot optimization with always-on intelligence.

import { setCache, getCache } from './marketCache';
import { validatePriceUpdate } from './marketValidation';

export interface OptimizationSignal {
  id: string;
  portfolioId: string;
  type: 'refinance_opportunity' | 'duration_mismatch' | 'credit_deterioration' | 'spread_widening' | 'rate_shift' | 'maturity_approaching' | 'cost_reduction';
  severity: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  description: string;
  currentPosition: {
    instrument: string;
    currentValue: number;
    yield: number;
    spread: number;
    maturity: string;
  };
  recommendedAction: {
    action: string;
    estimatedSavings: number;
    riskImpact: string;
    confidence: number;
    timeframe: string;
  };
  triggerReason: string;
  detectedAt: number;
  expiresAt: number;
  status: 'new' | 'acknowledged' | 'acted' | 'expired' | 'dismissed';
  confidence?: number;
  affectedInstruments?: Array<{ name: string }>;
  marketContext?: MarketContext & { creditSpreads?: number };
  estimatedSavings?: number;
  riskImpact?: number;
  priority?: number;
  peerAlignment?: number;
  trendDirection?: 'increasing' | 'decreasing' | 'stable';
}

export interface PortfolioSnapshot {
  portfolioId: string;
  timestamp: number;
  totalPrincipal: number;
  weightedYield: number;
  weightedMaturity: number;
  weightedSpread: number;
  duration: number;
  instruments: Array<{
    id: string;
    name: string;
    principal: number;
    yield: number;
    spread: number;
    maturityDate: string;
    daysToMaturity: number;
    creditRating: string;
  }>;
}

export interface MarketContext {
  timestamp: number;
  fedFundsRate: number;
  treasury10Y: number;
  treasury2Y: number;
  yieldCurveSlope: number; // 10Y - 2Y in bps
  igSpread: number;
  hySpread: number;
  vix: number;
  changes: {
    fedFundsRate: number;
    treasury10Y: number;
    igSpread: number;
    hySpread: number;
  };
}

// ── Signal Generation Engine ──────────────────────────────────────────

function generateRefinanceSignals(snapshot: PortfolioSnapshot, context: MarketContext): OptimizationSignal[] {
  const signals: OptimizationSignal[] = [];

  snapshot.instruments.forEach((inst) => {
    // If rates dropped significantly since instrument was issued, refinance opportunity
    if (context.changes.treasury10Y < -20 && inst.spread > 100) {
      const estimatedSavings = inst.principal * (context.changes.treasury10Y / 10000);
      signals.push({
        id: `sig-refi-${inst.id}-${Date.now()}`,
        portfolioId: snapshot.portfolioId,
        type: 'refinance_opportunity',
        severity: estimatedSavings > 100000 ? 'high' : 'medium',
        title: `Refinance opportunity: ${inst.name}`,
        description: `Treasury yields dropped ${Math.abs(context.changes.treasury10Y)}bps. Refinancing this ${inst.spread}bps spread instrument could save ~$${Math.abs(estimatedSavings).toFixed(0)}.`,
        currentPosition: {
          instrument: inst.name,
          currentValue: inst.principal,
          yield: inst.yield,
          spread: inst.spread,
          maturity: inst.maturityDate,
        },
        recommendedAction: {
          action: `Refinance at current ${inst.spread - Math.round(context.changes.treasury10Y * 0.3)}bps spread`,
          estimatedSavings: Math.abs(estimatedSavings),
          riskImpact: 'Low — same credit quality, lower cost',
          confidence: 75,
          timeframe: 'Execute within 30 days',
        },
        triggerReason: `Treasury 10Y fell ${Math.abs(context.changes.treasury10Y)}bps to ${context.treasury10Y}%`,
        detectedAt: Date.now(),
        expiresAt: Date.now() + 30 * 24 * 60 * 60 * 1000, // 30 days
        status: 'new',
      });
    }
  });

  return signals;
}

function generateDurationSignals(snapshot: PortfolioSnapshot, context: MarketContext): OptimizationSignal[] {
  const signals: OptimizationSignal[] = [];

  // If yield curve inverted or steepened significantly, flag duration mismatch
  if (Math.abs(context.yieldCurveSlope) < 20 || context.yieldCurveSlope < -10) {
    signals.push({
      id: `sig-dur-${snapshot.portfolioId}-${Date.now()}`,
      portfolioId: snapshot.portfolioId,
      type: 'duration_mismatch',
      severity: context.yieldCurveSlope < -10 ? 'critical' : 'high',
      title: 'Duration mismatch detected',
      description: `Yield curve ${context.yieldCurveSlope < 0 ? 'inverted' : 'flat'} at ${context.yieldCurveSlope}bps. Portfolio duration of ${snapshot.duration.toFixed(1)} years may be misaligned with rate outlook.`,
      currentPosition: {
        instrument: 'Portfolio Aggregate',
        currentValue: snapshot.totalPrincipal,
        yield: snapshot.weightedYield,
        spread: snapshot.weightedSpread,
        maturity: `${snapshot.weightedMaturity.toFixed(0)}yr avg`,
      },
      recommendedAction: {
        action: context.yieldCurveSlope < 0 ? 'Shorten duration by 0.5-1.0 years' : 'Consider extending duration for higher carry',
        estimatedSavings: snapshot.totalPrincipal * 0.002,
        riskImpact: 'Moderate — changes portfolio risk profile',
        confidence: 65,
        timeframe: 'Evaluate within 2 weeks',
      },
      triggerReason: `Yield curve slope: ${context.yieldCurveSlope}bps (2Y: ${context.treasury2Y}%, 10Y: ${context.treasury10Y}%)`,
      detectedAt: Date.now(),
      expiresAt: Date.now() + 14 * 24 * 60 * 60 * 1000,
      status: 'new',
    });
  }

  return signals;
}

function generateCreditSignals(snapshot: PortfolioSnapshot, context: MarketContext): OptimizationSignal[] {
  const signals: OptimizationSignal[] = [];

  snapshot.instruments.forEach((inst) => {
    // If credit spreads widened significantly, flag potential credit deterioration
    if (context.changes.igSpread > 15 || context.changes.hySpread > 30) {
      const impactScore = inst.spread > 200 ? context.changes.hySpread : context.changes.igSpread;
      if (impactScore > 15) {
        signals.push({
          id: `sig-cred-${inst.id}-${Date.now()}`,
          portfolioId: snapshot.portfolioId,
          type: 'credit_deterioration',
          severity: inst.spread > 300 ? 'critical' : inst.spread > 150 ? 'high' : 'medium',
          title: `Credit pressure: ${inst.name}`,
          description: `${inst.creditRating}-rated instrument showing spread widening of ${impactScore}bps. Monitor for potential downgrade risk.`,
          currentPosition: {
            instrument: inst.name,
            currentValue: inst.principal,
            yield: inst.yield,
            spread: inst.spread,
            maturity: inst.maturityDate,
          },
          recommendedAction: {
            action: inst.spread > 300 ? 'Consider reducing exposure or hedging' : 'Monitor closely — no immediate action needed',
            estimatedSavings: 0,
            riskImpact: 'High — potential mark-to-market loss',
            confidence: 60,
            timeframe: 'Review within 1 week',
          },
          triggerReason: `IG spreads +${context.changes.igSpread}bps, HY spreads +${context.changes.hySpread}bps`,
          detectedAt: Date.now(),
          expiresAt: Date.now() + 7 * 24 * 60 * 60 * 1000,
          status: 'new',
        });
      }
    }
  });

  return signals;
}

function generateMaturitySignals(snapshot: PortfolioSnapshot): OptimizationSignal[] {
  const signals: OptimizationSignal[] = [];

  snapshot.instruments.forEach((inst) => {
    if (inst.daysToMaturity <= 90 && inst.daysToMaturity > 0) {
      signals.push({
        id: `sig-mat-${inst.id}-${Date.now()}`,
        portfolioId: snapshot.portfolioId,
        type: 'maturity_approaching',
        severity: inst.daysToMaturity <= 30 ? 'critical' : 'high',
        title: `Maturity approaching: ${inst.name}`,
        description: `${inst.name} matures in ${inst.daysToMaturity} days (${inst.maturityDate}). Principal of $${(inst.principal / 1e6).toFixed(1)}M will be returned.`,
        currentPosition: {
          instrument: inst.name,
          currentValue: inst.principal,
          yield: inst.yield,
          spread: inst.spread,
          maturity: inst.maturityDate,
        },
        recommendedAction: {
          action: 'Evaluate reinvestment options or extend maturity',
          estimatedSavings: inst.principal * 0.005,
          riskImpact: 'Low — planned maturity event',
          confidence: 90,
          timeframe: `Execute before ${inst.maturityDate}`,
        },
        triggerReason: `${inst.daysToMaturity} days to maturity`,
        detectedAt: Date.now(),
        expiresAt: Date.now() + inst.daysToMaturity * 24 * 60 * 60 * 1000,
        status: 'new',
      });
    }
  });

  return signals;
}

// ── Main Monitor Class ────────────────────────────────────────────────

export class ContinuousOptimizer {
  private signals: OptimizationSignal[] = [];
  private snapshots: Map<string, PortfolioSnapshot> = new Map();
  private lastMarketContext: MarketContext | null = null;
  private listeners: Set<(signals: OptimizationSignal[]) => void> = new Set();
  private checkInterval: ReturnType<typeof setInterval> | null = null;
  private portfolioUpdateCallbacks: Map<string, () => void> = new Map();

  /**
   * Update the portfolio snapshot for a given portfolio.
   */
  updatePortfolio(snapshot: PortfolioSnapshot): void {
    const previous = this.snapshots.get(snapshot.portfolioId);
    this.snapshots.set(snapshot.portfolioId, snapshot);

    // If we have a market context, re-evaluate immediately
    if (this.lastMarketContext) {
      this.evaluate(snapshot, this.lastMarketContext);
    }

    // If significant change detected, notify
    if (previous) {
      const totalPrincipalChange = Math.abs(snapshot.totalPrincipal - previous.totalPrincipal) / previous.totalPrincipal;
      if (totalPrincipalChange > 0.01) {
        this.notifyListeners();
      }
    }
  }

  /**
   * Update market context and re-evaluate all portfolios.
   */
  updateMarketContext(context: MarketContext): void {
    const previous = this.lastMarketContext;
    this.lastMarketContext = context;

    // Check for significant market moves
    if (previous) {
      const significantMove =
        Math.abs(context.changes.treasury10Y) > 5 ||
        Math.abs(context.changes.igSpread) > 10 ||
        Math.abs(context.changes.hySpread) > 20;

      if (significantMove) {
        // Re-evaluate all portfolios
        this.snapshots.forEach((snapshot) => {
          this.evaluate(snapshot, context);
        });
      }
    }
  }

  /**
   * Evaluate a single portfolio against current market context.
   */
  private evaluate(snapshot: PortfolioSnapshot, context: MarketContext): void {
    const newSignals: OptimizationSignal[] = [
      ...generateRefinanceSignals(snapshot, context),
      ...generateDurationSignals(snapshot, context),
      ...generateCreditSignals(snapshot, context),
      ...generateMaturitySignals(snapshot),
    ];

    // Add new signals (avoid duplicates)
    newSignals.forEach((signal) => {
      const isDuplicate = this.signals.some(
        (existing) =>
          existing.type === signal.type &&
          existing.currentPosition.instrument === signal.currentPosition.instrument &&
          existing.status !== 'expired' &&
          existing.status !== 'dismissed'
      );

      if (!isDuplicate) {
        this.signals.push(signal);
      }
    });

    // Expire old signals
    const now = Date.now();
    this.signals.forEach((signal) => {
      if (signal.expiresAt < now && signal.status === 'new') {
        signal.status = 'expired';
      }
    });

    // Cache signals
    setCache(`optimizer_signals_${snapshot.portfolioId}`, this.getSignalsForPortfolio(snapshot.portfolioId), 60000);

    this.notifyListeners();
  }

  /**
   * Get active signals for a specific portfolio.
   */
  getSignalsForPortfolio(portfolioId: string): OptimizationSignal[] {
    return this.signals.filter(
      (s) => s.portfolioId === portfolioId && s.status !== 'expired' && s.status !== 'dismissed'
    );
  }

  /**
   * Get all active signals across all portfolios.
   */
  getAllActiveSignals(): OptimizationSignal[] {
    return this.signals.filter((s) => s.status !== 'expired' && s.status !== 'dismissed');
  }

  /**
   * Get all signals (used by pipeline runners and demo data).
   */
  getSignals(): OptimizationSignal[] {
    return this.getAllActiveSignals();
  }

  /**
   * Get signal statistics.
   */
  getSignalStats(): {
    total: number;
    critical: number;
    high: number;
    medium: number;
    low: number;
    new: number;
    byType: Record<string, number>;
  } {
    const active = this.getAllActiveSignals();
    return {
      total: active.length,
      critical: active.filter((s) => s.severity === 'critical').length,
      high: active.filter((s) => s.severity === 'high').length,
      medium: active.filter((s) => s.severity === 'medium').length,
      low: active.filter((s) => s.severity === 'low').length,
      new: active.filter((s) => s.status === 'new').length,
      byType: active.reduce((acc, s) => {
        acc[s.type] = (acc[s.type] || 0) + 1;
        return acc;
      }, {} as Record<string, number>),
    };
  }

  /**
   * Acknowledge a signal.
   */
  acknowledgeSignal(signalId: string): void {
    const signal = this.signals.find((s) => s.id === signalId);
    if (signal) {
      signal.status = 'acknowledged';
      this.notifyListeners();
    }
  }

  /**
   * Mark a signal as acted upon.
   */
  actOnSignal(signalId: string): void {
    const signal = this.signals.find((s) => s.id === signalId);
    if (signal) {
      signal.status = 'acted';
      this.notifyListeners();
    }
  }

  /**
   * Dismiss a signal.
   */
  dismissSignal(signalId: string): void {
    const signal = this.signals.find((s) => s.id === signalId);
    if (signal) {
      signal.status = 'dismissed';
      this.notifyListeners();
    }
  }

  /**
   * Subscribe to signal updates.
   */
  onSignalsUpdate(callback: (signals: OptimizationSignal[]) => void): () => void {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }

  /**
   * Start periodic evaluation (every 30 seconds).
   */
  startMonitoring(intervalMs: number = 30000): void {
    if (this.checkInterval) return;
    this.checkInterval = setInterval(() => {
      if (this.lastMarketContext) {
        this.snapshots.forEach((snapshot) => {
          this.evaluate(snapshot, this.lastMarketContext!);
        });
      }
    }, intervalMs);
  }

  /**
   * Stop periodic evaluation.
   */
  stopMonitoring(): void {
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
      this.checkInterval = null;
    }
  }

  private notifyListeners(): void {
    const active = this.getAllActiveSignals();
    this.listeners.forEach((cb) => cb(active));
  }
}

// ── Singleton ─────────────────────────────────────────────────────────

let instance: ContinuousOptimizer | null = null;

export function getContinuousOptimizer(): ContinuousOptimizer {
  if (!instance) {
    instance = new ContinuousOptimizer();
  }
  return instance;
}
