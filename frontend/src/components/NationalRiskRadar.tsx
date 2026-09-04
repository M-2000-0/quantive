import { useState, useEffect, useCallback } from 'react';
import Card, { CardHeader } from './ui/Card';
import Badge from './ui/Badge';
import Button from './ui/Button';

interface RiskAlert {
  id: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  description: string;
  historicalParallel: string;
  triggerCondition: string;
  confidence: number;
  detectedAt: string;
  category: 'liquidity' | 'refinancing' | 'fx' | 'rating' | 'geopolitical';
}

const MOCK_ALERTS: RiskAlert[] = [
  {
    id: 'ra1',
    severity: 'critical',
    title: 'Maturity Wall Concentration Detected',
    description: '28% of outstanding debt matures within 18 months. This concentration pattern is similar to Greece pre-2010, where a maturity wall of 32% contributed to the sovereign debt crisis.',
    historicalParallel: 'Greece 2010 — 32% maturity wall preceded debt crisis',
    triggerCondition: '>25% of debt maturing within 18 months',
    confidence: 92,
    detectedAt: '2026-08-27T08:30:00Z',
    category: 'refinancing' },
  {
    id: 'ra2',
    severity: 'high',
    title: 'FX Exposure Approaching Dangerous Threshold',
    description: 'Foreign currency denominated debt has reached 41% of total portfolio. Mexico experienced severe pressure when FX exposure exceeded 45% during the 1994 Peso Crisis.',
    historicalParallel: 'Mexico 1994 — 47% FX exposure preceded currency crisis',
    triggerCondition: '>35% foreign currency debt',
    confidence: 85,
    detectedAt: '2026-08-27T07:15:00Z',
    category: 'fx' },
  {
    id: 'ra3',
    severity: 'high',
    title: 'Floating Rate Exposure Amplifies Rate Risk',
    description: 'Floating rate instruments represent 33% of portfolio. During the 2022-2023 rate hiking cycle, countries with >30% floating exposure saw interest expenses increase by 40-60%.',
    historicalParallel: 'Global 2022-2023 — floating-heavy portfolios saw 45% cost increase',
    triggerCondition: '>30% floating rate instruments',
    confidence: 88,
    detectedAt: '2026-08-26T14:00:00Z',
    category: 'refinancing' },
  {
    id: 'ra4',
    severity: 'medium',
    title: 'Single Investor Concentration Risk',
    description: 'One institutional investor holds 18% of outstanding bonds. Argentina experienced liquidity freeze when major holders simultaneously reduced positions in 2001.',
    historicalParallel: 'Argentina 2001 — concentrated holdings led to forced sell-off',
    triggerCondition: '>15% held by single investor',
    confidence: 74,
    detectedAt: '2026-08-25T10:00:00Z',
    category: 'liquidity' },
  {
    id: 'ra5',
    severity: 'medium',
    title: 'Coupon Step-Up Coming Due',
    description: 'Three callable bonds with step-up provisions totaling $2.1B face value have call dates within 6 months. If not called, coupon rates increase by 75-150bps.',
    historicalParallel: 'Brazil 2015 — un-called step-ups added $800M to annual costs',
    triggerCondition: 'Callable bonds with step-ups approaching call date',
    confidence: 91,
    detectedAt: '2026-08-24T16:00:00Z',
    category: 'refinancing' },
  {
    id: 'ra6',
    severity: 'low',
    title: 'Rating Watch Negative Implied by Fiscal Trajectory',
    description: 'Current deficit-to-GDP trajectory of 4.2% combined with debt-to-GDP of 98% historically precedes rating outlook changes within 12-18 months.',
    historicalParallel: 'Italy 2011 — similar fiscal metrics preceded downgrade',
    triggerCondition: 'Deficit >3.5% with Debt/GDP >90%',
    confidence: 67,
    detectedAt: '2026-08-23T09:00:00Z',
    category: 'rating' },
];

const SEVERITY_CONFIG: Record<string, { label: string; color: string; bg: string; dot: string }> = {
  critical: { label: 'CRITICAL', color: 'text-red-700', bg: 'bg-red-500/12 border-red-500/20', dot: 'bg-red-500 animate-pulse' },
  high: { label: 'HIGH', color: 'text-orange-700', bg: 'bg-orange-500/12 border-orange-500/20', dot: 'bg-orange-500' },
  medium: { label: 'MEDIUM', color: 'text-amber-700', bg: 'bg-amber-500/12 border-amber-500/20', dot: 'bg-amber-500' },
  low: { label: 'LOW', color: 'text-blue-700', bg: 'bg-blue-500/12 border-blue-500/20', dot: 'bg-blue-500' } };

const CATEGORY_ICONS: Record<string, string> = {
  liquidity: '💧',
  refinancing: 'RefreshCw',
  fx: '💱',
  rating: '⭐',
  geopolitical: 'Globe' };

export default function NationalRiskRadar() {
  const [alerts, setAlerts] = useState<RiskAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('all');
  const [expanded, setExpanded] = useState<string | null>(null);

  const fetchAlerts = useCallback(async () => {
    setLoading(true);
    await new Promise((r) => setTimeout(r, 500));
    setAlerts(MOCK_ALERTS);
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  const filtered = filter === 'all' ? alerts : alerts.filter((a) => a.severity === filter);
  const criticalCount = alerts.filter((a) => a.severity === 'critical').length;
  const highCount = alerts.filter((a) => a.severity === 'high').length;

  return (
    <div className="space-y-6">
      {/* Severity summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card>
          <div className="p-4 text-center">
            <p className="text-2xl font-bold text-red-600">{criticalCount}</p>
            <p className="text-xs text-slate-500 mt-1">Critical Alerts</p>
          </div>
        </Card>
        <Card>
          <div className="p-4 text-center">
            <p className="text-2xl font-bold text-orange-600">{highCount}</p>
            <p className="text-xs text-slate-500 mt-1">High Alerts</p>
          </div>
        </Card>
        <Card>
          <div className="p-4 text-center">
            <p className="text-2xl font-bold text-amber-600">{alerts.filter((a) => a.severity === 'medium').length}</p>
            <p className="text-xs text-slate-500 mt-1">Medium Alerts</p>
          </div>
        </Card>
        <Card>
          <div className="p-4 text-center">
            <p className="text-2xl font-bold text-slate-900">{alerts.length}</p>
            <p className="text-xs text-slate-500 mt-1">Total Active</p>
          </div>
        </Card>
      </div>

      {/* Filter */}
      <div className="flex items-center gap-2">
        {['all', 'critical', 'high', 'medium', 'low'].map((sev) => (
          <button
            key={sev}
            onClick={() => setFilter(sev)}
            className={`px-3 py-1.5 text-xs font-medium rounded-full border backdrop-blur transition-all ${
              filter === sev
                ? 'bg-slate-900 text-white border-slate-900'
                : 'bg-white/60 text-slate-600 border-white/60 hover:bg-white/80'
            }`}
          >
            {sev === 'all' ? 'All Alerts' : sev.charAt(0).toUpperCase() + sev.slice(1)}
          </button>
        ))}
      </div>

      {/* Alerts */}
      <div className="space-y-4">
        {loading ? (
          <Card>
            <div className="p-12 text-center text-slate-400">Scanning risk patterns...</div>
          </Card>
        ) : filtered.length === 0 ? (
          <Card>
            <div className="p-12 text-center text-slate-400">No alerts for this severity level.</div>
          </Card>
        ) : (
          filtered.map((alert) => {
            const sev = SEVERITY_CONFIG[alert.severity];
            return (
              <Card key={alert.id} padding={false}>
                <div
                  className="px-6 py-5 cursor-pointer hover:bg-white/30 transition-colors"
                  onClick={() => setExpanded(expanded === alert.id ? null : alert.id)}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-start gap-3">
                      <span className="mt-0.5">{CATEGORY_ICONS[alert.category]}</span>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className={`w-2 h-2 rounded-full ${sev.dot}`} />
                          <h3 className="text-[15px] font-bold text-slate-900">{alert.title}</h3>
                        </div>
                        <p className="text-xs text-slate-500 mt-1">
                          Detected {new Date(alert.detectedAt).toLocaleString()} · {alert.confidence}% confidence
                        </p>
                      </div>
                    </div>
                    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[10px] font-bold border ${sev.bg} ${sev.color}`}>
                      {sev.label}
                    </span>
                  </div>

                  {expanded === alert.id && (
                    <div className="mt-4 pt-4 border-t border-white/40 space-y-3">
                      <p className="text-sm text-slate-700 leading-relaxed">{alert.description}</p>
                      <div className="bg-slate-50/80 rounded-xl p-4 space-y-2">
                        <div className="flex items-start gap-2">
                          <span className="text-xs font-bold text-slate-500 whitespace-nowrap">Historical Parallel:</span>
                          <span className="text-xs text-slate-700">{alert.historicalParallel}</span>
                        </div>
                        <div className="flex items-start gap-2">
                          <span className="text-xs font-bold text-slate-500 whitespace-nowrap">Trigger Condition:</span>
                          <span className="text-xs text-slate-700 font-mono">{alert.triggerCondition}</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </Card>
            );
          })
        )}
      </div>
    </div>
  );
}
