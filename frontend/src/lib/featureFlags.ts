// ── Feature Flags & Plan Gating System ────────────────────────────────
// Controls which features are available at each plan tier.
// Gates features on both frontend (UI rendering) and backend (API routes).

export type PlanTier = 'starter' | 'professional' | 'enterprise' | 'demo';

export interface PlanDefinition {
  id: PlanTier;
  name: string;
  description: string;
  price: number; // monthly USD
  priceAnnual: number; // monthly price when billed annually
  maxPortfolios: number;
  maxInstruments: number;
  maxUsers: number;
  maxApiProviders: number;
  maxAlerts: number;
  supportLevel: 'email' | 'priority' | 'dedicated';
  supportSlaHours: number;
  customSla: boolean;
  billingCycle: string;
}

export interface FeatureDefinition {
  id: string;
  name: string;
  description: string;
  minPlan: PlanTier;
  category: string;
  isBeta?: boolean;
}

// ── Plan Definitions ─────────────────────────────────────────────────

export const PLANS: Record<PlanTier, PlanDefinition> = {
  demo: {
    id: 'demo',
    name: 'Demo',
    description: 'Full access with synthetic data — no signup needed',
    price: 0,
    priceAnnual: 0,
    maxPortfolios: 999,
    maxInstruments: 9999,
    maxUsers: 999,
    maxApiProviders: 999,
    maxAlerts: 999,
    supportLevel: 'email',
    supportSlaHours: 168,
    customSla: false,
    billingCycle: 'N/A',
  },
  starter: {
    id: 'starter',
    name: 'Starter',
    description: 'Essential portfolio tracking for small treasury teams',
    price: 299,
    priceAnnual: 249,
    maxPortfolios: 3,
    maxInstruments: 50,
    maxUsers: 2,
    maxApiProviders: 0,
    maxAlerts: 3,
    supportLevel: 'email',
    supportSlaHours: 48,
    customSla: false,
    billingCycle: 'Monthly / Annual',
  },
  professional: {
    id: 'professional',
    name: 'Professional',
    description: 'Full optimization engine with real-time data for growing teams',
    price: 899,
    priceAnnual: 749,
    maxPortfolios: 999,
    maxInstruments: 500,
    maxUsers: 10,
    maxApiProviders: 2,
    maxAlerts: 999,
    supportLevel: 'priority',
    supportSlaHours: 4,
    customSla: false,
    billingCycle: 'Monthly / Annual',
  },
  enterprise: {
    id: 'enterprise',
    name: 'Enterprise',
    description: 'Full platform with compliance, advanced analytics, and white-glove support',
    price: 2499,
    priceAnnual: 2099,
    maxPortfolios: 9999,
    maxInstruments: 99999,
    maxUsers: 999,
    maxApiProviders: 999,
    maxAlerts: 999,
    supportLevel: 'dedicated',
    supportSlaHours: 1,
    customSla: true,
    billingCycle: 'Monthly / Annual / Custom',
  },
};

// ── Plan Tier Order (for comparison) ──────────────────────────────────

const PLAN_ORDER: PlanTier[] = ['demo', 'starter', 'professional', 'enterprise'];

// ── Feature Definitions ──────────────────────────────────────────────

export const FEATURES: FeatureDefinition[] = [
  // ── Portfolio & Data ──────────────────────────────────────────────
  { id: 'portfolio.create', name: 'Create Portfolios', description: 'Import or create debt portfolios', minPlan: 'professional', category: 'Portfolio' },
  { id: 'portfolio.edit', name: 'Edit Portfolios', description: 'Modify instruments and metadata', minPlan: 'professional', category: 'Portfolio' },
  { id: 'portfolio.unlimited', name: 'Unlimited Portfolios', description: 'No limit on portfolio count', minPlan: 'professional', category: 'Portfolio' },
  { id: 'portfolio.instruments.large', name: '500+ Instruments', description: 'Support up to 500 instruments per portfolio', minPlan: 'professional', category: 'Portfolio' },
  { id: 'portfolio.instruments.unlimited', name: 'Unlimited Instruments', description: 'No limit on instruments per portfolio', minPlan: 'enterprise', category: 'Portfolio' },
  { id: 'portfolio.csv_import', name: 'CSV Import Wizard', description: 'Bulk import instruments from CSV files', minPlan: 'professional', category: 'Portfolio' },

  // ── Optimization ──────────────────────────────────────────────────
  { id: 'optimization.run', name: 'Run Optimization', description: 'Multi-objective debt portfolio optimization', minPlan: 'professional', category: 'Optimization' },
  { id: 'optimization.unlimited', name: 'Unlimited Optimizations', description: 'No limit on optimization runs', minPlan: 'professional', category: 'Optimization' },
  { id: 'optimization.advanced', name: 'Advanced Solver', description: 'Custom constraints and multi-stage optimization', minPlan: 'enterprise', category: 'Optimization' },

  // ── Charts & Visualization ────────────────────────────────────────
  { id: 'charts.basic', name: 'Basic Charts (4)', description: 'Area, Bar, Pie, Line charts', minPlan: 'starter', category: 'Charts' },
  { id: 'charts.advanced', name: 'Advanced Charts (11)', description: 'Radar, Scatter, Treemap, Heatmap, Gauge, Waterfall, Bubble, Candlestick, Sankey, BoxPlot, Composed', minPlan: 'professional', category: 'Charts' },

  // ── Market Data ───────────────────────────────────────────────────
  { id: 'market.daily', name: 'Daily Market Data', description: 'End-of-day yield curves and FX rates', minPlan: 'starter', category: 'Market Data' },
  { id: 'market.realtime', name: 'Real-Time Data (3s)', description: 'Live polling with 3-second refresh', minPlan: 'professional', category: 'Market Data' },
  { id: 'market.websocket', name: 'WebSocket Streaming', description: 'Real-time stock price streaming with flash animations', minPlan: 'professional', category: 'Market Data' },
  { id: 'market.api_connections', name: 'API Connections', description: 'Connect Bloomberg, Reuters, FRED, etc.', minPlan: 'professional', category: 'Market Data' },
  { id: 'market.api_unlimited', name: 'Unlimited API Providers', description: 'Connect all available data providers', minPlan: 'enterprise', category: 'Market Data' },

  // ── Analytics ─────────────────────────────────────────────────────
  { id: 'analytics.monte_carlo', name: 'Monte Carlo Simulation', description: 'Probabilistic portfolio outcome modeling', minPlan: 'enterprise', category: 'Analytics' },
  { id: 'analytics.correlation', name: 'Correlation Matrix', description: 'Asset correlation heatmap analysis', minPlan: 'enterprise', category: 'Analytics' },
  { id: 'analytics.stress_test', name: 'Stress Testing', description: 'Scenario-based portfolio stress analysis', minPlan: 'enterprise', category: 'Analytics' },
  { id: 'analytics.what_if', name: 'What-If Scenarios', description: 'Simulate rate shocks and market moves', minPlan: 'professional', category: 'Analytics' },
  { id: 'analytics.rating_sim', name: 'Rating Simulator', description: 'Credit rating change impact analysis', minPlan: 'enterprise', category: 'Analytics' },

  // ── Risk ──────────────────────────────────────────────────────────
  { id: 'risk.basic', name: 'Basic Risk Dashboard', description: 'Risk scores and key metrics', minPlan: 'starter', category: 'Risk' },
  { id: 'risk.advanced', name: 'Advanced Risk Dashboard', description: 'Full risk analytics with scenario charts', minPlan: 'professional', category: 'Risk' },
  { id: 'risk.intelligence', name: 'Risk Intelligence', description: 'AI-powered risk event detection and recommendations', minPlan: 'enterprise', category: 'Risk' },

  // ── Events ────────────────────────────────────────────────────────
  { id: 'events.impact', name: 'Event Impact Dashboard', description: 'Real-time event-to-asset correlation analysis', minPlan: 'enterprise', category: 'Events' },

  // ── Collaboration ─────────────────────────────────────────────────
  { id: 'collab.comments', name: 'Comment Threads', description: 'Team discussion on portfolios', minPlan: 'professional', category: 'Collaboration' },
  { id: 'collab.annotations', name: 'Annotations', description: 'Pin notes to risk areas and charts', minPlan: 'professional', category: 'Collaboration' },
  { id: 'collab.users.large', name: '10+ Team Members', description: 'Support larger teams', minPlan: 'enterprise', category: 'Collaboration' },
  { id: 'collab.sso', name: 'SSO / SAML', description: 'Single sign-on with enterprise identity providers', minPlan: 'enterprise', category: 'Collaboration' },

  // ── Compliance & ESG ─────────────────────────────────────────────
  { id: 'compliance.imf', name: 'IMF Compliance Tracking', description: 'Monitor IMF compliance requirements', minPlan: 'enterprise', category: 'Compliance' },
  { id: 'compliance.audit', name: 'Full Audit Log', description: 'Immutable audit trail with export', minPlan: 'enterprise', category: 'Compliance' },
  { id: 'compliance.explainability', name: 'AI Explainability', description: 'Understand why the optimizer made each recommendation', minPlan: 'enterprise', category: 'Compliance' },
  { id: 'esg.tracking', name: 'ESG / Green Bond Tracking', description: 'Sustainability scoring and green bond analysis', minPlan: 'enterprise', category: 'ESG' },

  // ── Reports ───────────────────────────────────────────────────────
  { id: 'reports.pdf', name: 'PDF Export', description: 'Export reports as PDF', minPlan: 'starter', category: 'Reports' },
  { id: 'reports.csv', name: 'CSV Export', description: 'Export data as CSV', minPlan: 'professional', category: 'Reports' },
  { id: 'reports.white_label', name: 'White-Label Reports', description: 'Custom branded reports with company logo', minPlan: 'enterprise', category: 'Reports' },
  { id: 'reports.market_intel', name: 'Market Intelligence Report', description: 'Full market analysis with charts and recommendations', minPlan: 'professional', category: 'Reports' },

  // ── Alerts ────────────────────────────────────────────────────────
  { id: 'alerts.basic', name: '3 Email Alerts', description: 'Basic price change and maturity alerts', minPlan: 'starter', category: 'Alerts' },
  { id: 'alerts.unlimited', name: 'Unlimited Alerts', description: 'All alert types across all channels', minPlan: 'professional', category: 'Alerts' },
  { id: 'alerts.sms', name: 'SMS Alerts', description: 'Text message notifications for critical events', minPlan: 'enterprise', category: 'Alerts' },
  { id: 'alerts.webhook', name: 'Webhook Alerts', description: 'Push notifications to custom endpoints', minPlan: 'enterprise', category: 'Alerts' },

  // ── Support ───────────────────────────────────────────────────────
  { id: 'support.email', name: 'Email Support (48h)', description: 'Basic email support with 48-hour response', minPlan: 'starter', category: 'Support' },
  { id: 'support.priority', name: 'Priority Support (4h)', description: 'Priority email and chat support', minPlan: 'professional', category: 'Support' },
  { id: 'support.dedicated', name: 'Dedicated CSM (1h)', description: 'Dedicated customer success manager with 1-hour SLA', minPlan: 'enterprise', category: 'Support' },
  { id: 'support.sla', name: 'Custom SLA', description: '99.9% uptime guarantee with financial penalty', minPlan: 'enterprise', category: 'Support' },
];

// ── Plan Comparison Functions ─────────────────────────────────────────

/**
 * Check if a plan has access to a feature.
 */
export function hasFeature(plan: PlanTier, featureId: string): boolean {
  const feature = FEATURES.find((f) => f.id === featureId);
  if (!feature) return false;
  // Demo has full access to everything
  if (plan === 'demo') return true;
  return PLAN_ORDER.indexOf(plan) >= PLAN_ORDER.indexOf(feature.minPlan);
}

/**
 * Check if a plan meets or exceeds a minimum tier.
 */
export function hasMinimumPlan(plan: PlanTier, minPlan: PlanTier): boolean {
  return PLAN_ORDER.indexOf(plan) >= PLAN_ORDER.indexOf(minPlan);
}

/**
 * Get all features available for a given plan.
 */
export function getPlanFeatures(plan: PlanTier): FeatureDefinition[] {
  return FEATURES.filter((f) => hasFeature(plan, f.id));
}

/**
 * Get all features NOT available for a given plan.
 */
export function getLockedFeatures(plan: PlanTier): FeatureDefinition[] {
  return FEATURES.filter((f) => !hasFeature(plan, f.id));
}

/**
 * Get the minimum plan required for a feature.
 */
export function getRequiredPlan(featureId: string): PlanTier | null {
  const feature = FEATURES.find((f) => f.id === featureId);
  return feature?.minPlan ?? null;
}

/**
 * Get the next tier up from the current plan.
 */
export function getUpgradePlan(currentPlan: PlanTier): PlanTier | null {
  const idx = PLAN_ORDER.indexOf(currentPlan);
  if (idx >= PLAN_ORDER.length - 1) return null;
  return PLAN_ORDER[idx + 1];
}

/**
 * Calculate savings for annual billing.
 */
export function getAnnualSavings(plan: PlanTier): number {
  const def = PLANS[plan];
  return (def.price - def.priceAnnual) * 12;
}

/**
 * Get features grouped by category, showing availability per plan.
 */
export function getFeatureMatrix(): Array<{
  category: string;
  features: Array<{
    feature: FeatureDefinition;
    starter: boolean;
    professional: boolean;
    enterprise: boolean;
  }>;
}> {
  const categories = [...new Set(FEATURES.map((f) => f.category))];
  return categories.map((category) => ({
    category,
    features: FEATURES.filter((f) => f.category === category).map((feature) => ({
      feature,
      starter: hasFeature('starter', feature.id),
      professional: hasFeature('professional', feature.id),
      enterprise: hasFeature('enterprise', feature.id),
    })),
  }));
}

/**
 * Get plan limits for usage checks.
 */
export function getPlanLimits(plan: PlanTier) {
  const def = PLANS[plan];
  return {
    maxPortfolios: def.maxPortfolios,
    maxInstruments: def.maxInstruments,
    maxUsers: def.maxUsers,
    maxApiProviders: def.maxApiProviders,
    maxAlerts: def.maxAlerts,
  };
}

/**
 * Check if usage exceeds plan limits.
 */
export function checkPlanLimits(
  plan: PlanTier,
  usage: {
    portfolios?: number;
    instruments?: number;
    users?: number;
    apiProviders?: number;
    alerts?: number;
  }
): { withinLimits: boolean; violations: string[] } {
  const limits = getPlanLimits(plan);
  const violations: string[] = [];

  if (usage.portfolios !== undefined && usage.portfolios > limits.maxPortfolios) {
    violations.push(`Portfolios: ${usage.portfolios}/${limits.maxPortfolios}`);
  }
  if (usage.instruments !== undefined && usage.instruments > limits.maxInstruments) {
    violations.push(`Instruments: ${usage.instruments}/${limits.maxInstruments}`);
  }
  if (usage.users !== undefined && usage.users > limits.maxUsers) {
    violations.push(`Users: ${usage.users}/${limits.maxUsers}`);
  }
  if (usage.apiProviders !== undefined && usage.apiProviders > limits.maxApiProviders) {
    violations.push(`API Providers: ${usage.apiProviders}/${limits.maxApiProviders}`);
  }
  if (usage.alerts !== undefined && usage.alerts > limits.maxAlerts) {
    violations.push(`Alerts: ${usage.alerts}/${limits.maxAlerts}`);
  }

  return { withinLimits: violations.length === 0, violations };
}
