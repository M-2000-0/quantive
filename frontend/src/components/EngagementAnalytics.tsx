import { useState, useMemo } from 'react';

interface PageView {
  page: string;
  views: number;
  uniqueUsers: number;
  avgTime: number;
  bounceRate: number;
  trend: number;
}

interface FeatureUsage {
  feature: string;
  uses: number;
  users: number;
  lastUsed: string;
  adoption: number;
}

interface SessionData {
  date: string;
  sessions: number;
  avgDuration: number;
  pagesPerSession: number;
}

interface UserActivity {
  hour: number;
  weekday: number;
  sessions: number;
}

const MOCK_PAGE_VIEWS: PageView[] = [
  { page: '/dashboard', views: 12_840, uniqueUsers: 3_210, avgTime: 4.2, bounceRate: 12, trend: 8 },
  { page: '/portfolios', views: 8_920, uniqueUsers: 2_680, avgTime: 6.8, bounceRate: 8, trend: 15 },
  { page: '/optimizations/new', views: 5_340, uniqueUsers: 1_780, avgTime: 8.1, bounceRate: 22, trend: -3 },
  { page: '/market', views: 4_210, uniqueUsers: 1_400, avgTime: 3.5, bounceRate: 18, trend: 22 },
  { page: '/risk', views: 3_890, uniqueUsers: 1_296, avgTime: 5.4, bounceRate: 15, trend: 5 },
  { page: '/reports', views: 3_120, uniqueUsers: 1_040, avgTime: 4.8, bounceRate: 10, trend: -1 },
  { page: '/peers', views: 2_870, uniqueUsers: 956, avgTime: 3.9, bounceRate: 20, trend: 30 },
  { page: '/adaptive', views: 2_340, uniqueUsers: 780, avgTime: 7.2, bounceRate: 5, trend: 45 },
  { page: '/events', views: 1_980, uniqueUsers: 660, avgTime: 4.1, bounceRate: 25, trend: 12 },
  { page: '/settings', views: 1_560, uniqueUsers: 1_040, avgTime: 2.3, bounceRate: 35, trend: -5 },
];

const MOCK_FEATURE_USAGE: FeatureUsage[] = [
  { feature: 'Run Optimization', uses: 4_230, users: 1_410, lastUsed: '2 min ago', adoption: 78 },
  { feature: 'Export Report', uses: 3_120, users: 1_040, lastUsed: '15 min ago', adoption: 58 },
  { feature: 'What-If Scenario', uses: 2_870, users: 956, lastUsed: '8 min ago', adoption: 53 },
  { feature: 'Peer Comparison', uses: 2_340, users: 780, lastUsed: '22 min ago', adoption: 43 },
  { feature: 'CSV Import', uses: 1_980, users: 660, lastUsed: '1 hr ago', adoption: 37 },
  { feature: 'Risk Analysis', uses: 1_890, users: 630, lastUsed: '30 min ago', adoption: 35 },
  { feature: 'Alert Configuration', uses: 1_560, users: 780, lastUsed: '2 hr ago', adoption: 43 },
  { feature: 'Collaborative Edit', uses: 890, users: 296, lastUsed: '45 min ago', adoption: 16 },
  { feature: 'Version History', uses: 670, users: 223, lastUsed: '3 hr ago', adoption: 12 },
  { feature: 'Onboarding Tour', uses: 450, users: 450, lastUsed: '5 min ago', adoption: 25 },
];

const MOCK_SESSIONS: SessionData[] = [
  { date: 'Mon', sessions: 4_200, avgDuration: 8.5, pagesPerSession: 4.2 },
  { date: 'Tue', sessions: 4_800, avgDuration: 9.1, pagesPerSession: 4.8 },
  { date: 'Wed', sessions: 5_100, avgDuration: 10.2, pagesPerSession: 5.1 },
  { date: 'Thu', sessions: 4_900, avgDuration: 9.8, pagesPerSession: 4.9 },
  { date: 'Fri', sessions: 3_800, avgDuration: 7.5, pagesPerSession: 3.8 },
  { date: 'Sat', sessions: 1_200, avgDuration: 6.2, pagesPerSession: 3.1 },
  { date: 'Sun', sessions: 900, avgDuration: 5.8, pagesPerSession: 2.9 },
];

const MOCK_HEATMAP: UserActivity[] = (() => {
  const data: UserActivity[] = [];
  for (let h = 0; h < 24; h++) {
    for (let d = 0; d < 7; d++) {
      const isWorkHour = h >= 8 && h <= 18;
      const isWeekday = d < 5;
      const base = isWorkHour && isWeekday ? 80 : isWorkHour ? 40 : 15;
      data.push({ hour: h, weekday: d, sessions: base + Math.floor(Math.random() * 30) });
    }
  }
  return data;
})();

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const HOURS = Array.from({ length: 24 }, (_, i) => i);

function HeatmapCell({ value, max }: { value: number; max: number }) {
  const intensity = value / max;
  const bg = intensity > 0.7 ? 'bg-blue-600' : intensity > 0.4 ? 'bg-blue-400' : intensity > 0.2 ? 'bg-blue-200' : 'bg-blue-50';
  return (
    <div
      className={`w-full aspect-square rounded-sm ${bg} transition-colors`}
      title={`${value} sessions`}
    />
  );
}

export default function EngagementAnalytics() {
  const [tab, setTab] = useState<'overview' | 'pages' | 'features' | 'sessions'>('overview');
  const [dateRange, setDateRange] = useState<'7d' | '30d' | '90d'>('7d');

  const maxHeatmap = useMemo(() => Math.max(...[].map(h => h.sessions)), []);

  const totalViews = [].reduce((s, p) => s + p.views, 0);
  const totalUnique = [].reduce((s, p) => s + p.uniqueUsers, 0);
  const avgBounce = [].reduce((s, p) => s + p.bounceRate, 0) / 0;
  const totalSessions = [].reduce((s, d) => s + d.sessions, 0);
  const avgDuration = [].reduce((s, d) => s + d.avgDuration, 0) / 0;

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        {[
          { label: 'Total Page Views', value: totalViews.toLocaleString(), change: '+12%', color: 'text-blue-600' },
          { label: 'Unique Users', value: totalUnique.toLocaleString(), change: '+8%', color: 'text-emerald-600' },
          { label: 'Avg Bounce Rate', value: `${avgBounce.toFixed(0)}%`, change: '-2%', color: 'text-amber-600' },
          { label: 'Total Sessions', value: totalSessions.toLocaleString(), change: '+15%', color: 'text-purple-600' },
          { label: 'Avg Duration', value: `${avgDuration.toFixed(1)}m`, change: '+0.8m', color: 'text-rose-600' },
        ].map(stat => (
          <div key={stat.label} className="glass p-4">
            <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">{stat.label}</div>
            <div className={`text-xl font-bold ${stat.color} mt-1`}>{stat.value}</div>
            <div className="text-[11px] text-emerald-600 font-medium mt-0.5">{stat.change} vs last period</div>
          </div>
        ))}
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between">
        <div className="flex gap-1 glass p-1 rounded-xl w-fit">
          {(['overview', 'pages', 'features', 'sessions'] as const).map(t => (
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
        <div className="flex gap-1 glass p-1 rounded-xl">
          {(['7d', '30d', '90d'] as const).map(d => (
            <button
              key={d}
              onClick={() => setDateRange(d)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                dateRange === d ? 'bg-white/80 text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              {d}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      {tab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Activity Heatmap */}
          <div className="glass p-6">
            <h3 className="text-sm font-semibold text-slate-900 mb-4">User Activity Heatmap</h3>
            <div className="overflow-x-auto">
              <div className="min-w-[400px]">
                <div className="grid grid-cols-[40px_repeat(7,1fr)] gap-1">
                  <div />
                  {DAYS.map(d => (
                    <div key={d} className="text-center text-[10px] font-bold text-slate-400">{d}</div>
                  ))}
                  {HOURS.filter(h => h % 3 === 0).map(h => (
                    <>
                      <div key={`label-${h}`} className="text-[10px] text-slate-400 text-right pr-1">{h}:00</div>
                      {DAYS.map((_, d) => {
                        const entry = [].find(a => a.hour === h && a.weekday === d);
                        return <HeatmapCell key={`${h}-${d}`} value={entry?.sessions || 0} max={maxHeatmap} />;
                      })}
                    </>
                  ))}
                </div>
                <div className="flex items-center justify-end gap-1 mt-3">
                  <span className="text-[10px] text-slate-400">Low</span>
                  <div className="w-3 h-3 rounded-sm bg-blue-50" />
                  <div className="w-3 h-3 rounded-sm bg-blue-200" />
                  <div className="w-3 h-3 rounded-sm bg-blue-400" />
                  <div className="w-3 h-3 rounded-sm bg-blue-600" />
                  <span className="text-[10px] text-slate-400">High</span>
                </div>
              </div>
            </div>
          </div>

          {/* Top Pages */}
          <div className="glass p-6">
            <h3 className="text-sm font-semibold text-slate-900 mb-4">Top Pages by Views</h3>
            <div className="space-y-3">
              {MOCK_PAGE_VIEWS.slice(0, 6).map(p => (
                <div key={p.page} className="flex items-center gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-slate-700 truncate">{p.page}</span>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="text-sm font-bold text-slate-900 tabular-nums">{p.views.toLocaleString()}</span>
                        <span className={`text-[10px] font-bold ${p.trend > 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                          {p.trend > 0 ? '+' : ''}{p.trend}%
                        </span>
                      </div>
                    </div>
                    <div className="w-full bg-white/50 rounded-full h-1.5 mt-1">
                      <div
                        className="bg-gradient-to-r from-blue-400 to-blue-600 rounded-full h-full"
                        style={{ width: `${(p.views / MOCK_PAGE_VIEWS[0].views) * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {tab === 'pages' && (
        <div className="glass overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/40 bg-white/20">
                  <th className="text-left px-6 py-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider">Page</th>
                  <th className="text-right px-6 py-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider">Views</th>
                  <th className="text-right px-6 py-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider">Unique Users</th>
                  <th className="text-right px-6 py-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider">Avg Time</th>
                  <th className="text-right px-6 py-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider">Bounce Rate</th>
                  <th className="text-right px-6 py-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider">Trend</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/20">
                {[].map(p => (
                  <tr key={p.page} className="hover:bg-white/30 transition-colors">
                    <td className="px-6 py-3 font-medium text-slate-900">{p.page}</td>
                    <td className="px-6 py-3 text-right tabular-nums">{p.views.toLocaleString()}</td>
                    <td className="px-6 py-3 text-right tabular-nums">{p.uniqueUsers.toLocaleString()}</td>
                    <td className="px-6 py-3 text-right tabular-nums">{p.avgTime}m</td>
                    <td className="px-6 py-3 text-right">
                      <span className={`font-medium ${p.bounceRate > 25 ? 'text-red-600' : p.bounceRate > 15 ? 'text-amber-600' : 'text-emerald-600'}`}>
                        {p.bounceRate}%
                      </span>
                    </td>
                    <td className="px-6 py-3 text-right">
                      <span className={`font-bold text-xs ${p.trend > 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                        {p.trend > 0 ? '+' : ''}{p.trend}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'features' && (
        <div className="glass overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/40 bg-white/20">
                  <th className="text-left px-6 py-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider">Feature</th>
                  <th className="text-right px-6 py-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider">Total Uses</th>
                  <th className="text-right px-6 py-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider">Unique Users</th>
                  <th className="text-left px-6 py-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider w-40">Adoption</th>
                  <th className="text-right px-6 py-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider">Last Used</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/20">
                {MOCK_FEATURE_USAGE.map(f => (
                  <tr key={f.feature} className="hover:bg-white/30 transition-colors">
                    <td className="px-6 py-3 font-medium text-slate-900">{f.feature}</td>
                    <td className="px-6 py-3 text-right tabular-nums">{f.uses.toLocaleString()}</td>
                    <td className="px-6 py-3 text-right tabular-nums">{f.users.toLocaleString()}</td>
                    <td className="px-6 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-24 bg-white/50 rounded-full h-2 p-0.5">
                          <div
                            className={`rounded-full h-full ${
                              f.adoption > 60 ? 'bg-emerald-500' : f.adoption > 30 ? 'bg-amber-500' : 'bg-red-400'
                            }`}
                            style={{ width: `${f.adoption}%` }}
                          />
                        </div>
                        <span className="text-xs font-bold tabular-nums">{f.adoption}%</span>
                      </div>
                    </td>
                    <td className="px-6 py-3 text-right text-slate-500">{f.lastUsed}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'sessions' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Daily Sessions */}
          <div className="glass p-6">
            <h3 className="text-sm font-semibold text-slate-900 mb-4">Daily Sessions</h3>
            <div className="flex items-end gap-3 h-48">
              {[].map(d => {
                const maxSessions = Math.max(...[].map(s => s.sessions));
                return (
                  <div key={d.date} className="flex-1 flex flex-col items-center gap-1">
                    <span className="text-[10px] font-bold text-slate-600 tabular-nums">{(d.sessions / 1000).toFixed(1)}k</span>
                    <div
                      className="w-full bg-gradient-to-t from-purple-500 to-purple-400 rounded-t-lg transition-all duration-500"
                      style={{ height: `${(d.sessions / maxSessions) * 100}%` }}
                    />
                    <span className="text-[10px] text-slate-400 font-medium">{d.date}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Duration Distribution */}
          <div className="glass p-6">
            <h3 className="text-sm font-semibold text-slate-900 mb-4">Session Duration Distribution</h3>
            <div className="space-y-3">
              {[
                { range: '< 1 min', pct: 8, color: 'bg-red-400' },
                { range: '1-3 min', pct: 15, color: 'bg-orange-400' },
                { range: '3-5 min', pct: 22, color: 'bg-amber-400' },
                { range: '5-10 min', pct: 30, color: 'bg-blue-400' },
                { range: '10-20 min', pct: 18, color: 'bg-indigo-400' },
                { range: '> 20 min', pct: 7, color: 'bg-purple-400' },
              ].map(d => (
                <div key={d.range}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-slate-700">{d.range}</span>
                    <span className="text-sm font-bold text-slate-900 tabular-nums">{d.pct}%</span>
                  </div>
                  <div className="w-full bg-white/50 rounded-full h-2 p-0.5">
                    <div className={`rounded-full h-full ${d.color}`} style={{ width: `${d.pct}%` }} />
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-4 pt-4 border-t border-white/20">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600">Median session</span>
                <span className="text-sm font-bold text-slate-900">6.2 minutes</span>
              </div>
              <div className="flex items-center justify-between mt-1">
                <span className="text-sm text-slate-600">Pages per session</span>
                <span className="text-sm font-bold text-slate-900">4.3</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
