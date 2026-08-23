import { useEffect, useState, useMemo } from 'react';
import { api } from '../api';
import { MOCK_AUDIT_EVENTS } from '../api/mock';
import type { AuditEvent } from '../types';
import AppShell from '../components/layout/AppShell';
import Card from '../components/ui/Card';
import StatCard from '../components/ui/StatCard';
import Badge from '../components/ui/Badge';
import LoadingSpinner from '../components/ui/LoadingSpinner';

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  const day = d.getDate();
  const month = d.toLocaleString('en-GB', { month: 'short' });
  const year = d.getFullYear();
  const hours = d.getHours();
  const minutes = d.getMinutes().toString().padStart(2, '0');
  const ampm = hours >= 12 ? 'PM' : 'AM';
  const h12 = hours % 12 || 12;
  return `${day} ${month} ${year}, ${h12}:${minutes} ${ampm}`;
}

function isToday(iso: string): boolean {
  const d = new Date(iso);
  const now = new Date();
  return (
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate()
  );
}

const ACTION_BADGE: Record<string, 'success' | 'info' | 'outline' | 'default'> = {
  create: 'success',
  run: 'info',
  export: 'outline',
  view: 'default',
};

const RESOURCE_BADGE: Record<string, 'info' | 'success' | 'warning' | 'default'> = {
  portfolio: 'info',
  optimization: 'success',
  report: 'warning',
};

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text).catch(() => {});
}

export default function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [resourceFilter, setResourceFilter] = useState<string>('all');
  const [actionFilter, setActionFilter] = useState<string>('all');

  useEffect(() => {
    api.audit
      .list({ limit: 200 })
      .then(setEvents)
      .catch(() => setEvents(MOCK_AUDIT_EVENTS))
      .finally(() => setLoading(false));
  }, []);

  const filteredEvents = useMemo(() => {
    return events.filter((e) => {
      if (resourceFilter !== 'all' && e.resource_type !== resourceFilter) return false;
      if (actionFilter !== 'all' && e.action !== actionFilter) return false;
      return true;
    });
  }, [events, resourceFilter, actionFilter]);

  const todayCount = useMemo(
    () => events.filter((e) => isToday(e.created_at)).length,
    [events],
  );

  const uniqueActors = useMemo(
    () => new Set(events.map((e) => e.actor_email).filter(Boolean)).size,
    [events],
  );

  const resourceTypes = useMemo(
    () => new Set(events.map((e) => e.resource_type)).size,
    [events],
  );

  if (loading) {
    return (
      <AppShell>
        <LoadingSpinner message="Loading audit log..." />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="px-8 py-6 max-w-[1440px] mx-auto">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-slate-900">Audit Log</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Complete record of system activity for compliance and review
          </p>
        </div>

        <div className="mb-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Total Events" value={events.length} icon={<span className="text-lg">▤</span>} />
          <StatCard label="Today's Events" value={todayCount} icon={<span className="text-lg">◷</span>} />
          <StatCard label="Unique Actors" value={uniqueActors} icon={<span className="text-lg">●</span>} />
          <StatCard label="Resource Types" value={resourceTypes} icon={<span className="text-lg">▦</span>} />
        </div>

        <Card padding={false} className="mb-6">
          <div className="px-4 py-3 border-b border-slate-200 flex flex-wrap items-center gap-3">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Filters</span>

            <select
              value={resourceFilter}
              onChange={(e) => setResourceFilter(e.target.value)}
              className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="all">Resource Type: All</option>
              <option value="portfolio">Portfolio</option>
              <option value="optimization">Optimization</option>
              <option value="report">Report</option>
            </select>

            <select
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="all">Action: All</option>
              <option value="create">Create</option>
              <option value="run">Run</option>
              <option value="export">Export</option>
              <option value="view">View</option>
            </select>

            <span className="text-xs text-slate-400 ml-auto">
              {filteredEvents.length} of {events.length} events
            </span>
          </div>
        </Card>

        <Card padding={false}>
          <div className="px-6 py-4 border-b border-slate-200">
            <h3 className="text-base font-semibold text-slate-900">Event Log</h3>
          </div>

          {filteredEvents.length === 0 ? (
            <div className="px-6 py-16 text-center">
              <p className="text-sm text-slate-500">No audit events recorded.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Timestamp</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Actor</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Action</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Resource Type</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Resource ID</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">IP Address</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredEvents.map((event) => (
                    <tr key={event.id} className="hover:bg-slate-50 transition-colors">
                      <td className="px-4 py-3.5 text-slate-700 tabular-nums whitespace-nowrap">
                        {formatTimestamp(event.created_at)}
                      </td>
                      <td className="px-4 py-3.5 font-medium text-slate-900">
                        {event.actor_email || 'System'}
                      </td>
                      <td className="px-4 py-3.5">
                        <Badge variant={ACTION_BADGE[event.action] ?? 'default'}>
                          {event.action}
                        </Badge>
                      </td>
                      <td className="px-4 py-3.5">
                        <Badge variant={RESOURCE_BADGE[event.resource_type] ?? 'default'}>
                          {event.resource_type}
                        </Badge>
                      </td>
                      <td className="px-4 py-3.5">
                        <div className="flex items-center gap-2">
                          <code className="text-xs font-mono text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded">
                            {event.resource_id?.slice(0, 8) || '—'}
                          </code>
                          {event.resource_id && (
                            <button
                              onClick={() => copyToClipboard(event.resource_id!)}
                              className="text-slate-400 hover:text-slate-600 transition-colors"
                              title="Copy full ID"
                            >
                              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 01-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 011.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 00-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 01-1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 00-3.375-3.375h-1.5a1.125 1.125 0 01-1.125-1.125v-1.5a3.375 3.375 0 00-3.375-3.375H9.75" />
                              </svg>
                            </button>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3.5 text-slate-500 tabular-nums font-mono text-xs">
                        {event.ip_address || '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </AppShell>
  );
}
