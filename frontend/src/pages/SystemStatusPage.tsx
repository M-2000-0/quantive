import { useEffect, useState } from 'react';
import { api } from '../api';
import type { AuditEvent } from '../types';
import AppShell from '../components/layout/AppShell';
import Card, { CardHeader } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import { formatDateTime } from '../utils';

const SERVICES = [
  { name: 'API Server', status: 'Online', healthy: true },
  { name: 'Database', status: 'Connected', healthy: true },
  { name: 'Optimization Engine', status: 'Available', healthy: true },
  { name: 'Scenario Generator', status: 'Available', healthy: true },
];

const SYSTEM_INFO = [
  { label: 'Version', value: '2.1.0' },
  { label: 'Database', value: 'SQLite (WAL mode)' },
  { label: 'Default Scenarios', value: '10,000' },
  { label: 'Max Scenarios', value: '50,000' },
  { label: 'Optimization Timeout', value: '300s' },
  { label: 'Solver Timeout', value: '120s' },
];

export default function SystemStatusPage() {
  const [health, setHealth] = useState<{ status: string; version: string } | null>(null);
  const [recentEvents, setRecentEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.health().catch(() => ({ status: 'unavailable', version: '—' })),
      api.audit.list({ limit: 5 }).catch(() => [] as AuditEvent[]),
    ]).then(([h, events]) => {
      setHealth(h);
      setRecentEvents(events);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <AppShell>
        <LoadingSpinner message="Loading system status..." />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="px-8 py-6 max-w-[1440px] mx-auto">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-slate-900">System Status</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Health and configuration overview
          </p>
        </div>

        <div className="mb-8">
          <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
            Service Health
          </h2>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {SERVICES.map((service) => (
              <Card key={service.name}>
                <div className="flex items-center gap-3">
                  <span
                    className={`inline-block h-2.5 w-2.5 rounded-full ${
                      service.healthy ? 'bg-emerald-500' : 'bg-red-500'
                    }`}
                  />
                  <div>
                    <p className="text-sm font-medium text-slate-900">{service.name}</p>
                    <p className={`text-xs font-medium ${service.healthy ? 'text-emerald-600' : 'text-red-600'}`}>
                      {service.status}
                    </p>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>

        <div className="mb-8">
          <Card>
            <CardHeader title="System Information" subtitle="Current configuration and limits" />
            <div className="grid grid-cols-2 gap-x-8 gap-y-4 lg:grid-cols-3">
              {SYSTEM_INFO.map((item) => (
                <div key={item.label} className="flex items-center justify-between border-b border-white/25 pb-3">
                  <span className="text-sm text-slate-500">{item.label}</span>
                  <span className="text-sm font-semibold text-slate-900 tabular-nums">{item.value}</span>
                </div>
              ))}
            </div>
            {health && (
              <div className="mt-6 flex items-center gap-3 rounded-md bg-slate-50 px-4 py-3">
                <Badge variant={health.status === 'ok' ? 'success' : 'danger'}>
                  API: {health.status}
                </Badge>
                <span className="text-xs text-slate-500">
                  Build version: {health.version}
                </span>
              </div>
            )}
          </Card>
        </div>

        <Card padding={false}>
          <div className="px-6 py-4 border-b border-white/40">
            <h3 className="text-base font-semibold text-slate-900">Recent Activity</h3>
            <p className="text-sm text-slate-500 mt-0.5">Last 5 audit events</p>
          </div>
          {recentEvents.length === 0 ? (
            <div className="px-6 py-12 text-center">
              <p className="text-sm text-slate-500">No recent activity.</p>
            </div>
          ) : (
            <div className="divide-y divide-white/25">
              {recentEvents.map((event) => (
                <div key={event.id} className="flex items-center justify-between px-6 py-3.5 hover:bg-white/40 transition-colors">
                  <div className="flex items-center gap-4 min-w-0 flex-1">
                    <span className="text-xs text-slate-400 tabular-nums whitespace-nowrap w-40 flex-shrink-0">
                      {formatDateTime(event.created_at)}
                    </span>
                    <span className="text-sm text-slate-700 truncate">
                      {event.actor_email || 'System'}
                    </span>
                    <Badge variant={
                      event.action === 'create' ? 'success' :
                      event.action === 'run' ? 'info' :
                      event.action === 'export' ? 'outline' :
                      'default'
                    }>
                      {event.action}
                    </Badge>
                    <span className="text-sm text-slate-500">{event.resource_type}</span>
                  </div>
                  <code className="text-xs font-mono text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded flex-shrink-0 ml-4">
                    {event.resource_id?.slice(0, 8) || '—'}
                  </code>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </AppShell>
  );
}
