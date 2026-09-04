import { useState } from 'react';
import { MOCK_EVENTS, getEventImpactSummary, getCategoryBreakdown, getRegionBreakdown, getMostImpactedAssets } from '../lib/eventImpactData';

export default function EventImpactDashboard() {
  const [category, setCategory] = useState('All');
  const [severity, setSeverity] = useState('All');
  const [view, setView] = useState<'list' | 'matrix'>('list');
  const summary = getEventImpactSummary(MOCK_EVENTS);
  const byCategory = getCategoryBreakdown(MOCK_EVENTS);
  const byRegion = getRegionBreakdown(MOCK_EVENTS);
  const assets = getMostImpactedAssets(MOCK_EVENTS);

  const filtered = MOCK_EVENTS.filter(
    (e) =>
      (category === 'All' || e.category === category.toLowerCase()) &&
      (severity === 'All' || e.severity === severity.toLowerCase()),
  );

  return (
    <div>
      <h1>Event Impact Dashboard</h1>
      <div>
        <span>Total Events</span>
        <span>{summary.totalEvents}</span>
        <span>Positive</span>
        <span>{summary.totalPositive}</span>
        <span>Negative</span>
        <span>{summary.totalNegative}</span>
      </div>
      <div>
        {['All', 'Political', 'Economic', 'Geopolitical', 'Commercial', 'Regulatory'].map((c) => (
          <button key={c} type="button" onClick={() => setCategory(c)}>
            {c}
          </button>
        ))}
      </div>
      <div>
        {['All', 'Critical', 'High', 'Medium', 'Low'].map((s) => (
          <button key={s} type="button" onClick={() => setSeverity(s)}>
            {s}
          </button>
        ))}
      </div>
      <button type="button" onClick={() => setView(view === 'list' ? 'matrix' : 'list')}>
        {view === 'list' ? 'List View' : 'Matrix View'}
      </button>
      <ul>
        {filtered.map((e) => (
          <li key={e.id}>{e.title}</li>
        ))}
      </ul>
      <aside>
        <h2>Most Impacted Assets</h2>
        <ul>
          {assets.map((a) => (
            <li key={a.name}>{a.name}</li>
          ))}
        </ul>
        <h2>Events by Category</h2>
        <ul>
          {Object.entries(byCategory).map(([k, v]) => (
            <li key={k}>
              {k}: {v}
            </li>
          ))}
        </ul>
        <h2>Regional Exposure</h2>
        <ul>
          {Object.entries(byRegion).map(([k, v]) => (
            <li key={k}>
              {k}: {v}
            </li>
          ))}
        </ul>
      </aside>
    </div>
  );
}
