import { useState, useMemo } from 'react';

interface ReturnData {
  totalReturns: number;
  totalOrders: number;
  returnRate: number;
  avgProcessingDays: number;
  refundTotal: number;
  byReason: Array<{ reason: string; count: number; pct: number; trend: 'up' | 'down' | 'flat' }>;
  byCategory: Array<{ category: string; rate: number; change: number }>;
  bySegment: Array<{ segment: string; rate: number; orders: number }>;
  monthlyTrend: Array<{ month: string; rate: number; orders: number; returns: number }>;
  topReturned: Array<{ name: string; returns: number; reason: string; revenue: number }>;
}

const MOCK_DATA: ReturnData = {
  totalReturns: 1_247,
  totalOrders: 38_420,
  returnRate: 3.25,
  avgProcessingDays: 2.8,
  refundTotal: 89_400,
  byReason: [
    { reason: 'Size/Fit Issue', count: 412, pct: 33, trend: 'up' },
    { reason: 'Quality Defect', count: 199, pct: 16, trend: 'down' },
    { reason: 'Not as Described', count: 174, pct: 14, trend: 'down' },
    { reason: 'Changed Mind', count: 162, pct: 13, trend: 'flat' },
    { reason: 'Wrong Item Sent', count: 87, pct: 7, trend: 'down' },
    { reason: 'Damaged in Transit', count: 75, pct: 6, trend: 'flat' },
    { reason: 'Other', count: 138, pct: 11, trend: 'flat' },
  ],
  byCategory: [
    { category: 'Apparel', rate: 5.8, change: -0.3 },
    { category: 'Footwear', rate: 4.2, change: +0.1 },
    { category: 'Accessories', rate: 2.1, change: -0.5 },
    { category: 'Electronics', rate: 3.8, change: -0.2 },
    { category: 'Home & Garden', rate: 1.9, change: -0.1 },
  ],
  bySegment: [
    { segment: 'First-Time Buyers', rate: 5.4, orders: 12_800 },
    { segment: 'Repeat Buyers (2-5)', rate: 2.8, orders: 15_620 },
    { segment: 'Loyal (6+)', rate: 1.2, orders: 10_000 },
    { segment: 'High-Value (>$200)', rate: 4.1, orders: 8_200 },
    { segment: 'Gen Z (18-27)', rate: 4.8, orders: 11_400 },
    { segment: 'Boomer (58+)', rate: 1.9, orders: 6_800 },
  ],
  monthlyTrend: [
    { month: 'Jan', rate: 3.8, orders: 3_200, returns: 122 },
    { month: 'Feb', rate: 3.5, orders: 3_000, returns: 105 },
    { month: 'Mar', rate: 3.2, orders: 3_400, returns: 109 },
    { month: 'Apr', rate: 3.1, orders: 3_300, returns: 102 },
    { month: 'May', rate: 3.0, orders: 3_100, returns: 93 },
    { month: 'Jun', rate: 3.3, orders: 3_200, returns: 106 },
    { month: 'Jul', rate: 3.5, orders: 3_500, returns: 123 },
    { month: 'Aug', rate: 3.25, orders: 3_420, returns: 111 },
  ],
  topReturned: [
    { name: 'Slim Fit Chino Pants', returns: 48, reason: 'Size/Fit Issue', revenue: 2_880 },
    { name: 'Wireless Earbuds Pro', returns: 32, reason: 'Quality Defect', revenue: 4_160 },
    { name: 'Linen Summer Blazer', returns: 28, reason: 'Not as Described', revenue: 3_360 },
    { name: 'Running Shoes X1', returns: 24, reason: 'Size/Fit Issue', revenue: 2_880 },
    { name: 'Smart Home Hub', returns: 19, reason: 'Changed Mind', revenue: 2_470 },
  ] };

const REASON_COLORS: Record<string, string> = {
  'Size/Fit Issue': 'bg-blue-500',
  'Quality Defect': 'bg-red-500',
  'Not as Described': 'bg-amber-500',
  'Changed Mind': 'bg-slate-400',
  'Wrong Item Sent': 'bg-orange-500',
  'Damaged in Transit': 'bg-purple-500',
  'Other': 'bg-gray-300' };

const TREND_ICONS: Record<string, string> = {
  up: '↗️',
  down: '↘️',
  flat: '→' };

export default function ReturnRateAnalytics() {
  const [tab, setTab] = useState<'overview' | 'reasons' | 'segments' | 'products'>('overview');
  const data = MOCK_DATA;

  const maxMonthlyRate = useMemo(() => Math.max(...data.monthlyTrend.map(m => m.rate)), [data]);

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        {[
          { label: 'Return Rate', value: `${data.returnRate}%`, color: 'text-amber-600', sub: '↓ 0.3% vs last month' },
          { label: 'Total Returns', value: data.totalReturns.toLocaleString(), color: 'text-slate-900', sub: `of ${data.totalOrders.toLocaleString()} orders` },
          { label: 'Avg Processing', value: `${data.avgProcessingDays} days`, color: 'text-blue-600', sub: 'Target: < 3 days' },
          { label: 'Refund Total', value: `$${(data.refundTotal / 1000).toFixed(1)}K`, color: 'text-red-600', sub: 'Last 30 days' },
          { label: 'Exchange Rate', value: '18%', color: 'text-emerald-600', sub: '↑ 3% vs last month' },
        ].map(stat => (
          <div key={stat.label} className="glass p-4">
            <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">{stat.label}</div>
            <div className={`text-xl font-bold ${stat.color} mt-1`}>{stat.value}</div>
            <div className="text-[11px] text-slate-500 mt-0.5">{stat.sub}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 glass p-1 rounded-xl w-fit">
        {(['overview', 'reasons', 'segments', 'products'] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              tab === t ? 'bg-white/80 text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {tab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Monthly Trend */}
          <div className="glass p-6">
            <h3 className="text-sm font-semibold text-slate-900 mb-4">Monthly Return Rate Trend</h3>
            <div className="flex items-end gap-2 h-40">
              {data.monthlyTrend.map((m, i) => (
                <div key={m.month} className="flex-1 flex flex-col items-center gap-1">
                  <span className="text-[10px] font-bold text-slate-600 tabular-nums">{m.rate}%</span>
                  <div
                    className="w-full bg-gradient-to-t from-amber-400 to-amber-300 rounded-t-lg transition-all duration-500"
                    style={{ height: `${(m.rate / maxMonthlyRate) * 100}%` }}
                  />
                  <span className="text-[10px] text-slate-400 font-medium">{m.month}</span>
                </div>
              ))}
            </div>
          </div>

          {/* By Category */}
          <div className="glass p-6">
            <h3 className="text-sm font-semibold text-slate-900 mb-4">Return Rate by Category</h3>
            <div className="space-y-3">
              {data.byCategory.map(cat => (
                <div key={cat.category}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-slate-700">{cat.category}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-slate-900 tabular-nums">{cat.rate}%</span>
                      <span className={`text-[11px] font-medium ${cat.change < 0 ? 'text-emerald-600' : cat.change > 0 ? 'text-red-600' : 'text-slate-400'}`}>
                        {cat.change > 0 ? '+' : ''}{cat.change}%
                      </span>
                    </div>
                  </div>
                  <div className="w-full bg-white/50 rounded-full h-2 p-0.5">
                    <div
                      className={`rounded-full h-full transition-all duration-500 ${
                        cat.rate > 4 ? 'bg-gradient-to-r from-red-400 to-red-500' :
                        cat.rate > 3 ? 'bg-gradient-to-r from-amber-400 to-amber-500' :
                        'bg-gradient-to-r from-emerald-400 to-emerald-500'
                      }`}
                      style={{ width: `${(cat.rate / 7) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {tab === 'reasons' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="glass p-6">
            <h3 className="text-sm font-semibold text-slate-900 mb-4">Top Return Reasons</h3>
            <div className="space-y-3">
              {data.byReason.map(reason => (
                <div key={reason.reason} className="flex items-center gap-3">
                  <div className={`w-3 h-3 rounded-full ${REASON_COLORS[reason.reason] || 'bg-gray-300'} shrink-0`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-slate-700 truncate">{reason.reason}</span>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="text-sm font-bold text-slate-900 tabular-nums">{reason.pct}%</span>
                        <span className="text-xs">{TREND_ICONS[reason.trend]}</span>
                      </div>
                    </div>
                    <div className="w-full bg-white/50 rounded-full h-1.5 mt-1">
                      <div
                        className={`rounded-full h-full ${REASON_COLORS[reason.reason] || 'bg-gray-300'}`}
                        style={{ width: `${reason.pct}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="glass p-6">
            <h3 className="text-sm font-semibold text-slate-900 mb-2">Actionable Recommendations</h3>
            <div className="space-y-3 mt-4">
              {[
                { title: 'Add size recommendation widget', impact: 'Could reduce Size/Fit returns by 20-30%', effort: 'Medium', priority: 'High' },
                { title: 'Improve product photography', impact: 'Could reduce "Not as described" by 25%', effort: 'Low', priority: 'High' },
                { title: 'Implement quality feedback loop', impact: 'Could reduce defects by 15% over 3 months', effort: 'Medium', priority: 'Medium' },
                { title: 'Add exchange incentives (+10% credit)', impact: 'Could convert 30% of refunds to exchanges', effort: 'Low', priority: 'High' },
              ].map((rec, i) => (
                <div key={i} className="p-3 rounded-xl bg-white/40 border border-white/40">
                  <div className="flex items-start justify-between">
                    <div className="text-sm font-medium text-slate-900">{rec.title}</div>
                    <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                      rec.priority === 'High' ? 'bg-red-50 text-red-700' : 'bg-blue-50 text-blue-700'
                    }`}>{rec.priority}</span>
                  </div>
                  <div className="text-xs text-slate-600 mt-1">{rec.impact}</div>
                  <div className="text-[11px] text-slate-400 mt-0.5">Effort: {rec.effort}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {tab === 'segments' && (
        <div className="glass p-6">
          <h3 className="text-sm font-semibold text-slate-900 mb-4">Return Rate by Customer Segment</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/40">
                  <th className="text-left px-4 py-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider">Segment</th>
                  <th className="text-right px-4 py-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider">Orders</th>
                  <th className="text-right px-4 py-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider">Return Rate</th>
                  <th className="text-left px-4 py-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider w-48">Visual</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/20">
                {data.bySegment.map(seg => (
                  <tr key={seg.segment} className="hover:bg-white/30 transition-colors">
                    <td className="px-4 py-3 font-medium text-slate-900">{seg.segment}</td>
                    <td className="px-4 py-3 text-right text-slate-600 tabular-nums">{seg.orders.toLocaleString()}</td>
                    <td className="px-4 py-3 text-right font-bold text-slate-900 tabular-nums">{seg.rate}%</td>
                    <td className="px-4 py-3">
                      <div className="w-full bg-white/50 rounded-full h-2 p-0.5">
                        <div
                          className={`rounded-full h-full ${
                            seg.rate > 4 ? 'bg-red-400' : seg.rate > 2.5 ? 'bg-amber-400' : 'bg-emerald-400'
                          }`}
                          style={{ width: `${(seg.rate / 6) * 100}%` }}
                        />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'products' && (
        <div className="glass p-6">
          <h3 className="text-sm font-semibold text-slate-900 mb-4">Most Returned Products</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/40">
                  <th className="text-left px-4 py-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider">Product</th>
                  <th className="text-right px-4 py-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider">Returns</th>
                  <th className="text-left px-4 py-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider">Primary Reason</th>
                  <th className="text-right px-4 py-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider">Revenue Lost</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/20">
                {data.topReturned.map(p => (
                  <tr key={p.name} className="hover:bg-white/30 transition-colors">
                    <td className="px-4 py-3 font-medium text-slate-900">{p.name}</td>
                    <td className="px-4 py-3 text-right font-bold text-slate-900 tabular-nums">{p.returns}</td>
                    <td className="px-4 py-3">
                      <span className="text-xs font-medium text-slate-600 bg-white/60 rounded-full px-2 py-0.5">{p.reason}</span>
                    </td>
                    <td className="px-4 py-3 text-right text-red-600 font-medium tabular-nums">${p.revenue.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
