import { useState, useEffect } from 'react';
import { api } from '../api';

interface RevenueData {
  total_revenue: number;
  pipeline_value: number;
  annual_recurring: number;
  win_rate: number;
  total_deals: number;
  won_deals: number;
  lost_deals: number;
  by_stage: Record<string, { count: number; value: number }>;
}

interface MRRData {
  mrr: number;
  arr: number;
  subscription_count: number;
  avg_revenue_per_deal: number;
}

interface ChurnData {
  churn_rate: number;
  total_deals: number;
  lost_deals: number;
  lost_value: number;
  at_risk_count: number;
  at_risk_deals: { id: string; name: string; company: string; value: number; probability: number }[];
}

interface CustomerData {
  total_users: number;
  active_users: number;
  inactive_users: number;
  unique_companies: number;
  companies: string[];
}

const STAGE_LABELS: Record<string, string> = {
  lead: 'Lead',
  qualified: 'Qualified',
  proposal: 'Proposal',
  negotiation: 'Negotiation',
  closed_won: 'Closed Won',
  closed_lost: 'Closed Lost' };

const STAGE_COLORS: Record<string, string> = {
  lead: '#6b7280',
  qualified: '#3b82f6',
  proposal: '#8b5cf6',
  negotiation: '#f59e0b',
  closed_won: '#22c55e',
  closed_lost: '#ef4444' };

function fmt(n: number) {
  if (n >= 1e6) return `$${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `$${(n / 1e3).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
}

export function RevenueDashboard() {
  const [revenue, setRevenue] = useState<RevenueData | null>(null);
  const [mrr, setMRR] = useState<MRRData | null>(null);
  const [churn, setChurn] = useState<ChurnData | null>(null);
  const [customers, setCustomers] = useState<CustomerData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [r, m, c, cu] = await Promise.all([
          api.request<RevenueData>('/management/revenue'),
          api.request<MRRData>('/management/mrr'),
          api.request<ChurnData>('/management/churn'),
          api.request<CustomerData>('/management/customers'),
        ]);
        setRevenue(r);
        setMRR(m);
        setChurn(c);
        setCustomers(cu);
      } catch (e) {
        console.error('Failed to load management data', e);
      }
      setLoading(false);
    };
    load();
  }, []);

  if (loading) return <div className="text-gray-400 py-8 text-center">Loading dashboards...</div>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Management Dashboard</h1>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {revenue && (
          <>
            <div className="p-4 bg-white/[0.03] rounded-xl border border-white/5">
              <p className="text-xs text-gray-500">Total Revenue</p>
              <p className="text-2xl font-bold text-white mt-1">{fmt(revenue.total_revenue)}</p>
            </div>
            <div className="p-4 bg-white/[0.03] rounded-xl border border-white/5">
              <p className="text-xs text-gray-500">Pipeline Value</p>
              <p className="text-2xl font-bold text-white mt-1">{fmt(revenue.pipeline_value)}</p>
            </div>
            <div className="p-4 bg-white/[0.03] rounded-xl border border-white/5">
              <p className="text-xs text-gray-500">Win Rate</p>
              <p className="text-2xl font-bold text-white mt-1">{revenue.win_rate}%</p>
            </div>
            <div className="p-4 bg-white/[0.03] rounded-xl border border-white/5">
              <p className="text-xs text-gray-500">Total Deals</p>
              <p className="text-2xl font-bold text-white mt-1">{revenue.total_deals}</p>
            </div>
          </>
        )}
      </div>

      {/* MRR & Churn */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {mrr && (
          <div className="p-4 bg-white/[0.03] rounded-xl border border-white/5">
            <h3 className="text-sm font-medium text-white mb-3">Monthly Recurring Revenue</h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <p className="text-xs text-gray-500">MRR</p>
                <p className="text-lg font-bold text-green-400">{fmt(mrr.mrr)}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">ARR</p>
                <p className="text-lg font-bold text-green-400">{fmt(mrr.arr)}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Subscriptions</p>
                <p className="text-lg font-bold text-white">{mrr.subscription_count}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Avg per Deal</p>
                <p className="text-lg font-bold text-white">{fmt(mrr.avg_revenue_per_deal)}</p>
              </div>
            </div>
          </div>
        )}

        {churn && (
          <div className="p-4 bg-white/[0.03] rounded-xl border border-white/5">
            <h3 className="text-sm font-medium text-white mb-3">Churn Analysis</h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <p className="text-xs text-gray-500">Churn Rate</p>
                <p className="text-lg font-bold text-red-400">{churn.churn_rate}%</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Lost Value</p>
                <p className="text-lg font-bold text-red-400">{fmt(churn.lost_value)}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">At Risk</p>
                <p className="text-lg font-bold text-yellow-400">{churn.at_risk_count}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Lost Deals</p>
                <p className="text-lg font-bold text-white">{churn.lost_deals}</p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Pipeline by Stage */}
      {revenue && Object.keys(revenue.by_stage).length > 0 && (
        <div className="p-4 bg-white/[0.03] rounded-xl border border-white/5">
          <h3 className="text-sm font-medium text-white mb-3">Pipeline by Stage</h3>
          <div className="space-y-2">
            {Object.entries(revenue.by_stage).map(([stage, data]) => (
              <div key={stage} className="flex items-center gap-3">
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: STAGE_COLORS[stage] }} />
                <span className="text-xs text-gray-400 w-24">{STAGE_LABELS[stage] || stage}</span>
                <div className="flex-1 h-2 bg-white/5 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      backgroundColor: STAGE_COLORS[stage],
                      width: `${Math.min((data.count / revenue.total_deals) * 100, 100)}%` }}
                  />
                </div>
                <span className="text-xs text-gray-500 w-16 text-right">{data.count} deals</span>
                <span className="text-xs text-gray-400 w-20 text-right">{fmt(data.value)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Customers */}
      {customers && (
        <div className="p-4 bg-white/[0.03] rounded-xl border border-white/5">
          <h3 className="text-sm font-medium text-white mb-3">Customer Overview</h3>
          <div className="grid grid-cols-4 gap-3">
            <div>
              <p className="text-xs text-gray-500">Total Users</p>
              <p className="text-lg font-bold text-white">{customers.total_users}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Active</p>
              <p className="text-lg font-bold text-green-400">{customers.active_users}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Inactive</p>
              <p className="text-lg font-bold text-gray-400">{customers.inactive_users}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Companies</p>
              <p className="text-lg font-bold text-white">{customers.unique_companies}</p>
            </div>
          </div>
        </div>
      )}

      {/* At-Risk Deals */}
      {churn && churn.at_risk_deals.length > 0 && (
        <div className="p-4 bg-white/[0.03] rounded-xl border border-white/5">
          <h3 className="text-sm font-medium text-white mb-3">At-Risk Deals</h3>
          <div className="space-y-2">
            {churn.at_risk_deals.map(deal => (
              <div key={deal.id} className="flex items-center justify-between p-2 bg-white/[0.02] rounded-lg">
                <div>
                  <p className="text-xs text-white">{deal.name}</p>
                  <p className="text-[10px] text-gray-500">{deal.company}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-gray-400">{fmt(deal.value)}</p>
                  <p className="text-[10px] text-red-400">{deal.probability}% prob</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
