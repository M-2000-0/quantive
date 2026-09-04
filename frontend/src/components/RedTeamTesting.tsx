import React from 'react';
import { Target } from 'lucide-react';

interface RedTeamExercise {
  id: string;
  name: string;
  type: 'penetration' | 'adversarial' | 'insider_threat' | 'incident_response';
  date: string;
  conductedBy: string;
  findings: { critical: number; high: number; medium: number; low: number };
  status: 'completed' | 'scheduled';
  score: number;
}

const EXERCISES: RedTeamExercise[] = [
  { id: 'rt-001', name: 'Full Penetration Test', type: 'penetration', date: '2026-07-15', conductedBy: 'CrowdStrike', findings: { critical: 0, high: 2, medium: 5, low: 8 }, status: 'completed', score: 94 },
  { id: 'rt-002', name: 'Adversarial ML Testing', type: 'adversarial', date: '2026-07-20', conductedBy: 'Internal Red Team', findings: { critical: 0, high: 0, medium: 3, low: 4 }, status: 'completed', score: 91 },
  { id: 'rt-003', name: 'Insider Threat Simulation', type: 'insider_threat', date: '2026-08-01', conductedBy: 'Deloitte', findings: { critical: 0, high: 1, medium: 2, low: 3 }, status: 'completed', score: 88 },
  { id: 'rt-004', name: 'Incident Response Drill', type: 'incident_response', date: '2026-08-10', conductedBy: 'Internal SOC', findings: { critical: 0, high: 0, medium: 1, low: 2 }, status: 'completed', score: 96 },
  { id: 'rt-005', name: 'Pre-Deployment Pen Test', type: 'penetration', date: '2026-09-15', conductedBy: 'CrowdStrike', findings: { critical: 0, high: 0, medium: 0, low: 0 }, status: 'scheduled', score: 0 },
];

const TYPE_INFO: Record<string, { icon: string; color: string }> = {
  penetration: { icon: 'Target', color: 'red' },
  adversarial: { icon: '🤖', color: 'purple' },
  insider_threat: { icon: '🕵️', color: 'amber' },
  incident_response: { icon: '🚨', color: 'blue' } };

export default function RedTeamTesting() {
  return (
    <div className="space-y-6 animate-glass-in">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-gradient-to-br from-red-500 to-rose-600 rounded-xl flex items-center justify-center">
          <Target className="w-5 h-5" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">Red Team Testing</h2>
          <p className="text-sm text-slate-400">Penetration tests, adversarial AI testing, insider threat simulations</p>
        </div>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-4 gap-4">
        <div className="glass rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-green-400">92%</p>
          <p className="text-xs text-slate-400">Avg Score</p>
        </div>
        <div className="glass rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-green-400">0</p>
          <p className="text-xs text-slate-400">Open Critical</p>
        </div>
        <div className="glass rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-amber-400">3</p>
          <p className="text-xs text-slate-400">Open High</p>
        </div>
        <div className="glass rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-white">4</p>
          <p className="text-xs text-slate-400">Exercises Completed</p>
        </div>
      </div>

      {/* Exercises */}
      <div className="space-y-3">
        {EXERCISES.map(ex => (
          <div key={ex.id} className={`glass rounded-xl p-5 ${ex.status === 'scheduled' ? 'border-l-4 border-amber-500' : ''}`}>
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <span className="text-2xl">{TYPE_INFO[ex.type]?.icon}</span>
                <div>
                  <h4 className="text-white font-medium">{ex.name}</h4>
                  <p className="text-xs text-slate-400">{ex.conductedBy} • {ex.date}</p>
                </div>
              </div>
              {ex.status === 'completed' ? (
                <span className={`text-2xl font-bold ${ex.score >= 90 ? 'text-green-400' : 'text-yellow-400'}`}>{ex.score}%</span>
              ) : (
                <span className="px-3 py-1 bg-amber-500/20 text-amber-400 rounded text-xs font-medium">SCHEDULED</span>
              )}
            </div>
            {ex.status === 'completed' && (
              <div className="mt-3 flex gap-4">
                <span className="text-xs"><span className="text-red-400 font-bold">{ex.findings.critical}</span> Critical</span>
                <span className="text-xs"><span className="text-orange-400 font-bold">{ex.findings.high}</span> High</span>
                <span className="text-xs"><span className="text-yellow-400 font-bold">{ex.findings.medium}</span> Medium</span>
                <span className="text-xs"><span className="text-slate-400 font-bold">{ex.findings.low}</span> Low</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
