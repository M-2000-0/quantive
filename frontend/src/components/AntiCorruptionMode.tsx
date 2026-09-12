import { useState } from 'react';
import Card, { CardHeader } from './ui/Card';
import Badge from './ui/Badge';

interface Anomaly {
  id: string;
  title: string;
  description: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  category: 'approval' | 'override' | 'beneficiary' | 'timing' | 'access';
  detectedAt: string;
  user: string;
  details: string;
  riskScore: number;
  status: 'open' | 'investigating' | 'resolved';
}

const MOCK_ANOMALIES: Anomaly[] = [
  {
    id: 'a1', title: 'Unusual Approval Pattern Detected',
    description: 'User approved 12 transactions in rapid succession (within 8 minutes) outside normal business hours.',
    severity: 'high', category: 'approval', detectedAt: '2026-08-27T02:34:00Z',
    user: 'analyst@treasury.gov', details: 'All 12 approvals were for amounts between $50M-$200M. Normal pattern: 2-3 approvals per day during business hours. Risk score elevated due to timing and volume.',
    riskScore: 82, status: 'open' },
  {
    id: 'a2', title: 'Manual Override of Automated Limit',
    description: 'Transaction exceeded automatic authorization limit by 340% and was manually approved without secondary review.',
    severity: 'critical', category: 'override', detectedAt: '2026-08-26T16:45:00Z',
    user: 'director@treasury.gov', details: 'Transaction of $850M approved manually. Automatic limit: $250M. Four-eyes principle bypassed. No documentation of exception rationale found.',
    riskScore: 94, status: 'investigating' },
  {
    id: 'a3', title: 'New Beneficiary Added Without Standard Verification',
    description: 'A new bank account was added to the payment system with expedited verification, skipping the standard 48-hour cooling period.',
    severity: 'high', category: 'beneficiary', detectedAt: '2026-08-25T09:12:00Z',
    user: 'ops@treasury.gov', details: 'Beneficiary: Meridian Capital Partners. Account added with "urgent" flag. Standard verification requires dual approval and 48-hour wait. Both requirements waived.',
    riskScore: 88, status: 'open' },
  {
    id: 'a4', title: 'Access Pattern Anomaly',
    description: 'User accessed classified debt portfolio data from an unusual IP address and location.',
    severity: 'medium', category: 'access', detectedAt: '2026-08-24T23:15:00Z',
    user: 'analyst@treasury.gov', details: 'Normal access: Office network, 9am-6pm. This access: VPN from foreign IP, 11pm. User has Top Secret clearance but unusual location.',
    riskScore: 65, status: 'investigating' },
  {
    id: 'a5', title: 'End-of-Quarter Transaction Timing',
    description: 'Large transaction executed 2 hours before quarter-end reporting deadline, potentially affecting reported metrics.',
    severity: 'medium', category: 'timing', detectedAt: '2026-06-30T22:00:00Z',
    user: 'manager@treasury.gov', details: '$1.2B swap executed at 22:00 on last day of Q2. Transaction changed reported duration by 0.3 years. Timing unusual — no historical precedent for late-quarter execution.',
    riskScore: 58, status: 'resolved' },
];

const SEVERITY_CONFIG: Record<string, { label: string; color: string; bg: string; dot: string }> = {
  critical: { label: 'CRITICAL', color: 'text-red-700', bg: 'bg-red-500/12 border-red-500/20', dot: 'bg-red-500 animate-pulse' },
  high: { label: 'HIGH', color: 'text-orange-700', bg: 'bg-orange-500/12 border-orange-500/20', dot: 'bg-orange-500' },
  medium: { label: 'MEDIUM', color: 'text-amber-700', bg: 'bg-amber-500/12 border-amber-500/20', dot: 'bg-amber-500' },
  low: { label: 'LOW', color: 'text-blue-700', bg: 'bg-blue-500/12 border-blue-500/20', dot: 'bg-blue-500' } };

const CATEGORY_ICONS: Record<string, string> = {
  approval: 'CheckCircle', override: 'RefreshCw', beneficiary: 'Landmark', timing: 'Clock', access: 'Key' };

const STATUS_CONFIG: Record<string, { label: string; variant: string }> = {
  open: { label: 'Open', variant: 'danger' },
  investigating: { label: 'Investigating', variant: 'warning' },
  resolved: { label: 'Resolved', variant: 'success' } };

export default function AntiCorruptionMode() {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>('all');

  const filtered = filter === 'all' ? MOCK_ANOMALIES : ([] as Anomaly[]).filter((a) => a.severity === filter);
  const openCount = ([] as Anomaly[]).filter((a) => a.status === 'open').length;

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card><div className="p-4 text-center"><p className="text-2xl font-bold text-red-600">{openCount}</p><p className="text-xs text-slate-500">Open Anomalies</p></div></Card>
        <Card><div className="p-4 text-center"><p className="text-2xl font-bold text-amber-600">{([] as Anomaly[]).filter((a) => a.status === 'investigating').length}</p><p className="text-xs text-slate-500">Investigating</p></div></Card>
        <Card><div className="p-4 text-center"><p className="text-2xl font-bold text-emerald-600">{([] as Anomaly[]).filter((a) => a.status === 'resolved').length}</p><p className="text-xs text-slate-500">Resolved</p></div></Card>
        <Card><div className="p-4 text-center"><p className="text-2xl font-bold text-slate-900">{0}</p><p className="text-xs text-slate-500">Total Detected</p></div></Card>
      </div>

      {/* Filter */}
      <div className="flex items-center gap-2">
        {['all', 'critical', 'high', 'medium', 'low'].map((sev) => (
          <button key={sev} onClick={() => setFilter(sev)} className={`px-3 py-1.5 text-xs font-medium rounded-full border backdrop-blur transition-all ${filter === sev ? 'bg-slate-900 text-white border-slate-900' : 'bg-white/60 text-slate-600 border-white/60 hover:bg-white/80'}`}>
            {sev === 'all' ? 'All Anomalies' : sev.charAt(0).toUpperCase() + sev.slice(1)}
          </button>
        ))}
      </div>

      {/* Anomalies */}
      <div className="space-y-4">
        {filtered.map((a) => {
          const sev = SEVERITY_CONFIG[a.severity];
          const status = STATUS_CONFIG[a.status];
          return (
            <Card key={a.id} padding={false}>
              <div className="px-6 py-5 cursor-pointer hover:bg-white/30 transition-colors" onClick={() => setExpanded(expanded === a.id ? null : a.id)}>
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-start gap-3">
                    <span className="text-lg">{CATEGORY_ICONS[a.category]}</span>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${sev.dot}`} />
                        <h3 className="text-[15px] font-bold text-slate-900">{a.title}</h3>
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5">
                        {a.user} · {new Date(a.detectedAt).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={status.variant as 'danger' | 'warning' | 'success'}>{status.label}</Badge>
                    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold border ${sev.bg} ${sev.color}`}>{sev.label}</span>
                  </div>
                </div>
                <p className="text-sm text-slate-600 mt-2">{a.description}</p>

                {/* Risk score bar */}
                <div className="mt-3 flex items-center gap-3">
                  <span className="text-[10px] font-bold text-slate-400 uppercase">Risk Score</span>
                  <div className="flex-1 h-2 bg-white/50 backdrop-blur-sm border border-white/40 rounded-full p-0.5">
                    <div
                      className={`h-full rounded-full transition-all ${a.riskScore >= 80 ? 'bg-gradient-to-r from-red-500 to-rose-500' : a.riskScore >= 60 ? 'bg-gradient-to-r from-amber-500 to-orange-500' : 'bg-gradient-to-r from-blue-500 to-cyan-500'}`}
                      style={{ width: `${a.riskScore}%` }}
                    />
                  </div>
                  <span className="text-xs font-bold text-slate-700 tabular-nums">{a.riskScore}/100</span>
                </div>

                {expanded === a.id && (
                  <div className="mt-4 pt-4 border-t border-white/40">
                    <div className="bg-slate-50/80 rounded-xl p-4">
                      <p className="text-[10px] font-bold text-slate-400 uppercase mb-1">Detailed Analysis</p>
                      <p className="text-sm text-slate-700">{a.details}</p>
                    </div>
                  </div>
                )}
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
