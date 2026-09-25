import { useEffect, useState } from 'react';
import { personalApi } from '../api';
import { TrendingUp, Calculator, ArrowUpDown, DollarSign, BarChart3 } from 'lucide-react';

export default function ProjectionPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [scenario, setScenario] = useState({
    additional_income: 0,
    additional_deductions: 0,
    roth_conversion: 0,
    capital_gain: 0,
    capital_loss: 0,
  });

  useEffect(() => {
    personalApi.projection().then(setData).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const runWhatIf = async () => {
    const result = await personalApi.whatIf(scenario);
    setData(result.scenario);
  };

  if (loading) return <div className="p-8 text-zinc-400">Loading tax projection...</div>;
  if (!data) return <div className="p-8 text-zinc-500">Connect bank accounts to see your tax projection.</div>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Tax Projection</h1>
        <p className="text-zinc-400 mt-1">2026 federal tax estimate based on your financial data</p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-4">
          <p className="text-zinc-400 text-sm">Projected Income</p>
          <p className="text-white text-2xl font-bold">${(data.projected_annual_income / 100).toLocaleString()}</p>
        </div>
        <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-4">
          <p className="text-zinc-400 text-sm">Total Tax</p>
          <p className="text-sky-400 text-2xl font-bold">${(data.total_tax / 100).toLocaleString()}</p>
        </div>
        <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-4">
          <p className="text-zinc-400 text-sm">Effective Rate</p>
          <p className="text-white text-2xl font-bold">{data.effective_rate}%</p>
        </div>
        <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-4">
          <p className="text-zinc-400 text-sm">Marginal Rate</p>
          <p className="text-white text-2xl font-bold">{data.bracket || 'N/A'}</p>
        </div>
      </div>

      {/* Bracket Visualization */}
      {data.bracket_visualization?.length > 0 && (
        <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-6">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <BarChart3 className="w-5 h-5" /> Tax Bracket Breakdown
          </h2>
          <div className="space-y-3">
            {data.bracket_visualization.map((b: any, i: number) => (
              <div key={i} className="flex items-center gap-4">
                <div className="w-16 text-right">
                  <span className="text-zinc-400 text-sm">{b.bracket}</span>
                </div>
                <div className="flex-1 h-6 bg-zinc-800 rounded overflow-hidden">
                  <div className="h-full bg-blue-600/60 rounded flex items-center px-2"
                       style={{ width: `${b.pct_of_income}%`, minWidth: '2rem' }}>
                    <span className="text-white text-xs font-medium">
                      ${(b.income_in_bracket / 100).toLocaleString()}
                    </span>
                  </div>
                </div>
                <div className="w-24 text-right">
                  <span className="text-zinc-400 text-sm">${(b.tax_in_bracket / 100).toLocaleString()}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Deduction Comparison */}
      <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-6">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Calculator className="w-5 h-5" /> Deduction Strategy
        </h2>
        <div className="grid grid-cols-2 gap-4">
          <div className={`rounded-lg p-4 border ${data.use_standard ? 'border-emerald-800 bg-emerald-950/30' : 'border-zinc-800 bg-zinc-800/50'}`}>
            <p className="text-zinc-400 text-sm">Standard Deduction</p>
            <p className="text-white text-xl font-semibold">${(data.standard_deduction / 100).toLocaleString()}</p>
            {data.use_standard && <p className="text-emerald-400 text-xs mt-1">✓ Recommended</p>}
          </div>
          <div className={`rounded-lg p-4 border ${!data.use_standard ? 'border-emerald-800 bg-emerald-950/30' : 'border-zinc-800 bg-zinc-800/50'}`}>
            <p className="text-zinc-400 text-sm">Projected Itemized</p>
            <p className="text-white text-xl font-semibold">${(data.projected_itemized / 100).toLocaleString()}</p>
            {!data.use_standard && <p className="text-emerald-400 text-xs mt-1">✓ Recommended</p>}
          </div>
        </div>
      </div>

      {/* What-If Scenario */}
      <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-6">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <ArrowUpDown className="w-5 h-5" /> What-If Scenario
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div>
            <label className="text-zinc-400 text-sm block mb-1">Additional Income</label>
            <input type="number" value={scenario.additional_income / 100}
                   onChange={(e) => setScenario({ ...scenario, additional_income: Number(e.target.value) * 100 })}
                   className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm"
                   placeholder="$0" />
          </div>
          <div>
            <label className="text-zinc-400 text-sm block mb-1">Additional Deductions</label>
            <input type="number" value={scenario.additional_deductions / 100}
                   onChange={(e) => setScenario({ ...scenario, additional_deductions: Number(e.target.value) * 100 })}
                   className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm"
                   placeholder="$0" />
          </div>
          <div>
            <label className="text-zinc-400 text-sm block mb-1">Roth Conversion</label>
            <input type="number" value={scenario.roth_conversion / 100}
                   onChange={(e) => setScenario({ ...scenario, roth_conversion: Number(e.target.value) * 100 })}
                   className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm"
                   placeholder="$0" />
          </div>
          <div>
            <label className="text-zinc-400 text-sm block mb-1">Capital Gain</label>
            <input type="number" value={scenario.capital_gain / 100}
                   onChange={(e) => setScenario({ ...scenario, capital_gain: Number(e.target.value) * 100 })}
                   className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm"
                   placeholder="$0" />
          </div>
          <div>
            <label className="text-zinc-400 text-sm block mb-1">Capital Loss</label>
            <input type="number" value={scenario.capital_loss / 100}
                   onChange={(e) => setScenario({ ...scenario, capital_loss: Number(e.target.value) * 100 })}
                   className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white text-sm"
                   placeholder="$0" />
          </div>
          <div className="flex items-end">
            <button onClick={runWhatIf}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium">
              Run Scenario
            </button>
          </div>
        </div>
      </div>

      {/* SE Tax */}
      {data.se_tax?.total_se_tax > 0 && (
        <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Self-Employment Tax</h2>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-zinc-400">Social Security</p>
              <p className="text-white font-medium">${(data.se_tax.social_security / 100).toLocaleString()}</p>
            </div>
            <div>
              <p className="text-zinc-400">Medicare</p>
              <p className="text-white font-medium">${(data.se_tax.medicare / 100).toLocaleString()}</p>
            </div>
            <div>
              <p className="text-zinc-400">Deductible Portion</p>
              <p className="text-emerald-400 font-medium">${(data.se_tax.deductible_portion / 100).toLocaleString()}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
