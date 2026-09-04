import React from 'react';
import { Shield } from 'lucide-react';

interface Assessment {
  id: string;
  type: 'penetration_test' | 'vulnerability_assessment' | 'code_review' | 'architecture_review';
  name: string;
  conductedBy: string;
  date: string;
  score: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  remediated: number;
  status: 'completed' | 'in_progress';
}

const ASSESSMENTS: Assessment[] = [
  { id: 'sa-001', type: 'penetration_test', name: 'Annual Penetration Test', conductedBy: 'CrowdStrike', date: '2026-07-15', score: 94, critical: 0, high: 2, medium: 5, low: 8, remediated: 13, status: 'completed' },
  { id: 'sa-002', type: 'vulnerability_assessment', name: 'Quarterly Vulnerability Scan', conductedBy: 'Internal Security', date: '2026-08-01', score: 91, critical: 0, high: 1, medium: 8, low: 12, remediated: 19, status: 'completed' },
  { id: 'sa-003', type: 'code_review', name: 'Secure Code Review', conductedBy: 'NCC Group', date: '2026-06-20', score: 89, critical: 0, high: 3, medium: 6, low: 10, remediated: 17, status: 'completed' },
  { id: 'sa-004', type: 'architecture_review', name: 'Security Architecture Review', conductedBy: 'Deloitte', date: '2026-05-10', score: 92, critical: 0, high: 1, medium: 4, low: 7, remediated: 11, status: 'completed' },
  { id: 'sa-005', type: 'penetration_test', name: 'Pre-Deployment Pen Test', conductedBy: 'CrowdStrike', date: '2026-09-01', score: 0, critical: 0, high: 0, medium: 0, low: 0, remediated: 0, status: 'in_progress' },
];

const TYPE_INFO: Record<string, { icon: string; color: string }> = {
  penetration_test: { icon: 'Target', color: 'red' },
  vulnerability_assessment: { icon: 'Search', color: 'amber' },
  code_review: { icon: 'PencilLine', color: 'blue' },
  architecture_review: { icon: 'Building', color: 'purple' } };

export default function SecurityAssessment() {
  return (
    <div className="space-y-6 animate-glass-in">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-gradient-to-br from-red-500 to-orange-600 rounded-xl flex items-center justify-center">
          <Shield className="w-5 h-5" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">Independent Security Assessment</h2>
          <p className="text-sm text-slate-400">Penetration tests, vulnerability assessments, and remediation history</p>
        </div>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-4 gap-4">
        <div className="glass rounded-xl p-4 text-center">
          <p className="text-3xl font-bold text-green-400">91%</p>
          <p className="text-xs text-slate-400">Avg Security Score</p>
        </div>
        <div className="glass rounded-xl p-4 text-center">
          <p className="text-3xl font-bold text-red-400">0</p>
          <p className="text-xs text-slate-400">Open Critical</p>
        </div>
        <div className="glass rounded-xl p-4 text-center">
          <p className="text-3xl font-bold text-amber-400">3</p>
          <p className="text-xs text-slate-400">Open High</p>
        </div>
        <div className="glass rounded-xl p-4 text-center">
          <p className="text-3xl font-bold text-green-400">92%</p>
          <p className="text-xs text-slate-400">Remediation Rate</p>
        </div>
      </div>

      {/* Assessments */}
      <div className="space-y-3">
        {ASSESSMENTS.map(a => (
          <div key={a.id} className={`glass rounded-xl p-5 ${a.status === 'in_progress' ? 'border-l-4 border-amber-500' : ''}`}>
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <span className="text-2xl">{TYPE_INFO[a.type]?.icon}</span>
                <div>
                  <h4 className="text-white font-medium">{a.name}</h4>
                  <p className="text-xs text-slate-400">Conducted by {a.conductedBy} • {a.date}</p>
                </div>
              </div>
              {a.status === 'completed' ? (
                <span className={`text-2xl font-bold ${a.score >= 90 ? 'text-green-400' : a.score >= 75 ? 'text-yellow-400' : 'text-red-400'}`}>
                  {a.score}%
                </span>
              ) : (
                <span className="px-3 py-1 bg-amber-500/20 text-amber-400 rounded-lg text-xs font-medium">IN PROGRESS</span>
              )}
            </div>
            {a.status === 'completed' && (
              <div className="mt-3 flex gap-4">
                <span className="text-xs"><span className="text-red-400 font-bold">{a.critical}</span> Critical</span>
                <span className="text-xs"><span className="text-orange-400 font-bold">{a.high}</span> High</span>
                <span className="text-xs"><span className="text-yellow-400 font-bold">{a.medium}</span> Medium</span>
                <span className="text-xs"><span className="text-slate-400 font-bold">{a.low}</span> Low</span>
                <span className="text-xs"><span className="text-green-400 font-bold">{a.remediated}</span> Remediated</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
