import React from 'react';

interface BlackSwan {
  id: string;
  name: string;
  description: string;
  probability: string;
  impact: string;
  category: 'geopolitical' | 'economic' | 'environmental' | 'technological' | 'social';
  adversarialAngle: string;
  preparationLevel: number;
}

const SCENARIOS: BlackSwan[] = [
  { id: 'bs-001', name: 'Simultaneous Sovereign Defaults', description: 'Multiple emerging market defaults trigger contagion across frontier markets', probability: '<1%', impact: 'Catastrophic', category: 'economic', adversarialAngle: 'An adversary could deliberately trigger defaults through coordinated sanctions', preparationLevel: 25 },
  { id: 'bs-002', name: 'AI-Driven Market Manipulation', description: 'Sophisticated AI executes coordinated flash crash across sovereign bond markets', probability: '2%', impact: 'Severe', category: 'technological', adversarialAngle: 'State-sponsored AI could target specific sovereign bonds to destabilize', preparationLevel: 40 },
  { id: 'bs-003', name: 'Energy Embargo', description: 'Major supplier cuts off energy exports, triggering fiscal crisis', probability: '5%', impact: 'Severe', category: 'geopolitical', adversarialAngle: 'Energy weapon used to pressure policy changes', preparationLevel: 55 },
  { id: 'bs-004', name: 'Climate Disaster Fiscal Shock', description: 'Major natural disaster causes 5% GDP drop and fiscal emergency', probability: '8%', impact: 'High', category: 'environmental', adversarialAngle: 'Environmental degradation deliberately accelerated', preparationLevel: 30 },
  { id: 'bs-005', name: 'Digital Currency Disruption', description: 'Central bank digital currency adoption disrupts traditional debt markets', probability: '15%', impact: 'Moderate', category: 'technological', adversarialAngle: 'Adversary launches competing CBDC to undermine monetary sovereignty', preparationLevel: 60 },
  { id: 'bs-006', name: 'Pandemic 2.0', description: 'Novel pathogen causes global economic shutdown', probability: '3%', impact: 'Catastrophic', category: 'social', adversarialAngle: 'Bioterrorism risk', preparationLevel: 35 },
];

const CATEGORY_INFO: Record<string, { icon: string; color: string }> = {
  geopolitical: { icon: 'Globe', color: 'red' },
  economic: { icon: 'BarChart3', color: 'amber' },
  environmental: { icon: '🌿', color: 'green' },
  technological: { icon: '💻', color: 'blue' },
  social: { icon: 'Users', color: 'purple' } };

export default function BlackSwanLab() {
  return (
    <div className="space-y-6 animate-glass-in">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-violet-600 rounded-xl flex items-center justify-center">
          <span className="text-lg">🦢</span>
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">Black Swan Laboratory</h2>
          <p className="text-sm text-slate-400">Not stress testing — black swan discovery. What could nobody be considering?</p>
        </div>
      </div>

      {/* Scenarios */}
      <div className="space-y-3">
        {SCENARIOS.map(s => (
          <div key={s.id} className="glass rounded-xl p-5">
            <div className="flex items-start gap-4">
              <span className="text-2xl">{CATEGORY_INFO[s.category]?.icon}</span>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <h4 className="text-white font-medium">{s.name}</h4>
                  <span className={`px-2 py-0.5 rounded text-xs ${s.impact === 'Catastrophic' ? 'bg-red-500/20 text-red-400' : s.impact === 'Severe' ? 'bg-orange-500/20 text-orange-400' : 'bg-yellow-500/20 text-yellow-400'}`}>
                    {s.impact}
                  </span>
                </div>
                <p className="text-sm text-slate-400 mb-2">{s.description}</p>
                <div className="flex items-center gap-4 text-xs">
                  <span className="text-slate-500">Probability: {s.probability}</span>
                  <span className="text-slate-500">Category: {s.category}</span>
                </div>
                <div className="mt-3 p-3 bg-purple-500/10 rounded-xl">
                  <p className="text-xs text-purple-300"><strong>Adversarial Angle:</strong> {s.adversarialAngle}</p>
                </div>
                <div className="mt-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-500">Preparedness:</span>
                    <div className="flex-1 bg-white/5 rounded-full h-1.5">
                      <div className={`h-1.5 rounded-full ${s.preparationLevel >= 60 ? 'bg-green-400' : s.preparationLevel >= 40 ? 'bg-yellow-400' : 'bg-red-400'}`} style={{ width: `${s.preparationLevel}%` }} />
                    </div>
                    <span className="text-xs text-white">{s.preparationLevel}%</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
