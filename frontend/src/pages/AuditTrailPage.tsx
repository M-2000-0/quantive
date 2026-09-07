import { useCallback, useEffect, useState } from 'react';
import {
  Shield, Search, Plus, CheckCircle, AlertTriangle,
  Clock, ExternalLink, RefreshCw, FileText
} from 'lucide-react';
import { api } from '../api';

interface AuditEvent {
  event_id: string;
  timestamp: string;
  event_type: string;
  actor_id: string;
  resource_type: string;
  resource_id: string;
  action: string;
  integrity_valid: boolean;
}

export default function AuditTrailPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    event_type: '',
    actor_id: '',
    start_date: '',
    end_date: '',
  });
  const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null);
  const [verifyResult, setVerifyResult] = useState<any>(null);

  const loadEvents = useCallback(async () => {
    setLoading(true);
    try {
      const params: any = { limit: 50 };
      if (filters.event_type) params.event_type = filters.event_type;
      if (filters.actor_id) params.actor_id = filters.actor_id;
      if (filters.start_date) params.start_date = filters.start_date;
      if (filters.end_date) params.end_date = filters.end_date;

      const data = await api.immutableAudit.query(params);
      setEvents(data.events || []);
    } catch (e) {
      console.error('Failed to load audit events:', e);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    void loadEvents();
  }, [loadEvents]);

  const verifyEvent = async (eventId: string) => {
    try {
      const result = await api.immutableAudit.verify(eventId);
      setVerifyResult(result);
      setSelectedEvent(events.find(e => e.event_id === eventId) || null);
    } catch (e) {
      console.error('Verification failed:', e);
    }
  };

  const eventTypeColors: Record<string, string> = {
    authentication: 'bg-blue-100 text-blue-700',
    authorization: 'bg-purple-100 text-purple-700',
    data_access: 'bg-emerald-100 text-emerald-700',
    data_modification: 'bg-amber-100 text-amber-700',
    system_config: 'bg-red-100 text-red-700',
    ai_decision: 'bg-cyan-100 text-cyan-700',
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
              <Shield className="w-8 h-8 text-blue-600" />
              Immutable Audit Trail
            </h1>
            <p className="text-slate-600 mt-2">
              Cryptographically verified audit log with tamper-evident hash chain.
            </p>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-xl shadow-sm p-4 border border-slate-200 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Event Type</label>
              <select
                value={filters.event_type}
                onChange={(e) => setFilters({ ...filters, event_type: e.target.value })}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
              >
                <option value="">All Types</option>
                <option value="authentication">Authentication</option>
                <option value="authorization">Authorization</option>
                <option value="data_access">Data Access</option>
                <option value="data_modification">Data Modification</option>
                <option value="system_config">System Config</option>
                <option value="ai_decision">AI Decision</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Actor</label>
              <input
                type="text"
                placeholder="User ID..."
                value={filters.actor_id}
                onChange={(e) => setFilters({ ...filters, actor_id: e.target.value })}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Start Date</label>
              <input
                type="date"
                value={filters.start_date}
                onChange={(e) => setFilters({ ...filters, start_date: e.target.value })}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">End Date</label>
              <input
                type="date"
                value={filters.end_date}
                onChange={(e) => setFilters({ ...filters, end_date: e.target.value })}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
              />
            </div>
          </div>
          <div className="flex justify-end mt-4">
            <button
              onClick={loadEvents}
              className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 text-sm"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
          </div>
        </div>

        {/* Event List */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          {loading ? (
            <div className="p-12 text-center">
              <div className="animate-spin w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full mx-auto"></div>
              <p className="text-slate-500 mt-4">Loading audit events...</p>
            </div>
          ) : events.length === 0 ? (
            <div className="p-12 text-center">
              <Shield className="w-12 h-12 text-slate-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-900 mb-2">No audit events found</h3>
              <p className="text-slate-500">Adjust filters or generate some activity.</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-200">
              {events.map(event => (
                <div
                  key={event.event_id}
                  className="p-4 hover:bg-slate-50 cursor-pointer"
                  onClick={() => setSelectedEvent(event)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className={`px-2 py-1 rounded text-xs font-medium ${eventTypeColors[event.event_type] || 'bg-slate-100 text-slate-700'}`}>
                        {event.event_type}
                      </div>
                      <div>
                        <div className="font-medium text-slate-900 text-sm">{event.action}</div>
                        <div className="text-xs text-slate-500">
                          {event.resource_type}/{event.resource_id}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <div className="text-xs text-slate-500">{event.actor_id}</div>
                        <div className="text-xs text-slate-400">
                          {new Date(event.timestamp).toLocaleString()}
                        </div>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          verifyEvent(event.event_id);
                        }}
                        className="p-2 hover:bg-slate-100 rounded-lg"
                        title="Verify integrity"
                      >
                        {event.integrity_valid ? (
                          <CheckCircle className="w-4 h-4 text-emerald-500" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 text-red-500" />
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Verification Modal */}
        {verifyResult && selectedEvent && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl shadow-xl max-w-lg w-full mx-4 p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-slate-900">Integrity Verification</h3>
                <button onClick={() => setVerifyResult(null)} className="text-slate-400 hover:text-slate-600">
                  ×
                </button>
              </div>
              <div className="space-y-3">
                <div className={`p-4 rounded-lg ${verifyResult.valid ? 'bg-emerald-50' : 'bg-red-50'}`}>
                  <div className="flex items-center gap-2">
                    {verifyResult.valid ? (
                      <CheckCircle className="w-5 h-5 text-emerald-600" />
                    ) : (
                      <AlertTriangle className="w-5 h-5 text-red-600" />
                    )}
                    <span className={`font-medium ${verifyResult.valid ? 'text-emerald-800' : 'text-red-800'}`}>
                      {verifyResult.valid ? 'Integrity Verified' : 'Integrity Compromised'}
                    </span>
                  </div>
                </div>
                <div className="text-sm space-y-1">
                  <div><span className="text-slate-500">Event ID:</span> {verifyResult.event_id}</div>
                  <div><span className="text-slate-500">Chain Valid:</span> {verifyResult.chain_valid ? 'Yes' : 'No'}</div>
                  <div><span className="text-slate-500">Timestamp:</span> {new Date(verifyResult.timestamp).toLocaleString()}</div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
