import { useState } from 'react';
import { useAuth } from '../stores/auth';

export default function AdminDashboardPage() {
  const { user } = useAuth();
  const [tab, setTab] = useState('Overview');

  if (!user || user.role !== 'admin') {
    return (
      <div>
        <h1>Access Denied</h1>
        <p>You need an admin role to view this page.</p>
      </div>
    );
  }

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
      {tab === 'System' && (
        <div>
          <p>System Health</p>
          <p>Performance Metrics</p>
        </div>
      )}
      {tab === 'Billing' && (
        <div>
          <p>Billing overview</p>
          <button type="button">Upgrade to Enterprise</button>
        </div>
      )}
    </div>
  );
}
