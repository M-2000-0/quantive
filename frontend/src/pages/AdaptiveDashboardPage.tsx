import { useState } from 'react';

type View = 'Cause & Effect' | 'Insights' | 'Market Events' | 'Pipeline';

export default function AdaptiveDashboardPage() {
  const [view, setView] = useState<View>('Cause & Effect');

  return (
    <div>
      <h1>Adaptive Dashboard</h1>
      <p>
        Personalized dashboard view. <span>Live</span>
      </p>
      <div style={{ display: 'flex', gap: 8, margin: '12px 0' }}>
        {(['Cause & Effect', 'Insights', 'Market Events', 'Pipeline'] as View[]).map((v) => (
          <button key={v} type="button" onClick={() => setView(v)}>
            {v}
          </button>
        ))}
      </div>
      {view === 'Cause & Effect' && (
        <div className="panel">
          <h2>Cause & Effect</h2>
          <p>Policy impacts mapped to outcomes.</p>
        </div>
      )}
      {view === 'Insights' && (
        <div className="panel">
          <h2>Insights</h2>
          <p>Select an Insight to see details.</p>
        </div>
      )}
      {view === 'Market Events' && (
        <div className="panel">
          <h2>Market Events</h2>
          <p>Magnitude</p>
        </div>
      )}
      {view === 'Pipeline' && (
        <div className="panel">
          <h2>Pipeline</h2>
          <p>Total Runs: 4</p>
        </div>
      )}
    </div>
  );
}
