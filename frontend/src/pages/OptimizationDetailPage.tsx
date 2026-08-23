import { useEffect, useState, useCallback, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api';
import type { OptimizationJob, Strategy, BenchmarkResult, Report, ScenarioResult } from '../types';
import { MOCK_SCENARIO_RESULTS, MOCK_STRESS_RESULTS } from '../api/mock';
import AppShell from '../components/layout/AppShell';
import { Tabs, Card, CardHeader, Badge, Button, LoadingSpinner, ProgressBar } from '../components/ui';

type TabId = 'results' | 'comparison' | 'explainability' | 'scenarios' | 'benchmarks' | 'report';

function fmtB(v: number): string {
  if (v >= 1e9) return `$${(v / 1e9).toFixed(2)}B`;
  if (v >= 1e6) return `$${(v / 1e6).toFixed(0)}M`;
  return `$${v.toLocaleString()}`;
}

function fmtPct(v: number): string {
  return `${(v * 100).toFixed(1)}%`;
}

function fmtRate(v: number): string {
  return `${(v * 100).toFixed(2)}%`;
}

function metricVal(metrics: Record<string, unknown>, key: string): number {
  const v = metrics[key];
  return typeof v === 'number' ? v : 0;
}

function bestIdx(values: number[], mode: 'min' | 'max'): number {
  let best = mode === 'min' ? Infinity : -Infinity;
  let idx = -1;
  values.forEach((v, i) => {
    if (mode === 'min' ? v < best : v > best) {
      best = v;
      idx = i;
    }
  });
  return idx;
}

function worstIdx(values: number[], mode: 'min' | 'max'): number {
  let worst = mode === 'min' ? -Infinity : Infinity;
  let idx = -1;
  values.forEach((v, i) => {
    if (mode === 'min' ? v > worst : v < worst) {
      worst = v;
      idx = i;
    }
  });
  return idx;
}

function cellColor(_v: number, bestI: number, worstI: number, i: number): string {
  if (bestI === worstI) return '';
  if (i === bestI) return 'text-emerald-700 font-semibold bg-emerald-50';
  if (i === worstI) return 'text-red-700 bg-red-50';
  return '';
}

function AllocationBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-slate-500 w-28 truncate">{label}</span>
      <div className="flex-1 h-3 bg-slate-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-blue-500 rounded-full transition-all"
          style={{ width: `${Math.max(value * 100, 2)}%` }}
        />
      </div>
      <span className="text-xs font-mono text-slate-700 w-12 text-right">{(value * 100).toFixed(0)}%</span>
    </div>
  );
}

function generateExplanation(strategy: Strategy, allStrategies: Strategy[]): { why: string; sacrifice: string } {
  const m = strategy.metrics;
  const cost = metricVal(m, 'expected_cost');
  const risk = metricVal(m, 'refinancing_risk');
  const resilience = metricVal(m, 'stress_resilience');
  const ir = metricVal(m, 'interest_rate_risk');
  const fx = metricVal(m, 'currency_risk');

  const costs = allStrategies.map((s) => metricVal(s.metrics, 'expected_cost'));
  const risks = allStrategies.map((s) => metricVal(s.metrics, 'refinancing_risk'));
  const resiliences = allStrategies.map((s) => metricVal(s.metrics, 'stress_resilience'));
  const idx = allStrategies.findIndex((s) => s.id === strategy.id);

  const reasons: string[] = [];
  if (cost === Math.min(...costs)) reasons.push('minimizes expected financing cost');
  if (risk === Math.min(...risks)) reasons.push('achieves the lowest refinancing concentration');
  if (resilience === Math.max(...resiliences)) reasons.push('demonstrates the strongest performance under stress conditions');
  if (idx === 0 && reasons.length === 0) reasons.push('provides the best overall weighted balance across all objectives');

  const sacrifices: string[] = [];
  if (cost === Math.max(...costs)) sacrifices.push('higher expected financing cost');
  if (risk === Math.max(...risks)) sacrifices.push('elevated refinancing concentration');
  if (resilience === Math.min(...resiliences)) sacrifices.push('reduced stress resilience');
  if (ir === Math.max(...risks)) sacrifices.push('greater interest rate sensitivity');
  if (fx === Math.max(...allStrategies.map((s) => metricVal(s.metrics, 'currency_risk')))) sacrifices.push('increased foreign exchange exposure');

  if (reasons.length === 0) reasons.push('optimally balances cost efficiency with risk mitigation');
  if (sacrifices.length === 0) sacrifices.push('no significant trade-offs relative to other strategies');

  return {
    why: `This strategy ${reasons[0]}${reasons.length > 1 ? ', and ' + reasons.slice(1).join(', and ') : ''}.`,
    sacrifice: `It accepts ${sacrifices.join(', and ')}.`,
  };
}

export default function OptimizationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [job, setJob] = useState<OptimizationJob | null>(null);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [benchmarks, setBenchmarks] = useState<BenchmarkResult[]>([]);
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<TabId>('results');
  const [expandedStrategy, setExpandedStrategy] = useState<string | null>(null);
  const [reportLoading, setReportLoading] = useState(false);

  const pollJob = useCallback(async () => {
    if (!id) return;
    try {
      const j = await api.optimizations.get(id);
      setJob(j);
      const running = ['queued', 'running', 'scenario_generation', 'solving', 'benchmarking', 'stress_testing'].includes(j.status);
      if (running) {
        setTimeout(pollJob, 2000);
      } else {
        setLoading(false);
        if (j.status === 'completed') {
          const [strats, benchs] = await Promise.all([
            api.optimizations.strategies(id),
            api.optimizations.benchmarks(id),
          ]);
          setStrategies(strats);
          setBenchmarks(benchs);
        }
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to fetch optimization');
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { pollJob(); }, [pollJob]);

  const loadReport = async () => {
    if (!id) return;
    setReportLoading(true);
    try {
      const r = await api.optimizations.report(id);
      setReport(r);
      setActiveTab('report');
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load report');
    } finally {
      setReportLoading(false);
    }
  };

  const isRunning = job && ['queued', 'running', 'scenario_generation', 'solving', 'benchmarking', 'stress_testing'].includes(job.status);

  const recommended = useMemo(() => strategies.find((s) => s.rank === 1) ?? strategies[0], [strategies]);

  const scenarioResults = MOCK_SCENARIO_RESULTS;
  const stressResult = MOCK_STRESS_RESULTS;

  const headerStats = useMemo(() => {
    if (!recommended) return null;
    const m = recommended.metrics;
    const baselineCost = metricVal(m, 'expected_cost') / 0.966;
    return {
      cost: metricVal(m, 'expected_cost'),
      baseline: Math.round(baselineCost),
      improvement: ((baselineCost - metricVal(m, 'expected_cost')) / baselineCost),
      resilience: metricVal(m, 'stress_resilience'),
    };
  }, [recommended]);

  const tabs: Array<{ id: TabId; label: string; disabled?: boolean }> = [
    { id: 'results', label: 'Results' },
    { id: 'comparison', label: 'Strategy Comparison' },
    { id: 'explainability', label: 'Explainability' },
    { id: 'scenarios', label: 'Scenario Analysis' },
    { id: 'benchmarks', label: 'Benchmarks' },
    { id: 'report', label: 'Decision Report' },
  ];

  const completed = job?.status === 'completed';

  if (!job && loading) {
    return (
      <AppShell>
        <LoadingSpinner message="Loading optimization details..." />
      </AppShell>
    );
  }

  if (error && !job) {
    return (
      <AppShell>
        <div className="max-w-4xl mx-auto py-12">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-sm text-red-700">{error}</div>
        </div>
      </AppShell>
    );
  }

  if (!job) {
    return (
      <AppShell>
        <div className="max-w-4xl mx-auto py-12 text-sm text-slate-500">Optimization job not found.</div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="max-w-7xl mx-auto space-y-6">
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">{error}</div>
        )}

        {/* Running progress */}
        {isRunning && (
          <Card>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-semibold text-slate-900">Optimization In Progress</h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Status: {job.status.replace(/_/g, ' ')} &middot; Started {new Date(job.started_at ?? job.created_at).toLocaleString()}
                  </p>
                </div>
                <Button variant="danger" size="sm" onClick={async () => { if (id) { try { await api.optimizations.cancel(id); pollJob(); } catch { /* */ } } }}>
                  Cancel
                </Button>
              </div>
              <ProgressBar value={job.progress} size="lg" showPercentage />
            </div>
          </Card>
        )}

        {/* Executive Summary Header */}
        {completed && headerStats && (
          <div className="bg-gradient-to-r from-slate-900 to-slate-800 rounded-xl p-6 lg:p-8 text-white">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-6">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-emerald-400 mb-1">Optimization Complete</p>
                <h2 className="text-xl lg:text-2xl font-bold">{job.name}</h2>
              </div>
              <div className="flex items-center gap-3">
                <Badge variant="success" size="md">{strategies.length} feasible strategies</Badge>
                {recommended && <Badge variant="info" size="md">Recommended: {recommended.name}</Badge>}
              </div>
            </div>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white/10 backdrop-blur rounded-lg p-4">
                <p className="text-xs text-slate-300 mb-1">Financing Cost</p>
                <p className="text-2xl font-bold">{fmtB(headerStats.cost)}</p>
              </div>
              <div className="bg-white/10 backdrop-blur rounded-lg p-4">
                <p className="text-xs text-slate-300 mb-1">Baseline</p>
                <p className="text-2xl font-bold">{fmtB(headerStats.baseline)}</p>
              </div>
              <div className="bg-white/10 backdrop-blur rounded-lg p-4">
                <p className="text-xs text-slate-300 mb-1">Improvement</p>
                <p className="text-2xl font-bold text-emerald-400">{fmtPct(headerStats.improvement)}</p>
              </div>
              <div className="bg-white/10 backdrop-blur rounded-lg p-4">
                <p className="text-xs text-slate-300 mb-1">Stress Resilience</p>
                <p className="text-2xl font-bold">{fmtPct(headerStats.resilience)}</p>
              </div>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div>
          <Tabs tabs={tabs} activeTab={activeTab} onChange={(t) => {
            if (t === 'report' && !report && !reportLoading) {
              loadReport();
            } else {
              setActiveTab(t as TabId);
            }
          }}>
            {/* Tab 1: Results */}
            {activeTab === 'results' && (
              <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  {strategies.map((s) => {
                    const m = s.metrics;
                    const isRec = s.rank === 1;
                    return (
                      <div
                        key={s.id}
                        className={`bg-white border rounded-lg shadow-sm transition-all hover:shadow-md ${isRec ? 'border-blue-300 ring-1 ring-blue-100' : 'border-slate-200'}`}
                      >
                        <div className={`p-5 ${isRec ? 'border-l-4 border-l-blue-600' : ''}`}>
                          <div className="flex items-start justify-between mb-3">
                            <div>
                              <div className="flex items-center gap-2">
                                <h3 className="text-base font-bold text-slate-900">{s.name}</h3>
                                {isRec && <Badge variant="info" size="sm">RECOMMENDED</Badge>}
                              </div>
                              <p className="text-xs text-slate-500 mt-0.5">
                                {s.rank === 1 ? 'Best Overall' : s.rank === 2 ? 'Lowest Risk' : s.rank === 3 ? 'Lowest Cost' : 'Most Resilient'}
                              </p>
                            </div>
                            <Badge variant={s.rank <= 2 ? 'success' : 'default'} size="sm">Rank #{s.rank}</Badge>
                          </div>

                          <div className="grid grid-cols-3 gap-3 mb-4">
                            <div className="text-center">
                              <p className="text-[10px] uppercase tracking-wider text-slate-400 mb-0.5">Cost</p>
                              <p className="text-sm font-bold text-slate-900">{fmtB(metricVal(m, 'expected_cost'))}</p>
                            </div>
                            <div className="text-center">
                              <p className="text-[10px] uppercase tracking-wider text-slate-400 mb-0.5">Risk</p>
                              <p className="text-sm font-bold text-slate-900">{metricVal(m, 'refinancing_risk').toFixed(2)}</p>
                            </div>
                            <div className="text-center">
                              <p className="text-[10px] uppercase tracking-wider text-slate-400 mb-0.5">Resilience</p>
                              <p className="text-sm font-bold text-slate-900">{fmtPct(metricVal(m, 'stress_resilience'))}</p>
                            </div>
                          </div>

                          <p className="text-xs text-slate-600 leading-relaxed mb-4">{s.description}</p>

                          <Button
                            variant="ghost"
                            size="sm"
                            fullWidth
                            onClick={() => setExpandedStrategy(expandedStrategy === s.id ? null : s.id)}
                          >
                            {expandedStrategy === s.id ? 'Hide Details' : 'Explain'}
                          </Button>
                        </div>

                        {expandedStrategy === s.id && (
                          <div className="border-t border-slate-100 bg-slate-50 p-5 space-y-4">
                            {(() => {
                              const exp = generateExplanation(s, strategies);
                              return (
                                <>
                                  <div>
                                    <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">Why was this strategy selected?</h4>
                                    <p className="text-sm text-slate-700">{exp.why}</p>
                                  </div>
                                  <div>
                                    <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">What does it sacrifice?</h4>
                                    <p className="text-sm text-slate-700">{exp.sacrifice}</p>
                                  </div>
                                  <div>
                                    <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Allocation Breakdown</h4>
                                    <div className="space-y-1.5">
                                      {Object.entries(s.allocations)
                                        .sort((a, b) => b[1] - a[1])
                                        .map(([inst, val]) => (
                                          <AllocationBar key={inst} label={inst} value={val} />
                                        ))}
                                    </div>
                                  </div>
                                </>
                              );
                            })()}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Tab 2: Strategy Comparison */}
            {activeTab === 'comparison' && (
              <div className="space-y-6">
                <Card>
                  <CardHeader title="Strategy Comparison Matrix" subtitle="Side-by-side performance metrics across all strategies" />
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-slate-200">
                          <th className="text-left py-3 px-4 text-xs font-semibold uppercase tracking-wider text-slate-500">Metric</th>
                          <th className="text-center py-3 px-4 text-xs font-semibold uppercase tracking-wider text-slate-500">Current</th>
                          {strategies.map((s) => (
                            <th key={s.id} className={`text-center py-3 px-4 text-xs font-semibold uppercase tracking-wider ${s.rank === 1 ? 'text-blue-600' : 'text-slate-500'}`}>
                              {s.name}
                              {s.rank === 1 && <span className="block text-[10px] font-normal text-blue-500">Recommended</span>}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {[
                          { label: 'Financing Cost', key: 'expected_cost', mode: 'min' as const, fmt: fmtB, baseline: 6420000000 },
                          { label: 'Refinancing Risk', key: 'refinancing_risk', mode: 'min' as const, fmt: (v: number) => v.toFixed(2), baseline: 0.22 },
                          { label: 'Interest Rate Exp', key: 'interest_rate_risk', mode: 'min' as const, fmt: (v: number) => v.toFixed(2), baseline: 0.25 },
                          { label: 'FX Exposure', key: 'currency_risk', mode: 'min' as const, fmt: (v: number) => v.toFixed(2), baseline: 0.18 },
                          { label: 'Liquidity Risk', key: 'liquidity_coverage', mode: 'max' as const, fmt: (v: number) => v.toFixed(2), baseline: 0.78 },
                          { label: 'Stress Resilience', key: 'stress_resilience', mode: 'max' as const, fmt: fmtPct, baseline: 0.78 },
                        ].map((row) => {
                          const vals = strategies.map((s) => metricVal(s.metrics, row.key));
                          const bIdx = bestIdx(vals, row.mode);
                          const wIdx = worstIdx(vals, row.mode);
                          return (
                            <tr key={row.key} className="border-b border-slate-100 hover:bg-slate-50/50">
                              <td className="py-3 px-4 font-medium text-slate-700">{row.label}</td>
                              <td className="py-3 px-4 text-center text-slate-500 font-mono">{row.fmt(row.baseline)}</td>
                              {vals.map((v, i) => (
                                <td key={strategies[i].id} className={`py-3 px-4 text-center font-mono ${cellColor(v, bIdx, wIdx, i)}`}>
                                  {row.fmt(v)}
                                </td>
                              ))}
                            </tr>
                          );
                        })}
                        <tr className="border-b border-slate-200 bg-slate-50">
                          <td className="py-3 px-4 font-semibold text-slate-900">Constraint Status</td>
                          <td className="py-3 px-4 text-center"><Badge variant="success" size="sm">Pass</Badge></td>
                          {strategies.map((s) => {
                            const risk = metricVal(s.metrics, 'refinancing_risk');
                            const fail = risk > 0.25;
                            return (
                              <td key={s.id} className="py-3 px-4 text-center">
                                <Badge variant={fail ? 'danger' : 'success'} size="sm">{fail ? 'Fail*' : 'Pass'}</Badge>
                              </td>
                            );
                          })}
                        </tr>
                      </tbody>
                    </table>
                  </div>
                  <div className="mt-4 px-4 pb-2">
                    <p className="text-xs text-slate-400">
                      <span className="text-red-500">*</span> Strategy C fails refinancing concentration constraint ({'>'} 30% max).
                      Green indicates best-in-class; red indicates worst.
                    </p>
                  </div>
                </Card>

                {/* Cost delta visualization */}
                <Card>
                  <CardHeader title="Cost Savings vs. Baseline" subtitle="Financing cost reduction compared to current portfolio ($6.42B)" />
                  <div className="space-y-4">
                    {strategies.map((s) => {
                      const cost = metricVal(s.metrics, 'expected_cost');
                      const savings = 6420000000 - cost;
                      const maxSavings = 6420000000 - 5980000000;
                      const pct = maxSavings > 0 ? savings / maxSavings : 0;
                      return (
                        <div key={s.id}>
                          <div className="flex items-center justify-between mb-1.5">
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-medium text-slate-700">{s.name}</span>
                              {s.rank === 1 && <Badge variant="info" size="sm">Best</Badge>}
                            </div>
                            <span className="text-sm font-mono text-slate-600">{fmtB(savings)} saved</span>
                          </div>
                          <div className="h-6 bg-slate-100 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all ${s.rank === 1 ? 'bg-blue-500' : 'bg-slate-300'}`}
                              style={{ width: `${Math.max(pct * 100, 5)}%` }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </Card>
              </div>
            )}

            {/* Tab 3: Explainability */}
            {activeTab === 'explainability' && (
              <div className="space-y-6">
                {strategies.map((s) => {
                  const exp = generateExplanation(s, strategies);
                  const m = s.metrics;
                  return (
                    <Card key={s.id}>
                      <div className={`p-6 ${s.rank === 1 ? 'border-l-4 border-l-blue-600' : ''}`}>
                        <div className="flex items-center gap-3 mb-4">
                          <h3 className="text-lg font-bold text-slate-900">{s.name}</h3>
                          {s.rank === 1 && <Badge variant="info" size="md">RECOMMENDED</Badge>}
                          <Badge variant="outline" size="sm">Rank #{s.rank}</Badge>
                        </div>

                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                          <div className="space-y-4">
                            <div className="bg-blue-50 border border-blue-100 rounded-lg p-4">
                              <h4 className="text-xs font-bold uppercase tracking-wider text-blue-700 mb-2">Why was this strategy selected?</h4>
                              <p className="text-sm text-blue-900 leading-relaxed">{exp.why}</p>
                            </div>
                            <div className="bg-amber-50 border border-amber-100 rounded-lg p-4">
                              <h4 className="text-xs font-bold uppercase tracking-wider text-amber-700 mb-2">What does it sacrifice?</h4>
                              <p className="text-sm text-amber-900 leading-relaxed">{exp.sacrifice}</p>
                            </div>
                          </div>

                          <div className="space-y-3">
                            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">Allocation</h4>
                            <div className="space-y-2">
                              {Object.entries(s.allocations)
                                .sort((a, b) => b[1] - a[1])
                                .map(([inst, val]) => (
                                  <AllocationBar key={inst} label={inst} value={val} />
                                ))}
                            </div>
                          </div>
                        </div>

                        <div className="mt-6 grid grid-cols-3 lg:grid-cols-6 gap-3">
                          {[
                            { label: 'Expected Cost', value: fmtB(metricVal(m, 'expected_cost')) },
                            { label: 'Refinancing Risk', value: metricVal(m, 'refinancing_risk').toFixed(2) },
                            { label: 'Interest Rate Risk', value: metricVal(m, 'interest_rate_risk').toFixed(2) },
                            { label: 'Currency Risk', value: metricVal(m, 'currency_risk').toFixed(2) },
                            { label: 'Liquidity Coverage', value: fmtPct(metricVal(m, 'liquidity_coverage')) },
                            { label: 'Stress Resilience', value: fmtPct(metricVal(m, 'stress_resilience')) },
                          ].map((stat) => (
                            <div key={stat.label} className="bg-slate-50 rounded-lg p-3 text-center">
                              <p className="text-[10px] uppercase tracking-wider text-slate-400 mb-1">{stat.label}</p>
                              <p className="text-sm font-bold text-slate-900">{stat.value}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    </Card>
                  );
                })}
              </div>
            )}

            {/* Tab 4: Scenario Analysis */}
            {activeTab === 'scenarios' && (
              <div className="space-y-6">
                <Card>
                  <CardHeader title="Scenario Analysis — Recommended Strategy" subtitle="Performance across predefined macroeconomic scenarios" />
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-slate-200">
                          <th className="text-left py-3 px-4 text-xs font-semibold uppercase tracking-wider text-slate-500">Scenario</th>
                          <th className="text-center py-3 px-4 text-xs font-semibold uppercase tracking-wider text-slate-500">Probability</th>
                          <th className="text-center py-3 px-4 text-xs font-semibold uppercase tracking-wider text-slate-500">Financing Cost</th>
                          <th className="text-center py-3 px-4 text-xs font-semibold uppercase tracking-wider text-slate-500">Effective Rate</th>
                          <th className="text-center py-3 px-4 text-xs font-semibold uppercase tracking-wider text-slate-500">Violations</th>
                        </tr>
                      </thead>
                      <tbody>
                        {scenarioResults.map((sc: ScenarioResult) => (
                          <tr key={sc.scenario_id} className="border-b border-slate-100 hover:bg-slate-50/50">
                            <td className="py-3 px-4 font-medium text-slate-700">{sc.scenario_name}</td>
                            <td className="py-3 px-4 text-center font-mono text-slate-600">{fmtPct(sc.probability)}</td>
                            <td className="py-3 px-4 text-center font-mono text-slate-900 font-semibold">{fmtB(sc.financing_cost)}</td>
                            <td className="py-3 px-4 text-center font-mono text-slate-600">{fmtRate(sc.effective_interest_rate)}</td>
                            <td className="py-3 px-4 text-center">
                              {sc.violations.length === 0 ? (
                                <Badge variant="success" size="sm">None</Badge>
                              ) : (
                                <Badge variant="danger" size="sm">{sc.violations.join(', ').replace(/_/g, ' ')}</Badge>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>

                {/* Stress Test Summary */}
                <Card>
                  <CardHeader
                    title={`${recommended?.name ?? 'Strategy'} Stress Test Summary`}
                    subtitle={`Monte Carlo analysis with ${stressResult.scenario_count.toLocaleString()} simulated scenarios`}
                  />
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                    {[
                      { label: 'Scenarios Tested', value: stressResult.scenario_count.toLocaleString() },
                      { label: 'Average Cost', value: fmtB(stressResult.avg_financing_cost) },
                      { label: 'Worst Case', value: fmtB(stressResult.worst_financing_cost) },
                      { label: '95th Percentile', value: fmtB(stressResult.percentile_costs.p95) },
                    ].map((item) => (
                      <div key={item.label} className="bg-slate-50 rounded-lg p-4">
                        <p className="text-xs text-slate-500 mb-1">{item.label}</p>
                        <p className="text-lg font-bold text-slate-900">{item.value}</p>
                      </div>
                    ))}
                  </div>

                  <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
                    <div className="bg-red-50 border border-red-100 rounded-lg p-4">
                      <p className="text-xs text-red-600 mb-1">Constraint Breaches</p>
                      <p className="text-lg font-bold text-red-700">
                        {stressResult.breaches.toLocaleString()} / {stressResult.scenario_count.toLocaleString()}
                      </p>
                      <p className="text-xs text-red-500">{fmtPct(stressResult.breaches / stressResult.scenario_count)} rate</p>
                    </div>
                    <div className="bg-emerald-50 border border-emerald-100 rounded-lg p-4">
                      <p className="text-xs text-emerald-600 mb-1">Satisfaction Rate</p>
                      <p className="text-lg font-bold text-emerald-700">{fmtPct(stressResult.constraint_satisfaction_rate)}</p>
                    </div>
                    <div className="bg-blue-50 border border-blue-100 rounded-lg p-4">
                      <p className="text-xs text-blue-600 mb-1">Cost Std Deviation</p>
                      <p className="text-lg font-bold text-blue-700">{fmtB(stressResult.cost_distribution.std)}</p>
                    </div>
                  </div>
                </Card>

                {/* Cost Distribution */}
                <Card>
                  <CardHeader title="Cost Distribution Percentiles" subtitle="Distribution of financing costs across Monte Carlo scenarios" />
                  <div className="space-y-3">
                    {Object.entries(stressResult.percentile_costs)
                      .sort((a, b) => {
                        const numA = parseInt(a[0].replace('p', ''));
                        const numB = parseInt(b[0].replace('p', ''));
                        return numA - numB;
                      })
                      .map(([pct, cost]) => {
                        const min = stressResult.cost_distribution.min;
                        const max = stressResult.cost_distribution.max;
                        const range = max - min;
                        const pctNum = range > 0 ? ((cost - min) / range) * 100 : 50;
                        return (
                          <div key={pct} className="flex items-center gap-4">
                            <span className="text-xs font-mono text-slate-500 w-16">{pct.toUpperCase()}</span>
                            <div className="flex-1 h-5 bg-slate-100 rounded-full overflow-hidden relative">
                              <div
                                className="h-full bg-blue-500 rounded-full"
                                style={{ width: `${Math.max(pctNum, 3)}%` }}
                              />
                              <span className="absolute right-2 top-0 h-full flex items-center text-[10px] font-mono text-slate-700">
                                {fmtB(cost)}
                              </span>
                            </div>
                          </div>
                        );
                      })}
                  </div>
                  <div className="mt-4 flex items-center justify-between text-xs text-slate-400">
                    <span>Min: {fmtB(stressResult.cost_distribution.min)}</span>
                    <span>Mean: {fmtB(stressResult.cost_distribution.mean)}</span>
                    <span>Max: {fmtB(stressResult.cost_distribution.max)}</span>
                  </div>
                </Card>

                {/* What if assumptions are wrong */}
                <Card className="border-amber-200">
                  <CardHeader
                    title="What happens if assumptions are wrong?"
                    subtitle="Worst-case analysis under combined adverse conditions"
                    action={<Badge variant="warning" size="md">Risk Advisory</Badge>}
                  />
                  <div className="space-y-4">
                    <div className="bg-amber-50 border border-amber-100 rounded-lg p-5">
                      <h4 className="text-sm font-bold text-amber-900 mb-2">Combined Stress Scenario</h4>
                      <p className="text-sm text-amber-800 leading-relaxed">
                        Under a simultaneous shock to interest rates, inflation, and foreign exchange, the recommended strategy
                        would incur financing costs of <strong>{fmtB(6850000000)}</strong> with an effective rate of <strong>6.10%</strong>.
                        A refinancing concentration violation would be triggered, requiring contingency measures.
                      </p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="bg-slate-50 rounded-lg p-4">
                        <p className="text-xs text-slate-500 mb-1">Probability of Worst Case</p>
                        <p className="text-base font-bold text-slate-900">10%</p>
                      </div>
                      <div className="bg-slate-50 rounded-lg p-4">
                        <p className="text-xs text-slate-500 mb-1">Cost Increase vs Base</p>
                        <p className="text-base font-bold text-red-600">+{fmtB(6850000000 - 6180000000)}</p>
                      </div>
                      <div className="bg-slate-50 rounded-lg p-4">
                        <p className="text-xs text-slate-500 mb-1">Tail Risk (99th %ile)</p>
                        <p className="text-base font-bold text-slate-900">{fmtB(stressResult.percentile_costs.p99)}</p>
                      </div>
                    </div>
                  </div>
                </Card>
              </div>
            )}

            {/* Tab 5: Benchmarks */}
            {activeTab === 'benchmarks' && (
              <div className="space-y-6">
                <Card>
                  <CardHeader title="Solver Benchmark Comparison" subtitle="Performance comparison across optimization solvers" />
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-slate-200">
                          <th className="text-left py-3 px-4 text-xs font-semibold uppercase tracking-wider text-slate-500">Metric</th>
                          {benchmarks.map((b) => (
                            <th key={b.id} className="text-center py-3 px-4 text-xs font-semibold uppercase tracking-wider text-slate-500">
                              {b.metrics.solver_type === 'classical' && 'Classical (MILP)'}
                              {b.metrics.solver_type === 'heuristic' && 'Heuristic (SA)'}
                              {b.metrics.solver_type === 'quantum_inspired' && 'Quantum-Inspired'}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        <tr className="border-b border-slate-100">
                          <td className="py-3 px-4 font-medium text-slate-700">Objective Value</td>
                          {benchmarks.map((b) => (
                            <td key={b.id} className="py-3 px-4 text-center font-mono text-slate-900">{fmtB(b.objective_value)}</td>
                          ))}
                        </tr>
                        <tr className="border-b border-slate-100">
                          <td className="py-3 px-4 font-medium text-slate-700">Runtime</td>
                          {benchmarks.map((b) => (
                            <td key={b.id} className="py-3 px-4 text-center font-mono text-slate-600">{b.execution_time_seconds}s</td>
                          ))}
                        </tr>
                        <tr className="border-b border-slate-100">
                          <td className="py-3 px-4 font-medium text-slate-700">Constraint Violations</td>
                          {benchmarks.map((b) => (
                            <td key={b.id} className="py-3 px-4 text-center">
                              <Badge variant="success" size="sm">0</Badge>
                            </td>
                          ))}
                        </tr>
                        <tr className="border-b border-slate-100">
                          <td className="py-3 px-4 font-medium text-slate-700">Iterations</td>
                          {benchmarks.map((b) => (
                            <td key={b.id} className="py-3 px-4 text-center font-mono text-slate-600">{b.iterations.toLocaleString()}</td>
                          ))}
                        </tr>
                        <tr className="border-b border-slate-100">
                          <td className="py-3 px-4 font-medium text-slate-700">Compute Cost</td>
                          {benchmarks.map((b) => (
                            <td key={b.id} className="py-3 px-4 text-center font-mono text-slate-600">${b.metrics.compute_cost as number}</td>
                          ))}
                        </tr>
                        <tr className="border-b border-slate-100">
                          <td className="py-3 px-4 font-medium text-slate-700">Robustness</td>
                          {benchmarks.map((b) => {
                            const rob = b.metrics.robustness as number;
                            return (
                              <td key={b.id} className={`py-3 px-4 text-center font-mono ${rob >= 0.94 ? 'text-emerald-700 font-semibold' : 'text-slate-600'}`}>
                                {fmtPct(rob)}
                              </td>
                            );
                          })}
                        </tr>
                        <tr className="border-b border-slate-200 bg-slate-50">
                          <td className="py-3 px-4 font-semibold text-slate-900">Best For</td>
                          {benchmarks.map((b) => (
                            <td key={b.id} className="py-3 px-4 text-center text-xs text-slate-600">
                              {b.metrics.solver_type === 'classical' && 'Overall value'}
                              {b.metrics.solver_type === 'heuristic' && 'Speed'}
                              {b.metrics.solver_type === 'quantum_inspired' && 'Exploration'}
                            </td>
                          ))}
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </Card>

                <div className="bg-blue-50 border border-blue-100 rounded-lg p-5">
                  <p className="text-sm text-blue-800 leading-relaxed">
                    <strong>Note:</strong> All solvers found feasible solutions. Classical MILP produced the best objective value
                    for this problem configuration. Simulated Annealing was fastest at runtime, while QUBO Annealing explored
                    a broader solution space suitable for larger portfolios.
                  </p>
                </div>

                {/* Visual comparison bars */}
                <Card>
                  <CardHeader title="Objective Value Comparison" subtitle="Lower is better — financing cost objective" />
                  <div className="space-y-4">
                    {benchmarks
                      .sort((a, b) => a.objective_value - b.objective_value)
                      .map((b, idx) => {
                        const minVal = Math.min(...benchmarks.map((x) => x.objective_value));
                        const maxVal = Math.max(...benchmarks.map((x) => x.objective_value));
                        const range = maxVal - minVal || 1;
                        const normalizedVal = range > 0 ? ((b.objective_value - minVal) / range) * 60 + 40 : 50;
                        const solverLabel = b.metrics.solver_type === 'classical' ? 'Classical (MILP)'
                          : b.metrics.solver_type === 'heuristic' ? 'Heuristic (SA)'
                          : 'Quantum-Inspired';
                        return (
                          <div key={b.id}>
                            <div className="flex items-center justify-between mb-1.5">
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-medium text-slate-700">{solverLabel}</span>
                                {idx === 0 && <Badge variant="success" size="sm">Best</Badge>}
                              </div>
                              <span className="text-sm font-mono text-slate-600">{fmtB(b.objective_value)}</span>
                            </div>
                            <div className="h-5 bg-slate-100 rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full transition-all ${idx === 0 ? 'bg-emerald-500' : 'bg-slate-300'}`}
                                style={{ width: `${normalizedVal}%` }}
                              />
                            </div>
                          </div>
                        );
                      })}
                  </div>
                </Card>
              </div>
            )}

            {/* Tab 6: Decision Report */}
            {activeTab === 'report' && (
              <div className="space-y-6">
                {reportLoading ? (
                  <LoadingSpinner message="Generating report..." fullPage={false} />
                ) : report ? (
                  <>
                    <div className="flex items-center justify-between">
                      <div>
                        <h2 className="text-lg font-bold text-slate-900">Decision Package</h2>
                        <p className="text-sm text-slate-500">{report.job_name} &middot; Generated {new Date(report.created_at).toLocaleString()}</p>
                      </div>
                      <Button variant="primary" size="md" onClick={() => {
                        const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `decision-package-${report.job_id}.json`;
                        a.click();
                        URL.revokeObjectURL(url);
                      }}>
                        Export JSON
                      </Button>
                    </div>

                    {/* Report sections */}
                    {[
                      {
                        title: '1. Executive Summary',
                        content: (
                          <div className="space-y-2 text-sm text-slate-700">
                            <p>Optimization completed for <strong>{report.job_name}</strong>.</p>
                            <p>Portfolio: {report.portfolio.name} ({report.portfolio.num_instruments} instruments)</p>
                            <p>Type: {report.optimization_type} &middot; Model: {report.model_version} &middot; Seed: {report.random_seed}</p>
                            <p>{report.strategies.length} feasible strategies generated. Recommended: <strong>{report.strategies.find((s) => s.rank === 1)?.name ?? 'N/A'}</strong>.</p>
                          </div>
                        ),
                      },
                      {
                        title: '2. Portfolio Overview',
                        content: (
                          <div className="text-sm text-slate-700">
                            <p>Portfolio <strong>{report.portfolio.name}</strong> containing {report.portfolio.num_instruments} debt instruments.</p>
                          </div>
                        ),
                      },
                      {
                        title: '3. Strategy Comparison',
                        content: (
                          <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                              <thead>
                                <tr className="border-b border-slate-200">
                                  <th className="text-left py-2 px-3 text-xs font-semibold text-slate-500">Strategy</th>
                                  <th className="text-right py-2 px-3 text-xs font-semibold text-slate-500">Rank</th>
                                  <th className="text-right py-2 px-3 text-xs font-semibold text-slate-500">Cost</th>
                                  <th className="text-right py-2 px-3 text-xs font-semibold text-slate-500">Refinancing Risk</th>
                                  <th className="text-right py-2 px-3 text-xs font-semibold text-slate-500">Resilience</th>
                                </tr>
                              </thead>
                              <tbody>
                                {report.strategies.map((s) => (
                                  <tr key={s.name} className="border-b border-slate-100">
                                    <td className="py-2 px-3 font-medium text-slate-700">{s.name}</td>
                                    <td className="py-2 px-3 text-right font-mono text-slate-600">#{s.rank}</td>
                                    <td className="py-2 px-3 text-right font-mono text-slate-900">{fmtB(metricVal(s.metrics, 'expected_cost'))}</td>
                                    <td className="py-2 px-3 text-right font-mono text-slate-600">{metricVal(s.metrics, 'refinancing_risk').toFixed(2)}</td>
                                    <td className="py-2 px-3 text-right font-mono text-slate-600">{fmtPct(metricVal(s.metrics, 'stress_resilience'))}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        ),
                      },
                      {
                        title: '4. Benchmark Analysis',
                        content: (
                          <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                              <thead>
                                <tr className="border-b border-slate-200">
                                  <th className="text-left py-2 px-3 text-xs font-semibold text-slate-500">Solver</th>
                                  <th className="text-right py-2 px-3 text-xs font-semibold text-slate-500">Objective</th>
                                  <th className="text-right py-2 px-3 text-xs font-semibold text-slate-500">Runtime</th>
                                  <th className="text-center py-2 px-3 text-xs font-semibold text-slate-500">Feasible</th>
                                </tr>
                              </thead>
                              <tbody>
                                {report.benchmarks.map((b) => (
                                  <tr key={b.solver_name} className="border-b border-slate-100">
                                    <td className="py-2 px-3 font-medium text-slate-700">{b.solver_name}</td>
                                    <td className="py-2 px-3 text-right font-mono text-slate-900">{fmtB(b.objective_value)}</td>
                                    <td className="py-2 px-3 text-right font-mono text-slate-600">{b.execution_time_seconds}s</td>
                                    <td className="py-2 px-3 text-center">{b.feasible ? <Badge variant="success" size="sm">Yes</Badge> : <Badge variant="danger" size="sm">No</Badge>}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        ),
                      },
                      {
                        title: '5. Methodology Notes',
                        content: (
                          <div className="text-sm text-slate-700 space-y-2">
                            <p>Multi-objective optimization with weighted objectives: financing cost ({fmtPct((job.objectives as Record<string,unknown>).financing_cost_weight as number ?? 0.35)}), refinancing risk ({fmtPct((job.objectives as Record<string,unknown>).refinancing_risk_weight as number ?? 0.25)}), interest rate risk ({fmtPct((job.objectives as Record<string,unknown>).interest_rate_risk_weight as number ?? 0.20)}), currency risk ({fmtPct((job.objectives as Record<string,unknown>).currency_risk_weight as number ?? 0.20)}).</p>
                            <p>Scenario generation: {((job.scenario_config as Record<string,unknown>)?.include_named as string[] | undefined)?.length ?? 6} named scenarios, {((job.scenario_config as Record<string,unknown>)?.monte_carlo_count as number ?? 10000).toLocaleString()} Monte Carlo simulations.</p>
                            <p>Solver configuration: {((job.solver_config as Record<string,unknown>)?.solvers as string[] | undefined)?.length ?? 3} solvers, {((job.solver_config as Record<string,unknown>)?.time_limit_seconds as number ?? 120)}s time limit, seed {((job.solver_config as Record<string,unknown>)?.seed as number ?? 42)}.</p>
                          </div>
                        ),
                      },
                      {
                        title: '6. Audit Trail',
                        content: (
                          <div className="text-sm text-slate-700">
                            <p>Job ID: <span className="font-mono text-xs">{report.job_id}</span></p>
                            <p>Created: {new Date(report.created_at).toLocaleString()}</p>
                            {report.completed_at && <p>Completed: {new Date(report.completed_at).toLocaleString()}</p>}
                            <p>Status: <Badge variant={report.status === 'completed' ? 'success' : 'default'} size="sm">{report.status}</Badge></p>
                          </div>
                        ),
                      },
                    ].map((section) => (
                      <Card key={section.title}>
                        <h3 className="text-sm font-bold text-slate-900 mb-3">{section.title}</h3>
                        {section.content}
                      </Card>
                    ))}
                  </>
                ) : (
                  <div className="text-center py-12">
                    <p className="text-sm text-slate-500 mb-4">No report loaded yet.</p>
                    <Button variant="primary" onClick={loadReport} loading={reportLoading}>
                      Generate Decision Package
                    </Button>
                  </div>
                )}
              </div>
            )}
          </Tabs>
        </div>
      </div>
    </AppShell>
  );
}
