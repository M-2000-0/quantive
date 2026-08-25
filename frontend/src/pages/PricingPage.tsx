import { useState } from 'react';

interface Calculation {
  baseline: string;
  optimized: string;
  savings: string;
  savingsPct: string;
  fee: string;
  eligible: boolean;
  reason: string;
}

export default function PricingPage() {
  const [calculation, setCalculation] = useState<Calculation | null>(null);
  const [loading, setLoading] = useState(false);

  const calculateFee = async (baseline: number, optimized: number, portfolioNotional: number) => {
    setLoading(true);
    try {
      const res = await fetch('/api/pay-for-performance/calculate-fee', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify({
          baseline_cost: baseline,
          optimized_cost: optimized,
          portfolio_notional: portfolioNotional,
          fee_percentage: 10,
          min_savings_threshold: 2,
          max_fee_cap_percentage: 0.5,
        }),
      });
      const data = await res.json();
      setCalculation(data.calculation);
    } catch (e) {
      console.error('Calculation failed', e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass p-6">
      <h2 className="text-lg font-semibold">Quantive Pricing</h2>
      <p className="text-sm text-slate-500 mb-6">
        Pay-for-performance pricing: 10% of financing cost savings, minimum 2% savings threshold, capped at 0.5% of portfolio notional.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-2">Baseline Annual Financing Cost</label>
          <input type="number" id="baseline" placeholder="e.g., 6420000000" className="w-full border rounded px-3 py-2" />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-2">Optimized Annual Financing Cost</label>
          <input type="number" id="optimized" placeholder="e.g., 6180000000" className="w-full border rounded px-3 py-2" />
        </div>
      </div>
      <div className="mb-4">
        <label className="block text-sm font-medium text-slate-700 mb-2">Portfolio Notional (USD)</label>
        <input type="number" id="portfolioNotional" placeholder="e.g., 50000000000" className="w-full border rounded px-3 py-2" />
      </div>
      <div className="flex gap-3">
        <button
          onClick={() => {
            const b = Number((document.getElementById('baseline') as HTMLInputElement)?.value) || 0;
            const o = Number((document.getElementById('optimized') as HTMLInputElement)?.value) || 0;
            const p = Number((document.getElementById('portfolioNotional') as HTMLInputElement)?.value) || 0;
            void calculateFee(b, o, p);
          }}
          disabled={loading}
          className="glass-btn-primary"
        >
          {loading ? 'Calculating...' : 'Calculate Fee'}
        </button>
      </div>
      {calculation && (
        <div className={`mt-6 p-4 rounded border ${calculation.eligible ? 'bg-emerald-50' : 'bg-red-50'}`}>
          <h3 className="font-medium text-slate-900 mb-2">{calculation.eligible ? 'Eligible for Success Fee' : 'Not Eligible'}</h3>
          <p className="text-sm text-slate-500 mb-2">Savings: <strong>{calculation.savingsPct}%</strong></p>
          <p className="text-xs text-slate-500">{calculation.reason}</p>
        </div>
      )}
    </div>
  );
}
