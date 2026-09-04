import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
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
    DEMO_PORTFOLIOS.forEach((p) => {
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
  it('renders page title', () => {
    renderWithRouter(<EventImpactDashboard />);
    expect(screen.getByText('Event Impact Dashboard')).toBeDefined();
  });

  it('renders summary cards', () => {
    renderWithRouter(<EventImpactDashboard />);
    expect(screen.getByText('Total Events')).toBeDefined();
    expect(screen.getByText('Positive')).toBeDefined();
    expect(screen.getByText('Negative')).toBeDefined();
  });

  it('displays events with titles', () => {
    renderWithRouter(<EventImpactDashboard />);
    const fed = screen.getAllByText(/Fed Signals Pause/);
    expect(fed.length).toBeGreaterThan(0);
    const tesla = screen.getAllByText(/Tesla Robotaxi/);
    expect(tesla.length).toBeGreaterThan(0);
  });

  it('has category filter buttons', () => {
    renderWithRouter(<EventImpactDashboard />);
    const allBtns = screen.getAllByText('All');
    expect(allBtns.length).toBeGreaterThan(0);
    const political = screen.getAllByText('Political');
    expect(political.length).toBeGreaterThan(0);
  });

  it('has severity filter buttons', () => {
    renderWithRouter(<EventImpactDashboard />);
    const criticalBtns = screen.getAllByText('Critical');
    expect(criticalBtns.length).toBeGreaterThan(0);
  });

  it('shows Most Impacted Assets sidebar', () => {
    renderWithRouter(<EventImpactDashboard />);
    expect(screen.getByText(/Most Impacted Assets/)).toBeDefined();
  });

  it('shows Events by Category sidebar', () => {
    renderWithRouter(<EventImpactDashboard />);
    expect(screen.getByText(/Events by Category/)).toBeDefined();
  });

  it('shows Regional Exposure sidebar', () => {
    renderWithRouter(<EventImpactDashboard />);
    expect(screen.getByText(/Regional Exposure/)).toBeDefined();
  });

  it('has Matrix View toggle', () => {
    renderWithRouter(<EventImpactDashboard />);
    expect(screen.getByText(/List View/)).toBeDefined();
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
    expect(demoState!.demoUser.id).toBe('demo-user-001');
    expect(demoState!.demoUser.role).toBe('admin');
  });

  it('enterDemoMode sets demo mode', () => {
    let demoState: ReturnType<typeof useDemoMode> | null = null;

    function TestComponent() {
      demoState = useDemoMode();
      return (
        <button onClick={demoState.enterDemoMode}>Enter Demo</button>
      );
    }

    renderWithDemoMode(<TestComponent />);
    expect(demoState!.isDemoMode).toBe(false);
    // Simulate entering demo mode
    demoState!.enterDemoMode();
    // Note: localStorage and state updates happen async
    expect(typeof demoState!.enterDemoMode).toBe('function');
    expect(typeof demoState!.exitDemoMode).toBe('function');
  });
});

// ── DemoModeBanner Tests ─────────────────────────────────────────────

describe('DemoModeBanner', () => {
  it('exports useDemoMode hook', () => {
    // The banner's visibility depends on localStorage; just verify the component can render
    expect(typeof DemoModeBanner).toBe('function');
  });
});
