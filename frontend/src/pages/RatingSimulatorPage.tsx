import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { api } from '../api';

interface RatingAssessment {
  agency: string;
  current_rating: string;
  simulated_rating: string;
  change: string;
  score: number;
  components: Record<string, number>;
  key_drivers: Array<{ metric: string; impact: string; detail: string }>;
}

interface SimResult {
  country: string;
  current_ratings: { sp: string; moodys: string; fitch: string };
  simulated_ratings: { sp: string; moodys: string; fitch: string };
  rating_changes: { sp: string; moodys: string; fitch: string };
  assessments: { sp: RatingAssessment; moodys: RatingAssessment; fitch: RatingAssessment };
  outlook: string;
  average_score: number;
  key_drivers: Array<{ metric: string; impact: string; detail: string }>;
}

interface CountryInfo {
  code: string;
  sp_rating: string;
  moodys_rating: string;
  fitch_rating: string;
  gdp_per_capita: number;
  debt_to_gdp: number;
}

const SHOCK_FIELDS = [
  { key: 'gdp_per_capita', label: 'GDP per Capita', placeholder: 'e.g. 76000' },
  { key: 'gdp_growth', label: 'GDP Growth %', placeholder: 'e.g. 2.5' },
  { key: 'inflation', label: 'Inflation %', placeholder: 'e.g. 3.2' },
  { key: 'debt_to_gdp', label: 'Debt/GDP %', placeholder: 'e.g. 123' },
  { key: 'deficit_to_gdp', label: 'Deficit/GDP %', placeholder: 'e.g. -6.3' },
  { key: 'primary_balance', label: 'Primary Balance/GDP %', placeholder: 'e.g. -3.8' },
  { key: 'reserves_months', label: 'Reserves (months)', placeholder: 'e.g. 2' },
  { key: 'current_account_pct', label: 'Current Account/GDP %', placeholder: 'e.g. -3.5' },
  { key: 'institutions_score', label: 'Institutions (0-100)', placeholder: 'e.g. 85' },
  { key: 'rule_of_law', label: 'Rule of Law (0-100)', placeholder: 'e.g. 90' },
  { key: 'political_stability', label: 'Political Stability (0-100)', placeholder: 'e.g. 75' },
];

export default function RatingSimulatorPage() {
  const [countries, setCountries] = useState<CountryInfo[]>([]);
  const [selectedCountry, setSelectedCountry] = useState('US');
  const [result, setResult] = useState<SimResult | null>(null);
  const [shocks, setShocks] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.getRatingCountries().then((res: unknown) => setCountries(res as CountryInfo[]));
  }, []);

  const simulate = (withShocks = false) => {
    setLoading(true);
    const shockData: Record<string, number> = {};
    if (withShocks) {
      for (const [k, v] of Object.entries(shocks)) {
        if (v) shockData[k] = Number(v);
      }
    }

    const doSim = Object.keys(shockData).length > 0
      ? api.simulateRatingsWithShocks(selectedCountry, shockData)
      : api.simulateRatings(selectedCountry);

    doSim
      .then(d => setResult(d as unknown as SimResult))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (selectedCountry) simulate();
  }, [selectedCountry]);

  const agencyColors = { sp: '#3b82f6', moodys: '#8b5cf6', fitch: '#f59e0b' };
  const changeColors = { upgrade: 'text-green-600', downgrade: 'text-red-600', unchanged: 'text-gray-500' };

  const componentData = result ? (() => {
    const allKeys = new Set<string>();
    Object.values(result.assessments).forEach(a => Object.keys(a.components).forEach(k => allKeys.add(k)));
    return Array.from(allKeys).map(key => {
      const entry: Record<string, string | number> = { component: key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) };
      (['sp', 'moodys', 'fitch'] as const).forEach(agency => {
        entry[agency] = result.assessments[agency]?.components[key] ?? 0;
      });
      return entry;
    });
  })() : [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Rating Agency Simulator</h1>
          <p className="text-gray-500 mt-1">Simulate how S&P, Moody's, and Fitch would assess sovereign credit</p>
        </div>
        <div className="flex items-center gap-4">
          <div>
            <label className="block text-sm text-gray-500">Country</label>
            <select value={selectedCountry} onChange={e => setSelectedCountry(e.target.value)} className="border rounded px-2 py-1 text-sm">
              {countries.map(c => (
                <option key={c.code} value={c.code}>{c.code} — SP:{c.sp_rating} / Moody's:{c.moodys_rating} / Fitch:{c.fitch_rating}</option>
              ))}
            </select>
          </div>
          <button onClick={() => simulate(true)} className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">
            Run What-If
          </button>
        </div>
      </div>

      {/* Shock Inputs */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-3">Apply Economic Shocks</h2>
        <div className="grid grid-cols-3 md:grid-cols-4 gap-3">
          {SHOCK_FIELDS.map(f => (
            <div key={f.key}>
              <label className="block text-xs text-gray-500 mb-1">{f.label}</label>
              <input
                type="number"
                value={shocks[f.key] || ''}
                onChange={e => setShocks(s => ({ ...s, [f.key]: e.target.value }))}
                placeholder={f.placeholder}
                className="border rounded px-2 py-1 text-sm w-full"
              />
            </div>
          ))}
        </div>
      </div>

      {loading && <div className="text-center py-8 text-gray-500">Simulating ratings...</div>}

      {result && !loading && (
        <>
          {/* Current vs Simulated Ratings */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {(['sp', 'moodys', 'fitch'] as const).map(agency => {
              const a = result.assessments[agency];
              return (
                <div key={agency} className="bg-white rounded-lg shadow p-6">
                  <div className="text-sm text-gray-500 uppercase font-semibold">{a.agency}</div>
                  <div className="flex items-center gap-4 mt-3">
                    <div className="text-center">
                      <div className="text-xs text-gray-400">Current</div>
                      <div className="text-2xl font-bold" style={{ color: agencyColors[agency] }}>{a.current_rating}</div>
                    </div>
                    <div className="text-2xl text-gray-300">→</div>
                    <div className="text-center">
                      <div className="text-xs text-gray-400">Simulated</div>
                      <div className="text-2xl font-bold" style={{ color: agencyColors[agency] }}>{a.simulated_rating}</div>
                    </div>
                    <div className={`text-sm font-bold ${changeColors[a.change as keyof typeof changeColors]}`}>
                      {a.change === 'upgrade' ? '▲ Upgrade' : a.change === 'downgrade' ? '▼ Downgrade' : '— Unchanged'}
                    </div>
                  </div>
                  <div className="mt-4 text-sm text-gray-600">Score: {a.score}/100</div>

                  {/* Component Breakdown */}
                  <div className="mt-3 space-y-1">
                    {Object.entries(a.components).map(([key, val]) => (
                      <div key={key} className="flex items-center justify-between text-xs">
                        <span className="text-gray-500">{key.replace(/_/g, ' ')}</span>
                        <div className="flex items-center gap-2">
                          <div className="w-24 h-1.5 bg-gray-100 rounded">
                            <div className="h-1.5 rounded" style={{ width: `${Math.min(100, val as number)}%`, backgroundColor: agencyColors[agency] }} />
                          </div>
                          <span className="font-medium w-8 text-right">{(val as number).toFixed(0)}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Outlook */}
          <div className={`rounded-lg p-4 text-center ${result.outlook === 'positive' ? 'bg-green-50 text-green-800' : result.outlook === 'negative' ? 'bg-red-50 text-red-800' : 'bg-gray-50 text-gray-800'}`}>
            <span className="font-semibold">Overall Outlook: </span>
            <span className="text-lg font-bold uppercase">{result.outlook}</span>
            <span className="ml-2 text-sm">(Average Score: {result.average_score}/100)</span>
          </div>

          {/* Component Comparison Chart */}
          {componentData.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Component Comparison Across Agencies</h2>
              <ResponsiveContainer width="100%" height={350}>
                <BarChart data={componentData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="component" tick={{ fontSize: 10 }} />
                  <YAxis domain={[0, 100]} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="sp" name="S&P" fill={agencyColors.sp} />
                  <Bar dataKey="moodys" name="Moody's" fill={agencyColors.moodys} />
                  <Bar dataKey="fitch" name="Fitch" fill={agencyColors.fitch} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Key Drivers */}
          {result.key_drivers.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">Key Rating Drivers</h2>
              <div className="space-y-2">
                {result.key_drivers.map((driver, i) => (
                  <div key={i} className={`flex items-start gap-3 p-3 rounded ${driver.impact === 'positive' ? 'bg-green-50' : 'bg-red-50'}`}>
                    <span className={`text-xs font-bold px-2 py-0.5 rounded mt-0.5 ${driver.impact === 'positive' ? 'bg-green-200 text-green-800' : 'bg-red-200 text-red-800'}`}>
                      {driver.impact === 'positive' ? '▲' : '▼'}
                    </span>
                    <div>
                      <div className="text-sm font-medium text-gray-800">{driver.metric.replace(/_/g, ' ')}</div>
                      <div className="text-xs text-gray-600">{driver.detail}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Country List */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">All Countries ({countries.length})</h2>
            <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
              {countries.map(c => (
                <div
                  key={c.code}
                  onClick={() => setSelectedCountry(c.code)}
                  className={`p-2 rounded cursor-pointer text-center transition ${c.code === selectedCountry ? 'bg-blue-100 border-2 border-blue-500' : 'bg-gray-50 hover:bg-gray-100 border'}`}
                >
                  <div className="text-xs font-bold">{c.code}</div>
                  <div className="text-xs text-gray-600">SP: {c.sp_rating}</div>
                  <div className="text-xs text-gray-600">M: {c.moodys_rating}</div>
                  <div className="text-xs text-gray-600">F: {c.fitch_rating}</div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
