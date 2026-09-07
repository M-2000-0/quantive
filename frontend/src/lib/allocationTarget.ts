// ── Allocation Target Service ────────────────────────────────────────
// Defines target allocations by risk profile, detects drift from
// targets, and generates rebalancing trade suggestions.

// ── Types ────────────────────────────────────────────────────────────

export type RiskProfile = 'conservative' | 'balanced' | 'aggressive';

export interface AssetAllocation {
  assetClass: string;
  category: 'equity' | 'fixed_income' | 'alternatives' | 'cash';
  targetPct: number;
  currentPct: number;
  drift: number; // currentPct - targetPct (positive = overweight)
  holdings?: HoldingAllocation[];
}

export interface HoldingAllocation {
  name: string;
  ticker?: string;
  type: string;
  principal: number;
  currentPct: number;
  targetPct: number;
  sector?: string;
  currency?: string;
}

export interface RebalanceTrade {
  action: 'buy' | 'sell';
  assetClass: string;
  holding?: string;
  amount: number; // USD
  currentPct: number;
  targetPct: number;
  rationale: string;
  priority: 'high' | 'medium' | 'low';
}

export interface ProfileRecommendation {
  profile: RiskProfile;
  confidence: number; // 0-100
  rationale: string;
  targetAllocation: TargetAllocation;
  riskScore: number; // 1-100
  expectedReturn: string;
  maxDrawdown: string;
  timeHorizon: string;
}

export interface TargetAllocation {
  profile: RiskProfile;
  label: string;
  description: string;
  buckets: Array<{
    category: string;
    assetClass: string;
    targetPct: number;
    minPct: number;
    maxPct: number;
    examples: string[];
  }>;
}

// ── Risk Profile Definitions ────────────────────────────────────────

export const TARGET_ALLOCATIONS: Record<RiskProfile, TargetAllocation> = {
  conservative: {
    profile: 'conservative',
    label: 'Conservative',
    description: 'Capital preservation with steady income. Minimal equity exposure, focus on high-quality bonds and cash equivalents.',
    buckets: [
      {
        category: 'fixed_income',
        assetClass: 'Government Bonds',
        targetPct: 35,
        minPct: 30,
        maxPct: 40,
        examples: ['US Treasuries (2-10Y)', 'TIPS', 'Agency MBS'],
      },
      {
        category: 'fixed_income',
        assetClass: 'Corporate Bonds (IG)',
        targetPct: 25,
        minPct: 20,
        maxPct: 30,
        examples: ['Investment-grade corporates', 'AA-rated notes'],
      },
      {
        category: 'equity',
        assetClass: 'Dividend Equities',
        targetPct: 15,
        minPct: 10,
        maxPct: 20,
        examples: ['Dividend Aristocrats', 'Utilities', 'Consumer Staples'],
      },
      {
        category: 'equity',
        assetClass: 'International Equity',
        targetPct: 5,
        minPct: 0,
        maxPct: 10,
        examples: ['Developed market index'],
      },
      {
        category: 'alternatives',
        assetClass: 'REITs',
        targetPct: 5,
        minPct: 0,
        maxPct: 10,
        examples: ['Real estate investment trusts'],
      },
      {
        category: 'cash',
        assetClass: 'Cash & Equivalents',
        targetPct: 15,
        minPct: 10,
        maxPct: 20,
        examples: ['Money market', 'T-bills', 'Short-term CDs'],
      },
    ],
  },
  balanced: {
    profile: 'balanced',
    label: 'Balanced',
    description: 'Growth with guardrails. Meaningful equity exposure tempered by bonds and alternatives for stability.',
    buckets: [
      {
        category: 'equity',
        assetClass: 'US Large Cap',
        targetPct: 25,
        minPct: 20,
        maxPct: 30,
        examples: ['S&P 500 index', 'Large-cap blend'],
      },
      {
        category: 'equity',
        assetClass: 'International Equity',
        targetPct: 15,
        minPct: 10,
        maxPct: 20,
        examples: ['Developed + emerging markets'],
      },
      {
        category: 'equity',
        assetClass: 'Small Cap Value',
        targetPct: 10,
        minPct: 5,
        maxPct: 15,
        examples: ['Small-cap value index'],
      },
      {
        category: 'fixed_income',
        assetClass: 'Government Bonds',
        targetPct: 20,
        minPct: 15,
        maxPct: 25,
        examples: ['Intermediate Treasuries', 'TIPS'],
      },
      {
        category: 'fixed_income',
        assetClass: 'Corporate Bonds',
        targetPct: 10,
        minPct: 5,
        maxPct: 15,
        examples: ['IG corporates', 'High-yield (limited)'],
      },
      {
        category: 'alternatives',
        assetClass: 'REITs & Commodities',
        targetPct: 10,
        minPct: 5,
        maxPct: 15,
        examples: ['REIT index', 'Commodity ETF'],
      },
      {
        category: 'cash',
        assetClass: 'Cash',
        targetPct: 10,
        minPct: 5,
        maxPct: 15,
        examples: ['Money market', 'T-bills'],
      },
    ],
  },
  aggressive: {
    profile: 'aggressive',
    label: 'Aggressive',
    description: 'Maximum long-term growth. High equity concentration with tolerance for significant short-term volatility.',
    buckets: [
      {
        category: 'equity',
        assetClass: 'US Growth Equities',
        targetPct: 30,
        minPct: 25,
        maxPct: 35,
        examples: ['Nasdaq 100', 'Growth ETF', 'Tech sector'],
      },
      {
        category: 'equity',
        assetClass: 'US Value Equities',
        targetPct: 15,
        minPct: 10,
        maxPct: 20,
        examples: ['Value ETF', 'Small-cap value'],
      },
      {
        category: 'equity',
        assetClass: 'International & EM',
        targetPct: 20,
        minPct: 15,
        maxPct: 25,
        examples: ['EAFE index', 'Emerging markets', 'Frontier markets'],
      },
      {
        category: 'fixed_income',
        assetClass: 'Bonds',
        targetPct: 15,
        minPct: 10,
        maxPct: 20,
        examples: ['Short-duration Treasuries', 'TIPS'],
      },
      {
        category: 'alternatives',
        assetClass: 'Alternatives',
        targetPct: 15,
        minPct: 10,
        maxPct: 20,
        examples: ['REITs', 'Commodities', 'Crypto (limited)'],
      },
      {
        category: 'cash',
        assetClass: 'Cash',
        targetPct: 5,
        minPct: 0,
        maxPct: 10,
        examples: ['Money market'],
      },
    ],
  },
};

// ── Risk Profile Assessment Questions ───────────────────────────────

export interface QuizQuestion {
  id: string;
  question: string;
  category: 'timeline' | 'income' | 'loss_tolerance' | 'goals' | 'experience';
  options: Array<{
    label: string;
    value: number; // 1-5 scale (1=conservative, 5=aggressive)
    description?: string;
  }>;
}

export const QUIZ_QUESTIONS: QuizQuestion[] = [
  {
    id: 'timeline',
    question: 'When will you need to start withdrawing from this portfolio?',
    category: 'timeline',
    options: [
      { label: 'Within 2 years', value: 1, description: 'Near-term need for funds' },
      { label: '3-5 years', value: 2, description: 'Short-to-medium timeline' },
      { label: '5-10 years', value: 3, description: 'Medium timeline' },
      { label: '10-20 years', value: 4, description: 'Long timeline' },
      { label: '20+ years', value: 5, description: 'Very long time horizon' },
    ],
  },
  {
    id: 'income_stability',
    question: 'How stable is your current income?',
    category: 'income',
    options: [
      { label: 'Very unstable / retired', value: 1, description: 'Income varies significantly or no employment income' },
      { label: 'Somewhat unstable', value: 2, description: 'Freelance or commission-based' },
      { label: 'Moderately stable', value: 3, description: 'Salaried but could change' },
      { label: 'Very stable', value: 4, description: 'Tenured or government position' },
      { label: 'Extremely stable + growing', value: 5, description: 'Multiple income streams, growing' },
    ],
  },
  {
    id: 'loss_tolerance_1',
    question: 'If your portfolio dropped 20% in one month, what would you do?',
    category: 'loss_tolerance',
    options: [
      { label: 'Sell everything immediately', value: 1, description: 'Cannot tolerate further losses' },
      { label: 'Sell some to reduce risk', value: 2, description: 'Partial defensive move' },
      { label: 'Hold and wait', value: 3, description: 'Uncomfortable but won\'t act' },
      { label: 'Hold and consider buying more', value: 4, description: 'See opportunity in decline' },
      { label: 'Buy aggressively', value: 5, description: 'Deploy additional capital' },
    ],
  },
  {
    id: 'loss_tolerance_2',
    question: 'What is the maximum portfolio loss you could accept in a single year?',
    category: 'loss_tolerance',
    options: [
      { label: 'Less than 5%', value: 1, description: 'Minimal loss tolerance' },
      { label: '5-10%', value: 2, description: 'Low loss tolerance' },
      { label: '10-20%', value: 3, description: 'Moderate loss tolerance' },
      { label: '20-30%', value: 4, description: 'Higher loss tolerance' },
      { label: 'More than 30%', value: 5, description: 'High loss tolerance' },
    ],
  },
  {
    id: 'primary_goal',
    question: 'What is your primary investment goal?',
    category: 'goals',
    options: [
      { label: 'Preserve my capital', value: 1, description: 'Don\'t lose what I have' },
      { label: 'Generate steady income', value: 2, description: 'Regular cash flow' },
      { label: 'Beat inflation', value: 3, description: 'Maintain purchasing power' },
      { label: 'Grow wealth steadily', value: 4, description: 'Long-term accumulation' },
      { label: 'Maximize growth', value: 5, description: 'Aggressive wealth building' },
    ],
  },
  {
    id: 'emergency_fund',
    question: 'Do you have an emergency fund covering 6+ months of expenses?',
    category: 'income',
    options: [
      { label: 'No emergency fund', value: 1, description: 'Build this first' },
      { label: '1-3 months saved', value: 2, description: 'Partial safety net' },
      { label: '3-6 months saved', value: 3, description: 'Reasonable safety net' },
      { label: '6-12 months saved', value: 4, description: 'Strong safety net' },
      { label: '12+ months saved', value: 5, description: 'Very strong safety net' },
    ],
  },
  {
    id: 'investment_experience',
    question: 'How would you describe your investment experience?',
    category: 'experience',
    options: [
      { label: 'Complete beginner', value: 1, description: 'Never invested before' },
      { label: 'Some experience', value: 2, description: 'Basic knowledge, few investments' },
      { label: 'Intermediate', value: 3, description: 'Diversified portfolio, understand basics' },
      { label: 'Experienced', value: 4, description: 'Multiple asset classes, active management' },
      { label: 'Very experienced', value: 5, description: 'Derivatives, alternatives, complex strategies' },
    ],
  },
  {
    id: 'income_dependency',
    question: 'How dependent are you on this portfolio for living expenses?',
    category: 'income',
    options: [
      { label: 'Entirely dependent', value: 1, description: 'Portfolio funds all expenses' },
      { label: 'Heavily dependent', value: 2, description: 'Portfolio covers 50%+ of expenses' },
      { label: 'Moderately dependent', value: 3, description: 'Portfolio covers 25-50%' },
      { label: 'Slightly dependent', value: 4, description: 'Portfolio covers <25%' },
      { label: 'Not dependent', value: 5, description: 'Other income covers all expenses' },
    ],
  },
  {
    id: 'market_crash_history',
    question: 'Did you invest during the last major market downturn? What happened?',
    category: 'loss_tolerance',
    options: [
      { label: 'Wasn\'t investing yet', value: 3, description: 'No experience to draw from' },
      { label: 'Sold at a loss', value: 1, description: 'Couldn\'t handle the losses' },
      { label: 'Sold some, held some', value: 2, description: 'Mixed response' },
      { label: 'Held through it', value: 4, description: 'Stayed the course' },
      { label: 'Bought more', value: 5, description: 'Added capital during the dip' },
    ],
  },
  {
    id: 'return_vs_safety',
    question: 'Would you accept a lower return for more safety, or higher return for more risk?',
    category: 'loss_tolerance',
    options: [
      { label: 'Much lower return for safety', value: 1, description: 'Safety is paramount' },
      { label: 'Slightly lower return for safety', value: 2, description: 'Lean toward safety' },
      { label: 'Equal weight to both', value: 3, description: 'Balance return and safety' },
      { label: 'Slightly higher return for risk', value: 4, description: 'Lean toward growth' },
      { label: 'Much higher return for risk', value: 5, description: 'Maximize growth potential' },
    ],
  },
];

// ── Profile Assessment ──────────────────────────────────────────────

export function assessProfile(answers: Record<string, number>): ProfileRecommendation {
  const scores = Object.values(answers);
  const avg = scores.reduce((sum, s) => sum + s, 0) / scores.length;

  let profile: RiskProfile;
  let confidence: number;
  let rationale: string;

  if (avg <= 2.2) {
    profile = 'conservative';
    confidence = Math.min(95, Math.round(60 + (2.2 - avg) * 30));
    rationale = `Your answers indicate a strong preference for capital preservation and income generation. With a score of ${avg.toFixed(1)}/5.0, a conservative allocation focusing on high-quality bonds and dividend equities aligns with your risk tolerance and timeline.`;
  } else if (avg <= 3.5) {
    profile = 'balanced';
    confidence = Math.min(95, Math.round(60 + Math.abs(avg - 2.85) * 20));
    rationale = `Your responses suggest a moderate risk tolerance with a need for both growth and stability. A balanced approach splitting between equities and fixed income provides growth potential while limiting downside.`;
  } else {
    profile = 'aggressive';
    confidence = Math.min(95, Math.round(60 + (avg - 3.5) * 25));
    rationale = `Your answers reflect high risk tolerance and a long time horizon. An aggressive allocation with heavy equity exposure maximizes long-term growth potential, accepting short-term volatility for superior compounding.`;
  }

  return {
    profile,
    confidence,
    rationale,
    targetAllocation: TARGET_ALLOCATIONS[profile],
    riskScore: Math.round(avg * 20),
    expectedReturn: profile === 'conservative' ? '4-5% annually' : profile === 'balanced' ? '6-8% annually' : '8-12% annually',
    maxDrawdown: profile === 'conservative' ? '5-10%' : profile === 'balanced' ? '15-25%' : '30-50%',
    timeHorizon: profile === 'conservative' ? '1-5 years' : profile === 'balanced' ? '5-15 years' : '15+ years',
  };
}

// ── Drift Detection & Rebalancing ───────────────────────────────────

const DRIFT_THRESHOLD = 5; // 5% drift triggers rebalancing alert

export function calculateDrift(
  currentAllocation: Record<string, number>,
  targetProfile: RiskProfile,
): AssetAllocation[] {
  const target = TARGET_ALLOCATIONS[targetProfile];

  return target.buckets.map((bucket) => {
    const currentPct = currentAllocation[bucket.assetClass] || 0;
    const drift = currentPct - bucket.targetPct;
    return {
      assetClass: bucket.assetClass,
      category: bucket.category as AssetAllocation['category'],
      targetPct: bucket.targetPct,
      currentPct,
      drift,
      holdings: [], // Will be populated with actual holdings
    };
  });
}

export function generateRebalanceTrades(
  allocations: AssetAllocation[],
  totalPortfolioValue: number,
): RebalanceTrade[] {
  const trades: RebalanceTrade[] = [];

  for (const alloc of allocations) {
    const absDrift = Math.abs(alloc.drift);
    if (absDrift < 1) continue; // Skip minimal drift

    const targetValue = (alloc.targetPct / 100) * totalPortfolioValue;
    const currentValue = (alloc.currentPct / 100) * totalPortfolioValue;
    const tradeAmount = Math.abs(targetValue - currentValue);
    const isOverweight = alloc.drift > 0;

    trades.push({
      action: isOverweight ? 'sell' : 'buy',
      assetClass: alloc.assetClass,
      amount: tradeAmount,
      currentPct: alloc.currentPct,
      targetPct: alloc.targetPct,
      rationale: isOverweight
        ? `Overweight by ${alloc.drift.toFixed(1)}%. Reduce to target allocation.`
        : `Underweight by ${Math.abs(alloc.drift).toFixed(1)}%. Increase to target allocation.`,
      priority: absDrift >= 10 ? 'high' : absDrift >= 5 ? 'medium' : 'low',
    });
  }

  // Sort by priority and amount
  return trades.sort((a, b) => {
    const priorityOrder = { high: 0, medium: 1, low: 2 };
    return (priorityOrder[a.priority] - priorityOrder[b.priority]) || (b.amount - a.amount);
  });
}

export function hasSignificantDrift(allocations: AssetAllocation[]): boolean {
  return allocations.some((a) => Math.abs(a.drift) >= DRIFT_THRESHOLD);
}

export function getDriftSeverity(allocations: AssetAllocation[]): 'none' | 'minor' | 'moderate' | 'significant' {
  const maxDrift = Math.max(...allocations.map((a) => Math.abs(a.drift)));
  if (maxDrift < 2) return 'none';
  if (maxDrift < 5) return 'minor';
  if (maxDrift < 10) return 'moderate';
  return 'significant';
}

// ── Portfolio Health Score ──────────────────────────────────────────

export interface HealthScore {
  overall: number; // 0-100
  grade: 'A+' | 'A' | 'B+' | 'B' | 'C+' | 'C' | 'D' | 'F';
  dimensions: Array<{
    name: string;
    score: number;
    weight: number;
    description: string;
    status: 'excellent' | 'good' | 'fair' | 'poor';
  }>;
  recommendations: string[];
}

export function calculateHealthScore(
  allocations: AssetAllocation[],
  targetProfile: RiskProfile,
  portfolioMetrics: {
    totalPrincipal: number;
    avgYield: number;
    avgDuration: number;
    riskScore: number;
    unrealizedPnl: number;
    instrumentCount: number;
  },
): HealthScore {
  const target = TARGET_ALLOCATIONS[targetProfile];

  // 1. Diversification Score (25% weight)
  const categoryDrift = allocations.reduce((sum, a) => sum + Math.abs(a.drift), 0) / allocations.length;
  const diversificationScore = Math.max(0, 100 - categoryDrift * 5);

  // 2. Target Alignment Score (25% weight)
  const alignmentScore = Math.max(0, 100 - categoryDrift * 8);

  // 3. Risk Appropriateness Score (20% weight)
  const profileRiskRanges: Record<RiskProfile, [number, number]> = {
    conservative: [0, 35],
    balanced: [30, 65],
    aggressive: [55, 100],
  };
  const [minRisk, maxRisk] = profileRiskRanges[targetProfile];
  const riskInRange = portfolioMetrics.riskScore >= minRisk && portfolioMetrics.riskScore <= maxRisk;
  const riskScore = riskInRange
    ? 100 - Math.abs(portfolioMetrics.riskScore - (minRisk + maxRisk) / 2) * 2
    : Math.max(0, 60 - Math.abs(portfolioMetrics.riskScore - (minRisk + maxRisk) / 2) * 3);

  // 4. Yield Quality Score (15% weight)
  const expectedYields: Record<RiskProfile, [number, number]> = {
    conservative: [3.5, 5.5],
    balanced: [4.5, 7.0],
    aggressive: [5.5, 9.0],
  };
  const [minYield, maxYield] = expectedYields[targetProfile];
  const yieldScore = portfolioMetrics.avgYield >= minYield && portfolioMetrics.avgYield <= maxYield
    ? 90
    : Math.max(20, 80 - Math.abs(portfolioMetrics.avgYield - (minYield + maxYield) / 2) * 15);

  // 5. Liquidity Score (15% weight)
  const hasCash = allocations.find((a) => a.category === 'cash');
  const cashPct = hasCash?.currentPct || 0;
  const liquidityScore = cashPct >= 10 ? 90 : cashPct >= 5 ? 70 : cashPct > 0 ? 50 : 30;

  const dimensions = [
    { name: 'Diversification', score: Math.round(diversificationScore), weight: 25, description: 'Spread across asset classes and sectors', status: getStatus(diversificationScore) },
    { name: 'Target Alignment', score: Math.round(alignmentScore), weight: 25, description: 'How well current allocation matches your target', status: getStatus(alignmentScore) },
    { name: 'Risk Fit', score: Math.round(Math.max(0, riskScore)), weight: 20, description: 'Risk level appropriate for your profile', status: getStatus(riskScore) },
    { name: 'Yield Quality', score: Math.round(yieldScore), weight: 15, description: 'Income generation vs your profile expectations', status: getStatus(yieldScore) },
    { name: 'Liquidity', score: Math.round(liquidityScore), weight: 15, description: 'Cash reserves for opportunities and emergencies', status: getStatus(liquidityScore) },
  ];

  const overall = Math.round(
    dimensions.reduce((sum, d) => sum + (d.score * d.weight) / 100, 0),
  );

  const grade = getGrade(overall);

  const recommendations: string[] = [];
  if (alignmentScore < 60) recommendations.push('Rebalance your portfolio to align with your target allocation.');
  if (riskScore < 50) recommendations.push('Your risk level may not match your profile. Consider adjusting equity/fixed income mix.');
  if (liquidityScore < 60) recommendations.push('Increase cash reserves to at least 10% of portfolio value.');
  if (portfolioMetrics.instrumentCount < 5) recommendations.push('Consider adding more holdings for better diversification.');
  if (categoryDrift > 8) recommendations.push('Significant allocation drift detected. Rebalancing recommended.');

  return { overall, grade, dimensions, recommendations };
}

function getStatus(score: number): 'excellent' | 'good' | 'fair' | 'poor' {
  if (score >= 80) return 'excellent';
  if (score >= 60) return 'good';
  if (score >= 40) return 'fair';
  return 'poor';
}

function getGrade(score: number): HealthScore['grade'] {
  if (score >= 95) return 'A+';
  if (score >= 90) return 'A';
  if (score >= 85) return 'B+';
  if (score >= 75) return 'B';
  if (score >= 65) return 'C+';
  if (score >= 55) return 'C';
  if (score >= 40) return 'D';
  return 'F';
}
