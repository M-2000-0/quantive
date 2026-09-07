import RiskDashboard from '../components/RiskDashboard';

export default function RiskDashboardPage() {
  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, margin: 0 }}>Risk Dashboard</h1>
        <p style={{ fontSize: 13, color: '#6b7280', margin: '4px 0 0' }}>
          Monitor risk exposure across all categories with real-time early warning signals.
        </p>
      </div>
      <RiskDashboard />
    </div>
  );
}
