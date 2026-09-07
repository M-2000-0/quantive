import { useState } from 'react';

type View = 'Executions' | 'Trades' | 'Outcomes' | 'Activity';

const DEMO_EXECUTIONS = [
  { id: 'ex-1', name: 'Q1 Refinancing Pass', status: 'COMPLETED', savings: 1_200_000 },
  { id: 'ex-2', name: 'Duration Rebalance', status: 'RUNNING', savings: 0 },
];

const DEMO_TRADES = [
  { id: 't-1', instrument: 'US Treasury 10Y', side: 'BUY', amount: 50_000_000 },
];

export default function ExecutionDashboardPage() {
  const [view, setView] = useState<View>('Executions');

  return (
    <div>
      <h1>Execution Dashboard</h1>
      <div style={{ display: 'flex', gap: 12, margin: '12px 0' }}>
        <div className="panel">Total Executions: {DEMO_EXECUTIONS.length}</div>
        <div className="panel">Completed: {DEMO_EXECUTIONS.filter((e) => e.status === 'COMPLETED').length}</div>
        <div className="panel">Realized Savings: $1.2M</div>
        <div className="panel">Avg Accuracy: 87%</div>
      </div>
      <div role="tablist" style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        {(['Executions', 'Trades', 'Outcomes', 'Activity'] as View[]).map((v) => (
          <button key={v} role="tab" aria-selected={view === v} type="button" onClick={() => setView(v)}>
            {v}
          </button>
        ))}
      </div>
      {view === 'Executions' && (
        <ul>
          {DEMO_EXECUTIONS.map((e) => (
            <li key={e.id}>
              {e.name} — {e.status}
            </li>
          ))}
        </ul>
      )}
      {view === 'Trades' && (
        <table className="q-table">
          <thead>
            <tr>
              <th>Instrument</th>
              <th>Side</th>
              <th>Amount</th>
            </tr>
          </thead>
          <tbody>
            {DEMO_TRADES.map((t) => (
              <tr key={t.id}>
                <td>{t.instrument}</td>
                <td>{t.side}</td>
                <td>{t.amount}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {view === 'Outcomes' && (
        <div className="panel">
          <h2>Total Savings</h2>
          <p>$1.2M realized across completed executions.</p>
        </div>
      )}
      {view === 'Activity' && (
        <div className="panel">
          <p>No recent activity events.</p>
        </div>
      )}
    </div>
  );
}
