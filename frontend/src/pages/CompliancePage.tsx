import { useState, useEffect } from 'react';
import { api } from '../api';

interface DSAResult {
  country_code: string;
  country_name: string;
  assessment_date: string;
  current_metrics: {
    public_debt_to_gdp: number;
    gross_financing_needs_to_gdp: number;
    debt_service_to_revenue: number;
    debt_service_to_exports: number;
  };
  projections: {
    horizon_years: number;
    debt_to_gdp: number[];
    growth: number[];
    primary_balance: number[];
    interest_rate: number[];
    inflation: number[];
  };
  fanchart: {
    median: number[];
    p75: number[];
    p95: number[];
  };
  risk_assessment: {
    overall: string;
    market_access: string;
    financing: string;
    rollover: string;
    interest_rate: string;
  };
  adjustment_needed_pct_gdp: number;
  recommendations: string[];
}

interface MTDSResult {
  country_code: string;
  country_name: string;
  horizon_years: number;
  targets: {
    debt_to_gdp: number;
    avg_maturity: number;
    domestic_share: number;
    fixed_rate_share: number;
    currency_mix: Record<string, number>;
  };
  annual_targets: Array<{
    year: number;
    target_debt_to_gdp: number;
    target_avg_maturity: number;
    target_issuance_bn: number;
    target_domestic_pct: number;
  }>;
  issuance_plan: {
    total_required: number;
    avg_target_coupon: number;
    recommended_issuances: Array<{
      tenor: string;
      currency: string;
      amount_bn: number;
      purpose: string;
    }>;
  };
}

const RISK_COLORS: Record<string, string> = {
  low: '#22c55e',
  moderate: '#eab308',
  high: '#ef4444',
  'in distress': '#dc2626',
};

const COUNTRIES = [
  { code: 'US', name: 'United States' },
  { code: 'GB', name: 'United Kingdom' },
  { code: 'JP', name: 'Japan' },
  { code: 'DE', name: 'Germany' },
  { code: 'FR', name: 'France' },
  { code: 'IT', name: 'Italy' },
  { code: 'CA', name: 'Canada' },
  { code: 'CN', name: 'China' },
  { code: 'IN', name: 'India' },
  { code: 'BR', name: 'Brazil' },
  { code: 'AU', name: 'Australia' },
  { code: 'KR', name: 'South Korea' },
  { code: 'MX', name: 'Mexico' },
  { code: 'ZA', name: 'South Africa' },
  { code: 'SA', name: 'Saudi Arabia' },
  { code: 'CH', name: 'Switzerland' },
  { code: 'SE', name: 'Sweden' },
  { code: 'NO', name: 'Norway' },
  { code: 'SG', name: 'Singapore' },
  { code: 'TR', name: 'Turkey' },
  { code: 'AR', name: 'Argentina' },
  { code: 'PL', name: 'Poland' },
  { code: 'NL', name: 'Netherlands' },
  { code: 'ES', name: 'Spain' },
];

export default function CompliancePage() {
  const [selectedCountry, setSelectedCountry] = useState('US');
  const [dsa, setDsa] = useState<DSAResult | null>(null);
  const [mtds, setMtds] = useState<MTDSResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<'dsa' | 'mtds'>('dsa');
  const [error, setError] = useState('');

  const loadReports = async () => {
    setLoading(true);
    setError('');
    try {
      const [dsaRes, mtdsRes] = await Promise.all([
        api.compliance.dsa(selectedCountry) as unknown as Promise<{ success: boolean; data: DSAResult }>,
        api.compliance.mtds(selectedCountry) as unknown as Promise<{ success: boolean; data: MTDSResult }>,
      ]);
      setDsa(dsaRes.data);
      setMtds(mtdsRes.data);
    } catch (err) {
      setError('Failed to load compliance reports');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReports();
  }, [selectedCountry]);

  const riskBadge = (risk: string) => (
    <span
      className="inline-block px-2 py-1 rounded text-xs font-medium text-white"
      style={{ backgroundColor: RISK_COLORS[risk] || '#6b7280' }}
    >
      {risk.toUpperCase()}
    </span>
  );

  const years = dsa ? Array.from({ length: 5 }, (_, i) => new Date().getFullYear() + i + 1) : [];

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">IMF Compliance Dashboard</h1>
      <p className="text-gray-400 mb-6">
        Debt Sustainability Analysis, Medium-Term Debt Strategy, and Government Finance Statistics
        — required by the IMF for lending programs.
      </p>

      {/* Country Selector */}
      <div className="flex items-center gap-4 mb-6">
        <select
          value={selectedCountry}
          onChange={(e) => setSelectedCountry(e.target.value)}
          className="bg-gray-800 border border-gray-600 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-blue-500"
        >
          {COUNTRIES.map((c) => (
            <option key={c.code} value={c.code}>
              {c.name}
            </option>
          ))}
        </select>
        <button
          onClick={loadReports}
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg disabled:opacity-50"
        >
          {loading ? 'Generating...' : 'Regenerate Reports'}
        </button>
      </div>

      {error && (
        <div className="bg-red-900/30 border border-red-500 rounded-lg p-4 mb-6 text-red-300">{error}</div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setTab('dsa')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            tab === 'dsa' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'
          }`}
        >
          Debt Sustainability Analysis
        </button>
        <button
          onClick={() => setTab('mtds')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            tab === 'mtds' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'
          }`}
        >
          Medium-Term Debt Strategy
        </button>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <span className="ml-3 text-gray-400">Generating compliance report...</span>
        </div>
      )}

      {/* DSA Tab */}
      {tab === 'dsa' && dsa && !loading && (
        <div className="space-y-6">
          {/* Risk Assessment */}
          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">
              Risk Assessment — {dsa.country_name}
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {Object.entries(dsa.risk_assessment).map(([key, value]) => (
                <div key={key} className="text-center">
                  <div className="text-sm text-gray-400 mb-1">
                    {key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                  </div>
                  {riskBadge(value)}
                </div>
              ))}
            </div>
          </div>

          {/* Current Metrics */}
          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Current Debt Metrics</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <div className="text-center p-4 bg-gray-700/50 rounded-lg">
                <div className="text-3xl font-bold text-blue-400">
                  {dsa.current_metrics.public_debt_to_gdp}%
                </div>
                <div className="text-sm text-gray-400 mt-1">Public Debt / GDP</div>
              </div>
              <div className="text-center p-4 bg-gray-700/50 rounded-lg">
                <div className="text-3xl font-bold text-yellow-400">
                  {dsa.current_metrics.gross_financing_needs_to_gdp}%
                </div>
                <div className="text-sm text-gray-400 mt-1">GFN / GDP</div>
              </div>
              <div className="text-center p-4 bg-gray-700/50 rounded-lg">
                <div className="text-3xl font-bold text-orange-400">
                  {dsa.current_metrics.debt_service_to_revenue}%
                </div>
                <div className="text-sm text-gray-400 mt-1">Debt Service / Revenue</div>
              </div>
              <div className="text-center p-4 bg-gray-700/50 rounded-lg">
                <div className="text-3xl font-bold text-red-400">
                  {dsa.current_metrics.debt_service_to_exports}%
                </div>
                <div className="text-sm text-gray-400 mt-1">Debt Service / Exports</div>
              </div>
            </div>
          </div>

          {/* 5-Year Debt Projections */}
          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">5-Year Debt Projections</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-700">
                    <th className="text-left py-2 text-gray-400">Year</th>
                    {dsa.projections.debt_to_gdp.map((_, i) => (
                      <th key={i} className="text-right py-2 text-gray-400">{years[i]}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b border-gray-700/50">
                    <td className="py-2 text-gray-300">Debt / GDP</td>
                    {dsa.projections.debt_to_gdp.map((v, i) => (
                      <td key={i} className="text-right py-2 font-mono text-white">{v.toFixed(1)}%</td>
                    ))}
                  </tr>
                  <tr className="border-b border-gray-700/50">
                    <td className="py-2 text-gray-300">GDP Growth</td>
                    {dsa.projections.growth.map((v, i) => (
                      <td key={i} className="text-right py-2 font-mono text-green-400">{v.toFixed(1)}%</td>
                    ))}
                  </tr>
                  <tr className="border-b border-gray-700/50">
                    <td className="py-2 text-gray-300">Primary Balance</td>
                    {dsa.projections.primary_balance.map((v, i) => (
                      <td key={i} className={`text-right py-2 font-mono ${v >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {v >= 0 ? '+' : ''}{v.toFixed(1)}%
                      </td>
                    ))}
                  </tr>
                  <tr className="border-b border-gray-700/50">
                    <td className="py-2 text-gray-300">Interest Rate</td>
                    {dsa.projections.interest_rate.map((v, i) => (
                      <td key={i} className="text-right py-2 font-mono text-yellow-400">{v.toFixed(1)}%</td>
                    ))}
                  </tr>
                  <tr>
                    <td className="py-2 text-gray-300">Inflation</td>
                    {dsa.projections.inflation.map((v, i) => (
                      <td key={i} className="text-right py-2 font-mono text-purple-400">{v.toFixed(1)}%</td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* Fanchart */}
          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Debt Fanchart (Monte Carlo)</h2>
            <div className="relative h-64">
              <svg viewBox="0 0 500 200" className="w-full h-full">
                {/* 95th percentile band */}
                {dsa.fanchart.p95.map((val, i) => {
                  const x = 50 + (i / 4) * 400;
                  const nextX = i < 4 ? 50 + ((i + 1) / 4) * 400 : x;
                  const y95 = 180 - (val / 200) * 160;
                  const y95n = i < 4 ? 180 - (dsa.fanchart.p95[i + 1] / 200) * 160 : y95;
                  return (
                    <rect
                      key={`p95-${i}`}
                      x={x}
                      y={Math.min(y95, y95n)}
                      width={nextX - x || 10}
                      height={Math.abs(y95 - y95n) || 2}
                      fill="rgba(239,68,68,0.1)"
                    />
                  );
                })}
                {/* 75th percentile band */}
                {dsa.fanchart.p75.map((val, i) => {
                  const x = 50 + (i / 4) * 400;
                  const nextX = i < 4 ? 50 + ((i + 1) / 4) * 400 : x;
                  const y75 = 180 - (val / 200) * 160;
                  const y75n = i < 4 ? 180 - (dsa.fanchart.p75[i + 1] / 200) * 160 : y75;
                  return (
                    <rect
                      key={`p75-${i}`}
                      x={x}
                      y={Math.min(y75, y75n)}
                      width={nextX - x || 10}
                      height={Math.abs(y75 - y75n) || 2}
                      fill="rgba(234,179,8,0.15)"
                    />
                  );
                })}
                {/* Median line */}
                <polyline
                  points={dsa.fanchart.median
                    .map((val, i) => `${50 + (i / 4) * 400},${180 - (val / 200) * 160}`)
                    .join(' ')}
                  fill="none"
                  stroke="#3b82f6"
                  strokeWidth="2.5"
                />
                {/* Labels */}
                {dsa.fanchart.median.map((val, i) => (
                  <g key={`label-${i}`}>
                    <circle cx={50 + (i / 4) * 400} cy={180 - (val / 200) * 160} r="4" fill="#3b82f6" />
                    <text
                      x={50 + (i / 4) * 400}
                      y={175 - (val / 200) * 160}
                      textAnchor="middle"
                      fill="#9ca3af"
                      fontSize="10"
                    >
                      {val.toFixed(1)}%
                    </text>
                  </g>
                ))}
                {/* Year labels */}
                {years.map((year, i) => (
                  <text
                    key={`year-${i}`}
                    x={50 + (i / 4) * 400}
                    y={198}
                    textAnchor="middle"
                    fill="#6b7280"
                    fontSize="11"
                  >
                    {year}
                  </text>
                ))}
              </svg>
              <div className="absolute top-2 right-2 flex gap-4 text-xs">
                <span className="flex items-center gap-1">
                  <span className="w-3 h-0.5 bg-blue-500 inline-block"></span> Median
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-3 h-3 bg-yellow-500/20 inline-block rounded"></span> P75
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-3 h-3 bg-red-500/10 inline-block rounded"></span> P95
                </span>
              </div>
            </div>
          </div>

          {/* Adjustments & Recommendations */}
          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">
              Fiscal Adjustment Needed
            </h2>
            <div className="text-center mb-4">
              <span className="text-4xl font-bold text-yellow-400">
                {dsa.adjustment_needed_pct_gdp > 0 ? '+' : ''}
                {dsa.adjustment_needed_pct_gdp}%
              </span>
              <div className="text-sm text-gray-400 mt-1">of GDP primary balance adjustment</div>
            </div>
            <h3 className="text-md font-semibold mb-2 text-gray-300">Recommendations</h3>
            <ul className="space-y-2">
              {dsa.recommendations.map((rec, i) => (
                <li key={i} className="flex items-start gap-2 text-gray-300">
                  <span className="text-blue-400 mt-0.5">→</span>
                  {rec}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* MTDS Tab */}
      {tab === 'mtds' && mtds && !loading && (
        <div className="space-y-6">
          {/* Strategy Targets */}
          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">
              5-Year Strategy Targets — {mtds.country_name}
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="text-center p-4 bg-gray-700/50 rounded-lg">
                <div className="text-2xl font-bold text-blue-400">{mtds.targets.debt_to_gdp}%</div>
                <div className="text-xs text-gray-400 mt-1">Target Debt/GDP</div>
              </div>
              <div className="text-center p-4 bg-gray-700/50 rounded-lg">
                <div className="text-2xl font-bold text-green-400">{mtds.targets.avg_maturity}Y</div>
                <div className="text-xs text-gray-400 mt-1">Target Maturity</div>
              </div>
              <div className="text-center p-4 bg-gray-700/50 rounded-lg">
                <div className="text-2xl font-bold text-purple-400">{mtds.targets.domestic_share}%</div>
                <div className="text-xs text-gray-400 mt-1">Domestic Share</div>
              </div>
              <div className="text-center p-4 bg-gray-700/50 rounded-lg">
                <div className="text-2xl font-bold text-yellow-400">{mtds.targets.fixed_rate_share}%</div>
                <div className="text-xs text-gray-400 mt-1">Fixed Rate</div>
              </div>
              <div className="text-center p-4 bg-gray-700/50 rounded-lg">
                <div className="text-2xl font-bold text-orange-400">{mtds.issuance_plan.total_required >= 1000 ? `$${(mtds.issuance_plan.total_required / 1000).toFixed(1)}T` : `$${mtds.issuance_plan.total_required.toFixed(0)}B`}</div>
                <div className="text-xs text-gray-400 mt-1">Total Issuance</div>
              </div>
            </div>
          </div>

          {/* Annual Targets */}
          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Annual Targets</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-700">
                    <th className="text-left py-2 text-gray-400">Year</th>
                    <th className="text-right py-2 text-gray-400">Debt/GDP</th>
                    <th className="text-right py-2 text-gray-400">Avg Maturity</th>
                    <th className="text-right py-2 text-gray-400">Issuance</th>
                    <th className="text-right py-2 text-gray-400">Domestic %</th>
                  </tr>
                </thead>
                <tbody>
                  {mtds.annual_targets.map((t) => (
                    <tr key={t.year} className="border-b border-gray-700/50">
                      <td className="py-2 font-medium text-white">{t.year}</td>
                      <td className="text-right py-2 font-mono text-blue-400">{t.target_debt_to_gdp}%</td>
                      <td className="text-right py-2 font-mono text-green-400">{t.target_avg_maturity}Y</td>
                      <td className="text-right py-2 font-mono text-yellow-400">${t.target_issuance_bn}B</td>
                      <td className="text-right py-2 font-mono text-purple-400">{t.target_domestic_pct}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Recommended Issuances */}
          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Recommended Issuances</h2>
            <div className="space-y-3">
              {mtds.issuance_plan.recommended_issuances.map((iss, i) => (
                <div key={i} className="flex items-center justify-between bg-gray-700/50 rounded-lg p-4">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-blue-600/20 rounded-lg flex items-center justify-center text-blue-400 font-bold text-sm">
                      {iss.tenor}
                    </div>
                    <div>
                      <div className="font-medium text-white">{iss.currency} {iss.tenor} Bond</div>
                      <div className="text-sm text-gray-400">{iss.purpose}</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-bold text-white">${iss.amount_bn >= 1000 ? `${(iss.amount_bn / 1000).toFixed(1)}T` : `${iss.amount_bn.toFixed(0)}B`}</div>
                    <div className="text-xs text-gray-400">
                      Target coupon: {mtds.issuance_plan.avg_target_coupon.toFixed(2)}%
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Currency Mix */}
          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Target Currency Mix</h2>
            <div className="flex gap-2 h-8 rounded-lg overflow-hidden">
              {Object.entries(mtds.targets.currency_mix).map(([ccy, pct], i) => {
                const colors = ['#3b82f6', '#22c55e', '#eab308', '#ef4444', '#a855f7'];
                return (
                  <div
                    key={ccy}
                    className="flex items-center justify-center text-xs font-medium text-white"
                    style={{ width: `${pct}%`, backgroundColor: colors[i % colors.length] }}
                    title={`${ccy}: ${pct.toFixed(1)}%`}
                  >
                    {pct > 10 ? `${ccy} ${pct.toFixed(0)}%` : ''}
                  </div>
                );
              })}
            </div>
            <div className="flex gap-4 mt-3 flex-wrap">
              {Object.entries(mtds.targets.currency_mix).map(([ccy, pct], i) => {
                const colors = ['#3b82f6', '#22c55e', '#eab308', '#ef4444', '#a855f7'];
                return (
                  <div key={ccy} className="flex items-center gap-2 text-sm text-gray-300">
                    <span className="w-3 h-3 rounded" style={{ backgroundColor: colors[i % colors.length] }}></span>
                    {ccy}: {pct.toFixed(1)}%
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
