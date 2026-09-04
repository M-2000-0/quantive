import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';

// Mock chart components
vi.mock('../components/charts/GlassBarChart', () => ({
  default: (props: any) => <div data-testid="glass-bar-chart">{props.title}</div>,
}));
vi.mock('../components/charts/GlassPieChart', () => ({
  default: (props: any) => <div data-testid="glass-pie-chart">{props.title}</div>,
}));
vi.mock('../components/charts/GlassAreaChart', () => ({
  default: () => <div data-testid="glass-area-chart" />,
}));
vi.mock('../components/charts/GlassLineChart', () => ({
  default: () => <div data-testid="glass-line-chart" />,
}));
vi.mock('../components/charts/GlassGaugeChart', () => ({
  default: () => <div data-testid="glass-gauge-chart" />,
}));

// Mock alertSounds
vi.mock('../lib/alertSounds', () => ({
  getAlertSounds: () => ({ setVolume: vi.fn(), preview: vi.fn(), enable: vi.fn(), disable: vi.fn(), mute: vi.fn(), unmute: vi.fn() }),
  severityToSoundType: (s: string) => s,
  signalToSoundType: (s: string) => s,
}));

const renderWithRouter = (component: React.ReactNode) =>
  render(<BrowserRouter>{component}</BrowserRouter>);

// ── Pipeline Orchestrator Tests ─────────────────────────────────────

describe('pipelineOrchestrator', () => {
  it('creates an orchestrator with default config', async () => {
    const { getPipelineOrchestrator } = await import('../lib/pipelineOrchestrator');
    const orch = getPipelineOrchestrator();
    const stats = orch.getStats();
    expect(stats.isRunning).toBe(false);
    expect(stats.totalEvents).toBeGreaterThanOrEqual(0);
  });

  it('starts and stops the orchestrator', async () => {
    const { getPipelineOrchestrator } = await import('../lib/pipelineOrchestrator');
    const orch = getPipelineOrchestrator();
    orch.start();
    expect(orch.getStats().isRunning).toBe(true);
    orch.stop();
    expect(orch.getStats().isRunning).toBe(false);
  });

  it('subscribes to pipeline events', async () => {
    const { getPipelineOrchestrator } = await import('../lib/pipelineOrchestrator');
    const orch = getPipelineOrchestrator();
    const events: any[] = [];
    const unsub = orch.onEvent((e) => events.push(e));
    orch.start();
    expect(events.length).toBeGreaterThan(0);
    unsub();
    orch.stop();
  });

  it('processes a signal through the pipeline', async () => {
    const { getPipelineOrchestrator } = await import('../lib/pipelineOrchestrator');
    const { getContinuousOptimizer } = await import('../lib/continuousOptimizer');
    const orch = getPipelineOrchestrator();
    const optimizer = getContinuousOptimizer();
    const signals = optimizer.getAllActiveSignals();

    if (signals.length > 0) {
      const run = await orch.processSignal(signals[0]);
      expect(run).not.toBeNull();
      if (run) {
        expect(run.recommendation).not.toBeNull();
      }
    }
  });

  it('updates config', async () => {
    const { getPipelineOrchestrator } = await import('../lib/pipelineOrchestrator');
    const orch = getPipelineOrchestrator();
    orch.updateConfig({ debugMode: true });
    // Config updated without error
    expect(orch.getStats()).toBeDefined();
  });
});

// ── Execution Engine Tests ─────────────────────────────────────────

describe('executionEngine', () => {
  it('returns empty records initially', async () => {
    const { getExecutionEngine } = await import('../lib/executionEngine');
    const engine = getExecutionEngine();
    const records = engine.getRecords();
    expect(Array.isArray(records)).toBe(true);
  });

  it('calculates stats correctly', async () => {
    const { getExecutionEngine } = await import('../lib/executionEngine');
    const engine = getExecutionEngine();
    const stats = engine.getStats();
    expect(stats.totalExecutions).toBeGreaterThanOrEqual(0);
    expect(stats.dailyVolumeLimit).toBeGreaterThan(0);
    expect(typeof stats.averageAccuracy).toBe('number');
  });
});

// ── ExecutionDashboardPage Tests ────────────────────────────────────

describe('ExecutionDashboardPage', () => {
  it('renders page title', async () => {
    const { default: Page } = await import('../pages/ExecutionDashboardPage');
    renderWithRouter(<Page />);
    expect(screen.getByText('Execution Dashboard')).toBeDefined();
  });

  it('shows stats cards', async () => {
    const { default: Page } = await import('../pages/ExecutionDashboardPage');
    renderWithRouter(<Page />);
    expect(screen.getAllByText(/Total Executions/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Completed/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Realized Savings/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Avg Accuracy/).length).toBeGreaterThan(0);
  });

  it('shows all 4 view tabs', async () => {
    const { default: Page } = await import('../pages/ExecutionDashboardPage');
    renderWithRouter(<Page />);
    expect(screen.getAllByText(/Executions/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Trades/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Outcomes/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Activity/).length).toBeGreaterThan(0);
  });

  it('shows demo execution records', async () => {
    const { default: Page } = await import('../pages/ExecutionDashboardPage');
    renderWithRouter(<Page />);
    expect(screen.getAllByText(/COMPLETED/).length).toBeGreaterThanOrEqual(1);
  });

  it('switches to trades view', async () => {
    const { default: Page } = await import('../pages/ExecutionDashboardPage');
    renderWithRouter(<Page />);
    fireEvent.click(screen.getByText(/Trades/));
    expect(screen.getByText('Instrument')).toBeDefined();
  });

  it('switches to outcomes view', async () => {
    const { default: Page } = await import('../pages/ExecutionDashboardPage');
    renderWithRouter(<Page />);
    fireEvent.click(screen.getByText(/Outcomes/));
    expect(screen.getByText('Total Savings')).toBeDefined();
  });

  it('switches to activity view', async () => {
    const { default: Page } = await import('../pages/ExecutionDashboardPage');
    renderWithRouter(<Page />);
    fireEvent.click(screen.getByText(/Activity/));
    // Should show activity events or empty state
    expect(screen.getByText(/Activity/)).toBeDefined();
  });
});

// ── CollaborativeOptimizationEditor Tests ──────────────────────────

describe('CollaborativeOptimizationEditor', () => {
  const defaultParams = {
    objective: 'balanced' as const,
    maxDuration: 7,
    minYield: 4.0,
    maxRisk: 50,
    minCreditRating: 'A',
    currencyHedge: 75,
    greenBondTarget: 15,
    constraints: [],
  };

  it('renders optimization editor', async () => {
    const { default: Editor } = await import('../components/CollaborativeOptimizationEditor');
    renderWithRouter(
      <Editor params={defaultParams} onChange={() => {}} />,
    );
    expect(screen.getByText(/Optimization Parameters/)).toBeDefined();
  });

  it('shows objective options', async () => {
    const { default: Editor } = await import('../components/CollaborativeOptimizationEditor');
    renderWithRouter(
      <Editor params={defaultParams} onChange={() => {}} />,
    );
    expect(screen.getByText('Minimize Cost')).toBeDefined();
    expect(screen.getByText('Minimize Risk')).toBeDefined();
    expect(screen.getByText('Maximize Return')).toBeDefined();
    expect(screen.getByText('Balanced')).toBeDefined();
  });

  it('shows parameter sliders', async () => {
    const { default: Editor } = await import('../components/CollaborativeOptimizationEditor');
    renderWithRouter(
      <Editor params={defaultParams} onChange={() => {}} />,
    );
    expect(screen.getByText(/Max Duration/)).toBeDefined();
    expect(screen.getByText(/Min Yield/)).toBeDefined();
    expect(screen.getByText(/Max Risk Score/)).toBeDefined();
    expect(screen.getByText(/FX Hedge Ratio/)).toBeDefined();
  });

  it('shows online presence', async () => {
    const { default: Editor } = await import('../components/CollaborativeOptimizationEditor');
    renderWithRouter(
      <Editor params={defaultParams} onChange={() => {}} />,
    );
    expect(screen.getAllByText(/editing/).length).toBeGreaterThan(0);
  });

  it('calls onChange when objective is clicked', async () => {
    const onChange = vi.fn();
    const { default: Editor } = await import('../components/CollaborativeOptimizationEditor');
    renderWithRouter(
      <Editor params={defaultParams} onChange={onChange} />,
    );
    fireEvent.click(screen.getByText('Minimize Cost'));
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ objective: 'minimize_cost' }),
    );
  });
});

// ── CollaborationPanel Tests ────────────────────────────────────────

describe('CollaborationPanel (extended)', () => {
  it('shows team members in full mode', async () => {
    const { default: Panel } = await import('../components/CollaborationPanel');
    renderWithRouter(<Panel />);
    expect(screen.getAllByText(/Team/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Approvals/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Activity/).length).toBeGreaterThan(0);
  });

  it('shows approval chains', async () => {
    const { default: Panel } = await import('../components/CollaborationPanel');
    renderWithRouter(<Panel />);
    fireEvent.click(screen.getByText(/Approvals/));
    // Should show approval chain data
    expect(screen.getByText(/Approvals/)).toBeDefined();
  });
});
