export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'analyst' | 'viewer';
  org_id: string;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface DebtInstrument {
  id: string;
  name: string;
  instrument_type: string;
  currency: string;
  principal_outstanding: number;
  coupon_rate: number;
  maturity_date: string;
  issue_date: string;
  is_callable: boolean;
  call_date: string | null;
  call_price: number | null;
  spread_bps: number;
  created_at: string;
}

export interface Portfolio {
  id: string;
  name: string;
  description: string;
  org_id: string;
  created_by: string;
  created_at: string;
  updated_at: string;
  instruments: DebtInstrument[];
}

export interface OptimizationObjectives {
  financing_cost_weight: number;
  refinancing_risk_weight: number;
  interest_rate_risk_weight: number;
  currency_risk_weight: number;
}

export interface OptimizationConstraints {
  max_financing_cost?: number;
  max_refinancing_concentration?: number;
  max_currency_exposure?: number;
  max_floating_rate_exposure?: number;
  min_liquidity?: number;
  maturity_concentration_limit?: number;
  max_single_instrument_pct?: number;
}

export interface ScenarioConfig {
  include_named: string[];
  monte_carlo_count: number;
  monte_carlo_seed: number;
  include_base_in_mc: boolean;
}

export interface SolverConfig {
  solvers: string[];
  time_limit_seconds: number;
  seed: number;
}

export interface OptimizationJob {
  id: string;
  portfolio_id: string;
  org_id: string;
  created_by: string;
  name: string;
  status: string;
  optimization_type: string;
  objectives: Record<string, unknown>;
  constraints: Record<string, unknown>;
  solver_config: Record<string, unknown>;
  scenario_config: Record<string, unknown>;
  random_seed: number;
  model_version: string;
  progress: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Strategy {
  id: string;
  name: string;
  description: string;
  allocations: Record<string, number>;
  metrics: Record<string, unknown>;
  stress_test_results: Record<string, unknown> | null;
  rank: number;
  created_at: string;
}

export interface BenchmarkResult {
  id: string;
  solver_name: string;
  execution_time_seconds: number;
  objective_value: number;
  feasible: boolean;
  iterations: number;
  metrics: Record<string, unknown>;
  created_at: string;
}

export interface AuditEvent {
  id: string;
  actor_id: string | null;
  actor_email: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  org_id: string | null;
  metadata_json: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: string;
}

export interface Report {
  job_id: string;
  job_name: string;
  status: string;
  optimization_type: string;
  created_at: string;
  completed_at: string | null;
  random_seed: number;
  model_version: string;
  portfolio: { name: string; num_instruments: number };
  strategies: Array<{
    name: string;
    description: string;
    rank: number;
    metrics: Record<string, unknown>;
    stress_test_results: Record<string, unknown> | null;
  }>;
  benchmarks: Array<{
    solver_name: string;
    execution_time_seconds: number;
    objective_value: number;
    feasible: boolean;
    iterations: number;
    metrics: Record<string, unknown>;
  }>;
  summary: Record<string, unknown>;
}

export interface ScenarioResult {
  scenario_id: string;
  scenario_name: string;
  probability: number;
  financing_cost: number;
  effective_interest_rate: number;
  violations: string[];
}

export interface StressTestResult {
  strategy_id: string;
  scenario_count: number;
  avg_financing_cost: number;
  worst_financing_cost: number;
  percentile_costs: Record<string, number>;
  breaches: number;
  constraint_satisfaction_rate: number;
  cost_distribution: { min: number; max: number; mean: number; std: number };
}

export interface BenchmarkRow {
  solver: string;
  solver_type: string;
  execution_backend: string;
  feasible: boolean;
  objective_value: number;
  financing_cost: number;
  risk_total: number;
  runtime: number;
  constraint_violations: number;
  robustness: number;
  compute_cost: number;
  optimality_note: string;
  rank: number;
}

export interface NavItem {
  label: string;
  path: string;
  icon: string;
}

export interface PortfolioSummary {
  total_debt: number;
  instrument_count: number;
  currencies: string[];
  avg_maturity_years: number;
  weighted_coupon: number;
}

export interface OptimizationStep {
  id: string;
  label: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
}

// ── Market Data Types ──────────────────────────────────────────────

export interface YieldCurvePoint {
  label: string;
  rate_pct: number;
  months: number;
}

export interface YieldCurve {
  date: string;
  source: string;
  maturities: YieldCurvePoint[];
  twoTenSpreadBps: number | null;
}

export interface FxRate {
  currency: string;
  rate: number;
  name: string;
  source: string;
  date: string;
}

export interface InterestRate {
  name: string;
  value: number;
  unit: string;
  source: string;
  date: string;
  description: string;
}

export interface EconomicIndicator {
  name: string;
  value: number;
  unit: string;
  date: string;
  country: string;
  description: string;
}

export interface MarketSnapshot {
  yield_curve: {
    date: string;
    source: string;
    maturities: YieldCurvePoint[];
    twoTenSpreadBps: number | null;
  } | null;
  interest_rates: {
    rates: InterestRate[];
    summary: Record<string, number>;
  } | null;
  fx_rates: Record<string, number> | null;
  snapshot_time: string;
}

// ── Risk Types ─────────────────────────────────────────────────────

export interface InvestmentScenario {
  scenario_name: string;
  investment: number;
  return_amount: number;
  return_pct: number;
  probability: number;
  description: string;
}

export interface RiskScore {
  score: number;
  label: string;
  color: string;
  components: Record<string, { score: number; weight: number; description: string }>;
  recommendations: string[];
}

export interface VaRResult {
  confidence: number;
  horizon_days: number;
  var_amount: number;
  var_pct: number;
  cvar_amount: number;
  cvar_pct: number;
}

export interface RiskSummary {
  portfolio_id: string;
  portfolio_name: string;
  investment_scenarios: InvestmentScenario[];
  risk_score: RiskScore;
  var_analysis: VaRResult[];
  generated_at: string;
}

// ── National Risk Operating System (Layer 6) Types ───────────────────

export interface RiskCategoryPanel {
  id: RiskCategory;
  title: string;
  icon: string;
  color: string;
}

export interface RiskSummaryData {
  overall: number;
  by_category: Record<RiskCategory, number>;
  category_counts: Record<RiskCategory, number>;
  entity_id: string;
  entity_type: string;
  trending?: string;
}

export interface EarlyWarningSignal {
  id: string;
  name: string;
  category: string;
  indicator: string;
  currentValue: number;
  threshold: number;
  unit: string;
  direction: 'above_danger' | 'below_danger';
  status: 'normal' | 'watch' | 'warning' | 'critical';
  trend: 'improving' | 'stable' | 'deteriorating';
  description: string;
  lastUpdated: string;
}

export enum RiskCategory {
  CYBER = 'cyber',
  FISCAL = 'fiscal',
  CLIMATE = 'climate',
  INFRASTRUCTURE = 'infrastructure',
  GEOPOLITICAL = 'geopolitical',
  SUPPLY_CHAIN = 'supply_chain',
}

export enum RiskSeverity {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical',
}

export enum TrendDirection {
  IMPROVING = 'improving',
  STABLE = 'stable',
  DETERIORATING = 'deteriorating',
}

// ── Notification Types ─────────────────────────────────────────────

export interface Notification {
  id: string;
  user_id: string;
  type: string;
  title: string;
  message: string;
  is_read: boolean;
  resource_type: string | null;
  resource_id: string | null;
  created_at: string;
}

// ── Watchlist Types ────────────────────────────────────────────────

export interface Watchlist {
  id: string;
  name: string;
  description: string;
  org_id: string;
  created_by: string;
  created_at: string;
  items: WatchlistItem[];
}

export interface WatchlistItem {
  id: string;
  watchlist_id: string;
  instrument_id: string;
  instrument_name: string;
  alert_above_pct: number | null;
  alert_below_pct: number | null;
  created_at: string;
}

// ── Tag Types ──────────────────────────────────────────────────────

export interface Tag {
  id: string;
  name: string;
  color: string;
  org_id: string;
  created_at: string;
}

// ── Activity Types ─────────────────────────────────────────────────

export interface ActivityEvent {
  id: string;
  user_id: string;
  user_email: string;
  action: string;
  resource_type: string;
  resource_id: string;
  details: Record<string, unknown>;
  ip_address: string;
  created_at: string;
}

// ── Comment Types ──────────────────────────────────────────────────

export interface Comment {
  id: string;
  user_id: string;
  user_email: string;
  content: string;
  resource_type: string;
  resource_id: string;
  parent_id: string | null;
  created_at: string;
  updated_at: string;
}

// ── Dashboard Types ────────────────────────────────────────────────

export interface MaturityBucket {
  year: number;
  count: number;
  total_principal: number;
}

export interface DashboardSummary {
  total_debt: number;
  instrument_count: number;
  currency_count: number;
  portfolio_count: number;
  avg_maturity_years: number;
  weighted_coupon_pct: number;
  active_optimizations: number;
  completed_optimizations: number;
  risk_scores: {
    refinancing_risk: number;
    currency_risk: number;
    interest_rate_risk: number;
    overall: number;
  };
  maturity_distribution: MaturityBucket[];
  top_currencies: Array<{ currency: string; total_principal: number; percentage: number }>;
}

export interface DashboardTask {
  id: string;
  type: string;
  title: string;
  meta: string;
  status: string;
  priority: string;
  link?: string;
}

// ── Portfolio Detail Types ─────────────────────────────────────────

export interface PortfolioInstrument {
  id: string;
  name: string;
  instrument_type: string;
  currency: string;
  principal_outstanding: number;
  coupon_rate: number;
  maturity_date: string;
  issue_date: string;
  spread_bps: number;
  years_to_maturity: number;
  is_callable: boolean;
}

export interface PortfolioDetailSummary {
  total_principal: number;
  instrument_count: number;
  currency_count: number;
  avg_maturity_years: number;
  weighted_coupon_pct: number;
  weighted_spread_bps: number;
  callable_count: number;
}

export interface CurrencyBreakdown {
  currency: string;
  total_principal: number;
  percentage: number;
  instrument_count: number;
}

export interface PortfolioDetail {
  id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
  summary: PortfolioDetailSummary;
  instruments: PortfolioInstrument[];
  maturity_distribution: MaturityBucket[];
  currency_breakdown: CurrencyBreakdown[];
}

export type WasteType = 'overpayment' | 'duplicate' | 'uncompetitive' | 'scope_creep' | 'other';

export type BottleneckType = 'approval' | 'vendor' | 'budget' | 'compliance' | 'other';

// ── Export Types ───────────────────────────────────────────────────

export interface ExportJob {
  id: string;
  org_id: string;
  user_id: string;
  format: string;
  status: string;
  progress: number;
  file_path: string | null;
  error: string | null;
  created_at: string;
  completed_at: string | null;
}
