import React, { useState } from 'react';
import { Building2, ChartColumn as BarChart3 } from 'lucide-react';

interface FiscalInput {
 id: string;
 name: string;
 value: number;
 min: number;
 max: number;
 unit: string;
 description: string;
}

interface FiscalOutput {
 id: string;
 name: string;
 value: number;
 unit: string;
 status: 'healthy' | 'warning' | 'critical';
 description: string;
}

const DEFAULT_INPUTS: FiscalInput[] = [
 { id: 'debt', name: 'Total Debt Stock', value: 68.2, min: 30, max: 120, unit: '% GDP', description: 'Total government debt as percentage of GDP' },
 { id: 'tax', name: 'Tax Revenue', value: 18.5, min: 10, max: 35, unit: '% GDP', description: 'Total tax revenue as percentage of GDP' },
 { id: 'spending', name: 'Government Spending', value: 21.3, min: 15, max: 40, unit: '% GDP', description: 'Total government expenditure as percentage of GDP' },
 { id: 'inflation', name: 'Inflation Rate', value: 3.2, min: 0, max: 15, unit: '%', description: 'Annual consumer price inflation' },
 { id: 'gdp_growth', name: 'GDP Growth', value: 2.1, min: -5, max: 10, unit: '%', description: 'Real GDP growth rate' },
 { id: 'interest_rate', name: 'Average Borrowing Cost', value: 4.2, min: 1, max: 12, unit: '%', description: 'Weighted average interest rate on government debt' },
 { id: 'primary_balance', name: 'Primary Balance', value: -1.2, min: -10, max: 10, unit: '% GDP', description: 'Budget balance excluding interest payments' },
 { id: 'reserves', name: 'FX Reserves', value: 4.2, min: 0, max: 24, unit: 'months imports', description: 'Foreign exchange reserves in months of import cover' },
];

const MOCK_OUTPUTS: Record<string, FiscalOutput[]> = {
 default: [
 { id: 'debt_sustainability', name: 'Debt Sustainability', value: 68, unit: '/100', status: 'warning', description: 'Moderate risk. Debt trajectory requires attention.' },
 { id: 'fiscal_space', name: 'Fiscal Space', value: 42, unit: '/100', status: 'warning', description: 'Limited fiscal space for countercyclical policy.' },
 { id: 'financing_risk', name: 'Financing Risk', value: 55, unit: '/100', status: 'warning', description: 'Refinancing risk elevated due to maturity concentration.' },
 { id: 'external_vulnerability', name: 'External Vulnerability', value: 38, unit: '/100', status: 'healthy', description: 'External position manageable with adequate reserves.' },
 { id: 'sovereign_resilience', name: 'Sovereign Resilience Score', value: 62, unit: '/100', status: 'warning', description: 'Moderate resilience. Improvement needed for investment grade.' },
 { id: 'market_access', name: 'Market Access Score', value: 71, unit: '/100', status: 'healthy', description: 'Good market access. Spreads elevated but manageable.' },
 ] };

const STATUS_COLORS: Record<string, string> = {
 healthy: 'text-green-400',
 warning: 'text-yellow-400',
 critical: 'text-red-400' };

const STATUS_BG: Record<string, string> = {
 healthy: 'bg-green-500/20',
 warning: 'bg-yellow-500/20',
 critical: 'bg-red-500/20' };

// Second-order fiscal interaction coefficients
const FISCAL_SECOND_ORDER = {
   // Low liquidity amplifies rate impact
   rate_liq_amplification: 0.35,
   // Spending-tax gap feedback
   spending_tax_gap: 0.25,
   // Debt spiral coefficient
   debt_spiral: 0.15 };

export default function NationalDigitalTwin() {
 const [inputs, setInputs] = useState(DEFAULT_INPUTS);
 const [outputs, setOutputs] = useState(MOCK_OUTPUTS.default);
 const [isSimulating, setIsSimulating] = useState(false);
 const [hasSimulated, setHasSimulated] = useState(false);

 const updateInput = (id: string, value: number) => {
 setInputs(prev => prev.map(i => i.id === id ? { ...i, value } : i));
 setHasSimulated(false);
 };

const runSimulation = () => {
  setIsSimulating(true);
  setTimeout(() => {
   const debt = inputs.find(i => i.id === 'debt')?.value || 68;
   const spending = inputs.find(i => i.id === 'spending')?.value || 21;
   const tax = inputs.find(i => i.id === 'tax')?.value || 18.5;
   const growth = inputs.find(i => i.id === 'gdp_growth')?.value || 2.1;
   const rate = inputs.find(i => i.id === 'interest_rate')?.value || 4.2;
   const primary = inputs.find(i => i.id === 'primary_balance')?.value || -1.2;

   // First-order effects (original)
   const debtSustainability = Math.max(0, Math.min(100, 100 - debt * 0.8 + growth * 5 + primary * 3));
   const fiscalSpace = Math.max(0, Math.min(100, 100 - spending * 2 + tax * 2));
   const financingRisk = Math.max(0, Math.min(100, debt * 0.5 + rate * 5 + (spending - tax) * 3));
   const externalVulnerability = Math.max(0, Math.min(100, 100 - debt * 0.3 - rate * 3 + growth * 4));
   const resilience = (debtSustainability + fiscalSpace + financingRisk + externalVulnerability) / 4;
   const marketAccess = Math.max(0, Math.min(100, 100 - rate * 5 - debt * 0.3 + growth * 3));

   // Second-order fiscal interaction effects
   const liquidityFactor = Math.max(0.2, 1.0 - debt / 150); // debt erodes liquidity
   const rateAmplification = 1.0 + FISCAL_SECOND_ORDER.rate_liq_amplification * (1.0 - liquidityFactor);
   const adjustedRate = rate * rateAmplification;

   const spendingTaxGap = spending - tax;
   const gapAmplification = 1.0 + FISCAL_SECOND_ORDER.spending_tax_gap * Math.abs(spendingTaxGap) / 10;
   const adjustedFiscalSpace = Math.max(0, Math.min(100, 100 - spending * 2 / gapAmplification + tax * 2 / gapAmplification));

   // Debt spiral effect: higher debt -> higher rates -> higher debt
   const debtSpiralFactor = 1.0 + FISCAL_SECOND_ORDER.debt_spiral * debt / 100;
   const spiralingDebtSustainability = Math.max(0, Math.min(100, 100 - debt * 0.8 * debtSpiralFactor + growth * 5 * debtSpiralFactor + primary * 3 * debtSpiralFactor));
   const spiralingFinancingRisk = Math.max(0, Math.min(100, debt * 0.5 * debtSpiralFactor + adjustedRate * 5 + (spending - tax) * 3 * debtSpiralFactor));

   const getStatus = (v: number): 'healthy' | 'warning' | 'critical' => v >= 65 ? 'healthy' : v >= 40 ? 'warning' : 'critical';

   setOutputs([
    { id: 'debt_sustainability', name: 'Debt Sustainability', value: Math.round(spiralingDebtSustainability), unit: '/100', status: getStatus(spiralingDebtSustainability), description: spiralingDebtSustainability >= 65 ? 'Sustainable trajectory.' : spiralingDebtSustainability >= 40 ? 'Moderate risk. Requires fiscal consolidation.' : 'High risk. Urgent action needed.' },
    { id: 'fiscal_space', name: 'Fiscal Space', value: Math.round(adjustedFiscalSpace), unit: '/100', status: getStatus(adjustedFiscalSpace), description: adjustedFiscalSpace >= 65 ? 'Adequate fiscal space for policy response.' : adjustedFiscalSpace >= 40 ? 'Limited fiscal space.' : 'Fiscal space exhausted.' },
    { id: 'financing_risk', name: 'Financing Risk', value: Math.round(100 - spiralingFinancingRisk), unit: '/100', status: getStatus(100 - spiralingFinancingRisk), description: spiralingFinancingRisk <= 35 ? 'Low financing risk.' : spiralingFinancingRisk <= 60 ? 'Elevated financing risk.' : 'Critical financing risk.' },
    { id: 'external_vulnerability', name: 'External Vulnerability', value: Math.round(externalVulnerability), unit: '/100', status: getStatus(externalVulnerability), description: externalVulnerability >= 65 ? 'External position stable.' : externalVulnerability >= 40 ? 'Some external vulnerabilities.' : 'High external vulnerability.' },
    { id: 'sovereign_resilience', name: 'Sovereign Resilience Score', value: Math.round(resilience), unit: '/100', status: getStatus(resilience), description: resilience >= 65 ? 'Resilient sovereign.' : resilience >= 40 ? 'Moderate resilience.' : 'Low resilience. At risk.' },
    { id: 'market_access', name: 'Market Access Score', value: Math.round(marketAccess), unit: '/100', status: getStatus(marketAccess), description: marketAccess >= 65 ? 'Good market access.' : marketAccess >= 40 ? 'Restricted market access.' : 'Market access impaired.' },
   ]);
   setHasSimulated(true);
   setIsSimulating(false);
  }, 2000);
 };

 return (
 <div className="space-y-6 animate-glass-in">
 <div className="flex items-center gap-3">
 <div className="w-10 h-10 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-xl flex items-center justify-center">
 <Building2 className="w-5 h-5" />
 </div>
 <div>
 <h2 className="text-xl font-bold text-white">National Digital Twin</h2>
 <p className="text-sm text-slate-400">Simulate the entire country's fiscal position and debt sustainability</p>
 </div>
 </div>

 <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
 {/* Inputs */}
 <div className="space-y-4">
 <h3 className="text-sm font-medium text-slate-400">FISCAL INPUTS</h3>
 {inputs.map(input => (
 <div key={input.id} className="glass rounded-xl p-4">
 <div className="flex items-center justify-between mb-2">
 <div>
 <h4 className="text-white text-sm font-medium">{input.name}</h4>
 <p className="text-xs text-slate-500">{input.description}</p>
 </div>
 <span className="text-lg font-bold text-white">{input.value} {input.unit}</span>
 </div>
 <input
 type="range"
 min={input.min}
 max={input.max}
 step={input.unit.includes('GDP') ? 0.1 : 0.1}
 value={input.value}
 onChange={(e) => updateInput(input.id, Number(e.target.value))}
 className="w-full"
 />
 <div className="flex justify-between text-xs text-slate-500 mt-1">
 <span>{input.min}{input.unit}</span>
 <span>{input.max}{input.unit}</span>
 </div>
 </div>
 ))}
 <button
 onClick={runSimulation}
 disabled={isSimulating}
 className="w-full py-4 bg-gradient-to-r from-cyan-500 to-blue-600 rounded-2xl text-white font-bold text-lg hover:opacity-90 transition-opacity disabled:opacity-50"
 >
 {isSimulating ? ' <RefreshCw className="w-4 h-4 inline" /> Running National Simulation...' : ' <Building2 className="w-4 h-4 inline" /> Run Digital Twin Simulation'}
 </button>
 </div>

 {/* Outputs */}
 <div className="space-y-4">
 <h3 className="text-sm font-medium text-slate-400">SIMULATION OUTPUTS</h3>
 {isSimulating && (
 <div className="glass rounded-2xl p-8 text-center">
 <div className="animate-spin w-10 h-10 border-2 border-cyan-400 border-t-transparent rounded-full mx-auto mb-4" />
 <p className="text-white font-medium">Simulating national fiscal dynamics...</p>
 </div>
 )}
 {!isSimulating && outputs.map(output => (
 <div key={output.id} className="glass rounded-xl p-4">
 <div className="flex items-center justify-between mb-2">
 <h4 className="text-white font-medium">{output.name}</h4>
 <div className="flex items-center gap-2">
 <span className={`text-2xl font-bold ${STATUS_COLORS[output.status]}`}>{output.value}</span>
 <span className="text-xs text-slate-500">{output.unit}</span>
 </div>
 </div>
 <div className="w-full bg-white/5 rounded-full h-2 mb-2">
 <div
 className={`h-2 rounded-full ${STATUS_BG[output.status]}`}
 style={{ width: `${output.value}%` }}
 />
 </div>
 <p className="text-xs text-slate-400">{output.description}</p>
 </div>
 ))}
 {!isSimulating && hasSimulated && (
 <div className="glass rounded-2xl p-4 border-l-2 border-cyan-500">
 <h4 className="text-sm font-medium text-cyan-400 mb-2"> <BarChart3 className="w-4 h-4 inline" /> Summary</h4>
 <p className="text-sm text-slate-300">
 The national digital twin indicates a <strong className={outputs[4]?.status === 'healthy' ? 'text-green-400' : outputs[4]?.status === 'warning' ? 'text-yellow-400' : 'text-red-400'}>{outputs[4]?.status}</strong> sovereign resilience position.
 With current parameters, debt-to-GDP is {inputs.find(i => i.id === 'debt')?.value}% and primary balance is {inputs.find(i => i.id === 'primary_balance')?.value}% GDP.
 {outputs[4]?.value < 50 ? ' Urgent fiscal consolidation recommended.' : ' Maintain current policy trajectory.'}
 </p>
 </div>
 )}
 </div>
 </div>
 </div>
 );
}
