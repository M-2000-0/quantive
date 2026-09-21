import { useCallback, useEffect, useState } from 'react';
import {
  Clock, CheckCircle, AlertTriangle, TrendingUp,
  FileText, Plus, RefreshCw
} from 'lucide-react';
import { api } from '../api';
import type { SLACompliance as SLAComplianceType, SLABreach } from '../types';

export default function SLAMonitoringPage() {
  const [compliance, setCompliance] = useState<SLAComplianceType | null>(null);
  const [breaches, setBreaches] = useState<SLABreach[]>([]);
  const [credits, setCredits] = useState<any>(null);
  const [documentation, setDocumentation] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [complianceData, breachesData, creditsData, docData] = await Promise.all([
        api.sla.compliance().catch(() => null),
        api.sla.getBreaches(30).catch(() => []),
        api.sla.getCredits().catch(() => null),
        api.sla.documentation().catch(() => null),
      ]);

      if (complianceData) setCompliance(complianceData);
      if (breachesData) setBreaches(breachesData?.breaches || []);
      if (creditsData) setCredits(creditsData);
      if (docData) setDocumentation(docData);
    } catch (e) {
      console.error('Failed to load SLA data:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="animate-pulse space-y-6">
            <div className="h-8 bg-slate-200 rounded w-1/3"></div>
            <div className="h-64 bg-slate-200 rounded-lg"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
              <Clock className="w-8 h-8 text-blue-600" />
              SLA Monitoring
            </h1>
            <p className="text-slate-600 mt-2">
              Service level agreement compliance, incident tracking, and breach penalties.
            </p>
          </div>
          <button
            onClick={loadData}
            className="flex items-center gap-2 bg-white text-slate-700 px-4 py-2 rounded-lg border border-slate-200 hover:bg-slate-50"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>

        {/* Compliance Status */}
        {compliance && (
          <div className={`rounded-xl p-6 mb-8 ${
            compliance.overall_compliance >= 99.9
              ? 'bg-gradient-to-r from-emerald-600 to-emerald-700 text-white'
              : 'bg-gradient-to-r from-red-500 to-red-600 text-white'
          }`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                {compliance.overall_compliance >= 99.9 ? (
                  <CheckCircle className="w-10 h-10" />
                ) : (
                  <AlertTriangle className="w-10 h-10" />
                )}
                <div>
                  <div className="text-2xl font-bold">
                    {compliance.overall_compliance >= 99.9 ? 'SLA Compliant' : 'SLA Breach'}
                  </div>
                  <div className="text-emerald-100">
                    {compliance.breaches} incidents this month
                  </div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-4xl font-bold">
                  {compliance.uptime_pct.toFixed(2)}%
                </div>
                <div className="text-emerald-100">Current Uptime</div>
              </div>
            </div>
          </div>
        )}

        {/* SLA Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
            <div className="text-sm text-slate-500 mb-1">Monthly Uptime</div>
            <div className="flex items-end gap-2">
              <span className="text-3xl font-bold text-slate-900">
                {compliance?.uptime_pct.toFixed(2) || '0'}%
              </span>
              <span className="text-sm text-slate-500 mb-1">
                / 99.95% target
              </span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-2 mt-3">
              <div
                className={`h-2 rounded-full ${(compliance?.uptime_pct || 0) >= 99.95 ? 'bg-emerald-500' : 'bg-red-500'}`}
                style={{ width: `${Math.min(compliance?.uptime_pct || 0, 100)}%` }}
              ></div>
            </div>
          </div>
          <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
            <div className="text-sm text-slate-500 mb-1">Incidents This Month</div>
            <div className="text-3xl font-bold text-slate-900">
              {compliance?.breaches || 0}
            </div>
          </div>
          <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
            <div className="text-sm text-slate-500 mb-1">Credits Owed</div>
            <div className="text-3xl font-bold text-amber-600">
              ${compliance?.credits_owed?.toFixed(2) || '0.00'}
            </div>
          </div>
        </div>

        {/* Breach History */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 mb-6">
          <div className="p-4 border-b border-slate-200">
            <h2 className="font-semibold text-slate-900">Breach History (30 days)</h2>
          </div>
          <div className="divide-y divide-slate-200 max-h-64 overflow-y-auto">
            {breaches.length === 0 ? (
              <div className="p-6 text-center text-slate-500">No breaches in the last 30 days</div>
            ) : (
              breaches.map((breach, idx) => (
                <div key={idx} className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <AlertTriangle className="w-4 h-4 text-red-500" />
                      <div>
                        <div className="font-medium text-slate-900 text-sm">{breach.type}</div>
                        <div className="text-xs text-slate-500">{breach.id}</div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm text-slate-500">{breach.severity}</div>
                      <div className="text-xs text-slate-400">
                        {new Date(breach.started_at).toLocaleString()}
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* SLA Documentation */}
        {documentation && (
          <div className="bg-white rounded-xl shadow-sm border border-slate-200">
            <div className="p-4 border-b border-slate-200">
              <h2 className="font-semibold text-slate-900 flex items-center gap-2">
                <FileText className="w-5 h-5" />
                SLA Documentation
              </h2>
            </div>
            <div className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 bg-slate-50 rounded-lg">
                  <h3 className="font-medium text-slate-900 mb-2">Commitments</h3>
                  <ul className="text-sm text-slate-600 space-y-1">
                    <li>Monthly Uptime: ≥ {documentation.uptime_sla || '99.95%'}</li>
                    <li>API Response P95: ≤ {documentation.response_time_sla || '500ms'}</li>
                    <li>RTO: {documentation.rto_sla || '4 hours'}</li>
                    <li>RPO: {documentation.rpo_sla || '15 minutes'}</li>
                  </ul>
                </div>
                <div className="p-4 bg-slate-50 rounded-lg">
                  <h3 className="font-medium text-slate-900 mb-2">Penalties</h3>
                  <ul className="text-sm text-slate-600 space-y-1">
                    <li>99.90-99.95%: 10% credit</li>
                    <li>99.50-99.90%: 25% credit</li>
                    <li>99.00-99.50%: 50% credit</li>
                    <li>&lt; 99.00%: 100% credit</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
