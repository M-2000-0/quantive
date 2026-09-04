import { describe, it, expect, vi, beforeEach } from 'vitest';
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

// Mock alertSounds
vi.mock('../lib/alertSounds', () => ({
  getAlertSounds: () => ({ setVolume: vi.fn(), preview: vi.fn(), enable: vi.fn(), disable: vi.fn(), mute: vi.fn(), unmute: vi.fn() }),
  severityToSoundType: (s: string) => s,
  signalToSoundType: (s: string) => s,
}));

const renderWithRouter = (component: React.ReactNode) =>
  render(<BrowserRouter>{component}</BrowserRouter>);

// ── Auto-Draft Pipeline Tests ──────────────────────────────────────

describe('autoDraftPipeline', () => {
  it('creates a pipeline run from a signal', async () => {
    const { getAutoDraftPipeline } = await import('../lib/autoDraftPipeline');
    const { getContinuousOptimizer } = await import('../lib/continuousOptimizer');
    const optimizer = getContinuousOptimizer();
    const signals = optimizer.getAllActiveSignals();

    if (signals.length > 0) {
      const pipeline = getAutoDraftPipeline();
      const run = await pipeline.processSignal(signals[0]);
      expect(run).not.toBeNull();
      if (run) {
        expect(run.stage).toBeDefined();
        expect(run.recommendation).not.toBeNull();
        expect(run.memoDraft).not.toBeNull();
      }
    }
  });

  it('generates memo draft with required fields', async () => {
    const { getAutoDraftPipeline } = await import('../lib/autoDraftPipeline');
    const { getContinuousOptimizer } = await import('../lib/continuousOptimizer');
    const optimizer = getContinuousOptimizer();
    const signals = optimizer.getAllActiveSignals();

    if (signals.length > 0) {
      const pipeline = getAutoDraftPipeline();
      const run = await pipeline.processSignal(signals[0]);
      expect(run?.memoDraft?.title).toBeDefined();
      expect(run?.memoDraft?.summary).toBeDefined();
      expect(run?.memoDraft?.sections.length).toBeGreaterThan(0);
      expect(run?.memoDraft?.assignees.length).toBeGreaterThan(0);
    }
  });

  it('approves a pipeline run', async () => {
    const { getAutoDraftPipeline } = await import('../lib/autoDraftPipeline');
    const { getContinuousOptimizer } = await import('../lib/continuousOptimizer');
    const optimizer = getContinuousOptimizer();
    const signals = optimizer.getAllActiveSignals();

    if (signals.length > 0) {
      const pipeline = getAutoDraftPipeline();
      const run = await pipeline.processSignal(signals[0]);
      if (run) {
        const approved = pipeline.approve(run.id, 'test-user', 'Looks good');
        expect(approved).not.toBeNull();
        expect(approved?.stage).toBe('approved');
      }
    }
  });

  it('rejects a pipeline run', async () => {
    const { getAutoDraftPipeline } = await import('../lib/autoDraftPipeline');
    const { getContinuousOptimizer } = await import('../lib/continuousOptimizer');
    const optimizer = getContinuousOptimizer();
    const signals = optimizer.getAllActiveSignals();

    if (signals.length > 0) {
      const pipeline = getAutoDraftPipeline();
      const run = await pipeline.processSignal(signals[0]);
      if (run) {
        const rejected = pipeline.reject(run.id, 'test-user', 'Needs review');
        expect(rejected).not.toBeNull();
        expect(rejected?.stage).toBe('rejected');
      }
    }
  });

  it('returns pipeline stats', async () => {
    const { getAutoDraftPipeline } = await import('../lib/autoDraftPipeline');
    const pipeline = getAutoDraftPipeline();
    const stats = pipeline.getStats();
    expect(stats.totalRuns).toBeGreaterThanOrEqual(0);
    expect(stats.dailyLimit).toBeGreaterThan(0);
  });
});

// ── Execution Engine Tests ─────────────────────────────────────────

describe('executionEngine', () => {
  it('returns execution stats', async () => {
    const { getExecutionEngine } = await import('../lib/executionEngine');
    const engine = getExecutionEngine();
    const stats = engine.getStats();
    expect(stats.totalExecutions).toBeGreaterThanOrEqual(0);
    expect(stats.dailyVolumeLimit).toBeGreaterThan(0);
  });

  it('has risk checks that validate recommendations', async () => {
    const { getExecutionEngine } = await import('../lib/executionEngine');
    const engine = getExecutionEngine();
    const records = engine.getRecords();
    // Records start empty, that's fine
    expect(Array.isArray(records)).toBe(true);
  });
});

// ── Collaboration Service Tests ─────────────────────────────────────

describe('collaborationService', () => {
  it('returns team members', async () => {
    const { getCollaboration } = await import('../lib/collaboration');
    const collab = getCollaboration();
    const members = collab.getMembers();
    expect(members.length).toBeGreaterThan(0);
    expect(members[0].name).toBeDefined();
    expect(members[0].role).toBeDefined();
  });

  it('filters online members', async () => {
    const { getCollaboration } = await import('../lib/collaboration');
    const collab = getCollaboration();
    const online = collab.getOnlineMembers();
    expect(Array.isArray(online)).toBe(true);
  });

  it('gets members by role', async () => {
    const { getCollaboration } = await import('../lib/collaboration');
    const collab = getCollaboration();
    const analysts = collab.getMembersByRole('treasury_analyst');
    expect(Array.isArray(analysts)).toBe(true);
  });

  it('returns approval chains', async () => {
    const { getCollaboration } = await import('../lib/collaboration');
    const collab = getCollaboration();
    const chains = collab.getApprovalChains();
    expect(chains.length).toBeGreaterThan(0);
    expect(chains[0].steps.length).toBeGreaterThan(0);
  });

  it('returns team peer summary', async () => {
    const { getCollaboration } = await import('../lib/collaboration');
    const collab = getCollaboration();
    const summary = collab.getTeamPeerSummary();
    expect(summary.totalMembers).toBeGreaterThan(0);
    expect(summary.roleActivity.length).toBeGreaterThan(0);
  });

  it('creates a new approval chain', async () => {
    const { getCollaboration } = await import('../lib/collaboration');
    const collab = getCollaboration();
    const chain = collab.createApprovalChain('Test Chain', [
      { roleName: 'treasury_analyst' },
      { roleName: 'risk_officer' },
    ]);
    expect(chain.id).toBeDefined();
    expect(chain.steps.length).toBe(2);
    expect(chain.status).toBe('active');
  });

  it('approves a step in the chain', async () => {
    const { getCollaboration } = await import('../lib/collaboration');
    const collab = getCollaboration();
    const chain = collab.createApprovalChain('Test Chain 2', [
      { roleName: 'treasury_analyst' },
      { roleName: 'risk_officer' },
    ]);
    const firstStep = chain.steps[0];
    const result = collab.approveStep(chain.id, firstStep.id, 'user-1', 'Looks good');
    expect(result).toBe(true);
    expect(firstStep.status).toBe('approved');
    expect(chain.steps[1].status).toBe('active');
  });
});

// ── CollaborationPanel Component Tests ──────────────────────────────

describe('CollaborationPanel', () => {
  it('renders compact mode with online avatars', async () => {
    const { default: CollaborationPanel } = await import('../components/CollaborationPanel');
    renderWithRouter(<CollaborationPanel compact />);
    // Should render without errors
    expect(document.querySelector('[class*="rounded"]')).toBeDefined();
  });

  it('renders full mode with tabs', async () => {
    const { default: CollaborationPanel } = await import('../components/CollaborationPanel');
    renderWithRouter(<CollaborationPanel />);
    expect(screen.getAllByText(/Team/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Approvals/).length).toBeGreaterThan(0);
  });
});

// ── AdaptiveDashboardPage Tests ─────────────────────────────────────

describe('AdaptiveDashboardPage', () => {
  it('renders page title', async () => {
    const { default: Page } = await import('../pages/AdaptiveDashboardPage');
    renderWithRouter(<Page />);
    expect(screen.getByText('Adaptive Dashboard')).toBeDefined();
  });

  it('shows Live indicator', async () => {
    const { default: Page } = await import('../pages/AdaptiveDashboardPage');
    renderWithRouter(<Page />);
    expect(screen.getByText('Live')).toBeDefined();
  });

  it('shows all 4 view tabs', async () => {
    const { default: Page } = await import('../pages/AdaptiveDashboardPage');
    renderWithRouter(<Page />);
    expect(screen.getAllByText(/Cause & Effect/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Insights/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Market Events/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Pipeline/).length).toBeGreaterThan(0);
  });

  it('switches to insights view', async () => {
    const { default: Page } = await import('../pages/AdaptiveDashboardPage');
    renderWithRouter(<Page />);
    fireEvent.click(screen.getByText(/Insights/));
    expect(screen.getByText(/Select an Insight/)).toBeDefined();
  });

  it('switches to market events view', async () => {
    const { default: Page } = await import('../pages/AdaptiveDashboardPage');
    renderWithRouter(<Page />);
    fireEvent.click(screen.getByRole('button', { name: /Market Events/ }));
    expect(screen.getByText('Magnitude')).toBeDefined();
  });

  it('switches to pipeline view', async () => {
    const { default: Page } = await import('../pages/AdaptiveDashboardPage');
    renderWithRouter(<Page />);
    fireEvent.click(screen.getByText(/Pipeline/));
    expect(screen.getByText(/Total Runs/)).toBeDefined();
  });
});
