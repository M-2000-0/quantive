import React from 'react';
import { Shield } from 'lucide-react';

interface RecoveryMetric {
  name: string;
  value: string;
  description: string;
  icon: string;
  status: 'met' | 'at_risk' | 'missed';
}

const METRICS: RecoveryMetric[] = [
  { name: 'RTO (Recovery Time Objective)', value: '< 4 hours', description: 'Maximum time to restore service after failure', icon: '⏱️', status: 'met' },
  { name: 'RPO (Recovery Point Objective)', value: '< 15 minutes', description: 'Maximum data loss in case of failure', icon: '💾', status: 'met' },
  { name: 'Backup Frequency', value: 'Every 5 minutes', description: 'Automated backups with point-in-time recovery', icon: 'RefreshCw', status: 'met' },
  { name: 'Geographic Redundancy', value: '3 regions', description: 'Data replicated across 3 geographic regions', icon: 'Globe', status: 'met' },
  { name: 'SLA Uptime', value: '99.99%', description: 'Guaranteed availability with financial penalties', icon: 'TrendingUp', status: 'met' },
  { name: 'Last DR Test', value: '2026-08-15', description: 'Full disaster recovery simulation completed', icon: '🧪', status: 'met' },
];

export default function DisasterRecovery() {
  return (
    <div className="space-y-6 animate-glass-in">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center">
          <Shield className="w-5 h-5" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">Business Continuity & Disaster Recovery</h2>
          <p className="text-sm text-slate-400">What happens if the datacenter burns down? We're ready.</p>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-3 gap-4">
        {METRICS.slice(0, 3).map((m, i) => (
          <div key={i} className="glass rounded-xl p-5 text-center">
            <span className="text-3xl mb-2 block">{m.icon}</span>
            <p className="text-2xl font-bold text-white mb-1">{m.value}</p>
            <p className="text-sm text-slate-400 mb-1">{m.name}</p>
            <p className="text-xs text-slate-500">{m.description}</p>
          </div>
        ))}
      </div>

      {/* Recovery Procedures */}
      <div className="glass rounded-2xl p-6">
        <h3 className="text-sm font-medium text-slate-400 mb-4">RECOVERY PROCEDURES</h3>
        <div className="space-y-3">
          {[
            { phase: '1', title: 'Detection & Alerting', time: '0-5 min', description: 'Automated monitoring detects failure. On-call team alerted via PagerDuty, SMS, and satellite phone.', status: 'Automated' },
            { phase: '2', title: 'Assessment & Triage', time: '5-15 min', description: 'Incident commander assesses scope. Determines recovery strategy: failover, restore, or manual.', status: 'SOP Documented' },
            { phase: '3', title: 'Failover Execution', time: '15-30 min', description: 'Automated failover to secondary region. DNS switches. Users connected to healthy instance.', status: 'Automated' },
            { phase: '4', title: 'Data Recovery', time: '30-60 min', description: 'Point-in-time recovery from backups. Transaction log replay. Data integrity verification.', status: 'Automated + Manual' },
            { phase: '5', title: 'Service Restoration', time: '1-4 hours', description: 'Full service restored. Performance validation. User notification. Post-incident review.', status: 'Manual' },
          ].map((p, i) => (
            <div key={i} className="flex items-start gap-4 p-4 bg-white/5 rounded-xl">
              <span className="w-8 h-8 bg-blue-500/20 text-blue-400 rounded-full flex items-center justify-center text-sm font-bold">{p.phase}</span>
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-1">
                  <h4 className="text-white font-medium">{p.title}</h4>
                  <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded text-xs">{p.time}</span>
                  <span className="px-2 py-0.5 bg-white/10 text-slate-400 rounded text-xs">{p.status}</span>
                </div>
                <p className="text-sm text-slate-400">{p.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Backup Strategy */}
      <div className="glass rounded-2xl p-6">
        <h3 className="text-sm font-medium text-slate-400 mb-4">BACKUP STRATEGY</h3>
        <div className="grid grid-cols-2 gap-4">
          {[
            { type: 'Real-time Replication', frequency: 'Continuous', retention: '30 days', location: '3 geographic regions' },
            { type: 'Automated Snapshots', frequency: 'Every 5 minutes', retention: '90 days', location: 'Encrypted cold storage' },
            { type: 'Daily Full Backup', frequency: 'Daily 02:00 UTC', retention: '1 year', location: 'Offsite vault' },
            { type: 'Archive Backup', frequency: 'Weekly', retention: '7 years', location: 'Air-gapped storage' },
          ].map((b, i) => (
            <div key={i} className="bg-white/5 rounded-xl p-4">
              <h4 className="text-white text-sm font-medium mb-2">{b.type}</h4>
              <div className="space-y-1 text-xs">
                <p><span className="text-slate-500">Frequency: </span><span className="text-white">{b.frequency}</span></p>
                <p><span className="text-slate-500">Retention: </span><span className="text-white">{b.retention}</span></p>
                <p><span className="text-slate-500">Location: </span><span className="text-white">{b.location}</span></p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
