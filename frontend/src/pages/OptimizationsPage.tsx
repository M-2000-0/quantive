import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { api } from '../api';
import type { OptimizationJob } from '../types';

const TERMINAL = new Set(['completed', 'failed', 'cancelled']);

function statusTone(status: string): string {
  const s = status.toLowerCase();
  if (s === 'completed') return '#16a34a';
  if (s === 'failed') return '#dc2626';
  if (s === 'cancelled') return '#6b7280';
  if (s === 'running') return '#2563eb';
  return '#d97706'; // queued / pending
}

function progressPct(job: OptimizationJob): number {
  if (typeof job.progress !== 'number' || Number.isNaN(job.progress)) return 0;
  // Backend stores 0.0–1.0; tolerate 0–100 just in case
  const p = job.progress <= 1 ? job.progress * 100 : job.progress;
  return Math.min(100, Math.max(0, Math.round(p)));
}

export default function OptimizationsPage() {
  const [jobs, setJobs] = useState<OptimizationJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cancellingId, setCancellingId] = useState<string | null>(null);
  const pollRef = useRef<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = (await api.optimizations.list()) as unknown as
        | OptimizationJob[]
        | { data: OptimizationJob[] };
      setJobs(Array.isArray(res) ? res : (res.data ?? []));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load optimizations');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // Poll active jobs every 2s via JSON poll endpoint; stop when all terminal
  useEffect(() => {
    if (pollRef.current !== null) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
    const active = jobs.filter((j) => !TERMINAL.has(j.status.toLowerCase()));
    if (active.length === 0) return;

    const tick = async () => {
      try {
        const updated = await Promise.all(
          active.map(async (j) => {
            try {
              const p = await api.optimizations.progress(j.id);
              return { ...j, status: p.status, progress: p.status.toLowerCase() === 'completed' ? 1 : j.progress } as OptimizationJob;
            } catch {
              // Fall back to full job fetch (also updates progress field)
              try {
                return await api.optimizations.get(j.id);
              } catch {
                return j;
              }
            }
          }),
        );
        setJobs((prev) => {
          const byId = new Map(updated.map((u) => [u.id, u]));
          return prev.map((j) => byId.get(j.id) ?? j);
        });
      } catch {
        // ignore transient poll errors; next tick retries
      }
    };

    pollRef.current = window.setInterval(() => void tick(), 2000);
    return () => {
      if (pollRef.current !== null) window.clearInterval(pollRef.current);
      pollRef.current = null;
    };
  }, [jobs.map((j) => `${j.id}:${j.status}`).join(',')]);

  async function cancelJob(id: string) {
    setCancellingId(id);
    try {
      await api.optimizations.cancel(id);
      setJobs((prev) => prev.map((j) => (j.id === id ? { ...j, status: 'cancelled' } : j)));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to cancel job');
    } finally {
      setCancellingId(null);
    }
  }

  if (loading) {
    return (
      <div style={{ padding: 60, textAlign: 'center', color: '#6b7280' }}>
        <Loader2 size={24} style={{ animation: 'spin 1s linear infinite' }} />
        <p>Loading optimizations...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 60, textAlign: 'center' }}>
        <p style={{ color: '#dc2626', marginBottom: 12 }}>{error}</p>
        <button type="button" onClick={() => void load()} style={{ padding: '8px 20px', borderRadius: 8, border: '1px solid #e5e7eb', background: '#fff', cursor: 'pointer' }}>
          Retry
        </button>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h1>Optimizations</h1>
        <Link to="/optimizations/new" className="primary-button" style={{ textDecoration: 'none' }}>
          New optimization
        </Link>
      </div>
      {jobs.length === 0 ? (
        <div className="panel" style={{ padding: 32, textAlign: 'center', color: '#6b7280' }}>
          <p>No optimizations yet.</p>
          <Link to="/optimizations/new">Run your first optimization</Link>
        </div>
      ) : (
        <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 12, padding: 0 }}>
          {jobs.map((job) => {
            const pct = progressPct(job);
            const tone = statusTone(job.status);
            const isActive = !TERMINAL.has(job.status.toLowerCase());
            const isDone = job.status.toLowerCase() === 'completed';
            return (
              <li key={job.id} className="panel" style={{ padding: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                  <strong>{job.name}</strong>
                  <span
                    style={{
                      fontSize: 12,
                      fontWeight: 600,
                      color: tone,
                      border: `1px solid ${tone}`,
                      borderRadius: 999,
                      padding: '2px 10px',
                      textTransform: 'capitalize',
                    }}
                  >
                    {job.status}
                  </span>
                </div>
                <div style={{ marginTop: 10, height: 6, borderRadius: 999, background: '#e5e7eb', overflow: 'hidden' }} role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label={`Progress for ${job.name}`}>
                  <div style={{ width: `${isDone ? 100 : pct}%`, height: '100%', background: tone, transition: 'width 0.4s ease' }} />
                </div>
                <div style={{ marginTop: 8, fontSize: 12, color: '#6b7280', display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
                  <span>{isDone ? '100% — complete' : `${pct}%`}{job.error_message ? ` — ${job.error_message}` : ''}</span>
                  <span style={{ display: 'flex', gap: 12 }}>
                    {isDone && (
                      <button
                        type="button"
                        onClick={() => void api.optimizations.report(job.id).then((r) => console.info('report', r)).catch((e: Error) => setError(e.message))}
                        style={{ background: 'none', border: 'none', color: '#2563eb', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}
                      >
                        View report
                      </button>
                    )}
                    {isActive && (
                      <button
                        type="button"
                        disabled={cancellingId === job.id}
                        onClick={() => void cancelJob(job.id)}
                        style={{ background: 'none', border: 'none', color: '#dc2626', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}
                      >
                        {cancellingId === job.id ? 'Cancelling…' : 'Cancel'}
                      </button>
                    )}
                  </span>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
