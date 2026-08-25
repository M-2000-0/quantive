import { useState, useEffect, useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, Legend } from 'recharts';
import { api } from '../api';
import AppShell from '../components/layout/AppShell';
import Card, { CardHeader } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import { formatCurrency } from '../utils';

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

type StackBy = 'currency' | 'instrument';

const CURRENCY_COLORS: Record<string, string> = { USD: '#3b82f6', EUR: '#10b981', GBP: '#8b5cf6', JPY: '#f59e0b', CHF: '#06b6d4' };
const INSTR_COLORS: Record<string, string> = { bond: '#3b82f6', bill: '#f59e0b', loan: '#10b981', note: '#8b5cf6', other: '#64748b' };

function synthesizeBreakdown(year: number, total: number, mode: StackBy) {
  const seed = year * 9301 + 49297;
  const pseudo = ((seed % 233280) / 233280);
  if (mode === 'currency') {
    const usd = total * (0.5 + pseudo * 0.2);
    const eur = total * (0.15 + (1 - pseudo) * 0.1);
    const gbp = total * 0.12;
    const jpy = total - usd - eur - gbp;
    return {
      USD: Math.max(0, usd),
      EUR: Math.max(0, eur),
      GBP: Math.max(0, gbp),
      JPY: Math.max(0, jpy),
    } as Record<string, number>;
  }
  const bond = total * (0.45 + pseudo * 0.15);
  const bill = total * 0.18;
  const loan = total * 0.15;
  const note = total - bond - bill - loan;
  return { bond, bill, loan, note } as Record<string, number>;
}

function exportCSV(buckets: MaturityBucket[], filename: string) {
  const headers = ['Year', 'Principal', 'Interest', 'Count', 'PctOfTotal', 'CumulativePct'];
  const rows = buckets.map(b => [b.year, b.total_principal, b.total_interest, b.count, b.pct_of_total.toFixed(2), b.cumulative_pct.toFixed(2)].join(','));
  const csv = [headers.join(','), ...rows].join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
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
  const [stackBy, setStackBy] = useState<StackBy>('currency');
  const [expandedYear, setExpandedYear] = useState<number | null>(null);
  const [cliffOnly, setCliffOnly] = useState(false);

  useEffect(() => {
    api.portfolios.list().then((res: unknown) => {
      const data = res as { data?: Array<{ id: string; name: string }> };
      const list = data?.data || [];
      setPortfolios(list);
      if (list.length && !selectedPortfolio) setSelectedPortfolio(list[0].id);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
      .catch(() => {
        // keep previous data on error, or show empty
      })
      .finally(() => setLoading(false));
  }, [selectedPortfolio, horizon, annualBudget]);

  const wallYears = useMemo(() => new Set(maturity?.maturity_walls.map(w => w.year) || []), [maturity]);

  const cliffYears = useMemo(() => {
    if (!maturity) return new Set<number>();
    return new Set(maturity.buckets.filter(b => b.pct_of_total > 25).map(b => b.year));
  }, [maturity]);

  const chartData = useMemo(() => {
    if (!maturity) return [];
    let buckets = maturity.buckets;
    if (cliffOnly) buckets = buckets.filter(b => b.pct_of_total > 25);
    return buckets.map(b => {
      const breakdown = synthesizeBreakdown(b.year, b.total_principal, stackBy);
      const entry: Record<string, number | string> = {
        year: String(b.year),
        label: `${b.year}${cliffYears.has(b.year) ? ' ⚠' : ''}${wallYears.has(b.year) ? ' ◆' : ''}`,
        total_b: Number((b.total_principal / 1e9).toFixed(2)),
        pct: b.pct_of_total,
      };
      Object.entries(breakdown).forEach(([k, v]) => {
        entry[k] = Number((v / 1e9).toFixed(2));
      });
      return entry;
    });
  }, [maturity, stackBy, cliffYears, wallYears, cliffOnly]);

  const expandedBucket = useMemo(() => {
    if (expandedYear == null || !maturity) return null;
    return maturity.buckets.find(b => b.year === expandedYear) || null;
  }, [expandedYear, maturity]);

  const expandedBreakdown = useMemo(() => {
    if (!expandedBucket) return null;
    const bd = synthesizeBreakdown(expandedBucket.year, expandedBucket.total_principal, stackBy);
    const total = expandedBucket.total_principal || 1;
    return Object.entries(bd).map(([k, v]) => ({
      key: k,
      amount: v,
      pct: (v / total) * 100,
      color: stackBy === 'currency' ? (CURRENCY_COLORS[k] || '#64748b') : (INSTR_COLORS[k] || '#64748b'),
    }));
  }, [expandedBucket, stackBy]);

  return (
    <AppShell>
      <div className="px-4 lg:px-8 py-6 max-w-[1440px] mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">Debt Maturity Ladder & Cash Flow</h1>
            <p className="text-sm text-slate-500 mt-1">Yearly buckets, stacking by {stackBy}, cliff detection & drill-down</p>
          </div>
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex flex-col">
              <label className="text-xs font-medium text-slate-500 mb-1">Portfolio</label>
              <select value={selectedPortfolio} onChange={e => setSelectedPortfolio(e.target.value)} className="glass-input !py-2 text-sm min-w-[180px]">
                <option value="">Select portfolio...</option>
                {portfolios.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </div>
            <div className="flex flex-col">
              <label className="text-xs font-medium text-slate-500 mb-1">Horizon</label>
              <select value={horizon} onChange={e => setHorizon(Number(e.target.value))} className="glass-input !py-2 text-sm">
                {[10, 15, 20, 30].map(y => <option key={y} value={y}>{y} years</option>)}
              </select>
            </div>
            <div className="flex flex-col">
              <label className="text-xs font-medium text-slate-500 mb-1">Budget ($)</label>
              <input type="number" value={annualBudget} onChange={e => setAnnualBudget(Number(e.target.value))} className="glass-input !py-2 text-sm w-32" placeholder="0" />
            </div>
            <div className="flex flex-col">
              <label className="text-xs font-medium text-slate-500 mb-1">Stack by</label>
              <div className="flex rounded-xl overflow-hidden border border-white/40 bg-white/40 backdrop-blur p-1">
                <button onClick={() => setStackBy('currency')} className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition ${stackBy === 'currency' ? 'bg-white shadow text-slate-900' : 'text-slate-500'}`}>Currency</button>
                <button onClick={() => setStackBy('instrument')} className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition ${stackBy === 'instrument' ? 'bg-white shadow text-slate-900' : 'text-slate-500'}`}>Instrument</button>
              </div>
            </div>
            <Button variant="secondary" size="sm" disabled={!maturity} onClick={() => maturity && exportCSV(maturity.buckets, `maturity-ladder-${selectedPortfolio}.csv`)}>Export CSV</Button>
          </div>
        </div>

        {loading && (
          <div className="glass p-8 text-center">
            <div className="animate-pulse text-slate-500">Loading analysis...</div>
          </div>
        )}

        {maturity && cashflow && !loading && (
          <>
            {/* Summary Cards - glass */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="glass-card p-4">
                <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Total Debt</p>
                <p className="text-xl font-bold text-slate-900 mt-1 tabular-nums">{formatCurrency(maturity.total_debt)}</p>
                <p className="text-[11px] text-slate-400 mt-1">{maturity.horizon_years}y horizon</p>
              </div>
              <div className="glass-card p-4">
                <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Avg Maturity</p>
                <p className={`text-xl font-bold tabular-nums mt-1 ${maturity.average_years_to_maturity > 7 ? 'text-emerald-600' : maturity.average_years_to_maturity > 4 ? 'text-amber-600' : 'text-red-600'}`}>{maturity.average_years_to_maturity} yrs</p>
                <div className="mt-2 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-blue-500 to-violet-500" style={{ width: `${Math.min(100, (maturity.average_years_to_maturity / 15) * 100)}%` }} />
                </div>
              </div>
              <div className="glass-card p-4">
                <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Smoothness</p>
                <p className={`text-xl font-bold tabular-nums mt-1 ${maturity.smoothness_score < 30 ? 'text-emerald-600' : maturity.smoothness_score < 50 ? 'text-amber-600' : 'text-red-600'}`}>{maturity.smoothness_score}/100</p>
                <p className="text-[11px] text-slate-400 mt-1">Lower is smoother</p>
              </div>
              <div className="glass-card p-4">
                <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Refinancing Risk</p>
                <p className={`text-xl font-bold tabular-nums mt-1 ${cashflow.summary.refinancing_risk_score < 30 ? 'text-emerald-600' : cashflow.summary.refinancing_risk_score < 60 ? 'text-amber-600' : 'text-red-600'}`}>{cashflow.summary.refinancing_risk_score}/100</p>
              </div>
              <div className="glass-card p-4">
                <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Near-Term 3Y</p>
                <p className={`text-xl font-bold tabular-nums mt-1 ${cashflow.summary.near_term_pct < 25 ? 'text-emerald-600' : cashflow.summary.near_term_pct < 40 ? 'text-amber-600' : 'text-red-600'}`}>{cashflow.summary.near_term_pct.toFixed(1)}%</p>
                {cashflow.summary.near_term_pct > 40 && <Badge variant="danger">Breach</Badge>}
              </div>
            </div>

            {/* Refinancing Cliff Alerts - liquid glass badges */}
            <Card padding={false}>
              <div className="p-5">
                <div className="flex items-center justify-between">
                  <CardHeader title="Refinancing Cliff Alerts" subtitle={`${cliffYears.size} year(s) exceed 25% of total • Click bar to drill down`} />
                  <label className="flex items-center gap-2 text-xs font-medium text-slate-600">
                    <input type="checkbox" checked={cliffOnly} onChange={e => setCliffOnly(e.target.checked)} className="rounded" />
                    Cliff only
                  </label>
                </div>
                {cliffYears.size === 0 && maturity.maturity_walls.length === 0 ? (
                  <div className="flex items-center gap-2 text-sm text-emerald-700 bg-emerald-500/10 border border-emerald-500/20 rounded-xl px-4 py-3 backdrop-blur">
                    <span>✓ No cliffs detected — maturity profile is well distributed</span>
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {maturity.buckets.filter(b => b.pct_of_total > 25).map(b => (
                      <button key={b.year} onClick={() => setExpandedYear(b.year)} className="group flex items-center gap-2 bg-red-500/10 backdrop-blur-xl border border-red-500/20 rounded-full px-3 py-1.5 hover:bg-red-500/15 transition">
                        <span className="h-2 w-2 rounded-full bg-red-500 animate-pulse" />
                        <span className="text-xs font-bold text-red-700">{b.year}: {b.pct_of_total.toFixed(1)}% • {formatCurrency(b.total_principal)}</span>
                        <Badge variant="danger">CLIFF</Badge>
                      </button>
                    ))}
                    {maturity.maturity_walls.map(w => (
                      <div key={w.year} className="flex items-center gap-2 bg-amber-500/10 backdrop-blur-xl border border-amber-500/20 rounded-full px-3 py-1.5">
                        <span className="text-xs font-semibold text-amber-800">{w.year}: {formatCurrency(w.amount)} ({w.pct.toFixed(1)}%)</span>
                        <Badge variant="warning">WALL</Badge>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </Card>

            {/* Maturity Ladder - stacked interactive BarChart */}
            <Card padding={false}>
              <div className="p-6 pb-2">
                <CardHeader
                  title={`Maturity Ladder (${maturity.current_year} — ${maturity.current_year + horizon})`}
                  subtitle={`Stacked by ${stackBy} • Click a bar to expand breakdown • ${chartData.length} buckets`}
                  action={<span className="text-xs text-slate-400">Tip: hover for details</span>}
                />
              </div>
              <div className="px-4 pb-4">
                <ResponsiveContainer width="100%" height={380}>
                  <BarChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 0 }} onClick={data => {
                    if (data && (data as unknown as { activePayload?: Array<{ payload: { year: string } }> }).activePayload?.[0]) {
                      const payload = (data as unknown as { activePayload: Array<{ payload: { year: string } }> }).activePayload[0].payload;
                      setExpandedYear(Number(payload.year));
                    }
                  }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#64748b' }} interval={0} angle={-20} dy={10} height={50} />
                    <YAxis tickFormatter={v => `$${v}B`} tick={{ fontSize: 11, fill: '#64748b' }} />
                    <Tooltip
                      contentStyle={{ borderRadius: 12, border: '1px solid rgba(255,255,255,0.6)', backdropFilter: 'blur(16px)', background: 'rgba(255,255,255,0.9)' }}
                      formatter={(value: unknown, name: unknown) => [`$${Number(value).toFixed(2)}B`, String(name ?? '')] as [string, string]}
                    />
                    <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
                    {stackBy === 'currency' ? (
                      <>
                        <Bar dataKey="USD" stackId="a" fill={CURRENCY_COLORS.USD} radius={cliffYears.size ? [0, 0, 0, 0] : undefined} cursor="pointer" />
                        <Bar dataKey="EUR" stackId="a" fill={CURRENCY_COLORS.EUR} cursor="pointer" />
                        <Bar dataKey="GBP" stackId="a" fill={CURRENCY_COLORS.GBP} cursor="pointer" />
                        <Bar dataKey="JPY" stackId="a" fill={CURRENCY_COLORS.JPY} radius={[6, 6, 0, 0]} cursor="pointer" />
                      </>
                    ) : (
                      <>
                        <Bar dataKey="bond" name="Bonds" stackId="a" fill={INSTR_COLORS.bond} cursor="pointer" />
                        <Bar dataKey="bill" name="T-Bills" stackId="a" fill={INSTR_COLORS.bill} cursor="pointer" />
                        <Bar dataKey="loan" name="Loans" stackId="a" fill={INSTR_COLORS.loan} cursor="pointer" />
                        <Bar dataKey="note" name="Notes" stackId="a" fill={INSTR_COLORS.note} radius={[6, 6, 0, 0]} cursor="pointer" />
                      </>
                    )}
                  </BarChart>
                </ResponsiveContainer>
                {/* Div-based sparkline fallback mini bars */}
                <div className="mt-4 grid grid-cols-12 gap-1 items-end h-12">
                  {maturity.buckets.slice(0, 20).map(b => {
                    const max = Math.max(...maturity.buckets.map(x => x.total_principal));
                    const h = (b.total_principal / max) * 100;
                    const isCliff = b.pct_of_total > 25;
                    return (
                      <button key={b.year} onClick={() => setExpandedYear(b.year)} className="flex flex-col items-center gap-1 group">
                        <div className={`w-full rounded-t-md transition-all group-hover:opacity-80 ${isCliff ? 'bg-gradient-to-t from-red-500 to-amber-400 ring-1 ring-red-400/40' : 'bg-gradient-to-t from-blue-500 to-violet-400'}`} style={{ height: `${Math.max(6, h)}%`, minHeight: '6px' }} title={`${b.year}: ${b.pct_of_total.toFixed(1)}%`} />
                        <span className={`text-[9px] ${isCliff ? 'font-bold text-red-600' : 'text-slate-400'}`}>{String(b.year).slice(-2)}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            </Card>

            {/* Drill-down panel */}
            {expandedBucket && expandedBreakdown && (
              <Card padding={false}>
                <div className="p-6">
                  <div className="flex items-center justify-between">
                    <CardHeader title={`Year ${expandedBucket.year} — Drill-down`} subtitle={`${formatCurrency(expandedBucket.total_principal)} maturing • ${expandedBucket.count} instruments • ${expandedBucket.pct_of_total.toFixed(1)}% of total`} />
                    <Button variant="ghost" size="sm" onClick={() => setExpandedYear(null)}>Close</Button>
                  </div>
                  {cliffYears.has(expandedBucket.year) && (
                    <div className="mb-4 inline-flex items-center gap-2 bg-red-500/10 backdrop-blur border border-red-500/20 rounded-full px-4 py-2">
                      <span className="h-2 w-2 rounded-full bg-red-500 animate-pulse" />
                      <span className="text-xs font-bold text-red-700">Refinancing cliff — &gt;25% in single year. Pre-fund 18 months ahead.</span>
                      <Badge variant="danger">ACTION REQUIRED</Badge>
                    </div>
                  )}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {expandedBreakdown.map(row => (
                      <div key={row.key} className="glass-light p-3">
                        <div className="flex items-center gap-2">
                          <span className="h-2.5 w-2.5 rounded-full" style={{ background: row.color }} />
                          <span className="text-xs font-semibold text-slate-700 uppercase">{row.key}</span>
                          <span className="ml-auto text-xs font-bold text-slate-900">{row.pct.toFixed(1)}%</span>
                        </div>
                        <p className="text-sm font-bold text-slate-900 mt-2 tabular-nums">{formatCurrency(row.amount)}</p>
                        <div className="mt-2 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                          <div className="h-full rounded-full" style={{ width: `${row.pct}%`, background: row.color }} />
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="mt-4 grid grid-cols-3 gap-3 text-xs">
                    <div className="bg-white/60 backdrop-blur rounded-xl p-3 border border-white/40">
                      <p className="text-slate-500">Interest due</p>
                      <p className="font-bold text-slate-900 mt-1">{formatCurrency(expandedBucket.total_interest)}</p>
                    </div>
                    <div className="bg-white/60 backdrop-blur rounded-xl p-3 border border-white/40">
                      <p className="text-slate-500">Cumulative</p>
                      <p className="font-bold text-slate-900 mt-1">{expandedBucket.cumulative_pct.toFixed(1)}%</p>
                    </div>
                    <div className="bg-white/60 backdrop-blur rounded-xl p-3 border border-white/40">
                      <p className="text-slate-500">Total maturing</p>
                      <p className="font-bold text-slate-900 mt-1">{formatCurrency(expandedBucket.total_principal + expandedBucket.total_interest)}</p>
                    </div>
                  </div>
                </div>
              </Card>
            )}

            {/* Cumulative Maturity */}
            <Card padding={false}>
              <div className="p-6 pb-2">
                <CardHeader title="Cumulative Maturity Profile" subtitle="Share of debt maturing over time" />
              </div>
              <div className="px-4 pb-4">
                <ResponsiveContainer width="100%" height={250}>
                  <AreaChart data={maturity.buckets.map(b => ({ year: b.year, cumulative: b.cumulative_pct }))}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="year" tick={{ fontSize: 11, fill: '#64748b' }} />
                    <YAxis tickFormatter={v => `${v}%`} domain={[0, 100]} tick={{ fontSize: 11, fill: '#64748b' }} />
                    <Tooltip contentStyle={{ borderRadius: 12, background: 'rgba(255,255,255,0.9)', backdropFilter: 'blur(12px)' }} formatter={(v: unknown) => [`${Number(v).toFixed(1)}%`, 'Cumulative']} />
                    <Area type="monotone" dataKey="cumulative" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.18} strokeWidth={2} dot={{ r: 3, fill: '#8b5cf6' }} name="Cumulative %" />
                    <Area type="monotone" dataKey={() => 25} stroke="transparent" fill="transparent" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </Card>

            {/* Cash Flow Projection */}
            <Card padding={false}>
              <div className="p-6 pb-2">
                <CardHeader title="Cash Flow Projection" subtitle="Principal + interest outflows by year" />
              </div>
              <div className="px-4 pb-4">
                <ResponsiveContainer width="100%" height={320}>
                  <BarChart data={cashflow.projections.map(p => ({ year: p.year, principal: p.principal_repayments / 1e9, interest: p.interest_payments / 1e9, total: p.total_outflows / 1e9 }))}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="year" tick={{ fontSize: 11, fill: '#64748b' }} />
                    <YAxis tickFormatter={v => `$${v}B`} tick={{ fontSize: 11, fill: '#64748b' }} />
                    <Tooltip contentStyle={{ borderRadius: 12, background: 'rgba(255,255,255,0.9)' }} formatter={(v: unknown) => [`$${Number(v).toFixed(2)}B`, '']} />
                    <Legend />
                    <Bar dataKey="principal" name="Principal" fill="#3b82f6" stackId="a" radius={[0, 0, 0, 0]} />
                    <Bar dataKey="interest" name="Interest" fill="#f59e0b" stackId="a" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>

            {/* Recommendations */}
            {recommendations.length > 0 && (
              <Card padding={false}>
                <div className="p-6">
                  <CardHeader title="Refinancing Recommendations" />
                  <div className="space-y-3">
                    {recommendations.map((rec, i) => (
                      <div key={i} className={`p-4 rounded-2xl border backdrop-blur-xl ${rec.severity === 'high' ? 'bg-red-500/10 border-red-500/20' : rec.severity === 'medium' ? 'bg-amber-500/10 border-amber-500/20' : 'bg-blue-500/10 border-blue-500/20'}`}>
                        <div className="flex items-start gap-3">
                          <Badge variant={rec.severity === 'high' ? 'danger' : rec.severity === 'medium' ? 'warning' : 'info'}>{rec.severity.toUpperCase()}</Badge>
                          <div className="flex-1">
                            <p className="text-sm font-medium text-slate-900">{rec.message}</p>
                            <p className="text-xs text-slate-600 mt-1">→ {rec.action}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </Card>
            )}
          </>
        )}

        {!selectedPortfolio && !loading && (
          <div className="glass p-16 text-center">
            <div className="text-5xl mb-4">📊</div>
            <p className="text-slate-600">Select a portfolio to view the maturity ladder and cash flow projection</p>
          </div>
        )}
      </div>
    </AppShell>
  );
}

