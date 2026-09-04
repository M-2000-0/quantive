import React from 'react';

interface ValidationReport {
  model: string;
  date: string;
  validator: string;
  score: number;
  biasTests: { name: string; result: 'pass' | 'warn' | 'fail' }[];
  methodology: string;
  mathematicalProof: string;
}

const REPORTS: ValidationReport[] = [
  {
    model: 'Optimization Solver v3.2.1', date: '2026-08-01', validator: 'Deloitte Independent Review',
    score: 94,
    biasTests: [
      { name: 'Currency bias test', result: 'pass' },
      { name: 'Maturity bias test', result: 'pass' },
      { name: 'Counterparty bias test', result: 'pass' },
      { name: 'Region bias test', result: 'pass' },
      { name: 'Size bias test', result: 'warn' },
    ],
    methodology: 'MILP solver validated against analytical solutions for 1,000 test cases. Metaheuristic convergence verified via 10,000 Monte Carlo runs.',
    mathematicalProof: 'Optimality gap < 0.1% for all test cases. Convergence guaranteed within 500 iterations for feasible problems.' },
  {
    model: 'Risk Prediction v2.8.0', date: '2026-07-15', validator: 'Internal Model Validation Team',
    score: 89,
    biasTests: [
      { name: 'Sovereign bias test', result: 'pass' },
      { name: 'Rating bias test', result: 'pass' },
      { name: 'Geographic bias test', result: 'warn' },
      { name: 'Time period bias test', result: 'pass' },
    ],
    methodology: 'Ensemble model validated via out-of-sample testing on 5Y rolling window. Backtested against 12 sovereign default events.',
    mathematicalProof: 'AUC-ROC: 0.89. Calibration error < 3%. Brier score: 0.12.' },
];

export default function ModelValidation() {
  return (
    <div className="space-y-6 animate-glass-in">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-gradient-to-br from-amber-500 to-orange-600 rounded-xl flex items-center justify-center">
          <span className="text-lg">📐</span>
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">Model Validation & Bias Detection</h2>
          <p className="text-sm text-slate-400">Independent validation, methodology documentation, and bias testing</p>
        </div>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        <div className="glass rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-green-400">91%</p>
          <p className="text-xs text-slate-400">Avg Validation Score</p>
        </div>
        <div className="glass rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-green-400">8/9</p>
          <p className="text-xs text-slate-400">Bias Tests Passed</p>
        </div>
        <div className="glass rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-white">2</p>
          <p className="text-xs text-slate-400">Independent Reviews</p>
        </div>
      </div>

      {/* Reports */}
      <div className="space-y-4">
        {REPORTS.map((r, i) => (
          <div key={i} className="glass rounded-2xl p-6 space-y-4">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-lg font-bold text-white">{r.model}</h3>
                <p className="text-sm text-slate-400">Validated by {r.validator} • {r.date}</p>
              </div>
              <span className={`text-2xl font-bold ${r.score >= 90 ? 'text-green-400' : 'text-yellow-400'}`}>{r.score}%</span>
            </div>

            {/* Bias Tests */}
            <div>
              <h4 className="text-xs font-medium text-slate-500 mb-2">BIAS TESTS</h4>
              <div className="flex gap-2 flex-wrap">
                {r.biasTests.map((b, j) => (
                  <span key={j} className={`px-3 py-1 rounded-lg text-xs font-medium ${
                    b.result === 'pass' ? 'bg-green-500/20 text-green-400' :
                    b.result === 'warn' ? 'bg-yellow-500/20 text-yellow-400' :
                    'bg-red-500/20 text-red-400'
                  }`}>
                    {b.result === 'pass' ? '✓' : b.result === 'warn' ? '⚠' : '✗'} {b.name}
                  </span>
                ))}
              </div>
            </div>

            {/* Methodology */}
            <div className="bg-white/5 rounded-xl p-4">
              <h4 className="text-xs text-slate-500 mb-1">METHODOLOGY</h4>
              <p className="text-sm text-slate-300">{r.methodology}</p>
            </div>

            {/* Mathematical Proof */}
            <div className="bg-white/5 rounded-xl p-4">
              <h4 className="text-xs text-slate-500 mb-1">MATHEMATICAL PROOF</h4>
              <p className="text-sm text-slate-300 font-mono">{r.mathematicalProof}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
