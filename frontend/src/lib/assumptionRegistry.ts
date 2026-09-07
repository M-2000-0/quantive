// ── Assumption Registry ──────────────────────────────────────────────
// Tracks every assumption made in forecasts and optimizations.
// Over time, Quantive learns which assumptions are consistently
// accurate or biased — creating institutional intelligence that
// survives personnel changes.

export interface Assumption {
  id: string;
  category: 'inflation' | 'gdp' | 'fx_rates' | 'interest_rates' | 'revenue' | 'spending' | 'political' | 'market' | 'credit_rating' | 'commodity';
  parameter: string;
  unit: string;

  // The prediction
  predictedValue: number;
  predictionRange: { low: number; high: number };
  predictionDate: string;
  targetDate: string;
  source: string;
  confidenceLevel: 'high' | 'medium' | 'low';
  justification: string;

  // Who made it
  author: string;
  authorRole: string;
  linkedDecisionId?: string;

  // Resolution
  actualValue?: number;
  resolvedDate?: string;
  resolutionStatus: 'pending' | 'resolved' | 'partially_resolved' | 'expired';

  // Accuracy tracking
  accuracy?: {
    absoluteError: number;
    percentError: number;
    withinRange: boolean;
    grade: 'A' | 'B' | 'C' | 'D' | 'F';
  };

  // Metadata
  version: number;
  tags: string[];
}

// ── Bias Tracking ────────────────────────────────────────────────────

export interface BiasReport {
  category: string;
  totalAssumptions: number;
  resolvedAssumptions: number;
  avgAbsoluteError: number;
  avgPercentError: number;
  withinRangeRate: number;
  biasDirection: 'overestimate' | 'underestimate' | 'neutral';
  biasMagnitude: number;
  trend: 'improving' | 'stable' | 'worsening';
  recommendation: string;
}

// ── In-Memory Store ──────────────────────────────────────────────────

const assumptions: Map<string, Assumption> = new Map();
let nextId = 1;

// ── Decision Quality Metrics ─────────────────────────────────────────

export function getEvidenceGatheringScore(): number {
  const all = Array.from(assumptions.values());
  const documented = all.filter(a => a.justification && a.justification.trim().length > 0);
  return all.length > 0 ? Math.round(documented.length / all.length * 100) : 0;
}

export function getScenarioConsiderationScore(): number {
  const categories = new Set(
    Array.from(assumptions.values()).map(a => a.category)
  );
  const coreCategories: Assumption['category'][] = ['inflation', 'gdp', 'fx_rates', 'interest_rates', 'revenue', 'spending'];
  const covered = coreCategories.filter(c => categories.has(c));
  return categories.size > 0 ? Math.round(covered.length / coreCategories.length * 100) : 0;
}

export function getRiskReviewCompletenessScore(): number {
  const all = Array.from(assumptions.values());
  const withRiskInsight = all.filter(a => 
    /risk|volatility|downside|upside/i.test(a.justification || '') || 
    /risk|volatility|downside|upside/i.test(a.tags?.join(' ') || '')
  );
  return all.length > 0 ? Math.round(withRiskInsight.length / all.length * 100) : 0;
}

export function getGovernmentResilienceScores(): {
  fiscal: number;
  infrastructure: number;
  energy: number;
  demographic: number;
} {
  const categories = new Set(
    Array.from(assumptions.values()).map(a => a.category)
  );

  const scoreForCat = (cat: Assumption['category']): number => {
    const catAssumptions = Array.from(assumptions.values()).filter(a => a.category === cat);
    if (catAssumptions.length === 0) return 50;
    const resolved = catAssumptions.filter(a => a.resolutionStatus === 'resolved' && a.accuracy);
    if (resolved.length === 0) return 50;
    const avgError = resolved.reduce((s, a) => s + (a.accuracy?.percentError || 0), 0) / resolved.length;
    return Math.round(100 - Math.min(100, avgError * 2));
  };

  const fiscalCats: Assumption['category'][] = ['inflation', 'interest_rates', 'revenue', 'spending'];
  const infraCats: Assumption['category'][] = ['fx_rates', 'commodity', 'credit_rating'];
  const energyCats: Assumption['category'][] = ['market']; // energy-related
  const demoCats: Assumption['category'][] = ['political', 'market', 'revenue']; // demographic-impacting

  const fiscal = fiscalCats.some(c => categories.has(c)) ? scoreForCat(fiscalCats.find(c => categories.has(c) || '') || 'inflation') : 50;
  const infrastructure = infraCats.some(c => categories.has(c)) ? scoreForCat(infraCats.find(c => categories.has(c) || '') || 'fx_rates') : 50;
  const energy = energyCats.some(c => categories.has(c)) ? scoreForCat(energyCats.find(c => categories.has(c) || '') || 'market') : 50;
  const demographic = demoCats.some(c => categories.has(c)) ? scoreForCat(demoCats.find(c => categories.has(c) || '') || 'political') : 50;

  return { fiscal, infrastructure, energy, demographic };
}

export function registerAssumption(input: Omit<Assumption, 'id' | 'version' | 'resolutionStatus' | 'accuracy'>): Assumption {
  const id = `ASM-${Date.now()}-${nextId++}`;
  const assumption: Assumption = {
    ...input,
    id,
    version: 1,
    resolutionStatus: 'pending',
  };
  assumptions.set(id, assumption);
  return assumption;
}

export function resolveAssumption(id: string, actualValue: number): Assumption {
  const assumption = assumptions.get(id);
  if (!assumption) throw new Error(`Assumption ${id} not found`);

  assumption.actualValue = actualValue;
  assumption.resolvedDate = new Date().toISOString();
  assumption.resolutionStatus = 'resolved';

  // Compute accuracy
  const absoluteError = Math.abs(actualValue - assumption.predictedValue);
  const percentError = assumption.predictedValue !== 0
    ? (absoluteError / Math.abs(assumption.predictedValue)) * 100
    : 0;
  const withinRange = actualValue >= assumption.predictionRange.low && actualValue <= assumption.predictionRange.high;

  let grade: 'A' | 'B' | 'C' | 'D' | 'F';
  if (percentError <= 5) grade = 'A';
  else if (percentError <= 10) grade = 'B';
  else if (percentError <= 20) grade = 'C';
  else if (percentError <= 35) grade = 'D';
  else grade = 'F';

  assumption.accuracy = {
    absoluteError,
    percentError: Math.round(percentError * 100) / 100,
    withinRange,
    grade,
  };

  return assumption;
}

export function getAssumptionsByCategory(category: Assumption['category']): Assumption[] {
  return Array.from(assumptions.values())
    .filter(a => a.category === category)
    .sort((a, b) => new Date(b.predictionDate).getTime() - new Date(a.predictionDate).getTime());
}

export function getPendingAssumptions(): Assumption[] {
  return Array.from(assumptions.values())
    .filter(a => a.resolutionStatus === 'pending' && new Date(a.targetDate) < new Date())
    .sort((a, b) => new Date(a.targetDate).getTime() - new Date(b.targetDate).getTime());
}

export function getBiasReport(category?: Assumption['category']): BiasReport[] {
  const categories: Assumption['category'][] = category
    ? [category]
    : ['inflation', 'gdp', 'fx_rates', 'interest_rates', 'revenue', 'spending', 'market', 'credit_rating'];

  return categories.map(cat => {
    const all = Array.from(assumptions.values()).filter(a => a.category === cat);
    const resolved = all.filter(a => a.resolutionStatus === 'resolved' && a.accuracy);

    const totalError = resolved.reduce((s, a) => s + (a.accuracy?.absoluteError || 0), 0);
    const totalPctError = resolved.reduce((s, a) => s + (a.accuracy?.percentError || 0), 0);
    const withinRange = resolved.filter(a => a.accuracy?.withinRange).length;
    const overestimates = resolved.filter(a => (a.actualValue || 0) < a.predictedValue).length;

    const avgAbsError = resolved.length > 0 ? totalError / resolved.length : 0;
    const avgPctError = resolved.length > 0 ? totalPctError / resolved.length : 0;
    const withinRangeRate = resolved.length > 0 ? withinRange / resolved.length : 0;

    const biasDirection: BiasReport['biasDirection'] =
      overestimates > resolved.length * 0.6 ? 'overestimate' :
      overestimates < resolved.length * 0.4 ? 'underestimate' : 'neutral';

    const gradeDistribution = resolved.reduce((acc, a) => {
      const g = a.accuracy?.grade || 'F';
      acc[g] = (acc[g] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    const aCount = gradeDistribution['A'] || 0;
    const bCount = gradeDistribution['B'] || 0;
    const trend: BiasReport['trend'] =
      resolved.length < 3 ? 'stable' :
      aCount + bCount > resolved.length * 0.7 ? 'improving' :
      aCount + bCount < resolved.length * 0.3 ? 'worsening' : 'stable';

    const recommendation =
      biasDirection === 'overestimate' ? `${cat} assumptions tend to overestimate. Consider systematic downward adjustment.` :
      biasDirection === 'underestimate' ? `${cat} assumptions tend to underestimate. Consider systematic upward adjustment.` :
      `${cat} assumptions are well-calibrated. Maintain current methodology.`;

    return {
      category: cat,
      totalAssumptions: all.length,
      resolvedAssumptions: resolved.length,
      avgAbsoluteError: Math.round(avgAbsError * 100) / 100,
      avgPercentError: Math.round(avgPctError * 100) / 100,
      withinRangeRate: Math.round(withinRangeRate * 100),
      biasDirection,
      biasMagnitude: Math.round(avgPctError),
      trend,
      recommendation,
    };
  });
}

export function getAssumptionAccuracy(): {
  total: number;
  resolved: number;
  pending: number;
  avgGrade: string;
  withinRangeRate: number;
  categoryScores: Record<string, number>;
} {
  const all = Array.from(assumptions.values());
  const resolved = all.filter(a => a.resolutionStatus === 'resolved' && a.accuracy);
  const pending = all.filter(a => a.resolutionStatus === 'pending');

  const gradePoints: Record<string, number> = { A: 4, B: 3, C: 2, D: 1, F: 0 };
  const avgPoints = resolved.length > 0
    ? resolved.reduce((s, a) => s + gradePoints[a.accuracy?.grade || 'F'], 0) / resolved.length
    : 3;

  const avgGrade = avgPoints >= 3.5 ? 'A' : avgPoints >= 2.5 ? 'B' : avgPoints >= 1.5 ? 'C' : avgPoints >= 0.5 ? 'D' : 'F';
  const withinRange = resolved.filter(a => a.accuracy?.withinRange).length;

  const categories = ['inflation', 'gdp', 'fx_rates', 'interest_rates', 'market', 'revenue'];
  const categoryScores: Record<string, number> = {};
  for (const cat of categories) {
    const catResolved = resolved.filter(a => a.category === cat);
    if (catResolved.length > 0) {
      const pts = catResolved.reduce((s, a) => s + gradePoints[a.accuracy?.grade || 'F'], 0) / catResolved.length;
      categoryScores[cat] = Math.round(pts / 4 * 100);
    }
  }

  return {
    total: all.length,
    resolved: resolved.length,
    pending: pending.length,
    avgGrade,
    withinRangeRate: resolved.length > 0 ? Math.round(withinRange / resolved.length * 100) : 0,
    categoryScores,
  };
}

// ── Decision Quality Calculation ─────────────────────────────────────

export function calculateDecisionQualityScore(assumptionAccuracy: number, governmentResilience: number, metrics?: {
  evidenceGathering?: number;
  scenarioConsideration?: number;
  riskReviewCompleteness?: number;
}): number {
  const defaultMetrics = {
    evidenceGathering: getEvidenceGatheringScore(),
    scenarioConsideration: getScenarioConsiderationScore(),
    riskReviewCompleteness: getRiskReviewCompletenessScore(),
  };

  const m = { ...defaultMetrics, ...metrics };

  const weights = {
    evidenceGathering: 0.25,
    scenarioConsideration: 0.25,
    riskReviewCompleteness: 0.15,
    assumptionAccuracy: 0.20,
    governmentResilience: 0.15,
  };

  const score =
    (m.evidenceGathering / 100) * weights.evidenceGathering +
    (m.scenarioConsideration / 100) * weights.scenarioConsideration +
    (m.riskReviewCompleteness / 100) * weights.riskReviewCompleteness +
    (assumptionAccuracy / 100) * weights.assumptionAccuracy +
    (governmentResilience / 100) * weights.governmentResilience;

  return Math.min(100, Math.max(0, Math.round(score * 100) / 10));
}

// ── Singleton ────────────────────────────────────────────────────────

let _instance: ReturnType<typeof createRegistry> | null = null;

function createRegistry() {
  return {
    register: registerAssumption,
    resolve: resolveAssumption,
    getByCategory: getAssumptionsByCategory,
    getAssumptionsByCategory,
    getPending: getPendingAssumptions,
    getBiasReport,
    getAccuracy: getAssumptionAccuracy,
  };
}

export function getAssumptionRegistry() {
  if (!_instance) _instance = createRegistry();
  return _instance;
}
