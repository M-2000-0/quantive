import { useState } from 'react';
import Card, { CardHeader } from './ui/Card';
import Badge from './ui/Badge';
import Button from './ui/Button';
import GlassAreaChart from './charts/GlassAreaChart';
import GlassBarChart from './charts/GlassBarChart';
import GlassPieChart from './charts/GlassPieChart';
import GlassLineChart from './charts/GlassLineChart';
import GlassGaugeChart from './charts/GlassGaugeChart';
import GlassHeatmap from './charts/GlassHeatmap';
import {
  POLICY_RATES,
  YIELD_CURVE,
  CREDIT_SPREADS,
  GREEN_BOND_ISSUANCE,
  EM_LOCAL_YIELDS,
  MARKET_OVERVIEW,
  REFINANCING_WALL,
  RISK_MATRIX,
  ALLOCATION_TARGETS,
  EXECUTIVE_SUMMARY,
  KEY_RECOMMENDATIONS } from '../lib/marketReportData';

type ReportSection = 'summary' | 'rates' | 'credit' | 'green' | 'em' | 'risk' | 'allocation';

const SECTIONS: { key: ReportSection; label: string; icon: string }[] = [
  { key: 'summary', label: 'Executive Summary', icon: 'BarChart3' },
  { key: 'rates', label: 'Interest Rates', icon: 'TrendingUp' },
  { key: 'credit', label: 'Credit Spreads', icon: 'CreditCard' },
  { key: 'green', label: 'Green Bonds', icon: '🌿' },
  { key: 'em', label: 'EM Debt', icon: 'Globe' },
  { key: 'risk', label: 'Risk Assessment', icon: 'AlertTriangle' },
  { key: 'allocation', label: 'Recommendations', icon: 'Target' },
];

function formatCurrency(val: number): string {
  if (val >= 1000) return `$${(val / 1000).toFixed(1)}T`;
  return `$${val}B`;
}

function SectionNav({ active, onChange }: { active: ReportSection; onChange: (s: ReportSection) => void }) {
  return (
    <div className="flex gap-1 mb-6 bg-white/40 backdrop-blur rounded-xl p-1 w-fit border border-white/30 flex-wrap">
      {SECTIONS.map((s) => (
        <button
          key={s.key}
          onClick={() => onChange(s.key)}
          className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${
            active === s.key
              ? 'bg-white text-slate-900 shadow-sm border border-white/60'
              : 'text-slate-500 hover:text-slate-700'
          }`}
        >
          {s.icon} {s.label}
        </button>
      ))}
    </div>
  );
}

function ExecutiveSummarySection() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader title="Global Fixed Income & Debt Markets" subtitle="Investment Outlook — August 2026" />
        <div className="px-6 pb-4">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
            <div className="glass-light p-3 text-center">
              <p className="text-xs font-medium text-slate-500">Total Global Debt</p>
              <p className="text-xl font-bold text-slate-900">${MARKET_OVERVIEW.totalGlobalDebt}T</p>
            </div>
            <div className="glass-light p-3 text-center">
              <p className="text-xs font-medium text-slate-500">IG Issuance YTD</p>
              <p className="text-xl font-bold text-slate-900">${MARKET_OVERVIEW.igIssuanceYTD}B</p>
              <Badge variant="success" size="sm">+{MARKET_OVERVIEW.igIssuanceYoYChange}% YoY</Badge>
            </div>
            <div className="glass-light p-3 text-center">
              <p className="text-xs font-medium text-slate-500">IG Default Rate</p>
              <p className="text-xl font-bold text-emerald-700">{MARKET_OVERVIEW.igDefaultRate}%</p>
            </div>
            <div className="glass-light p-3 text-center">
              <p className="text-xs font-medium text-slate-500">Core PCE</p>
              <p className="text-xl font-bold text-slate-900">{MARKET_OVERVIEW.corePCE}%</p>
            </div>
          </div>
          <h3 className="text-sm font-semibold text-slate-900 mb-3">Key Findings</h3>
          <ul className="space-y-2">
            {EXECUTIVE_SUMMARY.map((finding, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                <span className="text-blue-500 mt-0.5 font-bold">{i + 1}.</span>
                {finding}
              </li>
            ))}
          </ul>
        </div>
      </Card>
    </div>
  );
}

function RatesSection() {
  const yieldData = YIELD_CURVE.map((y) => ({
    maturity: y.maturity,
    'Aug 2026': y.yieldAug2026,
    'Jan 2025': y.yieldJan2025 }));

  return (
    <div className="space-y-6">
      <GlassLineChart
        data={yieldData}
        xKey="maturity"
        yKeys={[
          { key: 'Aug 2026', color: '#3b82f6', name: 'Aug 2026 Yield' },
          { key: 'Jan 2025', color: '#94a3b8', name: 'Jan 2025 Yield', dashed: true },
        ]}
        title="US Treasury Yield Curve — Current vs 18 Months Ago"
        height={320}
        formatY={(v) => `${v.toFixed(2)}%`}
      />

      <Card>
        <CardHeader title="Central Bank Policy Rates" subtitle="Current rates and forward guidance" />
        <div className="px-6 pb-4">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/40">
                  <th className="text-left px-4 py-2 text-xs font-semibold text-slate-500 uppercase">Central Bank</th>
                  <th className="text-right px-4 py-2 text-xs font-semibold text-slate-500 uppercase">Rate</th>
                  <th className="text-center px-4 py-2 text-xs font-semibold text-slate-500 uppercase">Direction</th>
                  <th className="text-left px-4 py-2 text-xs font-semibold text-slate-500 uppercase">Next Move</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/25">
                {POLICY_RATES.map((r) => (
                  <tr key={r.bank} className="hover:bg-white/30 transition-colors">
                    <td className="px-4 py-3 font-medium text-slate-900">{r.bank}</td>
                    <td className="px-4 py-3 text-right font-bold text-slate-900 tabular-nums">{r.rate.toFixed(2)}%</td>
                    <td className="px-4 py-3 text-center">
                      <Badge variant={r.direction === 'easing' ? 'success' : r.direction === 'tightening' ? 'danger' : 'info'}>
                        {r.direction}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{r.nextExpectedMove}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="glass-light p-3 text-center">
          <p className="text-xs text-slate-500">Fed Terminal Rate</p>
          <p className="text-lg font-bold text-slate-900">{MARKET_OVERVIEW.fedTerminalRate}%</p>
          <p className="text-[10px] text-slate-400">Market-implied</p>
        </div>
        <div className="glass-light p-3 text-center">
          <p className="text-xs text-slate-500">10Y TIPS Real Yield</p>
          <p className="text-lg font-bold text-slate-900">{MARKET_OVERVIEW.tipsRealYield10Y}%</p>
          <p className="text-[10px] text-slate-400">Above LT avg 1.2%</p>
        </div>
        <div className="glass-light p-3 text-center">
          <p className="text-xs text-slate-500">S&P 500 Margin</p>
          <p className="text-lg font-bold text-slate-900">{MARKET_OVERVIEW.sp500OperatingMargin}%</p>
          <p className="text-[10px] text-slate-400">Q2 2026</p>
        </div>
        <div className="glass-light p-3 text-center">
          <p className="text-xs text-slate-500">US Debt/GDP (2027)</p>
          <p className="text-lg font-bold text-red-700">{MARKET_OVERVIEW.usDebtToGDP}%</p>
          <p className="text-[10px] text-slate-400">CBO projection</p>
        </div>
      </div>
    </div>
  );
}

function CreditSection() {
  const spreadData = CREDIT_SPREADS.map((s) => ({
    month: s.month.replace(' 20', ' \''),
    'IG Spread': s.igSpread,
    'HY Spread': s.hySpread / 4, // scale for dual axis
  }));

  const spreadDetail = CREDIT_SPREADS.map((s) => ({
    month: s.month.replace(' 20', ' \''),
    'IG (bps)': s.igSpread,
    'HY (bps)': s.hySpread }));

  return (
    <div className="space-y-6">
      <GlassLineChart
        data={spreadData}
        xKey="month"
        yKeys={[
          { key: 'IG Spread', color: '#3b82f6', name: 'IG Spread (bps)' },
        ]}
        title="IG Credit Spreads — Tightening Trend"
        height={280}
        formatY={(v) => `${v}bps`}
      />

      <GlassBarChart
        data={spreadDetail}
        xKey="month"
        yKeys={[
          { key: 'IG (bps)', color: '#3b82f6', name: 'IG Spread' },
          { key: 'HY (bps)', color: '#f59e0b', name: 'HY Spread (÷4 for scale)' },
        ]}
        title="Credit Spreads by Rating Tier"
        height={280}
        formatY={(v) => `${v}bps`}
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="glass-light p-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-medium text-slate-500">IG Spread</p>
            <Badge variant="success">82 bps</Badge>
          </div>
          <p className="text-sm text-slate-600">
            40bps tighter than 10-year median of 122bps. Strong corporate fundamentals with 0.08% default rate.
          </p>
          <div className="mt-2">
            <GlassGaugeChart value={82} min={0} max={200} size={120} color="#3b82f6" formatValue={(v) => `${v}bps`} />
          </div>
        </div>
        <div className="glass-light p-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-medium text-slate-500">HY Spread</p>
            <Badge variant="warning">310 bps</Badge>
          </div>
          <p className="text-sm text-slate-600">
            40bps tighter than 10-year median of 350bps. Default rate elevated to 2.8% — selectivity required.
          </p>
          <div className="mt-2">
            <GlassGaugeChart value={310} min={0} max={600} size={120} color="#f59e0b" formatValue={(v) => `${v}bps`} />
          </div>
        </div>
      </div>

      <Card>
        <CardHeader title="Refinancing Wall" subtitle="Global bond maturities 2025-2027 (billions USD)" />
        <GlassBarChart
          data={REFINANCING_WALL.map((r) => ({
            year: String(r.year),
            'Total': r.totalMaturities,
            'HY': r.hyMaturities }))}
          xKey="year"
          yKeys={[
            { key: 'Total', color: '#6366f1', name: 'Total Maturities' },
            { key: 'HY', color: '#ef4444', name: 'HY Maturities' },
          ]}
          height={220}
          formatY={(v) => `$${v}B`}
        />
      </Card>
    </div>
  );
}

function GreenBondSection() {
  const issuanceData = GREEN_BOND_ISSUANCE.map((g) => ({
    year: String(g.year),
    'Annual Issuance': g.issuance,
    'Cumulative': g.cumulative }));

  return (
    <div className="space-y-6">
      <GlassBarChart
        data={issuanceData}
        xKey="year"
        yKeys={[
          { key: 'Annual Issuance', color: '#10b981', name: 'Annual Issuance ($B)' },
        ]}
        title="Green Bond Annual Issuance — Exponential Growth"
        height={300}
        formatY={(v) => `$${v}B`}
      />

      <GlassAreaChart
        data={issuanceData}
        xKey="year"
        yKeys={[{ key: 'Cumulative', color: '#10b981', name: 'Cumulative ($B)' }]}
        title="Cumulative Green Bond Issuance"
        height={250}
        formatY={(v) => `$${v}B`}
      />

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="glass-light p-3 text-center">
          <p className="text-xs text-slate-500">2025 Issuance</p>
          <p className="text-xl font-bold text-emerald-700">$1.2T</p>
          <p className="text-[10px] text-slate-400">Record year</p>
        </div>
        <div className="glass-light p-3 text-center">
          <p className="text-xs text-slate-500">2026 Projected</p>
          <p className="text-xl font-bold text-emerald-700">$1.5T</p>
          <p className="text-[10px] text-slate-400">+25% YoY</p>
        </div>
        <div className="glass-light p-3 text-center">
          <p className="text-xs text-slate-500">Greenium</p>
          <p className="text-xl font-bold text-emerald-700">3-5 bps</p>
          <p className="text-[10px] text-slate-400">Cost advantage</p>
        </div>
        <div className="glass-light p-3 text-center">
          <p className="text-xs text-slate-500">Portfolio Savings</p>
          <p className="text-xl font-bold text-emerald-700">$6-10M</p>
          <p className="text-[10px] text-slate-400">On $2B portfolio</p>
        </div>
      </div>

      <Card>
        <CardHeader title="EU Green Bond Standard (EUGBS)" subtitle="Effective January 2026 — Impact on Market" />
        <div className="px-6 pb-4 text-sm text-slate-600 space-y-2">
          <p>The EUGBS creates a standardized framework attracting institutional capital. Sovereign green bond issuance now accounts for <strong>35% of total supply</strong>.</p>
          <p>France, Germany, and Italy lead sovereign green issuance, with the EU itself planning €85B in green bonds for 2026.</p>
        </div>
      </Card>
    </div>
  );
}

function EMSection() {
  const emData = EM_LOCAL_YIELDS.map((e) => ({
    country: e.country,
    'Nominal Yield': e.yield10Y,
    'Real Yield': e.realYield,
    'Inflation': e.inflation }));

  const scatterData = EM_LOCAL_YIELDS.map((e) => ({
    name: e.country,
    risk: Math.abs(e.currentAccountPctGDP) + e.inflation * 0.5,
    return: e.realYield }));

  return (
    <div className="space-y-6">
      <GlassBarChart
        data={emData}
        xKey="country"
        yKeys={[
          { key: 'Nominal Yield', color: '#8b5cf6', name: 'Nominal 10Y Yield' },
          { key: 'Real Yield', color: '#10b981', name: 'Real Yield' },
        ]}
        title="EM Local Currency Bond Yields — 10Y Maturity"
        height={320}
        formatY={(v) => `${v.toFixed(1)}%`}
      />

      <Card>
        <CardHeader title="EM Yield Comparison Table" subtitle="Key metrics for EM local currency debt allocation" />
        <div className="px-6 pb-4">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/40">
                  <th className="text-left px-3 py-2 text-xs font-semibold text-slate-500 uppercase">Country</th>
                  <th className="text-left px-3 py-2 text-xs font-semibold text-slate-500 uppercase">Currency</th>
                  <th className="text-right px-3 py-2 text-xs font-semibold text-slate-500 uppercase">10Y Yield</th>
                  <th className="text-right px-3 py-2 text-xs font-semibold text-slate-500 uppercase">Inflation</th>
                  <th className="text-right px-3 py-2 text-xs font-semibold text-slate-500 uppercase">Real Yield</th>
                  <th className="text-right px-3 py-2 text-xs font-semibold text-slate-500 uppercase">CA % GDP</th>
                  <th className="text-center px-3 py-2 text-xs font-semibold text-slate-500 uppercase">Rating</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/25">
                {EM_LOCAL_YIELDS.map((e) => (
                  <tr key={e.country} className="hover:bg-white/30 transition-colors">
                    <td className="px-3 py-2.5 font-medium text-slate-900">{e.country}</td>
                    <td className="px-3 py-2.5 text-slate-600">{e.currency}</td>
                    <td className="px-3 py-2.5 text-right font-bold text-slate-900 tabular-nums">{e.yield10Y}%</td>
                    <td className="px-3 py-2.5 text-right text-slate-600 tabular-nums">{e.inflation}%</td>
                    <td className="px-3 py-2.5 text-right font-semibold text-emerald-700 tabular-nums">{e.realYield}%</td>
                    <td className={`px-3 py-2.5 text-right tabular-nums ${e.currentAccountPctGDP >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                      {e.currentAccountPctGDP > 0 ? '+' : ''}{e.currentAccountPctGDP}%
                    </td>
                    <td className="px-3 py-2.5 text-center">
                      <Badge variant={e.rating.startsWith('A') ? 'success' : e.rating.startsWith('BBB') ? 'info' : 'warning'} size="sm">
                        {e.rating}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </Card>

      <Card>
        <CardHeader title="EM Allocation Insights" subtitle="Currency risk and hedging considerations" />
        <div className="px-6 pb-4 text-sm text-slate-600 space-y-2">
          <p>JP Morgan GBI-EM Composite yield averages <strong>7.4%</strong> against developed market policy rates of 3.5–4.5%.</p>
          <p>Currency risk: A 5% FX depreciation negates ~40% of yield advantage. NDF hedging costs 150–250bps.</p>
          <p><strong>Recommended:</strong> Unhedged allocation of 5–10% with active FX management, focused on Mexico, Indonesia, and Brazil.</p>
        </div>
      </Card>
    </div>
  );
}

function RiskSection() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader title="Risk Assessment Matrix" subtitle="Key factors, probability, impact, and mitigation strategies" />
        <div className="px-6 pb-4">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/40">
                  <th className="text-left px-4 py-2 text-xs font-semibold text-slate-500 uppercase">Risk Factor</th>
                  <th className="text-center px-4 py-2 text-xs font-semibold text-slate-500 uppercase">Probability</th>
                  <th className="text-left px-4 py-2 text-xs font-semibold text-slate-500 uppercase">Impact</th>
                  <th className="text-left px-4 py-2 text-xs font-semibold text-slate-500 uppercase">Mitigation</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/25">
                {RISK_MATRIX.map((r) => (
                  <tr key={r.factor} className="hover:bg-white/30 transition-colors">
                    <td className="px-4 py-3 font-medium text-slate-900">{r.factor}</td>
                    <td className="px-4 py-3 text-center">
                      <Badge variant={r.probability === 'High' ? 'danger' : r.probability === 'Medium' ? 'warning' : 'info'}>
                        {r.probability}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{r.impact}</td>
                    <td className="px-4 py-3 text-slate-600">{r.mitigation}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </Card>

      <GlassHeatmap
        data={[
          { x: 'Inflation', y: 'Spread', value: 0.72 },
          { x: 'Inflation', y: 'Duration', value: 0.65 },
          { x: 'Inflation', y: 'FX', value: 0.35 },
          { x: 'Spread', y: 'Duration', value: 0.48 },
          { x: 'Spread', y: 'FX', value: 0.42 },
          { x: 'Duration', y: 'FX', value: 0.28 },
        ]}
        xLabels={['Inflation', 'Spread', 'Duration', 'FX']}
        yLabels={['Inflation', 'Spread', 'Duration', 'FX']}
        title="Risk Factor Correlation Matrix"
        height={240}
        formatValue={(v) => v.toFixed(2)}
      />
    </div>
  );
}

function AllocationSection() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader title="Recommended Portfolio Allocation" subtitle="Optimization targets for a $2B mid-market debt portfolio" />
        <div className="px-6 pb-4">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/40">
                  <th className="text-left px-4 py-2 text-xs font-semibold text-slate-500 uppercase">Metric</th>
                  <th className="text-center px-4 py-2 text-xs font-semibold text-slate-500 uppercase">Current</th>
                  <th className="text-center px-4 py-2 text-xs font-semibold text-slate-500 uppercase">Recommended</th>
                  <th className="text-center px-4 py-2 text-xs font-semibold text-slate-500 uppercase">Change</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/25">
                {ALLOCATION_TARGETS.map((a) => (
                  <tr key={a.metric} className="hover:bg-white/30 transition-colors">
                    <td className="px-4 py-3 font-medium text-slate-900">{a.metric}</td>
                    <td className="px-4 py-3 text-center text-slate-600 tabular-nums">{a.current}</td>
                    <td className="px-4 py-3 text-center font-bold text-slate-900 tabular-nums">{a.recommended}</td>
                    <td className="px-4 py-3 text-center">
                      <Badge variant="success" size="sm">Optimize</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </Card>

      <Card>
        <CardHeader title="Key Recommendations" subtitle="Actionable steps for portfolio optimization" />
        <div className="px-6 pb-4">
          <ol className="space-y-3">
            {KEY_RECOMMENDATIONS.map((rec, i) => (
              <li key={i} className="flex items-start gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-xs font-bold text-blue-700">
                  {i + 1}
                </span>
                <span className="text-sm text-slate-700 leading-relaxed">{rec}</span>
              </li>
            ))}
          </ol>
        </div>
      </Card>

      <GlassPieChart
        data={[
          { name: 'IG Corporates', value: 78, color: '#3b82f6' },
          { name: 'HY (BB-rated)', value: 12, color: '#f59e0b' },
          { name: 'Green Bonds', value: 12, color: '#10b981' },
          { name: 'EM Local', value: 7, color: '#8b5cf6' },
          { name: 'Cash/T-Bills', value: 5, color: '#94a3b8' },
        ]}
        title="Recommended Asset Allocation"
        height={320}
        showLegend={true}
      />

      <Card>
        <CardHeader title="Quantitative Impact" subtitle="Estimated annual savings on a $2B portfolio" />
        <div className="px-6 pb-4 grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="glass-light p-4 text-center">
            <p className="text-xs text-slate-500 mb-1">Coupon Optimization</p>
            <p className="text-2xl font-bold text-emerald-700">$8M</p>
            <p className="text-[10px] text-slate-400">4.8% → 4.4% WAC</p>
          </div>
          <div className="glass-light p-4 text-center">
            <p className="text-xs text-slate-500 mb-1">Green Bond Greenium</p>
            <p className="text-2xl font-bold text-emerald-700">$6-10M</p>
            <p className="text-[10px] text-slate-400">3-5bps on $240M allocation</p>
          </div>
          <div className="glass-light p-4 text-center">
            <p className="text-xs text-slate-500 mb-1">Duration Management</p>
            <p className="text-2xl font-bold text-emerald-700">$4M</p>
            <p className="text-[10px] text-slate-400">Reduced VaR + lower cost</p>
          </div>
        </div>
      </Card>
    </div>
  );
}

export default function MarketIntelligenceReport() {
  const [activeSection, setActiveSection] = useState<ReportSection>('summary');
  const [printMode, setPrintMode] = useState(false);

  const renderSection = () => {
    switch (activeSection) {
      case 'summary': return <ExecutiveSummarySection />;
      case 'rates': return <RatesSection />;
      case 'credit': return <CreditSection />;
      case 'green': return <GreenBondSection />;
      case 'em': return <EMSection />;
      case 'risk': return <RiskSection />;
      case 'allocation': return <AllocationSection />;
    }
  };

  return (
    <div className={printMode ? 'bg-white text-black' : ''}>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900">Global Fixed Income & Debt Markets</h2>
          <p className="text-xs text-slate-500 mt-0.5">Investment Outlook — August 2026 | Classification: For Institutional & Qualified Investors</p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => window.print()}
        >
          🖨️ Print / Export
        </Button>
      </div>
      <SectionNav active={activeSection} onChange={setActiveSection} />
      {renderSection()}
      <div className="mt-8 pt-4 border-t border-slate-200 text-[10px] text-slate-400">
        <p><strong>Disclaimer:</strong> This report is for informational purposes only and does not constitute investment advice. All data cited is from publicly available sources as of August 2026. Past performance is not indicative of future results.</p>
        <p className="mt-1"><strong>Sources:</strong> SIFMA, Bloomberg, Federal Reserve (H.15), BIS, CBO, Climate Bonds Initiative, Moody's, JP Morgan (GBI-EM), FactSet, IMF WEO.</p>
      </div>
    </div>
  );
}
