import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpDown, Loader2, Trophy, Zap, Clock, AlertTriangle } from 'lucide-react';
import { api } from '../api';
import type { BenchmarkRow } from '../types';

function formatTime(seconds: number): string {
  if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  return `${(seconds / 60).toFixed(1)}m`;
}

function formatCost(value: number): string {
  if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
  if (value >= 1e3) return `$${(value / 1e3).toFixed(1)}K`;
  return `$${value.toFixed(0)}`;
}

function solverTypeColor(type: string): string {
  switch (type) {
    case 'exact': return '#2563eb';
    case 'heuristic': return '#7c3aed';
    case 'quantum': return '#06b6d4';
    default: return '#6b7280';
  }
}

function solverTypeBg(type: string): string {
  switch (type) {
    case 'exact': return 'rgba(37,99,235,0.1)';
    case 'heuristic': return 'rgba(124,58,237,0.1)';
    case 'quantum': return 'rgba(6,182,212,0.1)';
    default: return 'rgba(107,114,128,0.1)';
  }
}

export default function SolverTournamentPage() {
  const [solvers, setSolvers] = useState<BenchmarkRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSolver, setSelectedSolver] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.solvers.leaderboard();
      setSolvers(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load leaderboard');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const maxObjective = solvers.length > 0
    ? Math.max(...solvers.map((s) => s.objective_value))
    : 1;

  const maxRuntime = solvers.length > 0
    ? Math.max(...solvers.map((s) => s.runtime))
    : 1;

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
        <div style={{ textAlign: 'center', color: '#6b7280' }}>
          <Loader2 size={32} style={{ animation: 'spin 1s linear infinite', marginBottom: 12 }} />
          <p>Loading solver leaderboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
        <div style={{ textAlign: 'center', maxWidth: 400 }}>
          <p style={{ fontSize: 18, fontWeight: 600, marginBottom: 8, color: '#dc2626' }}>Failed to load leaderboard</p>
          <p style={{ color: '#6b7280', marginBottom: 16 }}>{error}</p>
          <button
            type="button"
            onClick={() => void load()}
            style={{ padding: '8px 20px', borderRadius: 8, border: '1px solid #e5e7eb', background: '#fff', cursor: 'pointer', fontWeight: 500 }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const selected = solvers.find((s) => s.solver_name === selectedSolver);

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, margin: 0 }}>Solver Tournament</h1>
        <p style={{ fontSize: 13, color: '#6b7280', margin: '4px 0 0' }}>
          Compare solver performance across cost, risk, speed, and feasibility.
        </p>
      </div>

      {/* Leaderboard */}
      {solvers.length === 0 ? (
        <article className="panel" style={{ padding: 48, textAlign: 'center' }}>
          <Trophy size={48} style={{ color: '#d1d5db', marginBottom: 16 }} />
          <p style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>No benchmark data yet</p>
          <p style={{ color: '#6b7280', marginBottom: 16 }}>Run an optimization to see solver comparison results.</p>
          <Link
            to="/optimizations/new"
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              padding: '8px 16px', borderRadius: 8, border: 'none',
              background: '#2563eb', color: '#fff', fontSize: 13, fontWeight: 600,
              textDecoration: 'none',
            }}
          >
            <Zap size={14} /> Run Optimization
          </Link>
        </article>
      ) : (
        <>
          {/* Summary Cards */}
          <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12, marginBottom: 24 }}>
            {[
              { value: `${solvers.length}`, label: 'Solvers compared', icon: <Trophy size={16} /> },
              { value: solvers[0]?.solver_name || '—', label: 'Top performer', icon: <Zap size={16} /> },
              { value: formatTime(solvers[0]?.runtime || 0), label: 'Fastest time', icon: <Clock size={16} /> },
              { value: `${solvers.filter((s) => s.feasible).length}/${solvers.length}`, label: 'Feasible solutions', icon: <AlertTriangle size={16} /> },
            ].map(({ value, label, icon }) => (
              <article key={label} className="stat-card" style={{ borderTop: '3px solid #2563eb' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4, color: '#6b7280' }}>
                  {icon}
                  <span className="stat-label" style={{ margin: 0 }}>{label}</span>
                </div>
                <div className="stat-value" style={{ fontSize: 18 }}>{value}</div>
              </article>
            ))}
          </section>

          {/* Main Table */}
          <article className="panel">
            <div className="panel-header">
              <h2>Leaderboard</h2>
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table className="q-table" aria-label="Solver leaderboard">
                <thead>
                  <tr>
                    <th style={{ width: 40 }}>#</th>
                    <th>Solver</th>
                    <th>Type</th>
                    <th>Objective</th>
                    <th>Financing Cost</th>
                    <th>Risk</th>
                    <th>Runtime</th>
                    <th>Violations</th>
                    <th>Feasible</th>
                    <th>Note</th>
                  </tr>
                </thead>
                <tbody>
                  {solvers.map((solver) => (
                    <tr
                      key={solver.solver_name}
                      onClick={() => setSelectedSolver(solver.solver_name === selectedSolver ? null : solver.solver_name)}
                      style={{ cursor: 'pointer', background: solver.solver_name === selectedSolver ? 'rgba(37,99,235,0.05)' : undefined }}
                    >
                      <td style={{ fontWeight: 700, color: solver.rank === 1 ? '#d97706' : '#6b7280' }}>
                        {solver.rank === 1 ? '🏆' : solver.rank}
                      </td>
                      <td style={{ fontWeight: 600 }}>{solver.solver_name}</td>
                      <td>
                        <span style={{
                          display: 'inline-block', padding: '2px 8px', borderRadius: 6,
                          fontSize: 11, fontWeight: 600, textTransform: 'uppercase',
                          background: solverTypeBg(solver.solver_type),
                          color: solverTypeColor(solver.solver_type),
                        }}>
                          {solver.solver_type}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <div style={{ flex: 1, height: 6, background: '#f3f4f6', borderRadius: 3, overflow: 'hidden' }}>
                            <div style={{
                              height: '100%', borderRadius: 3,
                              width: `${(solver.objective_value / maxObjective) * 100}%`,
                              background: solver.rank === 1 ? '#16a34a' : '#2563eb',
                            }} />
                          </div>
                          <span style={{ fontSize: 12, fontWeight: 600, minWidth: 60 }}>{formatCost(solver.objective_value)}</span>
                        </div>
                      </td>
                      <td>{formatCost(solver.financing_cost)}</td>
                      <td>{formatCost(solver.risk_total)}</td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <div style={{ width: 40, height: 4, background: '#f3f4f6', borderRadius: 2, overflow: 'hidden' }}>
                            <div style={{
                              height: '100%', borderRadius: 2,
                              width: `${(solver.runtime / maxRuntime) * 100}%`,
                              background: solver.runtime < maxRuntime * 0.3 ? '#16a34a' : solver.runtime < maxRuntime * 0.7 ? '#d97706' : '#dc2626',
                            }} />
                          </div>
                          <span style={{ fontSize: 12 }}>{formatTime(solver.runtime)}</span>
                        </div>
                      </td>
                      <td style={{ color: solver.constraint_violations > 0 ? '#dc2626' : '#16a34a', fontWeight: 600 }}>
                        {solver.constraint_violations}
                      </td>
                      <td>
                        <span style={{
                          display: 'inline-block', padding: '2px 8px', borderRadius: 6,
                          fontSize: 11, fontWeight: 600,
                          background: solver.feasible ? 'rgba(22,163,74,0.1)' : 'rgba(220,38,38,0.1)',
                          color: solver.feasible ? '#16a34a' : '#dc2626',
                        }}>
                          {solver.feasible ? 'Yes' : 'No'}
                        </span>
                      </td>
                      <td style={{ fontSize: 12, color: '#6b7280' }}>{solver.optimality_note}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </article>

          {/* Detail Panel */}
          {selected && (
            <article className="panel" style={{ marginTop: 20 }}>
              <div className="panel-header">
                <h2>{selected} — Details</h2>
                <button className="soft-button" onClick={() => setSelectedSolver(null)}>Close</button>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, padding: '0 16px 16px' }}>
                {[
                  { label: 'Objective Value', value: formatCost(selected.objective_value) },
                  { label: 'Financing Cost', value: formatCost(selected.financing_cost) },
                  { label: 'Risk Total', value: formatCost(selected.risk_total) },
                  { label: 'Runtime', value: formatTime(selected.runtime) },
                  { label: 'Solver Type', value: selected.solver_type },
                  { label: 'Execution Backend', value: selected.execution_backend },
                  { label: 'Constraint Violations', value: `${selected.constraint_violations}` },
                  { label: 'Robustness', value: `${(selected.robustness * 100).toFixed(0)}%` },
                  { label: 'Compute Cost', value: formatCost(selected.compute_cost) },
                  { label: 'Optimality Note', value: selected.optimality_note },
                ].map(({ label, value }) => (
                  <div key={label}>
                    <p style={{ fontSize: 11, color: '#6b7280', textTransform: 'uppercase', marginBottom: 4 }}>{label}</p>
                    <p style={{ fontSize: 15, fontWeight: 600 }}>{value}</p>
                  </div>
                ))}
              </div>
            </article>
          )}
        </>
      )}
    </div>
  );
}
