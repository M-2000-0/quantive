import { useMemo, useState } from 'react';
import { MOCK_OPPORTUNITIES } from '../lib/purchaseData';

type RiskFilter = 'All' | 'Low' | 'Medium' | 'High';
type SortKey = 'relevance' | 'upside';

export default function OpportunityFeedPage() {
  const [risk, setRisk] = useState<RiskFilter>('All');
  const [sort, setSort] = useState<SortKey>('relevance');
  const [linkedOnly, setLinkedOnly] = useState(false);

  const visible = useMemo(() => {
    let list = MOCK_OPPORTUNITIES.filter((o) => {
      if (risk !== 'All' && o.riskLevel !== risk) return false;
      if (linkedOnly && !o.relatedPurchaseId) return false;
      return true;
    });
    list = [...list].sort((a, b) =>
      sort === 'relevance' ? b.relevanceScore - a.relevanceScore : b.upside - a.upside,
    );
    return list;
  }, [risk, sort, linkedOnly]);

  return (
    <div>
      <h1>Opportunity Feed</h1>
      <span className="rounded-lg text-[10px] font-bold">Live</span>
      <div style={{ display: 'flex', gap: 8, margin: '12px 0', flexWrap: 'wrap', alignItems: 'center' }}>
        <span>All Risk</span>
        {(['All', 'Low', 'Medium', 'High'] as RiskFilter[]).map((r) => (
          <button
            key={r}
            type="button"
            onClick={() => setRisk(r)}
            className="soft-button"
            aria-pressed={risk === r}
          >
            {r === 'All' ? 'All' : r}
          </button>
        ))}
        <button type="button" onClick={() => setSort('relevance')} className="soft-button">
          Relevance
        </button>
        <button type="button" onClick={() => setSort('upside')} className="soft-button">
          Upside
        </button>
        <label style={{ display: 'inline-flex', gap: 6, alignItems: 'center', fontSize: 13 }}>
          <input
            type="checkbox"
            checked={linkedOnly}
            onChange={(e) => setLinkedOnly(e.target.checked)}
          />
          Linked to holdings only
        </label>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {visible.map((o) => (
          <article key={o.id} className="panel">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
              <strong>{o.ticker}</strong>
              <span>{o.name}</span>
              <span>Upside</span>
            </div>
            <div style={{ display: 'flex', gap: 16, marginTop: 6, fontSize: 13 }}>
              <span>${o.currentPrice.toFixed(2)}</span>
              <span>${o.targetPrice.toFixed(2)}</span>
              <strong>+{o.upside}%</strong>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
