import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, Area, AreaChart, Legend } from 'recharts';
import { api } from '../api';

interface MaturityBucket {
  year: number;
  total_principal: number;
  total_interest: number;
  count: number;
  pct_of_total: number;
  cumulative_pct: number;
}

interface CashFlowYear {
  year: number;
  principal_repayments: number;
  interest_payments: number;
  total_outflows: number;
  refinancing_ratio: number;
  instruments_maturing: number;
}

interface MaturityData {
  total_debt: number;
  horizon_years: number;
  current_year: number;
  buckets: MaturityBucket[];
  maturity_walls: Array<{ year: number; amount: number; pct: number }>;
  smoothness_score: number;
  average_years_to_maturity: number;
}

interface CashFlowData {
  total_debt: number;
  projections: CashFlowYear[];
  summary: {
    total_interest_over_horizon: number;
    total_principal_repayments: number;
    total_outflows: number;
    refinancing_risk_score: number;
    near_term_pct: number;
    debt_service_coverage_ratio: number | null;
  };
}

interface Recommendation {
  type: string;
  severity: string;
  year?: number;
  message: string;
  action: string;
}

export default function MaturityLadderPage() {
  const [portfolios, setPortfolios] = useState<Array<{ id: string; name: string }>>([]);
  const [selectedPortfolio, setSelectedPortfolio] = useState('');
  const [maturity, setMaturity] = useState<MaturityData | null>(null);
  const [cashflow, setCashflow] = useState<CashFlowData | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [horizon, setHorizon] = useState(20);
  const [annualBudget, setAnnualBudget] = useState(0);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.portfolios.list().then((res: unknown) => {
      const data = res as { data?: Array<{ id: string; name: string }> };
      setPortfolios(data?.data || []);
    });
  }, []);

  useEffect(() => {
    if (!selectedPortfolio) return;
    setLoading(true);
    Promise.all([
      api.getMaturityLadder(selectedPortfolio, horizon),
      api.getCashFlowProjection(selectedPortfolio, horizon, annualBudget),
      api.getRefinancingRecommendations(selectedPortfolio),
    ])
      .then(([ladder, cf, recs]) => {
        setMaturity(ladder as unknown as MaturityData);
        setCashflow(cf as unknown as CashFlowData);
        setRecommendations((recs as { recommendations: Recommendation[] }).recommendations || []);
      })
      .finally(() => setLoading(false));
  }, [selectedPortfolio, horizon, annualBudget]);

  const wallYears = new Set(maturity?.maturity_walls.map(w => w.year) || []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Debt Maturity Ladder & Cash Flow</h1>
          <p className="text-gray-500 mt-1">Visualize when debt matures and project future cash flows</p>
        </div>
        <div className="flex items-center gap-4">
          <div>
            <label className="block text-sm text-gray-500">Horizon</label>
            <select value={horizon} onChange={e => setHorizon(Number(e.target.value))} className="border rounded px-2 py-1 text-sm">
              {[10, 15, 20, 30].map(y => <option key={y} value={y}>{y} years</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm text-gray-500">Annual Budget ($)</label>
            <input type="number" value={annualBudget} onChange={e => setAnnualBudget(Number(e.target.value))} className="border rounded px-2 py-1 text-sm w-36" placeholder="0" />
          </div>
          <div>
            <label className="block text-sm text-gray-500">Portfolio</label>
            <select value={selectedPortfolio} onChange={e => setSelectedPortfolio(e.target.value)} className="border rounded px-2 py-1 text-sm">
              <option value="">Select portfolio...</option>
              {portfolios.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>
        </div>
      </div>

      {loading && <div className="text-center py-8 text-gray-500">Loading analysis...</div>}

      {maturity && cashflow && !loading && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <Card title="Total Debt" value={`$${(maturity.total_debt / 1e9).toFixed(1)}B`} color="blue" />
            <Card title="Avg Maturity" value={`${maturity.average_years_to_maturity} yrs`} color={maturity.average_years_to_maturity > 7 ? 'green' : maturity.average_years_to_maturity > 4 ? 'yellow' : 'red'} />
            <Card title="Smoothness" value={`${maturity.smoothness_score}/100`} color={maturity.smoothness_score < 30 ? 'green' : maturity.smoothness_score < 50 ? 'yellow' : 'red'} />
            <Card title="Refinancing Risk" value={`${cashflow.summary.refinancing_risk_score}/100`} color={cashflow.summary.refinancing_risk_score < 30 ? 'green' : cashflow.summary.refinancing_risk_score < 60 ? 'yellow' : 'red'} />
            <Card title="Near-Term (3yr)" value={`${cashflow.summary.near_term_pct}%`} color={cashflow.summary.near_term_pct < 25 ? 'green' : cashflow.summary.near_term_pct < 40 ? 'yellow' : 'red'} />
          </div>

          {/* Maturity Walls Warning */}
          {maturity.maturity_walls.length > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <h3 className="text-red-800 font-semibold">⚠️ Maturity Walls Detected</h3>
              <div className="mt-2 space-y-1">
                {maturity.maturity_walls.map(w => (
                  <p key={w.year} className="text-red-700 text-sm">
                    {w.year}: ${(w.amount / 1e9).toFixed(1)}B ({w.pct.toFixed(0)}% of total) — Begin refinancing 18+ months ahead
                  </p>
                ))}
              </div>
            </div>
          )}

          {/* Maturity Ladder Chart */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">Maturity Ladder ({maturity.current_year} - {maturity.current_year + horizon})</h2>
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={maturity.buckets.map(b => ({ ...b, label: `${b.year}${wallYears.has(b.year) ? ' ⚠' : ''}`, principal_b: b.total_principal / 1e9, interest_b: b.total_interest / 1e9 }))}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                <YAxis tickFormatter={v => `$${v}B`} />
                <Tooltip formatter={(v: unknown) => `$${Number(v).toFixed(2)}B`} />
                <Legend />
                <Bar dataKey="principal_b" name="Principal Maturing" fill="#3b82f6" />
                <Bar dataKey="interest_b" name="Interest Due" fill="#f59e0b" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Cumulative Maturity */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">Cumulative Maturity Profile</h2>
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={maturity.buckets.map(b => ({ year: b.year, cumulative: b.cumulative_pct }))}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="year" />
                <YAxis tickFormatter={v => `${v}%`} domain={[0, 100]} />
                <Tooltip formatter={(v: unknown) => `${Number(v).toFixed(1)}%`} />
                <Area type="monotone" dataKey="cumulative" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.3} name="Cumulative %" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Cash Flow Projection */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">Cash Flow Projection</h2>
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={cashflow.projections.map(p => ({ year: p.year, principal: p.principal_repayments / 1e9, interest: p.interest_payments / 1e9, total: p.total_outflows / 1e9 }))}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="year" />
                <YAxis tickFormatter={v => `$${v}B`} />
                <Tooltip formatter={(v: unknown) => `$${Number(v).toFixed(2)}B`} />
                <Legend />
                <Bar dataKey="principal" name="Principal" fill="#ef4444" stackId="a" />
                <Bar dataKey="interest" name="Interest" fill="#f97316" stackId="a" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Refinancing Risk Line */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">Refinancing Risk by Year</h2>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={cashflow.projections.map(p => ({ year: p.year, ratio: p.refinancing_ratio }))}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="year" />
                <YAxis tickFormatter={v => `${v}%`} />
                <Tooltip formatter={(v: unknown) => `${Number(v).toFixed(1)}%`} />
                <Line type="monotone" dataKey="ratio" stroke="#ef4444" strokeWidth={2} name="Refinancing %" />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Recommendations */}
          {recommendations.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Refinancing Recommendations</h2>
              <div className="space-y-3">
                {recommendations.map((rec, i) => (
                  <div key={i} className={`p-4 rounded-lg border ${rec.severity === 'high' ? 'bg-red-50 border-red-200' : rec.severity === 'medium' ? 'bg-yellow-50 border-yellow-200' : 'bg-blue-50 border-blue-200'}`}>
                    <div className="flex items-start gap-2">
                      <span className={`text-xs font-bold px-2 py-0.5 rounded ${rec.severity === 'high' ? 'bg-red-200 text-red-800' : rec.severity === 'medium' ? 'bg-yellow-200 text-yellow-800' : 'bg-blue-200 text-blue-800'}`}>
                        {rec.severity.toUpperCase()}
                      </span>
                      <div>
                        <p className="text-sm text-gray-800">{rec.message}</p>
                        <p className="text-sm text-gray-600 mt-1">→ {rec.action}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {!selectedPortfolio && !loading && (
        <div className="text-center py-16 text-gray-400">
          <div className="text-5xl mb-4">📊</div>
          <p className="text-lg">Select a portfolio to view the maturity ladder and cash flow projection</p>
        </div>
      )}
    </div>
  );
}

function Card({ title, value, color }: { title: string; value: string; color: string }) {
  const colors: Record<string, string> = {
    green: 'text-green-600',
    yellow: 'text-yellow-600',
    red: 'text-red-600',
    blue: 'text-blue-600',
  };
  return (
    <div className="bg-white rounded-lg shadow p-4">
      <p className="text-sm text-gray-500">{title}</p>
      <p className={`text-xl font-bold ${colors[color] || 'text-gray-900'}`}>{value}</p>
    </div>
  );
}
