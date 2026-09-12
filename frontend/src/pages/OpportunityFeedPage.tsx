import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Loader2, TrendingUp, Zap } from 'lucide-react';
import { api } from '../api';
import type { Opportunity } from '../types';

type RiskFilter = 'All' | 'Low' | 'Medium' | 'High';
type SortKey = 'relevance' | 'upside';

export default function OpportunityFeedPage() {
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [risk, setRisk] = useState<RiskFilter>('All');
  const [sort, setSort] = useState<SortKey>('relevance');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.intelligence.opportunities();
      setOpportunities(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load opportunities');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const visible = useMemo(() => {
    let list = opportunities.filter((o) => {
      if (risk !== 'All' && o.risk_level !== risk) return false;
      return true;
    });
    list = [...list].sort((a, b) =>
      sort === 'relevance' ? b.relevance_score - a.relevance_score : b.upside - a.upside,
    );
    return list;
  }, [opportunities, risk, sort]);

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
        <div style={{ textAlign: 'center', color: '#6b7280' }}>
          <Loader2 size={32} style={{ animation: 'spin 1s linear infinite', marginBottom: 12 }} />
          <p>Loading opportunities...</p>
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
        <h1 style={{ fontSize: 24, fontWeight: 700, margin: 0 }}>Opportunity Feed</h1>
        <p style={{ fontSize: 13, color: '#6b7280', margin: '4px 0 0' }}>
          Investment opportunities derived from your portfolio analysis.
        </p>
      </div>

      {/* Summary */}
      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 12, marginBottom: 24 }}>
        {[
          { value: `${opportunities.length}`, label: 'Total Opportunities', icon: <Zap size={16} /> },
          { value: `${opportunities.filter((o) => o.risk_level === 'Low').length}`, label: 'Low Risk', icon: null },
          { value: `${opportunities.filter((o) => o.risk_level === 'Medium').length}`, label: 'Medium Risk', icon: null },
          { value: `${opportunities.filter((o) => o.risk_level === 'High').length}`, label: 'High Risk', icon: null },
        ].map(({ value, label, icon }) => (
          <article key={label} className="stat-card" style={{ borderTop: '3px solid #2563eb' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4, color: '#6b7280' }}>
              {icon}
              <span className="stat-label" style={{ margin: 0 }}>{label}</span>
            </div>
            <div className="stat-value" style={{ fontSize: 20 }}>{value}</div>
          </article>
        ))}
      </section>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16, alignItems: 'center', flexWrap: 'wrap' }}>
        <span style={{ fontSize: 12, color: '#6b7280', fontWeight: 600 }}>Risk:</span>
        {(['All', 'Low', 'Medium', 'High'] as RiskFilter[]).map((r) => (
          <button
            key={r}
            type="button"
            onClick={() => setRisk(r)}
            style={{
              padding: '5px 12px', borderRadius: 6, fontSize: 12, fontWeight: 500,
              border: `1px solid ${risk === r ? '#2563eb' : '#e5e7eb'}`,
              background: risk === r ? '#2563eb' : '#fff',
              color: risk === r ? '#fff' : '#374151',
              cursor: 'pointer',
            }}
          >
            {r}
          </button>
        ))}
        <span style={{ width: 1, height: 20, background: '#e5e7eb' }} />
        <span style={{ fontSize: 12, color: '#6b7280', fontWeight: 600 }}>Sort:</span>
        <button
          type="button"
          onClick={() => setSort('relevance')}
          style={{
            padding: '5px 12px', borderRadius: 6, fontSize: 12, fontWeight: 500,
            border: `1px solid ${sort === 'relevance' ? '#2563eb' : '#e5e7eb'}`,
            background: sort === 'relevance' ? '#2563eb' : '#fff',
            color: sort === 'relevance' ? '#fff' : '#374151',
            cursor: 'pointer',
          }}
        >
          Relevance
        </button>
        <button
          type="button"
          onClick={() => setSort('upside')}
          style={{
            padding: '5px 12px', borderRadius: 6, fontSize: 12, fontWeight: 500,
            border: `1px solid ${sort === 'upside' ? '#2563eb' : '#e5e7eb'}`,
            background: sort === 'upside' ? '#2563eb' : '#fff',
            color: sort === 'upside' ? '#fff' : '#374151',
            cursor: 'pointer',
          }}
        >
          Upside
        </button>
      </div>

      {/* Opportunities */}
      {visible.length === 0 ? (
        <div className="panel" style={{ padding: 48, textAlign: 'center', color: '#9ca3af' }}>
          No opportunities match your filters. Add more instruments to your portfolio to see opportunities.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {visible.map((o) => (
            <article key={o.id} className="panel" style={{ padding: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontSize: 15, fontWeight: 700 }}>{o.ticker}</span>
                    <span style={{
                      padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 600,
                      background: o.risk_level === 'Low' ? 'rgba(22,163,74,0.1)' : o.risk_level === 'Medium' ? 'rgba(217,119,6,0.1)' : 'rgba(220,38,38,0.1)',
                      color: o.risk_level === 'Low' ? '#16a34a' : o.risk_level === 'Medium' ? '#d97706' : '#dc2626',
                    }}>
                      {o.risk_level}
                    </span>
                    <span style={{ padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 500, background: '#f3f4f6', color: '#6b7280' }}>
                      {o.type}
                    </span>
                  </div>
                  <p style={{ fontSize: 13, color: '#6b7280', margin: 0 }}>{o.name} · {o.sector}</p>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4, justifyContent: 'flex-end' }}>
                    <TrendingUp size={14} style={{ color: '#16a34a' }} />
                    <span style={{ fontSize: 18, fontWeight: 700, color: '#16a34a' }}>+{o.upside}%</span>
                  </div>
                  <p style={{ fontSize: 11, color: '#6b7280', margin: 0 }}>upside</p>
                </div>
              </div>
              <div style={{ display: 'flex', gap: 20, marginTop: 10, fontSize: 13 }}>
                <div>
                  <span style={{ color: '#6b7280' }}>Current: </span>
                  <span style={{ fontWeight: 600 }}>${o.current_price.toFixed(2)}</span>
                </div>
                <div>
                  <span style={{ color: '#6b7280' }}>Target: </span>
                  <span style={{ fontWeight: 600 }}>${o.target_price.toFixed(2)}</span>
                </div>
                <div>
                  <span style={{ color: '#6b7280' }}>Relevance: </span>
                  <span style={{ fontWeight: 600 }}>{o.relevance_score}/100</span>
                </div>
              </div>
              {/* Relevance bar */}
              <div style={{ marginTop: 8, height: 4, background: '#f3f4f6', borderRadius: 2, overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${o.relevance_score}%`, background: '#2563eb', borderRadius: 2 }} />
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
