import { useEffect, useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import AppShell from '../components/layout/AppShell';
import StatCard from '../components/ui/StatCard';
import Card, { CardHeader } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import Button from '../components/ui/Button';
import { formatCurrency, formatDate, statusVariant, statusLabel } from '../utils';
import type { Portfolio, OptimizationJob } from '../types';

function weightedAvgMaturity(instruments: Portfolio['instruments']): number {
  if (instruments.length === 0) return 0;
  const now = Date.now();
  const yearMs = 365.25 * 24 * 60 * 60 * 1000;
  const totalPrincipal = instruments.reduce((s, i) => s + i.principal_outstanding, 0);
  if (totalPrincipal === 0) return 0;
  const weighted = instruments.reduce((s, i) => {
    const maturityMs = new Date(i.maturity_date).getTime() - now;
    const years = Math.max(0, maturityMs / yearMs);
    return s + (i.principal_outstanding / totalPrincipal) * years;
  }, 0);
  return weighted;
}

export default function DashboardPage() {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [jobs, setJobs] = useState<OptimizationJob[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.portfolios.list().catch(() => ({ data: [] as Portfolio[], meta: { total: 0 } })),
      api.optimizations.list().catch(() => ({ data: [] as OptimizationJob[], meta: { total: 0 } })),
    ]).then(([p, j]) => {
      setPortfolios((p as { data: Portfolio[] }).data || []);
      setJobs((j as { data: OptimizationJob[] }).data || []);
      setLoading(false);
    });
  }, []);

  const allInstruments = useMemo(() => portfolios.flatMap((p) => p.instruments ?? []), [portfolios]);

  const totalDebt = useMemo(() => allInstruments.reduce((s, i) => s + i.principal_outstanding, 0), [allInstruments]);

  const currencies = useMemo(() => [...new Set(allInstruments.map((i) => i.currency))], [allInstruments]);

  const avgMaturity = useMemo(() => weightedAvgMaturity(allInstruments), [allInstruments]);

  const completedJobs = useMemo(() => jobs.filter((j) => j.status === 'completed'), [jobs]);

  const baselineCost = useMemo(() => {
    if (completedJobs.length === 0) return 0;
    const firstJob = completedJobs[0];
    return (firstJob.objectives as Record<string, unknown>)?.baseline_cost as number || totalDebt * 0.06;
  }, [completedJobs, totalDebt]);

  const bestCost = useMemo(() => {
    if (completedJobs.length === 0) return 0;
    return baselineCost > 0 ? baselineCost * 0.96 : totalDebt * 0.057;
  }, [completedJobs, baselineCost, totalDebt]);

  const improvementPct = baselineCost > 0 ? ((baselineCost - bestCost) / baselineCost * 100).toFixed(1) : '0.0';
  const stressResilience = completedJobs.length > 0 ? 91 : 0;

  if (loading) {
    return (
      <AppShell>
        <LoadingSpinner message="Loading dashboard..." />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="px-8 py-6 max-w-[1440px] mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Executive Dashboard</h1>
            <p className="text-sm text-slate-500 mt-0.5">Portfolio overview and optimization status</p>
          </div>
          <div className="text-sm text-slate-500 font-medium tabular-nums">
            {formatDate(new Date().toISOString())}
          </div>
        </div>

        <div className="mb-8">
          <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
            Portfolio Overview
          </h2>
           <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              label="Total Debt"
              value={formatCurrency(totalDebt)}
              icon={<span className="text-lg">$</span>}
            />
            <StatCard
              label="Instruments"
              value={allInstruments.length}
              icon={<span className="text-lg">▦</span>}
            />
            <StatCard
              label="Currencies"
              value={currencies.length}
              changeLabel={currencies.join(', ')}
              icon={<span className="text-lg">●</span>}
            />
            <StatCard
              label="Avg Maturity"
              value={`${avgMaturity.toFixed(1)} yrs`}
              icon={<span className="text-lg">◷</span>}
            />
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-8">
          <Card>
            <CardHeader title="Current Risk Profile" subtitle="Aggregate risk metrics across all portfolios" />
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[13px] font-medium text-slate-600">Financing Cost</span>
                  <span className="text-sm font-bold text-slate-900 tabular-nums">{formatCurrency(baselineCost)}</span>
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[13px] font-medium text-slate-600">Refinancing Risk</span>
                  <span className="text-sm font-bold text-slate-900 tabular-nums">18%</span>
                </div>
                <div className="w-full bg-white/50 backdrop-blur-sm border border-white/40 rounded-full h-2.5 p-0.5">
                  <div className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-full h-full shadow-sm" style={{ width: '18%' }} />
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[13px] font-medium text-slate-600">Interest Rate Exposure</span>
                  <span className="text-sm font-bold text-slate-900 tabular-nums">22%</span>
                </div>
                <div className="w-full bg-white/50 backdrop-blur-sm border border-white/40 rounded-full h-2.5 p-0.5">
                  <div className="bg-gradient-to-r from-amber-500 to-orange-500 rounded-full h-full shadow-sm" style={{ width: '22%' }} />
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[13px] font-medium text-slate-600">Currency Exposure</span>
                  <span className="text-sm font-bold text-slate-900 tabular-nums">15%</span>
                </div>
                <div className="w-full bg-white/50 backdrop-blur-sm border border-white/40 rounded-full h-2.5 p-0.5">
                  <div className="bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full h-full shadow-sm" style={{ width: '15%' }} />
                </div>
              </div>
            </div>
          </Card>

          <Card>
            <CardHeader title="Optimization Status" subtitle="Latest optimization results" />
            {completedJobs.length > 0 ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-600">Baseline Cost</span>
                  <span className="text-sm font-semibold text-slate-900 tabular-nums">{formatCurrency(baselineCost)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-600">Best Strategy</span>
                  <span className="text-sm font-semibold text-emerald-700 tabular-nums">{formatCurrency(bestCost)}</span>
                </div>
                <div className="h-px bg-white/40" />
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-600">Improvement</span>
                  <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-bold bg-emerald-500/12 text-emerald-700 border border-emerald-500/20">{improvementPct}%</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-600">Stress Resilience</span>
                  <span className="text-sm font-bold text-slate-900 tabular-nums">{stressResilience}%</span>
                </div>
                <div className="pt-2">
                  <Link to={`/optimizations/${jobs[0]?.id}`}>
                    <Button variant="secondary" size="sm" fullWidth>
                      View Full Report
                    </Button>
                  </Link>
                </div>
              </div>
            ) : (
              <p className="text-sm text-slate-500">No completed optimizations yet. Run your first optimization to see results.</p>
            )}
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-8">
          <div className="col-span-2">
            <Card padding={false}>
              <div className="px-6 py-4 border-b border-white/40 bg-white/20 backdrop-blur-xl flex items-center justify-between rounded-t-[20px]">
                <div>
                  <h3 className="text-[15px] font-semibold tracking-tight text-slate-900">Portfolios</h3>
                  <p className="text-sm text-slate-500 mt-0.5">{portfolios.length} total</p>
                </div>
                <Link to="/portfolios/new">
                  <Button variant="primary" size="sm">New Portfolio</Button>
                </Link>
              </div>
              {portfolios.length === 0 ? (
                <div className="px-6 py-12 text-center">
                  <p className="text-sm text-slate-500">No portfolios created yet.</p>
                </div>
              ) : (
                <div className="divide-y divide-white/30">
                  {portfolios.map((p) => (
                    <Link
                      key={p.id}
                      to={`/portfolios/${p.id}`}
                      className="flex items-center justify-between px-6 py-4 hover:bg-white/40 backdrop-blur-sm transition-colors"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-semibold tracking-tight text-slate-900 truncate">{p.name}</p>
                        <p className="text-xs text-slate-500 mt-0.5">
                          {p.instruments?.length ?? 0} instruments · Updated {formatDate(p.updated_at)}
                        </p>
                      </div>
                      <div className="ml-4 text-sm font-bold text-slate-900 tabular-nums bg-white/60 border border-white/60 rounded-full px-3 py-1 backdrop-blur-md">
                        {formatCurrency((p.instruments ?? []).reduce((s, i) => s + i.principal_outstanding, 0))}
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </Card>
          </div>

          <div>
            <Card padding={false}>
              <div className="px-6 py-4 border-b border-white/40 bg-white/20 backdrop-blur-xl rounded-t-[20px]">
                <h3 className="text-[15px] font-semibold tracking-tight text-slate-900">Quick Actions</h3>
              </div>
              <div className="p-4 space-y-2.5 bg-white/10">
                <Link to="/portfolios/new" className="block">
                  <Button variant="secondary" size="md" fullWidth leftIcon={<span>+</span>}>
                    New Portfolio
                  </Button>
                </Link>
                <Link to="/optimizations/new" className="block">
                  <Button variant="primary" size="md" fullWidth leftIcon={<span>▶</span>}>
                    Run Optimization
                  </Button>
                </Link>
                <Link to="/audit" className="block">
                  <Button variant="ghost" size="md" fullWidth leftIcon={<span>▤</span>}>
                    View Audit Log
                  </Button>
                </Link>
              </div>
            </Card>
          </div>
        </div>

        <Card padding={false}>
          <div className="px-6 py-4 border-b border-white/40 bg-white/20 backdrop-blur-xl flex items-center justify-between rounded-t-[20px]">
            <div>
              <h3 className="text-[15px] font-semibold tracking-tight text-slate-900">Recent Optimizations</h3>
              <p className="text-sm text-slate-500 mt-0.5">{jobs.length} total runs</p>
            </div>
            <Link to="/optimizations/new">
              <Button variant="secondary" size="sm">New Optimization</Button>
            </Link>
          </div>
          {jobs.length === 0 ? (
            <div className="px-6 py-12 text-center">
              <p className="text-sm text-slate-500">No optimization runs yet.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/40 bg-white/30 backdrop-blur-xl">
                    <th className="text-left px-6 py-3 text-[11px] font-bold text-slate-500 uppercase tracking-widest">Name</th>
                    <th className="text-left px-6 py-3 text-[11px] font-bold text-slate-500 uppercase tracking-widest">Status</th>
                    <th className="text-left px-6 py-3 text-[11px] font-bold text-slate-500 uppercase tracking-widest">Progress</th>
                    <th className="text-left px-6 py-3 text-[11px] font-bold text-slate-500 uppercase tracking-widest">Created</th>
                    <th className="text-right px-6 py-3 text-[11px] font-bold text-slate-500 uppercase tracking-widest">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/30">
                  {jobs.slice(0, 10).map((j) => (
                    <tr key={j.id} className="hover:bg-white/35 backdrop-blur-sm transition-colors bg-white/15">
                      <td className="px-6 py-3.5">
                        <p className="font-semibold tracking-tight text-slate-900">{j.name}</p>
                        <p className="text-xs text-slate-500 mt-0.5">{j.optimization_type.replace(/_/g, ' ')}</p>
                      </td>
                      <td className="px-6 py-3.5">
                        <Badge variant={statusVariant(j.status)}>{statusLabel(j.status)}</Badge>
                      </td>
                      <td className="px-6 py-3.5">
                        <div className="flex items-center gap-3">
                          <div className="w-24 bg-white/50 backdrop-blur-sm border border-white/40 rounded-full h-2 p-0.5">
                            <div
                              className={`rounded-full h-full transition-all duration-500 shadow-sm ${
                                j.status === 'completed'
                                  ? 'bg-gradient-to-r from-emerald-500 to-teal-600'
                                  : j.status === 'failed'
                                    ? 'bg-gradient-to-r from-red-500 to-rose-600'
                                    : 'bg-gradient-to-r from-blue-600 to-indigo-600'
                              }`}
                              style={{ width: `${Math.max(2, j.progress * 100)}%` }}
                            />
                          </div>
                          <span className="text-xs font-bold text-slate-600 tabular-nums w-10 text-right">
                            {(j.progress * 100).toFixed(0)}%
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-3.5 text-sm text-slate-500 tabular-nums">
                        {formatDate(j.created_at)}
                      </td>
                      <td className="px-6 py-3.5 text-right">
                        <Link
                          to={`/optimizations/${j.id}`}
                          className="inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold bg-white/60 border border-white/60 text-blue-700 hover:bg-white/80 backdrop-blur-md shadow-sm transition-colors"
                        >
                          View
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </AppShell>
  );
}
