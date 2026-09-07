import React, { useState } from 'react';
import { CircleCheck as CheckCircle, Eye, Play, RefreshCw, Search, TriangleAlert as AlertTriangle, TriangleAlert as Warning } from 'lucide-react';

interface SimulationScenario {
 id: string;
 name: string;
 description: string;
 icon: string;
 color: string;
 presets: { label: string; params: Record<string, number> }[];
}

interface SimulationResult {
 metric: string;
 baseline: number;
 simulated: number;
 change: number;
 unit: string;
 impact: 'positive' | 'negative' | 'neutral';
}

const SCENARIOS: SimulationScenario[] = [
 {
 id: 'rates',
 name: 'Interest Rate Shock',
 description: 'Simulate parallel shifts in the yield curve',
 icon: 'TrendingUp',
 color: 'blue',
 presets: [
 { label: 'Rates +100bps', params: { rateShift: 100 } },
 { label: 'Rates +300bps', params: { rateShift: 300 } },
 { label: 'Rates -100bps', params: { rateShift: -100 } },
 { label: 'Inverted Curve', params: { rateShift: -50, shortEnd: 150 } },
 ]
 },
 {
 id: 'fx',
 name: 'Currency Shock',
 description: 'Simulate major currency movements',
 icon: 'Contrast',
 color: 'purple',
 presets: [
 { label: 'USD -10%', params: { usdShift: -10 } },
 { label: 'EUR +15%', params: { eurShift: 15 } },
 { label: 'JPY -20%', params: { jpyShift: -20 } },
 { label: 'Broad Dollar Rally', params: { usdShift: 8, eurShift: -5, jpyShift: -12 } },
 ]
 },
 {
 id: 'credit',
 name: 'Credit Event',
 description: 'Simulate credit spread widening or tightening',
 icon: 'AlertTriangle',
 color: 'red',
 presets: [
 { label: 'Spreads +200bps', params: { spreadWidening: 200 } },
 { label: 'Spread Compression', params: { spreadWidening: -100 } },
 { label: 'Default Event', params: { spreadWidening: 500, defaultRate: 2 } },
 ] },
 {
 id: 'macro',
 name: 'Macro Scenario',
 description: 'Simulate GDP, inflation, and recession scenarios',
 icon: 'Globe',
 color: 'green',
 presets: [
 { label: 'Recession', params: { gdpGrowth: -2, inflation: 1 } },
 { label: 'Stagflation', params: { gdpGrowth: 0.5, inflation: 6 } },
 { label: 'Goldilocks', params: { gdpGrowth: 3, inflation: 2 } },
 { label: 'Soft Landing', params: { gdpGrowth: 1.5, inflation: 2.5 } },
 ] },
 // New sector-specific scenario types per the Quantive vision doc
 {
 id: 'energy',
 name: 'Energy Stress',
 description: 'Simulate energy price shocks and sector-wide impact',
 icon: 'Sun',
 color: 'amber',
 presets: [
 { label: 'Oil +40%', params: { energyPriceShift: 40 } },
 { label: 'Oil -30%', params: { energyPriceShift: -30 } },
 { label: 'Gas Spike', params: { gasShift: 50 } },
 { label: 'Renewable Transition', params: { renewableShare: 35 } },
 ] },
 {
 id: 'infrastructure',
 name: 'Infrastructure Stress',
 description: 'Simulate infrastructure investment and demand shocks',
 icon: 'HardHat',
 color: 'cyan',
 presets: [
 { label: 'Demand +20%', params: { infraDemandShift: 20 } },
 { label: 'Supply Chain Disruption', params: { supplyShift: -25 } },
 { label: 'Investment Surge', params: { infraCapex: 15 } },
 { label: 'Aging Assets', params: { assetAgeShift: 40 } },
 ] },
 {
 id: 'water',
 name: 'Water Stress',
 description: 'Simulate water scarcity and resource allocation shocks',
 icon: 'Droplet',
 color: 'teal',
 presets: [
 { label: 'Scarcity +30%', params: { waterScarcity: 30 } },
 { label: 'Drought Conditions', params: { droughtShift: 40 } },
 { label: 'Demand Increase', params: { waterDemand: 35 } },
 { label: 'Conservation Policy', params: { conservationRate: 20 } },
 ] },
 {
 id: 'housing',
 name: 'Housing Stress',
 description: 'Simulate housing market corrections and mortgage shocks',
 icon: 'Home',
 color: 'rose',
 presets: [
 { label: 'Price Correction -20%', params: { homePriceShift: -20 } },
 { label: 'Mortgage Rate +200bps', params: { mortgageRateShift: 200 } },
 { label: 'Construction Slowdown', params: { constructionShift: -30 } },
 { label: 'Rental Demand Surge', params: { rentalDemand: 25 } },
 ] },
 {
 id: 'employment',
 name: 'Employment Stress',
 description: 'Simulate labor market fluctuations and employment shocks',
 icon: 'Layout',
 color: 'sky',
 presets: [
 { label: 'Unemployment +5%', params: { unemploymentShift: 5 } },
 { label: 'Wage Pressure', params: { wageShift: 10 } },
 { label: 'Labor Shortage', params: { laborShift: -15 } },
 { label: 'Participation Decline', params: { participation: -8 } },
 ] },
];

const BASELINE_METRICS = [
 { metric: 'Portfolio Value', baseline: 1000, unit: '$M', impact: 'neutral' as const },
 { metric: 'Annual Cost', baseline: 42.5, unit: '$M', impact: 'negative' as const },
 { metric: 'Duration', baseline: 5.1, unit: 'years', impact: 'neutral' as const },
 { metric: 'Yield', baseline: 4.8, unit: '%', impact: 'positive' as const },
 { metric: 'VaR (95%)', baseline: 3.2, unit: '%', impact: 'negative' as const },
 { metric: 'Liquidity Ratio', baseline: 22, unit: '%', impact: 'positive' as const },
 { metric: 'Green Bond %', baseline: 15, unit: '%', impact: 'positive' as const },
 { metric: 'Credit Quality', baseline: 85, unit: 'score', impact: 'positive' as const },
 { metric: 'Energy Exposure', baseline: 0, unit: '$M', impact: 'neutral' as const },
 { metric: 'Infrastructure Exposure', baseline: 0, unit: '$M', impact: 'neutral' as const },
 { metric: 'Water Exposure', baseline: 0, unit: '$M', impact: 'neutral' as const },
 { metric: 'Housing Exposure', baseline: 0, unit: '$M', impact: 'neutral' as const },
 { metric: 'Employment Exposure', baseline: 0, unit: '$M', impact: 'neutral' as const },
];

export default function DigitalTwin() {
 const [selectedScenario, setSelectedScenario] = useState(SCENARIOS[0]);
 const [params, setParams] = useState<Record<string, number>>({ rateShift: 0, usdShift: 0, eurShift: 0, jpyShift: 0, spreadWidening: 0, gdpGrowth: 2, inflation: 2 });
 const [isSimulating, setIsSimulating] = useState(false);
 const [results, setResults] = useState<SimulationResult[] | null>(null);

const NONLINEAR_COEFFS = {
    rate_liq_amplification: 0.4,     // low liquidity amplifies rate shock
    fx_rate_compounding: 0.25,       // FX moves compound rate exposure
    inf_rate_feedback: 0.30,         // inflation * real rate feedback loop
    sector_nonlinear: {
        energy: 0.35,
        infrastructure: 0.25,
        water: 0.20,
        housing: 0.30,
        employment: 0.20 } };

const SECTOR_MULTIPLIERS: Record<string, Record<string, number> & { sector_nonlinear: number }> = {
    energy: { 'energy': 1.4, 'high_inflation': 1.2, 'fx_shock': 1.15, sector_nonlinear: 1.15 },
    infrastructure: { 'infrastructure': 1.3, 'high_inflation': 1.12, 'fx_shock': 1.08, sector_nonlinear: 1.1 },
    water: { 'water': 1.25, 'high_inflation': 1.10, 'fx_shock': 1.05, sector_nonlinear: 1.08 },
    housing: { 'housing': 1.35, 'high_inflation': 1.15, 'fx_shock': 1.10, sector_nonlinear: 1.12 },
    employment: { 'employment': 1.2, 'high_inflation': 1.08, 'fx_shock': 1.06, sector_nonlinear: 1.05 } };

const runSimulation = () => {
 setIsSimulating(true);
 setTimeout(() => {
  const simResults: SimulationResult[] = BASELINE_METRICS.map(m => {
   let simulated = m.baseline;

   // --- Nonlinear rate effects with second-order interactions ---
   const rateShift = params.rateShift || 0;
   const liquidityFactor = 1.0 - (params.liquidityFactor || 0) / 100;
   const liquidityAmplification = 1.0 + NONLINEAR_COEFFS.rate_liq_amplification * Math.max(0, 1.0 - liquidityFactor);

   // --- FX effects with compounding ---
   const usdShift = params.usdShift || 0;
   const eurShift = params.eurShift || 0;
   const jpyShift = params.jpyShift || 0;
   const fxCompound = 1.0 + NONLINEAR_COEFFS.fx_rate_compounding * Math.abs(rateShift) / 100;

   const fxImpact = (usdShift || 0) * 0.3 * fxCompound + (eurShift || 0) * 0.3 * fxCompound + (jpyShift || 0) * 0.2 * fxCompound;

   // --- Second-order sector effects ---
   const sectorShocks: Record<string, number> = {};
   let totalSectorShift = 0;

   for (const [sector, multiplier] of Object.entries(SECTOR_MULTIPLIERS)) {
    const sectorParam = params[sector] || 0;
    if (sectorParam !== 0) {
     const nonlinearImpact = sectorParam * multiplier.sector_nonlinear;
     sectorShocks[sector] = sectorParam;
     totalSectorShift += nonlinearImpact;
    }
   }

   // --- Apply rate effects with second-order amplification ---
   if (rateShift) {
    const amplifiedRateShift = rateShift * liquidityAmplification;
    if (m.metric === 'Portfolio Value') simulated = m.baseline * (1 - amplifiedRateShift * 0.00005);
    if (m.metric === 'Duration') simulated = m.baseline * (1 + amplifiedRateShift * 0.0003);
    if (m.metric === 'Annual Cost') simulated = m.baseline * (1 + amplifiedRateShift * 0.001);
    if (m.metric === 'Yield') simulated = m.baseline + amplifiedRateShift * 0.01;
    if (m.metric === 'VaR (95%)') simulated = m.baseline + amplifiedRateShift * 0.008;
   }

   // --- Apply FX effects with compounding ---
   if (usdShift || eurShift || jpyShift) {
    if (m.metric === 'Portfolio Value') simulated = m.baseline * (1 + fxImpact * 0.001);
    if (m.metric === 'Yield') simulated = m.baseline + fxImpact * 0.01;
    if (m.metric === 'VaR (95%)') simulated = m.baseline + fxImpact * 0.005;
   }

   // --- Apply sector-specific nonlinear effects ---
   for (const [sector, multiplier] of Object.entries(SECTOR_MULTIPLIERS)) {
    const sectorParam = params[sector] || 0;
    if (sectorParam !== 0 && m.metric === `${sector} Exposure`) {
     // Nonlinear: quadratic impact for stress scenarios
     const baseChange = sectorParam * 0.01;
     const nonlinearFactor = 1.0 + multiplier.sector_nonlinear * Math.abs(sectorParam) / 100;
     simulated = m.baseline * (1 + baseChange * nonlinearFactor);
    }
   }

   // --- Apply macro effects with feedback ---
   if (params.gdpGrowth !== 2 || params.inflation !== 2) {
    const macroStress = (2 - params.gdpGrowth) * 0.4 + (params.inflation - 2) * 0.6;
    if (m.metric === 'Portfolio Value') simulated = m.baseline * (1 - macroStress * 0.01);
    if (m.metric === 'Yield') simulated = m.baseline + macroStress * 0.2;
    if (m.metric === 'VaR (95%)') simulated = m.baseline + macroStress * 0.15;
   }

   // --- Apply sector stress effects on exposure metrics ---
   const sectorShiftMap: Record<string, number> = {
    energy: params.energyPriceShift || 0,
    infrastructure: params.infraDemandShift || 0,
    water: params.waterScarcity || 0,
    housing: params.homePriceShift || 0,
    employment: params.unemploymentShift || 0 };

   for (const [sector, shift] of Object.entries(sectorShiftMap)) {
    if (shift !== 0 && m.metric === `${sector} Exposure`) {
     const mult = SECTOR_MULTIPLIERS[sector];
     const baseChange = shift * 0.01;
     const nonlinearFactor = 1.0 + mult.sector_nonlinear * Math.abs(shift) / 100;
     simulated = m.baseline * (1 + baseChange * nonlinearFactor);
     // Also propagate to related metrics
     if (m.metric === 'Portfolio Value') {
      simulated = m.baseline * (1 + baseChange * mult.sector_nonlinear * 0.005);
     }
    }
   }

   // --- Apply credit effects ---
   if (params.spreadWidening) {
    if (m.metric === 'Portfolio Value') simulated = m.baseline * (1 - params.spreadWidening * 0.00008);
    if (m.metric === 'VaR (95%)') simulated = m.baseline + params.spreadWidening * 0.005;
    if (m.metric === 'Credit Quality') simulated = Math.max(0, m.baseline - params.spreadWidening * 0.1);
   }

   const change = ((simulated - m.baseline) / m.baseline) * 100;

   return {
    ...m,
    simulated: Number(simulated.toFixed(2)),
    change: Number(change.toFixed(2)),
    impact: change > 0.5 ? 'positive' : change < -0.5 ? 'negative' : 'neutral'
   };
  });

  setResults(simResults);
  setIsSimulating(false);
 }, 1500);
};

 const applyPreset = (preset: Record<string, number>) => {
 setParams(prev => ({ ...prev, ...preset }));
 setResults(null);
 };

 return (
 <div className="space-y-6 animate-glass-in">
 <div className="flex items-center gap-3">
 <div className="w-10 h-10 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-xl flex items-center justify-center">
 <Eye className="w-5 h-5" />
 </div>
 <div>
 <h2 className="text-xl font-bold text-white">Digital Twin</h2>
 <p className="text-sm text-slate-400">Live simulation of your portfolio under stress scenarios</p>
 </div>
 </div>

 <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
 {/* Scenario Selection */}
 <div className="space-y-4">
 <h3 className="text-sm font-medium text-slate-400">Select Scenario</h3>
 <div className="space-y-2">
 {SCENARIOS.map(s => (
 <button
 key={s.id}
 onClick={() => { setSelectedScenario(s); setResults(null); }}
 className={`w-full text-left p-3 rounded-xl border transition-all ${
 selectedScenario.id === s.id
 ? `bg-${s.color}-500/10 border-${s.color}-500/30 text-white`
 : 'bg-white/5 border-white/10 text-slate-400 hover:bg-white/10'
 }`}
 >
 <div className="flex items-center gap-2">
 <span>{s.icon}</span>
 <span className="font-medium text-sm">{s.name}</span>
 </div>
 <p className="text-xs mt-1 opacity-70">{s.description}</p>
 </button>
 ))}
 </div>

 {/* Presets */}
 <div>
 <h3 className="text-sm font-medium text-slate-400 mb-2">Quick Presets</h3>
 <div className="flex flex-wrap gap-2">
 {selectedScenario.presets.map((p, i) => (
 <button
 key={i}
 onClick={() => applyPreset(p.params)}
 className="px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-xs text-slate-300 hover:bg-white/10 transition-colors"
 >
 {p.label}
 </button>
 ))}
 </div>
 </div>
 </div>

 {/* Parameter Controls */}
 <div className="space-y-4">
 <h3 className="text-sm font-medium text-slate-400">Parameters</h3>
 <div className="glass rounded-xl p-4 space-y-4">
 {selectedScenario.id === 'rates' && (
 <>
 <div>
 <label className="text-xs text-slate-400 block mb-1">Rate Shift (bps)</label>
 <input
 type="range"
 min={-200}
 max={500}
 value={params.rateShift || 0}
 onChange={(e) => setParams(p => ({ ...p, rateShift: Number(e.target.value) }))}
 className="w-full"
 />
 <span className="text-sm text-white">{params.rateShift || 0} bps</span>
 </div>
 </>
 )}
 {selectedScenario.id === 'fx' && (
 <>
 <div>
 <label className="text-xs text-slate-400 block mb-1">USD Shift (%)</label>
 <input
 type="range"
 min={-30}
 max={30}
 value={params.usdShift || 0}
 onChange={(e) => setParams(p => ({ ...p, usdShift: Number(e.target.value) }))}
 className="w-full"
 />
 <span className="text-sm text-white">{params.usdShift || 0}%</span>
 </div>
 <div>
 <label className="text-xs text-slate-400 block mb-1">EUR Shift (%)</label>
 <input
 type="range"
 min={-30}
 max={30}
 value={params.eurShift || 0}
 onChange={(e) => setParams(p => ({ ...p, eurShift: Number(e.target.value) }))}
 className="w-full"
 />
 <span className="text-sm text-white">{params.eurShift || 0}%</span>
 </div>
 <div>
 <label className="text-xs text-slate-400 block mb-1">JPY Shift (%)</label>
 <input
 type="range"
 min={-30}
 max={30}
 value={params.jpyShift || 0}
 onChange={(e) => setParams(p => ({ ...p, jpyShift: Number(e.target.value) }))}
 className="w-full"
 />
 <span className="text-sm text-white">{params.jpyShift || 0}%</span>
 </div>
 </>
 )}
 {selectedScenario.id === 'credit' && (
 <div>
 <label className="text-xs text-slate-400 block mb-1">Spread Widening (bps)</label>
 <input
 type="range"
 min={-200}
 max={600}
 value={params.spreadWidening || 0}
 onChange={(e) => setParams(p => ({ ...p, spreadWidening: Number(e.target.value) }))}
 className="w-full"
 />
 <span className="text-sm text-white">{params.spreadWidening || 0} bps</span>
 </div>
 )}
{selectedScenario.id === 'macro' && (
  <>
  <div>
  <label className="text-xs text-slate-400 block mb-1">GDP Growth (%)</label>
  <input
   type="range"
   min={-5}
   max={8}
   step={0.5}
   value={params.gdpGrowth}
   onChange={(e) => setParams(p => ({ ...p, gdpGrowth: Number(e.target.value) }))}
   className="w-full"
  />
  <span className="text-sm text-white">{params.gdpGrowth}%</span>
  </div>
  <div>
  <label className="text-xs text-slate-400 block mb-1">Inflation (%)</label>
  <input
   type="range"
   min={0}
   max={10}
   step={0.5}
   value={params.inflation}
   onChange={(e) => setParams(p => ({ ...p, inflation: Number(e.target.value) }))}
   className="w-full"
  />
  <span className="text-sm text-white">{params.inflation}%</span>
  </div>
  </>
  )}
  {selectedScenario.id === 'energy' && (
  <>
  <div>
  <label className="text-xs text-slate-400 block mb-1">Energy Price Shift (%)</label>
  <input
   type="range"
   min={-50}
   max={100}
   value={params.energyPriceShift || 0}
   onChange={(e) => setParams(p => ({ ...p, energyPriceShift: Number(e.target.value) }))}
   className="w-full"
  />
  <span className="text-sm text-white">{params.energyPriceShift || 0}%</span>
  </div>
  <div>
  <label className="text-xs text-slate-400 block mb-1">Gas Shift (%)</label>
  <input
   type="range"
   min={-30}
   max={50}
   value={params.gasShift || 0}
   onChange={(e) => setParams(p => ({ ...p, gasShift: Number(e.target.value) }))}
   className="w-full"
  />
  <span className="text-sm text-white">{params.gasShift || 0}%</span>
  </div>
  <div>
  <label className="text-xs text-slate-400 block mb-1">Renewable Share (%)</label>
  <input
   type="range"
   min={0}
   max={100}
   step={5}
   value={params.renewableShare || 0}
   onChange={(e) => setParams(p => ({ ...p, renewableShare: Number(e.target.value) }))}
   className="w-full"
  />
  <span className="text-sm text-white">{params.renewableShare || 0}%</span>
  </div>
  </>
  )}
  {selectedScenario.id === 'infrastructure' && (
  <>
  <div>
  <label className="text-xs text-slate-400 block mb-1">Infrastructure Demand Shift (%)</label>
  <input
   type="range"
   min={-30}
   max={50}
   value={params.infraDemandShift || 0}
   onChange={(e) => setParams(p => ({ ...p, infraDemandShift: Number(e.target.value) }))}
   className="w-full"
  />
  <span className="text-sm text-white">{params.infraDemandShift || 0}%</span>
  </div>
  <div>
  <label className="text-xs text-slate-400 block mb-1">Supply Chain Shift (%)</label>
  <input
   type="range"
   min={-50}
   max={25}
   value={params.supplyShift || 0}
   onChange={(e) => setParams(p => ({ ...p, supplyShift: Number(e.target.value) }))}
   className="w-full"
  />
  <span className="text-sm text-white">{params.supplyShift || 0}%</span>
  </div>
  <div>
  <label className="text-xs text-slate-400 block mb-1">Capex Shift (%)</label>
  <input
   type="range"
   min={-20}
   max={40}
   step={5}
   value={params.infraCapex || 0}
   onChange={(e) => setParams(p => ({ ...p, infraCapex: Number(e.target.value) }))}
   className="w-full"
  />
  <span className="text-sm text-white">{params.infraCapex || 0}%</span>
  </div>
  <div>
  <label className="text-xs text-slate-400 block mb-1">Asset Age Shift (%</label>
  <input
   type="range"
   min={-30}
   max={50}
   value={params.assetAgeShift || 0}
   onChange={(e) => setParams(p => ({ ...p, assetAgeShift: Number(e.target.value) }))}
   className="w-full"
  />
  <span className="text-sm text-white">{params.assetAgeShift || 0}%</span>
  </div>
  </>
  )}
  {selectedScenario.id === 'water' && (
  <>
  <div>
  <label className="text-xs text-slate-400 block mb-1">Water Scarcity (%)</label>
  <input
   type="range"
   min={0}
   max={60}
   value={params.waterScarcity || 0}
   onChange={(e) => setParams(p => ({ ...p, waterScarcity: Number(e.target.value) }))}
   className="w-full"
  />
  <span className="text-sm text-white">{params.waterScarcity || 0}%</span>
  </div>
  <div>
  <label className="text-xs text-slate-400 block mb-1">Drought Shift (%)</label>
  <input
   type="range"
   min={-20}
   max={40}
   value={params.droughtShift || 0}
   onChange={(e) => setParams(p => ({ ...p, droughtShift: Number(e.target.value) }))}
   className="w-full"
  />
  <span className="text-sm text-white">{params.droughtShift || 0}%</span>
  </div>
  <div>
  <label className="text-xs text-slate-400 block mb-1">Water Demand Shift (%)</label>
  <input
   type="range"
   min={-20}
   max={50}
   value={params.waterDemand || 0}
   onChange={(e) => setParams(p => ({ ...p, waterDemand: Number(e.target.value) }))}
   className="w-full"
  />
  <span className="text-sm text-white">{params.waterDemand || 0}%</span>
  </div>
  <div>
  <label className="text-xs text-slate-400 block mb-1">Conservation Rate (%)</label>
  <input
   type="range"
   min={0}
   max={40}
   step={5}
   value={params.conservationRate || 0}
   onChange={(e) => setParams(p => ({ ...p, conservationRate: Number(e.target.value) }))}
   className="w-full"
  />
  <span className="text-sm text-white">{params.conservationRate || 0}%</span>
  </div>
  </>
  )}
  {selectedScenario.id === 'housing' && (
  <>
  <div>
  <label className="text-xs text-slate-400 block mb-1">Home Price Shift (%)</label>
  <input
   type="range"
   min={-40}
   max={20}
   value={params.homePriceShift || 0}
   onChange={(e) => setParams(p => ({ ...p, homePriceShift: Number(e.target.value) }))}
   className="w-full"
  />
  <span className="text-sm text-white">{params.homePriceShift || 0}%</span>
  </div>
  <div>
  <label className="text-xs text-slate-400 block mb-1">Mortgage Rate Shift (bps)</label>
  <input
   type="range"
   min={-200}
   max={500}
   value={params.mortgageRateShift || 0}
   onChange={(e) => setParams(p => ({ ...p, mortgageRateShift: Number(e.target.value) }))}
   className="w-full"
  />
  <span className="text-sm text-white">{params.mortgageRateShift || 0} bps</span>
  </div>
  <div>
  <label className="text-xs text-slate-400 block mb-1">Construction Shift (%)</label>
  <input
   type="range"
   min={-40}
   max={20}
   value={params.constructionShift || 0}
   onChange={(e) => setParams(p => ({ ...p, constructionShift: Number(e.target.value) }))}
   className="w-full"
  />
  <span className="text-sm text-white">{params.constructionShift || 0}%</span>
  </div>
  <div>
  <label className="text-xs text-slate-400 block mb-1">Rental Demand Shift (%)</label>
  <input
   type="range"
   min={-20}
   max={40}
   value={params.rentalDemand || 0}
   onChange={(e) => setParams(p => ({ ...p, rentalDemand: Number(e.target.value) }))}
   className="w-full"
  />
   <span className="text-sm text-white">{params.rentalDemand || 0}%</span>
   </div>
   </>
   )}
   {selectedScenario.id === 'employment' && (
  <>
  <div>
  <label className="text-xs text-slate-400 block mb-1">Unemployment Shift (%)</label>
  <input
   type="range"
   min={-10}
   max={15}
   value={params.unemploymentShift || 0}
   onChange={(e) => setParams(p => ({ ...p, unemploymentShift: Number(e.target.value) }))}
   className="w-full"
  />
  <span className="text-sm text-white">{params.unemploymentShift || 0}%</span>
  </div>
  <div>
  <label className="text-xs text-slate-400 block mb-1">Wage Pressure Shift (%)</label>
  <input
   type="range"
   min={-20}
   max={30}
   value={params.wageShift || 0}
   onChange={(e) => setParams(p => ({ ...p, wageShift: Number(e.target.value) }))}
   className="w-full"
  />
  <span className="text-sm text-white">{params.wageShift || 0}%</span>
  </div>
  <div>
  <label className="text-xs text-slate-400 block mb-1">Labor Shortage Shift (%)</label>
  <input
   type="range"
   min={-30}
   max={10}
   value={params.laborShift || 0}
   onChange={(e) => setParams(p => ({ ...p, laborShift: Number(e.target.value) }))}
   className="w-full"
  />
  <span className="text-sm text-white">{params.laborShift || 0}%</span>
  </div>
  <div>
  <label className="text-xs text-slate-400 block mb-1">Participation Rate Shift (%)</label>
  <input
   type="range"
   min={-20}
   max={5}
   value={params.participation || 0}
   onChange={(e) => setParams(p => ({ ...p, participation: Number(e.target.value) }))}
   className="w-full"
  />
   <span className="text-sm text-white">{params.participation || 0}%</span>
   </div>
   </>
   )}

 <button
 onClick={runSimulation}
 disabled={isSimulating}
 className="w-full py-3 bg-gradient-to-r from-cyan-500 to-blue-600 rounded-xl text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
 >
 {isSimulating ? <> <RefreshCw className="w-4 h-4 inline" /> Simulating...</> : <> <Play className="w-4 h-4 inline" /> Run Simulation</>}
 </button>
 </div>
 </div>

 {/* Results */}
 <div className="space-y-4">
 <h3 className="text-sm font-medium text-slate-400">
 {results ? 'Simulation Results' : 'Results will appear here'}
 </h3>
 {isSimulating && (
 <div className="glass rounded-xl p-8 text-center">
 <div className="animate-spin w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full mx-auto mb-3" />
 <p className="text-slate-400 text-sm">Running {selectedScenario.name} simulation...</p>
 </div>
 )}
{results && !isSimulating && (
  <div className="space-y-2">
  {results.map((r, i) => (
   <div key={i} className="glass rounded-xl p-3 flex items-center justify-between">
    <span className="text-sm text-slate-300">{r.metric}</span>
    <div className="flex items-center gap-3">
     <span className="text-xs text-slate-500">{r.baseline}{r.unit}</span>
     <span className="text-xs text-slate-500">→</span>
     <span className={`text-sm font-medium ${
      r.impact === 'positive' ? 'text-green-400' :
      r.impact === 'negative' ? 'text-red-400' : 'text-slate-400'
     }`}>
      {r.simulated}{r.unit}
     </span>
     <span className={`text-xs px-1.5 py-0.5 rounded ${
      r.change > 0 ? 'bg-green-500/20 text-green-400' :
      r.change < 0 ? 'bg-red-500/20 text-red-400' :
      'bg-slate-500/20 text-slate-400'
     }`}>
      {r.change > 0 ? '+' : ''}{r.change}%
     </span>
    </div>
   </div>
  ))}
  {/* Sector stress impact summary */}
  {results.some(r => r.metric.startsWith('Energy') || r.metric.startsWith('Infrastructure') || r.metric.startsWith('Water') || r.metric.startsWith('Housing') || r.metric.startsWith('Employment')) && (
   <div className="glass rounded-xl p-4 mt-4 border-l-2 border-cyan-500">
    <h4 className="text-sm font-medium text-cyan-400 mb-2"> <Warning className="w-4 h-4 inline" /> Sector Stress Impact</h4>
    <div className="space-y-1 text-xs text-slate-400">
     {['energy', 'infrastructure', 'water', 'housing', 'employment'].map(s => {
      const sectorResult = results.find(r => r.metric === `${s} Exposure`);
      const shiftKey = `${s}PriceShift` || `${s}DemandShift` || `${s}Shift` || 0;
      const shift = params[shiftKey] || 0;
      if (shift !== 0 && sectorResult) {
       return (
        <p key={s} className="flex items-center gap-2">
         <span className={`w-2 h-2 rounded-full ${
          sectorResult.change > 0 ? 'bg-green-400' : 'bg-red-400'
         }`} />
         <span className="text-slate-300">{s}: {sectorResult.change > 0 ? '+' : ''}{sectorResult.change.toFixed(1)}%</span>
        </p>
       );
      }
      return null;
     })}
    </div>
   </div>
  )}
 {/* Risk Assessment */}
 <div className="glass rounded-xl p-4 mt-4 border-l-2 border-cyan-500">
 <h4 className="text-sm font-medium text-cyan-400 mb-2"> <Search className="w-4 h-4 inline" /> Risk Assessment</h4>
 <div className="space-y-1 text-xs text-slate-400">
 {results.find(r => r.metric === 'VaR (95%)' && r.change > 20) && (
 <p className="text-red-400"> <AlertTriangle className="w-4 h-4 inline" /> VaR increases significantly — consider hedging</p>
 )}
 {results.find(r => r.metric === 'Liquidity Ratio' && r.simulated < 15) && (
 <p className="text-yellow-400"> <AlertTriangle className="w-4 h-4 inline" /> Liquidity ratio drops below 15% buffer</p>
 )}
 {results.find(r => r.metric === 'Credit Quality' && r.simulated < 60) && (
 <p className="text-red-400"> <AlertTriangle className="w-4 h-4 inline" /> Credit quality falls below investment grade threshold</p>
 )}
 {results.every(r => Math.abs(r.change) < 5) && (
 <p className="text-green-400"> <CheckCircle className="w-4 h-4 inline" /> Portfolio is resilient to this scenario</p>
 )}
 </div>
 </div>
</div>
 )}
 </div>
 </div>
 </div>
 );
}
