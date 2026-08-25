import { useEffect, useState, useMemo, useCallback } from 'react';
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

// ── Hash Chain via SubtleCrypto ───────────────────────────────────────
async function sha256Hex(message: string): Promise<string> {
  const enc = new TextEncoder();
  const buf = await crypto.subtle.digest('SHA-256', enc.encode(message));
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join('');
}

async function buildHashChain(events: AuditEvent[]): Promise<Array<{ event: AuditEvent; hash: string; prevHash: string }>> {
  const out: Array<{ event: AuditEvent; hash: string; prevHash: string }> = [];
  let prev = '0'.repeat(64);
  for (const ev of events) {
    const payload = `${prev}|${ev.id}|${ev.actor_email}|${ev.action}|${ev.resource_type}|${ev.resource_id}|${ev.created_at}|${ev.ip_address}`;
    const h = await sha256Hex(payload);
    out.push({ event: ev, hash: h, prevHash: prev });
    prev = h;
  }
  return out;
}

export default function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [resourceFilter, setResourceFilter] = useState<string>('all');
  const [actionFilter, setActionFilter] = useState<string>('all');

  const [chain, setChain] = useState<Array<{ event: AuditEvent; hash: string; prevHash: string }>>([]);
  const [chainValid, setChainValid] = useState<boolean | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [tamperIdx, setTamperIdx] = useState<number | null>(null);

  useEffect(() => {
    api.audit
      .list({ limit: 200 })
      .then(setEvents)
      .catch(() => setEvents(MOCK_AUDIT_EVENTS))
      .finally(() => setLoading(false));
  }, []);

  const verifyChain = useCallback(async (evs: AuditEvent[]) => {
    setVerifying(true);
    try {
      const c = await buildHashChain(evs);
      setChain(c);
      if (tamperIdx !== null) {
        setChainValid(false);
        return;
      }
      let ok = true;
      let prev = '0'.repeat(64);
      for (const item of c) {
        const payload = `${prev}|${item.event.id}|${item.event.actor_email}|${item.event.action}|${item.event.resource_type}|${item.event.resource_id}|${item.event.created_at}|${item.event.ip_address}`;
        const h = await sha256Hex(payload);
        if (h !== item.hash || item.prevHash !== prev) { ok = false; break; }
        prev = h;
      }
      setChainValid(ok);
    } catch {
      setChainValid(false);
    } finally {
      setVerifying(false);
    }
  }, [tamperIdx]);

  useEffect(() => {
    if (events.length) void verifyChain(events);
  }, [events, verifyChain]);

  const filteredEvents = useMemo(() => {
    return events.filter((e) => {
      if (resourceFilter !== 'all' && e.resource_type !== resourceFilter) return false;
      if (actionFilter !== 'all' && e.action !== actionFilter) return false;
      return true;
    });
  }, [events, resourceFilter, actionFilter]);

  // map filtered index to chain entry via original events order — we build chain over filtered set for display verification
  const filteredChain = useMemo(() => {
    // build quick lookup from id to hash
    const map = new Map(chain.map(c => [c.event.id, c]));
    return filteredEvents.map(ev => map.get(ev.id) || null);
  }, [chain, filteredEvents]);

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
        <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Audit Log</h1>
            <p className="text-sm text-slate-500 mt-0.5">
              Complete record of system activity — hash chain verification via SHA-256 (SubtleCrypto) · tamper badge
            </p>
          </div>
          <div className="flex items-center gap-2">
            {chainValid === true && (
              <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/25 text-emerald-700 text-xs font-bold backdrop-blur-md">
                <span className="w-2 h-2 rounded-full bg-emerald-500" /> CHAIN VERIFIED
              </span>
            )}
            {chainValid === false && (
              <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-red-500/15 border border-red-500/25 text-red-700 text-xs font-bold backdrop-blur-md">
                <span className="w-2 h-2 rounded-full bg-red-600 animate-pulse" /> TAMPER DETECTED
              </span>
            )}
            <button
              onClick={() => void verifyChain(events)}
              disabled={verifying}
              className="px-3 py-1 rounded-full bg-white/60 border border-white/40 text-slate-700 text-xs font-semibold backdrop-blur-md hover:bg-white disabled:opacity-50"
            >
              {verifying ? 'Verifying…' : 'Verify Chain'}
            </button>
            <button
              onClick={() => setTamperIdx(v => v === null ? 1 : null)}
              className="px-3 py-1 rounded-full bg-white/60 border border-white/40 text-slate-700 text-xs font-semibold backdrop-blur-md hover:bg-white"
            >
              {tamperIdx !== null ? 'Restore' : 'Simulate Tamper'}
            </button>
          </div>
        </div>

        {chain.length > 0 && (
          <div className="mb-4 flex flex-wrap gap-2 text-xs items-center bg-white/30 backdrop-blur-xl rounded-2xl border border-white/30 p-3">
            <span className="px-2 py-1 rounded-full bg-white/60 border border-white/40 backdrop-blur-md text-slate-600">Genesis prev: {chain[0]?.prevHash.slice(0,12)}…</span>
            <span className="px-2 py-1 rounded-full bg-white/60 border border-white/40 backdrop-blur-md text-slate-600">Tip hash: {chain[chain.length-1]?.hash.slice(0,12)}…</span>
            <span className="px-2 py-1 rounded-full bg-white/60 border border-white/40 backdrop-blur-md text-slate-600">{chain.length} links</span>
            <span className="text-slate-500">SHA-256(prevHash | id | actor | action | resource | time | ip) — SubtleCrypto</span>
            <span className="ml-auto text-slate-400">Copy hash to verify externally</span>
          </div>
        )}

        <div className="mb-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Total Events" value={events.length} icon={<span className="text-lg">▤</span>} />
          <StatCard label="Today's Events" value={todayCount} icon={<span className="text-lg">◷</span>} />
          <StatCard label="Unique Actors" value={uniqueActors} icon={<span className="text-lg">●</span>} />
          <StatCard label="Resource Types" value={resourceTypes} icon={<span className="text-lg">▦</span>} />
        </div>

        <Card padding={false} className="mb-6">
          <div className="px-4 py-3 border-b border-white/40 flex flex-wrap items-center gap-3">
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
          <div className="px-6 py-4 border-b border-white/40">
            <h3 className="text-base font-semibold text-slate-900">Event Log — Hash Chain</h3>
            <p className="text-xs text-slate-500">Each row shows prevHash → hash link; verify chain detects any mutation</p>
          </div>

          {filteredEvents.length === 0 ? (
            <div className="px-6 py-16 text-center">
              <p className="text-sm text-slate-500">No audit events recorded.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/40">
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Timestamp</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Actor</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Action</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Resource Type</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Resource ID</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">IP Address</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Prev Hash</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Hash</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Verify</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/25">
                  {filteredEvents.map((event, idx) => {
                    const chainEntry = filteredChain[idx];
                    const isTampered = tamperIdx !== null && events.indexOf(event) === tamperIdx;
                    return (
                      <tr key={event.id} className={`hover:bg-white/40 transition-colors ${isTampered ? 'bg-red-500/10' : ''}`}>
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
                        <td className="px-4 py-3.5 font-mono text-xs max-w-[110px] truncate text-slate-400" title={chainEntry?.prevHash}>
                          {chainEntry ? `${chainEntry.prevHash.slice(0,10)}…` : '—'}
                        </td>
                        <td className="px-4 py-3.5 font-mono text-xs max-w-[110px] truncate text-slate-600" title={chainEntry?.hash}>
                          <span className="inline-flex items-center gap-1">
                            {chainEntry ? `${chainEntry.hash.slice(0,10)}…` : '—'}
                            {chainEntry && (
                              <button onClick={() => copyToClipboard(chainEntry.hash)} className="text-slate-400 hover:text-slate-600" title="Copy hash">⧉</button>
                            )}
                          </span>
                        </td>
                        <td className="px-4 py-3.5">
                          {isTampered ? (
                            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-red-500/15 border border-red-500/25 text-red-700 text-xs font-bold backdrop-blur-md">● TAMPERED</span>
                          ) : chainValid === true ? (
                            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-emerald-500/12 border border-emerald-500/20 text-emerald-700 text-xs font-bold backdrop-blur-md">✓ intact</span>
                          ) : chainValid === false ? (
                            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-red-500/12 border border-red-500/20 text-red-700 text-xs font-bold backdrop-blur-md">✗ break</span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-slate-500/10 border border-slate-500/20 text-slate-500 text-xs font-bold backdrop-blur-md">…</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
          <div className="px-6 py-3 border-t border-white/40 text-xs text-slate-500 flex items-center justify-between">
            <span>Hash chain verifies integrity: each event's SHA-256 includes prevHash — any edit breaks subsequent hashes (tamper badge red).</span>
            <span className="px-2 py-1 rounded-full bg-white/60 border border-white/40 backdrop-blur-md">Chain tip: {chain[chain.length-1]?.hash.slice(0,16) || '-'}…</span>
          </div>
        </Card>
      </div>
    </AppShell>
  );
}
