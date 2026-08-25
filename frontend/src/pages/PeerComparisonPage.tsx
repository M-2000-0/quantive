import { useState, useEffect } from 'react';
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

  useEffect(() => {
    Promise.all([
      api.countries.list({}).then(r => r.countries as unknown as CountryProfile[]),
      api.countries.stats(),
    ]).then(([c, s]) => {
      setCountries(c);
      setGlobalStats(s);
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

  if (loading) return <AppShell><LoadingSpinner message="Loading country data..." /></AppShell>;

  const debtChartData = filtered.slice(0, 12).map(c => ({
    name: c.code,
    debt: c.debt_metrics.debt_to_gdp,
    highlight: c.code === highlightCode,
  }));

  const growthChartData = filtered.slice(0, 12).map(c => ({
    name: c.code,
    growth: c.economy.gdp_growth_pct,
    highlight: c.code === highlightCode,
  }));

  const highlightCountry = countries.find(c => c.code === highlightCode);
  const radarData = highlightCountry ? [
    { subject: 'GDP Growth', value: Math.min(highlightCountry.economy.gdp_growth_pct * 10, 10), fullMark: 10 },
    { subject: 'Fiscal Balance', value: Math.max(0, 10 + highlightCountry.fiscal.fiscal_balance_pct), fullMark: 10 },
    { subject: 'Low Inflation', value: Math.max(0, 10 - highlightCountry.economy.inflation_pct), fullMark: 10 },
    { subject: 'Maturity', value: Math.min(highlightCountry.debt_management.avg_maturity_years, 10), fullMark: 10 },
    { subject: 'Reserves', value: Math.min(highlightCountry.external.foreign_held_pct / 5, 10), fullMark: 10 },
  ] : [];

  return (
    <AppShell>
      <div className="px-8 py-6 max-w-[1440px] mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Sovereign Peer Comparison</h1>
            <p className="text-sm text-slate-500 mt-0.5">{filtered.length} countries · {(globalStats?.investment_grade ?? 0) as number} investment grade</p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3 mb-6">
          <select value={selectedRegion} onChange={e => setSelectedRegion(e.target.value)}
            className="px-3 py-1.5 border border-slate-300 rounded-md text-sm">
            {REGIONS.map(r => <option key={r} value={r}>{r === 'all' ? 'All Regions' : r.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</option>)}
          </select>
          <select value={selectedGroup} onChange={e => setSelectedGroup(e.target.value)}
            className="px-3 py-1.5 border border-slate-300 rounded-md text-sm">
            {GROUPS.map(g => <option key={g} value={g}>{g === 'all' ? 'All Groups' : g.toUpperCase()}</option>)}
          </select>
          <select value={sortBy} onChange={e => setSortBy(e.target.value)}
            className="px-3 py-1.5 border border-slate-300 rounded-md text-sm">
            <option value="debt_to_gdp">Sort by Debt/GDP</option>
            <option value="gdp_growth">Sort by GDP Growth</option>
            <option value="rating">Sort by Credit Rating</option>
            <option value="gdp">Sort by GDP Size</option>
          </select>
          <select value={highlightCode} onChange={e => setHighlightCode(e.target.value)}
            className="px-3 py-1.5 border border-slate-300 rounded-md text-sm">
            {countries.map(c => <option key={c.code} value={c.code}>{c.name}</option>)}
          </select>
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          <Card>
            <CardHeader title="Debt-to-GDP Comparison" subtitle="Higher = more leveraged" />
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={debtChartData} layout="vertical" margin={{ left: 30 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis type="number" tick={{ fontSize: 11 }} unit="%" />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={30} />
                <Tooltip formatter={(value) => [`${Number(value).toFixed(0)}%`, 'Debt/GDP']} />
                <Bar dataKey="debt" radius={[0, 4, 4, 0]}>
                  {debtChartData.map((d, i) => (
                    <Cell key={i} fill={d.highlight ? '#3b82f6' : d.debt > 100 ? '#ef4444' : d.debt > 60 ? '#f59e0b' : '#10b981'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>

          <Card>
            <CardHeader title="GDP Growth Comparison" subtitle="Higher = faster growing" />
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={growthChartData} layout="vertical" margin={{ left: 30 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis type="number" tick={{ fontSize: 11 }} unit="%" />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={30} />
                <Tooltip formatter={(value) => [`${Number(value).toFixed(1)}%`, 'GDP Growth']} />
                <Bar dataKey="growth" radius={[0, 4, 4, 0]}>
                  {growthChartData.map((d, i) => (
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
                <ResponsiveContainer width="100%" height={200}>
                  <RadarChart data={radarData}>
                    <PolarGrid stroke="#e2e8f0" />
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
                    className={`cursor-pointer transition-colors ${c.code === highlightCode ? 'bg-blue-50' : 'hover:bg-white/40'}`}>
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
