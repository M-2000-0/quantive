import { useState, useEffect, useCallback } from 'react';
import { api } from '../api';
import AppShell from '../components/layout/AppShell';
import Card, { CardHeader } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import { formatCurrency, formatPercent } from '../utils';
import type { Portfolio, InvestmentScenario, RiskScore, VaRResult } from '../types';
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell,
} from 'recharts';

const INVESTMENT_AMOUNTS = [1_000_000, 5_000_000, 10_000_000, 50_000_000, 100_000_000, 1_000_000_000];

function ScenarioCard({ scenario, investment }: { scenario: InvestmentScenario; investment: number }) {
  const isPositive = scenario.return_pct > 0;
  const isNegative = scenario.return_pct < 0;

  const scenarioStyles: Record<string, { bg: string; border: string; icon: string; badgeVariant: 'success' | 'danger' | 'warning' | 'info' }> = {
    'Best Case': { bg: 'bg-emerald-50', border: 'border-emerald-200', icon: '🚀', badgeVariant: 'success' },
    'Strong Upside': { bg: 'bg-emerald-50', border: 'border-emerald-200', icon: '📈', badgeVariant: 'success' },
    'Expected Return': { bg: 'bg-blue-50', border: 'border-blue-200', icon: '📊', badgeVariant: 'info' },
    'Moderate Upside': { bg: 'bg-blue-50', border: 'border-blue-200', icon: '📈', badgeVariant: 'info' },
    'Moderate Downside': { bg: 'bg-amber-50', border: 'border-amber-200', icon: '⚠️', badgeVariant: 'warning' },
    'Worst Case': { bg: 'bg-red-50', border: 'border-red-200', icon: '🔴', badgeVariant: 'danger' },
    'Severe Downside': { bg: 'bg-red-50', border: 'border-red-200', icon: '💀', badgeVariant: 'danger' },
    'Tail Risk': { bg: 'bg-red-50', border: 'border-red-200', icon: '💀', badgeVariant: 'danger' },
  };

  const style = scenarioStyles[scenario.scenario_name] || { bg: 'bg-slate-50', border: 'border-slate-200', icon: '📋', badgeVariant: 'info' as const };

  return (
    <div className={`${style.bg} ${style.border} border rounded-xl p-5 transition-all hover:shadow-md`}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{style.icon}</span>
          <h3 className="text-base font-bold text-slate-900">{scenario.scenario_name}</h3>
        </div>
        <Badge variant={style.badgeVariant}>{(scenario.probability * 100).toFixed(0)}% chance</Badge>
      </div>

      {/* Investment → Return */}
      <div className="bg-white rounded-lg p-4 mb-3">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-slate-500 mb-0.5">You Invest</p>
            <p className="text-xl font-bold text-slate-900 tabular-nums">{formatCurrency(investment)}</p>
          </div>
          <span className="text-2xl text-slate-300 mx-4">→</span>
          <div className="text-right">
            <p className="text-xs text-slate-500 mb-0.5">You Get Back</p>
            <p className={`text-xl font-bold tabular-nums ${isPositive ? 'text-emerald-700' : isNegative ? 'text-red-700' : 'text-slate-900'}`}>
              {formatCurrency(scenario.return_amount)}
            </p>
          </div>
        </div>

        <div className="mt-2 flex items-center justify-center">
          <span className={`text-sm font-semibold px-3 py-1 rounded-full ${
            isPositive ? 'bg-emerald-100 text-emerald-700' : isNegative ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-700'
          }`}>
            {isPositive ? '+' : ''}{scenario.return_pct.toFixed(1)}% return
          </span>
        </div>
      </div>

      <p className="text-xs text-slate-600 leading-relaxed">{scenario.description}</p>
    </div>
  );
}

function RiskScoreRadar({ score }: { score: RiskScore }) {
  const radarData = Object.entries(score.components).map(([key, val]) => ({
    subject: key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
    score: val.score,
    fullMark: 10,
  }));

  return (
    <Card>
      <CardHeader title="Risk Score Analysis" subtitle={`Overall Score: ${score.score.toFixed(1)}/10 — ${score.label}`} />
      <div className="px-4 pb-2 flex justify-center">
        <ResponsiveContainer width="100%" height={300}>
          <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
            <PolarGrid stroke="#e2e8f0" />
            <PolarAngleAxis dataKey="subject" tick={{ fontSize: 10, fill: '#64748b' }} />
            <PolarRadiusAxis angle={30} domain={[0, 10]} tick={{ fontSize: 10, fill: '#94a3b8' }} />
            <Radar name="Risk Score" dataKey="score" stroke="#ef4444" fill="#ef4444" fillOpacity={0.15} strokeWidth={2} />
          </RadarChart>
        </ResponsiveContainer>
      </div>
      {/* Score Badge */}
      <div className="px-6 pb-4 flex items-center gap-3">
        <div className="w-12 h-12 rounded-full flex items-center justify-center text-white text-lg font-bold"
          style={{ backgroundColor: score.color }}>
          {score.score.toFixed(0)}
        </div>
        <div>
          <p className="text-sm font-bold text-slate-900">{score.label}</p>
          <p className="text-xs text-slate-500">Risk Score (1-10 scale)</p>
        </div>
      </div>
      {/* Components */}
      <div className="px-6 pb-4 space-y-2">
        {Object.entries(score.components).map(([key, val]) => (
          <div key={key} className="flex items-center gap-3">
            <span className="text-xs text-slate-500 w-32 truncate">{key.replace(/_/g, ' ')}</span>
            <div className="flex-1 bg-slate-100 rounded-full h-2">
              <div
                className="rounded-full h-2 transition-all"
                style={{
                  width: `${(val.score / 10) * 100}%`,
                  backgroundColor: val.score <= 3 ? '#10b981' : val.score <= 6 ? '#f59e0b' : '#ef4444',
                }}
              />
            </div>
            <span className="text-xs font-semibold text-slate-700 w-8 text-right tabular-nums">{val.score.toFixed(1)}</span>
          </div>
        ))}
      </div>
      {/* Recommendations */}
      {score.recommendations.length > 0 && (
        <div className="px-6 pb-6">
          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Recommendations</h4>
          <ul className="space-y-1.5">
            {score.recommendations.map((rec, i) => (
              <li key={i} className="text-xs text-slate-600 flex items-start gap-2">
                <span className="text-blue-500 mt-0.5">•</span>
                {rec}
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}

function VaRCard({ varResults }: { varResults: VaRResult[] }) {
  return (
    <Card>
      <CardHeader title="Value-at-Risk (VaR) Analysis" subtitle="Maximum expected loss at different confidence levels" />
      <div className="px-6 pb-4">
        {varResults.length === 0 ? (
          <p className="text-sm text-slate-400">No VaR data available. Add instruments to your portfolio.</p>
        ) : (
          <div className="space-y-4">
            {varResults.map((v, i) => (
              <div key={i} className="bg-slate-50 rounded-lg p-4 border border-slate-100">
                <div className="flex items-center justify-between mb-3">
                  <Badge variant={v.confidence >= 0.99 ? 'danger' : v.confidence >= 0.95 ? 'warning' : 'info'}>
                    {(v.confidence * 100).toFixed(0)}% Confidence
                  </Badge>
                  <span className="text-xs text-slate-400">{v.horizon_days}-day horizon</span>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs text-slate-500 mb-0.5">VaR (Value-at-Risk)</p>
                    <p className="text-lg font-bold text-red-700 tabular-nums">{formatCurrency(v.var_amount)}</p>
                    <p className="text-xs text-slate-400">{formatPercent(v.var_pct, 2)} of portfolio</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 mb-0.5">CVaR (Expected Shortfall)</p>
                    <p className="text-lg font-bold text-red-600 tabular-nums">{formatCurrency(v.cvar_amount)}</p>
                    <p className="text-xs text-slate-400">{formatPercent(v.cvar_pct, 2)} of portfolio</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}

function ScenarioBarChart({ scenarios }: { scenarios: InvestmentScenario[] }) {
  const chartData = scenarios.map(s => ({
    name: s.scenario_name,
    returnPct: s.return_pct,
    probability: s.probability * 100,
  }));

  return (
    <Card>
      <CardHeader title="Scenario Comparison" subtitle="Expected return (%) by scenario" />
      <div className="px-4 pb-4">
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#64748b' }} />
            <YAxis tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={(v: number) => `${v}%`} />
            <Tooltip
              contentStyle={{ borderRadius: 8, border: '1px solid #e2e8f0' }}
              formatter={(value, name) => [name === 'returnPct' ? `${Number(value).toFixed(1)}%` : `${Number(value).toFixed(0)}%`, String(name) === 'returnPct' ? 'Return' : 'Probability']}
            />
            <Bar dataKey="returnPct" radius={[4, 4, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.returnPct > 0 ? '#10b981' : entry.returnPct < 0 ? '#ef4444' : '#94a3b8'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}

export default function RiskDashboardPage() {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [investmentAmount, setInvestmentAmount] = useState(1_000_000);
  const [loading, setLoading] = useState(true);
  const [scenarios, setScenarios] = useState<InvestmentScenario[]>([]);
  const [riskScore, setRiskScore] = useState<RiskScore | null>(null);
  const [varResults, setVarResults] = useState<VaRResult[]>([]);
  const [loadingRisk, setLoadingRisk] = useState(false);

  useEffect(() => {
    api.portfolios.list().then(p => {
      setPortfolios(p.data || []);
      if (p.data?.length) setSelectedId(p.data[0].id);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const fetchRiskData = useCallback(async (portfolioId: string) => {
    setLoadingRisk(true);
    try {
      const [sc, score, varData] = await Promise.all([
        api.portfolios.investmentScenarios(portfolioId, investmentAmount).catch(() => ({ scenarios: [] as InvestmentScenario[] })),
        api.portfolios.riskScore(portfolioId).catch(() => null),
        api.portfolios.var(portfolioId, 0.95).catch(() => [] as VaRResult[]),
      ]);
      setScenarios(sc.scenarios || []);
      setRiskScore(score);
      setVarResults(varData || []);
    } catch {
      // silently fail
    } finally {
      setLoadingRisk(false);
    }
  }, [investmentAmount]);

  useEffect(() => {
    if (selectedId) fetchRiskData(selectedId);
  }, [selectedId, fetchRiskData]);

  if (loading) {
    return (
      <AppShell>
        <LoadingSpinner message="Loading portfolios..." />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="px-8 py-6 max-w-[1440px] mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Risk Dashboard</h1>
            <p className="text-sm text-slate-500 mt-0.5">
              Investment scenarios, risk scores, and value-at-risk analysis
            </p>
          </div>
        </div>

        {/* Portfolio Selector + Investment Amount */}
        <div className="flex flex-wrap items-center gap-4 mb-6 bg-white border border-slate-200 rounded-lg p-4">
          <div className="flex-1 min-w-[200px]">
            <label className="text-xs font-medium text-slate-500 block mb-1">Select Portfolio</label>
            <select
              value={selectedId || ''}
              onChange={e => setSelectedId(e.target.value)}
              className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {portfolios.map(p => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>
          <div className="flex-1 min-w-[200px]">
            <label className="text-xs font-medium text-slate-500 block mb-1">Investment Amount</label>
            <div className="flex gap-1">
              {INVESTMENT_AMOUNTS.map(amt => (
                <button
                  key={amt}
                  onClick={() => setInvestmentAmount(amt)}
                  className={`px-3 py-2 text-xs font-medium rounded-md transition-all ${
                    investmentAmount === amt
                      ? 'bg-blue-600 text-white'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {amt >= 1_000_000_000 ? `$${amt / 1_000_000_000}B` : `$${amt / 1_000_000}M`}
                </button>
              ))}
            </div>
          </div>
        </div>

        {loadingRisk ? (
          <LoadingSpinner message="Analyzing risk..." />
        ) : (
          <>
            {/* Investment Scenarios — The "$1M → $X Back" Cards */}
            {scenarios.length > 0 && (
              <div className="mb-6">
                <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
                  💰 What Happens to Your ${investmentAmount >= 1_000_000_000 ? `${investmentAmount / 1_000_000_000}B` : `${investmentAmount / 1_000_000}M`}?
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {scenarios.map((s, i) => (
                    <ScenarioCard key={i} scenario={s} investment={investmentAmount} />
                  ))}
                </div>
              </div>
            )}

            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
              {scenarios.length > 0 && <ScenarioBarChart scenarios={scenarios} />}
              {riskScore && <RiskScoreRadar score={riskScore} />}
            </div>

            {/* VaR Analysis */}
            {varResults.length > 0 && (
              <div className="mb-6">
                <VaRCard varResults={varResults} />
              </div>
            )}

            {/* Empty States */}
            {scenarios.length === 0 && !riskScore && varResults.length === 0 && (
              <Card>
                <div className="p-12 text-center">
                  <p className="text-4xl mb-4">📊</p>
                  <h3 className="text-lg font-semibold text-slate-900 mb-2">No Risk Data Available</h3>
                  <p className="text-sm text-slate-500 max-w-md mx-auto">
                    Select a portfolio above to view investment scenarios, risk scores, and VaR analysis.
                    Make sure the portfolio has instruments added.
                  </p>
                </div>
              </Card>
            )}

            {/* How It Works */}
            <Card>
              <CardHeader title="How Risk Analysis Works" subtitle="Understanding the numbers" />
              <div className="px-6 pb-6 grid grid-cols-1 sm:grid-cols-3 gap-6">
                <div>
                  <h4 className="text-sm font-semibold text-slate-900 mb-1">📈 Investment Scenarios</h4>
                  <p className="text-xs text-slate-500 leading-relaxed">
                    Based on current interest rates, historical volatility, and your portfolio composition,
                    we model different market outcomes and show you exactly what your money could return —
                    from best case to worst case — with probabilities for each.
                  </p>
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-slate-900 mb-1">🎯 Risk Score (1-10)</h4>
                  <p className="text-xs text-slate-500 leading-relaxed">
                    A composite score based on maturity risk, coupon risk, spread risk, floating rate exposure,
                    currency risk, and diversification. Lower is safer. The radar chart shows how each factor contributes.
                  </p>
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-slate-900 mb-1">🛡️ Value-at-Risk (VaR)</h4>
                  <p className="text-xs text-slate-500 leading-relaxed">
                    VaR tells you the maximum loss you could expect with X% confidence over a given time horizon.
                    CVaR (Expected Shortfall) shows the average loss if VaR is breached — the "tail risk" measure.
                  </p>
                </div>
              </div>
            </Card>
          </>
        )}
      </div>
    </AppShell>
  );
}
