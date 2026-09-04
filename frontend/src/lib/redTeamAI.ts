// ── Red Team AI ──────────────────────────────────────────────────────
// Every recommendation gets challenged by a second model.
// This mirrors real government decision-making where proposals
// face scrutiny from independent reviewers.

export interface RedTeamChallenge {
  id: string;
  recommendationId: string;
  timestamp: string;

  // The advisor's recommendation being challenged
  advisorRecommendation: {
    strategy: string;
    estimatedSavings: number;
    confidence: number;
  };

  // The challenger's critique
  challenge: {
    verdict: 'endorse' | 'challenge' | 'partial_challenge' | 'reject';
    confidenceInCritique: number;
    summary: string;
    detailedArguments: ChallengeArgument[];
    alternativeStrategy?: string;
    riskBlindSpots: string[];
    missingAssumptions: string[];
    historicalPrecedent?: string;
  };

  // Resolution
  resolution?: {
    outcome: 'accepted_challenge' | 'overruled' | 'modified' | 'deferred';
    modifiedStrategy?: string;
    rationale: string;
    resolvedBy: string;
    resolvedAt: string;
  };
}

export interface ChallengeArgument {
  id: string;
  type: 'risk' | 'assumption' | 'timing' | 'concentration' | 'liquidity' | 'regulatory' | 'political' | 'operational';
  severity: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  evidence: string;
  potentialImpact: string;
  mitigation?: string;
}

// ── Challenge Templates ──────────────────────────────────────────────

const CHALLENGE_TEMPLATES: Record<string, () => Partial<RedTeamChallenge['challenge']>> = {
  duration: () => ({
    detailedArguments: [
      {
        id: 'CHG-D1',
        type: 'concentration',
        severity: 'high',
        title: 'Maturity Wall Concentration',
        evidence: 'Extending duration creates a maturity wall in the target year.',
        potentialImpact: 'Refinancing $XB in a single year increases rollover risk.',
        mitigation: 'Consider staggering maturities across 2-3 years instead of concentrating.',
      },
      {
        id: 'CHG-D2',
        type: 'timing',
        severity: 'medium',
        title: 'Rate Timing Risk',
        evidence: 'Duration extension at current rates assumes rates stay elevated.',
        potentialImpact: 'If rates decline 100bps within 12 months, shorter duration would be cheaper.',
        mitigation: 'Consider a barbell strategy: short + long instead of pure extension.',
      },
    ],
    riskBlindSpots: [
      'Does not model scenario where rates drop rapidly',
      'Does not account for potential credit rating impact of longer duration',
    ],
    historicalPrecedent: 'Greece 2010: Extended duration under stress, then faced acute refinancing crisis.',
  }),

  hedging: () => ({
    detailedArguments: [
      {
        id: 'CHG-H1',
        type: 'liquidity',
        severity: 'high',
        title: 'Hedging Cost Drag',
        evidence: 'FX hedging costs currently exceed the potential FX risk reduction.',
        potentialImpact: 'Hedging may reduce returns by $XM while the unhedged scenario has only Y% probability of material loss.',
        mitigation: 'Consider partial hedging (50% of exposure) to balance cost and protection.',
      },
      {
        id: 'CHG-H2',
        type: 'operational',
        severity: 'medium',
        title: 'Hedge Effectiveness Risk',
        evidence: 'Cross-currency basis swaps may underperform during market stress.',
        potentialImpact: 'Hedge may provide false sense of security during exactly the conditions it is meant to protect against.',
        mitigation: 'Add stress testing for hedge failure scenarios.',
      },
    ],
    riskBlindSpots: [
      'Correlation between FX and rates increases during crises',
      'Counterparty risk on OTC derivatives not fully modeled',
    ],
  }),

  cost_reduction: () => ({
    detailedArguments: [
      {
        id: 'CHG-C1',
        type: 'risk',
        severity: 'critical',
        title: 'Hidden Cost Transfer',
        evidence: 'Lowering coupon may increase maturity concentration or reduce investor base diversity.',
        potentialImpact: 'Savings of $XM may be offset by $XM+ in increased rollover risk.',
        mitigation: 'Evaluate total cost of issuance including rollover probability.',
      },
    ],
    riskBlindSpots: [
      'Investor demand assumptions based on recent issuance, not stress conditions',
    ],
    alternativeStrategy: 'Consider maintaining coupon but extending maturity to reduce rollover frequency.',
  }),
};

// ── In-Memory Store ──────────────────────────────────────────────────

const challenges: Map<string, RedTeamChallenge> = new Map();
let nextId = 1;

// ── Public API ───────────────────────────────────────────────────────

export function generateChallenge(
  recommendationId: string,
  strategyType: string,
  advisorRecommendation: RedTeamChallenge['advisorRecommendation'],
): RedTeamChallenge {
  const template = CHALLENGE_TEMPLATES[strategyType] || CHALLENGE_TEMPLATES['cost_reduction'];
  const challengeData = template();

  const verdict: RedTeamChallenge['challenge']['verdict'] =
    advisorRecommendation.confidence > 90 ? 'endorse' :
    advisorRecommendation.confidence > 70 ? 'partial_challenge' :
    'challenge';

  const challenge: RedTeamChallenge = {
    id: `RT-${Date.now()}-${nextId++}`,
    recommendationId,
    timestamp: new Date().toISOString(),
    advisorRecommendation,
    challenge: {
      verdict,
      confidenceInCritique: 75 + Math.floor(Math.random() * 20),
      summary: verdict === 'endorse'
        ? `The recommended strategy is sound. Minor risk blindspots identified but within acceptable tolerance.`
        : verdict === 'partial_challenge'
        ? `The strategy is reasonable but has ${challengeData.detailedArguments?.length || 1} risk blindspots that should be addressed.`
        : `The strategy has significant risk blindspots. Consider the alternative approach.`,
      detailedArguments: challengeData.detailedArguments || [],
      riskBlindSpots: challengeData.riskBlindSpots || [],
      missingAssumptions: challengeData.missingAssumptions || [],
      historicalPrecedent: challengeData.historicalPrecedent,
      alternativeStrategy: challengeData.alternativeStrategy,
    },
  };

  challenges.set(challenge.id, challenge);
  return challenge;
}

export function getChallenge(id: string): RedTeamChallenge | undefined {
  return challenges.get(id);
}

export function getChallengesForRecommendation(recommendationId: string): RedTeamChallenge[] {
  return Array.from(challenges.values())
    .filter(c => c.recommendationId === recommendationId)
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
}

export function getAllChallenges(): RedTeamChallenge[] {
  return Array.from(challenges.values())
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
}

export function resolveChallenge(
  challengeId: string,
  resolution: RedTeamChallenge['resolution'],
): RedTeamChallenge | undefined {
  const challenge = challenges.get(challengeId);
  if (!challenge) return undefined;

  challenge.resolution = {
    ...resolution!,
    resolvedAt: new Date().toISOString(),
  };

  return challenge;
}

export function getRedTeamStats(): {
  totalChallenges: number;
  verdictDistribution: Record<string, number>;
  resolutionDistribution: Record<string, number>;
  avgConfidenceInCritique: number;
  topArgumentTypes: { type: string; count: number }[];
} {
  const all = Array.from(challenges.values());

  const verdicts: Record<string, number> = {};
  all.forEach(c => {
    const v = c.challenge.verdict;
    verdicts[v] = (verdicts[v] || 0) + 1;
  });

  const resolutions: Record<string, number> = {};
  all.filter(c => c.resolution).forEach(c => {
    const r = c.resolution!.outcome;
    resolutions[r] = (resolutions[r] || 0) + 1;
  });

  const avgConf = all.length > 0
    ? all.reduce((s, c) => s + c.challenge.confidenceInCritique, 0) / all.length
    : 0;

  const types: Record<string, number> = {};
  all.forEach(c => {
    c.challenge.detailedArguments.forEach(a => {
      types[a.type] = (types[a.type] || 0) + 1;
    });
  });

  const topTypes = Object.entries(types)
    .map(([type, count]) => ({ type, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 5);

  return {
    totalChallenges: all.length,
    verdictDistribution: verdicts,
    resolutionDistribution: resolutions,
    avgConfidenceInCritique: Math.round(avgConf),
    topArgumentTypes: topTypes,
  };
}

// ── Singleton ────────────────────────────────────────────────────────

let _instance: ReturnType<typeof createRedTeam> | null = null;

function createRedTeam() {
  return {
    generate: generateChallenge,
    get: getChallenge,
    getForRecommendation: getChallengesForRecommendation,
    getAll: getAllChallenges,
    resolve: resolveChallenge,
    getStats: getRedTeamStats,
  };
}

export function getRedTeam() {
  if (!_instance) _instance = createRedTeam();
  return _instance;
}
