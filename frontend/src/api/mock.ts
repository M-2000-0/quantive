import type { Portfolio, OptimizationJob, Strategy, BenchmarkResult, AuditEvent, ScenarioResult, StressTestResult } from '../types';

export const MOCK_PORTFOLIOS: Portfolio[] = [
  {
    id: 'port-001',
    name: 'Sovereign Debt Portfolio - FY2026',
    description: 'Primary government debt portfolio including domestic bonds, treasury bills, and external obligations.',
    org_id: 'org-001',
    created_by: 'user-001',
    created_at: '2026-01-15T10:00:00Z',
    updated_at: '2026-08-01T14:30:00Z',
    instruments: [
      { id: 'inst-001', name: 'US Treasury 10Y Bond', instrument_type: 'treasury_bond', currency: 'USD', principal_outstanding: 12500000000, coupon_rate: 0.0425, maturity_date: '2035-06-15', issue_date: '2025-06-15', is_callable: false, call_date: null, call_price: null, spread_bps: 0, created_at: '2026-01-15T10:00:00Z' },
      { id: 'inst-002', name: 'US Treasury 5Y Bond', instrument_type: 'treasury_bond', currency: 'USD', principal_outstanding: 8000000000, coupon_rate: 0.0375, maturity_date: '2031-03-15', issue_date: '2026-03-15', is_callable: false, call_date: null, call_price: null, spread_bps: 0, created_at: '2026-01-15T10:00:00Z' },
      { id: 'inst-003', name: 'Domestic Fixed Rate Bond', instrument_type: 'domestic_bond', currency: 'USD', principal_outstanding: 6000000000, coupon_rate: 0.0510, maturity_date: '2032-09-01', issue_date: '2022-09-01', is_callable: false, call_date: null, call_price: null, spread_bps: 45, created_at: '2026-01-15T10:00:00Z' },
      { id: 'inst-004', name: 'Floating Rate Note', instrument_type: 'floating_rate_note', currency: 'USD', principal_outstanding: 3500000000, coupon_rate: 0.0045, maturity_date: '2028-12-01', issue_date: '2025-12-01', is_callable: false, call_date: null, call_price: null, spread_bps: 15, created_at: '2026-01-15T10:00:00Z' },
      { id: 'inst-005', name: 'EUR Sovereign Bond', instrument_type: 'sovereign_bond', currency: 'EUR', principal_outstanding: 5000000000, coupon_rate: 0.0280, maturity_date: '2033-04-15', issue_date: '2023-04-15', is_callable: false, call_date: null, call_price: null, spread_bps: 12, created_at: '2026-01-15T10:00:00Z' },
      { id: 'inst-006', name: 'JPY Government Bond', instrument_type: 'sovereign_bond', currency: 'JPY', principal_outstanding: 750000000000, coupon_rate: 0.0080, maturity_date: '2036-03-20', issue_date: '2026-03-20', is_callable: false, call_date: null, call_price: null, spread_bps: 5, created_at: '2026-01-15T10:00:00Z' },
      { id: 'inst-007', name: 'Concessional Loan - Multilateral', instrument_type: 'concessional_loan', currency: 'USD', principal_outstanding: 2000000000, coupon_rate: 0.0150, maturity_date: '2040-06-30', issue_date: '2020-06-30', is_callable: false, call_date: null, call_price: null, spread_bps: 0, created_at: '2026-01-15T10:00:00Z' },
      { id: 'inst-008', name: 'T-Bill 3-Month', instrument_type: 't_bill', currency: 'USD', principal_outstanding: 4500000000, coupon_rate: 0.0, maturity_date: '2026-11-15', issue_date: '2026-08-15', is_callable: false, call_date: null, call_price: null, spread_bps: 0, created_at: '2026-01-15T10:00:00Z' },
      { id: 'inst-009', name: 'GBP Gilt 7Y', instrument_type: 'sovereign_bond', currency: 'GBP', principal_outstanding: 3000000000, coupon_rate: 0.0350, maturity_date: '2033-09-22', issue_date: '2026-09-22', is_callable: false, call_date: null, call_price: null, spread_bps: 8, created_at: '2026-01-15T10:00:00Z' },
      { id: 'inst-010', name: 'Inflation-Linked Bond', instrument_type: 'inflation_linked', currency: 'USD', principal_outstanding: 4000000000, coupon_rate: 0.0120, maturity_date: '2035-01-15', issue_date: '2025-01-15', is_callable: false, call_date: null, call_price: null, spread_bps: 22, created_at: '2026-01-15T10:00:00Z' },
    ],
  },
  {
    id: 'port-002',
    name: 'Emergency Liquidity Facility',
    description: 'Short-term instruments maintained for emergency liquidity requirements.',
    org_id: 'org-001',
    created_by: 'user-001',
    created_at: '2026-03-01T09:00:00Z',
    updated_at: '2026-07-20T11:00:00Z',
    instruments: [
      { id: 'inst-011', name: 'Commercial Paper', instrument_type: 'commercial_loan', currency: 'USD', principal_outstanding: 2000000000, coupon_rate: 0.0525, maturity_date: '2027-01-15', issue_date: '2026-07-15', is_callable: true, call_date: '2026-12-15', call_price: 100.5, spread_bps: 85, created_at: '2026-03-01T09:00:00Z' },
      { id: 'inst-012', name: 'Reverse Repo Facility', instrument_type: 't_bill', currency: 'USD', principal_outstanding: 3000000000, coupon_rate: 0.0025, maturity_date: '2026-09-30', issue_date: '2026-08-30', is_callable: false, call_date: null, call_price: null, spread_bps: 0, created_at: '2026-03-01T09:00:00Z' },
    ],
  },
];

export const MOCK_OPTIMIZATION_JOB: OptimizationJob = {
  id: 'opt-001',
  portfolio_id: 'port-001',
  org_id: 'org-001',
  created_by: 'user-001',
  name: 'FY2026 Debt Restructuring Analysis',
  status: 'completed',
  optimization_type: 'multi_objective',
  objectives: {
    financing_cost_weight: 0.35,
    refinancing_risk_weight: 0.25,
    interest_rate_risk_weight: 0.20,
    currency_risk_weight: 0.20,
  },
  constraints: {
    max_refinancing_concentration: 0.30,
    max_floating_rate_exposure: 0.25,
    min_liquidity: 5000000000,
    maturity_concentration_limit: 0.35,
  },
  solver_config: {
    solvers: ['classical', 'heuristic', 'quantum_inspired'],
    time_limit_seconds: 120,
    seed: 42,
  },
  scenario_config: {
    include_named: ['base', 'high_interest', 'low_interest', 'high_inflation', 'fx_shock', 'liquidity_shock'],
    monte_carlo_count: 10000,
    monte_carlo_seed: 42,
    include_base_in_mc: true,
  },
  random_seed: 42,
  model_version: '2.1.0',
  progress: 1.0,
  error_message: null,
  started_at: '2026-08-15T10:00:00Z',
  completed_at: '2026-08-15T10:04:32Z',
  created_at: '2026-08-15T10:00:00Z',
  updated_at: '2026-08-15T10:04:32Z',
};

export const MOCK_STRATEGIES: Strategy[] = [
  {
    id: 'strat-001',
    name: 'Strategy A',
    description: 'Best Overall — Balanced approach optimizing across all objectives simultaneously. Reduces expected financing cost while maintaining all defined refinancing and liquidity constraints.',
    rank: 1,
    created_at: '2026-08-15T10:04:32Z',
    allocations: { 'inst-001': 0.28, 'inst-002': 0.18, 'inst-003': 0.15, 'inst-005': 0.12, 'inst-007': 0.12, 'inst-008': 0.08, 'inst-010': 0.07 },
    metrics: { expected_cost: 6180000000, refinancing_risk: 0.18, interest_rate_risk: 0.22, currency_risk: 0.15, liquidity_coverage: 0.85, stress_resilience: 0.91 },
    stress_test_results: { 'Base': { severity: 'low', cost_impact: 0 }, 'High Interest': { severity: 'medium', cost_impact: 280000000 }, 'FX Shock': { severity: 'medium', cost_impact: 195000000 }, 'Liquidity Shock': { severity: 'low', cost_impact: 85000000 }, 'Inflation': { severity: 'low', cost_impact: 120000000 } },
  },
  {
    id: 'strat-002',
    name: 'Strategy B',
    description: 'Lowest Risk — Conservative allocation prioritizing refinancing safety and interest rate stability over cost minimization.',
    rank: 2,
    created_at: '2026-08-15T10:04:32Z',
    allocations: { 'inst-001': 0.22, 'inst-002': 0.20, 'inst-007': 0.18, 'inst-008': 0.15, 'inst-005': 0.13, 'inst-010': 0.07, 'inst-009': 0.05 },
    metrics: { expected_cost: 6350000000, refinancing_risk: 0.12, interest_rate_risk: 0.15, currency_risk: 0.10, liquidity_coverage: 0.92, stress_resilience: 0.95 },
    stress_test_results: { 'Base': { severity: 'low', cost_impact: 0 }, 'High Interest': { severity: 'low', cost_impact: 145000000 }, 'FX Shock': { severity: 'low', cost_impact: 98000000 }, 'Liquidity Shock': { severity: 'low', cost_impact: 42000000 }, 'Inflation': { severity: 'low', cost_impact: 88000000 } },
  },
  {
    id: 'strat-003',
    name: 'Strategy C',
    description: 'Lowest Cost — Aggressive cost minimization strategy with moderate risk acceptance. Higher refinancing concentration.',
    rank: 3,
    created_at: '2026-08-15T10:04:32Z',
    allocations: { 'inst-001': 0.32, 'inst-002': 0.22, 'inst-003': 0.18, 'inst-005': 0.10, 'inst-008': 0.10, 'inst-010': 0.08 },
    metrics: { expected_cost: 5980000000, refinancing_risk: 0.28, interest_rate_risk: 0.28, currency_risk: 0.12, liquidity_coverage: 0.72, stress_resilience: 0.82 },
    stress_test_results: { 'Base': { severity: 'low', cost_impact: 0 }, 'High Interest': { severity: 'high', cost_impact: 410000000 }, 'FX Shock': { severity: 'medium', cost_impact: 285000000 }, 'Liquidity Shock': { severity: 'high', cost_impact: 190000000 }, 'Inflation': { severity: 'medium', cost_impact: 165000000 } },
  },
  {
    id: 'strat-004',
    name: 'Strategy D',
    description: 'Most Resilient — Minimax approach optimized for worst-case scenario performance. Sacrifices expected cost for tail-risk protection.',
    rank: 4,
    created_at: '2026-08-15T10:04:32Z',
    allocations: { 'inst-001': 0.20, 'inst-002': 0.18, 'inst-007': 0.22, 'inst-008': 0.15, 'inst-005': 0.10, 'inst-010': 0.10, 'inst-009': 0.05 },
    metrics: { expected_cost: 6420000000, refinancing_risk: 0.14, interest_rate_risk: 0.16, currency_risk: 0.11, liquidity_coverage: 0.90, stress_resilience: 0.97 },
    stress_test_results: { 'Base': { severity: 'low', cost_impact: 0 }, 'High Interest': { severity: 'low', cost_impact: 110000000 }, 'FX Shock': { severity: 'low', cost_impact: 78000000 }, 'Liquidity Shock': { severity: 'low', cost_impact: 35000000 }, 'Inflation': { severity: 'low', cost_impact: 72000000 } },
  },
];

export const MOCK_BENCHMARKS: BenchmarkResult[] = [
  { id: 'bench-001', solver_name: 'MILP (CBC)', execution_time_seconds: 12.4, objective_value: 6180000000, feasible: true, iterations: 12847, metrics: { solver_type: 'classical', compute_cost: 0.85, robustness: 0.94 }, created_at: '2026-08-15T10:04:32Z' },
  { id: 'bench-002', solver_name: 'Simulated Annealing', execution_time_seconds: 8.7, objective_value: 6210000000, feasible: true, iterations: 50000, metrics: { solver_type: 'heuristic', compute_cost: 0.62, robustness: 0.89 }, created_at: '2026-08-15T10:04:32Z' },
  { id: 'bench-003', solver_name: 'QUBO Annealing (Simulator)', execution_time_seconds: 18.2, objective_value: 6250000000, feasible: true, iterations: 100000, metrics: { solver_type: 'quantum_inspired', compute_cost: 1.20, robustness: 0.91 }, created_at: '2026-08-15T10:04:32Z' },
];

export const MOCK_SCENARIO_RESULTS: ScenarioResult[] = [
  { scenario_id: 'base', scenario_name: 'Base', probability: 0.30, financing_cost: 6180000000, effective_interest_rate: 0.0412, violations: [] },
  { scenario_id: 'high_interest', scenario_name: 'High Rates', probability: 0.15, financing_cost: 6460000000, effective_interest_rate: 0.0525, violations: [] },
  { scenario_id: 'low_interest', scenario_name: 'Low Rates', probability: 0.15, financing_cost: 5920000000, effective_interest_rate: 0.0318, violations: [] },
  { scenario_id: 'high_inflation', scenario_name: 'High Inflation', probability: 0.10, financing_cost: 6300000000, effective_interest_rate: 0.0485, violations: [] },
  { scenario_id: 'fx_shock', scenario_name: 'FX Shock', probability: 0.10, financing_cost: 6375000000, effective_interest_rate: 0.0455, violations: ['currency_exposure'] },
  { scenario_id: 'liquidity_shock', scenario_name: 'Liquidity Shock', probability: 0.10, financing_cost: 6265000000, effective_interest_rate: 0.0435, violations: [] },
  { scenario_id: 'combined', scenario_name: 'Combined Stress', probability: 0.10, financing_cost: 6850000000, effective_interest_rate: 0.0610, violations: ['refinancing_concentration'] },
];

export const MOCK_STRESS_RESULTS: StressTestResult = {
  strategy_id: 'strat-001',
  scenario_count: 10000,
  avg_financing_cost: 6280000000,
  worst_financing_cost: 7150000000,
  percentile_costs: { p50: 6200000000, p75: 6450000000, p90: 6780000000, p95: 6950000000, p99: 7100000000 },
  breaches: 23,
  constraint_satisfaction_rate: 0.977,
  cost_distribution: { min: 5850000000, max: 7150000000, mean: 6280000000, std: 245000000 },
};

export const MOCK_AUDIT_EVENTS: AuditEvent[] = [
  { id: 'evt-001', actor_id: 'user-001', actor_email: 'admin@treasury.gov', action: 'create', resource_type: 'portfolio', resource_id: 'port-001', org_id: 'org-001', metadata_json: { name: 'Sovereign Debt Portfolio - FY2026' }, ip_address: '10.0.1.52', created_at: '2026-01-15T10:00:00Z' },
  { id: 'evt-002', actor_id: 'user-001', actor_email: 'admin@treasury.gov', action: 'create', resource_type: 'optimization', resource_id: 'opt-001', org_id: 'org-001', metadata_json: { name: 'FY2026 Debt Restructuring Analysis', solver_count: 3, scenario_count: 10000 }, ip_address: '10.0.1.52', created_at: '2026-08-15T10:00:00Z' },
  { id: 'evt-003', actor_id: 'user-001', actor_email: 'admin@treasury.gov', action: 'run', resource_type: 'optimization', resource_id: 'opt-001', org_id: 'org-001', metadata_json: { status: 'completed', duration_seconds: 272 }, ip_address: '10.0.1.52', created_at: '2026-08-15T10:04:32Z' },
  { id: 'evt-004', actor_id: 'user-001', actor_email: 'admin@treasury.gov', action: 'export', resource_type: 'report', resource_id: 'opt-001', org_id: 'org-001', metadata_json: { format: 'json', sections: 10 }, ip_address: '10.0.1.52', created_at: '2026-08-15T10:05:15Z' },
  { id: 'evt-005', actor_id: 'user-002', actor_email: 'analyst@treasury.gov', action: 'view', resource_type: 'optimization', resource_id: 'opt-001', org_id: 'org-001', metadata_json: {}, ip_address: '10.0.1.88', created_at: '2026-08-16T09:30:00Z' },
  { id: 'evt-006', actor_id: 'user-002', actor_email: 'analyst@treasury.gov', action: 'export', resource_type: 'report', resource_id: 'opt-001', org_id: 'org-001', metadata_json: { format: 'pdf' }, ip_address: '10.0.1.88', created_at: '2026-08-16T09:32:00Z' },
];

export const MOCK_RUNNING_JOB: OptimizationJob = {
  ...MOCK_OPTIMIZATION_JOB,
  id: 'opt-002',
  name: 'Stress Test Analysis — Rate Shock',
  status: 'solving',
  progress: 0.55,
  started_at: '2026-08-18T08:00:00Z',
  completed_at: null,
};
