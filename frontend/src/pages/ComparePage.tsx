import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { api } from '../api';

interface Strategy {
  name: string;
  description: string;
  rank: number;
  metrics: Record<string, unknown>;
  stress_test_results: Record<string, unknown>;
}

interface Benchmark {
  solver_name: string;
  execution_time_seconds: number;
  objective_value: number;
  feasible: boolean;
  iterations: number;
  metrics: Record<string, unknown>;
}

interface Report {
  job_id: string;
  job_name: string;
  optimization_type: string;
  created_at: string;
  completed_at: string;
  portfolio: { name: string; num_instruments: number };
  strategies: Strategy[];
  benchmarks: Benchmark[];
  summary: Record<string, unknown>;
}

function formatCurrency(value: number): string {
  if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `$${(value / 1e3).toFixed(1)}K`;
  return `$${value.toFixed(0)}`;
}

function formatNumber(value: unknown): string {
  if (typeof value === 'number') {
    if (Math.abs(value) >= 1e6) return formatCurrency(value);
    if (Number.isInteger(value)) return value.toLocaleString();
    return value.toFixed(2);
  }
  if (typeof value === 'string') return value;
  return String(value ?? '—');
}

function MetricRow({ label, values }: { label: string; values: (string | number)[] }) {
  const best = values.reduce((b, v, i) => (typeof v === 'number' && v < (typeof values[b] === 'number' ? (values[b] as number) : Infinity) ? i : b), 0);
  return (
    <tr>
      <td style={{ fontSize: 13, fontWeight: 500, padding: '8px 12px', borderBottom: '1px solid #f3f4f6' }}>{label}</td>
      {values.map((v, i) => (
        <td key={i} style={{ fontSize: 13, padding: '8px 12px', borderBottom: '1px solid #f3f4f6', textAlign: 'right', fontWeight: i === best ? 600 : 400, color: i === best ? '#16a34a' : '#374151' }}>
          {formatNumber(v)}
        </td>
      ))}
    </tr>
  );
}

export default function ComparePage() {
  const [params] = useSearchParams();
  const jobIds = useMemo(() => {
    const raw = params.get('jobs') ?? '';
    return raw.split(',').filter(Boolean);
  }, [params]);

  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (jobIds.length === 0) {
      setError('No jobs to compare. Add job IDs to the URL.');
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const results = await Promise.all(
        jobIds.map(async (id) => {
          try {
            return await api.optimizations.report(id) as unknown as Report;
          } catch {
            return null;
          }
        }),
      );
      const valid = results.filter(Boolean) as Report[];
      if (valid.length === 0) {
        setError('Could not load any optimization reports.');
      }
      setReports(valid);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load reports');
    } finally {
      setLoading(false);
    }
  }, [jobIds]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return (
      <div style={{ padding: 60, textAlign: 'center', color: '#6b7280' }}>
        <Loader2 size={24} style={{ animation: 'spin 1s linear infinite' }} />
        <p>Loading comparison...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 60, textAlign: 'center' }}>
        <p style={{ color: '#dc2626', marginBottom: 12 }}>{error}</p>
        <Link to="/optimizations" style={{ color: '#2563eb', fontSize: 14 }}>Back to optimizations</Link>
      </div>
    );
  }

  if (reports.length < 2) {
    return (
      <div style={{ padding: 60, textAlign: 'center', color: '#6b7280' }}>
        <p>Select at least 2 completed optimizations to compare.</p>
        <Link to="/optimizations" style={{ color: '#2563eb', fontSize: 14, marginTop: 8, display: 'inline-block' }}>Back to optimizations</Link>
      </div>
    );
  }

  // Collect all unique metric keys from strategies
  const allMetricKeys = new Set<string>();
  reports.forEach((r) => r.strategies.forEach((s) => Object.keys(s.metrics ?? {}).forEach((k) => allMetricKeys.add(k))));
  const metricKeys = Array.from(allMetricKeys);

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Link to="/optimizations" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 13, color: '#6b7280', textDecoration: 'none', marginBottom: 12 }}>
          <ArrowLeft size={14} /> Back to optimizations
        </Link>
        <h1>Compare Optimizations</h1>
      </div>

      {/* Summary Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: `repeat(${reports.length}, 1fr)`, gap: 16, marginBottom: 24 }}>
        {reports.map((r) => (
          <div key={r.job_id} className="panel" style={{ padding: 16 }}>
            <h3 style={{ fontSize: 15, fontWeight: 600, margin: '0 0 8px' }}>{r.job_name}</h3>
            <div style={{ fontSize: 12, color: '#6b7280' }}>
              <p>Portfolio: {r.portfolio.name}</p>
              <p>Type: {r.optimization_type}</p>
              <p>Strategies: {r.strategies.length}</p>
              <p>Completed: {r.completed_at ? new Date(r.completed_at).toLocaleDateString() : '—'}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Top Strategy Comparison */}
      <div className="panel" style={{ padding: 20, marginBottom: 24 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Top Strategy Comparison</h2>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                <th style={{ fontSize: 12, fontWeight: 600, color: '#6b7280', padding: '8px 12px', textAlign: 'left' }}>Metric</th>
                {reports.map((r, i) => (
                  <th key={i} style={{ fontSize: 12, fontWeight: 600, color: '#6b7280', padding: '8px 12px', textAlign: 'right' }}>
                    {r.job_name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <MetricRow label="Strategy Name" values={reports.map((r) => r.strategies[0]?.name ?? '—')} />
              <MetricRow label="Rank" values={reports.map((r) => r.strategies[0]?.rank ?? 0)} />
              {metricKeys.map((key) => (
                <MetricRow
                  key={key}
                  label={key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                  values={reports.map((r) => r.strategies[0]?.metrics?.[key] as string | number ?? '—')}
                />
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Solver Benchmarks */}
      <div className="panel" style={{ padding: 20 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Solver Benchmarks</h2>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                <th style={{ fontSize: 12, fontWeight: 600, color: '#6b7280', padding: '8px 12px', textAlign: 'left' }}>Solver</th>
                <th style={{ fontSize: 12, fontWeight: 600, color: '#6b7280', padding: '8px 12px', textAlign: 'right' }}>Objective</th>
                <th style={{ fontSize: 12, fontWeight: 600, color: '#6b7280', padding: '8px 12px', textAlign: 'right' }}>Time (s)</th>
                <th style={{ fontSize: 12, fontWeight: 600, color: '#6b7280', padding: '8px 12px', textAlign: 'right' }}>Feasible</th>
                <th style={{ fontSize: 12, fontWeight: 600, color: '#6b7280', padding: '8px 12px', textAlign: 'right' }}>Iterations</th>
              </tr>
            </thead>
            <tbody>
              {reports.flatMap((r) => r.benchmarks.map((b, i) => ({ ...b, jobName: r.job_name, idx: i }))).map((b) => (
                <tr key={`${b.jobName}-${b.solver_name}`}>
                  <td style={{ fontSize: 13, padding: '8px 12px', borderBottom: '1px solid #f3f4f6' }}>
                    <span style={{ fontSize: 11, color: '#9ca3af' }}>{b.jobName}</span><br />
                    {b.solver_name}
                  </td>
                  <td style={{ fontSize: 13, padding: '8px 12px', borderBottom: '1px solid #f3f4f6', textAlign: 'right' }}>{formatNumber(b.objective_value)}</td>
                  <td style={{ fontSize: 13, padding: '8px 12px', borderBottom: '1px solid #f3f4f6', textAlign: 'right' }}>{b.execution_time_seconds?.toFixed(2) ?? '—'}</td>
                  <td style={{ fontSize: 13, padding: '8px 12px', borderBottom: '1px solid #f3f4f6', textAlign: 'right', color: b.feasible ? '#16a34a' : '#dc2626' }}>{b.feasible ? 'Yes' : 'No'}</td>
                  <td style={{ fontSize: 13, padding: '8px 12px', borderBottom: '1px solid #f3f4f6', textAlign: 'right' }}>{b.iterations ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
