import { useState, useEffect, useMemo } from 'react';
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

// ── Local S&P/Moody's/Fitch Model ──────────────────────────────────────
const RATING_SCALE = ['AAA','AA+','AA','AA-','A+','A','A-','BBB+','BBB','BBB-','BB+','BB','BB-','B+','B','B-','CCC+','CCC','CCC-','CC','C','D'];
function scoreToRating(score: number): string {
  // score 0-100 maps to rating notch
  // 95+ AAA, 90-95 AA+, 85-90 AA, 80-85 AA-, 75-80 A+, etc.
  const idx = Math.max(0, Math.min(RATING_SCALE.length - 1, Math.floor((100 - score) / 4.5)));
  return RATING_SCALE[idx];
}
function ratingToScore(rating: string): number {
  const idx = RATING_SCALE.indexOf(rating);
  if (idx === -1) return 50;
  return Math.max(0, 100 - idx * 4.5 - 2);
}

type LocalInputs = {
  fiscalBalance: number; // primary balance % GDP
  debtToGdp: number;
  growth: number;
  reserves: number; // months
};

function computeAgencyScores(inputs: LocalInputs): { sp: number; moodys: number; fitch: number } {
  // Normalized sub-scores 0-100, then weighted
  const debtScore = Math.max(0, 100 - inputs.debtToGdp * 0.9 - (inputs.debtToGdp > 70 ? (inputs.debtToGdp - 70) * 0.5 : 0));
  const fiscalScore = Math.max(0, Math.min(100, 55 + inputs.fiscalBalance * 8)); // -5 => 15, 0=>55, 3=>79
  const growthScore = Math.max(0, Math.min(100, 40 + inputs.growth * 15)); // 2.5=>77
  const reservesScore = Math.max(0, Math.min(100, 20 + inputs.reserves * 12)); // 2=>44, 6=>92

  // Agency weightings differ subtly
  const sp = debtScore * 0.35 + fiscalScore * 0.25 + growthScore * 0.20 + reservesScore * 0.20;
  const moodys = debtScore * 0.30 + fiscalScore * 0.30 + growthScore * 0.25 + reservesScore * 0.15;
  const fitch = debtScore * 0.33 + fiscalScore * 0.27 + growthScore * 0.22 + reservesScore * 0.18;
  return {
    sp: Math.round(Math.max(0, Math.min(100, sp))),
    moodys: Math.round(Math.max(0, Math.min(100, moodys))),
    fitch: Math.round(Math.max(0, Math.min(100, fitch))),
  };
}

function downgradeProbability(score: number, currentRating: string): number {
  const currentScore = ratingToScore(currentRating);
  const gap = currentScore - score; // positive means deterioration
  // logistic: 50% at gap 0, 90% at gap +10, 10% at gap -10
  const p = 1 / (1 + Math.exp(-gap / 6));
  return Math.max(0.01, Math.min(0.99, p));
}

// Liquid Glass Gauge for downgrade probability
function DowngradeGauge({ probability }: { probability: number }) {
  const pct = Math.round(probability * 100);
  const color = pct >= 70 ? '#ef4444' : pct >= 40 ? '#f59e0b' : '#22c55e';
  const label = pct >= 70 ? 'High Risk' : pct >= 40 ? 'Moderate' : 'Low Risk';
  const angle = (pct / 100) * 180; // 0-180 degrees over semicircle
  const cx = 100, cy = 90, r = 80;
  const rad = (angle - 180) * Math.PI / 180;
  const x = cx + r * Math.cos(rad);
  const y = cy + r * Math.sin(rad);

  return (
    <div className="bg-white/40 backdrop-blur-xl rounded-2xl border border-white/30 p-4 flex flex-col items-center shadow-sm">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Downgrade Probability</p>
      <svg width="200" height="120" viewBox="0 0 200 120">
        <defs>
          <linearGradient id="gaugeBg" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#22c55e" />
            <stop offset="50%" stopColor="#f59e0b" />
            <stop offset="100%" stopColor="#ef4444" />
          </linearGradient>
          <filter id="glassGlow">
            <feGaussianBlur stdDeviation="2" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>
        {/* Track */}
        <path d={`M 20 90 A 80 80 0 0 1 180 90`} fill="none" stroke="rgba(255,255,255,0.6)" strokeWidth="14" strokeLinecap="round" />
        {/* Value arc */}
        <path d={`M 20 90 A 80 80 0 0 1 ${x} ${y}`} fill="none" stroke="url(#gaugeBg)" strokeWidth="14" strokeLinecap="round" filter="url(#glassGlow)" style={{ transition: 'all 0.8s ease-out' }} />
        {/* Tick marks */}
        {[0, 25, 50, 75, 100].map(t => {
          const a = (t / 100) * 180 - 180;
          const rad2 = a * Math.PI / 180;
          const x1 = cx + (r - 10) * Math.cos(rad2);
          const y1 = cy + (r - 10) * Math.sin(rad2);
          const x2 = cx + r * Math.cos(rad2);
          const y2 = cy + r * Math.sin(rad2);
          return <line key={t} x1={x1} y1={y1} x2={x2} y2={y2} stroke="white" strokeWidth="1.5" opacity="0.7" />;
        })}
        {/* Needle */}
        <line x1={cx} y1={cy} x2={x} y2={y} stroke={color} strokeWidth="3" strokeLinecap="round" />
        <circle cx={cx} cy={cy} r="8" fill="white" stroke={color} strokeWidth="2" />
        <circle cx={cx} cy={cy} r="3" fill={color} />
        {/* Center text */}
        <text x={cx} y={55} textAnchor="middle" fontSize="22" fontWeight="800" fill={color}>{pct}%</text>
        <text x={cx} y={72} textAnchor="middle" fontSize="10" fontWeight="600" fill="#64748b">{label}</text>
      </svg>
      <div className="flex gap-2 mt-1">
        <span className="px-2 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/20 text-emerald-700 text-[11px] font-bold backdrop-blur-md">0-40% Low</span>
        <span className="px-2 py-1 rounded-full bg-amber-500/15 border border-amber-500/20 text-amber-700 text-[11px] font-bold backdrop-blur-md">40-70% Mod</span>
        <span className="px-2 py-1 rounded-full bg-red-500/15 border border-red-500/20 text-red-700 text-[11px] font-bold backdrop-blur-md">70%+ High</span>
      </div>
    </div>
  );
}

function SensitivityTable({ inputs, baseScores, getRating }: { inputs: LocalInputs; baseScores: { sp: number; moodys: number; fitch: number }; getRating: (s: number) => string }) {
  const shocks: Array<{ label: string; apply: (inp: LocalInputs) => LocalInputs }> = [
    { label: 'Debt/GDP +10pp', apply: inp => ({ ...inp, debtToGdp: inp.debtToGdp + 10 }) },
    { label: 'Growth -1pp', apply: inp => ({ ...inp, growth: inp.growth - 1 }) },
    { label: 'Fiscal -1pp', apply: inp => ({ ...inp, fiscalBalance: inp.fiscalBalance - 1 }) },
    { label: 'Reserves -2m', apply: inp => ({ ...inp, reserves: Math.max(0, inp.reserves - 2) }) },
  ];
  return (
    <div className="bg-white/40 backdrop-blur-xl rounded-2xl border border-white/30 p-5 shadow-sm">
      <h3 className="text-sm font-bold text-slate-900 mb-3">Sensitivity — Rating Impact per Shock (Glass)</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/40">
              <th className="text-left py-2 text-xs font-semibold text-slate-500 uppercase">Shock</th>
              <th className="text-center py-2 text-xs font-semibold text-slate-500 uppercase">S&P Score → Notch</th>
              <th className="text-center py-2 text-xs font-semibold text-slate-500 uppercase">Moody's</th>
              <th className="text-center py-2 text-xs font-semibold text-slate-500 uppercase">Fitch</th>
              <th className="text-center py-2 text-xs font-semibold text-slate-500 uppercase">Δ Notches</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/20">
            <tr className="bg-white/40">
              <td className="py-2 font-medium text-slate-700">Baseline</td>
              <td className="py-2 text-center font-mono text-slate-900">{baseScores.sp} → {getRating(baseScores.sp)}</td>
              <td className="py-2 text-center font-mono text-slate-900">{baseScores.moodys} → {getRating(baseScores.moodys)}</td>
              <td className="py-2 text-center font-mono text-slate-900">{baseScores.fitch} → {getRating(baseScores.fitch)}</td>
              <td className="py-2 text-center">—</td>
            </tr>
            {shocks.map(s => {
              const shocked = s.apply(inputs);
              const sc = computeAgencyScores(shocked);
              const baseNotchIdx = (rating: string) => RATING_SCALE.indexOf(rating);
              const delta = (newScore: number, baseScore: number) => {
                const n1 = baseNotchIdx(getRating(baseScore));
                const n2 = baseNotchIdx(getRating(newScore));
                const d = n2 - n1;
                return d === 0 ? '—' : d > 0 ? `▼ ${d}` : `▲ ${Math.abs(d)}`;
              };
              return (
                <tr key={s.label} className="hover:bg-white/30">
                  <td className="py-2 text-slate-700">{s.label}</td>
                  <td className="py-2 text-center font-mono"><span className={sc.sp < baseScores.sp ? 'text-red-600 font-bold' : 'text-emerald-600'}>{sc.sp} → {getRating(sc.sp)}</span></td>
                  <td className="py-2 text-center font-mono"><span className={sc.moodys < baseScores.moodys ? 'text-red-600 font-bold' : 'text-emerald-600'}>{sc.moodys} → {getRating(sc.moodys)}</span></td>
                  <td className="py-2 text-center font-mono"><span className={sc.fitch < baseScores.fitch ? 'text-red-600 font-bold' : 'text-emerald-600'}>{sc.fitch} → {getRating(sc.fitch)}</span></td>
                  <td className="py-2 text-center font-mono text-xs">{delta(sc.sp, baseScores.sp)} / {delta(sc.moodys, baseScores.moodys)} / {delta(sc.fitch, baseScores.fitch)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-slate-400 mt-2">Notch delta vs baseline per agency — glass table with backdrop-blur.</p>
    </div>
  );
}

export default function RatingSimulatorPage() {
  const [countries, setCountries] = useState<CountryInfo[]>([]);
  const [selectedCountry, setSelectedCountry] = useState('US');
  const [result, setResult] = useState<SimResult | null>(null);
  const [shocks, setShocks] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  // Local model inputs
  const [fiscalBalance, setFiscalBalance] = useState(-3.5);
  const [debtToGdp, setDebtToGdp] = useState(85);
  const [growth, setGrowth] = useState(2.0);
  const [reserves, setReserves] = useState(4);

  useEffect(() => {
    api.getRatingCountries().then((res: unknown) => setCountries(res as CountryInfo[]));
  }, []);

  // Sync local inputs when country changes (use that country's debt_to_gdp as baseline)
  useEffect(() => {
    const c = countries.find(x => x.code === selectedCountry);
    if (c) setDebtToGdp(Math.round(c.debt_to_gdp || 85));
  }, [selectedCountry, countries]);

  const localInputs: LocalInputs = useMemo(() => ({
    fiscalBalance, debtToGdp, growth, reserves
  }), [fiscalBalance, debtToGdp, growth, reserves]);

  const localScores = useMemo(() => computeAgencyScores(localInputs), [localInputs]);
  const localRatings = useMemo(() => ({
    sp: scoreToRating(localScores.sp),
    moodys: scoreToRating(localScores.moodys),
    fitch: scoreToRating(localScores.fitch),
  }), [localScores]);

  const downgradeProbs = useMemo(() => {
    const base = countries.find(c => c.code === selectedCountry);
    return {
      sp: downgradeProbability(localScores.sp, base?.sp_rating || 'BBB'),
      moodys: downgradeProbability(localScores.moodys, base?.moodys_rating || 'Baa2'),
      fitch: downgradeProbability(localScores.fitch, base?.fitch_rating || 'BBB'),
    };
  }, [localScores, countries, selectedCountry]);

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
    <div className="space-y-6 p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Rating Agency Simulator</h1>
          <p className="text-gray-500 mt-1">Local S&P / Moody's / Fitch model — fiscal balance, debt/GDP, growth, reserves → score → notch; downgrade probability gauge (liquid glass) & sensitivity</p>
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

      {/* Local Model Inputs — Glass */}
      <div className="bg-white/40 backdrop-blur-xl rounded-2xl border border-white/30 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-slate-900">Local Rating Model — Core Inputs</h2>
          <span className="px-3 py-1 rounded-full bg-blue-500/15 border border-blue-500/20 text-blue-700 text-xs font-bold backdrop-blur-md">S&P / Moody's / Fitch weighted</span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Fiscal Balance (% GDP)</label>
            <input type="number" step="0.1" value={fiscalBalance} onChange={e => setFiscalBalance(Number(e.target.value))} className="w-full rounded-xl border border-white/40 bg-white/60 backdrop-blur-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/30" />
            <p className="text-xs text-slate-400 mt-1">Primary balance; surplus &gt;0</p>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Debt / GDP (%)</label>
            <input type="number" step="1" value={debtToGdp} onChange={e => setDebtToGdp(Number(e.target.value))} className="w-full rounded-xl border border-white/40 bg-white/60 backdrop-blur-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/30" />
            <p className="text-xs text-slate-400 mt-1">70% IMF threshold</p>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Real Growth (%)</label>
            <input type="number" step="0.1" value={growth} onChange={e => setGrowth(Number(e.target.value))} className="w-full rounded-xl border border-white/40 bg-white/60 backdrop-blur-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/30" />
            <p className="text-xs text-slate-400 mt-1">Medium-term avg</p>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Reserves (months imports)</label>
            <input type="number" step="0.5" value={reserves} onChange={e => setReserves(Number(e.target.value))} className="w-full rounded-xl border border-white/40 bg-white/60 backdrop-blur-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/30" />
            <p className="text-xs text-slate-400 mt-1">Liquidity buffer</p>
          </div>
        </div>

        {/* Score → Rating Notch Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
          {(['sp','moodys','fitch'] as const).map(agency => (
            <div key={agency} className="bg-white/60 backdrop-blur-xl rounded-2xl border border-white/40 p-4 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider" style={{ color: agencyColors[agency] }}>{agency === 'sp' ? 'S&P' : agency === 'moodys' ? "Moody's" : 'Fitch'}</span>
                <span className="px-2 py-1 rounded-full bg-white/70 border border-white/40 text-xs font-bold text-slate-700 backdrop-blur-md">Score {localScores[agency]}/100</span>
              </div>
              <div className="mt-3 flex items-baseline gap-3">
                <span className="text-3xl font-extrabold text-slate-900">{localRatings[agency]}</span>
                <span className="text-sm text-slate-500">→ notch from score</span>
              </div>
              <div className="mt-2 h-2 bg-white/60 rounded-full overflow-hidden">
                <div className="h-full rounded-full" style={{ width: `${localScores[agency]}%`, background: agencyColors[agency] }} />
              </div>
              <div className="mt-2 flex items-center justify-between text-xs">
                <span className="text-slate-500">Downgrade prob</span>
                <span className={`font-bold ${downgradeProbs[agency] > 0.7 ? 'text-red-600' : downgradeProbs[agency] > 0.4 ? 'text-amber-600' : 'text-emerald-600'}`}>{(downgradeProbs[agency]*100).toFixed(1)}%</span>
              </div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
          {(['sp','moodys','fitch'] as const).map(ag => (
            <DowngradeGauge key={ag} probability={downgradeProbs[ag]} />
          ))}
        </div>

        <div className="mt-4">
          <SensitivityTable inputs={localInputs} baseScores={localScores} getRating={scoreToRating} />
        </div>

        <div className="mt-4 flex flex-wrap gap-2 text-xs">
          <span className="px-3 py-1 rounded-full bg-white/60 border border-white/40 text-slate-600 backdrop-blur-md">Formula: weighted sum — debt 30-35%, fiscal 25-30%, growth 20-25%, reserves 15-20%</span>
          <span className="px-3 py-1 rounded-full bg-white/60 border border-white/40 text-slate-600 backdrop-blur-md">Notch map: 100→AAA, 0→D ≈ 4.5 pts per notch</span>
          <span className="px-3 py-1 rounded-full bg-white/60 border border-white/40 text-slate-600 backdrop-blur-md">Downgrade p = logistic(currentScore - modelScore)</span>
        </div>
      </div>

      {/* Shock Inputs */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-3">Apply Economic Shocks (API Simulation)</h2>
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
