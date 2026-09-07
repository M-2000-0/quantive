import { useState, useEffect, useMemo } from 'react';

interface VitalMetric {
  name: string;
  value: number;
  unit: string;
  target: number;
  rating: 'good' | 'needs-improvement' | 'poor';
  history: number[];
}

interface ApiMetric {
  endpoint: string;
  p50: number;
  p95: number;
  p99: number;
  target: number;
  requests: number;
  errors: number;
}

interface SystemHealth {
  cpu: number;
  memory: number;
  disk: number;
  network: number;
  uptime: string;
  activeConnections: number;
  cacheHitRate: number;
}

const MOCK_VITALS: VitalMetric[] = [
  { name: 'LCP', value: 1.8, unit: 's', target: 2.5, rating: 'good', history: [2.1, 1.9, 1.8, 1.7, 1.8, 1.9, 1.8] },
  { name: 'FID', value: 45, unit: 'ms', target: 100, rating: 'good', history: [62, 55, 48, 45, 42, 45, 45] },
  { name: 'CLS', value: 0.05, unit: '', target: 0.1, rating: 'good', history: [0.08, 0.07, 0.06, 0.05, 0.05, 0.04, 0.05] },
  { name: 'TTFB', value: 320, unit: 'ms', target: 800, rating: 'good', history: [410, 380, 350, 320, 310, 320, 320] },
  { name: 'INP', value: 120, unit: 'ms', target: 200, rating: 'good', history: [165, 145, 130, 120, 115, 120, 120] },
  { name: 'FCP', value: 0.9, unit: 's', target: 1.8, rating: 'good', history: [1.2, 1.1, 1.0, 0.9, 0.9, 0.9, 0.9] },
];

const MOCK_API: ApiMetric[] = [
  { endpoint: 'POST /auth/login', p50: 180, p95: 420, p99: 780, target: 200, requests: 12_400, errors: 23 },
  { endpoint: 'GET /portfolios', p50: 120, p95: 280, p99: 450, target: 150, requests: 45_200, errors: 5 },
  { endpoint: 'POST /optimizations', p50: 1_800, p95: 4_200, p99: 8_500, target: 2_000, requests: 8_900, errors: 12 },
  { endpoint: 'GET /market/data', p50: 85, p95: 220, p99: 380, target: 100, requests: 128_000, errors: 45 },
  { endpoint: 'GET /reports/:id', p50: 2_100, p95: 6_800, p99: 12_000, target: 3_000, requests: 3_200, errors: 8 },
  { endpoint: 'WS /stream', p50: 15, p95: 45, p99: 80, target: 50, requests: 89_000, errors: 0 },
  { endpoint: 'GET /audit/logs', p50: 95, p95: 210, p99: 350, target: 200, requests: 2_100, errors: 0 },
];

const MOCK_HEALTH: SystemHealth = {
  cpu: 34,
  memory: 62,
  disk: 45,
  network: 28,
  uptime: '47d 12h 34m',
  activeConnections: 187,
  cacheHitRate: 89 };

function MiniSparkline({ data, color }: { data: number[]; color: string }) {
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const height = 24;
  const width = 60;

  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((v - min) / range) * height;
    return `${x},${y}`;
  }).join(' ');

  return (
    <svg width={width} height={height} className="inline-block">
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function HealthGauge({ label, value, unit, color }: { label: string; value: number; unit: string; color: string }) {
  return (
    <div className="text-center">
      <div className="relative w-16 h-16 mx-auto">
        <svg className="w-16 h-16 -rotate-90" viewBox="0 0 36 36">
          <circle cx="18" cy="18" r="14" fill="none" stroke="currentColor" strokeWidth="3" className="text-white/20" />
          <circle
            cx="18" cy="18" r="14" fill="none" stroke={color} strokeWidth="3"
            strokeDasharray={`${value} ${100 - value}`}
            strokeLinecap="round"
            className="transition-all duration-1000"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-xs font-bold text-slate-900">{value}{unit}</span>
        </div>
      </div>
      <div className="text-[10px] font-medium text-slate-500 mt-1">{label}</div>
    </div>
  );
}

export default function PerformanceMonitor() {
  const [tab, setTab] = useState<'vitals' | 'api' | 'system'>('vitals');
  const [refreshTime, setRefreshTime] = useState(new Date());

  // Simulate live updates
  useEffect(() => {
    const interval = setInterval(() => setRefreshTime(new Date()), 30_000);
    return () => clearInterval(interval);
  }, []);

  const vitalsRating = useMemo(() => {
    const good = MOCK_VITALS.filter(v => v.rating === 'good').length;
    return `${good}/${MOCK_VITALS.length} passing`;
  }, []);

  const apiErrorRate = useMemo(() => {
    const totalReq = MOCK_API.reduce((s, a) => s + a.requests, 0);
    const totalErr = MOCK_API.reduce((s, a) => s + a.errors, 0);
    return ((totalErr / totalReq) * 100).toFixed(2);
  }, []);

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass p-4">
          <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Web Vitals</div>
          <div className="text-xl font-bold text-emerald-600 mt-1">{vitalsRating}</div>
          <div className="text-[11px] text-slate-500 mt-0.5">All metrics within target</div>
        </div>
        <div className="glass p-4">
          <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">API Error Rate</div>
          <div className="text-xl font-bold text-blue-600 mt-1">{apiErrorRate}%</div>
          <div className="text-[11px] text-slate-500 mt-0.5">Target: &lt; 1%</div>
        </div>
        <div className="glass p-4">
          <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Uptime</div>
          <div className="text-xl font-bold text-emerald-600 mt-1">{MOCK_HEALTH.uptime}</div>
          <div className="text-[11px] text-slate-500 mt-0.5">99.97% availability</div>
        </div>
        <div className="glass p-4">
          <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Active Connections</div>
          <div className="text-xl font-bold text-purple-600 mt-1">{MOCK_HEALTH.activeConnections}</div>
          <div className="text-[11px] text-slate-500 mt-0.5">Cache hit: {MOCK_HEALTH.cacheHitRate}%</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center justify-between">
        <div className="flex gap-1 glass p-1 rounded-xl w-fit">
          {(['vitals', 'api', 'system'] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                tab === t ? 'bg-white/80 text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              {t === 'vitals' ? 'Web Vitals' : t === 'api' ? 'API Performance' : 'System Health'}
            </button>
          ))}
        </div>
        <span className="text-[11px] text-slate-400">Last updated: {refreshTime.toLocaleTimeString()}</span>
      </div>

      {tab === 'vitals' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {MOCK_VITALS.map(v => (
            <div key={v.name} className="glass p-5">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">{v.name}</h3>
                  <p className="text-[11px] text-slate-500">Target: &lt; {v.target}{v.unit}</p>
                </div>
                <MiniSparkline data={v.history} color="#10b981" />
              </div>
              <div className="flex items-end gap-2">
                <span className="text-2xl font-bold text-slate-900 tabular-nums">{v.value}</span>
                <span className="text-sm text-slate-500 mb-1">{v.unit}</span>
                <span className="ml-auto inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold bg-emerald-50 text-emerald-700">
                  ✓ Good
                </span>
              </div>
              <div className="mt-3 flex gap-1">
                {v.history.map((h, i) => (
                  <div
                    key={i}
                    className="flex-1 rounded-sm bg-emerald-200"
                    style={{ height: `${(h / (v.target * 1.5)) * 20}px` }}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === 'api' && (
        <div className="glass overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/40 bg-white/20">
                  <th className="text-left px-6 py-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider">Endpoint</th>
                  <th className="text-right px-6 py-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider">P50</th>
                  <th className="text-right px-6 py-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider">P95</th>
                  <th className="text-right px-6 py-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider">P99</th>
                  <th className="text-right px-6 py-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider">Requests</th>
                  <th className="text-right px-6 py-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider">Errors</th>
                  <th className="text-left px-6 py-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider w-32">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/20">
                {MOCK_API.map(a => {
                  const errorRate = a.requests > 0 ? (a.errors / a.requests) * 100 : 0;
                  const p95Status = a.p95 <= a.target ? 'good' : a.p95 <= a.target * 1.5 ? 'warning' : 'poor';
                  return (
                    <tr key={a.endpoint} className="hover:bg-white/30 transition-colors">
                      <td className="px-6 py-3 font-mono text-xs font-medium text-slate-900">{a.endpoint}</td>
                      <td className="px-6 py-3 text-right tabular-nums">{a.p50}ms</td>
                      <td className="px-6 py-3 text-right tabular-nums">{a.p95}ms</td>
                      <td className="px-6 py-3 text-right tabular-nums">{a.p99}ms</td>
                      <td className="px-6 py-3 text-right tabular-nums">{a.requests.toLocaleString()}</td>
                      <td className="px-6 py-3 text-right">
                        <span className={`font-medium ${errorRate > 1 ? 'text-red-600' : errorRate > 0.1 ? 'text-amber-600' : 'text-emerald-600'}`}>
                          {a.errors}
                        </span>
                      </td>
                      <td className="px-6 py-3">
                        <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                          p95Status === 'good' ? 'bg-emerald-50 text-emerald-700' :
                          p95Status === 'warning' ? 'bg-amber-50 text-amber-700' :
                          'bg-red-50 text-red-700'
                        }`}>
                          {p95Status === 'good' ? '✓ Healthy' : p95Status === 'warning' ? '⚠ Slow' : '✗ Critical'}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'system' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="glass p-6">
            <h3 className="text-sm font-semibold text-slate-900 mb-6">Resource Usage</h3>
            <div className="flex justify-around">
              <HealthGauge label="CPU" value={MOCK_HEALTH.cpu} unit="%" color={MOCK_HEALTH.cpu > 80 ? '#ef4444' : MOCK_HEALTH.cpu > 60 ? '#f59e0b' : '#10b981'} />
              <HealthGauge label="Memory" value={MOCK_HEALTH.memory} unit="%" color={MOCK_HEALTH.memory > 80 ? '#ef4444' : MOCK_HEALTH.memory > 60 ? '#f59e0b' : '#10b981'} />
              <HealthGauge label="Disk" value={MOCK_HEALTH.disk} unit="%" color={MOCK_HEALTH.disk > 80 ? '#ef4444' : MOCK_HEALTH.disk > 60 ? '#f59e0b' : '#10b981'} />
              <HealthGauge label="Network" value={MOCK_HEALTH.network} unit="%" color={MOCK_HEALTH.network > 80 ? '#ef4444' : MOCK_HEALTH.network > 60 ? '#f59e0b' : '#10b981'} />
            </div>
          </div>

          <div className="glass p-6">
            <h3 className="text-sm font-semibold text-slate-900 mb-4">System Info</h3>
            <div className="space-y-3">
              {[
                { label: 'Uptime', value: MOCK_HEALTH.uptime },
                { label: 'Active Connections', value: MOCK_HEALTH.activeConnections.toString() },
                { label: 'Cache Hit Rate', value: `${MOCK_HEALTH.cacheHitRate}%` },
                { label: 'Bundle Size (gzip)', value: '187KB' },
                { label: 'Total Tests', value: '885 passing' },
                { label: 'TypeScript Errors', value: '0' },
              ].map(item => (
                <div key={item.label} className="flex items-center justify-between py-1.5">
                  <span className="text-sm text-slate-600">{item.label}</span>
                  <span className="text-sm font-bold text-slate-900 tabular-nums">{item.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
