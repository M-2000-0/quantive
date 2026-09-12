import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Loader2, CheckCircle, XCircle, Clock, AlertTriangle } from 'lucide-react';
import { api } from '../api';

interface OptimizationJob {
  id: string;
  name: string;
  status: string;
  optimization_type?: string;
  created_at?: string;
  completed_at?: string;
  random_seed?: number;
}

const STATUS_COLORS: Record<string, { bg: string; fg: string }> = {
  COMPLETED: { bg: 'rgba(22,163,74,0.1)', fg: '#16a34a' },
  RUNNING: { bg: 'rgba(37,99,235,0.1)', fg: '#2563eb' },
  QUEUED: { bg: 'rgba(217,119,6,0.1)', fg: '#d97706' },
  FAILED: { bg: 'rgba(220,38,38,0.1)', fg: '#dc2626' },
  CANCELLED: { bg: 'rgba(107,114,128,0.1)', fg: '#6b7280' },
};

function StatusIcon({ status }: { status: string }) {
  const s = STATUS_COLORS[status] ?? STATUS_COLORS.QUEUED;
  switch (status) {
    case 'COMPLETED': return <CheckCircle size={16} style={{ color: s.fg }} />;
    case 'RUNNING': return <Clock size={16} style={{ color: s.fg }} />;
    case 'FAILED': return <XCircle size={16} style={{ color: s.fg }} />;
    case 'CANCELLED': return <AlertTriangle size={16} style={{ color: s.fg }} />;
    default: return <Clock size={16} style={{ color: s.fg }} />;
  }
}

export default function ExecutionDashboardPage() {
  const [jobs, setJobs] = useState<OptimizationJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.optimizations.list() as unknown as
        | OptimizationJob[]
        | { data: OptimizationJob[] };
      setJobs(Array.isArray(res) ? res : (res.data ?? []));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load executions');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const stats = useMemo(() => {
    const total = jobs.length;
    const completed = jobs.filter((j) => j.status === 'COMPLETED').length;
    const running = jobs.filter((j) => j.status === 'RUNNING').length;
    const failed = jobs.filter((j) => j.status === 'FAILED').length;
    const queued = jobs.filter((j) => j.status === 'QUEUED').length;
    return { total, completed, running, failed, queued };
  }, [jobs]);

  const recent = useMemo(() => {
    return [...jobs]
      .sort((a, b) => {
        const da = a.created_at ?? '';
        const db2 = b.created_at ?? '';
        return db2.localeCompare(da);
      })
      .slice(0, 20);
  }, [jobs]);

  const selectedJob = useMemo(() => {
    if (!selectedId) return null;
    return jobs.find((j) => j.id === selectedId) ?? null;
  }, [jobs, selectedId]);

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
        <div style={{ textAlign: 'center', color: '#6b7280' }}>
          <Loader2 size={32} style={{ animation: 'spin 1s linear infinite', marginBottom: 12 }} />
          <p>Loading executions...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
        <div style={{ textAlign: 'center', maxWidth: 400 }}>
          <p style={{ fontSize: 18, fontWeight: 600, marginBottom: 8, color: '#dc2626' }}>Failed to load</p>
          <p style={{ color: '#6b7280', marginBottom: 16 }}>{error}</p>
          <button type="button" onClick={() => void load()} style={{ padding: '8px 20px', borderRadius: 8, border: '1px solid #e5e7eb', background: '#fff', cursor: 'pointer', fontWeight: 500 }}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, margin: 0 }}>Execution Dashboard</h1>
        <p style={{ fontSize: 13, color: '#6b7280', margin: '4px 0 0' }}>
          Monitor optimization jobs, strategies, and outcomes.
        </p>
      </div>

      {/* Summary Cards */}
      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12, marginBottom: 24 }}>
        {[
          { value: `${stats.total}`, label: 'Total Jobs', tone: '#2563eb' },
          { value: `${stats.completed}`, label: 'Completed', tone: '#16a34a' },
          { value: `${stats.running}`, label: 'Running', tone: '#2563eb' },
          { value: `${stats.failed}`, label: 'Failed', tone: '#dc2626' },
          { value: `${stats.queued}`, label: 'Queued', tone: '#d97706' },
        ].map(({ value, label, tone }) => (
          <article key={label} className="stat-card" style={{ borderTop: `3px solid ${tone}` }}>
            <div className="stat-value" style={{ fontSize: 20 }}>{value}</div>
            <div className="stat-label">{label}</div>
          </article>
        ))}
      </section>

      <div style={{ display: 'grid', gridTemplateColumns: selectedJob ? '1fr 360px' : '1fr', gap: 20 }}>
        {/* Jobs List */}
        <div>
          {recent.length === 0 ? (
            <div className="panel" style={{ padding: 48, textAlign: 'center', color: '#9ca3af' }}>
              No optimization jobs yet.{' '}
              <Link to="/optimization/new" style={{ color: '#2563eb' }}>Create one</Link>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {recent.map((job) => {
                const sc = STATUS_COLORS[job.status] ?? STATUS_COLORS.QUEUED;
                return (
                  <article
                    key={job.id}
                    className="panel"
                    style={{
                      padding: '12px 16px',
                      cursor: 'pointer',
                      borderColor: selectedId === job.id ? '#2563eb' : undefined,
                    }}
                    onClick={() => setSelectedId(job.id === selectedId ? null : job.id)}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <StatusIcon status={job.status} />
                        <div>
                          <p style={{ fontSize: 14, fontWeight: 600, margin: 0 }}>{job.name}</p>
                          <p style={{ fontSize: 11, color: '#6b7280', margin: '2px 0 0' }}>
                            {job.optimization_type ?? 'optimization'} · {job.id.slice(0, 8)}
                          </p>
                        </div>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <span style={{
                          padding: '2px 10px', borderRadius: 6, fontSize: 11, fontWeight: 600,
                          background: sc.bg, color: sc.fg,
                        }}>
                          {job.status}
                        </span>
                        <span style={{ fontSize: 11, color: '#9ca3af' }}>
                          {job.created_at ? new Date(job.created_at).toLocaleDateString() : '—'}
                        </span>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </div>

        {/* Detail Panel */}
        {selectedJob && (
          <div className="panel" style={{ padding: 20, position: 'sticky', top: 80, alignSelf: 'start' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
              <div>
                <h2 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>{selectedJob.name}</h2>
                <p style={{ fontSize: 12, color: '#6b7280', margin: '4px 0 0' }}>{selectedJob.id}</p>
              </div>
              <span style={{
                padding: '3px 10px', borderRadius: 6, fontSize: 11, fontWeight: 600,
                background: (STATUS_COLORS[selectedJob.status] ?? STATUS_COLORS.QUEUED).bg,
                color: (STATUS_COLORS[selectedJob.status] ?? STATUS_COLORS.QUEUED).fg,
              }}>
                {selectedJob.status}
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              {[
                { label: 'Type', value: selectedJob.optimization_type ?? '—' },
                { label: 'Seed', value: selectedJob.random_seed?.toString() ?? '—' },
                { label: 'Created', value: selectedJob.created_at ? new Date(selectedJob.created_at).toLocaleString() : '—' },
                { label: 'Completed', value: selectedJob.completed_at ? new Date(selectedJob.completed_at).toLocaleString() : '—' },
              ].map(({ label, value }) => (
                <div key={label}>
                  <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 2 }}>{label}</div>
                  <div style={{ fontSize: 13, fontWeight: 500 }}>{value}</div>
                </div>
              ))}
            </div>

            <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
              <Link
                to={`/optimizations/${selectedJob.id}`}
                style={{
                  padding: '6px 14px', borderRadius: 6, fontSize: 12, fontWeight: 500,
                  background: '#2563eb', color: '#fff', textDecoration: 'none',
                }}
              >
                View Details
              </Link>
              <Link
                to={`/optimizations/${selectedJob.id}/report`}
                style={{
                  padding: '6px 14px', borderRadius: 6, fontSize: 12, fontWeight: 500,
                  border: '1px solid #e5e7eb', color: '#374151', textDecoration: 'none',
                }}
              >
                View Report
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
