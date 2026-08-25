import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis } from 'recharts';
import { api } from '../api';

interface ESGSummary {
  total_instruments: number;
  total_principal: number;
  green_eligible_principal: number;
  green_eligible_pct: number;
  weighted_avg_esg: number;
  climate_risk_rating: string;
  climate_var: number;
}

interface InstrumentScore {
  instrument_id: string;
  instrument_name: string;
  currency: string;
  principal: number;
  esg_score: number;
  environmental: number;
  social: number;
  governance: number;
  is_green_eligible: boolean;
  carbon_risk_score: number;
}

interface CarbonScenario {
  carbon_price_per_tonne: number;
  estimated_annual_cost: number;
  cost_as_pct_of_debt: number;
}

interface ESGData {
  country_esg: { environmental: number; social: number; governance: number; overall: number };
  instrument_scores: InstrumentScore[];
  summary: ESGSummary;
  carbon_price_impacts: Record<string, CarbonScenario>;
  recommendations: Array<{ type: string; severity: string; message: string; action: string }>;
}

export default function ESGPage() {
  const [portfolios, setPortfolios] = useState<Array<{ id: string; name: string }>>([]);
  const [selectedPortfolio, setSelectedPortfolio] = useState('');
  const [countryCode, setCountryCode] = useState('US');
  const [data, setData] = useState<ESGData | null>(null);
  const [countryScores, setCountryScores] = useState<Record<string, { environmental: number; social: number; governance: number; overall: number }>>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.portfolios.list().then((res: unknown) => {
      const d = res as { data?: Array<{ id: string; name: string }> };
      setPortfolios(d?.data || []);
    });
    api.getCountryESGScores().then((res: unknown) => {
      setCountryScores(res as Record<string, { environmental: number; social: number; governance: number; overall: number }>);
    });
  }, []);

  useEffect(() => {
    if (!selectedPortfolio) return;
    setLoading(true);
    api.getESGScores(selectedPortfolio, countryCode)
      .then(d => setData(d as unknown as ESGData))
      .finally(() => setLoading(false));
  }, [selectedPortfolio, countryCode]);

  const radarData = data ? [
    { metric: 'Environmental', value: data.country_esg.environmental },
    { metric: 'Social', value: data.country_esg.social },
    { metric: 'Governance', value: data.country_esg.governance },
  ] : [];

  const carbonData = data ? Object.entries(data.carbon_price_impacts).map(([name, s]) => ({
    scenario: name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
    cost: s.estimated_annual_cost,
    pct: s.cost_as_pct_of_debt,
  })) : [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">ESG & Green Bond Analysis</h1>
          <p className="text-gray-500 mt-1">Climate-aware debt assessment and green bond eligibility</p>
        </div>
        <div className="flex items-center gap-4">
          <div>
            <label className="block text-sm text-gray-500">Country</label>
            <select value={countryCode} onChange={e => setCountryCode(e.target.value)} className="border rounded px-2 py-1 text-sm">
              {Object.keys(countryScores).length > 0
                ? Object.keys(countryScores).sort().map(c => <option key={c} value={c}>{c}</option>)
                : ['US','UK','DE','FR','JP','CN','IN','BR','CH','SE','NO'].map(c => <option key={c} value={c}>{c}</option>)
              }
            </select>
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

      {loading && <div className="text-center py-8 text-gray-500">Analyzing ESG metrics...</div>}

      {data && !loading && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <Card title="ESG Score" value={`${data.summary.weighted_avg_esg}/100`} color={data.summary.weighted_avg_esg > 60 ? 'green' : data.summary.weighted_avg_esg > 40 ? 'yellow' : 'red'} />
            <Card title="Green Eligible" value={`${data.summary.green_eligible_pct}%`} color={data.summary.green_eligible_pct > 20 ? 'green' : data.summary.green_eligible_pct > 10 ? 'yellow' : 'red'} />
            <Card title="Climate Rating" value={data.summary.climate_risk_rating} color={data.summary.climate_var < 0.02 ? 'green' : data.summary.climate_var < 0.03 ? 'yellow' : 'red'} />
            <Card title="Climate VaR" value={`${(data.summary.climate_var * 100).toFixed(1)}%`} color={data.summary.climate_var < 0.02 ? 'green' : 'red'} />
            <Card title="Instruments" value={`${data.summary.total_instruments}`} color="blue" />
          </div>

          {/* Country ESG Radar + Carbon Cost */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Country ESG Profile: {countryCode}</h2>
              <ResponsiveContainer width="100%" height={280}>
                <RadarChart data={radarData}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="metric" />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} />
                  <Radar name="ESG" dataKey="value" stroke="#22c55e" fill="#22c55e" fillOpacity={0.3} />
                </RadarChart>
              </ResponsiveContainer>
            </div>

            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Carbon Price Impact Scenarios</h2>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={carbonData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="scenario" tick={{ fontSize: 10 }} />
                  <YAxis tickFormatter={v => `$${v}M`} />
                  <Tooltip formatter={(v: unknown) => `$${Number(v).toFixed(1)}M`} />
                  <Bar dataKey="cost" name="Annual Cost" fill="#ef4444" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Instrument ESG Scores */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">Instrument ESG Scores</h2>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2 px-3">Instrument</th>
                    <th className="text-right py-2 px-3">Principal</th>
                    <th className="text-right py-2 px-3">ESG</th>
                    <th className="text-right py-2 px-3">E</th>
                    <th className="text-right py-2 px-3">S</th>
                    <th className="text-right py-2 px-3">G</th>
                    <th className="text-right py-2 px-3">Carbon Risk</th>
                    <th className="text-center py-2 px-3">Green</th>
                  </tr>
                </thead>
                <tbody>
                  {data.instrument_scores.map(inst => (
                    <tr key={inst.instrument_id} className="border-b hover:bg-gray-50">
                      <td className="py-2 px-3 font-medium">{inst.instrument_name}</td>
                      <td className="py-2 px-3 text-right">${(inst.principal / 1e9).toFixed(2)}B</td>
                      <td className="py-2 px-3 text-right">
                        <span className={inst.esg_score > 60 ? 'text-green-600' : inst.esg_score > 40 ? 'text-yellow-600' : 'text-red-600'}>
                          {inst.esg_score}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-right">{inst.environmental}</td>
                      <td className="py-2 px-3 text-right">{inst.social}</td>
                      <td className="py-2 px-3 text-right">{inst.governance}</td>
                      <td className="py-2 px-3 text-right">
                        <span className={inst.carbon_risk_score > 60 ? 'text-red-600' : inst.carbon_risk_score > 40 ? 'text-yellow-600' : 'text-green-600'}>
                          {inst.carbon_risk_score}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-center">
                        {inst.is_green_eligible ? (
                          <span className="text-green-600 font-bold">YES</span>
                        ) : (
                          <span className="text-gray-400">No</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Country Comparison */}
          {Object.keys(countryScores).length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Global ESG Comparison</h2>
              <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
                {Object.entries(countryScores)
                  .sort((a, b) => (b[1].overall || 0) - (a[1].overall || 0))
                  .slice(0, 18)
                  .map(([code, scores]) => (
                    <div
                      key={code}
                      onClick={() => setCountryCode(code)}
                      className={`p-2 rounded cursor-pointer text-center transition ${code === countryCode ? 'bg-blue-100 border-2 border-blue-500' : 'bg-gray-50 hover:bg-gray-100 border'}`}
                    >
                      <div className="text-xs font-bold">{code}</div>
                      <div className={`text-lg font-bold ${scores.overall > 60 ? 'text-green-600' : scores.overall > 40 ? 'text-yellow-600' : 'text-red-600'}`}>
                        {scores.overall}
                      </div>
                      <div className="text-[10px] text-gray-500">E:{scores.environmental} S:{scores.social} G:{scores.governance}</div>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* Recommendations */}
          {data.recommendations.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">ESG Recommendations</h2>
              <div className="space-y-3">
                {data.recommendations.map((rec, i) => (
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
          <div className="text-5xl mb-4">🌱</div>
          <p className="text-lg">Select a portfolio to view ESG analysis and green bond eligibility</p>
        </div>
      )}
    </div>
  );
}

function Card({ title, value, color }: { title: string; value: string; color: string }) {
  const colors: Record<string, string> = { green: 'text-green-600', yellow: 'text-yellow-600', red: 'text-red-600', blue: 'text-blue-600' };
  return (
    <div className="bg-white rounded-lg shadow p-4">
      <p className="text-sm text-gray-500">{title}</p>
      <p className={`text-xl font-bold ${colors[color] || 'text-gray-900'}`}>{value}</p>
    </div>
  );
}
