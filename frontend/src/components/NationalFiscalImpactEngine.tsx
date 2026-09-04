import React, { useState } from 'react';
import { Building2, ChartColumn as BarChart3, TriangleAlert as AlertTriangle } from 'lucide-react';

interface FiscalProjection {
 year: number;
 debtGDP: number;
 deficitGDP: number;
 debtService: number;
 liquidity: number;
 rating: string;
 savings: number;
}

const PROJECTIONS: FiscalProjection[] = [
 { year: 2026, debtGDP: 68.2, deficitGDP: 2.8, debtService: 22.1, liquidity: 14.2, rating: 'BBB+', savings: 0 },
 { year: 2027, debtGDP: 67.5, deficitGDP: 2.5, debtService: 21.3, liquidity: 16.8, rating: 'BBB+', savings: 120 },
 { year: 2028, debtGDP: 65.8, deficitGDP: 2.1, debtService: 19.8, liquidity: 18.5, rating: 'A-', savings: 280 },
 { year: 2029, debtGDP: 63.2, deficitGDP: 1.8, debtService: 18.2, liquidity: 19.2, rating: 'A-', savings: 380 },
 { year: 2030, debtGDP: 61.5, deficitGDP: 1.5, debtService: 17.1, liquidity: 20.5, rating: 'A', savings: 420 },
 { year: 2031, debtGDP: 59.8, deficitGDP: 1.2, debtService: 16.5, liquidity: 21.8, rating: 'A', savings: 450 },
 { year: 2032, debtGDP: 58.2, deficitGDP: 1.0, debtService: 15.8, liquidity: 22.5, rating: 'A+', savings: 480 },
 { year: 2033, debtGDP: 56.8, deficitGDP: 0.8, debtService: 15.2, liquidity: 23.2, rating: 'A+', savings: 500 },
 { year: 2034, debtGDP: 55.5, deficitGDP: 0.6, debtService: 14.8, liquidity: 23.8, rating: 'A+', savings: 520 },
 { year: 2035, debtGDP: 54.2, deficitGDP: 0.5, debtService: 14.5, liquidity: 24.2, rating: 'AA-', savings: 540 },
];

export default function NationalFiscalImpactEngine() {
 const [selectedYear, setSelectedYear] = useState(2030);
 const currentYear = PROJECTIONS[0];
 const targetYear = PROJECTIONS.find(p => p.year === selectedYear) || PROJECTIONS[4];

 const totalSavings = PROJECTIONS.filter(p => p.year <= selectedYear).reduce((sum, p) => sum + p.savings, 0);

 return (
 <div className="space-y-6 animate-glass-in">
 <div className="flex items-center gap-3">
 <div className="w-10 h-10 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-xl flex items-center justify-center">
 <Building2 className="w-5 h-5" />
 </div>
 <div>
 <h2 className="text-xl font-bold text-white">National Fiscal Impact Engine</h2>
 <p className="text-sm text-slate-400">10-year fiscal impact projection for financing strategy</p>
 </div>
 </div>

 {/* Executive Summary */}
 <div className="bg-gradient-to-r from-emerald-500/10 to-teal-500/10 border border-emerald-500/20 rounded-2xl p-6">
 <h3 className="text-sm font-medium text-emerald-400 mb-4"> <BarChart3 className="w-4 h-4 inline" /> EXECUTIVE SUMMARY: "If we adopt this financing strategy..."</h3>
 <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
 <div className="text-center">
 <p className="text-4xl font-bold text-emerald-400">${(totalSavings / 1000).toFixed(1)}B</p>
 <p className="text-sm text-slate-400 mt-1">Total Savings ({selectedYear})</p>
 </div>
 <div className="text-center">
 <p className="text-4xl font-bold text-green-400">{(currentYear.debtGDP - targetYear.debtGDP).toFixed(1)}pp</p>
 <p className="text-sm text-slate-400 mt-1">Debt-to-GDP Reduction</p>
 </div>
 <div className="text-center">
 <p className="text-4xl font-bold text-blue-400">{(currentYear.deficitGDP - targetYear.deficitGDP).toFixed(1)}pp</p>
 <p className="text-sm text-slate-400 mt-1">Deficit Reduction</p>
 </div>
 <div className="text-center">
 <p className="text-4xl font-bold text-purple-400">{targetYear.rating}</p>
 <p className="text-sm text-slate-400 mt-1">Projected Rating ({selectedYear})</p>
 </div>
 </div>
 </div>

 {/* Year Selector */}
 <div className="glass rounded-2xl p-4">
 <div className="flex items-center gap-4">
 <span className="text-sm text-slate-400">Projection Horizon:</span>
 <div className="flex gap-2">
 {[2028, 2030, 2032, 2035].map(year => (
 <button
 key={year}
 onClick={() => setSelectedYear(year)}
 className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
 selectedYear === year
 ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
 : 'bg-white/5 text-slate-400 hover:bg-white/10 border border-transparent'
 }`}
 >
 {year}
 </button>
 ))}
 </div>
 </div>
 </div>

 {/* Detailed Projections */}
 <div className="glass rounded-2xl p-6">
 <h3 className="text-sm font-medium text-slate-400 mb-4">10-YEAR FISCAL PROJECTIONS</h3>
 <div className="overflow-x-auto">
 <table className="w-full">
 <thead>
 <tr className="border-b border-white/10">
 <th className="text-left text-xs text-slate-500 py-3 px-4">Year</th>
 <th className="text-right text-xs text-slate-500 py-3 px-4">Debt/GDP</th>
 <th className="text-right text-xs text-slate-500 py-3 px-4">Deficit/GDP</th>
 <th className="text-right text-xs text-slate-500 py-3 px-4">Debt Service</th>
 <th className="text-right text-xs text-slate-500 py-3 px-4">Liquidity</th>
 <th className="text-right text-xs text-slate-500 py-3 px-4">Rating</th>
 <th className="text-right text-xs text-slate-500 py-3 px-4">Savings</th>
 </tr>
 </thead>
 <tbody>
 {PROJECTIONS.map((p, i) => (
 <tr key={p.year} className={`border-b border-white/5 ${
 p.year === selectedYear ? 'bg-emerald-500/10' : 'hover:bg-white/5'
 }`}>
 <td className="py-3 px-4 text-white text-sm font-medium">{p.year}</td>
 <td className={`py-3 px-4 text-right text-sm ${p.debtGDP < 60 ? 'text-green-400' : p.debtGDP < 70 ? 'text-yellow-400' : 'text-red-400'}`}>
 {p.debtGDP}%
 </td>
 <td className={`py-3 px-4 text-right text-sm ${p.deficitGDP < 1 ? 'text-green-400' : p.deficitGDP < 3 ? 'text-yellow-400' : 'text-red-400'}`}>
 {p.deficitGDP}%
 </td>
 <td className={`py-3 px-4 text-right text-sm ${p.debtService < 18 ? 'text-green-400' : p.debtService < 22 ? 'text-yellow-400' : 'text-red-400'}`}>
 {p.debtService}%
 </td>
 <td className={`py-3 px-4 text-right text-sm ${p.liquidity > 20 ? 'text-green-400' : p.liquidity > 15 ? 'text-yellow-400' : 'text-red-400'}`}>
 {p.liquidity}%
 </td>
 <td className="py-3 px-4 text-right text-sm text-white font-medium">{p.rating}</td>
 <td className="py-3 px-4 text-right text-sm text-green-400 font-medium">
 {p.savings > 0 ? `$${p.savings}M` : '-'}
 </td>
 </tr>
 ))}
 </tbody>
 </table>
 </div>
 </div>

 {/* Key Risks */}
 <div className="glass rounded-2xl p-6 border-l-2 border-amber-500">
 <h3 className="text-sm font-medium text-amber-400 mb-3"> <AlertTriangle className="w-4 h-4 inline" /> KEY RISKS & CAVEATS</h3>
 <div className="grid grid-cols-2 gap-4">
 <div className="space-y-2">
 <div className="flex items-start gap-2 text-sm text-slate-300">
 <span className="text-amber-400">•</span>
 <span>Interest rate environment may change, affecting projected savings</span>
 </div>
 <div className="flex items-start gap-2 text-sm text-slate-300">
 <span className="text-amber-400">•</span>
 <span>GDP growth assumptions may not materialize</span>
 </div>
 <div className="flex items-start gap-2 text-sm text-slate-300">
 <span className="text-amber-400">•</span>
 <span>External shocks (geopolitical, commodity) not fully modeled</span>
 </div>
 </div>
 <div className="space-y-2">
 <div className="flex items-start gap-2 text-sm text-slate-300">
 <span className="text-amber-400">•</span>
 <span>Rating agency response may differ from projections</span>
 </div>
 <div className="flex items-start gap-2 text-sm text-slate-300">
 <span className="text-amber-400">•</span>
 <span>Execution timing may affect actual savings</span>
 </div>
 <div className="flex items-start gap-2 text-sm text-slate-300">
 <span className="text-amber-400">•</span>
 <span>Contagion risk from regional sovereign stress</span>
 </div>
 </div>
 </div>
 </div>

 {/* Confidence Interval */}
 <div className="glass rounded-2xl p-6">
 <h3 className="text-sm font-medium text-slate-400 mb-3"> <BarChart3 className="w-4 h-4 inline" /> CONFIDENCE INTERVAL</h3>
 <div className="grid grid-cols-3 gap-4 text-center">
 <div className="bg-red-500/10 rounded-xl p-4">
 <p className="text-xs text-slate-500 mb-1">Pessimistic (25th)</p>
 <p className="text-2xl font-bold text-red-400">${(totalSavings * 0.7 / 1000).toFixed(1)}B</p>
 <p className="text-xs text-slate-500">Total Savings</p>
 </div>
 <div className="bg-emerald-500/10 rounded-xl p-4">
 <p className="text-xs text-slate-500 mb-1">Base Case (50th)</p>
 <p className="text-2xl font-bold text-emerald-400">${(totalSavings / 1000).toFixed(1)}B</p>
 <p className="text-xs text-slate-500">Total Savings</p>
 </div>
 <div className="bg-green-500/10 rounded-xl p-4">
 <p className="text-xs text-slate-500 mb-1">Optimistic (75th)</p>
 <p className="text-2xl font-bold text-green-400">${(totalSavings * 1.3 / 1000).toFixed(1)}B</p>
 <p className="text-xs text-slate-500">Total Savings</p>
 </div>
 </div>
 </div>
 </div>
 );
}
