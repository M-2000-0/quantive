import { useState, useEffect, useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Cell } from 'recharts';
import { api } from '../api';
import AppShell from '../components/layout/AppShell';
import Card, { CardHeader } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import LoadingSpinner from '../components/ui/LoadingSpinner';

type ESGTag = 'green' | 'social' | 'sustainability' | 'conventional';

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

interface EnrichedInstrument extends InstrumentScore {
  esg_tag: ESGTag;
  greenium_bps: number;
  taxonomy_alignment_pct: number;
  annual_greenium_saving: number;
}

function deriveTag(inst: InstrumentScore, idx: number): ESGTag {
  if (inst.is_green_eligible) {
    const m = idx % 3;
    if (m === 0) return 'green';
    if (m === 1) return 'sustainability';
    return 'social';
  }
  const m = idx % 5;
  if (m === 0) return 'green';
  if (m === 1) return 'social';
  if (m === 2) return 'sustainability';
  return 'conventional';
}

function deriveGreenium(tag: ESGTag, idx: number): number {
  if (tag === 'green') return -(8 + (idx % 8)); // -8 to -15
  if (tag === 'social') return -(5 + (idx % 6)); // -5 to -10
  if (tag === 'sustainability') return -(7 + (idx % 6)); // -7 to -12
  return 0;
}

function deriveTaxonomy(tag: ESGTag, idx: number, carbonRisk: number): number {
  let base: number;
  if (tag === 'green') base = 78 + (idx % 18); // 78-95
  else if (tag === 'sustainability') base = 70 + (idx % 21); // 70-90
  else if (tag === 'social') base = 45 + (idx % 26); // 45-70
  else base = 12 + (idx % 19); // 12-30
  // slight penalty for high carbon
  const adj = Math.max(0, base - Math.round(carbonRisk * 0.08));
  return Math.max(5, Math.min(98, adj));
}

const TAG_META: Record<ESGTag, { label: string; color: string; bg: string; dot: string }> = {
  green: { label: 'Green', color: '#059669', bg: 'bg-emerald-500/12 text-emerald-700 border-emerald-500/20', dot: '#10b981' },
  social: { label: 'Social', color: '#2563eb', bg: 'bg-blue-500/12 text-blue-700 border-blue-500/20', dot: '#3b82f6' },
  sustainability: { label: 'Sustainability', color: '#7c3aed', bg: 'bg-violet-500/12 text-violet-700 border-violet-500/20', dot: '#8b5cf6' },
  conventional: { label: 'Conventional', color: '#64748b', bg: 'bg-slate-500/10 text-slate-600 border-slate-300/40', dot: '#94a3b8' },
};

export default function ESGPage() {
  const [portfolios, setPortfolios] = useState<Array<{ id: string; name: string }>>([]);
  const [selectedPortfolio, setSelectedPortfolio] = useState('');
  const [countryCode, setCountryCode] = useState('US');
  const [data, setData] = useState<ESGData | null>(null);
  const [countryScores, setCountryScores] = useState<Record<string, { environmental: number; social: number; governance: number; overall: number }>>({});
  const [loading, setLoading] = useState(false);
  const [filterTag, setFilterTag] = useState<ESGTag | 'all'>('all');

  useEffect(() => {
    api.portfolios.list().then((res: unknown) => {
      const d = res as { data?: Array<{ id: string; name: string }> };
      const list = d?.data || [];
      setPortfolios(list);
      if (list.length > 0) setSelectedPortfolio(list[0].id);
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

  const enriched: EnrichedInstrument[] = useMemo(() => {
    if (!data) return [];
    return data.instrument_scores.map((inst, idx) => {
      const tag = deriveTag(inst, idx);
      const greenium_bps = deriveGreenium(tag, idx);
      const taxonomy_alignment_pct = deriveTaxonomy(tag, idx, inst.carbon_risk_score);
      const annual_greenium_saving = tag === 'conventional' ? 0 : (inst.principal * (-greenium_bps) / 10000);
      return { ...inst, esg_tag: tag, greenium_bps, taxonomy_alignment_pct, annual_greenium_saving };
    });
  }, [data]);

  const filteredInstruments = useMemo(() => {
    if (filterTag === 'all') return enriched;
    return enriched.filter(e => e.esg_tag === filterTag);
  }, [enriched, filterTag]);

  const greenStats = useMemo(() => {
    if (enriched.length === 0) return null;
    const total = enriched.reduce((s, e) => s + e.principal, 0);
    const greenLike = enriched.filter(e => e.esg_tag !== 'conventional');
    const greenPrincipal = greenLike.reduce((s, e) => s + e.principal, 0);
    const greenShare = total ? (greenPrincipal / total) * 100 : 0;
    const saving = greenLike.reduce((s, e) => s + e.annual_greenium_saving, 0);
    const wAvgGreenium = greenPrincipal ? greenLike.reduce((s, e) => s + e.greenium_bps * e.principal, 0) / greenPrincipal : 0;
    const wTaxAvg = total ? enriched.reduce((s, e) => s + e.taxonomy_alignment_pct * e.principal, 0) / total : 0;
    const tagCounts = { green: 0, social: 0, sustainability: 0, conventional: 0 } as Record<ESGTag, number>;
    enriched.forEach(e => { tagCounts[e.esg_tag]++; });
    return { total, greenPrincipal, greenShare, saving, wAvgGreenium, wTaxAvg, tagCounts };
  }, [enriched]);

  // liquidation analysis: estimate days to liquidate
  const liquidation = useMemo(() => {
    return [...filteredInstruments].map(e => {
      const principalB = e.principal / 1e9;
      const days = Math.round(8 + (100 - e.taxonomy_alignment_pct) * 0.45 + e.carbon_risk_score * 0.12 + principalB * 0.35);
      const tier = days <= 18 ? 'Highly liquid' : days <= 28 ? 'Liquid' : days <= 38 ? 'Moderate' : 'Illiquid';
      return { ...e, days_to_liquidate: days, liquidity_tier: tier };
    }).sort((a, b) => a.days_to_liquidate - b.days_to_liquidate);
  }, [filteredInstruments]);

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

  const greeniumChartData = [...enriched].sort((a, b) => a.greenium_bps - b.greenium_bps).slice(0, 12).map(e => ({
    name: e.instrument_name.length > 18 ? e.instrument_name.slice(0, 18) + '…' : e.instrument_name,
    greenium: e.greenium_bps,
    tag: e.esg_tag,
    full: e.instrument_name,
  }));

  const taxonomyByTag = useMemo(() => {
    const groups: Record<string, { tag: ESGTag; avg: number; count: number }> = {};
    (['green', 'social', 'sustainability', 'conventional'] as ESGTag[]).forEach(t => {
      const arr = enriched.filter(e => e.esg_tag === t);
      const avg = arr.length ? arr.reduce((s, e) => s + e.taxonomy_alignment_pct, 0) / arr.length : 0;
      groups[t] = { tag: t, avg: Math.round(avg), count: arr.length };
    });
    return Object.values(groups);
  }, [enriched]);

  return (
    <AppShell>
      <div className="px-4 lg:px-8 py-6 max-w-[1440px] mx-auto space-y-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">ESG & Green Bond Analysis</h1>
            <p className="text-sm text-slate-500 mt-1">Climate-aware debt · Greenium pricing · EU taxonomy tagging</p>
            <div className="mt-2 flex gap-2 text-[11px]">
              <span className="px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-700 font-semibold backdrop-blur">Greenium -5 to -15 bps</span>
              <span className="px-2.5 py-1 rounded-full bg-violet-500/10 border border-violet-500/20 text-violet-700 font-semibold backdrop-blur">Taxonomy aligned</span>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="glass-card px-3 py-2 flex items-center gap-2">
              <label className="text-xs font-semibold text-slate-500">Country</label>
              <select value={countryCode} onChange={e => setCountryCode(e.target.value)} className="bg-transparent text-sm font-medium outline-none">
                {Object.keys(countryScores).length > 0
                  ? Object.keys(countryScores).sort().map(c => <option key={c} value={c}>{c}</option>)
                  : ['US', 'UK', 'DE', 'FR', 'JP', 'CN', 'IN', 'BR', 'CH', 'SE', 'NO'].map(c => <option key={c} value={c}>{c}</option>)
                }
              </select>
            </div>
            <div className="glass-card px-3 py-2 flex items-center gap-2">
              <label className="text-xs font-semibold text-slate-500">Portfolio</label>
              <select value={selectedPortfolio} onChange={e => setSelectedPortfolio(e.target.value)} className="bg-transparent text-sm font-medium outline-none min-w-[180px]">
                <option value="">Select portfolio...</option>
                {portfolios.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </div>
          </div>
        </div>

        {loading && <LoadingSpinner message="Analyzing ESG metrics..." />}

        {data && !loading && greenStats && (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="glass-card p-4">
                <p className="text-xs font-semibold tracking-widest uppercase text-slate-500">ESG Score</p>
                <p className={`text-2xl font-bold mt-1 ${data.summary.weighted_avg_esg > 60 ? 'text-emerald-600' : data.summary.weighted_avg_esg > 40 ? 'text-amber-600' : 'text-red-600'}`}>{data.summary.weighted_avg_esg}/100</p>
                <p className="text-[11px] text-slate-400 mt-1">Weighted avg</p>
              </div>
              <div className="glass-card p-4 border-emerald-200/60">
                <p className="text-xs font-semibold tracking-widest uppercase text-slate-500">Green Share</p>
                <p className="text-2xl font-bold mt-1 text-emerald-600">{greenStats.greenShare.toFixed(1)}%</p>
                <p className="text-[11px] text-slate-500 mt-1">${(greenStats.greenPrincipal / 1e9).toFixed(1)}B / ${(greenStats.total / 1e9).toFixed(1)}B</p>
              </div>
              <div className="glass-card p-4">
                <p className="text-xs font-semibold tracking-widest uppercase text-slate-500">Greenium Impact</p>
                <p className="text-2xl font-bold mt-1 text-violet-600">{greenStats.wAvgGreenium.toFixed(1)} bps</p>
                <p className="text-[11px] text-emerald-600 mt-1">Saving ${(greenStats.saving / 1e6).toFixed(1)}M / yr</p>
              </div>
              <div className="glass-card p-4">
                <p className="text-xs font-semibold tracking-widest uppercase text-slate-500">Taxonomy Avg</p>
                <p className="text-2xl font-bold mt-1 text-blue-600">{greenStats.wTaxAvg.toFixed(1)}%</p>
                <p className="text-[11px] text-slate-400 mt-1">EU alignment</p>
              </div>
              <div className="glass-card p-4">
                <p className="text-xs font-semibold tracking-widest uppercase text-slate-500">Climate VaR</p>
                <p className={`text-2xl font-bold mt-1 ${data.summary.climate_var < 0.02 ? 'text-emerald-600' : data.summary.climate_var < 0.03 ? 'text-amber-600' : 'text-red-600'}`}>{(data.summary.climate_var * 100).toFixed(1)}%</p>
                <p className="text-[11px] text-slate-400 mt-1">{data.summary.climate_risk_rating}</p>
              </div>
            </div>

            {/* Tag filter + taxonomy overview */}
            <div className="flex flex-wrap gap-2 items-center">
              <span className="text-xs font-bold tracking-widest uppercase text-slate-500">Filter by ESG tag:</span>
              {(['all', 'green', 'social', 'sustainability', 'conventional'] as const).map(t => (
                <button
                  key={t}
                  onClick={() => setFilterTag(t as ESGTag | 'all')}
                  className={`px-3.5 py-1.5 rounded-full text-xs font-bold border backdrop-blur transition-all ${filterTag === t ? 'bg-slate-900 text-white border-slate-900 shadow' : 'bg-white/60 text-slate-600 border-white/60 hover:bg-white/80'}`}
                >
                  {t === 'all' ? `All (${enriched.length})` : `${TAG_META[t as ESGTag].label} (${greenStats.tagCounts[t as ESGTag]})`}
                </button>
              ))}
              <span className="ml-auto text-[11px] text-slate-400">Showing {filteredInstruments.length} instruments · Taxonomy alignment % and greenium bps are instrument-level</span>
            </div>

            {/* Taxonomy + Greenium charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader title="Greenium Pricing by Instrument" subtitle="Negative bps = cost saving vs conventional (green/social cheaper)" />
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={greeniumChartData} layout="vertical" margin={{ left: 110, right: 16 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(226,232,240,0.7)" />
                    <XAxis type="number" tick={{ fontSize: 11 }} domain={[-16, 1]} tickFormatter={v => `${v}bps`} />
                    <YAxis type="category" dataKey="name" tick={{ fontSize: 10, fill: '#475569' }} width={110} />
                    <Tooltip
                      formatter={(value: unknown) => [`${Number(value)} bps`, 'Greenium']}
                      labelFormatter={(_label, payload) => (payload?.[0]?.payload?.full as string) || String(_label)}
                      contentStyle={{ borderRadius: 12, background: 'rgba(255,255,255,0.92)', border: '1px solid rgba(255,255,255,0.6)' }}
                    />
                    <Bar dataKey="greenium" radius={[0, 8, 8, 0]}>
                      {greeniumChartData.map((d, i) => (
                        <Cell key={i} fill={d.greenium === 0 ? '#cbd5e1' : TAG_META[d.tag as ESGTag].dot} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                <div className="mt-2 flex gap-3 text-[11px] font-semibold justify-center">
                  <span className="inline-flex items-center gap-1"><span className="w-3 h-2 rounded" style={{ background: '#10b981' }} /> Green -8 to -15</span>
                  <span className="inline-flex items-center gap-1"><span className="w-3 h-2 rounded" style={{ background: '#3b82f6' }} /> Social -5 to -10</span>
                  <span className="inline-flex items-center gap-1"><span className="w-3 h-2 rounded" style={{ background: '#8b5cf6' }} /> Sustainability -7 to -12</span>
                </div>
              </Card>

              <Card>
                <CardHeader title="Taxonomy Alignment by Tag" subtitle="EU taxonomy % — weighted, mock classification" />
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={taxonomyByTag} margin={{ left: 8, right: 16 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(226,232,240,0.7)" />
                    <XAxis dataKey="tag" tick={{ fontSize: 11, fontWeight: 700 }} tickFormatter={(v: string) => TAG_META[v as ESGTag].label} />
                    <YAxis tick={{ fontSize: 11 }} domain={[0, 100]} tickFormatter={v => `${v}%`} />
                    <Tooltip formatter={(v: unknown, _n, p) => [`${Number(v).toFixed(1)}%`, `${TAG_META[(p?.payload as { tag: ESGTag })?.tag as ESGTag]?.label || 'Avg'} alignment`]} contentStyle={{ borderRadius: 12 }} />
                    <Bar dataKey="avg" radius={[8, 8, 0, 0]}>
                      {taxonomyByTag.map((d, i) => (
                        <Cell key={i} fill={TAG_META[d.tag].dot} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                <div className="grid grid-cols-4 gap-2 mt-2 text-center">
                  {taxonomyByTag.map(d => (
                    <div key={d.tag} className="rounded-xl bg-white/40 backdrop-blur border border-white/40 p-2">
                      <p className="text-[11px] font-bold uppercase tracking-wide" style={{ color: TAG_META[d.tag].color }}>{TAG_META[d.tag].label}</p>
                      <p className="text-lg font-bold tabular-nums" style={{ color: TAG_META[d.tag].color }}>{d.avg.toFixed(0)}%</p>
                      <p className="text-[10px] text-slate-500">{d.count} instruments</p>
                    </div>
                  ))}
                </div>
              </Card>
            </div>

            {/* Country ESG Radar + Carbon Cost */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card>
                <CardHeader title={`Country ESG Profile — ${countryCode}`} subtitle="Environmental / Social / Governance (0-100)" />
                <ResponsiveContainer width="100%" height={280}>
                  <RadarChart data={radarData}>
                    <PolarGrid stroke="rgba(226,232,240,0.8)" />
                    <PolarAngleAxis dataKey="metric" tick={{ fontSize: 12, fill: '#475569', fontWeight: 600 }} />
                    <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fontSize: 10 }} />
                    <Radar name="ESG" dataKey="value" stroke="#10b981" fill="#10b981" fillOpacity={0.22} strokeWidth={2} />
                  </RadarChart>
                </ResponsiveContainer>
              </Card>

              <Card>
                <CardHeader title="Carbon Price Impact Scenarios" subtitle="Annual cost at different carbon prices" />
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={carbonData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(226,232,240,0.7)" />
                    <XAxis dataKey="scenario" tick={{ fontSize: 10 }} interval={0} angle={-14} textAnchor="end" height={60} />
                    <YAxis tickFormatter={v => `$${v}M`} tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(v: unknown) => `$${Number(v).toFixed(1)}M`} contentStyle={{ borderRadius: 12 }} />
                    <Bar dataKey="cost" name="Annual Cost" fill="#ef4444" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </Card>
            </div>

            {/* Instrument ESG Scores — enriched with greenium/taxonomy */}
            <Card padding={false}>
              <div className="p-5 flex items-center justify-between">
                <div>
                  <h3 className="text-[15px] font-semibold tracking-tight text-slate-900">Instrument ESG & Taxonomy</h3>
                  <p className="text-xs text-slate-500 mt-1">Greenium bps and taxonomy alignment are instrument-level mock. Filter via tags above.</p>
                </div>
                <Badge variant="info">{filteredInstruments.length} shown · {enriched.length} total</Badge>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="border-y border-white/40 bg-white/30 backdrop-blur-xl">
                      <th className="text-left py-3 px-3 text-xs font-semibold uppercase text-slate-500">Instrument</th>
                      <th className="text-right py-3 px-3 text-xs font-semibold uppercase text-slate-500">Principal</th>
                      <th className="text-center py-3 px-3 text-xs font-semibold uppercase text-slate-500">Tag</th>
                      <th className="text-right py-3 px-3 text-xs font-semibold uppercase text-slate-500">ESG</th>
                      <th className="text-right py-3 px-3 text-xs font-semibold uppercase text-slate-500">E/S/G</th>
                      <th className="text-right py-3 px-3 text-xs font-semibold uppercase text-slate-500">Greenium</th>
                      <th className="text-right py-3 px-3 text-xs font-semibold uppercase text-slate-500">Taxonomy</th>
                      <th className="text-right py-3 px-3 text-xs font-semibold uppercase text-slate-500">Saving/yr</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/25">
                    {filteredInstruments.map(inst => (
                      <tr key={inst.instrument_id} className="hover:bg-white/40 transition-colors">
                        <td className="py-2.5 px-3">
                          <p className="font-semibold text-slate-900">{inst.instrument_name}</p>
                          <p className="text-[11px] text-slate-500">{inst.instrument_id} · {inst.currency}</p>
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono">${(inst.principal / 1e9).toFixed(2)}B</td>
                        <td className="py-2.5 px-3 text-center">
                          <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-bold border backdrop-blur ${TAG_META[inst.esg_tag].bg}`}>
                            {TAG_META[inst.esg_tag].label}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-right">
                          <span className={inst.esg_score > 60 ? 'text-emerald-600 font-bold' : inst.esg_score > 40 ? 'text-amber-600 font-bold' : 'text-red-600 font-bold'}>
                            {inst.esg_score}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-right text-xs tabular-nums">{inst.environmental}/{inst.social}/{inst.governance}</td>
                        <td className="py-2.5 px-3 text-right font-mono">
                          <span className={inst.greenium_bps < 0 ? 'text-emerald-600 font-bold' : 'text-slate-400'}>
                            {inst.greenium_bps === 0 ? '—' : `${inst.greenium_bps} bps`}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <div className="w-14 h-1.5 rounded-full bg-slate-200/70 overflow-hidden hidden sm:block">
                              <div className="h-full rounded-full" style={{ width: `${inst.taxonomy_alignment_pct}%`, background: inst.taxonomy_alignment_pct > 60 ? '#10b981' : inst.taxonomy_alignment_pct > 35 ? '#eab308' : '#94a3b8' }} />
                            </div>
                            <span className="font-mono font-semibold tabular-nums">{inst.taxonomy_alignment_pct}%</span>
                          </div>
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono text-emerald-600">
                          {inst.annual_greenium_saving ? `$${(inst.annual_greenium_saving / 1e6).toFixed(2)}M` : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="px-4 py-3 text-[11px] text-slate-400 bg-white/20 backdrop-blur border-t border-white/30 flex flex-wrap gap-3">
                <span>Green share: <b className="text-emerald-600">{greenStats.greenShare.toFixed(1)}%</b> (${(greenStats.greenPrincipal/1e9).toFixed(1)}B)</span>
                <span>·</span>
                <span>Weighted greenium: <b className="text-violet-600">{greenStats.wAvgGreenium.toFixed(1)} bps</b></span>
                <span>·</span>
                <span>Annual saving: <b className="text-emerald-600">${(greenStats.saving/1e6).toFixed(1)}M</b> (~${(greenStats.saving*10/1e6).toFixed(0)}M 10y)</span>
                <span>·</span>
                <span>Taxonomy avg: <b className="text-blue-600">{greenStats.wTaxAvg.toFixed(1)}%</b></span>
              </div>
            </Card>

            {/* Green share & cost impact deep dive */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <Card>
                <CardHeader title="Green Share Impact" subtitle="Portfolio funded via labeled bonds" />
                <div className="space-y-3">
                  <div className="h-3 rounded-full bg-slate-200/60 overflow-hidden flex">
                    <div className="h-full bg-emerald-500" style={{ width: `${greenStats.greenShare}%` }} />
                    <div className="h-full bg-blue-500" style={{ width: `${Math.max(0, greenStats.tagCounts.social / enriched.length * 100)}%` }} />
                    <div className="h-full bg-violet-500" style={{ width: `${Math.max(0, greenStats.tagCounts.sustainability / enriched.length * 100)}%` }} />
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-center text-xs">
                    <div className="glass-card p-2"><p className="font-bold text-emerald-600">{greenStats.tagCounts.green}</p><p className="text-slate-500">Green</p></div>
                    <div className="glass-card p-2"><p className="font-bold text-blue-600">{greenStats.tagCounts.social}</p><p className="text-slate-500">Social</p></div>
                    <div className="glass-card p-2"><p className="font-bold text-violet-600">{greenStats.tagCounts.sustainability}</p><p className="text-slate-500">Sustainability</p></div>
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    <span className="font-bold">{greenStats.greenShare.toFixed(1)}%</span> of principal is green/social/sustainability labeled.
                    At <span className="font-bold">{greenStats.wAvgGreenium.toFixed(1)} bps</span> weighted greenium, the labeled sleeve saves <span className="font-bold text-emerald-600">${(greenStats.saving/1e6).toFixed(1)}M/yr</span> vs conventional funding — ~<span className="font-bold">${(greenStats.saving*10/1e6).toFixed(0)}M</span> over 10y. Higher taxonomy alignment (avg {greenStats.wTaxAvg.toFixed(1)}%) supports eligibility for ECB collateral and EU GBS.
                  </p>
                </div>
              </Card>

              <Card>
                <CardHeader title="Cost Impact Sensitivity" subtitle="What if greenium widens?" />
                <div className="space-y-2 text-sm">
                  {[
                    { label: 'Current', bps: greenStats.wAvgGreenium },
                    { label: 'Greenium +5 bps tighter', bps: greenStats.wAvgGreenium - 5 },
                    { label: 'Greenium -5 bps wider', bps: greenStats.wAvgGreenium + 5 },
                  ].map(row => {
                    const saving = greenStats.greenPrincipal * (-row.bps) / 10000;
                    return (
                      <div key={row.label} className="flex items-center justify-between p-3 rounded-xl bg-white/40 backdrop-blur border border-white/40">
                        <span className="font-medium text-slate-700">{row.label} ({row.bps.toFixed(1)} bps)</span>
                        <span className="font-mono font-bold text-emerald-600">${(saving/1e6).toFixed(1)}M/yr</span>
                      </div>
                    );
                  })}
                  <p className="text-[11px] text-slate-500">Sensitivity on labeled principal ${(greenStats.greenPrincipal/1e9).toFixed(1)}B. Each 1 bp ≈ ${((greenStats.greenPrincipal/10000)/1e6).toFixed(2)}M/yr.</p>
                </div>
              </Card>

              <Card>
                <CardHeader title="Taxonomy Alignment" subtitle="Share of capex-aligned use-of-proceeds (mock)" />
                <div className="space-y-3">
                  <div className="flex items-end gap-2">
                    <span className="text-3xl font-bold text-blue-600 tabular-nums">{greenStats.wTaxAvg.toFixed(1)}%</span>
                    <span className="text-xs text-slate-500 mb-1">portfolio-weighted</span>
                  </div>
                  <div className="h-2 rounded-full bg-slate-200/60 overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${greenStats.wTaxAvg}%`, background: 'linear-gradient(90deg,#3b82f6,#10b981)' }} />
                  </div>
                  <div className="text-xs space-y-1">
                    <div className="flex justify-between"><span className="text-slate-500">Green sleeve avg</span><span className="font-bold text-emerald-600">{taxonomyByTag.find(t=>t.tag==='green')?.avg ?? 0}%</span></div>
                    <div className="flex justify-between"><span className="text-slate-500">Sustainability avg</span><span className="font-bold text-violet-600">{taxonomyByTag.find(t=>t.tag==='sustainability')?.avg ?? 0}%</span></div>
                    <div className="flex justify-between"><span className="text-slate-500">Conventional avg</span><span className="font-bold text-slate-600">{taxonomyByTag.find(t=>t.tag==='conventional')?.avg ?? 0}%</span></div>
                  </div>
                  <p className="text-[11px] text-slate-500 leading-relaxed">Alignment &gt; 60% is GBS-ready. Use-of-proceeds with higher alignment improves investor demand and may tighten greenium by 2-4 bps at issuance.</p>
                </div>
              </Card>
            </div>

            {/* Liquidation Analysis */}
            <Card>
              <CardHeader title="Liquidation Analysis — ESG-aware" subtitle={`Sorted by days to liquidate · Filter: ${filterTag === 'all' ? 'All tags' : TAG_META[filterTag as ESGTag].label} · Higher taxonomy & lower carbon = faster`} />
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/30 bg-white/20 backdrop-blur">
                      <th className="text-left py-2 px-3 text-xs font-semibold uppercase text-slate-500">Rank</th>
                      <th className="text-left py-2 px-3 text-xs font-semibold uppercase text-slate-500">Instrument</th>
                      <th className="text-center py-2 px-3 text-xs font-semibold uppercase text-slate-500">Tag</th>
                      <th className="text-right py-2 px-3 text-xs font-semibold uppercase text-slate-500">Taxonomy</th>
                      <th className="text-right py-2 px-3 text-xs font-semibold uppercase text-slate-500">Carbon</th>
                      <th className="text-right py-2 px-3 text-xs font-semibold uppercase text-slate-500">Greenium</th>
                      <th className="text-right py-2 px-3 text-xs font-semibold uppercase text-slate-500">Days</th>
                      <th className="text-left py-2 px-3 text-xs font-semibold uppercase text-slate-500">Tier</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/20">
                    {liquidation.slice(0, 12).map((e, idx) => (
                      <tr key={e.instrument_id} className="hover:bg-white/30">
                        <td className="py-2 px-3 font-mono text-xs">#{idx + 1}</td>
                        <td className="py-2 px-3">
                          <p className="font-medium text-slate-900">{e.instrument_name}</p>
                          <p className="text-[11px] text-slate-500">${(e.principal/1e9).toFixed(2)}B</p>
                        </td>
                        <td className="py-2 px-3 text-center">
                          <span className={`px-2 py-0.5 rounded-full text-[11px] font-bold border ${TAG_META[e.esg_tag].bg}`}>{TAG_META[e.esg_tag].label}</span>
                        </td>
                        <td className="py-2 px-3 text-right font-mono">{e.taxonomy_alignment_pct}%</td>
                        <td className="py-2 px-3 text-right font-mono"><span className={e.carbon_risk_score > 60 ? 'text-red-600 font-bold' : e.carbon_risk_score > 40 ? 'text-amber-600' : 'text-emerald-600'}>{e.carbon_risk_score}</span></td>
                        <td className="py-2 px-3 text-right font-mono">{e.greenium_bps === 0 ? '—' : `${e.greenium_bps}bps`}</td>
                        <td className="py-2 px-3 text-right font-mono font-bold">{e.days_to_liquidate}d</td>
                        <td className="py-2 px-3">
                          <Badge variant={e.liquidity_tier === 'Highly liquid' ? 'success' : e.liquidity_tier === 'Liquid' ? 'info' : e.liquidity_tier === 'Moderate' ? 'warning' : 'danger'}>{e.liquidity_tier}</Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="px-4 py-3 text-[11px] text-slate-500 bg-white/20 backdrop-blur border-t border-white/30">
                Model: days = 8 + (100 - taxonomy%)×0.45 + carbon×0.12 + principal(B)×0.35. Lower days = easier to liquidate without ESG concession. Green/sustainability with high taxonomy typically 12-20d; conventional high-carbon up to 38d+. For stress, add 40% to days (fire-sale).
              </div>
            </Card>

            {/* Country Comparison */}
            {Object.keys(countryScores).length > 0 && (
              <Card>
                <CardHeader title="Global ESG Comparison" subtitle="Click to switch country — overall score" />
                <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
                  {Object.entries(countryScores)
                    .sort((a, b) => (b[1].overall || 0) - (a[1].overall || 0))
                    .slice(0, 18)
                    .map(([code, scores]) => (
                      <div
                        key={code}
                        onClick={() => setCountryCode(code)}
                        className={`p-2.5 rounded-xl cursor-pointer text-center transition border backdrop-blur ${code === countryCode ? 'bg-blue-500/15 border-blue-500/30 shadow' : 'bg-white/40 hover:bg-white/60 border-white/40'}`}
                      >
                        <div className="text-xs font-bold">{code}</div>
                        <div className={`text-lg font-bold ${scores.overall > 60 ? 'text-emerald-600' : scores.overall > 40 ? 'text-amber-600' : 'text-red-600'}`}>
                          {scores.overall}
                        </div>
                        <div className="text-[10px] text-slate-500">E:{scores.environmental} S:{scores.social} G:{scores.governance}</div>
                      </div>
                    ))}
                </div>
              </Card>
            )}

            {/* Recommendations */}
            {data.recommendations.length > 0 && (
              <Card>
                <CardHeader title="ESG Recommendations" subtitle={`${data.recommendations.length} actions`} />
                <div className="space-y-3">
                  {data.recommendations.map((rec, i) => (
                    <div key={i} className={`p-4 rounded-xl border backdrop-blur ${rec.severity === 'high' ? 'bg-red-500/10 border-red-500/20' : rec.severity === 'medium' ? 'bg-amber-500/10 border-amber-500/20' : 'bg-blue-500/10 border-blue-500/20'}`}>
                      <div className="flex items-start gap-2">
                        <span className={`text-xs font-bold px-2 py-0.5 rounded-full border ${rec.severity === 'high' ? 'bg-red-500 text-white border-red-600' : rec.severity === 'medium' ? 'bg-amber-500 text-white border-amber-600' : 'bg-blue-500 text-white border-blue-600'}`}>
                          {rec.severity.toUpperCase()}
                        </span>
                        <div>
                          <p className="text-sm text-slate-800">{rec.message}</p>
                          <p className="text-sm text-slate-600 mt-1">→ {rec.action}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </>
        )}

        {!selectedPortfolio && !loading && (
          <div className="glass-card p-12 text-center">
            <div className="text-5xl mb-4">🌱</div>
            <p className="text-sm text-slate-600 font-medium">Select a portfolio to view ESG analysis, greenium pricing and taxonomy tagging</p>
          </div>
        )}

        {data && !loading && enriched.length === 0 && (
          <div className="glass-card p-8 text-center text-slate-500">No instruments found for this portfolio.</div>
        )}
      </div>
    </AppShell>
  );
}
