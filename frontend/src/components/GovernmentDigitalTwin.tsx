import { useState } from 'react';
import Card, { CardHeader } from './ui/Card';
import Badge from './ui/Badge';
import Button from './ui/Button';

interface SimulationScenario {
  id: string;
  name: string;
  description: string;
  category: 'commodity' | 'demographic' | 'fiscal' | 'external' | 'policy';
  impact: { gdp: number; debtToGdp: number; deficit: number; reserves: number; rating: string };
}

interface SimulationResult {
  scenario: string;
  current: Record<string, number>;
  projected: Record<string, number>;
  timeline: Array<{ year: string; gdp: number; debt: number; deficit: number }>;
}

const SCENARIOS: SimulationScenario[] = [
  { id: 'oil-drop', name: 'Oil Price Drop 40%', description: 'Simulate the impact of oil prices falling from $85 to $51/barrel', category: 'commodity', impact: { gdp: -1.8, debtToGdp: 8.5, deficit: 2.1, reserves: -12, rating: 'Watch Negative' } },
  { id: 'rate-hike', name: 'Interest Rates +300bps', description: 'Federal Reserve raises rates by 300 basis points over 12 months', category: 'fiscal', impact: { gdp: -0.9, debtToGdp: 5.2, deficit: 3.4, reserves: -8, rating: 'Stable' } },
  { id: 'birth-decline', name: 'Birth Rate Continued Decline', description: 'Fertility rate drops to 1.4, reducing working-age population by 8% over 20 years', category: 'demographic', impact: { gdp: -2.4, debtToGdp: 22, deficit: 1.8, reserves: -5, rating: 'Negative' } },
  { id: 'export-fall', name: 'Export Revenue Falls 25%', description: 'Major trading partners enter recession, reducing export demand', category: 'external', impact: { gdp: -3.1, debtToGdp: 14, deficit: 4.2, reserves: -18, rating: 'Watch Negative' } },
  { id: 'tax-reform', name: 'Tax Revenue Reform', description: 'Implement broadened tax base increasing revenue by 15%', category: 'policy', impact: { gdp: 0.8, debtToGdp: -12, deficit: -3.5, reserves: 8, rating: 'Positive' } },
  { id: 'pandemic', name: 'Pandemic 2.0', description: 'Global pandemic reduces GDP by 6% and increases health spending by 40%', category: 'external', impact: { gdp: -6.2, debtToGdp: 35, deficit: 8.5, reserves: -25, rating: 'Negative' } },
];

const CATEGORY_COLORS: Record<string, string> = {
  commodity: 'text-amber-700 bg-amber-500/12 border-amber-500/20',
  demographic: 'text-violet-700 bg-violet-500/12 border-violet-500/20',
  fiscal: 'text-red-700 bg-red-500/12 border-red-500/20',
  external: 'text-blue-700 bg-blue-500/12 border-blue-500/20',
  policy: 'text-emerald-700 bg-emerald-500/12 border-emerald-500/20' };

export default function GovernmentDigitalTwin() {
  const [selected, setSelected] = useState<SimulationScenario | null>(null);
  const [simulating, setSimulating] = useState(false);
  const [result, setResult] = useState<SimulationResult | null>(null);

  const runSimulation = async (scenario: SimulationScenario) => {
    setSelected(scenario);
    setSimulating(true);
    setResult(null);
    await new Promise((r) => setTimeout(r, 1200));

    const timeline = Array.from({ length: 10 }, (_, i) => {
      const year = 2027 + i;
      const gdpImpact = scenario.impact.gdp * ((i + 1) / 10);
      const debtImpact = scenario.impact.debtToGdp * ((i + 1) / 10);
      return {
        year: String(year),
        gdp: 2.4 + gdpImpact + (Math.random() - 0.5) * 0.3,
        debt: 98 + debtImpact + (Math.random() - 0.5) * 2,
        deficit: 3.8 + scenario.impact.deficit * ((i + 1) / 10) };
    });

    setResult({
      scenario: scenario.name,
      current: { gdp: 2.4, debtToGdp: 98.5, deficit: 3.8, reserves: 450 },
      projected: {
        gdp: 2.4 + scenario.impact.gdp,
        debtToGdp: 98.5 + scenario.impact.debtToGdp,
        deficit: 3.8 + scenario.impact.deficit,
        reserves: 450 + scenario.impact.reserves },
      timeline });
    setSimulating(false);
  };

  return (
    <div className="space-y-6">
      {/* National metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'GDP Growth', value: '2.4%', color: 'text-slate-900' },
          { label: 'Debt/GDP', value: '98.5%', color: 'text-amber-600' },
          { label: 'Fiscal Deficit', value: '3.8%', color: 'text-red-600' },
          { label: 'FX Reserves', value: '$450B', color: 'text-emerald-600' },
        ].map((m) => (
          <Card key={m.label}>
            <div className="p-4 text-center">
              <p className={`text-2xl font-bold ${m.color}`}>{m.value}</p>
              <p className="text-xs text-slate-500 mt-1">{m.label}</p>
            </div>
          </Card>
        ))}
      </div>

      {/* Scenario selection */}
      <Card>
        <CardHeader title="Simulation Scenarios" subtitle="Select a scenario to simulate national impact" />
        <div className="px-6 pb-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {SCENARIOS.map((s) => (
            <button
              key={s.id}
              onClick={() => runSimulation(s)}
              disabled={simulating}
              className={`text-left p-4 rounded-2xl border transition-all hover:shadow-lg ${
                selected?.id === s.id
                  ? 'bg-slate-900 text-white border-slate-900'
                  : 'bg-white/60 border-white/60 hover:bg-white/80'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className={`text-[10px] font-bold rounded-full px-2 py-0.5 border ${CATEGORY_COLORS[s.category]}`}>
                  {s.category}
                </span>
              </div>
              <h4 className="text-sm font-bold">{s.name}</h4>
              <p className="text-[11px] text-slate-500 mt-1 line-clamp-2">{s.description}</p>
            </button>
          ))}
        </div>
      </Card>

      {/* Simulation results */}
      {simulating && (
        <Card>
          <div className="p-12 text-center">
            <div className="animate-spin h-8 w-8 border-4 border-slate-200 border-t-blue-600 rounded-full mx-auto mb-4" />
            <p className="text-sm text-slate-500">Running simulation across 10-year horizon...</p>
          </div>
        </Card>
      )}

      {result && !simulating && (
        <div className="space-y-4">
          <Card>
            <CardHeader
              title={`Impact: ${result.scenario}`}
              subtitle="Projected changes over the simulation period"
            />
            <div className="px-6 pb-6 grid grid-cols-2 sm:grid-cols-4 gap-4">
              {[
                { label: 'GDP Growth', current: `${result.current.gdp}%`, projected: `${result.projected.gdp.toFixed(1)}%`, negative: result.projected.gdp < result.current.gdp },
                { label: 'Debt/GDP', current: `${result.current.debtToGdp}%`, projected: `${result.projected.debtToGdp.toFixed(1)}%`, negative: result.projected.debtToGdp > result.current.debtToGdp },
                { label: 'Fiscal Deficit', current: `${result.current.deficit}%`, projected: `${result.projected.deficit.toFixed(1)}%`, negative: result.projected.deficit > result.current.deficit },
                { label: 'FX Reserves', current: `$${result.current.reserves}B`, projected: `$${result.projected.reserves}B`, negative: result.projected.reserves < result.current.reserves },
              ].map((m) => (
                <div key={m.label} className="bg-white/50 rounded-2xl p-4">
                  <p className="text-[10px] uppercase tracking-wider text-slate-400 mb-1">{m.label}</p>
                  <p className="text-xs text-slate-500">Current: {m.current}</p>
                  <p className={`text-lg font-bold ${m.negative ? 'text-red-600' : 'text-emerald-600'}`}>{m.projected}</p>
                </div>
              ))}
            </div>
          </Card>

          {/* Timeline chart as div bars */}
          <Card>
            <CardHeader title="10-Year Projection" subtitle="GDP growth trajectory under this scenario" />
            <div className="px-6 pb-6">
              <div className="flex items-end gap-1 h-40">
                {result.timeline.map((t) => {
                  const h = Math.max(10, ((t.gdp + 5) / 10) * 100);
                  return (
                    <div key={t.year} className="flex-1 flex flex-col items-center gap-1">
                      <span className="text-[9px] text-slate-400 tabular-nums">{t.gdp.toFixed(1)}%</span>
                      <div
                        className={`w-full rounded-t-lg ${t.gdp >= 0 ? 'bg-gradient-to-t from-blue-600 to-cyan-400' : 'bg-gradient-to-t from-red-500 to-orange-400'}`}
                        style={{ height: `${h}%`, minHeight: '8px' }}
                      />
                      <span className="text-[9px] text-slate-500">{t.year.slice(2)}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </Card>

          {/* Rating impact */}
          <Card>
            <div className="px-6 py-4 flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-slate-900">Rating Outlook Impact</p>
                <p className="text-xs text-slate-500">Projected credit rating effect</p>
              </div>
              <Badge variant={result.projected.rating === 'Positive' ? 'success' : result.projected.rating === 'Negative' ? 'danger' : 'warning'}>
                {result.projected.rating}
              </Badge>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
