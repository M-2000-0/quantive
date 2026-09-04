import React from 'react';

interface DataSource {
  name: string;
  type: string;
  reliability: number;
  freshness: number;
  confidence: number;
  lastUpdate: string;
  conflicts: number;
  status: 'trusted' | 'warning' | 'untrusted';
}

const SOURCES: DataSource[] = [
  { name: 'Bloomberg Terminal', type: 'Market Data', reliability: 98, freshness: 99, confidence: 97, lastUpdate: 'Real-time', conflicts: 0, status: 'trusted' },
  { name: 'IMF Data', type: 'Fundamental', reliability: 95, freshness: 70, confidence: 92, lastUpdate: '2026-07-15', conflicts: 0, status: 'trusted' },
  { name: 'World Bank', type: 'Fundamental', reliability: 94, freshness: 65, confidence: 90, lastUpdate: '2026-06-30', conflicts: 0, status: 'trusted' },
  { name: 'Central Bank Data', type: 'Official', reliability: 99, freshness: 85, confidence: 98, lastUpdate: '2026-08-20', conflicts: 0, status: 'trusted' },
  { name: 'Reuters Eikon', type: 'Market Data', reliability: 97, freshness: 98, confidence: 96, lastUpdate: 'Real-time', conflicts: 0, status: 'trusted' },
  { name: 'Local Ministry Data', type: 'Government', reliability: 85, freshness: 60, confidence: 80, lastUpdate: '2026-05-01', conflicts: 2, status: 'warning' },
  { name: 'Credit Rating Agency', type: 'Credit', reliability: 92, freshness: 75, confidence: 88, lastUpdate: '2026-07-01', conflicts: 0, status: 'trusted' },
];

export default function DataSourceTrust() {
  return (
    <div className="space-y-6 animate-glass-in">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-xl flex items-center justify-center">
          <span className="text-lg">🔗</span>
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">Data Source Trust Scoring</h2>
          <p className="text-sm text-slate-400">Reliability, freshness, confidence, and conflict detection for every data feed</p>
        </div>
      </div>

      {/* Sources */}
      <div className="space-y-3">
        {SOURCES.sort((a, b) => a.status === 'warning' ? -1 : 1).map((s, i) => (
          <div key={i} className={`glass rounded-xl p-4 ${s.status === 'warning' ? 'border-l-4 border-yellow-500' : ''}`}>
            <div className="flex items-center justify-between mb-3">
              <div>
                <h4 className="text-white font-medium">{s.name}</h4>
                <p className="text-xs text-slate-400">{s.type} • Last: {s.lastUpdate}</p>
              </div>
              <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                s.status === 'trusted' ? 'bg-green-500/20 text-green-400' :
                s.status === 'warning' ? 'bg-yellow-500/20 text-yellow-400' :
                'bg-red-500/20 text-red-400'
              }`}>
                {s.status}
              </span>
            </div>
            <div className="grid grid-cols-4 gap-3">
              {[
                { label: 'Reliability', value: s.reliability },
                { label: 'Freshness', value: s.freshness },
                { label: 'Confidence', value: s.confidence },
                { label: 'Conflicts', value: s.conflicts * 25, display: `${s.conflicts} found` },
              ].map((m, j) => (
                <div key={j} className="text-center">
                  <p className={`text-lg font-bold ${
                    (typeof m.value === 'number' ? m.value : 0) >= 90 ? 'text-green-400' :
                    (typeof m.value === 'number' ? m.value : 0) >= 70 ? 'text-yellow-400' : 'text-red-400'
                  }`}>
                    {m.display || `${m.value}%`}
                  </p>
                  <p className="text-xs text-slate-500">{m.label}</p>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="p-4 bg-cyan-500/10 border border-cyan-500/20 rounded-xl">
        <p className="text-sm text-cyan-300">🔗 <strong>Data Trust:</strong> If one feed is wrong, decisions are wrong. Every data source is scored for reliability, freshness, and consistency before being used in any optimization or analysis.</p>
      </div>
    </div>
  );
}
