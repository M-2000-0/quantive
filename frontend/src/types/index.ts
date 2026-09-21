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

// ── Intelligence Feed Types ──────────────────────────────────────────

export interface AffectedAsset {
  name: string;
  type: string;
  impact: number;
}

export interface ImpactEvent {
  id: string;
  title: string;
  description: string;
  category: 'economic' | 'political' | 'commercial' | 'geopolitical' | 'regulatory' | 'environmental';
  severity: 'critical' | 'high' | 'medium' | 'low';
  region: string;
  affected_assets: AffectedAsset[];
  created_at: string;
}

export interface EventImpactSummary {
  total_events: number;
  total_positive: number;
  total_negative: number;
  avg_severity: number;
  critical_count: number;
}

export interface ImpactedAsset {
  name: string;
  type: string;
  avg_impact: number;
}

export interface Opportunity {
  id: string;
  name: string;
  ticker: string;
  type: string;
  current_price: number;
  target_price: number;
  upside: number;
  relevance_score: number;
  risk_score: number;
  risk_level: 'Low' | 'Medium' | 'High';
  sector: string;
}

export interface PurchaseRecord {
  id: string;
  instrument_name: string;
  issuer: string;
  principal: number;
  coupon: number;
  purchase_price: number;
  yield_to_maturity: number;
  maturity_date: string;
  days_to_maturity: number;
  unrealized_pnl: number;
  type: string;
  currency: string;
}

// ── News Types ───────────────────────────────────────────────────────

export interface NewsSource {
  id: string;
  name: string;
  source_type: string;
  url: string | null;
  is_active: boolean;
  last_fetched_at: string | null;
  article_count: number;
  config_json: Record<string, unknown> | null;
}

export interface NewsArticle {
  id: string;
  source_id: string;
  title: string;
  summary: string;
  content: string;
  url: string;
  published_at: string;
  category: string;
  tickers: string[];
  sentiment: number;
  is_read: boolean;
  is_starred: boolean;
}

export interface NewsDigest {
  period_hours: number;
  total_articles: number;
  categories: Record<string, number>;
  top_tickers: string[];
  avg_sentiment: number;
  articles: NewsArticle[];
}

export interface NewsStats {
  total_articles: number;
  unread_count: number;
  starred_count: number;
  by_category: Record<string, number>;
  by_source: Record<string, number>;
  avg_sentiment: number;
}

// ── Task Types ───────────────────────────────────────────────────────

export interface Task {
  id: string;
  title: string;
  description: string | null;
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled';
  priority: 'low' | 'medium' | 'high' | 'critical';
  assigned_to: string | null;
  due_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskComment {
  id: string;
  task_id: string;
  content: string;
  created_by: string;
  created_at: string;
}

// ── Management / CRM Types ──────────────────────────────────────────

export interface Deal {
  id: string;
  name: string;
  company: string | null;
  value: number;
  stage: string;
  probability: number;
  expected_close_date: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface PipelineSummary {
  total_deals: number;
  total_value: number;
  by_stage: Record<string, { count: number; value: number }>;
  weighted_value: number;
}

export interface Campaign {
  id: string;
  name: string;
  subject: string;
  body: string;
  status: string;
  sent_count: number;
  open_count: number;
  click_count: number;
  created_at: string;
}

export interface Revenue {
  mrr: number;
  arr: number;
  growth_rate: number;
  by_plan: Record<string, number>;
}

export interface Customer {
  id: string;
  name: string;
  email: string;
  plan: string;
  status: string;
  mrr: number;
  created_at: string;
}

export interface ChurnData {
  rate: number;
  total_customers: number;
  churned_customers: number;
  by_reason: Record<string, number>;
}

// ── Webhook Types ────────────────────────────────────────────────────

export interface Webhook {
  id: string;
  url: string;
  events: string[];
  active: boolean;
}

// ── Backup Types ─────────────────────────────────────────────────────

export interface BackupStatus {
  last_backup: string | null;
  backup_count: number;
  next_scheduled: string | null;
  storage_used_bytes: number;
}

// ── Pricing Types ────────────────────────────────────────────────────

export interface PricingResult {
  base_price: number;
  discount: number;
  final_price: number;
  optimization_type: string;
  debt_outstanding: number;
}

// ── Pilot Program Types ──────────────────────────────────────────────

export interface PilotProgram {
  id: string;
  country_code: string;
  country_name: string;
  government_entity: string;
  entity_type: string;
  contact_name: string;
  contact_email: string;
  total_debt_outstanding: number;
  annual_issuance: number;
  currency: string;
  debt_to_gdp: number;
  portfolio_tier: string;
  status: string;
  start_date: string;
  end_date: string | null;
  financing_cost_reduction_bps: number;
  risk_score_improvement_pct: number;
  user_adoption_rate_pct: number;
  conversion_status: string;
  conversion_value_usd: number;
  case_study_published: boolean;
  created_at: string;
}

// ── Government Relations Types ───────────────────────────────────────

export interface GovernmentOpportunity {
  id: string;
  title: string;
  agency: string;
  value: number;
  status: string;
  deadline: string | null;
  created_at: string;
}

export interface RFP {
  id: string;
  title: string;
  agency: string;
  status: string;
  deadline: string | null;
  created_at: string;
}

export interface GovernmentContact {
  id: string;
  name: string;
  title: string;
  agency: string;
  email: string;
  phone: string | null;
}

// ── Immutable Audit Types ────────────────────────────────────────────

export interface ImmutableAuditEvent {
  id: string;
  event_type: string;
  actor_id: string;
  data: Record<string, unknown>;
  hash: string;
  previous_hash: string | null;
  timestamp: string;
  verified: boolean;
}

// ── Approval Workflow Types ──────────────────────────────────────────

export interface ApprovalRequest {
  id: string;
  type: string;
  status: string;
  requested_by: string;
  data: Record<string, unknown>;
  created_at: string;
  resolved_at: string | null;
}

// ── Model Validation Types ───────────────────────────────────────────

export interface ValidationResult {
  id: string;
  solution_id: string;
  validation_type: string;
  passed: boolean;
  score: number;
  details: Record<string, unknown>;
  created_at: string;
}

// ── SLA Types ────────────────────────────────────────────────────────

export interface SLACompliance {
  overall_compliance: number;
  uptime_pct: number;
  response_time_pct: number;
  breaches: number;
  credits_owed: number;
}

export interface SLABreach {
  id: string;
  type: string;
  severity: string;
  started_at: string;
  resolved_at: string | null;
  duration_minutes: number;
  impact: string;
}

// ── Escrow Types ─────────────────────────────────────────────────────

export interface EscrowAgreement {
  id: string;
  name: string;
  status: string;
  source_code_url: string | null;
  version: string | null;
  created_at: string;
}

// ── Disaster Recovery Types ──────────────────────────────────────────

export interface DRStatus {
  status: string;
  last_backup: string | null;
  last_test: string | null;
  rto_hours: number;
  rpo_hours: number;
  compliance_score: number;
}

export interface DRBackup {
  id: string;
  type: string;
  location: string;
  size_bytes: number;
  created_at: string;
  verified: boolean;
}

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

// Agent runs + projects

export interface AgentStep {
  seq: number;
  tool: string;
  args: Record<string, unknown>;
  status: string;
  output: Record<string, unknown> | null;
  approval_status: string;
  approved_by: string | null;
  approved_at: string | null;
  error: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface AgentRun {
  id: string;
  goal: string;
  status: string;
  current_step: number;
  error: string;
  created_at: string | null;
  completed_at: string | null;
  steps: AgentStep[];
}

export interface AgentTool {
  name: string;
  description: string;
  risk: string;
  min_role: string;
  timeout_seconds: number;
  cost: number;
}

export interface ProjectSummary {
  id: string;
  name: string;
  status: string;
}

