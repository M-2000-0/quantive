import { useCallback, useEffect, useMemo, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { api } from '../api';
import type { ImpactEvent, EventImpactSummary, ImpactedAsset } from '../types';

function severityColor(severity: string): string {
  switch (severity) {
    case 'critical': return '#dc2626';
    case 'high': return '#ea580c';
    case 'medium': return '#3b82f6';
    default: return '#16a34a';
  }
}

function categoryIcon(category: string): string {
  switch (category) {
    case 'political': return '🏛';
    case 'economic': return '📈';
    case 'geopolitical': return '🌍';
    case 'commercial': return '🏢';
    case 'regulatory': return '📋';
    default: return '🌱';
  }
}

export default function EventImpactDashboard() {
  const [events, setEvents] = useState<ImpactEvent[]>([]);
  const [summary, setSummary] = useState<EventImpactSummary | null>(null);
  const [assets, setAssets] = useState<ImpactedAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [category, setCategory] = useState('All');
  const [severity, setSeverity] = useState('All');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [eventsData, summaryData, assetsData] = await Promise.all([
        api.intelligence.events(),
        api.intelligence.eventSummary(),
        api.intelligence.impactedAssets(),
      ]);
      setEvents(eventsData);
      setSummary(summaryData);
      setAssets(assetsData);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load event data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    return events.filter(
      (e) =>
        (category === 'All' || e.category === category.toLowerCase()) &&
        (severity === 'All' || e.severity === severity.toLowerCase()),
    );
  }, [events, category, severity]);

  const byCategory = useMemo(() => {
    const map: Record<string, number> = {};
    events.forEach((e) => { map[e.category] = (map[e.category] ?? 0) + 1; });
    return map;
  }, [events]);

  const byRegion = useMemo(() => {
    const map: Record<string, number> = {};
    events.forEach((e) => { map[e.region] = (map[e.region] ?? 0) + 1; });
    return map;
  }, [events]);

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
        <div style={{ textAlign: 'center', color: '#6b7280' }}>
          <Loader2 size={32} style={{ animation: 'spin 1s linear infinite', marginBottom: 12 }} />
          <p>Analyzing event impact...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
        <div style={{ textAlign: 'center', maxWidth: 400 }}>
          <p style={{ fontSize: 18, fontWeight: 600, marginBottom: 8, color: '#dc2626' }}>Failed to load events</p>
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
        <h1 style={{ fontSize: 24, fontWeight: 700, margin: 0 }}>Event Impact Dashboard</h1>
        <p style={{ fontSize: 13, color: '#6b7280', margin: '4px 0 0' }}>
          Real-time analysis of market events affecting your portfolio.
        </p>
      </div>

      {/* Summary Cards */}
      {summary && (
        <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 12, marginBottom: 24 }}>
          {[
            { value: `${summary.total_events}`, label: 'Total Events', tone: '#2563eb' },
            { value: `${summary.total_positive}`, label: 'Positive Impact', tone: '#16a34a' },
            { value: `${summary.total_negative}`, label: 'Negative Impact', tone: '#dc2626' },
            { value: `${summary.avg_severity}`, label: 'Avg Severity', tone: '#3b82f6' },
            { value: `${summary.critical_count}`, label: 'Critical', tone: '#dc2626' },
          ].map(({ value, label, tone }) => (
            <article key={label} className="stat-card" style={{ borderTop: `3px solid ${tone}` }}>
              <div className="stat-value" style={{ fontSize: 20 }}>{value}</div>
              <div className="stat-label">{label}</div>
            </article>
          ))}
        </section>
      )}

      {/* Filters */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
        {['All', 'Economic', 'Political', 'Geopolitical', 'Commercial', 'Regulatory', 'Environmental'].map((c) => (
          <button
            key={c}
            type="button"
            onClick={() => setCategory(c)}
            style={{
              padding: '6px 12px', borderRadius: 6, fontSize: 12, fontWeight: 500,
              border: `1px solid ${category === c ? '#2563eb' : '#e5e7eb'}`,
              background: category === c ? '#2563eb' : '#fff',
              color: category === c ? '#fff' : '#374151',
              cursor: 'pointer',
            }}
          >
            {c}
          </button>
        ))}
        <span style={{ width: 1, background: '#e5e7eb' }} />
        {['All', 'Critical', 'High', 'Medium', 'Low'].map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setSeverity(s)}
            style={{
              padding: '6px 12px', borderRadius: 6, fontSize: 12, fontWeight: 500,
              border: `1px solid ${severity === s ? '#2563eb' : '#e5e7eb'}`,
              background: severity === s ? '#2563eb' : '#fff',
              color: severity === s ? '#fff' : '#374151',
              cursor: 'pointer',
            }}
          >
            {s}
          </button>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 20 }}>
        {/* Events List */}
        <div>
          {filtered.length === 0 ? (
            <div className="panel" style={{ padding: 48, textAlign: 'center', color: '#9ca3af' }}>
              No events match your filters
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {filtered.map((event) => (
                <article key={event.id} className="panel" style={{ padding: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                      <span style={{ fontSize: 20 }}>{categoryIcon(event.category)}</span>
                      <div>
                        <h3 style={{ fontSize: 14, fontWeight: 600, margin: 0 }}>{event.title}</h3>
                        <p style={{ fontSize: 12, color: '#6b7280', margin: '2px 0 0' }}>{event.description}</p>
                      </div>
                    </div>
                    <span style={{
                      padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 600,
                      background: `${severityColor(event.severity)}15`,
                      color: severityColor(event.severity),
                      textTransform: 'uppercase',
                      whiteSpace: 'nowrap',
                    }}>
                      {event.severity}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: 12, fontSize: 12, color: '#6b7280' }}>
                    <span>{event.region}</span>
                    <span>{event.affected_assets.length} asset{event.affected_assets.length !== 1 ? 's' : ''} affected</span>
                    {event.affected_assets.map((a) => (
                      <span key={a.name} style={{ color: a.impact > 0 ? '#16a34a' : '#dc2626' }}>
                        {a.name}: {a.impact > 0 ? '+' : ''}{(a.impact * 100).toFixed(0)}%
                      </span>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Most Impacted Assets */}
          <article className="panel" style={{ padding: 16 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Most Impacted Assets</h3>
            {assets.length === 0 ? (
              <p style={{ fontSize: 13, color: '#9ca3af' }}>No assets impacted</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {assets.slice(0, 5).map((a) => (
                  <div key={a.name} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <p style={{ fontSize: 13, fontWeight: 500 }}>{a.name}</p>
                      <p style={{ fontSize: 11, color: '#6b7280' }}>{a.type}</p>
                    </div>
                    <span style={{
                      fontSize: 13, fontWeight: 600,
                      color: a.avg_impact > 0 ? '#16a34a' : '#dc2626',
                    }}>
                      {a.avg_impact > 0 ? '+' : ''}{(a.avg_impact * 100).toFixed(1)}%
                    </span>
                  </div>
                ))}
              </div>
            )}
          </article>

          {/* By Category */}
          <article className="panel" style={{ padding: 16 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>By Category</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {Object.entries(byCategory).sort(([, a], [, b]) => b - a).map(([cat, count]) => (
                <div key={cat} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                  <span style={{ textTransform: 'capitalize' }}>{cat}</span>
                  <span style={{ fontWeight: 600 }}>{count}</span>
                </div>
              ))}
            </div>
          </article>

          {/* By Region */}
          <article className="panel" style={{ padding: 16 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>By Region</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {Object.entries(byRegion).sort(([, a], [, b]) => b - a).map(([region, count]) => (
                <div key={region} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                  <span>{region}</span>
                  <span style={{ fontWeight: 600 }}>{count}</span>
                </div>
              ))}
            </div>
          </article>
        </div>
      </div>
    </div>
  );
}
