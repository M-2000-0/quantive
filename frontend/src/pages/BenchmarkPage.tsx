import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api';
import type { BenchmarkResult } from '../types';
import AppShell from '../components/layout/AppShell';
import Card, { CardHeader } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import EmptyState from '../components/ui/EmptyState';
import { formatCurrency, formatRuntime } from '../utils';

const TYPE_BADGE: Record<string, { label: string; variant: 'info' | 'success' | 'outline' }> = {
  classical: { label: 'Classical', variant: 'info' },
  heuristic: { label: 'Heuristic', variant: 'success' },
  quantum_inspired: { label: 'Quantum-Inspired', variant: 'outline' },
};

const METHODOLOGY_NOTES = [
  {
    type: 'Classical',
    color: 'border-blue-500 bg-blue-50/50',
    dot: 'bg-blue-500',
    description: 'Mixed-Integer Linear Programming (MILP) using branch-and-bound with CBC solver. Guarantees optimality within time limit.',
  },
  {
    type: 'Heuristic',
    color: 'border-emerald-500 bg-emerald-50/50',
    dot: 'bg-emerald-500',
    description: 'Simulated annealing with feasibility repair. Faster but may not find global optimum.',
  },
  {
    type: 'Quantum-Inspired',
    color: 'border-violet-500 bg-violet-50/50',
    dot: 'bg-violet-500',
    description: 'QUBO-encoded binary annealing on classical simulator. Explores solution space differently from traditional methods.',
  },
];

export default function BenchmarkPage() {
  const { id } = useParams<{ id: string }>();
  const [benchmarks, setBenchmarks] = useState<BenchmarkResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id) {
      setLoading(false);
      return;
    }
    api.optimizations.benchmarks(id)
      .then(setBenchmarks)
      .catch((e) => setError(e.message || 'Failed to load benchmarks'))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <AppShell>
        <LoadingSpinner message="Loading benchmarks..." />
      </AppShell>
    );
  }

  if (!id) {
    return (
      <AppShell>
        <div className="px-8 py-6 max-w-[1440px] mx-auto">
          <EmptyState
            icon={<span className="text-4xl">&#x1F4CA;</span>}
            title="Select an optimization"
            description="Navigate from an optimization to view its solver benchmarks."
          />
        </div>
      </AppShell>
    );
  }

  const bestObjective = benchmarks.length > 0 ? Math.min(...benchmarks.map((b) => b.objective_value)) : 0;
  const bestRuntime = benchmarks.length > 0 ? Math.min(...benchmarks.map((b) => b.execution_time_seconds)) : 0;

  return (
    <AppShell>
      <div className="px-8 py-6 max-w-[1440px] mx-auto">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-slate-900">Performance Benchmarks</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Comparison of optimization methodologies
          </p>
        </div>

        {error && (
          <div className="mb-6 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            {error}
          </div>
        )}

        <div className="mb-6 rounded-md border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">
          All solvers are run against the same problem configuration for fair comparison.
        </div>

        {benchmarks.length === 0 ? (
          <EmptyState
            icon={<span className="text-4xl">&#x2699;</span>}
            title="No benchmarks yet"
            description="Run an optimization to see solver benchmarks."
          />
        ) : (
          <Card padding={false} className="mb-8">
            <CardHeader
              title="Solver Comparison"
              subtitle={`Results from ${benchmarks.length} solver${benchmarks.length !== 1 ? 's' : ''}`}
            />
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/40">
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Rank</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Solver</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Type</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Runtime</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Objective Value</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">Feasible</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Iterations</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/25">
                  {benchmarks.map((b, idx) => {
                    const typeInfo = TYPE_BADGE[b.metrics?.solver_type as string] ?? { label: (b.metrics?.solver_type as string) || 'Unknown', variant: 'default' as const };
                    const isBestObj = b.objective_value === bestObjective;
                    const isBestTime = b.execution_time_seconds === bestRuntime;

                    return (
                      <tr key={b.id} className="hover:bg-white/40 transition-colors">
                        <td className="px-4 py-3.5">
                          <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-slate-900 text-xs font-bold text-white">
                            {idx + 1}
                          </span>
                        </td>
                        <td className="px-4 py-3.5 font-medium text-slate-900">{b.solver_name}</td>
                        <td className="px-4 py-3.5">
                          <Badge variant={typeInfo.variant}>{typeInfo.label}</Badge>
                        </td>
                        <td className={`px-4 py-3.5 text-right tabular-nums font-medium ${isBestTime ? 'text-emerald-700 bg-emerald-50 rounded' : 'text-slate-700'}`}>
                          {formatRuntime(b.execution_time_seconds)}
                        </td>
                        <td className={`px-4 py-3.5 text-right tabular-nums font-medium ${isBestObj ? 'text-emerald-700 bg-emerald-50 rounded' : 'text-slate-700'}`}>
                          {formatCurrency(b.objective_value)}
                        </td>
                        <td className="px-4 py-3.5 text-center">
                          {b.feasible ? (
                            <span className="inline-flex items-center justify-center h-5 w-5 rounded-full bg-emerald-100 text-emerald-700 text-xs font-bold">&#x2713;</span>
                          ) : (
                            <span className="inline-flex items-center justify-center h-5 w-5 rounded-full bg-red-100 text-red-700 text-xs font-bold">&#x2717;</span>
                          )}
                        </td>
                        <td className="px-4 py-3.5 text-right tabular-nums text-slate-600">
                          {b.iterations.toLocaleString()}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        )}

        <Card>
          <CardHeader title="Methodology Notes" subtitle="Technical details of each optimization approach" />
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            {METHODOLOGY_NOTES.map((note) => (
              <div key={note.type} className={`rounded-lg border-l-4 p-5 ${note.color}`}>
                <div className="flex items-center gap-2 mb-2">
                  <span className={`h-2 w-2 rounded-full ${note.dot}`} />
                  <h4 className="text-sm font-semibold text-slate-900">{note.type}</h4>
                </div>
                <p className="text-sm text-slate-600 leading-relaxed">{note.description}</p>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </AppShell>
  );
}
