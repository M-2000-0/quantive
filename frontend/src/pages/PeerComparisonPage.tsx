import { useState, useEffect, useMemo } from 'react';
import { api } from '../api';
import AppShell from '../components/layout/AppShell';
import Card, { CardHeader } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
} from 'recharts';

interface CountryProfile {
  code: string;
  name: string;
  region: string;
  ratings: { sp: string; moody: string; fitch: string; outlook: string; investment_grade: boolean; risk_tier: string };
  debt_metrics: { debt_to_gdp: number; interest_to_revenue: number; debt_service_to_revenue: number };
  economy: { gdp_nominal_trillions: number; gdp_growth_pct: number; inflation_pct: number; unemployment_pct: number };
  fiscal: { fiscal_balance_pct: number; revenue_to_gdp: number };
  external: { current_account_pct: number; foreign_held_pct: number };
  debt_management: { avg_maturity_years: number; avg_coupon_pct: number; currency: string };
  demographics: { population_millions: number };
  groups: string[];
}

// ── Mock IMF / World Bank peers (WEO Oct 2024, IDS 2024) ───────────────
interface PeerMetrics {
  code: string;
  name: string;
  flag: string;
  debtToGDP: number;
  avgMaturity: number;
  fxShare: number;
  avgCost: number;
  rating: string;
  gdpGrowth: number;
}

const PEER_BENCHMARKS: PeerMetrics[] = [
  { code: 'US', name: 'United States', flag: '🇺🇸', debtToGDP: 123.3, avgMaturity: 6.0, fxShare: 0.5, avgCost: 3.28, rating: 'AA+', gdpGrowth: 2.8 },
  { code: 'DE', name: 'Germany', flag: '🇩🇪', debtToGDP: 64.3, avgMaturity: 7.3, fxShare: 2.1, avgCost: 2.08, rating: 'AAA', gdpGrowth: 0.2 },
  { code: 'FR', name: 'France', flag: '🇫🇷', debtToGDP: 111.4, avgMaturity: 8.5, fxShare: 2.8, avgCost: 2.42, rating: 'AA-', gdpGrowth: 0.9 },
  { code: 'JP', name: 'Japan', flag: '🇯🇵', debtToGDP: 255.2, avgMaturity: 8.9, fxShare: 8.4, avgCost: 0.88, rating: 'A+', gdpGrowth: 1.0 },
  { code: 'UK', name: 'United Kingdom', flag: '🇬🇧', debtToGDP: 101.3, avgMaturity: 14.2, fxShare: 4.9, avgCost: 3.15, rating: 'AA-', gdpGrowth: 0.5 },
  { code: 'IT', name: 'Italy', flag: '🇮🇹', debtToGDP: 140.5, avgMaturity: 7.0, fxShare: 2.3, avgCost: 3.02, rating: 'BBB', gdpGrowth: 0.7 },
  { code: 'ES', name: 'Spain', flag: '🇪🇸', debtToGDP: 107.7, avgMaturity: 8.0, fxShare: 2.6, avgCost: 2.68, rating: 'A', gdpGrowth: 2.1 },
];

function rankFor(metric: keyof PeerMetrics, value: number, lowerIsBetter: boolean): number {
  const sorted = [...PEER_BENCHMARKS].sort((a, b) => {
    const av = a[metric] as number;
    const bv = b[metric] as number;
    return lowerIsBetter ? av - bv : bv - av;
  });
  const idx = sorted.findIndex(p => (p[metric] as number) === value);
  return idx >= 0 ? idx + 1 : 4;
}

function percentileFromRank(rank: number, n: number): number {
  if (n <= 1) return 100;
  return Math.round(((n - rank) / (n - 1)) * 100);
}

function RankBadge({ rank }: { rank: number }) {
  const styles: Record<number, string> = {
    1: 'bg-gradient-to-br from-amber-400 to-yellow-600 text-white border-amber-300 shadow-md',
    2: 'bg-gradient-to-br from-slate-300 to-slate-500 text-white border-slate-200 shadow',
    3: 'bg-gradient-to-br from-orange-400 to-amber-700 text-white border-orange-300 shadow',
  };
  const cls = styles[rank] || 'bg-white/60 text-slate-600 border-white/50';
  return (
    <span className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-[11px] font-extrabold border backdrop-blur-md ${cls}`}>
      {rank === 1 ? '1' : rank === 2 ? '2' : rank === 3 ? '3' : `${rank}`}
    </span>
  );
}

function MetricGlassCard({ label, value, unit, rank, percentile, lowerIsBetter, best, median, sovereign }: {
  label: string; value: number; unit: string; rank: number; percentile: number; lowerIsBetter: boolean; best: number; median: number; sovereign: number;
}) {
  const gapVsBest = value - best;
  const gapVsMedian = value - median;
  const isAheadOfMedian = lowerIsBetter ? gapVsMedian < 0 : gapVsMedian > 0;
  return (
    <div className="glass-card p-4 relative overflow-hidden">
      <div className="absolute -top-10 -right-10 w-28 h-28 bg-gradient-to-br from-blue-400/10 to-violet-400/10 rounded-full blur-2xl" />
      <div className="flex items-start justify-between gap-2 relative">
        <div>
          <p className="text-[11px] font-bold tracking-widest uppercase text-slate-500">{label}</p>
          <p className="text-2xl font-bold tracking-tight text-slate-900 mt-1 tabular-nums">{value.toFixed(value >= 100 ? 1 : 2)}<span className="text-sm font-semibold text-slate-500 ml-1">{unit}</span></p>
          <p className="text-[11px] text-slate-500 mt-1">Median {median.toFixed(1)}{unit} · Best {best.toFixed(1)}{unit}</p>
        </div>
        <RankBadge rank={rank} />
      </div>
      <div className="mt-3 flex items-center gap-2">
        <div className="flex-1 h-1.5 rounded-full bg-slate-200/60 overflow-hidden">
          <div className="h-full rounded-full transition-all" style={{ width: `${percentile}%`, background: percentile >= 60 ? 'linear-gradient(90deg,#22c55e,#10b981)' : percentile >= 40 ? 'linear-gradient(90deg,#eab308,#f59e0b)' : 'linear-gradient(90deg,#ef4444,#f97316)' }} />
        </div>
        <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full border backdrop-blur-md ${percentile >= 60 ? 'bg-emerald-500/10 text-emerald-700 border-emerald-500/20' : percentile >= 35 ? 'bg-amber-500/10 text-amber-700 border-amber-500/20' : 'bg-red-500/10 text-red-700 border-red-500/20'}`}>{percentile}th pct</span>
      </div>
      <div className="mt-2 flex gap-1.5 flex-wrap">
        <Badge variant={isAheadOfMedian ? 'success' : 'danger'}>{isAheadOfMedian ? 'Ahead' : 'Behind'} median by {Math.abs(gapVsMedian).toFixed(1)}{unit}</Badge>
        <span className="text-[11px] text-slate-400">vs best {gapVsBest > 0 ? '+' : ''}{gapVsBest.toFixed(1)}{unit}</span>
        {sovereign !== value && <span className="text-[11px] text-slate-400">· Sovereign {sovereign.toFixed(1)}{unit}</span>}
      </div>
    </div>
  );
}

const REGIONS = ['all', 'north_america', 'europe', 'asia_pacific', 'latin_america', 'middle_east', 'africa'];
const GROUPS = ['all', 'g7', 'g20', 'oecd', 'brics', 'eu', 'nato'];

export default function PeerComparisonPage() {
  const [countries, setCountries] = useState<CountryProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedRegion, setSelectedRegion] = useState('all');
  const [selectedGroup, setSelectedGroup] = useState('all');
  const [sortBy, setSortBy] = useState('debt_to_gdp');
  const [highlightCode, setHighlightCode] = useState('US');
  const [globalStats, setGlobalStats] = useState<{ investment_grade?: number; high_yield?: number; total_countries?: number } | null>(null);
  const [sovereignCode, setSovereignCode] = useState('US');

  useEffect(() => {
    Promise.all([
      api.countries.list({}).then(r => r.countries as unknown as CountryProfile[]).catch(() => [] as CountryProfile[]),
      api.countries.stats().catch(() => null),
    ]).then(([c, s]) => {
      setCountries(c);
      setGlobalStats(s as unknown as { investment_grade?: number; total_countries?: number } | null);
    }).finally(() => setLoading(false));
  }, []);

  const filtered = countries
    .filter(c => selectedRegion === 'all' || c.region === selectedRegion)
    .filter(c => selectedGroup === 'all' || c.groups.includes(selectedGroup))
    .sort((a, b) => {
      if (sortBy === 'debt_to_gdp') return b.debt_metrics.debt_to_gdp - a.debt_metrics.debt_to_gdp;
      if (sortBy === 'gdp_growth') return b.economy.gdp_growth_pct - a.economy.gdp_growth_pct;
      if (sortBy === 'rating') {
        const order = ['AAA', 'AA+', 'AA', 'AA-', 'A+', 'A', 'A-', 'BBB+', 'BBB', 'BBB-', 'BB+', 'BB', 'BB-', 'B+'];
        return order.indexOf(a.ratings.sp) - order.indexOf(b.ratings.sp);
      }
      return b.economy.gdp_nominal_trillions - a.economy.gdp_nominal_trillions;
    });

  const sovereign = useMemo(() => PEER_BENCHMARKS.find(p => p.code === sovereignCode) || PEER_BENCHMARKS[0], [sovereignCode]);

  // ranking helpers
  const n = PEER_BENCHMARKS.length;

  const rankDebt = rankFor('debtToGDP', sovereign.debtToGDP, true);
  const rankMat = rankFor('avgMaturity', sovereign.avgMaturity, false);
  const rankFx = rankFor('fxShare', sovereign.fxShare, true);
  const rankCost = rankFor('avgCost', sovereign.avgCost, true);

  const pctDebt = percentileFromRank(rankDebt, n);
  const pctMat = percentileFromRank(rankMat, n);
  const pctFx = percentileFromRank(rankFx, n);
  const pctCost = percentileFromRank(rankCost, n);

  const medianDebt = [...PEER_BENCHMARKS].map(p=>p.debtToGDP).sort((a,b)=>a-b)[Math.floor(n/2)];
  const medianMat = [...PEER_BENCHMARKS].map(p=>p.avgMaturity).sort((a,b)=>a-b)[Math.floor(n/2)];
  const medianFx = [...PEER_BENCHMARKS].map(p=>p.fxShare).sort((a,b)=>a-b)[Math.floor(n/2)];
  const medianCost = [...PEER_BENCHMARKS].map(p=>p.avgCost).sort((a,b)=>a-b)[Math.floor(n/2)];
  const bestDebt = Math.min(...PEER_BENCHMARKS.map(p=>p.debtToGDP));
  const bestMat = Math.max(...PEER_BENCHMARKS.map(p=>p.avgMaturity));
  const bestFx = Math.min(...PEER_BENCHMARKS.map(p=>p.fxShare));
  const bestCost = Math.min(...PEER_BENCHMARKS.map(p=>p.avgCost));

  // radar normalization: higher = better (0..10)
  const radarData = useMemo(() => {
    const maxDebt = Math.max(...PEER_BENCHMARKS.map(p=>p.debtToGDP));
    const minDebt = Math.min(...PEER_BENCHMARKS.map(p=>p.debtToGDP));
    const maxMat = Math.max(...PEER_BENCHMARKS.map(p=>p.avgMaturity));
    const minMat = Math.min(...PEER_BENCHMARKS.map(p=>p.avgMaturity));
    const maxFx = Math.max(...PEER_BENCHMARKS.map(p=>p.fxShare));
    const minFx = Math.min(...PEER_BENCHMARKS.map(p=>p.fxShare));
    const maxCost = Math.max(...PEER_BENCHMARKS.map(p=>p.avgCost));
    const minCost = Math.min(...PEER_BENCHMARKS.map(p=>p.avgCost));
    const normInv = (v:number,min:number,max:number)=> max===min?5: 10 - ((v-min)/(max-min))*9;
    const norm = (v:number,min:number,max:number)=> max===min?5: 1 + ((v-min)/(max-min))*9;
    const mk = (p:PeerMetrics)=>[
      { subject: 'Low Debt', A: normInv(p.debtToGDP,minDebt,maxDebt), fullMark: 10 },
      { subject: 'Maturity', A: norm(p.avgMaturity,minMat,maxMat), fullMark: 10 },
      { subject: 'Low FX', A: normInv(p.fxShare,minFx,maxFx), fullMark: 10 },
      { subject: 'Low Cost', A: normInv(p.avgCost,minCost,maxCost), fullMark: 10 },
    ];
    // merge sovereign vs median vs best
    const medianPeer: PeerMetrics = {
      code: 'MED', name: 'Median', flag: '⬥',
      debtToGDP: medianDebt, avgMaturity: medianMat, fxShare: medianFx, avgCost: medianCost,
      rating: '—', gdpGrowth: 0,
    };
    const bestPeer: PeerMetrics = {
      code: 'BEST', name: 'Best-in-class', flag: '★',
      debtToGDP: bestDebt, avgMaturity: bestMat, fxShare: bestFx, avgCost: bestCost,
      rating: '—', gdpGrowth: 0,
    };
    const s = mk(sovereign);
    const m = mk(medianPeer);
    const b = mk(bestPeer);
    return s.map((row,i)=>({ subject: row.subject, sovereign: row.A, median: m[i].A, best: b[i].A, fullMark: 10 }));
  }, [sovereign, medianDebt, medianMat, medianFx, medianCost, bestDebt, bestMat, bestFx, bestCost]);

  // bar datasets
  const debtChartData = [...PEER_BENCHMARKS].sort((a,b)=>b.debtToGDP-a.debtToGDP).map(p=>({ name: p.code, debt: p.debtToGDP, highlight: p.code===sovereign.code }));
  const maturityChartData = [...PEER_BENCHMARKS].sort((a,b)=>b.avgMaturity-a.avgMaturity).map(p=>({ name: p.code, mat: p.avgMaturity, highlight: p.code===sovereign.code }));
  const fxChartData = [...PEER_BENCHMARKS].sort((a,b)=>b.fxShare-a.fxShare).map(p=>({ name: p.code, fx: p.fxShare, highlight: p.code===sovereign.code }));
  const costChartData = [...PEER_BENCHMARKS].sort((a,b)=>b.avgCost-a.avgCost).map(p=>({ name: p.code, cost: p.avgCost, highlight: p.code===sovereign.code }));

  const highlightCountry = countries.find(c => c.code === highlightCode);

  if (loading) return <AppShell><LoadingSpinner message="Loading country data..." /></AppShell>;

  const legacyDebtChartData = filtered.slice(0, 12).map(c => ({
    name: c.code,
    debt: c.debt_metrics.debt_to_gdp,
    highlight: c.code === highlightCode,
  }));
  const legacyGrowthChartData = filtered.slice(0, 12).map(c => ({
    name: c.code,
    growth: c.economy.gdp_growth_pct,
    highlight: c.code === highlightCode,
  }));
  const legacyRadarData = highlightCountry ? [
    { subject: 'GDP Growth', value: Math.min(highlightCountry.economy.gdp_growth_pct * 10, 10), fullMark: 10 },
    { subject: 'Fiscal Balance', value: Math.max(0, 10 + highlightCountry.fiscal.fiscal_balance_pct), fullMark: 10 },
    { subject: 'Low Inflation', value: Math.max(0, 10 - highlightCountry.economy.inflation_pct), fullMark: 10 },
    { subject: 'Maturity', value: Math.min(highlightCountry.debt_management.avg_maturity_years, 10), fullMark: 10 },
    { subject: 'Reserves', value: Math.min(highlightCountry.external.foreign_held_pct / 5, 10), fullMark: 10 },
  ] : [];

  return (
    <AppShell>
      <div className="px-4 lg:px-8 py-6 max-w-[1440px] mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">Sovereign Peer Comparison</h1>
            <p className="text-sm text-slate-500 mt-1">IMF WEO Oct 2024 · World Bank IDS 2024 · Mock benchmark — {filtered.length} countries · {(globalStats?.investment_grade ?? 0) as number} investment grade</p>
            <div className="mt-2 flex items-center gap-2 text-[11px] text-slate-400">
              <span className="px-2 py-1 rounded-full bg-white/50 border border-white/50 backdrop-blur">Source: IMF/World Bank (mock)</span>
              <span className="px-2 py-1 rounded-full bg-white/50 border border-white/50 backdrop-blur">6 peers vs sovereign</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs font-semibold text-slate-600">Sovereign</label>
            <select value={sovereignCode} onChange={e => setSovereignCode(e.target.value)} className="px-3 py-2 rounded-xl border border-white/60 bg-white/70 backdrop-blur-md text-sm font-medium shadow-sm">
              {PEER_BENCHMARKS.map(p => <option key={p.code} value={p.code}>{p.flag} {p.code} — {p.name}</option>)}
            </select>
          </div>
        </div>

        {/* ── Peer Benchmark Glass Cards ───────────────────────────────── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricGlassCard label="Debt / GDP" value={sovereign.debtToGDP} unit="%" rank={rankDebt} percentile={pctDebt} lowerIsBetter best={bestDebt} median={medianDebt} sovereign={sovereign.debtToGDP} />
          <MetricGlassCard label="Avg Maturity" value={sovereign.avgMaturity} unit="y" rank={rankMat} percentile={pctMat} lowerIsBetter={false} best={bestMat} median={medianMat} sovereign={sovereign.avgMaturity} />
          <MetricGlassCard label="FX Share" value={sovereign.fxShare} unit="%" rank={rankFx} percentile={pctFx} lowerIsBetter best={bestFx} median={medianFx} sovereign={sovereign.fxShare} />
          <MetricGlassCard label="Avg Cost" value={sovereign.avgCost} unit="%" rank={rankCost} percentile={pctCost} lowerIsBetter best={bestCost} median={medianCost} sovereign={sovereign.avgCost} />
        </div>

        {/* ── Radar + Bar comparisons ──────────────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card>
            <CardHeader title="Peer Radar — Sovereign vs Median vs Best" subtitle="Higher = better (inverse for debt, FX, cost)" />
            <ResponsiveContainer width="100%" height={280}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="rgba(148,163,184,0.25)" />
                <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11, fill: '#475569', fontWeight: 600 }} />
                <PolarRadiusAxis domain={[0, 10]} tick={false} axisLine={false} />
                <Radar name="Sovereign" dataKey="sovereign" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.22} strokeWidth={2.5} dot={{ r: 3, fill: '#3b82f6' }} />
                <Radar name="Median" dataKey="median" stroke="#94a3b8" fill="#94a3b8" fillOpacity={0.08} strokeWidth={1.5} strokeDasharray="6 4" />
                <Radar name="Best" dataKey="best" stroke="#10b981" fill="#10b981" fillOpacity={0.07} strokeWidth={1.5} strokeDasharray="4 4" />
                <Tooltip contentStyle={{ borderRadius: 12, border: '1px solid rgba(255,255,255,0.6)', background: 'rgba(255,255,255,0.9)', backdropFilter: 'blur(12px)' }} />
              </RadarChart>
            </ResponsiveContainer>
            <div className="flex gap-3 justify-center mt-2 text-[11px] font-semibold">
              <span className="inline-flex items-center gap-1"><span className="w-3 h-1.5 rounded bg-blue-500" /> Sovereign ({sovereign.code})</span>
              <span className="inline-flex items-center gap-1"><span className="w-3 h-1.5 rounded bg-slate-400" /> Median</span>
              <span className="inline-flex items-center gap-1"><span className="w-3 h-1.5 rounded bg-emerald-500" /> Best</span>
            </div>
          </Card>

          <Card>
            <CardHeader title="Debt-to-GDP" subtitle="Lower is stronger — percentile rank shown" />
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={debtChartData} layout="vertical" margin={{ left: 30, right: 16 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(226,232,240,0.8)" />
                <XAxis type="number" tick={{ fontSize: 11 }} unit="%" domain={[0, 270]} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fontWeight: 700 }} width={32} />
                <Tooltip formatter={(value) => [`${Number(value).toFixed(1)}%`, 'Debt/GDP']} contentStyle={{ borderRadius: 12, border: '1px solid rgba(255,255,255,0.6)', background: 'rgba(255,255,255,0.92)' }} />
                <Bar dataKey="debt" radius={[0, 8, 8, 0]}>
                  {debtChartData.map((d, i) => (
                    <Cell key={i} fill={d.highlight ? '#3b82f6' : d.debt > 120 ? '#ef4444' : d.debt > 90 ? '#f59e0b' : '#10b981'} stroke={d.highlight ? '#1d4ed8' : 'none'} strokeWidth={d.highlight ? 1.5 : 0} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>

          <Card>
            <CardHeader title="Avg Maturity vs Peers" subtitle="Longer = lower refinancing risk" />
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={maturityChartData} layout="vertical" margin={{ left: 30, right: 16 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(226,232,240,0.8)" />
                <XAxis type="number" tick={{ fontSize: 11 }} unit="y" />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fontWeight: 700 }} width={32} />
                <Tooltip formatter={(value) => [`${Number(value).toFixed(1)}y`, 'Maturity']} contentStyle={{ borderRadius: 12 }} />
                <Bar dataKey="mat" radius={[0, 8, 8, 0]}>
                  {maturityChartData.map((d, i) => (
                    <Cell key={i} fill={d.highlight ? '#3b82f6' : d.mat >= 10 ? '#10b981' : d.mat >= 7 ? '#0ea5e9' : '#f59e0b'} stroke={d.highlight ? '#1d4ed8' : 'none'} strokeWidth={d.highlight ? 1.5 : 0} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card>
            <CardHeader title="FX Share of Debt" subtitle="Lower FX = lower currency risk" />
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={fxChartData} layout="vertical" margin={{ left: 30 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(226,232,240,0.8)" />
                <XAxis type="number" tick={{ fontSize: 11 }} unit="%" />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fontWeight: 700 }} width={32} />
                <Tooltip formatter={(v) => [`${Number(v).toFixed(1)}%`, 'FX Share']} />
                <Bar dataKey="fx" radius={[0, 8, 8, 0]}>
                  {fxChartData.map((d, i) => (
                    <Cell key={i} fill={d.highlight ? '#3b82f6' : d.fx > 6 ? '#ef4444' : d.fx > 3 ? '#f59e0b' : '#10b981'} stroke={d.highlight ? '#1d4ed8' : 'none'} strokeWidth={d.highlight ? 1.5 : 0} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>
          <Card>
            <CardHeader title="Average Cost (coupon)" subtitle="Effective funding cost — mock IMF" />
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={costChartData} layout="vertical" margin={{ left: 30 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(226,232,240,0.8)" />
                <XAxis type="number" tick={{ fontSize: 11 }} unit="%" />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fontWeight: 700 }} width={32} />
                <Tooltip formatter={(v) => [`${Number(v).toFixed(2)}%`, 'Cost']} />
                <Bar dataKey="cost" radius={[0, 8, 8, 0]}>
                  {costChartData.map((d, i) => (
                    <Cell key={i} fill={d.highlight ? '#3b82f6' : d.cost > 3 ? '#ef4444' : d.cost > 2.2 ? '#f59e0b' : '#10b981'} stroke={d.highlight ? '#1d4ed8' : 'none'} strokeWidth={d.highlight ? 1.5 : 0} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>
          <Card>
            <CardHeader title="Gap Analysis — Where Sovereign Stands" subtitle={`Sovereign ${sovereign.code} vs 6 peers`} />
            <div className="space-y-3 text-sm">
              {[
                { label: 'Debt/GDP', val: sovereign.debtToGDP, med: medianDebt, best: bestDebt, lo: true, unit: '%' },
                { label: 'Avg Maturity', val: sovereign.avgMaturity, med: medianMat, best: bestMat, lo: false, unit: 'y' },
                { label: 'FX Share', val: sovereign.fxShare, med: medianFx, best: bestFx, lo: true, unit: '%' },
                { label: 'Avg Cost', val: sovereign.avgCost, med: medianCost, best: bestCost, lo: true, unit: '%' },
              ].map(row => {
                const vsMedian = row.val - row.med;
                const vsBest = row.val - row.best;
                const aheadMedian = row.lo ? vsMedian < 0 : vsMedian > 0;
                const aheadBest = row.lo ? vsBest <= 0.01 : vsBest >= -0.01;
                return (
                  <div key={row.label} className="flex items-center justify-between p-3 rounded-xl bg-white/40 backdrop-blur border border-white/40">
                    <div>
                      <p className="font-semibold text-slate-800 text-xs uppercase tracking-wide">{row.label}</p>
                      <p className="text-[11px] text-slate-500 mt-0.5">Sov {row.val.toFixed(1)}{row.unit} · Med {row.med.toFixed(1)}{row.unit} · Best {row.best.toFixed(1)}{row.unit}</p>
                    </div>
                    <div className="text-right">
                      <Badge variant={aheadBest ? 'success' : aheadMedian ? 'warning' : 'danger'}>
                        {aheadBest ? 'Best' : aheadMedian ? 'Above median' : 'Below median'}
                      </Badge>
                      <p className="text-[11px] text-slate-500 mt-1 tabular-nums">Δ median {vsMedian > 0 ? '+' : ''}{vsMedian.toFixed(1)}{row.unit} · Δ best {vsBest > 0 ? '+' : ''}{vsBest.toFixed(1)}{row.unit}</p>
                    </div>
                  </div>
                );
              })}
              <div className="rounded-xl bg-blue-500/10 border border-blue-500/20 p-3 text-xs leading-relaxed text-slate-700">
                <span className="font-bold text-blue-700">Interpretation:</span> {sovereign.code} ranks #{rankDebt} on debt, #{rankMat} on maturity, #{rankFx} on FX, #{rankCost} on cost among 7. Percentiles {pctDebt}/{pctMat}/{pctFx}/{pctCost}. Focus refinancing risk if maturity in lower quartile; FX &lt; 5% is investment-grade norm.
              </div>
            </div>
          </Card>
        </div>

        {/* ── Peer Table with rank badges & percentile ─────────────────── */}
        <Card padding={false}>
          <div className="p-5 flex items-center justify-between">
            <div>
              <h3 className="text-[15px] font-semibold tracking-tight text-slate-900">Peer Benchmark Table — Mock IMF/World Bank</h3>
              <p className="text-[13px] text-slate-500">Rank 1 = best (lowest debt/FX/cost, longest maturity). Percentile 100 = top.</p>
            </div>
            <Badge variant="info">7 economies</Badge>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-y border-white/40 bg-white/30 backdrop-blur-xl">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Peer</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Rating</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Debt/GDP</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Maturity</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 uppercase">FX Share</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Cost</th>
                  <th className="text-center px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Rank (Debt)</th>
                  <th className="text-center px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Rank (Mat)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/25">
                {[...PEER_BENCHMARKS].sort((a,b)=>a.code.localeCompare(b.code)).map(p => {
                  const rd = rankFor('debtToGDP', p.debtToGDP, true);
                  const rm = rankFor('avgMaturity', p.avgMaturity, false);
                  const isSov = p.code === sovereign.code;
                  return (
                    <tr key={p.code} className={`transition-colors ${isSov ? 'bg-blue-500/10' : 'hover:bg-white/40'}`}>
                      <td className="px-4 py-3">
                        <span className="inline-flex items-center gap-2">
                          <span className="text-base">{p.flag}</span>
                          <span className="font-bold text-slate-900">{p.code}</span>
                          <span className="text-slate-500 hidden sm:inline">{p.name}</span>
                          {isSov && <Badge variant="info">Sovereign</Badge>}
                        </span>
                      </td>
                      <td className="px-4 py-3"><Badge variant={['AAA','AA+'].includes(p.rating) ? 'success' : p.rating.startsWith('A') ? 'info' : 'warning'}>{p.rating}</Badge></td>
                      <td className="px-4 py-3 text-right font-mono font-semibold">{p.debtToGDP.toFixed(1)}%</td>
                      <td className="px-4 py-3 text-right font-mono">{p.avgMaturity.toFixed(1)}y</td>
                      <td className="px-4 py-3 text-right font-mono">{p.fxShare.toFixed(1)}%</td>
                      <td className="px-4 py-3 text-right font-mono">{p.avgCost.toFixed(2)}%</td>
                      <td className="px-4 py-3 text-center"><RankBadge rank={rd} /> <span className="text-[11px] text-slate-500 ml-1">{percentileFromRank(rd,n)}th</span></td>
                      <td className="px-4 py-3 text-center"><RankBadge rank={rm} /> <span className="text-[11px] text-slate-500 ml-1">{percentileFromRank(rm,n)}th</span></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="px-4 py-3 text-[11px] text-slate-400 border-t border-white/30 bg-white/20 backdrop-blur">
            Mock provenance: IMF World Economic Outlook (Oct 2024) debt/GDP, World Bank International Debt Statistics FX composition, OECD maturity & coupon averages. For demo only — not live market data.
          </div>
        </Card>

        {/* ── Legacy global comparison (optional, kept for parity) ─────── */}
        <div className="flex items-center justify-between pt-2">
          <h2 className="text-sm font-bold tracking-widest uppercase text-slate-500">Global Country Explorer (live API)</h2>
          <span className="text-xs text-slate-400">{filtered.length} countries</span>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3">
          <select value={selectedRegion} onChange={e => setSelectedRegion(e.target.value)}
            className="px-3 py-2 border border-white/60 bg-white/70 backdrop-blur-md rounded-xl text-sm shadow-sm">
            {REGIONS.map(r => <option key={r} value={r}>{r === 'all' ? 'All Regions' : r.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</option>)}
          </select>
          <select value={selectedGroup} onChange={e => setSelectedGroup(e.target.value)}
            className="px-3 py-2 border border-white/60 bg-white/70 backdrop-blur-md rounded-xl text-sm shadow-sm">
            {GROUPS.map(g => <option key={g} value={g}>{g === 'all' ? 'All Groups' : g.toUpperCase()}</option>)}
          </select>
          <select value={sortBy} onChange={e => setSortBy(e.target.value)}
            className="px-3 py-2 border border-white/60 bg-white/70 backdrop-blur-md rounded-xl text-sm shadow-sm">
            <option value="debt_to_gdp">Sort by Debt/GDP</option>
            <option value="gdp_growth">Sort by GDP Growth</option>
            <option value="rating">Sort by Credit Rating</option>
            <option value="gdp">Sort by GDP Size</option>
          </select>
          <select value={highlightCode} onChange={e => setHighlightCode(e.target.value)}
            className="px-3 py-2 border border-white/60 bg-white/70 backdrop-blur-md rounded-xl text-sm shadow-sm">
            {countries.map(c => <option key={c.code} value={c.code}>{c.name}</option>)}
          </select>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card>
            <CardHeader title="Debt-to-GDP Comparison" subtitle="Higher = more leveraged" />
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={legacyDebtChartData} layout="vertical" margin={{ left: 30 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(226,232,240,0.8)" />
                <XAxis type="number" tick={{ fontSize: 11 }} unit="%" />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={30} />
                <Tooltip formatter={(value) => [`${Number(value).toFixed(0)}%`, 'Debt/GDP']} />
                <Bar dataKey="debt" radius={[0, 4, 4, 0]}>
                  {legacyDebtChartData.map((d, i) => (
                    <Cell key={i} fill={d.highlight ? '#3b82f6' : d.debt > 100 ? '#ef4444' : d.debt > 60 ? '#f59e0b' : '#10b981'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>

          <Card>
            <CardHeader title="GDP Growth Comparison" subtitle="Higher = faster growing" />
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={legacyGrowthChartData} layout="vertical" margin={{ left: 30 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(226,232,240,0.8)" />
                <XAxis type="number" tick={{ fontSize: 11 }} unit="%" />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={30} />
                <Tooltip formatter={(value) => [`${Number(value).toFixed(1)}%`, 'GDP Growth']} />
                <Bar dataKey="growth" radius={[0, 4, 4, 0]}>
                  {legacyGrowthChartData.map((d, i) => (
                    <Cell key={i} fill={d.highlight ? '#3b82f6' : d.growth > 4 ? '#10b981' : d.growth > 2 ? '#eab308' : '#ef4444'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>

          {highlightCountry && (
            <Card>
              <CardHeader title={`${highlightCountry.name} Profile`} subtitle={highlightCountry.ratings.sp} />
              <div className="flex justify-center mb-4">
                <ResponsiveContainer width="100%" height={180}>
                  <RadarChart data={legacyRadarData}>
                    <PolarGrid stroke="rgba(226,232,240,0.8)" />
                    <PolarAngleAxis dataKey="subject" tick={{ fontSize: 9, fill: '#64748b' }} />
                    <PolarRadiusAxis domain={[0, 10]} tick={false} />
                    <Radar dataKey="value" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.2} strokeWidth={2} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
              <div className="space-y-1 text-xs">
                <div className="flex justify-between"><span className="text-slate-500">GDP</span><span className="font-semibold">${highlightCountry.economy.gdp_nominal_trillions}T</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Debt/GDP</span><span className="font-semibold">{highlightCountry.debt_metrics.debt_to_gdp}%</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Growth</span><span className="font-semibold">{highlightCountry.economy.gdp_growth_pct}%</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Inflation</span><span className="font-semibold">{highlightCountry.economy.inflation_pct}%</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Avg Maturity</span><span className="font-semibold">{highlightCountry.debt_management.avg_maturity_years}y</span></div>
              </div>
            </Card>
          )}
        </div>

        {/* Table */}
        <Card padding={false}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/40 bg-white/30 backdrop-blur-xl">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Country</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Rating</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Debt/GDP</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 uppercase">GDP ($T)</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Growth</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Inflation</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Fiscal</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-slate-500 uppercase">Avg Mat.</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/25">
                {filtered.map((c: CountryProfile) => (
                  <tr key={c.code} onClick={() => setHighlightCode(c.code)}
                    className={`cursor-pointer transition-colors ${c.code === highlightCode ? 'bg-blue-500/10' : 'hover:bg-white/40'}`}>
                    <td className="px-4 py-3">
                      <span className="font-semibold text-slate-900">{c.code}</span>
                      <span className="text-slate-400 ml-2">{c.name}</span>
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={c.ratings.investment_grade ? 'success' : 'danger'}>{c.ratings.sp}</Badge>
                    </td>
                    <td className="px-4 py-3 text-right font-mono">{c.debt_metrics.debt_to_gdp}%</td>
                    <td className="px-4 py-3 text-right font-mono">${c.economy.gdp_nominal_trillions}T</td>
                    <td className="px-4 py-3 text-right font-mono">{c.economy.gdp_growth_pct}%</td>
                    <td className="px-4 py-3 text-right font-mono">{c.economy.inflation_pct}%</td>
                    <td className="px-4 py-3 text-right font-mono">{c.fiscal.fiscal_balance_pct}%</td>
                    <td className="px-4 py-3 text-right font-mono">{c.debt_management.avg_maturity_years}y</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </AppShell>
  );
}
