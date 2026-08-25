import { useState } from 'react';

interface PilotContract {
  id: string;
  portfolio_size_usd: string;
  duration_months: number;
  fee_percentage: string;
  min_savings_threshold: string;
  status: 'active' | 'completed' | 'expired' | 'cancelled';
  created_at: string;
  expires_at: string;
  optimization_jobs: number;
  total_savings_usd?: number;
  total_fees_earned_usd?: number;
}

export default function PilotDashboard() {
  const [contracts] = useState<PilotContract[]>([]);
  return (
    <div className="glass p-6">
      <h2 className="text-lg font-semibold">My Pilot Contracts</h2>
      <p className="text-sm text-slate-500">{contracts.length} active contract(s) — stub</p>
    </div>
  );
}
