// ── Quantive Maturity Model ──────────────────────────────────────────
// Scores governments on 5 dimensions. This is a sales tool:
// it shows current state vs. benchmarks, creating urgency for adoption.

export interface MaturityDimension {
  id: string;
  name: string;
  weight: number; // percentage contribution to overall score
  score: number; // 0-100
  benchmark: number; // what top countries average
  status: 'leading' | 'on_track' | 'developing' | 'lagging';
  subDimensions: {
    name: string;
    score: number;
    detail: string;
    evidence: string[];
  }[];
  recommendations: string[];
}

export interface MaturityReport {
  timestamp: string;
  country: string;
  overallScore: number;
  overallBenchmark: number;
  overallGrade: 'A' | 'B' | 'C' | 'D' | 'F';
  percentile: number; // among all assessed countries
  dimensions: MaturityDimension[];
  trend: 'improving' | 'stable' | 'declining';
  improvementOpportunities: {
    dimension: string;
    currentScore: number;
    potentialScore: number;
    effort: 'low' | 'medium' | 'high';
    impact: 'low' | 'medium' | 'high';
    timeline: string;
  }[];
  comparisonWithPeers: {
    country: string;
    score: number;
    rank: number;
  }[];
}

// ── Default Dimensions ───────────────────────────────────────────────

function getDefaultDimensions(): MaturityDimension[] {
  return [
    {
      id: 'governance',
      name: 'Governance & Decision Process',
      weight: 25,
      score: 68,
      benchmark: 82,
      status: 'developing',
      subDimensions: [
        {
          name: 'Decision Documentation',
          score: 72,
          detail: 'Major decisions are documented but inconsistently.',
          evidence: ['60% of decisions have formal documentation', 'Approval chains exist but not consistently enforced'],
        },
        {
          name: 'Segregation of Duties',
          score: 58,
          detail: 'Basic controls exist but dual-approval is not universal.',
          evidence: ['Analyst-Manager separation exists', 'Large transactions sometimes lack second approver'],
        },
        {
          name: 'Audit Trail',
          score: 74,
          detail: 'System logs capture most actions but lack cryptographic integrity.',
          evidence: ['Application logs active', 'No immutable hash chain for tamper evidence'],
        },
        {
          name: 'Policy Compliance',
          score: 68,
          detail: 'Basic policies in place but not regularly reviewed.',
          evidence: ['Debt management policy exists (last updated 18 months ago)', 'No automated compliance checking'],
        },
      ],
      recommendations: [
        'Implement immutable audit trail with cryptographic signatures',
        'Enforce dual-approval for transactions above $50M',
        'Update debt management policy to current best practices',
        'Deploy automated compliance checking against IMF guidelines',
      ],
    },
    {
      id: 'risk_management',
      name: 'Risk Management',
      weight: 25,
      score: 72,
      benchmark: 85,
      status: 'developing',
      subDimensions: [
        {
          name: 'Risk Identification',
          score: 75,
          detail: 'Major risks are identified but not systematically tracked.',
          evidence: ['Interest rate risk is monitored', 'FX risk assessment is ad hoc', 'No systematic stress testing program'],
        },
        {
          name: 'Stress Testing',
          score: 55,
          detail: 'Basic scenario analysis performed quarterly.',
          evidence: ['3 standard scenarios run annually', 'No Monte Carlo analysis', 'Black swan scenarios not covered'],
        },
        {
          name: 'Risk Limits',
          score: 80,
          detail: 'Published risk limits exist and are mostly respected.',
          evidence: ['Duration limit: 5 years', 'FX exposure limit: 40%', 'Credit concentration limit: 25%'],
        },
        {
          name: 'Contingency Planning',
          score: 78,
          detail: 'Liquidity buffers exist but are not formally tested.',
          evidence: ['6-month liquidity reserve maintained', 'Emergency issuance procedures documented but untested'],
        },
      ],
      recommendations: [
        'Implement Monte Carlo scenario simulation (50,000+ scenarios)',
        'Add black swan scenario library with geopolitical stress tests',
        'Formally test emergency issuance procedures annually',
        'Deploy continuous risk monitoring instead of quarterly reviews',
      ],
    },
    {
      id: 'forecasting',
      name: 'Forecasting & Analytics',
      weight: 20,
      score: 58,
      benchmark: 78,
      status: 'developing',
      subDimensions: [
        {
          name: 'Yield Curve Forecasting',
          score: 62,
          detail: 'Uses forward rates as primary forecasting tool.',
          evidence: ['Forward curve used for 1-5 year horizon', 'No proprietary yield model', 'AI forecasting not deployed'],
        },
        {
          name: 'Assumption Tracking',
          score: 45,
          detail: 'Assumptions are documented but not tracked for accuracy.',
          evidence: ['Budget assumptions documented annually', 'No systematic accuracy tracking', 'No bias correction applied'],
        },
        {
          name: 'Model Validation',
          score: 55,
          detail: 'Basic model validation performed.',
          evidence: ['Annual model review by internal team', 'No independent validation', 'Backtesting is informal'],
        },
        {
          name: 'Data Integration',
          score: 70,
          detail: 'Market data feeds are active but manual reconciliation common.',
          evidence: ['Bloomberg terminal available', 'Manual data entry still common for some indicators', 'No automated data quality checks'],
        },
      ],
      recommendations: [
        'Deploy assumption tracking and accuracy scoring',
        'Implement automated data quality framework',
        'Conduct independent model validation',
        'Build scenario generation engine with Monte Carlo simulation',
      ],
    },
    {
      id: 'debt_management',
      name: 'Debt Management Operations',
      weight: 20,
      score: 75,
      benchmark: 88,
      status: 'on_track',
      subDimensions: [
        {
          name: 'Portfolio Visibility',
          score: 80,
          detail: 'Comprehensive debt inventory maintained.',
          evidence: ['All instruments tracked in system', 'Real-time position reporting', 'Currency breakdown available'],
        },
        {
          name: 'Issuance Execution',
          score: 78,
          detail: 'Experienced treasury operations team.',
          evidence: ['Successful track record of market access', 'Diversified investor base', 'Regular issuance calendar maintained'],
        },
        {
          name: 'Cost Optimization',
          score: 68,
          detail: 'Some optimization performed but not systematic.',
          evidence: ['Manual cost comparisons for new issuances', 'No systematic refinancing analysis', 'Opportunity cost tracking limited'],
        },
        {
          name: 'ESG Integration',
          score: 74,
          detail: 'Green bond framework established, ESG reporting initiated.',
          evidence: ['Green bond framework published', 'ESG reporting to investors', 'No integrated ESG scoring in portfolio analytics'],
        },
      ],
      recommendations: [
        'Deploy systematic optimization for all refinancing decisions',
        'Integrate ESG scoring into portfolio analytics',
        'Build automated opportunity detection for cost savings',
        'Implement real-time portfolio health monitoring',
      ],
    },
    {
      id: 'technology',
      name: 'Technology & Security',
      weight: 10,
      score: 62,
      benchmark: 80,
      status: 'developing',
      subDimensions: [
        {
          name: 'Cybersecurity',
          score: 65,
          detail: 'Basic security controls in place.',
          evidence: ['MFA enforced for system access', 'Annual penetration testing', 'No zero-trust architecture', 'Air-gapped backup capability not tested'],
        },
        {
          name: 'System Resilience',
          score: 60,
          detail: 'Disaster recovery plan exists but is partially tested.',
          evidence: ['DR plan documented', 'Annual DR test (tabletop only)', 'RPO: 4 hours, RTO: 24 hours (target: 1 hour / 4 hours)'],
        },
        {
          name: 'Automation',
          score: 55,
          detail: 'Many processes still manual.',
          evidence: ['Basic API integrations active', 'Manual report generation common', 'No automated compliance checking'],
        },
        {
          name: 'Audit Technology',
          score: 68,
          detail: 'Audit logs exist but lack immutability.',
          evidence: ['Application logs captured', 'No cryptographic audit trail', 'No real-time fraud detection'],
        },
      ],
      recommendations: [
        'Deploy immutable audit trail with SHA-256 hash chain',
        'Implement zero-trust architecture for all system access',
        'Achieve RPO < 15 minutes and RTO < 4 hours',
        'Deploy real-time anomaly detection for financial transactions',
      ],
    },
  ];
}

// ── In-Memory Store ──────────────────────────────────────────────────

let currentReport: MaturityReport | null = null;

// ── Public API ───────────────────────────────────────────────────────

export function generateMaturityReport(country: string = 'Current Assessment'): MaturityReport {
  const dimensions = getDefaultDimensions();

  const totalWeight = dimensions.reduce((s, d) => s + d.weight, 0);
  const overallScore = Math.round(
    dimensions.reduce((s, d) => s + d.score * d.weight / totalWeight, 0)
  );
  const overallBenchmark = Math.round(
    dimensions.reduce((s, d) => s + d.benchmark * d.weight / totalWeight, 0)
  );

  const grade = overallScore >= 90 ? 'A' : overallScore >= 80 ? 'B' : overallScore >= 70 ? 'C' : overallScore >= 60 ? 'D' : 'F';
  const percentile = Math.round(overallScore * 0.95 + Math.random() * 5); // Simplified

  const improvementOpportunities = dimensions
    .filter(d => d.score < d.benchmark)
    .map(d => ({
      dimension: d.name,
      currentScore: d.score,
      potentialScore: Math.min(d.benchmark + 5, 100),
      effort: d.benchmark - d.score > 20 ? 'high' as const : d.benchmark - d.score > 10 ? 'medium' as const : 'low' as const,
      impact: d.weight >= 25 ? 'high' as const : d.weight >= 20 ? 'medium' as const : 'low' as const,
      timeline: d.benchmark - d.score > 20 ? '6-12 months' : d.benchmark - d.score > 10 ? '3-6 months' : '1-3 months',
    }))
    .sort((a, b) => (b.impact === 'high' ? 1 : 0) - (a.impact === 'high' ? 1 : 0));

  const comparisonWithPeers = [
    { country: 'Chile', score: 88, rank: 1 },
    { country: 'South Korea', score: 85, rank: 2 },
    { country: 'Czech Republic', score: 82, rank: 3 },
    { country: 'Poland', score: 79, rank: 4 },
    { country: 'Peru', score: 76, rank: 5 },
    { country: 'Mexico', score: 74, rank: 6 },
    { country: 'Colombia', score: 71, rank: 7 },
    { country: country === 'Current Assessment' ? 'Your Country' : country, score: overallScore, rank: 8 },
  ].sort((a, b) => b.score - a.score)
    .map((c, i) => ({ ...c, rank: i + 1 }));

  currentReport = {
    timestamp: new Date().toISOString(),
    country,
    overallScore,
    overallBenchmark,
    overallGrade: grade,
    percentile,
    dimensions,
    trend: 'stable',
    improvementOpportunities,
    comparisonWithPeers,
  };

  return currentReport;
}

export function getCurrentReport(): MaturityReport | null {
  return currentReport;
}

export function getMaturityDimensions(): MaturityDimension[] {
  return currentReport?.dimensions || getDefaultDimensions();
}

// ── Singleton ────────────────────────────────────────────────────────

let _instance: ReturnType<typeof createMaturityModel> | null = null;

function createMaturityModel() {
  return {
    generateReport: generateMaturityReport,
    getCurrentReport,
    getDimensions: getMaturityDimensions,
  };
}

export function getMaturityModel() {
  if (!_instance) _instance = createMaturityModel();
  return _instance;
}
