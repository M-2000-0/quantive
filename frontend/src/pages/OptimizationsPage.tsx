import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { api } from '../api';

export default function OptimizationsPage() {
  const [jobs, setJobs] = useState<Array<{ id: string; name: string; status: string }>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = (await api.optimizations.list()) as unknown as
        | Array<{ id: string; name: string; status: string }>
        | { data: Array<{ id: string; name: string; status: string }> };
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
          {jobs.map((job) => (
            <li key={job.id} className="panel" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <strong>{job.name}</strong>
              <span>{job.status}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
