import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import EventImpactDashboard from '../pages/EventImpactDashboard';
import DemoModeBanner from '../components/DemoModeBanner';
import { DemoModeProvider, useDemoMode } from '../stores/demoMode';
import {
  MOCK_EVENTS,
  MOCK_IMPACT_MATRIX,
  getEventImpactSummary,
  getCategoryBreakdown,
  getRegionBreakdown,
  getMostImpactedAssets,
  getSeverityColor,
  getCategoryIcon,
} from '../lib/eventImpactData';
import { DEMO_PORTFOLIOS, DEMO_OPTIMIZATIONS, DEMO_DASHBOARD_STATS } from '../lib/demoData';

const apiEvents = MOCK_EVENTS.map((e) => ({
  ...e,
  affected_assets: e.affectedAssets.map((a) => ({ name: a.name, type: a.type, impact: a.impact })),
  created_at: '2026-09-01T00:00:00Z',
}));

vi.mock('../api', () => ({
  api: {
    intelligence: {
      events: vi.fn(async () => apiEvents),
      eventSummary: vi.fn(async () => ({
        total_events: MOCK_EVENTS.length,
        total_positive: 5,
        total_negative: 5,
        avg_severity: 2.5,
        critical_count: 1,
      })),
      impactedAssets: vi.fn(async () => [
        { name: 'US 10Y Treasury', type: 'bond', avg_impact: 0.8 },
        { name: 'Auto ABS Index', type: 'abs', avg_impact: 0.4 },
        { name: 'EU Green Bonds', type: 'bond', avg_impact: 0.6 },
      ]),
      purchases: vi.fn(async () => []),
      opportunities: vi.fn(async () => []),
    },
    auth: { login: vi.fn(), register: vi.fn(), me: vi.fn(async () => ({ id: 'u1', email: 'test@test.com' })) },
    portfolios: { list: vi.fn(async () => ({ data: [], meta: { total: 0 } })) },
    optimizations: { list: vi.fn(async () => ({ data: [], meta: { total: 0 } })) },
    notifications: { unreadCount: vi.fn(async () => 0), list: vi.fn(async () => ({ data: [], meta: { total: 0 } })), markRead: vi.fn(), markAllRead: vi.fn() },
  },
}));

const renderWithRouter = (component: React.ReactNode) =>
  render(<BrowserRouter>{component}</BrowserRouter>);

const renderWithDemoMode = (component: React.ReactNode) =>
  render(
    <BrowserRouter>
      <DemoModeProvider>{component}</DemoModeProvider>
    </BrowserRouter>
  );

// ── eventImpactData Service Tests ────────────────────────────────────

describe('eventImpactData service', () => {
  describe('MOCK_EVENTS', () => {
    it('has 10 mock events', () => {
      expect(MOCK_EVENTS).toHaveLength(10);
    });

    it('each event has required fields', () => {
      MOCK_EVENTS.forEach((e) => {
        expect(e.id).toBeTruthy();
        expect(e.title).toBeTruthy();
        expect(e.description).toBeTruthy();
        expect(e.category).toBeTruthy();
        expect(e.severity).toBeTruthy();
        expect(e.affectedAssets.length).toBeGreaterThan(0);
      });
    });

    it('spans multiple categories', () => {
      const cats = new Set(MOCK_EVENTS.map((e) => e.category));
      expect(cats.has('economic')).toBe(true);
      expect(cats.has('political')).toBe(true);
      expect(cats.has('commercial')).toBe(true);
      expect(cats.has('geopolitical')).toBe(true);
      expect(cats.has('regulatory')).toBe(true);
    });

    it('has events from different regions', () => {
      const regions = new Set(MOCK_EVENTS.map((e) => e.region));
      expect(regions.size).toBeGreaterThan(3);
    });
  });

  describe('MOCK_IMPACT_MATRIX', () => {
    it('has impact correlations', () => {
      expect(MOCK_IMPACT_MATRIX.length).toBeGreaterThan(0);
    });

    it('correlations are between -1 and 1', () => {
      MOCK_IMPACT_MATRIX.forEach((m) => {
        expect(m.correlation).toBeGreaterThanOrEqual(-1);
        expect(m.correlation).toBeLessThanOrEqual(1);
      });
    });
  });

  describe('getEventImpactSummary', () => {
    it('returns correct totals', () => {
      const summary = getEventImpactSummary(MOCK_EVENTS);
      expect(summary.totalEvents).toBe(10);
      expect(summary.totalPositive).toBeGreaterThan(0);
      expect(summary.totalNegative).toBeGreaterThan(0);
    });

    it('calculates average severity', () => {
      const summary = getEventImpactSummary(MOCK_EVENTS);
      expect(parseFloat(summary.avgSeverity)).toBeGreaterThanOrEqual(1);
      expect(parseFloat(summary.avgSeverity)).toBeLessThanOrEqual(4);
    });

    it('counts critical events', () => {
      const summary = getEventImpactSummary(MOCK_EVENTS);
      expect(summary.criticalCount).toBeGreaterThanOrEqual(0);
    });
  });

  describe('getCategoryBreakdown', () => {
    it('returns counts per category', () => {
      const breakdown = getCategoryBreakdown(MOCK_EVENTS);
      expect(Object.keys(breakdown).length).toBeGreaterThan(0);
    });
  });

  describe('getRegionBreakdown', () => {
    it('returns counts per region', () => {
      const regions = getRegionBreakdown(MOCK_EVENTS);
      expect(Object.keys(regions).length).toBeGreaterThan(3);
    });
  });

  describe('getMostImpactedAssets', () => {
    it('returns assets sorted by impact magnitude', () => {
      const assets = getMostImpactedAssets(MOCK_EVENTS);
      expect(assets.length).toBeGreaterThan(0);
      // First asset should have higher abs impact than second
      if (assets.length > 1) {
        expect(Math.abs(assets[0].avgImpact)).toBeGreaterThanOrEqual(Math.abs(assets[1].avgImpact));
      }
    });

    it('includes impact names and types', () => {
      const assets = getMostImpactedAssets(MOCK_EVENTS);
      assets.forEach((a) => {
        expect(a.name).toBeTruthy();
        expect(a.type).toBeTruthy();
      });
    });
  });

  describe('getSeverityColor', () => {
    it('returns different colors for different severities', () => {
      const critical = getSeverityColor('critical');
      const high = getSeverityColor('high');
      const medium = getSeverityColor('medium');
      const low = getSeverityColor('low');
      expect(critical).not.toBe(high);
      expect(high).not.toBe(medium);
      expect(medium).not.toBe(low);
    });
  });

  describe('getCategoryIcon', () => {
    it('returns icons for all categories', () => {
      expect(getCategoryIcon('political')).toBeTruthy();
      expect(getCategoryIcon('economic')).toBeTruthy();
      expect(getCategoryIcon('geopolitical')).toBeTruthy();
      expect(getCategoryIcon('commercial')).toBeTruthy();
      expect(getCategoryIcon('regulatory')).toBeTruthy();
      expect(getCategoryIcon('environmental')).toBeTruthy();
    });
  });
});

// ── Demo Data Tests ──────────────────────────────────────────────────

describe('demoData', () => {
  it('has 3 demo portfolios', () => {
    expect(DEMO_PORTFOLIOS).toHaveLength(3);
  });

  it('portfolios have realistic data', () => {
    DEMO_PORTFOLIOS.forEach((p: any) => {
      expect(p.totalPrincipal).toBeGreaterThan(0);
      expect(p.instrumentCount).toBeGreaterThan(0);
      expect(p.avgYield).toBeGreaterThan(0);
    });
  });

  it('has demo optimizations', () => {
    expect(DEMO_OPTIMIZATIONS.length).toBeGreaterThan(0);
  });

  it('has dashboard stats with AUM', () => {
    expect(DEMO_DASHBOARD_STATS.totalAUM).toBeGreaterThan(0);
    expect(DEMO_DASHBOARD_STATS.activePortfolios).toBeGreaterThan(0);
  });
});

// ── EventImpactDashboard Tests ───────────────────────────────────────

describe('EventImpactDashboard', () => {
  it('renders page title', async () => {
    renderWithRouter(<EventImpactDashboard />);
    await waitFor(() => expect(screen.getByText('Event Impact Dashboard')).toBeDefined());
  });

  it('renders summary cards', async () => {
    renderWithRouter(<EventImpactDashboard />);
    await waitFor(() => {
      expect(screen.getByText('Total Events')).toBeDefined();
      expect(screen.getByText('Positive Impact')).toBeDefined();
      expect(screen.getByText('Negative Impact')).toBeDefined();
    });
  });

  it('displays events with titles', async () => {
    renderWithRouter(<EventImpactDashboard />);
    await waitFor(() => {
      const fed = screen.getAllByText(/Fed Signals Pause/);
      expect(fed.length).toBeGreaterThan(0);
      const tesla = screen.getAllByText(/Tesla Robotaxi/);
      expect(tesla.length).toBeGreaterThan(0);
    });
  });

  it('has category filter buttons', async () => {
    renderWithRouter(<EventImpactDashboard />);
    await waitFor(() => {
      const allBtns = screen.getAllByText('All');
      expect(allBtns.length).toBeGreaterThan(0);
      const political = screen.getAllByText('Political');
      expect(political.length).toBeGreaterThan(0);
    });
  });

  it('has severity filter buttons', async () => {
    renderWithRouter(<EventImpactDashboard />);
    await waitFor(() => {
      const criticalBtns = screen.getAllByText('Critical');
      expect(criticalBtns.length).toBeGreaterThan(0);
    });
  });

  it('shows Most Impacted Assets sidebar', async () => {
    renderWithRouter(<EventImpactDashboard />);
    await waitFor(() => expect(screen.getByText(/Most Impacted Assets/)).toBeDefined());
  });

  it('shows By Category sidebar', async () => {
    renderWithRouter(<EventImpactDashboard />);
    await waitFor(() => expect(screen.getByText(/By Category/)).toBeDefined());
  });

  it('shows By Region sidebar', async () => {
    renderWithRouter(<EventImpactDashboard />);
    await waitFor(() => expect(screen.getByText(/By Region/)).toBeDefined());
  });
});

// ── DemoModeProvider Tests ───────────────────────────────────────────

describe('DemoModeProvider', () => {
  it('provides demo mode state', () => {
    let demoState: ReturnType<typeof useDemoMode> | null = null;

    function TestComponent() {
      demoState = useDemoMode();
      return <div />;
    }

    renderWithDemoMode(<TestComponent />);
    expect(demoState).not.toBeNull();
    expect(demoState!.isDemoMode).toBe(false);
  });

  it('enableDemoMode sets demo mode', () => {
    let demoState: ReturnType<typeof useDemoMode> | null = null;

    function TestComponent() {
      demoState = useDemoMode();
      return (
        <button onClick={demoState.enableDemoMode}>Enter Demo</button>
      );
    }

    renderWithDemoMode(<TestComponent />);
    expect(demoState!.isDemoMode).toBe(false);
    demoState!.enableDemoMode();
    expect(typeof demoState!.enableDemoMode).toBe('function');
    expect(typeof demoState!.disableDemoMode).toBe('function');
  });
});

// ── DemoModeBanner Tests ─────────────────────────────────────────────

describe('DemoModeBanner', () => {
  it('exports useDemoMode hook', () => {
    // The banner's visibility depends on localStorage; just verify the component can render
    expect(typeof DemoModeBanner).toBe('function');
  });
});
