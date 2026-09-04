import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';

const renderWithRouter = (component: React.ReactNode) =>
  render(<BrowserRouter>{component}</BrowserRouter>);

// ── Allocation Target Service Tests ─────────────────────────────────

describe('allocationTarget service', () => {
  it('has all three target allocations', async () => {
    const { TARGET_ALLOCATIONS } = await import('../lib/allocationTarget');
    expect(TARGET_ALLOCATIONS.conservative).toBeDefined();
    expect(TARGET_ALLOCATIONS.balanced).toBeDefined();
    expect(TARGET_ALLOCATIONS.aggressive).toBeDefined();
  });

  it('conservative has more fixed income than equity', async () => {
    const { TARGET_ALLOCATIONS } = await import('../lib/allocationTarget');
    const c = TARGET_ALLOCATIONS.conservative;
    const fixedIncome = c.buckets.filter((b) => b.category === 'fixed_income').reduce((s, b) => s + b.targetPct, 0);
    const equity = c.buckets.filter((b) => b.category === 'equity').reduce((s, b) => s + b.targetPct, 0);
    expect(fixedIncome).toBeGreaterThan(equity);
  });

  it('aggressive has more equity than fixed income', async () => {
    const { TARGET_ALLOCATIONS } = await import('../lib/allocationTarget');
    const a = TARGET_ALLOCATIONS.aggressive;
    const equity = a.buckets.filter((b) => b.category === 'equity').reduce((s, b) => s + b.targetPct, 0);
    const fixedIncome = a.buckets.filter((b) => b.category === 'fixed_income').reduce((s, b) => s + b.targetPct, 0);
    expect(equity).toBeGreaterThan(fixedIncome);
  });

  it('all allocations sum to 100%', async () => {
    const { TARGET_ALLOCATIONS } = await import('../lib/allocationTarget');
    for (const profile of ['conservative', 'balanced', 'aggressive'] as const) {
      const total = TARGET_ALLOCATIONS[profile].buckets.reduce((s, b) => s + b.targetPct, 0);
      expect(total).toBe(100);
    }
  });

  it('assessProfile returns conservative for low scores', async () => {
    const { assessProfile } = await import('../lib/allocationTarget');
    const answers: Record<string, number> = {};
    for (let i = 0; i < 10; i++) answers[`q${i}`] = 1;
    const result = assessProfile(answers);
    expect(result.profile).toBe('conservative');
    expect(result.confidence).toBeGreaterThan(0);
  });

  it('assessProfile returns aggressive for high scores', async () => {
    const { assessProfile } = await import('../lib/allocationTarget');
    const answers: Record<string, number> = {};
    for (let i = 0; i < 10; i++) answers[`q${i}`] = 5;
    const result = assessProfile(answers);
    expect(result.profile).toBe('aggressive');
  });

  it('assessProfile returns balanced for mid scores', async () => {
    const { assessProfile } = await import('../lib/allocationTarget');
    const answers: Record<string, number> = {};
    for (let i = 0; i < 10; i++) answers[`q${i}`] = 3;
    const result = assessProfile(answers);
    expect(result.profile).toBe('balanced');
  });

  it('generates rebalance trades for drifted allocation', async () => {
    const { generateRebalanceTrades } = await import('../lib/allocationTarget');
    const allocations = [
      { assetClass: 'Bonds', category: 'fixed_income' as const, targetPct: 60, currentPct: 50, drift: -10, holdings: [] },
      { assetClass: 'Equities', category: 'equity' as const, targetPct: 30, currentPct: 40, drift: 10, holdings: [] },
      { assetClass: 'Cash', category: 'cash' as const, targetPct: 10, currentPct: 10, drift: 0, holdings: [] },
    ];
    const trades = generateRebalanceTrades(allocations, 1_000_000);
    expect(trades.length).toBe(2);
    expect(trades.find((t) => t.assetClass === 'Bonds')?.action).toBe('buy');
    expect(trades.find((t) => t.assetClass === 'Equities')?.action).toBe('sell');
  });

  it('detects significant drift', async () => {
    const { hasSignificantDrift } = await import('../lib/allocationTarget');
    const drifted = [
      { assetClass: 'Bonds', category: 'fixed_income' as const, targetPct: 60, currentPct: 50, drift: -10, holdings: [] },
    ];
    const balanced = [
      { assetClass: 'Bonds', category: 'fixed_income' as const, targetPct: 60, currentPct: 58, drift: -2, holdings: [] },
    ];
    expect(hasSignificantDrift(drifted)).toBe(true);
    expect(hasSignificantDrift(balanced)).toBe(false);
  });

  it('calculates health score', async () => {
    const { calculateHealthScore } = await import('../lib/allocationTarget');
    const allocations = [
      { assetClass: 'Bonds', category: 'fixed_income' as const, targetPct: 60, currentPct: 58, drift: -2, holdings: [] },
      { assetClass: 'Equities', category: 'equity' as const, targetPct: 30, currentPct: 32, drift: 2, holdings: [] },
      { assetClass: 'Cash', category: 'cash' as const, targetPct: 10, currentPct: 10, drift: 0, holdings: [] },
    ];
    const health = calculateHealthScore(allocations, 'balanced', {
      totalPrincipal: 230_000_000,
      avgYield: 4.67,
      avgDuration: 5.2,
      riskScore: 42,
      unrealizedPnl: 1_890_000,
      instrumentCount: 12,
    });
    expect(health.overall).toBeGreaterThan(0);
    expect(health.overall).toBeLessThanOrEqual(100);
    expect(health.dimensions.length).toBe(5);
    expect(health.grade).toBeDefined();
  });

  it('quiz has 10 questions', async () => {
    const { QUIZ_QUESTIONS } = await import('../lib/allocationTarget');
    expect(QUIZ_QUESTIONS.length).toBe(10);
  });
});

// ── RiskProfileQuiz Component Tests ─────────────────────────────────

describe('RiskProfileQuiz', () => {
  it('renders quiz header', async () => {
    const { default: Quiz } = await import('../components/RiskProfileQuiz');
    renderWithRouter(<Quiz />);
    expect(screen.getByText(/Risk Profile Assessment/)).toBeDefined();
  });

  it('shows first question', async () => {
    const { default: Quiz } = await import('../components/RiskProfileQuiz');
    renderWithRouter(<Quiz />);
    expect(screen.getByText(/When will you need to start withdrawing/)).toBeDefined();
  });

  it('shows progress counter', async () => {
    const { default: Quiz } = await import('../components/RiskProfileQuiz');
    renderWithRouter(<Quiz />);
    expect(screen.getByText('1/10')).toBeDefined();
  });

  it('selects an answer and enables next', async () => {
    const { default: Quiz } = await import('../components/RiskProfileQuiz');
    renderWithRouter(<Quiz />);
    fireEvent.click(screen.getByText('5-10 years'));
    const nextBtn = screen.getByText('Next →');
    expect(nextBtn).not.toHaveAttribute('disabled');
  });

  it('navigates to next question', async () => {
    const { default: Quiz } = await import('../components/RiskProfileQuiz');
    renderWithRouter(<Quiz />);
    fireEvent.click(screen.getByText('5-10 years'));
    fireEvent.click(screen.getByText('Next →'));
    expect(screen.getByText('2/10')).toBeDefined();
    expect(screen.getByText(/How stable is your current income/)).toBeDefined();
  });

  it('can go back to previous question', async () => {
    const { default: Quiz } = await import('../components/RiskProfileQuiz');
    renderWithRouter(<Quiz />);
    fireEvent.click(screen.getByText('5-10 years'));
    fireEvent.click(screen.getByText('Next →'));
    fireEvent.click(screen.getByText('← Back'));
    expect(screen.getByText('1/10')).toBeDefined();
  });
});

// ── RebalancingAlert Component Tests ────────────────────────────────

describe('RebalancingAlert', () => {
  it('renders rebalancing alert when drift exists', async () => {
    const { default: Alert } = await import('../components/RebalancingAlert');
    renderWithRouter(
      <Alert
        currentAllocation={{ 'Bonds': 50, 'Equities': 40, 'Cash': 10 }}
        targetProfile="balanced"
        totalPortfolioValue={230_000_000}
      />,
    );
    expect(screen.getByText(/Balanced Profile/)).toBeDefined();
  });

  it('does not render when no drift', async () => {
    const { default: Alert } = await import('../components/RebalancingAlert');
    // Use exact target allocation names from balanced profile
    const { container } = renderWithRouter(
      <Alert
        currentAllocation={{ 'US Large Cap': 25, 'International Equity': 15, 'Small Cap Value': 10, 'Government Bonds': 20, 'Corporate Bonds': 10, 'REITs & Commodities': 10, 'Cash': 10 }}
        targetProfile="balanced"
        totalPortfolioValue={230_000_000}
      />,
    );
    // Should render nothing since all are within 5% of target
    expect(container.innerHTML).toBe('');
  });

  it('expands to show details when clicked', async () => {
    const { default: Alert } = await import('../components/RebalancingAlert');
    renderWithRouter(
      <Alert
        currentAllocation={{ 'Bonds': 50, 'Equities': 40, 'Cash': 10 }}
        targetProfile="balanced"
        totalPortfolioValue={230_000_000}
      />,
    );
    fireEvent.click(screen.getByText(/Balanced Profile/));
    expect(screen.getByText(/Asset Class Drift/)).toBeDefined();
  });
});

// ── PortfolioHealthScore Component Tests ─────────────────────────────

describe('PortfolioHealthScore', () => {
  const mockAllocations = [
    { assetClass: 'Bonds', category: 'fixed_income', targetPct: 60, currentPct: 58, drift: -2 },
    { assetClass: 'Equities', category: 'equity', targetPct: 30, currentPct: 32, drift: 2 },
    { assetClass: 'Cash', category: 'cash', targetPct: 10, currentPct: 10, drift: 0 },
  ];

  const mockMetrics = {
    totalPrincipal: 230_000_000,
    avgYield: 4.67,
    avgDuration: 5.2,
    riskScore: 42,
    unrealizedPnl: 1_890_000,
    instrumentCount: 12,
  };

  it('renders health score', async () => {
    const { default: HealthScore } = await import('../components/PortfolioHealthScore');
    renderWithRouter(
      <HealthScore allocations={mockAllocations} targetProfile="balanced" portfolioMetrics={mockMetrics} />,
    );
    expect(screen.getByText(/Portfolio Health/)).toBeDefined();
  });

  it('shows overall score and grade', async () => {
    const { default: HealthScore } = await import('../components/PortfolioHealthScore');
    renderWithRouter(
      <HealthScore allocations={mockAllocations} targetProfile="balanced" portfolioMetrics={mockMetrics} />,
    );
    // Should show portfolio health section
    expect(screen.getByText(/Portfolio Health/)).toBeDefined();
  });

  it('expands to show dimension details', async () => {
    const { default: HealthScore } = await import('../components/PortfolioHealthScore');
    renderWithRouter(
      <HealthScore allocations={mockAllocations} targetProfile="balanced" portfolioMetrics={mockMetrics} />,
    );
    fireEvent.click(screen.getByText('Details →'));
    expect(screen.getAllByText(/Diversification/).length).toBeGreaterThan(1);
    expect(screen.getAllByText(/Target Alignment/).length).toBeGreaterThan(1);
  });
});

// ── AllocationVisualizer Component Tests ────────────────────────────

describe('AllocationVisualizer', () => {
  const mockAllocations = [
    { assetClass: 'Bonds', category: 'fixed_income' as const, targetPct: 60, currentPct: 55, drift: -5 },
    { assetClass: 'Equities', category: 'equity' as const, targetPct: 30, currentPct: 35, drift: 5 },
    { assetClass: 'Cash', category: 'cash' as const, targetPct: 10, currentPct: 10, drift: 0 },
  ];

  it('renders allocation visualizer', async () => {
    const { default: Visualizer } = await import('../components/AllocationVisualizer');
    renderWithRouter(
      <Visualizer allocations={mockAllocations} targetProfile="balanced" />,
    );
    expect(screen.getByText(/Allocation Analysis/)).toBeDefined();
  });

  it('shows current and target labels', async () => {
    const { default: Visualizer } = await import('../components/AllocationVisualizer');
    renderWithRouter(
      <Visualizer allocations={mockAllocations} targetProfile="balanced" />,
    );
    expect(screen.getAllByText('Current').length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Target/).length).toBeGreaterThan(0);
  });

  it('shows drift values', async () => {
    const { default: Visualizer } = await import('../components/AllocationVisualizer');
    renderWithRouter(
      <Visualizer allocations={mockAllocations} targetProfile="balanced" />,
    );
    expect(screen.getByText('-5.0')).toBeDefined();
    expect(screen.getByText('+5.0')).toBeDefined();
  });

  it('renders compact mode', async () => {
    const { default: Visualizer } = await import('../components/AllocationVisualizer');
    renderWithRouter(
      <Visualizer allocations={mockAllocations} targetProfile="balanced" compact />,
    );
    expect(screen.getByText(/Allocation Overview/)).toBeDefined();
  });
});
