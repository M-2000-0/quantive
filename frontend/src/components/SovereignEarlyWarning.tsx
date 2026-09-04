import { useState } from 'react';
import Card, { CardHeader } from './ui/Card';
import Badge from './ui/Badge';
import { FileText } from 'lucide-react';

interface Warning {
  id: string;
  title: string;
  description: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  category: 'liquidity' | 'debt_cliff' | 'refinancing' | 'fx' | 'revenue';
  probability: number;
  timeframe: string;
  leadTime: string;
  triggerMetrics: string[];
  historicalPrecedents: string[];
}

const WARNINGS: Warning[] = [
  {
    id: 'w1', title: 'Liquidity Crunch Risk in 6 Months',
    description: 'Based on current cash flow projections and upcoming maturities, government liquidity could fall below the 3-month import cover threshold by Q2 2027.',
    severity: 'critical', category: 'liquidity', probability: 78, timeframe: '6 months', leadTime: '6-12 months',
    triggerMetrics: ['Cash reserves declining 8% QoQ', 'Tax revenue shortfall of 12%', 'Upcoming $8.3B maturity wall'],
    historicalPrecedents: ['Sri Lanka 2022 — liquidity fell below 3-month cover 8 months before default', 'Pakistan 2019 — similar trajectory led to IMF program'] },
  {
    id: 'w2', title: 'Debt Cliff Approaching in 18 Months',
    description: 'A maturity wall of $32B (28% of outstanding debt) is approaching in 18-24 months. Without proactive refinancing, refinancing risk could spike.',
    severity: 'high', category: 'debt_cliff', probability: 85, timeframe: '18 months', leadTime: '12-18 months',
    triggerMetrics: ['28% of debt maturing within 18 months', 'Average tenor declining', 'No new issuance plan on file'],
    historicalPrecedents: ['Greece 2010 — 32% maturity wall preceded crisis', 'Argentina 2001 — concentrated maturities overwhelmed market access'] },
  {
    id: 'w3', title: 'FX Exposure Breach Warning',
    description: 'Foreign currency debt is on track to exceed the 45% policy threshold within 3 quarters if current borrowing patterns continue.',
    severity: 'high', category: 'fx', probability: 72, timeframe: '9 months', leadTime: '6-9 months',
    triggerMetrics: ['FX debt at 41% (threshold: 45%)', 'USD strength accelerating', 'EM currencies weakening'],
    historicalPrecedents: ['Mexico 1994 — FX exposure at 47% preceded peso crisis', 'Turkey 2018 — FX debt concentration amplified lira collapse'] },
  {
    id: 'w4', title: 'Revenue Shortfall Forecast',
    description: 'Tax revenue collections are tracking 8% below budget projections. If sustained, this could widen the fiscal deficit beyond the 4% threshold.',
    severity: 'medium', category: 'revenue', probability: 65, timeframe: '12 months', leadTime: '9-15 months',
    triggerMetrics: ['Tax revenue -8% vs budget', 'VAT collections declining', 'Corporate tax receipts flat'],
    historicalPrecedents: ['Brazil 2015 — revenue shortfall widened deficit and triggered downgrade', 'South Africa 2020 — revenue collapse preceded fiscal crisis'] },
  {
    id: 'w5', title: 'Refinancing Spike Concentration',
    description: 'Three major bond maturities totaling $12B fall within the same 3-month window. Without staggering, this creates a concentrated refinancing event.',
    severity: 'medium', category: 'refinancing', probability: 90, timeframe: '14 months', leadTime: '12-18 months',
    triggerMetrics: ['$12B maturing in Q3 2027', 'No partial call options available', 'Market conditions uncertain'],
    historicalPrecedents: ['Italy 2011 — concentrated maturities amplified contagion', 'Portugal 2012 — refinancing wall contributed to bailout'] },
];

const SEVERITY_CONFIG: Record<string, { label: string; color: string; bg: string; dot: string }> = {
  critical: { label: 'CRITICAL', color: 'text-red-700', bg: 'bg-red-500/12 border-red-500/20', dot: 'bg-red-500 animate-pulse' },
  high: { label: 'HIGH', color: 'text-orange-700', bg: 'bg-orange-500/12 border-orange-500/20', dot: 'bg-orange-500' },
  medium: { label: 'MEDIUM', color: 'text-amber-700', bg: 'bg-amber-500/12 border-amber-500/20', dot: 'bg-amber-500' },
  low: { label: 'LOW', color: 'text-blue-700', bg: 'bg-blue-500/12 border-blue-500/20', dot: 'bg-blue-500' } };

export default function SovereignEarlyWarning() {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>('all');

  const filtered = filter === 'all' ? WARNINGS : WARNINGS.filter((w) => w.severity === filter);

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card><div className="p-4 text-center"><p className="text-2xl font-bold text-red-600">{WARNINGS.filter((w) => w.severity === 'critical').length}</p><p className="text-xs text-slate-500">Critical</p></div></Card>
        <Card><div className="p-4 text-center"><p className="text-2xl font-bold text-orange-600">{WARNINGS.filter((w) => w.severity === 'high').length}</p><p className="text-xs text-slate-500">High</p></div></Card>
        <Card><div className="p-4 text-center"><p className="text-2xl font-bold text-amber-600">{WARNINGS.filter((w) => w.severity === 'medium').length}</p><p className="text-xs text-slate-500">Medium</p></div></Card>
        <Card><div className="p-4 text-center"><p className="text-2xl font-bold text-blue-600">{WARNINGS.filter((w) => w.severity === 'low').length}</p><p className="text-xs text-slate-500">Low</p></div></Card>
      </div>

      {/* Filter */}
      <div className="flex items-center gap-2">
        {['all', 'critical', 'high', 'medium', 'low'].map((sev) => (
          <button key={sev} onClick={() => setFilter(sev)} className={`px-3 py-1.5 text-xs font-medium rounded-full border backdrop-blur transition-all ${filter === sev ? 'bg-slate-900 text-white border-slate-900' : 'bg-white/60 text-slate-600 border-white/60 hover:bg-white/80'}`}>
            {sev === 'all' ? 'All Warnings' : sev.charAt(0).toUpperCase() + sev.slice(1)}
          </button>
        ))}
      </div>

      {/* Warnings */}
      <div className="space-y-4">
        {filtered.map((w) => {
          const sev = SEVERITY_CONFIG[w.severity];
          return (
            <Card key={w.id} padding={false}>
              <div className="px-6 py-5 cursor-pointer hover:bg-white/30 transition-colors" onClick={() => setExpanded(expanded === w.id ? null : w.id)}>
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-start gap-3">
                    <span className={`w-2.5 h-2.5 rounded-full mt-1.5 ${sev.dot}`} />
                    <div>
                      <h3 className="text-[15px] font-bold text-slate-900">{w.title}</h3>
                      <p className="text-xs text-slate-500 mt-0.5">Timeframe: {w.timeframe} · Lead time: {w.leadTime}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={w.probability >= 80 ? 'danger' : w.probability >= 65 ? 'warning' : 'info'}>{w.probability}% probability</Badge>
                    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold border ${sev.bg} ${sev.color}`}>{sev.label}</span>
                  </div>
                </div>
                <p className="text-sm text-slate-600 mt-2">{w.description}</p>

                {expanded === w.id && (
                  <div className="mt-4 pt-4 border-t border-white/40 space-y-4">
                    <div>
                      <p className="text-[10px] font-bold text-slate-400 uppercase mb-2">Trigger Metrics</p>
                      <div className="space-y-1">{w.triggerMetrics.map((m, i) => <div key={i} className="text-xs text-slate-600 flex items-start gap-2"><span className="text-amber-500">⚠</span>{m}</div>)}</div>
                    </div>
                    <div>
                      <p className="text-[10px] font-bold text-slate-400 uppercase mb-2">Historical Precedents</p>
                      <div className="space-y-1">{w.historicalPrecedents.map((p, i) => <div key={i} className="text-xs text-slate-600 flex items-start gap-2"><FileText className="w-5 h-5" />{p}</div>)}</div>
                    </div>
                  </div>
                )}
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
