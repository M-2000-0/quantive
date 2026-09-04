import { useState, useEffect, useCallback } from 'react';
import Card, { CardHeader } from './ui/Card';
import Badge from './ui/Badge';

interface Decision {
  id: string;
  title: string;
  date: string;
  decisionMaker: string;
  role: string;
  type: 'issuance' | 'refinancing' | 'hedging' | 'policy' | 'emergency';
  status: 'successful' | 'mixed' | 'underperforming' | 'pending';
  summary: string;
  assumptions: string[];
  alternatives: string[];
  outcome: string;
  marketConditions: string;
  portfolioSnapshot: { totalDebt: string; avgMaturity: string; avgCoupon: string };
}

const MOCK_DECISIONS: Decision[] = [
  {
    id: 'd1', title: '$15B 20-Year Bond Issuance', date: '2025-03-15',
    decisionMaker: 'Maria Chen', role: 'Deputy Minister', type: 'issuance',
    status: 'successful', summary: 'Issued $15B in 20-year bonds at 4.82% coupon during favorable market window.',
    assumptions: ['Fed pauses rate hikes', 'Inflation moderates to 2.5%', 'Demand for long-end paper remains strong'],
    alternatives: ['$10B 10-year at 4.45%', '$12B 30-year at 5.15%', '$8B FRN at SOFR+85bps'],
    outcome: 'Saved 23bps vs. alternative timing. 1.8x oversubscribed. Reduced refinancing wall by $8B.',
    marketConditions: '10Y at 4.65%, VIX at 14, credit spreads tight',
    portfolioSnapshot: { totalDebt: '$285B', avgMaturity: '6.2yr', avgCoupon: '4.71%' } },
  {
    id: 'd2', title: 'FX Hedge Program Expansion', date: '2025-06-22',
    decisionMaker: 'James Okafor', role: 'Treasury Director', type: 'hedging',
    status: 'mixed', summary: 'Expanded FX hedging from 40% to 65% of foreign currency exposure via 3-year NDFs.',
    assumptions: ['USD strengthens against EM currencies', 'EUR/USD remains above 1.05', 'Hedging costs stay below 120bps'],
    alternatives: ['Maintain 40% hedge ratio', 'Hedge to 80% via options', 'Natural hedge via revenue matching'],
    outcome: 'Hedged portion protected against 8% EM depreciation. Unhedged 35% lost value. Net benefit marginal.',
    marketConditions: 'EUR/USD at 1.08, EM currencies weakening, NDF costs at 95bps',
    portfolioSnapshot: { totalDebt: '$285B', avgMaturity: '6.4yr', avgCoupon: '4.68%' } },
  {
    id: 'd3', title: 'Green Bond Framework Adoption', date: '2025-09-10',
    decisionMaker: 'Sarah Mueller', role: 'Director of Sustainability', type: 'policy',
    status: 'successful', summary: 'Adopted ICMA Green Bond Principles framework for $5B inaugural green bond issuance.',
    assumptions: ['ESG fund flows continue growing', 'Greenium remains above 5bps', 'Verification costs stay below 0.1%'],
    alternatives: ['Social bond framework', 'Sustainability-linked bond', 'Conventional issuance'],
    outcome: 'Achieved 7bps greenium. Unlocked $12B in ESG-dedicated investor demand. Improved sovereign ESG score by 12 points.',
    marketConditions: 'ESG AUM at $35T, green bond issuance record, investor demand strong',
    portfolioSnapshot: { totalDebt: '$290B', avgMaturity: '6.5yr', avgCoupon: '4.65%' } },
];

const TYPE_CONFIG: Record<string, { label: string; icon: string; color: string }> = {
  issuance: { label: 'Issuance', icon: 'FileText', color: 'text-blue-700 bg-blue-500/12 border-blue-500/20' },
  refinancing: { label: 'Refinancing', icon: 'RefreshCw', color: 'text-emerald-700 bg-emerald-500/12 border-emerald-500/20' },
  hedging: { label: 'Hedging', icon: '💱', color: 'text-amber-700 bg-amber-500/12 border-amber-500/20' },
  policy: { label: 'Policy', icon: 'Building2', color: 'text-violet-700 bg-violet-500/12 border-violet-500/20' },
  emergency: { label: 'Emergency', icon: '🚨', color: 'text-red-700 bg-red-500/12 border-red-500/20' } };

const STATUS_CONFIG: Record<string, { label: string; variant: string }> = {
  successful: { label: 'Successful', variant: 'success' },
  mixed: { label: 'Mixed Results', variant: 'warning' },
  underperforming: { label: 'Underperforming', variant: 'danger' },
  pending: { label: 'Pending', variant: 'info' } };

export default function NationalDecisionArchive() {
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    setTimeout(() => { setDecisions(MOCK_DECISIONS); setLoading(false); }, 400);
  }, []);

  const filtered = filter === 'all' ? decisions : decisions.filter((d) => d.type === filter);

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card><div className="p-4 text-center"><p className="text-2xl font-bold text-slate-900">{decisions.length}</p><p className="text-xs text-slate-500">Decisions Archived</p></div></Card>
        <Card><div className="p-4 text-center"><p className="text-2xl font-bold text-emerald-600">{decisions.filter((d) => d.status === 'successful').length}</p><p className="text-xs text-slate-500">Successful</p></div></Card>
        <Card><div className="p-4 text-center"><p className="text-2xl font-bold text-amber-600">{decisions.filter((d) => d.status === 'mixed').length}</p><p className="text-xs text-slate-500">Mixed Results</p></div></Card>
        <Card><div className="p-4 text-center"><p className="text-2xl font-bold text-violet-600">25yr</p><p className="text-xs text-slate-500">Retention Guarantee</p></div></Card>
      </div>

      {/* Filter */}
      <div className="flex items-center gap-2 flex-wrap">
        {['all', 'issuance', 'refinancing', 'hedging', 'policy', 'emergency'].map((t) => (
          <button key={t} onClick={() => setFilter(t)} className={`px-3 py-1.5 text-xs font-medium rounded-full border backdrop-blur transition-all ${filter === t ? 'bg-slate-900 text-white border-slate-900' : 'bg-white/60 text-slate-600 border-white/60 hover:bg-white/80'}`}>
            {t === 'all' ? 'All' : TYPE_CONFIG[t]?.icon + ' ' + TYPE_CONFIG[t]?.label}
          </button>
        ))}
      </div>

      {/* Decisions */}
      <div className="space-y-4">
        {loading ? <Card><div className="p-12 text-center text-slate-400">Loading decision archive...</div></Card> :
          filtered.map((d) => {
            const type = TYPE_CONFIG[d.type];
            const status = STATUS_CONFIG[d.status];
            return (
              <Card key={d.id} padding={false}>
                <div className="px-6 py-5 cursor-pointer hover:bg-white/30 transition-colors" onClick={() => setExpanded(expanded === d.id ? null : d.id)}>
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-start gap-3">
                      <span className="text-lg">{type?.icon}</span>
                      <div>
                        <h3 className="text-[15px] font-bold text-slate-900">{d.title}</h3>
                        <p className="text-xs text-slate-500 mt-0.5">{d.decisionMaker} · {d.role} · {new Date(d.date).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={status.variant as 'success' | 'warning' | 'danger' | 'info'}>{status.label}</Badge>
                      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold border ${type?.color}`}>{type?.label}</span>
                    </div>
                  </div>
                  <p className="text-sm text-slate-600 mt-2">{d.summary}</p>

                  {expanded === d.id && (
                    <div className="mt-4 pt-4 border-t border-white/40 space-y-4">
                      {/* Market conditions */}
                      <div className="bg-slate-50/80 rounded-xl p-4">
                        <p className="text-[10px] font-bold text-slate-400 uppercase mb-1">Market Conditions at Decision</p>
                        <p className="text-sm text-slate-700">{d.marketConditions}</p>
                      </div>
                      {/* Portfolio snapshot */}
                      <div className="grid grid-cols-3 gap-3">
                        {Object.entries(d.portfolioSnapshot).map(([k, v]) => (
                          <div key={k} className="bg-white/60 rounded-xl p-3 text-center">
                            <p className="text-[10px] uppercase text-slate-400">{k.replace(/([A-Z])/g, ' $1')}</p>
                            <p className="text-sm font-bold text-slate-900">{v}</p>
                          </div>
                        ))}
                      </div>
                      {/* Assumptions */}
                      <div>
                        <p className="text-[10px] font-bold text-slate-400 uppercase mb-2">Assumptions</p>
                        <div className="space-y-1">{d.assumptions.map((a, i) => <div key={i} className="text-xs text-slate-600 flex items-start gap-2"><span className="text-slate-400">•</span>{a}</div>)}</div>
                      </div>
                      {/* Alternatives */}
                      <div>
                        <p className="text-[10px] font-bold text-slate-400 uppercase mb-2">Alternatives Considered</p>
                        <div className="space-y-1">{d.alternatives.map((a, i) => <div key={i} className="text-xs text-slate-600 flex items-start gap-2"><span className="text-slate-400">→</span>{a}</div>)}</div>
                      </div>
                      {/* Outcome */}
                      <div className="bg-emerald-50/80 rounded-xl p-4">
                        <p className="text-[10px] font-bold text-emerald-600 uppercase mb-1">Outcome</p>
                        <p className="text-sm text-emerald-800">{d.outcome}</p>
                      </div>
                    </div>
                  )}
                </div>
              </Card>
            );
          })
        }
      </div>
    </div>
  );
}
