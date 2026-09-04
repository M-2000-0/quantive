// ── Portfolio Comparison Mode Component ────────────────────────────────
// Side-by-side comparison of two portfolios with metrics, charts,
// and optimization recommendations.

import { useState, useMemo } from 'react';
import GlassBarChart from './charts/GlassBarChart';
import GlassPieChart from './charts/GlassPieChart';

interface PortfolioData {
  id: string;
  name: string;
  totalPrincipal: number;
  avgYield: number;
  avgDuration: number;
  avgRating: string;
  instrumentCount: number;
  currencyBreakdown: Record<string, number>;
  sectorBreakdown: Record<string, number>;
  riskScore: number;
  unrealizedPnl: number;
  maturityProfile: Array<{ label: string; value: number }>;
  topInstruments: Array<{ name: string; principal: number; yield: number; rating: string }>;
}

const MOCK_PORTFOLIOS: PortfolioData[] = [
  {
    id: 'pf-001',
    name: 'US Investment Grade Corporate',
    totalPrincipal: 150_000_000,
    avgYield: 4.92,
    avgDuration: 4.8,
    avgRating: 'A+',
    instrumentCount: 12,
    currencyBreakdown: { USD: 85, EUR: 10, GBP: 5 },
    sectorBreakdown: { Technology: 30, Financial: 25, Healthcare: 20, Energy: 15, Other: 10 },
    riskScore: 42,
    unrealizedPnl: 2_340_000,
    maturityProfile: [
      { label: '<1Y', value: 15 },
      { label: '1-3Y', value: 25 },
      { label: '3-5Y', value: 30 },
      { label: '5-10Y', value: 20 },
      { label: '>10Y', value: 10 },
    ],
    topInstruments: [
      { name: 'US Treasury 10Y', principal: 50_000_000, yield: 3.95, rating: 'AAA' },
      { name: 'Apple Senior Note 2030', principal: 25_000_000, yield: 3.85, rating: 'AA+' },
      { name: 'JPMorgan Term Loan B', principal: 35_000_000, yield: 5.65, rating: 'A+' },
    ] },
  {
    id: 'pf-002',
    name: 'European Sovereign & Corporate',
    totalPrincipal: 80_000_000,
    avgYield: 3.42,
    avgDuration: 7.1,
    avgRating: 'AA-',
    instrumentCount: 8,
    currencyBreakdown: { EUR: 70, GBP: 20, USD: 10 },
    sectorBreakdown: { Government: 40, Financial: 30, Consumer: 20, Other: 10 },
    riskScore: 28,
    unrealizedPnl: -450_000,
    maturityProfile: [
      { label: '<1Y', value: 5 },
      { label: '1-3Y', value: 15 },
      { label: '3-5Y', value: 25 },
      { label: '5-10Y', value: 35 },
      { label: '>10Y', value: 20 },
    ],
    topInstruments: [
      { name: 'UK Gilt 5Y', principal: 30_000_000, yield: 3.35, rating: 'AA+' },
      { name: 'Nestlé Euro CP', principal: 20_000_000, yield: 2.95, rating: 'AAA' },
      { name: 'Deutsche Bank FRN', principal: 25_000_000, yield: 3.65, rating: 'BBB+' },
    ] },
];

interface PortfolioComparisonModeProps {
  /** First portfolio ID */
  portfolio1Id?: string;
  /** Second portfolio ID */
  portfolio2Id?: string;
}

export default function PortfolioComparisonMode({
  portfolio1Id = 'pf-001',
  portfolio2Id = 'pf-002' }: PortfolioComparisonModeProps) {
  const [selected1, setSelected1] = useState(portfolio1Id);
  const [selected2, setSelected2] = useState(portfolio2Id);
  const [activeMetric, setActiveMetric] = useState<'overview' | 'allocation' | 'risk' | 'instruments'>('overview');

  const portfolio1 = useMemo(() => MOCK_PORTFOLIOS.find((p) => p.id === selected1)!, [selected1]);
  const portfolio2 = useMemo(() => MOCK_PORTFOLIOS.find((p) => p.id === selected2)!, [selected2]);

  const comparisonMetrics = useMemo(() => {
    if (!portfolio1 || !portfolio2) return [];
    return [
      {
        label: 'Total Principal',
        p1: `$${(portfolio1.totalPrincipal / 1e6).toFixed(0)}M`,
        p2: `$${(portfolio2.totalPrincipal / 1e6).toFixed(0)}M`,
        winner: portfolio1.totalPrincipal > portfolio2.totalPrincipal ? 1 : 2,
        diff: Math.abs(portfolio1.totalPrincipal - portfolio2.totalPrincipal) / 1e6 },
      {
        label: 'Avg Yield',
        p1: `${portfolio1.avgYield}%`,
        p2: `${portfolio2.avgYield}%`,
        winner: portfolio1.avgYield > portfolio2.avgYield ? 1 : 2,
        diff: Math.abs(portfolio1.avgYield - portfolio2.avgYield) },
      {
        label: 'Avg Duration',
        p1: `${portfolio1.avgDuration}yr`,
        p2: `${portfolio2.avgDuration}yr`,
        winner: portfolio1.avgDuration < portfolio2.avgDuration ? 1 : 2,
        diff: Math.abs(portfolio1.avgDuration - portfolio2.avgDuration) },
      {
        label: 'Risk Score',
        p1: `${portfolio1.riskScore}/100`,
        p2: `${portfolio2.riskScore}/100`,
        winner: portfolio1.riskScore < portfolio2.riskScore ? 1 : 2,
        diff: Math.abs(portfolio1.riskScore - portfolio2.riskScore) },
      {
        label: 'Unrealized P&L',
        p1: `$${(portfolio1.unrealizedPnl / 1e6).toFixed(2)}M`,
        p2: `$${(portfolio2.unrealizedPnl / 1e6).toFixed(2)}M`,
        winner: portfolio1.unrealizedPnl > portfolio2.unrealizedPnl ? 1 : 2,
        diff: Math.abs(portfolio1.unrealizedPnl - portfolio2.unrealizedPnl) / 1e6 },
      {
        label: 'Instruments',
        p1: `${portfolio1.instrumentCount}`,
        p2: `${portfolio2.instrumentCount}`,
        winner: portfolio1.instrumentCount > portfolio2.instrumentCount ? 1 : 2,
        diff: Math.abs(portfolio1.instrumentCount - portfolio2.instrumentCount) },
    ];
  }, [portfolio1, portfolio2]);

  // Chart data for comparison
  const yieldCompareData = useMemo(() => {
    if (!portfolio1 || !portfolio2) return [];
    return [
      { name: portfolio1.name.split(' ')[0], yield: portfolio1.avgYield },
      { name: portfolio2.name.split(' ')[0], yield: portfolio2.avgYield },
    ];
  }, [portfolio1, portfolio2]);

  const riskCompareData = useMemo(() => {
    if (!portfolio1 || !portfolio2) return [];
    return [
      { name: portfolio1.name.split(' ')[0], risk: portfolio1.riskScore },
      { name: portfolio2.name.split(' ')[0], risk: portfolio2.riskScore },
    ];
  }, [portfolio1, portfolio2]);

  const currencyCompareData = useMemo(() => {
    if (!portfolio1 || !portfolio2) return [];
    const allCurrencies = new Set([...Object.keys(portfolio1.currencyBreakdown), ...Object.keys(portfolio2.currencyBreakdown)]);
    return Array.from(allCurrencies).map((currency) => ({
      currency,
      p1: portfolio1.currencyBreakdown[currency] || 0,
      p2: portfolio2.currencyBreakdown[currency] || 0 }));
  }, [portfolio1, portfolio2]);

  return (
    <div className="space-y-6 animate-glass-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900">Portfolio Comparison</h2>
          <p className="text-sm text-slate-600 mt-1">Side-by-side analysis of portfolio metrics and allocation</p>
        </div>
      </div>

      {/* Portfolio Selectors */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[portfolio1, portfolio2].map((portfolio, idx) => (
          <div key={portfolio?.id} className="glass rounded-2xl p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-slate-500">PORTFOLIO {idx + 1}</span>
              <select
                value={idx === 0 ? selected1 : selected2}
                onChange={(e) => idx === 0 ? setSelected1(e.target.value) : setSelected2(e.target.value)}
                className="text-sm font-medium text-slate-900 bg-transparent border-none focus:outline-none cursor-pointer"
              >
                {MOCK_PORTFOLIOS.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <div className="text-xs text-slate-500">Principal</div>
                <div className="text-lg font-bold text-slate-900">${(portfolio!.totalPrincipal / 1e6).toFixed(0)}M</div>
              </div>
              <div>
                <div className="text-xs text-slate-500">Yield</div>
                <div className="text-lg font-bold text-slate-900">{portfolio!.avgYield}%</div>
              </div>
              <div>
                <div className="text-xs text-slate-500">Duration</div>
                <div className="text-lg font-bold text-slate-900">{portfolio!.avgDuration}yr</div>
              </div>
              <div>
                <div className="text-xs text-slate-500">Risk</div>
                <div className={`text-lg font-bold ${portfolio!.riskScore < 40 ? 'text-emerald-600' : 'text-amber-600'}`}>{portfolio!.riskScore}</div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Metric Tabs */}
      <div className="flex gap-1 bg-white/40 backdrop-blur rounded-xl p-1 w-fit border border-white/30">
        {(['overview', 'allocation', 'risk', 'instruments'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveMetric(tab)}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-all capitalize ${
              activeMetric === tab
                ? 'bg-white text-slate-900 shadow-sm border border-white/60'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Overview Comparison */}
      {activeMetric === 'overview' && (
        <div className="glass rounded-2xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/20">
                <th className="px-4 py-3 text-left font-semibold text-slate-700">Metric</th>
                <th className="px-4 py-3 text-center font-semibold text-blue-700">{portfolio1.name}</th>
                <th className="px-4 py-3 text-center font-semibold text-purple-700">{portfolio2.name}</th>
                <th className="px-4 py-3 text-center font-semibold text-slate-700">Better</th>
              </tr>
            </thead>
            <tbody>
              {comparisonMetrics.map((metric) => (
                <tr key={metric.label} className="border-b border-white/10 hover:bg-white/30">
                  <td className="px-4 py-3 font-medium text-slate-900">{metric.label}</td>
                  <td className={`px-4 py-3 text-center font-bold ${metric.winner === 1 ? 'text-blue-600' : 'text-slate-600'}`}>
                    {metric.p1}
                  </td>
                  <td className={`px-4 py-3 text-center font-bold ${metric.winner === 2 ? 'text-purple-600' : 'text-slate-600'}`}>
                    {metric.p2}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      metric.winner === 1 ? 'bg-blue-50 text-blue-600' : 'bg-purple-50 text-purple-600'
                    }`}>
                      {metric.winner === 1 ? portfolio1.name.split(' ')[0] : portfolio2.name.split(' ')[0]}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Allocation Comparison */}
      {activeMetric === 'allocation' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="glass rounded-2xl p-4">
            <h3 className="text-sm font-bold text-slate-900 mb-3">Currency Breakdown</h3>
            <div className="space-y-2">
              {currencyCompareData.map((item) => (
                <div key={item.currency} className="flex items-center gap-2">
                  <span className="text-xs font-medium text-slate-700 w-12">{item.currency}</span>
                  <div className="flex-1 flex items-center gap-1">
                    <div className="h-3 rounded bg-blue-400" style={{ width: `${item.p1}%` }} />
                    <div className="h-3 rounded bg-purple-400" style={{ width: `${item.p2}%` }} />
                  </div>
                  <span className="text-[10px] text-slate-500 w-16 text-right">{item.p1}% / {item.p2}%</span>
                </div>
              ))}
            </div>
            <div className="flex items-center gap-4 mt-3 text-[10px] text-slate-500">
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-blue-400" /> Portfolio 1</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-purple-400" /> Portfolio 2</span>
            </div>
          </div>

          <div className="glass rounded-2xl p-4">
            <h3 className="text-sm font-bold text-slate-900 mb-3">Sector Breakdown</h3>
            <div className="space-y-2">
              {Object.keys(portfolio1.sectorBreakdown).map((sector) => (
                <div key={sector} className="flex items-center gap-2">
                  <span className="text-xs font-medium text-slate-700 w-24 truncate">{sector}</span>
                  <div className="flex-1 flex items-center gap-1">
                    <div className="h-3 rounded bg-blue-400" style={{ width: `${portfolio1.sectorBreakdown[sector]}%` }} />
                    <div className="h-3 rounded bg-purple-400" style={{ width: `${portfolio2.sectorBreakdown[sector] || 0}%` }} />
                  </div>
                  <span className="text-[10px] text-slate-500 w-16 text-right">{portfolio1.sectorBreakdown[sector]}% / {portfolio2.sectorBreakdown[sector] || 0}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Risk Comparison */}
      {activeMetric === 'risk' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="glass rounded-2xl p-4">
            <GlassBarChart
              data={riskCompareData}
              xKey="name"
              yKeys={[{ key: 'risk', color: '#ef4444', name: 'Risk Score' }]}
              title="Risk Score Comparison"
              height={200}
            />
          </div>
          <div className="glass rounded-2xl p-4">
            <GlassBarChart
              data={yieldCompareData}
              xKey="name"
              yKeys={[{ key: 'yield', color: '#10b981', name: 'Avg Yield %' }]}
              title="Yield Comparison"
              height={200}
              formatY={(v) => `${v.toFixed(2)}%`}
            />
          </div>
        </div>
      )}

      {/* Instruments */}
      {activeMetric === 'instruments' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[portfolio1, portfolio2].map((portfolio, idx) => (
            <div key={portfolio?.id} className="glass rounded-2xl p-4">
              <h3 className="text-sm font-bold text-slate-900 mb-3">Top Instruments — Portfolio {idx + 1}</h3>
              <div className="space-y-2">
                {portfolio!.topInstruments.map((inst) => (
                  <div key={inst.name} className="flex items-center justify-between p-2 rounded-lg bg-white/30">
                    <div>
                      <div className="text-xs font-medium text-slate-900">{inst.name}</div>
                      <div className="text-[10px] text-slate-500">{inst.rating} · {inst.yield}%</div>
                    </div>
                    <div className="text-xs font-bold text-slate-900">${(inst.principal / 1e6).toFixed(0)}M</div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
