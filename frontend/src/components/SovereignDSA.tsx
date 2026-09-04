import React, { useState } from 'react';
import { FileText } from 'lucide-react';

interface DSAResult {
  framework: string;
  status: 'sustainable' | 'moderate_risk' | 'high_risk' | 'unsustainable';
  score: number;
  metrics: { name: string; value: string; threshold: string; status: 'pass' | 'warning' | 'fail' }[];
  recommendations: string[];
  lastUpdated: string;
}

const MOCK_DSA: DSAResult[] = [
  {
    framework: 'IMF Debt Sustainability Framework',
    status: 'moderate_risk',
    score: 68,
    metrics: [
      { name: 'PV of Debt/GDP', value: '52.3%', threshold: '<70%', status: 'pass' },
      { name: 'PV of Debt/Revenue', value: '185%', threshold: '<200%', status: 'pass' },
      { name: 'Debt Service/Revenue', value: '22.1%', threshold: '<25%', status: 'warning' },
      { name: 'Gross Financing Needs/GDP', value: '18.5%', threshold: '<20%', status: 'warning' },
      { name: 'Real GDP Growth', value: '2.1%', threshold: '>2%', status: 'pass' },
      { name: 'Primary Balance/GDP', value: '-1.2%', threshold: '>-2%', status: 'warning' },
      { name: 'International Reserves', value: '4.2 months', threshold: '>3 months', status: 'pass' },
      { name: 'Short-term Debt/Total', value: '18.3%', threshold: '<20%', status: 'pass' },
    ],
    recommendations: [
      'Implement fiscal consolidation plan to achieve primary surplus of 0.5% by 2028',
      'Reduce short-term debt rollover risk by extending average maturity',
      'Build reserves to 5+ months of import cover',
      'Monitor debt service ratio closely as interest rates may rise',
    ],
    lastUpdated: '2026-08-24' },
  {
    framework: 'World Bank Composite DSA',
    status: 'moderate_risk',
    score: 62,
    metrics: [
      { name: 'Total Debt/GDP', value: '68.2%', threshold: '<75%', status: 'pass' },
      { name: 'External Debt/GNI', value: '38.5%', threshold: '<40%', status: 'warning' },
      { name: 'Debt Service/Exports', value: '14.2%', threshold: '<15%', status: 'warning' },
      { name: 'Concessional Debt/Total', value: '32.1%', threshold: '>25%', status: 'pass' },
      { name: 'Short-term Debt/Reserves', value: '42.3%', threshold: '<50%', status: 'pass' },
      { name: 'Current Account/GDP', value: '-3.8%', threshold: '-5% to 5%', status: 'pass' },
      { name: 'FDI/GDP', value: '2.1%', threshold: '>2%', status: 'pass' },
      { name: 'Remittances/GDP', value: '1.8%', threshold: '>1%', status: 'pass' },
    ],
    recommendations: [
      'Diversify export base to reduce commodity dependency',
      'Attract more FDI in non-extractive sectors',
      'Negotiate extended maturities with bilateral creditors',
      'Strengthen debt management office capacity',
    ],
    lastUpdated: '2026-08-24' },
  {
    framework: 'ECB Fiscal Sustainability',
    status: 'sustainable',
    score: 78,
    metrics: [
      { name: 'Debt/GDP', value: '68.2%', threshold: '<60%', status: 'warning' },
      { name: 'Deficit/GDP', value: '2.8%', threshold: '<3%', status: 'pass' },
      { name: 'Maastricht Compliance', value: '2/3', threshold: '3/3', status: 'warning' },
      { name: 'Excessive Deficit Procedure', value: 'No', threshold: 'No', status: 'pass' },
      { name: 'Structural Balance', value: '-1.5%', threshold: '>-1%', status: 'warning' },
      { name: 'Age-related Spending', value: '+2.1pp', threshold: '<0.5pp', status: 'fail' },
    ],
    recommendations: [
      'Develop medium-term fiscal framework to address age-related spending',
      'Implement pension reform to ensure long-term sustainability',
      'Achieve structural balance surplus by 2030',
      'Comply with Maastricht debt criterion within 15-year horizon',
    ],
    lastUpdated: '2026-08-24' },
  {
    framework: 'BIS Basel III',
    status: 'sustainable',
    score: 85,
    metrics: [
      { name: 'Capital Adequacy', value: '14.2%', threshold: '>10.5%', status: 'pass' },
      { name: 'Leverage Ratio', value: '5.8%', threshold: '>3%', status: 'pass' },
      { name: 'Liquidity Coverage', value: '125%', threshold: '>100%', status: 'pass' },
      { name: 'Net Stable Funding', value: '118%', threshold: '>100%', status: 'pass' },
      { name: 'Counterparty Risk', value: '2.1%', threshold: '<5%', status: 'pass' },
      { name: 'Market Risk', value: '3.2%', threshold: '<8%', status: 'pass' },
    ],
    recommendations: [
      'Maintain current capital buffers',
      'Monitor interest rate risk in banking book',
      'Stress test against 300bps rate shock',
    ],
    lastUpdated: '2026-08-24' },
];

const STATUS_COLORS: Record<string, string> = {
  sustainable: 'bg-green-500/20 text-green-400',
  moderate_risk: 'bg-yellow-500/20 text-yellow-400',
  high_risk: 'bg-orange-500/20 text-orange-400',
  unsustainable: 'bg-red-500/20 text-red-400' };

const STATUS_LABELS: Record<string, string> = {
  sustainable: 'Sustainable',
  moderate_risk: 'Moderate Risk',
  high_risk: 'High Risk',
  unsustainable: 'Unsustainable' };

export default function SovereignDSA() {
  const [selectedFramework, setSelectedFramework] = useState(MOCK_DSA[0]);
  const [activeTab, setActiveTab] = useState<'overview' | 'metrics' | 'projections' | 'recommendations'>('overview');

  return (
    <div className="space-y-6 animate-glass-in">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-xl flex items-center justify-center">
          <FileText className="w-5 h-5" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">Sovereign Debt Sustainability</h2>
          <p className="text-sm text-slate-400">IMF, World Bank, ECB & BIS compliance frameworks</p>
        </div>
      </div>

      {/* Framework Selector */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[].map(f => (
          <button
            key={f.framework}
            onClick={() => setSelectedFramework(f)}
            className={`text-left p-4 rounded-xl border transition-all ${
              selectedFramework.framework === f.framework
                ? 'bg-emerald-500/10 border-emerald-500/30'
                : 'bg-white/5 border-white/10 hover:bg-white/10'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[f.status]}`}>
                {STATUS_LABELS[f.status]}
              </span>
            </div>
            <h4 className="text-white text-sm font-medium mb-1">{f.framework.split(' ')[0]}</h4>
            <p className="text-xs text-slate-400">{f.framework}</p>
            <div className="mt-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-slate-500">Score</span>
                <span className="text-sm font-bold text-white">{f.score}/100</span>
              </div>
              <div className="w-full bg-white/5 rounded-full h-2">
                <div
                  className={`h-2 rounded-full ${
                    f.score >= 75 ? 'bg-green-400' :
                    f.score >= 50 ? 'bg-yellow-400' : 'bg-red-400'
                  }`}
                  style={{ width: `${f.score}%` }}
                />
              </div>
            </div>
          </button>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-2">
        {(['overview', 'metrics', 'projections', 'recommendations'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
              activeTab === tab
                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                : 'bg-white/5 text-slate-400 hover:bg-white/10 border border-transparent'
            }`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview */}
      {activeTab === 'overview' && (
        <div className="space-y-4">
          <div className="glass rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-white">{selectedFramework.framework}</h3>
              <span className={`px-3 py-1 rounded-lg text-sm font-medium ${STATUS_COLORS[selectedFramework.status]}`}>
                {STATUS_LABELS[selectedFramework.status]}
              </span>
            </div>
            <div className="grid grid-cols-4 gap-4 text-center">
              <div>
                <p className="text-3xl font-bold text-white">{selectedFramework.score}</p>
                <p className="text-xs text-slate-500">Score</p>
              </div>
              <div>
                <p className="text-3xl font-bold text-white">
                  {selectedFramework.metrics.filter(m => m.status === 'pass').length}
                </p>
                <p className="text-xs text-slate-500">Passing</p>
              </div>
              <div>
                <p className="text-3xl font-bold text-yellow-400">
                  {selectedFramework.metrics.filter(m => m.status === 'warning').length}
                </p>
                <p className="text-xs text-slate-500">Warnings</p>
              </div>
              <div>
                <p className="text-3xl font-bold text-red-400">
                  {selectedFramework.metrics.filter(m => m.status === 'fail').length}
                </p>
                <p className="text-xs text-slate-500">Failing</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Metrics */}
      {activeTab === 'metrics' && (
        <div className="glass rounded-2xl p-6">
          <h3 className="text-sm font-medium text-slate-400 mb-4">KEY METRICS</h3>
          <div className="space-y-3">
            {selectedFramework.metrics.map((m, i) => (
              <div key={i} className={`flex items-center justify-between p-3 rounded-xl border ${
                m.status === 'pass' ? 'bg-green-500/5 border-green-500/20' :
                m.status === 'warning' ? 'bg-yellow-500/5 border-yellow-500/20' :
                'bg-red-500/5 border-red-500/20'
              }`}>
                <div className="flex items-center gap-3">
                  <span className={`w-2 h-2 rounded-full ${
                    m.status === 'pass' ? 'bg-green-400' :
                    m.status === 'warning' ? 'bg-yellow-400' : 'bg-red-400'
                  }`} />
                  <span className="text-white text-sm">{m.name}</span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-xs text-slate-500">Threshold: {m.threshold}</span>
                  <span className={`text-sm font-medium ${
                    m.status === 'pass' ? 'text-green-400' :
                    m.status === 'warning' ? 'text-yellow-400' : 'text-red-400'
                  }`}>
                    {m.value}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Projections */}
      {activeTab === 'projections' && (
        <div className="glass rounded-2xl p-6">
          <h3 className="text-sm font-medium text-slate-400 mb-4">10-YEAR PROJECTIONS</h3>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { year: '2026', debt: '68.2%', deficit: '2.8%', growth: '2.1%', risk: 'moderate' },
              { year: '2027', debt: '69.1%', deficit: '2.5%', growth: '2.3%', risk: 'moderate' },
              { year: '2028', debt: '67.8%', deficit: '2.0%', growth: '2.5%', risk: 'moderate' },
              { year: '2029', debt: '66.5%', deficit: '1.5%', growth: '2.4%', risk: 'low' },
              { year: '2030', debt: '65.2%', deficit: '1.0%', growth: '2.3%', risk: 'low' },
              { year: '2031', debt: '63.8%', deficit: '0.5%', growth: '2.2%', risk: 'low' },
              { year: '2032', debt: '62.5%', deficit: '0.0%', growth: '2.1%', risk: 'low' },
              { year: '2033', debt: '61.2%', deficit: '-0.5%', growth: '2.0%', risk: 'low' },
            ].map(p => (
              <div key={p.year} className="bg-white/5 rounded-xl p-3 text-center">
                <p className="text-lg font-bold text-white">{p.year}</p>
                <p className="text-xs text-slate-400 mb-2">Debt/GDP</p>
                <p className="text-xl font-bold text-white">{p.debt}</p>
                <div className="mt-2 space-y-1">
                  <p className="text-xs text-slate-500">Deficit: {p.deficit}</p>
                  <p className="text-xs text-slate-500">Growth: {p.growth}</p>
                  <span className={`px-2 py-0.5 rounded text-xs ${
                    p.risk === 'low' ? 'bg-green-500/20 text-green-400' :
                    p.risk === 'moderate' ? 'bg-yellow-500/20 text-yellow-400' :
                    'bg-red-500/20 text-red-400'
                  }`}>
                    {p.risk} risk
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {activeTab === 'recommendations' && (
        <div className="glass rounded-2xl p-6">
          <h3 className="text-sm font-medium text-slate-400 mb-4">COMPLIANCE RECOMMENDATIONS</h3>
          <div className="space-y-3">
            {selectedFramework.recommendations.map((rec, i) => (
              <div key={i} className="flex items-start gap-3 p-3 bg-white/5 rounded-xl">
                <span className="text-emerald-400 mt-0.5">{i + 1}.</span>
                <p className="text-sm text-slate-300">{rec}</p>
              </div>
            ))}
          </div>
          <div className="mt-4 flex gap-3">
            <button className="flex-1 py-3 bg-emerald-500/20 border border-emerald-500/30 rounded-xl text-emerald-400 font-medium hover:bg-emerald-500/30 transition-colors">
              📄 Export Compliance Report
            </button>
            <button className="flex-1 py-3 bg-white/5 border border-white/10 rounded-xl text-slate-400 hover:bg-white/10 transition-colors">
              📧 Share with Stakeholders
            </button>
          </div>
        </div>
      )}

      {/* Last Updated */}
      <div className="text-right text-xs text-slate-500">
        Last updated: {selectedFramework.lastUpdated}
      </div>
    </div>
  );
}
