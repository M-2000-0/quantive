import { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertCircle, BarChart2, Info } from 'lucide-react';
import { personalApi } from '../api';
import type { PersonalScore, PersonalTask } from '../api';

function formatCurrency(value: number): string {
  if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `$${(value / 1e3).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

export default function DashboardPage() {
  const [score, setScore] = useState<PersonalScore | null>(null);
  const [tasks, setTasks] = useState<PersonalTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [scoreData, tasksData] = await Promise.all([
        personalApi.score(),
        personalApi.tasks(),
      ]);
      setScore(scoreData);
      setTasks(tasksData || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const openTasks = useMemo(() => tasks.filter((t) => t.status !== 'closed'), [tasks]);

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
        <div style={{ textAlign: 'center', color: '#6b7280' }}>
          <BarChart2 size={32} className="animate-spin" /> Loading dashboard…
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
        <div style={{ textAlign: 'center', maxWidth: 400 }}>
          <p style={{ fontSize: 18, fontWeight: 600, marginBottom: 8, color: '#dc2626' }}>Failed to load dashboard</p>
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

  const statCards = [
    { label: 'Tax Score', value: score ? `${score.score}/100` : '—' },
    { label: 'Open Actions', value: String(score?.open_actions ?? openTasks.length) },
    { label: 'Opportunities', value: String(score?.opportunities ?? 0) },
    { label: 'Document Gaps', value: String(score?.doc_gaps ?? 0) },
  ];

  return (
    <div style={{ padding: 16, maxWidth: 1100, margin: '0 auto' }}>
      {score?.message && (
        <div
          style={{
            marginBottom: 16,
            padding: '12px 16px',
            borderRadius: 8,
            background: '#ecfdf5',
            border: '1px solid #a7f3d0',
            color: '#047857',
            fontSize: 13,
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <Info size={16} style={{ marginRight: 8 }} /> {score.message}
        </div>
      )}

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: 12,
          marginBottom: 16,
        }}
      >
        {statCards.map((s) => (
          <div key={s.label} style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 16, background: '#fff' }}>
            <div style={{ fontSize: 12, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {s.label}
            </div>
            <div style={{ fontSize: 24, fontWeight: 700, marginTop: 4 }}>{s.value}</div>
          </div>
        ))}
      </div>

      <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 16, background: '#fff' }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Open Tasks ({openTasks.length})</h2>
        {openTasks.length === 0 ? (
          <p style={{ color: '#6b7280', fontSize: 14 }}>
            No open tasks right now. Check back after your next transaction sync.
          </p>
        ) : (
          <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {openTasks.slice(0, 8).map((t) => (
              <li
                key={t.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '10px 0',
                  borderBottom: '1px solid #f3f4f6',
                  gap: 12,
                }}
              >
                <div>
                  <div style={{ fontWeight: 500, fontSize: 14 }}>{t.title}</div>
                  <div style={{ fontSize: 12, color: '#6b7280' }}>{t.reason}</div>
                </div>
                <span
                  style={{
                    fontSize: 11,
                    padding: '2px 8px',
                    borderRadius: 9999,
                    background: t.priority === 'high' ? '#fee2e2' : t.priority === 'medium' ? '#eff6ff' : '#e5e7eb',
                    color: t.priority === 'high' ? '#b91c1c' : t.priority === 'medium' ? '#1e40af' : '#374151',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {t.priority}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
