import { useState, useEffect } from 'react';
import { api } from '../api';

interface FactorImportance {
  factor: string;
  weight: number;
  direction: string;
  impact: string;
  score: number;
  confidence: number;
}

interface DecisionTrail {
  step: number;
  category: string;
  reasoning: string;
  data_points: Record<string, string>;
  confidence: number;
}

interface Counterfactual {
  condition: string;
  current_outcome: string;
  alternative_outcome: string;
  impact: string;
}

interface ExplainabilityReport {
  recommendation_id: string;
  country_code: string;
  generated_at: string;
  headline: string;
  plain_english_summary: string;
  factor_importance: FactorImportance[];
  decision_trail: DecisionTrail[];
  counterfactuals: Counterfactual[];
  confidence: {
    overall: number;
    uncertainty_sources: string[];
  };
  methodology: string;
  data_sources: string[];
  assumptions: string[];
  limitations: string[];
}

const CATEGORY_ICONS: Record<string, string> = {
  data: '📊',
  analysis: '🔬',
  model: '🤖',
  constraint: '🔒',
  recommendation: '✅',
};

const CATEGORY_COLORS: Record<string, string> = {
  data: '#3b82f6',
  analysis: '#a855f7',
  model: '#22c55e',
  constraint: '#eab308',
  recommendation: '#ef4444',
};

const DIRECTION_COLORS: Record<string, string> = {
  positive: '#22c55e',
  negative: '#ef4444',
  neutral: '#6b7280',
};

export default function ExplainabilityPage() {
  const [report, setReport] = useState<ExplainabilityReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [countryCode, setCountryCode] = useState('US');
  const [methodology, setMethodology] = useState<Record<string, unknown> | null>(null);
  const [activeTab, setActiveTab] = useState<'explain' | 'methodology'>('explain');

  // Load methodology on mount
  useEffect(() => {
    api.explain.methodology()
      .then((res: { success: boolean; data: Record<string, unknown> }) => setMethodology(res.data))
      .catch(() => {});
  }, []);

  const generateExplanation = async () => {
    setLoading(true);
    setError('');
    try {
      // Use a demo strategy for explanation
      const demoStrategy = {
        name: 'Balanced Cost-Risk Strategy',
        metrics: {
          expected_cost: 45_000_000,
          refinancing_risk: 0.18,
          interest_rate_risk: 0.22,
          currency_risk: 0.12,
        },
      };
      const demoPortfolio = {
        instruments: [
          { principal_outstanding: 5_000_000_000, coupon_rate: 3.5, currency: 'USD', instrument_type: 'treasury_bond', maturity_date: '2030-06-15' },
          { principal_outstanding: 3_000_000_000, coupon_rate: 2.8, currency: 'EUR', instrument_type: 'eurobond', maturity_date: '2032-03-01' },
          { principal_outstanding: 2_000_000_000, coupon_rate: 4.2, currency: 'USD', instrument_type: 'floating_rate_note', maturity_date: '2028-09-15' },
          { principal_outstanding: 1_500_000_000, coupon_rate: 5.1, currency: 'GBP', instrument_type: 'treasury_bond', maturity_date: '2035-12-01' },
          { principal_outstanding: 1_000_000_000, coupon_rate: 3.0, currency: 'JPY', instrument_type: 'samurai_bond', maturity_date: '2029-06-15' },
          { principal_outstanding: 500_000_000, coupon_rate: 4.5, currency: 'BRL', instrument_type: 'eurobond', maturity_date: '2027-04-01' },
        ],
      };
      const res = await api.explain.strategy({
        strategy: demoStrategy,
        portfolio_data: demoPortfolio,
        country_code: countryCode,
      }) as unknown as { success: boolean; data: ExplainabilityReport };
      setReport(res.data);
    } catch (err) {
      setError('Failed to generate explanation');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    generateExplanation();
  }, [countryCode]);

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">Explainability Engine</h1>
      <p className="text-gray-400 mb-6">
        Understand WHY every recommendation was made. Full decision audit trail for government procurement.
      </p>

      {/* Controls */}
      <div className="flex items-center gap-4 mb-6">
        <select
          value={countryCode}
          onChange={(e) => setCountryCode(e.target.value)}
          className="bg-gray-800 border border-gray-600 rounded-lg px-4 py-2 text-white"
        >
          <option value="US">United States</option>
          <option value="GB">United Kingdom</option>
          <option value="JP">Japan</option>
          <option value="DE">Germany</option>
          <option value="FR">France</option>
          <option value="IN">India</option>
          <option value="BR">Brazil</option>
          <option value="ZA">South Africa</option>
        </select>
        <div className="flex gap-1 bg-gray-800 rounded-lg p-1">
          <button
            onClick={() => setActiveTab('explain')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === 'explain' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'
            }`}
          >
            Explanation
          </button>
          <button
            onClick={() => setActiveTab('methodology')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === 'methodology' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'
            }`}
          >
            Methodology
          </button>
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <span className="ml-3 text-gray-400">Generating explanation...</span>
        </div>
      )}

      {error && (
        <div className="bg-red-900/30 border border-red-500 rounded-lg p-4 mb-6 text-red-300">{error}</div>
      )}

      {/* Explanation Tab */}
      {activeTab === 'explain' && report && !loading && (
        <div className="space-y-6">
          {/* Headline */}
          <div className="bg-gray-800 rounded-xl p-6 border-l-4 border-blue-500">
            <h2 className="text-lg font-semibold text-blue-400 mb-2">Headline</h2>
            <p className="text-white text-lg">{report.headline}</p>
          </div>

          {/* Plain English Summary */}
          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-3">Plain English Summary</h2>
            <p className="text-gray-300 leading-relaxed">{report.plain_english_summary}</p>
          </div>

          {/* Confidence Meter */}
          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Overall Confidence</h2>
            <div className="relative h-6 bg-gray-700 rounded-full overflow-hidden">
              <div
                className="absolute inset-y-0 left-0 rounded-full transition-all duration-1000"
                style={{
                  width: `${report.confidence.overall * 100}%`,
                  backgroundColor: report.confidence.overall > 0.8 ? '#22c55e' : report.confidence.overall > 0.6 ? '#eab308' : '#ef4444',
                }}
              />
              <div className="absolute inset-0 flex items-center justify-center text-sm font-medium text-white">
                {(report.confidence.overall * 100).toFixed(0)}%
              </div>
            </div>
            <div className="mt-3">
              <h3 className="text-sm font-medium text-gray-400 mb-1">Uncertainty Sources</h3>
              <ul className="space-y-1">
                {report.confidence.uncertainty_sources.map((src, i) => (
                  <li key={i} className="text-sm text-gray-400 flex items-start gap-2">
                    <span className="text-yellow-400 mt-0.5">⚠</span>
                    {src}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Factor Importance */}
          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Factor Importance Ranking</h2>
            <div className="space-y-3">
              {report.factor_importance.map((f, i) => (
                <div key={i} className="bg-gray-700/50 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <span className="text-lg font-bold text-gray-500">#{i + 1}</span>
                      <span className="font-medium text-white">{f.factor}</span>
                      <span
                        className="text-xs px-2 py-0.5 rounded-full"
                        style={{
                          backgroundColor: `${DIRECTION_COLORS[f.direction]}20`,
                          color: DIRECTION_COLORS[f.direction],
                        }}
                      >
                        {f.direction}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-sm">
                      <span className="text-gray-400">Weight: {(f.weight * 100).toFixed(0)}%</span>
                      <span className="text-gray-400">Confidence: {(f.confidence * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                  <p className="text-sm text-gray-300 mb-2">{f.impact}</p>
                  <div className="h-2 bg-gray-600 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-700"
                      style={{
                        width: `${f.score * 10}%`,
                        backgroundColor: f.direction === 'positive' ? '#22c55e' : f.direction === 'negative' ? '#ef4444' : '#6b7280',
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Decision Trail */}
          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Decision Trail (Step-by-Step)</h2>
            <div className="relative">
              {/* Timeline line */}
              <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-gray-700"></div>
              <div className="space-y-6">
                {report.decision_trail.map((step) => (
                  <div key={step.step} className="relative flex gap-4">
                    {/* Step number */}
                    <div
                      className="w-12 h-12 rounded-full flex items-center justify-center text-white font-bold text-sm z-10 flex-shrink-0"
                      style={{ backgroundColor: CATEGORY_COLORS[step.category] || '#6b7280' }}
                    >
                      {CATEGORY_ICONS[step.category] || step.step}
                    </div>
                    {/* Content */}
                    <div className="bg-gray-700/50 rounded-lg p-4 flex-1">
                      <div className="flex items-center justify-between mb-2">
                        <span
                          className="text-xs px-2 py-0.5 rounded-full font-medium"
                          style={{
                            backgroundColor: `${CATEGORY_COLORS[step.category]}20`,
                            color: CATEGORY_COLORS[step.category],
                          }}
                        >
                          {step.category.toUpperCase()}
                        </span>
                        <span className="text-xs text-gray-400">
                          Confidence: {(step.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                      <p className="text-gray-200 mb-2">{step.reasoning}</p>
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(step.data_points).map(([key, val]) => (
                          <span key={key} className="text-xs bg-gray-600/50 rounded px-2 py-1 text-gray-300">
                            {key.replace(/_/g, ' ')}: <span className="text-white font-medium">{val}</span>
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Counterfactuals */}
          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Counterfactual Analysis</h2>
            <p className="text-sm text-gray-400 mb-4">What would change if conditions were different</p>
            <div className="space-y-4">
              {report.counterfactuals.map((cf, i) => (
                <div key={i} className="bg-gray-700/50 rounded-lg p-4 border-l-4 border-purple-500">
                  <div className="font-medium text-purple-400 mb-2">{cf.condition}</div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                    <div>
                      <div className="text-gray-400 mb-1">Current Outcome</div>
                      <div className="text-white">{cf.current_outcome}</div>
                    </div>
                    <div>
                      <div className="text-gray-400 mb-1">Alternative Outcome</div>
                      <div className="text-gray-200">{cf.alternative_outcome}</div>
                    </div>
                  </div>
                  <div className="mt-2 text-sm text-yellow-400 font-medium">
                    Impact: {cf.impact}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Methodology, Data, Assumptions */}
          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Documentation</h2>
            <div className="space-y-4">
              <div>
                <h3 className="text-sm font-medium text-gray-400 mb-1">Methodology</h3>
                <p className="text-sm text-gray-300">{report.methodology}</p>
              </div>
              <div>
                <h3 className="text-sm font-medium text-gray-400 mb-1">Data Sources</h3>
                <ul className="space-y-1">
                  {report.data_sources.map((ds, i) => (
                    <li key={i} className="text-sm text-gray-300 flex items-center gap-2">
                      <span className="text-blue-400">•</span> {ds}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h3 className="text-sm font-medium text-gray-400 mb-1">Assumptions</h3>
                <ul className="space-y-1">
                  {report.assumptions.map((a, i) => (
                    <li key={i} className="text-sm text-gray-300 flex items-center gap-2">
                      <span className="text-yellow-400">⚠</span> {a}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h3 className="text-sm font-medium text-gray-400 mb-1">Limitations</h3>
                <ul className="space-y-1">
                  {report.limitations.map((l, i) => (
                    <li key={i} className="text-sm text-gray-300 flex items-center gap-2">
                      <span className="text-red-400">✗</span> {l}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Methodology Tab */}
      {activeTab === 'methodology' && methodology && (
        <div className="space-y-6">
          {/* Optimization Solvers */}
          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">
              {(methodology.optimization as Record<string, unknown>)?.title as string}
            </h2>
            <p className="text-gray-300 mb-4">
              {(methodology.optimization as Record<string, unknown>)?.description as string}
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {((methodology.optimization as Record<string, unknown>)?.solvers as Array<Record<string, string>>)?.map(
                (solver, i) => (
                  <div key={i} className="bg-gray-700/50 rounded-lg p-4">
                    <h3 className="font-medium text-white mb-2">{solver.name}</h3>
                    <div className="text-xs text-gray-400 space-y-1">
                      <div>Engine: <span className="text-gray-300">{solver.engine}</span></div>
                      <div>Strength: <span className="text-green-400">{solver.strength}</span></div>
                      <div>Weakness: <span className="text-red-400">{solver.weakness}</span></div>
                      <div>Use: <span className="text-blue-400">{solver.use_case}</span></div>
                    </div>
                  </div>
                ),
              )}
            </div>
          </div>

          {/* Scenario Generation */}
          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">
              {(methodology.scenario_generation as Record<string, unknown>)?.title as string}
            </h2>
            <p className="text-gray-300 mb-4">
              {(methodology.scenario_generation as Record<string, unknown>)?.description as string}
            </p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-gray-700/50 rounded-lg p-3 text-center">
                <div className="text-lg font-bold text-blue-400">
                  {(methodology.scenario_generation as Record<string, unknown>)?.model as string}
                </div>
                <div className="text-xs text-gray-400 mt-1">Model</div>
              </div>
              <div className="bg-gray-700/50 rounded-lg p-3 text-center">
                <div className="text-lg font-bold text-green-400">
                  {(methodology.scenario_generation as Record<string, unknown>)?.calibration as string}
                </div>
                <div className="text-xs text-gray-400 mt-1">Calibration</div>
              </div>
              <div className="bg-gray-700/50 rounded-lg p-3 text-center">
                <div className="text-lg font-bold text-yellow-400">
                  {((methodology.scenario_generation as Record<string, unknown>)?.factors as string[])?.length || 0} factors
                </div>
                <div className="text-xs text-gray-400 mt-1">Shock Factors</div>
              </div>
              <div className="bg-gray-700/50 rounded-lg p-3 text-center">
                <div className="text-lg font-bold text-purple-400">
                  {((methodology.scenario_generation as Record<string, unknown>)?.factors as string[])?.join(', ')}
                </div>
                <div className="text-xs text-gray-400 mt-1">Factors</div>
              </div>
            </div>
          </div>

          {/* Data Sources */}
          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Data Sources</h2>
            <div className="space-y-2">
              {((methodology.data_sources as string[]) || []).map((ds, i) => (
                <div key={i} className="flex items-center gap-3 bg-gray-700/50 rounded-lg p-3">
                  <span className="text-blue-400 text-lg">📡</span>
                  <span className="text-gray-200">{ds}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
