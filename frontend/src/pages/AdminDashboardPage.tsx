import { useState } from 'react';

export default function AdminDashboardPage() {
  const [tab, setTab] = useState('Overview');
  return (
    <div>
      <h1>Admin Dashboard</h1>
      <nav>
        {['Overview', 'Users', 'System', 'Billing'].map((t) => (
          <button key={t} type="button" onClick={() => setTab(t)}>
            {t}
          </button>
        ))}
      </nav>
      {tab === 'Overview' && (
        <div>
          <p>Total Users</p>
          <p>Portfolios</p>
          <p>Optimizations</p>
        </div>
      )}
      {tab === 'Users' && (
        <div>
          <p>Total Users</p>
          <p>User Activity</p>
        </div>
      )}
      {tab === 'System' && <p>System health</p>}
      {tab === 'Billing' && <p>Billing overview</p>}
    </div>
  );
}
