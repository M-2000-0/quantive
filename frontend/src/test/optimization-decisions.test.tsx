import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import {
  ContinuousOptimizer,
  getContinuousOptimizer,
  type PortfolioSnapshot,
  type MarketContext,
} from '../lib/continuousOptimizer';
import {
  DecisionJournal,
  getDecisionJournal,
  type DecisionEntry,
} from '../lib/decisionJournal';
import SmartReportGenerator from '../components/SmartReportGenerator';
import ApprovalWorkflow from '../components/ApprovalWorkflow';

const renderWithRouter = (component: React.ReactNode) =>
  render(<BrowserRouter>{component}</BrowserRouter>);

// ── ContinuousOptimizer Tests ─────────────────────────────────────────

describe('ContinuousOptimizer', () => {
  let optimizer: ContinuousOptimizer;

  beforeEach(() => {
    optimizer = new ContinuousOptimizer();
  });

  it('creates singleton instance', () => {
    const opt1 = getContinuousOptimizer();
    const opt2 = getContinuousOptimizer();
    expect(opt1).toBe(opt2);
  });

  it('stores portfolio snapshots', () => {
    const snapshot: PortfolioSnapshot = {
      portfolioId: 'pf-001',
      timestamp: Date.now(),
      totalPrincipal: 100_000_000,
      weightedYield: 4.5,
      weightedMaturity: 5.2,
      weightedSpread: 85,
      duration: 4.8,
      instruments: [
        {
          id: 'inst-001',
          name: 'US Treasury 10Y',
          principal: 50_000_000,
          yield: 3.95,
          spread: 0,
          maturityDate: '2035-03-15',
          daysToMaturity: 3083,
          creditRating: 'AAA',
        },
      ],
    };

    optimizer.updatePortfolio(snapshot);
    expect(optimizer.getSignalsForPortfolio('pf-001')).toBeDefined();
  });

  it('generates maturity signals for instruments maturing within 90 days', () => {
    // Set market context first so signals can be generated
    const context: MarketContext = {
      timestamp: Date.now(),
      fedFundsRate: 4.50,
      treasury10Y: 3.68,
      treasury2Y: 3.45,
      yieldCurveSlope: 23,
      igSpread: 82,
      hySpread: 310,
      vix: 18,
      changes: { fedFundsRate: 0, treasury10Y: 0, igSpread: 0, hySpread: 0 },
    };
    optimizer.updateMarketContext(context);

    const snapshot: PortfolioSnapshot = {
      portfolioId: 'pf-002',
      timestamp: Date.now(),
      totalPrincipal: 20_000_000,
      weightedYield: 5.0,
      weightedMaturity: 0.5,
      weightedSpread: 150,
      duration: 0.5,
      instruments: [
        {
          id: 'inst-002',
          name: 'Short-term Note',
          principal: 20_000_000,
          yield: 5.0,
          spread: 150,
          maturityDate: new Date(Date.now() + 20 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          daysToMaturity: 20,
          creditRating: 'A',
        },
      ],
    };

    optimizer.updatePortfolio(snapshot);
    const signals = optimizer.getSignalsForPortfolio('pf-002');
    const maturitySignals = signals.filter((s) => s.type === 'maturity_approaching');
    expect(maturitySignals.length).toBeGreaterThan(0);
  });

  it('generates duration signals when yield curve is inverted', () => {
    const snapshot: PortfolioSnapshot = {
      portfolioId: 'pf-003',
      timestamp: Date.now(),
      totalPrincipal: 100_000_000,
      weightedYield: 4.5,
      weightedMaturity: 7.0,
      weightedSpread: 85,
      duration: 6.5,
      instruments: [],
    };

    // Set context first so the snapshot evaluation triggers
    const context: MarketContext = {
      timestamp: Date.now(),
      fedFundsRate: 4.50,
      treasury10Y: 3.50,
      treasury2Y: 4.20,
      yieldCurveSlope: -70, // inverted
      igSpread: 82,
      hySpread: 310,
      vix: 18,
      changes: { fedFundsRate: 0, treasury10Y: -10, igSpread: 0, hySpread: 0 },
    };

    optimizer.updateMarketContext(context);
    optimizer.updatePortfolio(snapshot);

    const signals = optimizer.getSignalsForPortfolio('pf-003');
    const durationSignals = signals.filter((s) => s.type === 'duration_mismatch');
    expect(durationSignals.length).toBeGreaterThan(0);
  });

  it('tracks signal status changes', () => {
    // Set market context
    const context: MarketContext = {
      timestamp: Date.now(),
      fedFundsRate: 4.50,
      treasury10Y: 3.68,
      treasury2Y: 3.45,
      yieldCurveSlope: 23,
      igSpread: 82,
      hySpread: 310,
      vix: 18,
      changes: { fedFundsRate: 0, treasury10Y: 0, igSpread: 0, hySpread: 0 },
    };
    optimizer.updateMarketContext(context);

    const snapshot: PortfolioSnapshot = {
      portfolioId: 'pf-004',
      timestamp: Date.now(),
      totalPrincipal: 50_000_000,
      weightedYield: 4.0,
      weightedMaturity: 3.0,
      weightedSpread: 60,
      duration: 2.8,
      instruments: [
        {
          id: 'inst-003',
          name: 'Corporate Bond',
          principal: 50_000_000,
          yield: 4.0,
          spread: 60,
          maturityDate: new Date(Date.now() + 15 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          daysToMaturity: 15,
          creditRating: 'BBB+',
        },
      ],
    };

    optimizer.updatePortfolio(snapshot);
    const signals = optimizer.getSignalsForPortfolio('pf-004');
    expect(signals.length).toBeGreaterThan(0);

    const signalId = signals[0].id;
    optimizer.acknowledgeSignal(signalId);
    expect(optimizer.getSignalsForPortfolio('pf-004').find((s) => s.id === signalId)?.status).toBe('acknowledged');

    optimizer.actOnSignal(signalId);
    expect(optimizer.getSignalsForPortfolio('pf-004').find((s) => s.id === signalId)?.status).toBe('acted');
  });

  it('calculates signal statistics', () => {
    // Set market context
    const context: MarketContext = {
      timestamp: Date.now(),
      fedFundsRate: 4.50,
      treasury10Y: 3.68,
      treasury2Y: 3.45,
      yieldCurveSlope: 23,
      igSpread: 82,
      hySpread: 310,
      vix: 18,
      changes: { fedFundsRate: 0, treasury10Y: 0, igSpread: 0, hySpread: 0 },
    };
    optimizer.updateMarketContext(context);

    const snapshot: PortfolioSnapshot = {
      portfolioId: 'pf-005',
      timestamp: Date.now(),
      totalPrincipal: 100_000_000,
      weightedYield: 4.5,
      weightedMaturity: 5.0,
      weightedSpread: 80,
      duration: 4.5,
      instruments: [
        {
          id: 'inst-004',
          name: 'Bond A',
          principal: 50_000_000,
          yield: 4.5,
          spread: 80,
          maturityDate: new Date(Date.now() + 10 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          daysToMaturity: 10,
          creditRating: 'A',
        },
        {
          id: 'inst-005',
          name: 'Bond B',
          principal: 50_000_000,
          yield: 4.5,
          spread: 80,
          maturityDate: new Date(Date.now() + 25 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          daysToMaturity: 25,
          creditRating: 'A',
        },
      ],
    };

    optimizer.updatePortfolio(snapshot);
    const stats = optimizer.getSignalStats();
    expect(stats.total).toBeGreaterThan(0);
    expect(typeof stats.critical).toBe('number');
    expect(typeof stats.high).toBe('number');
    expect(stats.byType).toBeDefined();
  });

  it('subscribes to signal updates', () => {
    // Set market context first
    const context: MarketContext = {
      timestamp: Date.now(),
      fedFundsRate: 4.50,
      treasury10Y: 3.68,
      treasury2Y: 3.45,
      yieldCurveSlope: 23,
      igSpread: 82,
      hySpread: 310,
      vix: 18,
      changes: { fedFundsRate: 0, treasury10Y: 0, igSpread: 0, hySpread: 0 },
    };
    optimizer.updateMarketContext(context);

    let updateCount = 0;
    const unsub = optimizer.onSignalsUpdate(() => {
      updateCount++;
    });

    const snapshot: PortfolioSnapshot = {
      portfolioId: 'pf-006',
      timestamp: Date.now(),
      totalPrincipal: 100_000_000,
      weightedYield: 4.5,
      weightedMaturity: 5.0,
      weightedSpread: 80,
      duration: 4.5,
      instruments: [],
    };

    optimizer.updatePortfolio(snapshot);
    expect(updateCount).toBeGreaterThan(0);
    unsub();
  });

  it('starts and stops monitoring', () => {
    optimizer.startMonitoring(1000);
    optimizer.stopMonitoring();
    // No error thrown
    expect(true).toBe(true);
  });
});

// ── DecisionJournal Tests ─────────────────────────────────────────────

describe('DecisionJournal', () => {
  let journal: DecisionJournal;

  beforeEach(() => {
    journal = new DecisionJournal();
  });

  it('creates singleton instance', () => {
    const j1 = getDecisionJournal();
    expect(j1).toBeDefined();
  });

  it('has mock decisions', () => {
    const entries = journal.getAllEntries();
    expect(entries.length).toBeGreaterThan(0);
  });

  it('records a new decision', () => {
    const entry = journal.recordDecision({
      portfolioId: 'pf-test',
      recommendation: {
        type: 'refinance_opportunity',
        title: 'Test recommendation',
        description: 'Test description',
        instruments: ['Test Bond'],
        estimatedSavings: 50000,
        riskImpact: 'Low',
        confidence: 80,
      },
      marketSnapshot: {
        fedFundsRate: 4.5,
        treasury10Y: 3.7,
        igSpread: 82,
        hySpread: 310,
        yieldCurveSlope: 22,
        vix: 18,
      },
      decision: { status: 'recommended' },
    });

    expect(entry.id).toBeTruthy();
    expect(entry.portfolioId).toBe('pf-test');
    expect(entry.recommendation.title).toBe('Test recommendation');
  });

  it('updates decision status', () => {
    const entry = journal.recordDecision({
      portfolioId: 'pf-test',
      recommendation: {
        type: 'refinance_opportunity',
        title: 'Test',
        description: 'Test',
        instruments: ['Test'],
        estimatedSavings: 50000,
        riskImpact: 'Low',
        confidence: 80,
      },
      marketSnapshot: {
        fedFundsRate: 4.5,
        treasury10Y: 3.7,
        igSpread: 82,
        hySpread: 310,
        yieldCurveSlope: 22,
        vix: 18,
      },
      decision: { status: 'recommended' },
    });

    journal.updateDecisionStatus(entry.id, 'approved', 'Test User', 'Looks good');
    const updated = journal.getAllEntries().find((e) => e.id === entry.id);
    expect(updated?.decision.status).toBe('approved');
    expect(updated?.decision.decidedBy).toBe('Test User');
  });

  it('records outcome', () => {
    const entry = journal.recordDecision({
      portfolioId: 'pf-test',
      recommendation: {
        type: 'refinance_opportunity',
        title: 'Test',
        description: 'Test',
        instruments: ['Test'],
        estimatedSavings: 50000,
        riskImpact: 'Low',
        confidence: 80,
      },
      marketSnapshot: {
        fedFundsRate: 4.5,
        treasury10Y: 3.7,
        igSpread: 82,
        hySpread: 310,
        yieldCurveSlope: 22,
        vix: 18,
      },
      decision: { status: 'completed' },
    });

    journal.recordOutcome(entry.id, {
      actualSavings: 55000,
      actualRiskChange: -1,
      rating: 'good',
      notes: 'Slightly better than expected',
      measuredAt: Date.now(),
    });

    const updated = journal.getAllEntries().find((e) => e.id === entry.id);
    expect(updated?.outcome?.actualSavings).toBe(55000);
    expect(updated?.outcome?.rating).toBe('good');
  });

  it('calculates summary statistics', () => {
    const summary = journal.getSummary();
    expect(summary.totalDecisions).toBeGreaterThan(0);
    expect(typeof summary.approvedRate).toBe('number');
    expect(typeof summary.avgConfidence).toBe('number');
    expect(summary.topDecisionTypes).toBeDefined();
    expect(summary.marketRegimePerformance).toBeDefined();
  });

  it('filters entries by portfolio', () => {
    const entries = journal.getEntriesForPortfolio('demo-pf-001');
    expect(entries.length).toBeGreaterThan(0);
    entries.forEach((e) => expect(e.portfolioId).toBe('demo-pf-001'));
  });

  it('filters entries by status', () => {
    const completed = journal.getEntriesByStatus('completed');
    expect(completed.length).toBeGreaterThan(0);
    completed.forEach((e) => expect(e.decision.status).toBe('completed'));
  });
});

// ── SmartReportGenerator Tests ────────────────────────────────────────

describe('SmartReportGenerator', () => {
  const mockDecision: DecisionEntry = {
    id: 'dec-test',
    portfolioId: 'pf-test',
    timestamp: Date.now(),
    recommendation: {
      type: 'refinance_opportunity',
      title: 'Refinance Test Bond',
      description: 'Treasury yields dropped 25bps',
      instruments: ['Test Bond'],
      estimatedSavings: 125000,
      riskImpact: 'Low',
      confidence: 82,
    },
    marketSnapshot: {
      fedFundsRate: 4.5,
      treasury10Y: 3.85,
      igSpread: 85,
      hySpread: 315,
      yieldCurveSlope: 32,
      vix: 16.5,
    },
    decision: {
      status: 'completed',
      decidedBy: 'Test User',
      decidedAt: Date.now(),
      reason: 'Good opportunity',
    },
    outcome: {
      actualSavings: 142000,
      actualRiskChange: -2,
      rating: 'excellent',
      notes: 'Better than expected',
      measuredAt: Date.now(),
    },
  };

  it('renders generate button', () => {
    renderWithRouter(<SmartReportGenerator decision={mockDecision} />);
    expect(screen.getByText(/Generate Committee Memo/)).toBeDefined();
  });

  it('shows report after generation', async () => {
    renderWithRouter(<SmartReportGenerator decision={mockDecision} />);
    const btn = screen.getByText(/Generate Committee Memo/);
    btn.click();
    // Wait for generation
    await new Promise((r) => setTimeout(r, 1000));
    expect(screen.getByText(/Investment Committee Memo/)).toBeDefined();
    expect(screen.getByText(/Executive Summary/)).toBeDefined();
  });
});

// ── ApprovalWorkflow Tests ────────────────────────────────────────────

describe('ApprovalWorkflow', () => {
  const mockDecision: DecisionEntry = {
    id: 'dec-wf-test',
    portfolioId: 'pf-test',
    timestamp: Date.now(),
    recommendation: {
      type: 'refinance_opportunity',
      title: 'Refinance Test Bond',
      description: 'Test',
      instruments: ['Test Bond'],
      estimatedSavings: 125000,
      riskImpact: 'Low',
      confidence: 82,
    },
    marketSnapshot: {
      fedFundsRate: 4.5,
      treasury10Y: 3.85,
      igSpread: 85,
      hySpread: 315,
      yieldCurveSlope: 32,
      vix: 16.5,
    },
    decision: { status: 'recommended' },
  };

  it('renders workflow steps', () => {
    renderWithRouter(<ApprovalWorkflow decision={mockDecision} />);
    expect(screen.getByText('Approval Workflow')).toBeDefined();
    expect(screen.getByText('Recommendation Generated')).toBeDefined();
    expect(screen.getByText('Submitted for Review')).toBeDefined();
  });

  it('shows approve and reject buttons for recommended status', () => {
    renderWithRouter(<ApprovalWorkflow decision={mockDecision} />);
    expect(screen.getByText(/Approve/)).toBeDefined();
    expect(screen.getByText(/Reject/)).toBeDefined();
  });

  it('shows progress bar', () => {
    renderWithRouter(<ApprovalWorkflow decision={mockDecision} />);
    expect(screen.getByText('Progress')).toBeDefined();
  });

  it('shows current status badge', () => {
    renderWithRouter(<ApprovalWorkflow decision={mockDecision} />);
    expect(screen.getByText('recommended')).toBeDefined();
  });
});
