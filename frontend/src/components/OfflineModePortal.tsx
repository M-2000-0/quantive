import React, { useState } from 'react';

interface OfflineCapability {
  feature: string;
  offline: 'full' | 'partial' | 'limited';
  description: string;
}

const CAPABILITIES: OfflineCapability[] = [
  { feature: 'Portfolio Viewing', offline: 'full', description: 'View all portfolios, instruments, and positions without internet' },
  { feature: 'Optimization Engine', offline: 'full', description: 'Run solvers locally using cached market data and models' },
  { feature: 'Report Generation', offline: 'full', description: 'Generate PDF, Excel, and CSV reports offline' },
  { feature: 'Approval Workflows', offline: 'full', description: 'Process approvals with digital signatures using local HSM' },
  { feature: 'Audit Logging', offline: 'full', description: 'All actions logged locally, synced when connected' },
  { feature: 'Market Data', offline: 'partial', description: 'Uses cached data (last 24h). Real-time requires connection' },
  { feature: 'Model Updates', offline: 'limited', description: 'Import via USB/manual transfer. No auto-updates' },
  { feature: 'Compliance Reports', offline: 'full', description: 'Generate IMF, World Bank, and local compliance reports' },
  { feature: 'Export Controls', offline: 'full', description: 'Sanctions screening with local database' },
  { feature: 'Multi-User', offline: 'full', description: 'Local LDAP/AD authentication. No cloud auth needed' },
];

const STATUS_COLORS: Record<string, string> = {
  full: 'bg-green-500/20 text-green-400',
  partial: 'bg-yellow-500/20 text-yellow-400',
  limited: 'bg-orange-500/20 text-orange-400' };

export default function OfflineModePortal() {
  const [selected, setSelected] = useState<OfflineCapability | null>(null);

  return (
    <div className="space-y-6 animate-glass-in">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-gradient-to-br from-slate-500 to-gray-600 rounded-xl flex items-center justify-center">
          <span className="text-lg">📴</span>
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">Offline & Air-Gapped Mode</h2>
          <p className="text-sm text-slate-400">Full functionality without internet — via USB, manual import, and local networks</p>
        </div>
      </div>

      {/* Key Guarantees */}
      <div className="glass rounded-2xl p-5">
        <div className="grid grid-cols-4 gap-4">
          {[
            { icon: '📴', title: 'Zero Internet', desc: 'Complete offline operation' },
            { icon: '💾', title: 'USB Updates', desc: 'Manual model/data import' },
            { icon: '🔐', title: 'Local Auth', desc: 'LDAP/AD without cloud' },
            { icon: 'FileText', title: 'Full Audit', desc: 'Synced when connected' },
          ].map((g, i) => (
            <div key={i} className="bg-white/5 rounded-xl p-4 text-center">
              <span className="text-2xl mb-2 block">{g.icon}</span>
              <h4 className="text-white text-sm font-medium">{g.title}</h4>
              <p className="text-xs text-slate-500">{g.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Capabilities */}
      <div className="glass rounded-2xl p-6">
        <h3 className="text-sm font-medium text-slate-400 mb-4">OFFLINE CAPABILITY MATRIX</h3>
        <div className="space-y-2">
          {CAPABILITIES.map((cap, i) => (
            <button key={i} onClick={() => setSelected(cap)} className={`w-full text-left flex items-center gap-4 p-3 rounded-xl transition-all ${selected?.feature === cap.feature ? 'bg-white/10' : 'hover:bg-white/5'}`}>
              <span className="text-white text-sm flex-1">{cap.feature}</span>
              <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[cap.offline]}`}>
                {cap.offline === 'full' ? '✓ Full' : cap.offline === 'partial' ? '~ Partial' : '○ Limited'}
              </span>
            </button>
          ))}
        </div>
      </div>

      {selected && (
        <div className="glass rounded-2xl p-5">
          <h4 className="text-white font-medium mb-2">{selected.feature}</h4>
          <p className="text-sm text-slate-400">{selected.description}</p>
          <div className="mt-3">
            <span className={`px-3 py-1 rounded-lg text-xs font-medium ${STATUS_COLORS[selected.offline]}`}>
              Offline: {selected.offline.toUpperCase()}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
