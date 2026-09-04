import React, { useState } from 'react';

interface AIModel {
  id: string;
  name: string;
  type: string;
  version: string;
  lastTrained: string;
  accuracy: number;
  biasScore: number;
  status: 'validated' | 'pending' | 'deprecated';
  trainingData: string;
  documentation: string;
}

const MODELS: AIModel[] = [
  { id: 'm1', name: 'Optimization Solver', type: 'MILP + Metaheuristic', version: '3.2.1', lastTrained: '2026-08-01', accuracy: 94, biasScore: 2, status: 'validated', trainingData: '10Y historical market data, 50K scenarios', documentation: 'Full methodology docs available' },
  { id: 'm2', name: 'Risk Prediction', type: 'Ensemble ML', version: '2.8.0', lastTrained: '2026-07-15', accuracy: 89, biasScore: 5, status: 'validated', trainingData: 'Sovereign default data, CDS spreads, macro indicators', documentation: 'Model cards and fairness reports available' },
  { id: 'm3', name: 'Market Forecasting', type: 'LSTM Neural Network', version: '1.4.2', lastTrained: '2026-06-30', accuracy: 82, biasScore: 8, status: 'validated', trainingData: '30Y yield curve history, macro data', documentation: 'Confidence intervals documented' },
  { id: 'm4', name: 'Fraud Detection', type: 'Anomaly Detection', version: '2.1.0', lastTrained: '2026-08-10', accuracy: 91, biasScore: 3, status: 'validated', trainingData: 'Transaction patterns, behavioral baselines', documentation: 'False positive rates documented' },
];

export default function AIGovernanceLayer() {
  const [selected, setSelected] = useState<AIModel | null>(null);

  return (
    <div className="space-y-6 animate-glass-in">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center">
          <span className="text-lg">🤖</span>
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">AI Governance Layer</h2>
          <p className="text-sm text-slate-400">Model documentation, bias detection, explainability, and human-in-the-loop controls</p>
        </div>
      </div>

      {/* Key Principles */}
      <div className="glass rounded-2xl p-5">
        <div className="grid grid-cols-4 gap-4">
          {[
            { icon: 'Users', title: 'Human Approval', desc: 'No autonomous execution' },
            { icon: 'BarChart3', title: 'Confidence Scoring', desc: 'Every prediction scored' },
            { icon: 'Search', title: 'Full Explainability', desc: 'Every recommendation explained' },
            { icon: 'PencilLine', title: 'Audit Trail', desc: 'Complete decision history' },
          ].map((p, i) => (
            <div key={i} className="bg-white/5 rounded-xl p-4 text-center">
              <span className="text-2xl mb-2 block">{p.icon}</span>
              <h4 className="text-white text-sm font-medium">{p.title}</h4>
              <p className="text-xs text-slate-500">{p.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Models */}
      <div className="grid grid-cols-2 gap-4">
        {MODELS.map(m => (
          <button key={m.id} onClick={() => setSelected(m)} className={`text-left glass rounded-xl p-5 transition-all ${selected?.id === m.id ? 'ring-2 ring-indigo-500/50' : 'hover:bg-white/5'}`}>
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-white font-medium">{m.name}</h4>
              <span className={`px-2 py-0.5 rounded text-xs ${m.status === 'validated' ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'}`}>
                {m.status}
              </span>
            </div>
            <p className="text-xs text-slate-400 mb-2">{m.type} • v{m.version}</p>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <p className="text-xs text-slate-500">Accuracy</p>
                <p className="text-sm font-bold text-white">{m.accuracy}%</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Bias Score</p>
                <p className={`text-sm font-bold ${m.biasScore <= 5 ? 'text-green-400' : 'text-yellow-400'}`}>{m.biasScore}/100</p>
              </div>
            </div>
          </button>
        ))}
      </div>

      {selected && (
        <div className="glass rounded-2xl p-6 space-y-4">
          <h3 className="text-lg font-bold text-white">{selected.name}</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-white/5 rounded-xl p-4">
              <h4 className="text-xs text-slate-500 mb-2">TRAINING DATA</h4>
              <p className="text-sm text-slate-300">{selected.trainingData}</p>
            </div>
            <div className="bg-white/5 rounded-xl p-4">
              <h4 className="text-xs text-slate-500 mb-2">DOCUMENTATION</h4>
              <p className="text-sm text-slate-300">{selected.documentation}</p>
            </div>
          </div>
          <div className="p-4 bg-indigo-500/10 border border-indigo-500/20 rounded-xl">
            <p className="text-sm text-indigo-300">🤖 <strong>AI Governance:</strong> This model has been independently validated. Human approval is required for all recommendations. Bias testing conducted quarterly. Full model cards and change logs maintained.</p>
          </div>
        </div>
      )}
    </div>
  );
}
