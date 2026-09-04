import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

// Mock recharts
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div data-testid="responsive-container">{children}</div>,
  AreaChart: ({ children }: { children: React.ReactNode }) => <div data-testid="area-chart">{children}</div>,
  Area: () => null,
  BarChart: ({ children }: { children: React.ReactNode }) => <div data-testid="bar-chart">{children}</div>,
  Bar: () => null,
  Cell: () => null,
  PieChart: ({ children }: { children: React.ReactNode }) => <div data-testid="pie-chart">{children}</div>,
  Pie: () => null,
  LineChart: ({ children }: { children: React.ReactNode }) => <div data-testid="line-chart">{children}</div>,
  Line: () => null,
  RadarChart: ({ children }: { children: React.ReactNode }) => <div data-testid="radar-chart">{children}</div>,
  Radar: () => null,
  ScatterChart: ({ children }: { children: React.ReactNode }) => <div data-testid="scatter-chart">{children}</div>,
  Scatter: () => null,
  Treemap: () => null,
  Tooltip: () => null,
  Legend: () => null,
  XAxis: () => null,
  YAxis: () => null,
  ZAxis: () => null,
  CartesianGrid: () => null,
  PolarGrid: () => null,
  PolarAngleAxis: () => null,
  PolarRadiusAxis: () => null,
}));

import MarketIntelligenceReport from '../components/MarketIntelligenceReport';
import {
  POLICY_RATES,
  YIELD_CURVE,
  CREDIT_SPREADS,
  GREEN_BOND_ISSUANCE,
  EM_LOCAL_YIELDS,
  MARKET_OVERVIEW,
  REFINANCING_WALL,
  RISK_MATRIX,
  ALLOCATION_TARGETS,
  EXECUTIVE_SUMMARY,
  KEY_RECOMMENDATIONS,
} from '../lib/marketReportData';

// ─── Data Service Tests ──────────────────────────────────────────────────────

describe('Market Report Data', () => {
  it('has policy rates for 4 central banks', () => {
    expect(POLICY_RATES).toHaveLength(4);
    expect(POLICY_RATES.map(r => r.bank)).toContain('US Federal Reserve');
    expect(POLICY_RATES.map(r => r.bank)).toContain('European Central Bank');
  });

  it('yield curve has 10 maturity points', () => {
    expect(YIELD_CURVE).toHaveLength(10);
    expect(YIELD_CURVE[0].maturity).toBe('3M');
    expect(YIELD_CURVE[9].maturity).toBe('30Y');
  });

  it('yield curve 2026 > 2025 at long end (bear steepening)', () => {
    const y10 = YIELD_CURVE.find(y => y.maturity === '10Y')!;
    expect(y10.yieldAug2026).toBeGreaterThan(y10.yieldJan2025);
  });

  it('credit spreads are tightening (current < historical)', () => {
    const latest = CREDIT_SPREADS[CREDIT_SPREADS.length - 1];
    const earliest = CREDIT_SPREADS[0];
    expect(latest.igSpread).toBeLessThan(earliest.igSpread);
    expect(latest.hySpread).toBeLessThan(earliest.hySpread);
  });

  it('green bond issuance is growing long-term', () => {
    // 2026 projected > 2019 baseline (long-term growth trend)
    const first = GREEN_BOND_ISSUANCE[0];
    const last = GREEN_BOND_ISSUANCE[GREEN_BOND_ISSUANCE.length - 1];
    expect(last.issuance).toBeGreaterThan(first.issuance);
    // Cumulative is monotonically increasing
    for (let i = 1; i < GREEN_BOND_ISSUANCE.length; i++) {
      expect(GREEN_BOND_ISSUANCE[i].cumulative).toBeGreaterThan(GREEN_BOND_ISSUANCE[i - 1].cumulative);
    }
  });

  it('EM yields all have positive real yields', () => {
    EM_LOCAL_YIELDS.forEach(em => {
      expect(em.realYield).toBeGreaterThan(0);
    });
  });

  it('market overview has key metrics', () => {
    expect(MARKET_OVERVIEW.totalGlobalDebt).toBeGreaterThan(100);
    expect(MARKET_OVERVIEW.igDefaultRate).toBeLessThan(1);
    expect(MARKET_OVERVIEW.corePCE).toBeGreaterThan(0);
  });

  it('refinancing wall has 3 years', () => {
    expect(REFINANCING_WALL).toHaveLength(3);
    expect(REFINANCING_WALL[0].year).toBe(2025);
  });

  it('risk matrix has 5 factors', () => {
    expect(RISK_MATRIX).toHaveLength(5);
    RISK_MATRIX.forEach(r => {
      expect(['Low', 'Low-Medium', 'Medium', 'High']).toContain(r.probability);
      expect(r.mitigation.length).toBeGreaterThan(0);
    });
  });

  it('allocation targets has 8 metrics', () => {
    expect(ALLOCATION_TARGETS).toHaveLength(8);
    ALLOCATION_TARGETS.forEach(a => {
      expect(a.metric.length).toBeGreaterThan(0);
      expect(a.current.length).toBeGreaterThan(0);
      expect(a.recommended.length).toBeGreaterThan(0);
    });
  });

  it('executive summary has 4 findings', () => {
    expect(EXECUTIVE_SUMMARY).toHaveLength(4);
    EXECUTIVE_SUMMARY.forEach(f => expect(f.length).toBeGreaterThan(20));
  });

  it('key recommendations has 5 items', () => {
    expect(KEY_RECOMMENDATIONS).toHaveLength(5);
    KEY_RECOMMENDATIONS.forEach(r => expect(r.length).toBeGreaterThan(20));
  });
});

// ─── Component Tests ─────────────────────────────────────────────────────────

describe('MarketIntelligenceReport', () => {
  it('renders title and subtitle', () => {
    render(<MarketIntelligenceReport />);
    const titles = screen.getAllByText(/Global Fixed Income/);
    expect(titles.length).toBeGreaterThanOrEqual(1);
    const dates = screen.getAllByText(/August 2026/);
    expect(dates.length).toBeGreaterThanOrEqual(1);
  });

  it('renders section navigation', () => {
    render(<MarketIntelligenceReport />);
    expect(screen.getByText(/Executive Summary/)).toBeTruthy();
    expect(screen.getByText(/Interest Rates/)).toBeTruthy();
    expect(screen.getByText(/Credit Spreads/)).toBeTruthy();
    expect(screen.getByText(/Green Bonds/)).toBeTruthy();
    expect(screen.getByText(/EM Debt/)).toBeTruthy();
    expect(screen.getByText(/Risk Assessment/)).toBeTruthy();
    expect(screen.getByText(/Recommendations/)).toBeTruthy();
  });

  it('shows executive summary by default', () => {
    render(<MarketIntelligenceReport />);
    expect(screen.getByText(/Key Findings/)).toBeTruthy();
    expect(screen.getByText(/\$133.7T/)).toBeTruthy(); // Total global debt
  });

  it('switches to rates section', () => {
    render(<MarketIntelligenceReport />);
    fireEvent.click(screen.getByText(/Interest Rates/));
    expect(screen.getByText(/US Treasury Yield Curve/)).toBeTruthy();
    const fedRefs = screen.getAllByText(/Federal Reserve/);
    expect(fedRefs.length).toBeGreaterThanOrEqual(1);
  });

  it('switches to credit section', () => {
    render(<MarketIntelligenceReport />);
    fireEvent.click(screen.getByText(/Credit Spreads/));
    expect(screen.getByText(/IG Credit Spreads/)).toBeTruthy();
    expect(screen.getByText(/82 bps/)).toBeTruthy();
  });

  it('switches to green bonds section', () => {
    render(<MarketIntelligenceReport />);
    fireEvent.click(screen.getByText(/Green Bonds/));
    expect(screen.getByText(/Green Bond Annual Issuance/)).toBeTruthy();
    expect(screen.getByText(/\$1.2T/)).toBeTruthy();
  });

  it('switches to EM debt section', () => {
    render(<MarketIntelligenceReport />);
    fireEvent.click(screen.getByText(/EM Debt/));
    expect(screen.getByText(/EM Local Currency Bond Yields/)).toBeTruthy();
    expect(screen.getByText('Brazil')).toBeTruthy();
    expect(screen.getByText('Mexico')).toBeTruthy();
  });

  it('switches to risk section', () => {
    render(<MarketIntelligenceReport />);
    fireEvent.click(screen.getByText(/Risk Assessment/));
    expect(screen.getByText(/Risk Assessment Matrix/)).toBeTruthy();
    expect(screen.getByText(/inflation re-acceleration/)).toBeTruthy();
  });

  it('switches to allocation section', () => {
    render(<MarketIntelligenceReport />);
    fireEvent.click(screen.getByText(/Recommendations/));
    expect(screen.getByText(/Recommended Portfolio Allocation/)).toBeTruthy();
    expect(screen.getByText(/Key Recommendations/)).toBeTruthy();
    expect(screen.getByText(/Coupon Optimization/)).toBeTruthy();
  });

  it('renders disclaimer', () => {
    render(<MarketIntelligenceReport />);
    expect(screen.getByText(/Disclaimer/)).toBeTruthy();
    expect(screen.getByText(/Sources/)).toBeTruthy();
  });

  it('has print button', () => {
    render(<MarketIntelligenceReport />);
    expect(screen.getByText(/Print/)).toBeTruthy();
  });
});
