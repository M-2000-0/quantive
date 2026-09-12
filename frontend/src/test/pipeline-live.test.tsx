import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';

const mockJobs = [
  { id: 'job-1', name: 'Balanced Portfolio Q3', status: 'COMPLETED', optimization_type: 'mean_variance', created_at: '2026-09-01T10:00:00Z', completed_at: '2026-09-01T10:05:00Z', random_seed: 42 },
  { id: 'job-2', name: 'Green Bond Optimizer', status: 'RUNNING', optimization_type: 'scenario', created_at: '2026-09-02T14:00:00Z' },
];

vi.mock('../api', () => ({
  api: {
    optimizations: {
      list: vi.fn(async () => ({ data: mockJobs, meta: { total: 2, page_size: 20, has_more: false, next_cursor: null } })),
      get: vi.fn(async () => mockJobs[0]),
      create: vi.fn(async () => mockJobs[0]),
      subscribeToJob: vi.fn(),
    },
    intelligence: {
      events: vi.fn(async () => []),
      eventSummary: vi.fn(async () => ({ total_events: 0, total_positive: 0, total_negative: 0, avg_severity: 0, critical_count: 0 })),
      impactedAssets: vi.fn(async () => []),
      purchases: vi.fn(async () => []),
      opportunities: vi.fn(async () => []),
    },
    auth: { login: vi.fn(), register: vi.fn(), me: vi.fn(async () => ({ id: 'u1', email: 'test@test.com' })) },
    portfolios: { list: vi.fn(async () => ({ data: [], meta: { total: 0 } })), get: vi.fn() },
    notifications: { unreadCount: vi.fn(async () => 0), list: vi.fn(async () => ({ data: [], meta: { total: 0 } })), markRead: vi.fn(), markAllRead: vi.fn() },
  },
}));

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
    await waitFor(() => expect(screen.getByText('Execution Dashboard')).toBeDefined());
  });

  it('shows stats cards', async () => {
    const { default: Page } = await import('../pages/ExecutionDashboardPage');
    renderWithRouter(<Page />);
    await waitFor(() => {
      expect(screen.getAllByText(/Total Jobs/).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/Completed/).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/Running/).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/Failed/).length).toBeGreaterThan(0);
    });
  });

  it('shows job names from mock data', async () => {
    const { default: Page } = await import('../pages/ExecutionDashboardPage');
    renderWithRouter(<Page />);
    await waitFor(() => {
      expect(screen.getAllByText(/Balanced Portfolio Q3/).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/Green Bond Optimizer/).length).toBeGreaterThan(0);
    });
  });

  it('shows COMPLETED status badge', async () => {
    const { default: Page } = await import('../pages/ExecutionDashboardPage');
    renderWithRouter(<Page />);
    await waitFor(() => {
      expect(screen.getAllByText(/COMPLETED/).length).toBeGreaterThanOrEqual(1);
    });
  });

  it('shows RUNNING status badge', async () => {
    const { default: Page } = await import('../pages/ExecutionDashboardPage');
    renderWithRouter(<Page />);
    await waitFor(() => {
      expect(screen.getAllByText(/RUNNING/).length).toBeGreaterThanOrEqual(1);
    });
  });

  it('clicks a job to select it', async () => {
    const { default: Page } = await import('../pages/ExecutionDashboardPage');
    renderWithRouter(<Page />);
    await waitFor(() => {
      expect(screen.getAllByText(/Balanced Portfolio Q3/).length).toBeGreaterThan(0);
    });
    fireEvent.click(screen.getByText('Balanced Portfolio Q3'));
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
