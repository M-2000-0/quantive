export interface DemoPortfolio {
  id: string;
  name: string;
  totalPrincipal: number;
  instrumentCount: number;
  avgYield: number;
  currency: string;
}

export interface DemoOptimization {
  id: string;
  portfolioId: string;
  name: string;
  status: string;
  savingsPct: number;
}

export const DEMO_PORTFOLIOS: DemoPortfolio[] = [
  { id: 'demo-port-1', name: 'Sovereign Core Portfolio', totalPrincipal: 2_400_000_000, instrumentCount: 12, avgYield: 4.2, currency: 'USD' },
  { id: 'demo-port-2', name: 'Green Transition Fund', totalPrincipal: 850_000_000, instrumentCount: 8, avgYield: 3.6, currency: 'EUR' },
  { id: 'demo-port-3', name: 'Resilience Reserve', totalPrincipal: 410_000_000, instrumentCount: 6, avgYield: 5.1, currency: 'USD' },
];

export const DEMO_OPTIMIZATIONS: DemoOptimization[] = [
  { id: 'demo-opt-1', portfolioId: 'demo-port-1', name: 'Q1 Refinancing Pass', status: 'completed', savingsPct: 8.4 },
  { id: 'demo-opt-2', portfolioId: 'demo-port-2', name: 'Duration Rebalance', status: 'running', savingsPct: 3.1 },
];

export const DEMO_DASHBOARD_STATS = {
  totalAUM: 3_660_000_000,
  activePortfolios: 3,
  totalSavings: 12_400_000,
  riskScore: 42,
};
