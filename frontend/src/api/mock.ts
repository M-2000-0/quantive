export interface MockUser {
  id: string;
  email: string;
  name: string;
  role: string;
  org_id: string;
  is_active: boolean;
  created_at: string;
}

export interface MockPortfolio {
  id: string;
  name: string;
  description: string;
}

export const MOCK_USER: MockUser = {
  id: 'user-001',
  email: 'admin@treasury.gov',
  name: 'Treasury Admin',
  role: 'admin',
  org_id: 'org-1',
  is_active: true,
  created_at: '2026-01-01',
};

export const MOCK_PORTFOLIOS: MockPortfolio[] = [
  { id: 'port-001', name: 'Sovereign Debt Portfolio - FY2026', description: 'Core sovereign holdings' },
  { id: 'port-002', name: 'Green Bond Sleeve', description: 'ESG-labelled issuance' },
];

export const MOCK_STRATEGIES = [
  { id: 'strat-1', name: 'Strategy A', savingsPct: 6.2 },
  { id: 'strat-2', name: 'Strategy B', savingsPct: 3.8 },
];

export const MOCK_BENCHMARKS = [
  { id: 'bench-1', name: 'Peer Median', returnPct: 4.1 },
];

export const MOCK_AUDIT_EVENTS = [
  { id: 'audit-1', action: 'create', actor: 'admin@treasury.gov' },
];
