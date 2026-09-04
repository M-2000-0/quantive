/**
 * Tests for API and integration layer.
 * Tests frontend hooks and modules, validates integration points.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// ── Mock WebSocket ────────────────────────────────────────────────────

class MockWebSocket {
  static instances: MockWebSocket[] = [];
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  readyState = 1;
  url: string;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
    setTimeout(() => this.onopen?.(), 10);
  }

  send(data: string) { /* noop */ }
  close() { this.readyState = 3; }
}

beforeEach(() => {
  MockWebSocket.instances = [];
  (globalThis as unknown as { WebSocket: typeof MockWebSocket }).WebSocket = MockWebSocket;
});

afterEach(() => {
  MockWebSocket.instances = [];
});

// ── WebSocket Module Tests ────────────────────────────────────────────

describe('WebSocket module', () => {
  it('useWebSocket exports a function', async () => {
    const mod = await import('../hooks/useWebSocket');
    expect(typeof mod.useWebSocket).toBe('function');
  });

  it('useOptimizationProgress exports a function', async () => {
    const mod = await import('../hooks/useOptimizationProgress');
    expect(typeof mod.useOptimizationProgress).toBe('function');
  });
});

// ── API Layer Tests ───────────────────────────────────────────────────

describe('API layer', () => {
  it('mockAdapter exports mockAdapter object', async () => {
    const mod = await import('../api/mockAdapter');
    expect(mod.mockAdapter).toBeDefined();
    expect(typeof mod.setMockEnabled).toBe('function');
  });

  it('mock data is importable', async () => {
    const mod = await import('../api/mock');
    expect(mod).toBeDefined();
    // Check exports exist
    const keys = Object.keys(mod);
    expect(keys.length).toBeGreaterThan(0);
  });
});

// ── Export Utility Tests ──────────────────────────────────────────────

describe('Export utilities', () => {
  it('toCSV generates CSV string', async () => {
    const { toCSV } = await import('../lib/export');
    const csv = toCSV(['name', 'principal'], [['Bond A', 1000000], ['Bond B', 2000000]]);
    expect(csv).toContain('name,principal');
    expect(csv).toContain('Bond A');
    expect(csv).toContain('Bond B');
  });

  it('toCSV handles empty data', async () => {
    const { toCSV } = await import('../lib/export');
    const csv = toCSV(['name'], []);
    expect(csv).toBe('name');
  });

  it('toJSON generates JSON string', async () => {
    const { toJSON } = await import('../lib/export');
    const data = [{ name: 'Bond A', principal: 1000000 }];
    const json = toJSON(data);
    const parsed = JSON.parse(json);
    expect(parsed).toEqual(data);
  });

  it('toJSON compact mode', async () => {
    const { toJSON } = await import('../lib/export');
    const json = toJSON({ a: 1 }, false);
    expect(json).not.toContain('\n');
  });

  it('toXLSX generates Excel XML', async () => {
    const { toXLSX } = await import('../lib/export');
    const xlsx = toXLSX(['Name', 'Principal'], [['Bond A', 1000000]]);
    expect(xlsx).toContain('<?xml');
    expect(xlsx).toContain('Bond A');
  });

  it('exportData is callable', async () => {
    const { exportData } = await import('../lib/export');
    expect(typeof exportData).toBe('function');
  });

  it('exportPortfolio is callable', async () => {
    const { exportPortfolio } = await import('../lib/export');
    expect(typeof exportPortfolio).toBe('function');
  });

  it('exportOptimizationResults is callable', async () => {
    const { exportOptimizationResults } = await import('../lib/export');
    expect(typeof exportOptimizationResults).toBe('function');
  });

  it('exportAuditLog is callable', async () => {
    const { exportAuditLog } = await import('../lib/export');
    expect(typeof exportAuditLog).toBe('function');
  });
});

// ── Analytics Module Tests ────────────────────────────────────────────

describe('Analytics module', () => {
  it('events object has key event helpers', async () => {
    const { events } = await import('../lib/analytics');
    expect(typeof events.login).toBe('function');
    expect(typeof events.portfolioCreated).toBe('function');
    expect(typeof events.optimizationStarted).toBe('function');
    expect(typeof events.onboardingStarted).toBe('function');
    expect(typeof events.themeChanged).toBe('function');
    expect(typeof events.commandPaletteOpened).toBe('function');
  });

  it('track is callable without throwing', async () => {
    const { track } = await import('../lib/analytics');
    expect(() => track('test_event', { key: 'value' })).not.toThrow();
  });

  it('identify is callable', async () => {
    const { identify } = await import('../lib/analytics');
    expect(() => identify('user-123', { role: 'admin' })).not.toThrow();
  });

  it('resetIdentity is callable', async () => {
    const { resetIdentity } = await import('../lib/analytics');
    expect(() => resetIdentity()).not.toThrow();
  });

  it('events fire without errors', async () => {
    const { events } = await import('../lib/analytics');
    expect(() => events.login()).not.toThrow();
    expect(() => events.register()).not.toThrow();
    expect(() => events.logout()).not.toThrow();
    expect(() => events.portfolioCreated('p1')).not.toThrow();
    expect(() => events.optimizationStarted('o1', 'nsga2')).not.toThrow();
    expect(() => events.advisorQuery(50)).not.toThrow();
    expect(() => events.reportExported('csv')).not.toThrow();
  });
});

// ── Sentry Module Tests ───────────────────────────────────────────────

describe('Sentry module', () => {
  it('initSentry is callable without throwing', async () => {
    const { initSentry } = await import('../lib/sentry');
    expect(() => initSentry()).not.toThrow();
  });

  it('captureError is callable', async () => {
    const { captureError } = await import('../lib/sentry');
    expect(() => captureError(new Error('test'))).not.toThrow();
  });

  it('captureMessage is callable', async () => {
    const { captureMessage } = await import('../lib/sentry');
    expect(() => captureMessage('test message')).not.toThrow();
    expect(() => captureMessage('warning', 'warning')).not.toThrow();
    expect(() => captureMessage('error msg', 'error')).not.toThrow();
  });

  it('setUser and clearUser are callable', async () => {
    const { setUser, clearUser } = await import('../lib/sentry');
    expect(() => setUser({ id: 'u1', email: 'test@test.com', role: 'admin' })).not.toThrow();
    expect(() => clearUser()).not.toThrow();
  });
});

// ── Email Template Tests ──────────────────────────────────────────────

describe('Email templates', () => {
  it('welcomeEmail returns template with correct fields', async () => {
    const { welcomeEmail } = await import('../lib/emailTemplates');
    const template = welcomeEmail('John', 'https://quantive.io/login');
    expect(template.subject).toContain('Welcome');
    expect(template.html).toContain('John');
    expect(template.text).toContain('John');
  });

  it('passwordResetEmail returns template with reset URL', async () => {
    const { passwordResetEmail } = await import('../lib/emailTemplates');
    const template = passwordResetEmail('John', 'https://quantive.io/reset?token=abc');
    expect(template.subject).toContain('Reset');
    expect(template.html).toContain('abc');
  });

  it('reportReadyEmail returns template', async () => {
    const { reportReadyEmail } = await import('../lib/emailTemplates');
    const template = reportReadyEmail('John', 'Portfolio Report', 'My Portfolio', 'https://quantive.io/reports/1');
    expect(template.subject).toContain('Report');
    expect(template.html).toContain('John');
    expect(template.html).toContain('Portfolio Report');
  });

  it('optimizationCompleteEmail returns template', async () => {
    const { optimizationCompleteEmail } = await import('../lib/emailTemplates');
    const template = optimizationCompleteEmail('John', 'My Optimization', '12%', 5, 'https://quantive.io/opt/1');
    expect(template.subject).toContain('My Optimization');
    expect(template.html).toContain('My Optimization');
    expect(template.text).toContain('5 strategies');
  });

  it('mfaCodeEmail returns template with code', async () => {
    const { mfaCodeEmail } = await import('../lib/emailTemplates');
    const template = mfaCodeEmail('John', '123456');
    expect(template.html).toContain('123456');
    expect(template.text).toContain('123456');
  });
});

// ── Onboarding Tour Tests ────────────────────────────────────────────

describe('useOnboardingTour', () => {
  it('exports correct function', async () => {
    const mod = await import('../hooks/useOnboardingTour');
    expect(typeof mod.useOnboardingTour).toBe('function');
  });
});

// ── Version History Tests ─────────────────────────────────────────────

describe('useVersionHistory', () => {
  it('exports correct functions', async () => {
    const mod = await import('../hooks/useVersionHistory');
    expect(typeof mod.useVersionHistory).toBe('function');
    expect(typeof mod.computeDiff).toBe('function');
    expect(typeof mod.formatDiffValue).toBe('function');
  });

  it('formatDiffValue handles numbers', async () => {
    const { formatDiffValue } = await import('../hooks/useVersionHistory');
    const result1 = formatDiffValue(1000000);
    expect(typeof result1).toBe('string');
    expect(result1.length).toBeGreaterThan(0);
  });

  it('formatDiffValue handles strings', async () => {
    const { formatDiffValue } = await import('../hooks/useVersionHistory');
    expect(formatDiffValue('hello')).toBe('hello');
  });

  it('formatDiffValue handles booleans', async () => {
    const { formatDiffValue } = await import('../hooks/useVersionHistory');
    expect(formatDiffValue(true)).toBe('Yes');
    expect(formatDiffValue(false)).toBe('No');
  });
});

// ── Undo/Redo Tests ──────────────────────────────────────────────────

describe('useUndoRedo', () => {
  it('exports correct function', async () => {
    const mod = await import('../hooks/useUndoRedo');
    expect(typeof mod.useUndoRedo).toBe('function');
  });
});

// ── Version History Panel ─────────────────────────────────────────────

describe('VersionHistoryPanel', () => {
  it('exports component', async () => {
    const mod = await import('../components/VersionHistoryPanel');
    expect(typeof mod.default).toBe('function');
  });
});

// ── Onboarding Tour Component ─────────────────────────────────────────

describe('OnboardingTour', () => {
  it('exports component', async () => {
    const mod = await import('../components/OnboardingTour');
    expect(typeof mod.default).toBe('function');
  });
});
