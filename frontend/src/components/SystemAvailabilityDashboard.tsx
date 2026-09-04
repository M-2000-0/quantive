import React from 'react';
import { ChartColumn as BarChart3 } from 'lucide-react';

interface UptimeData {
  month: string;
  uptime: number;
  incidents: number;
  maintenance: string;
}

const UPTIME_HISTORY: UptimeData[] = [
  { month: 'Feb 2026', uptime: 99.99, incidents: 0, maintenance: '0 min' },
  { month: 'Mar 2026', uptime: 99.99, incidents: 0, maintenance: '15 min' },
  { month: 'Apr 2026', uptime: 100.00, incidents: 0, maintenance: '0 min' },
  { month: 'May 2026', uptime: 99.98, incidents: 1, maintenance: '30 min' },
  { month: 'Jun 2026', uptime: 99.99, incidents: 0, maintenance: '20 min' },
  { month: 'Jul 2026', uptime: 100.00, incidents: 0, maintenance: '0 min' },
  { month: 'Aug 2026', uptime: 99.99, incidents: 0, maintenance: '10 min' },
];

const SERVICES = [
  { name: 'Core Optimization Engine', status: 'operational', uptime: '99.99%' },
  { name: 'API Gateway', status: 'operational', uptime: '100.00%' },
  { name: 'Authentication Service', status: 'operational', uptime: '99.99%' },
  { name: 'Database Cluster', status: 'operational', uptime: '100.00%' },
  { name: 'Real-time Market Data', status: 'operational', uptime: '99.98%' },
  { name: 'Report Generation', status: 'operational', uptime: '99.99%' },
  { name: 'Backup Systems', status: 'operational', uptime: '100.00%' },
  { name: 'Monitoring & Alerting', status: 'operational', uptime: '100.00%' },
];

const STATUS_COLORS: Record<string, string> = {
  operational: 'bg-green-400',
  degraded: 'bg-yellow-400',
  outage: 'bg-red-400' };

export default function SystemAvailabilityDashboard() {
  const avgUptime = (UPTIME_HISTORY.reduce((sum, u) => sum + u.uptime, 0) / UPTIME_HISTORY.length).toFixed(2);
  const totalIncidents = UPTIME_HISTORY.reduce((sum, u) => sum + u.incidents, 0);

  return (
    <div className="space-y-6 animate-glass-in">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-gradient-to-br from-green-500 to-emerald-600 rounded-xl flex items-center justify-center">
          <BarChart3 className="w-5 h-5" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">System Availability</h2>
          <p className="text-sm text-slate-400">Real-time uptime monitoring and SLA compliance</p>
        </div>
      </div>

      {/* Status Banner */}
      <div className="bg-green-500/10 border border-green-500/20 rounded-2xl p-4 flex items-center gap-3">
        <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse" />
        <span className="text-green-400 font-medium">All Systems Operational</span>
        <span className="text-xs text-slate-500 ml-auto">Last updated: {new Date().toLocaleTimeString()}</span>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-4 gap-4">
        <div className="glass rounded-xl p-4 text-center">
          <p className="text-3xl font-bold text-green-400">{avgUptime}%</p>
          <p className="text-xs text-slate-400">Avg Uptime (7mo)</p>
        </div>
        <div className="glass rounded-xl p-4 text-center">
          <p className="text-3xl font-bold text-white">{totalIncidents}</p>
          <p className="text-xs text-slate-400">Total Incidents (7mo)</p>
        </div>
        <div className="glass rounded-xl p-4 text-center">
          <p className="text-3xl font-bold text-white">&lt; 15min</p>
          <p className="text-xs text-slate-400">Avg Recovery Time</p>
        </div>
        <div className="glass rounded-xl p-4 text-center">
          <p className="text-3xl font-bold text-green-400">99.99%</p>
          <p className="text-xs text-slate-400">SLA Commitment</p>
        </div>
      </div>

      {/* Uptime History */}
      <div className="glass rounded-2xl p-6">
        <h3 className="text-sm font-medium text-slate-400 mb-4">UPTIME HISTORY</h3>
        <div className="flex items-end gap-2 h-32">
          {UPTIME_HISTORY.map((u, i) => (
            <div key={i} className="flex-1 flex flex-col items-center">
              <div
                className="w-full bg-gradient-to-t from-green-500/60 to-green-400/20 rounded-t-lg"
                style={{ height: `${(u.uptime - 99.9) * 500}%` }}
              />
              <p className="text-xs text-slate-500 mt-1">{u.month.split(' ')[0]}</p>
              <p className="text-xs text-white font-medium">{u.uptime}%</p>
            </div>
          ))}
        </div>
      </div>

      {/* Service Status */}
      <div className="glass rounded-2xl p-6">
        <h3 className="text-sm font-medium text-slate-400 mb-4">SERVICE STATUS</h3>
        <div className="space-y-2">
          {SERVICES.map((s, i) => (
            <div key={i} className="flex items-center gap-3 p-3 bg-white/5 rounded-xl">
              <div className={`w-2.5 h-2.5 rounded-full ${STATUS_COLORS[s.status]}`} />
              <span className="text-white text-sm flex-1">{s.name}</span>
              <span className="text-xs text-green-400">{s.uptime}</span>
              <span className="px-2 py-0.5 bg-green-500/20 text-green-400 rounded text-xs capitalize">{s.status}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
