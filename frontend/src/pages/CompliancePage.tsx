import { useState, useEffect, useMemo } from 'react';
import { api } from '../api';

interface DSAResult {
  country_code: string;
  country_name: string;
  assessment_date: string;
  current_metrics: {
    public_debt_to_gdp: number;
    gross_financing_needs_to_gdp: number;
    debt_service_to_revenue: number;
    debt_service_to_exports: number;
  };
  projections: {
    horizon_years: number;
    debt_to_gdp: number[];
    growth: number[];
    primary_balance: number[];
    interest_rate: number[];
    inflation: number[];
  };
  fanchart: {
    median: number[];
    p75: number[];
    p95: number[];
  };
  risk_assessment: {
    overall: string;
    market_access: string;
    financing: string;
    rollover: string;
    interest_rate: string;
  };
  adjustment_needed_pct_gdp: number;
  recommendations: string[];
}

interface MTDSResult {
  country_code: string;
  country_name: string;
  horizon_years: number;
  targets: {
    debt_to_gdp: number;
    avg_maturity: number;
    domestic_share: number;
    fixed_rate_share: number;
    currency_mix: Record<string, number>;
  };
  annual_targets: Array<{
    year: number;
    target_debt_to_gdp: number;
    target_avg_maturity: number;
    target_issuance_bn: number;
    target_domestic_pct: number;
  }>;
  issuance_plan: {
    total_required: number;
    avg_target_coupon: number;
    recommended_issuances: Array<{
      tenor: string;
      currency: string;
      amount_bn: number;
      purpose: string;
    }>;
  };
}

const RISK_COLORS: Record<string, string> = {
  low: '#22c55e',
  moderate: '#eab308',
  high: '#ef4444',
  'in distress': '#dc2626',
};

const COUNTRIES = [
  { code: 'US', name: 'United States' },
  { code: 'GB', name: 'United Kingdom' },
  { code: 'JP', name: 'Japan' },
  { code: 'DE', name: 'Germany' },
  { code: 'FR', name: 'France' },
  { code: 'IT', name: 'Italy' },
  { code: 'CA', name: 'Canada' },
  { code: 'CN', name: 'China' },
  { code: 'IN', name: 'India' },
  { code: 'BR', name: 'Brazil' },
  { code: 'AU', name: 'Australia' },
  { code: 'KR', name: 'South Korea' },
  { code: 'MX', name: 'Mexico' },
  { code: 'ZA', name: 'South Africa' },
  { code: 'SA', name: 'Saudi Arabia' },
  { code: 'CH', name: 'Switzerland' },
  { code: 'SE', name: 'Sweden' },
  { code: 'NO', name: 'Norway' },
  { code: 'SG', name: 'Singapore' },
  { code: 'TR', name: 'Turkey' },
  { code: 'AR', name: 'Argentina' },
  { code: 'PL', name: 'Poland' },
  { code: 'NL', name: 'Netherlands' },
  { code: 'ES', name: 'Spain' },
];

// ── IMF DSA Thresholds ───────────────────────────────────────────────
const IMF_THRESHOLDS = {
  debtToGdp: 70, // %
  gfnToGdp: 15, // %
  debtServiceToRevenue: 25, // %
  debtServiceToExports: 20, // %
};

type ViolationLevel = 'ok' | 'amber' | 'red';

function checkViolation(value: number, threshold: number, amberPct = 0.8): { level: ViolationLevel; label: string } {
  if (value > threshold) return { level: 'red', label: 'BREACH' };
  if (value > threshold * amberPct) return { level: 'amber', label: 'WARNING' };
  return { level: 'ok', label: 'COMPLIANT' };
}

function GlassPill({ level, label }: { level: ViolationLevel; label: string }) {
  const styles = {
    red: 'bg-red-500/15 border-red-500/25 text-red-700',
    amber: 'bg-amber-500/15 border-amber-500/25 text-amber-700',
    ok: 'bg-emerald-500/12 border-emerald-500/20 text-emerald-700',
  } as const;
  const dot = { red: 'bg-red-600', amber: 'bg-amber-500', ok: 'bg-emerald-500' } as const;
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border backdrop-blur-md ${styles[level]}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dot[level]} ${level !== 'ok' ? 'animate-pulse' : ''}`} />
      {label}
    </span>
  );
}

export default function CompliancePage() {
  const [selectedCountry, setSelectedCountry] = useState('US');
  const [dsa, setDsa] = useState<DSAResult | null>(null);
  const [mtds, setMtds] = useState<MTDSResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<'dsa' | 'mtds'>('dsa');
  const [error, setError] = useState('');

  const loadReports = async () => {
    setLoading(true);
    setError('');
    try {
      const [dsaRes, mtdsRes] = await Promise.all([
        api.compliance.dsa(selectedCountry) as unknown as Promise<{ success: boolean; data: DSAResult }>,
        api.compliance.mtds(selectedCountry) as unknown as Promise<{ success: boolean; data: MTDSResult }>,
      ]);
      setDsa(dsaRes.data);
      setMtds(mtdsRes.data);
    } catch {
      setError('Failed to load compliance reports');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReports();
  }, [selectedCountry]);

  const riskBadge = (risk: string) => (
    <span
      className="inline-block px-2 py-1 rounded text-xs font-medium text-white"
      style={{ backgroundColor: RISK_COLORS[risk] || '#6b7280' }}
    >
      {risk.toUpperCase()}
    </span>
  );

  const years = dsa ? Array.from({ length: 5 }, (_, i) => new Date().getFullYear() + i + 1) : [];

  // IMF DSA auto-check computed
  const dsaViolations = useMemo(() => {
    if (!dsa) return null;
    const v = {
      debtToGdp: checkViolation(dsa.current_metrics.public_debt_to_gdp, IMF_THRESHOLDS.debtToGdp),
      gfn: checkViolation(dsa.current_metrics.gross_financing_needs_to_gdp, IMF_THRESHOLDS.gfnToGdp),
      dsRevenue: checkViolation(dsa.current_metrics.debt_service_to_revenue, IMF_THRESHOLDS.debtServiceToRevenue),
      dsExports: checkViolation(dsa.current_metrics.debt_service_to_exports, IMF_THRESHOLDS.debtServiceToExports),
    };
    const breached = Object.values(v).filter(x => x.level === 'red').length;
    const warnings = Object.values(v).filter(x => x.level === 'amber').length;
    const overall: ViolationLevel = breached > 0 ? 'red' : warnings > 0 ? 'amber' : 'ok';
    return { ...v, breached, warnings, overall };
  }, [dsa]);

  const exportReport = () => {
    if (!dsa && !mtds) return;
    const payload = {
      country: selectedCountry,
      generated_at: new Date().toISOString(),
      imf_thresholds: IMF_THRESHOLDS,
      dsa: dsa ? {
        country_name: dsa.country_name,
        current_metrics: dsa.current_metrics,
        violations: dsaViolations,
        risk_assessment: dsa.risk_assessment,
        projections: dsa.projections,
        adjustment_needed_pct_gdp: dsa.adjustment_needed_pct_gdp,
      } : null,
      mtds: mtds ? {
        targets: mtds.targets,
        annual_targets: mtds.annual_targets,
        issuance_plan: mtds.issuance_plan,
      } : null,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `IMF_Compliance_${selectedCountry}_${new Date().toISOString().slice(0,10)}.json`;
    a.click();
    URL.revokeObjectURL(url);

    // Also CSV export for current metrics
    if (dsa) {
      const csvRows = [
        ['Metric','Value','Threshold','Status'],
        ['Public Debt/GDP', `${dsa.current_metrics.public_debt_to_gdp}%`, `${IMF_THRESHOLDS.debtToGdp}%`, dsaViolations!.debtToGdp.label],
        ['GFN/GDP', `${dsa.current_metrics.gross_financing_needs_to_gdp}%`, `${IMF_THRESHOLDS.gfnToGdp}%`, dsaViolations!.gfn.label],
        ['Debt Service/Revenue', `${dsa.current_metrics.debt_service_to_revenue}%`, `${IMF_THRESHOLDS.debtServiceToRevenue}%`, dsaViolations!.dsRevenue.label],
        ['Debt Service/Exports', `${dsa.current_metrics.debt_service_to_exports}%`, `${IMF_THRESHOLDS.debtServiceToExports}%`, dsaViolations!.dsExports.label],
      ];
      const csv = csvRows.map(r => r.map(c => `"${c}"`).join(',')).join('\n');
      const blobCsv = new Blob([csv], { type: 'text/csv' });
      const urlCsv = URL.createObjectURL(blobCsv);
      const a2 = document.createElement('a');
      a2.href = urlCsv;
      a2.download = `IMF_DSA_metrics_${selectedCountry}.csv`;
      // trigger secondary download after short delay to avoid blocking
      setTimeout(() => { a2.click(); URL.revokeObjectURL(urlCsv); }, 300);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">IMF Compliance Dashboard</h1>
      <p className="text-gray-400 mb-6">
        Debt Sustainability Analysis, Medium-Term Debt Strategy, and Government Finance Statistics
        — IMF thresholds auto-checked. Debt/GDP &gt;70% and DS/service ratios flagged with glass pills.
      </p>

      {/* Country Selector */}
      <div className="flex items-center gap-4 mb-6 flex-wrap">
        <select
          value={selectedCountry}
          onChange={(e) => setSelectedCountry(e.target.value)}
          className="bg-gray-800 border border-gray-600 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-blue-500"
        >
          {COUNTRIES.map((c) => (
            <option key={c.code} value={c.code}>
              {c.name}
            </option>
          ))}
        </select>
        <button
          onClick={loadReports}
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg disabled:opacity-50"
        >
          {loading ? 'Generating...' : 'Regenerate Reports'}
        </button>
        <button
          onClick={exportReport}
          disabled={!dsa && !mtds}
          className="bg-white/10 backdrop-blur-md border border-white/20 hover:bg-white/15 text-white px-4 py-2 rounded-lg disabled:opacity-50 flex items-center gap-2"
        >
          <span>⤓</span> Export JSON + CSV
        </button>
        {dsaViolations && (
          <div className="flex items-center gap-2">
            <GlassPill level={dsaViolations.overall} label={dsaViolations.overall === 'red' ? `${dsaViolations.breached} BREACHES` : dsaViolations.overall === 'amber' ? `${dsaViolations.warnings} WARNINGS` : 'ALL COMPLIANT'} />
            <span className="text-xs text-gray-400">IMF DSA thresholds: Debt/GDP 70%, GFN 15%, DS/Rev 25%, DS/Exp 20%</span>
          </div>
        )}
      </div>

      {error && (
        <div className="bg-red-900/30 border border-red-500 rounded-lg p-4 mb-6 text-red-300">{error}</div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setTab('dsa')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            tab === 'dsa' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'
          }`}
        >
          Debt Sustainability Analysis
        </button>
        <button
          onClick={() => setTab('mtds')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            tab === 'mtds' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'
          }`}
        >
          Medium-Term Debt Strategy
        </button>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <span className="ml-3 text-gray-400">Generating compliance report...</span>
        </div>
      )}

      {/* DSA Tab */}
      {tab === 'dsa' && dsa && !loading && (
        <div className="space-y-6">
          {/* Auto-check banner */}
          {dsaViolations && (
            <div className={`rounded-xl p-4 backdrop-blur-xl border flex flex-wrap items-center gap-3 ${dsaViolations.overall === 'red' ? 'bg-red-500/10 border-red-500/20' : dsaViolations.overall === 'amber' ? 'bg-amber-500/10 border-amber-500/20' : 'bg-emerald-500/10 border-emerald-500/20'}`}>
              <span className={`w-2 h-2 rounded-full ${dsaViolations.overall === 'red' ? 'bg-red-600 animate-pulse' : dsaViolations.overall === 'amber' ? 'bg-amber-500 animate-pulse' : 'bg-emerald-500'}`} />
              <span className="text-sm font-bold" style={{ color: dsaViolations.overall === 'red' ? '#b91c1c' : dsaViolations.overall === 'amber' ? '#92400e' : '#166534' }}>
                IMF DSA AUTO-CHECK — {dsaViolations.overall === 'red' ? `${dsaViolations.breached} threshold(s) breached` : dsaViolations.overall === 'amber' ? `${dsaViolations.warnings} warning(s) — approaching threshold` : 'All thresholds compliant'}
              </span>
              <span className="text-xs text-gray-400">Debt/GDP 70% · GFN/GDP 15% · DS/Revenue 25% · DS/Exports 20% (IMF benchmarks)</span>
              <button onClick={exportReport} className="ml-auto text-xs px-3 py-1 rounded-full bg-white/80 border border-white/40 hover:bg-white text-slate-700 font-semibold">Export Report</button>
            </div>
          )}

          {/* Risk Assessment */}
          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">
              Risk Assessment — {dsa.country_name}
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {Object.entries(dsa.risk_assessment).map(([key, value]) => (
                <div key={key} className="text-center">
                  <div className="text-sm text-gray-400 mb-1">
                    {key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                  </div>
                  {riskBadge(value)}
                </div>
              ))}
            </div>
          </div>

          {/* Current Metrics with violation highlighting */}
          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Current Debt Metrics — IMF Thresholds Auto-Checked</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <div className={`text-center p-4 rounded-lg backdrop-blur-xl border ${dsaViolations?.debtToGdp.level === 'red' ? 'bg-red-500/10 border-red-500/20' : dsaViolations?.debtToGdp.level === 'amber' ? 'bg-amber-500/10 border-amber-500/20' : 'bg-gray-700/50 border-transparent'}`}>
                <div className={`text-3xl font-bold tabular-nums ${dsaViolations?.debtToGdp.level === 'red' ? 'text-red-400' : dsaViolations?.debtToGdp.level === 'amber' ? 'text-amber-400' : 'text-blue-400'}`}>
                  {dsa.current_metrics.public_debt_to_gdp}%
                </div>
                <div className="text-sm text-gray-400 mt-1">Public Debt / GDP</div>
                <div className="text-xs text-gray-500">Threshold 70%</div>
                <div className="mt-2 flex justify-center">
                  <GlassPill level={dsaViolations?.debtToGdp.level || 'ok'} label={dsaViolations?.debtToGdp.label || ''} />
                </div>
              </div>
              <div className={`text-center p-4 rounded-lg backdrop-blur-xl border ${dsaViolations?.gfn.level === 'red' ? 'bg-red-500/10 border-red-500/20' : dsaViolations?.gfn.level === 'amber' ? 'bg-amber-500/10 border-amber-500/20' : 'bg-gray-700/50 border-transparent'}`}>
                <div className={`text-3xl font-bold tabular-nums ${dsaViolations?.gfn.level === 'red' ? 'text-red-400' : dsaViolations?.gfn.level === 'amber' ? 'text-amber-400' : 'text-yellow-400'}`}>
                  {dsa.current_metrics.gross_financing_needs_to_gdp}%
                </div>
                <div className="text-sm text-gray-400 mt-1">GFN / GDP</div>
                <div className="text-xs text-gray-500">Threshold 15%</div>
                <div className="mt-2 flex justify-center">
                  <GlassPill level={dsaViolations?.gfn.level || 'ok'} label={dsaViolations?.gfn.label || ''} />
                </div>
              </div>
              <div className={`text-center p-4 rounded-lg backdrop-blur-xl border ${dsaViolations?.dsRevenue.level === 'red' ? 'bg-red-500/10 border-red-500/20' : dsaViolations?.dsRevenue.level === 'amber' ? 'bg-amber-500/10 border-amber-500/20' : 'bg-gray-700/50 border-transparent'}`}>
                <div className={`text-3xl font-bold tabular-nums ${dsaViolations?.dsRevenue.level === 'red' ? 'text-red-400' : dsaViolations?.dsRevenue.level === 'amber' ? 'text-amber-400' : 'text-orange-400'}`}>
                  {dsa.current_metrics.debt_service_to_revenue}%
                </div>
                <div className="text-sm text-gray-400 mt-1">Debt Service / Revenue</div>
                <div className="text-xs text-gray-500">Threshold 25% (DS/service)</div>
                <div className="mt-2 flex justify-center">
                  <GlassPill level={dsaViolations?.dsRevenue.level || 'ok'} label={dsaViolations?.dsRevenue.label || ''} />
                </div>
              </div>
              <div className={`text-center p-4 rounded-lg backdrop-blur-xl border ${dsaViolations?.dsExports.level === 'red' ? 'bg-red-500/10 border-red-500/20' : dsaViolations?.dsExports.level === 'amber' ? 'bg-amber-500/10 border-amber-500/20' : 'bg-gray-700/50 border-transparent'}`}>
                <div className={`text-3xl font-bold tabular-nums ${dsaViolations?.dsExports.level === 'red' ? 'text-red-400' : dsaViolations?.dsExports.level === 'amber' ? 'text-amber-400' : 'text-red-400'}`}>
                  {dsa.current_metrics.debt_service_to_exports}%
                </div>
                <div className="text-sm text-gray-400 mt-1">Debt Service / Exports</div>
                <div className="text-xs text-gray-500">Threshold 20%</div>
                <div className="mt-2 flex justify-center">
                  <GlassPill level={dsaViolations?.dsExports.level || 'ok'} label={dsaViolations?.dsExports.label || ''} />
                </div>
              </div>
            </div>
            {dsaViolations && dsaViolations.overall !== 'ok' && (
              <div className="mt-4 space-y-2">
                {dsaViolations.debtToGdp.level === 'red' && <div className="flex items-center gap-2 text-xs px-3 py-2 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300"><span className="w-1.5 h-1.5 bg-red-500 rounded-full" /> Debt/GDP {dsa.current_metrics.public_debt_to_gdp}% &gt; 70% IMF threshold — breach, requires corrective fiscal path</div>}
                {dsaViolations.debtToGdp.level === 'amber' && <div className="flex items-center gap-2 text-xs px-3 py-2 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300"><span className="w-1.5 h-1.5 bg-amber-500 rounded-full" /> Debt/GDP {dsa.current_metrics.public_debt_to_gdp}% approaching 70% — warning zone</div>}
                {dsaViolations.dsRevenue.level !== 'ok' && <div className={`flex items-center gap-2 text-xs px-3 py-2 rounded-xl border ${dsaViolations.dsRevenue.level==='red' ? 'bg-red-500/10 border-red-500/20 text-red-300' : 'bg-amber-500/10 border-amber-500/20 text-amber-300'}`}><span className={`w-1.5 h-1.5 rounded-full ${dsaViolations.dsRevenue.level==='red' ? 'bg-red-500' : 'bg-amber-500'}`} /> Debt service / revenue {dsa.current_metrics.debt_service_to_revenue}% {dsaViolations.dsRevenue.level==='red' ? '> 25% — breach' : 'approaching 25%'}</div>}
                {dsaViolations.dsExports.level !== 'ok' && <div className={`flex items-center gap-2 text-xs px-3 py-2 rounded-xl border ${dsaViolations.dsExports.level==='red' ? 'bg-red-500/10 border-red-500/20 text-red-300' : 'bg-amber-500/10 border-amber-500/20 text-amber-300'}`}><span className={`w-1.5 h-1.5 rounded-full ${dsaViolations.dsExports.level==='red' ? 'bg-red-500' : 'bg-amber-500'}`} /> Debt service / exports {dsa.current_metrics.debt_service_to_exports}% {dsaViolations.dsExports.level==='red' ? '> 20% — breach' : 'approaching 20%'}</div>}
              </div>
            )}
          </div>

          {/* 5-Year Debt Projections with breach highlighting */}
          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">5-Year Debt Projections — threshold 70% breach highlighted</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-700">
                    <th className="text-left py-2 text-gray-400">Year</th>
                    {dsa.projections.debt_to_gdp.map((_, i) => (
                      <th key={i} className="text-right py-2 text-gray-400">{years[i]}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b border-gray-700/50">
                    <td className="py-2 text-gray-300">Debt / GDP</td>
                    {dsa.projections.debt_to_gdp.map((v, i) => {
                      const lv = checkViolation(v, 70);
                      return (
                        <td key={i} className={`text-right py-2 font-mono ${lv.level==='red' ? 'text-red-400 font-bold' : lv.level==='amber' ? 'text-amber-400' : 'text-white'}`}>
                          <span className="inline-flex items-center gap-1">
                            {v.toFixed(1)}%
                            {lv.level !== 'ok' && <span className={`w-1.5 h-1.5 rounded-full ${lv.level==='red' ? 'bg-red-500' : 'bg-amber-500'}`} />}
                          </span>
                        </td>
                      );
                    })}
                  </tr>
                  <tr className="border-b border-gray-700/50">
                    <td className="py-2 text-gray-300">GDP Growth</td>
                    {dsa.projections.growth.map((v, i) => (
                      <td key={i} className="text-right py-2 font-mono text-green-400">{v.toFixed(1)}%</td>
                    ))}
                  </tr>
                  <tr className="border-b border-gray-700/50">
                    <td className="py-2 text-gray-300">Primary Balance</td>
                    {dsa.projections.primary_balance.map((v, i) => (
                      <td key={i} className={`text-right py-2 font-mono ${v >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {v >= 0 ? '+' : ''}{v.toFixed(1)}%
                      </td>
                    ))}
                  </tr>
                  <tr className="border-b border-gray-700/50">
                    <td className="py-2 text-gray-300">Interest Rate</td>
                    {dsa.projections.interest_rate.map((v, i) => (
                      <td key={i} className="text-right py-2 font-mono text-yellow-400">{v.toFixed(1)}%</td>
                    ))}
                  </tr>
                  <tr>
                    <td className="py-2 text-gray-300">Inflation</td>
                    {dsa.projections.inflation.map((v, i) => (
                      <td key={i} className="text-right py-2 font-mono text-purple-400">{v.toFixed(1)}%</td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
            <div className="mt-3 flex gap-2 text-xs">
              <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-red-500/10 border border-red-500/20 text-red-300 backdrop-blur-md">● &gt;70% breach</span>
              <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-300 backdrop-blur-md">● 56-70% warning</span>
              <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 backdrop-blur-md">● Compliant</span>
            </div>
          </div>

          {/* Fanchart */}
          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Debt Fanchart (Monte Carlo) — 70% threshold line</h2>
            <div className="relative h-64">
              <svg viewBox="0 0 500 200" className="w-full h-full">
                {/* 70% threshold line */}
                <line x1="40" y1={180 - (70/200)*160} x2="470" y2={180 - (70/200)*160} stroke="#f59e0b" strokeDasharray="6 4" strokeWidth="1.5" opacity="0.7" />
                <text x="475" y={180 - (70/200)*160 - 4} fill="#f59e0b" fontSize="9" fontWeight="bold">70% THR</text>
                {/* 95th percentile band */}
                {dsa.fanchart.p95.map((val, i) => {
                  const x = 50 + (i / 4) * 400;
                  const nextX = i < 4 ? 50 + ((i + 1) / 4) * 400 : x;
                  const y95 = 180 - (val / 200) * 160;
                  const y95n = i < 4 ? 180 - (dsa.fanchart.p95[i + 1] / 200) * 160 : y95;
                  return (
                    <rect
                      key={`p95-${i}`}
                      x={x}
                      y={Math.min(y95, y95n)}
                      width={nextX - x || 10}
                      height={Math.abs(y95 - y95n) || 2}
                      fill="rgba(239,68,68,0.1)"
                    />
                  );
                })}
                {/* 75th percentile band */}
                {dsa.fanchart.p75.map((val, i) => {
                  const x = 50 + (i / 4) * 400;
                  const nextX = i < 4 ? 50 + ((i + 1) / 4) * 400 : x;
                  const y75 = 180 - (val / 200) * 160;
                  const y75n = i < 4 ? 180 - (dsa.fanchart.p75[i + 1] / 200) * 160 : y75;
                  return (
                    <rect
                      key={`p75-${i}`}
                      x={x}
                      y={Math.min(y75, y75n)}
                      width={nextX - x || 10}
                      height={Math.abs(y75 - y75n) || 2}
                      fill="rgba(234,179,8,0.15)"
                    />
                  );
                })}
                {/* Median line */}
                <polyline
                  points={dsa.fanchart.median
                    .map((val, i) => `${50 + (i / 4) * 400},${180 - (val / 200) * 160}`)
                    .join(' ')}
                  fill="none"
                  stroke="#3b82f6"
                  strokeWidth="2.5"
                />
                {/* Labels */}
                {dsa.fanchart.median.map((val, i) => (
                  <g key={`label-${i}`}>
                    <circle cx={50 + (i / 4) * 400} cy={180 - (val / 200) * 160} r="4" fill="#3b82f6" />
                    <text
                      x={50 + (i / 4) * 400}
                      y={175 - (val / 200) * 160}
                      textAnchor="middle"
                      fill="#9ca3af"
                      fontSize="10"
                    >
                      {val.toFixed(1)}%
                    </text>
                  </g>
                ))}
                {/* Year labels */}
                {years.map((year, i) => (
                  <text
                    key={`year-${i}`}
                    x={50 + (i / 4) * 400}
                    y={198}
                    textAnchor="middle"
                    fill="#6b7280"
                    fontSize="11"
                  >
                    {year}
                  </text>
                ))}
              </svg>
              <div className="absolute top-2 right-2 flex gap-4 text-xs">
                <span className="flex items-center gap-1">
                  <span className="w-3 h-0.5 bg-blue-500 inline-block"></span> Median
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-3 h-3 bg-yellow-500/20 inline-block rounded"></span> P75
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-3 h-3 bg-red-500/10 inline-block rounded"></span> P95
                </span>
              </div>
            </div>
          </div>

          {/* Adjustments & Recommendations */}
          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">
              Fiscal Adjustment Needed
            </h2>
            <div className="text-center mb-4">
              <span className="text-4xl font-bold text-yellow-400">
                {dsa.adjustment_needed_pct_gdp > 0 ? '+' : ''}
                {dsa.adjustment_needed_pct_gdp}%
              </span>
              <div className="text-sm text-gray-400 mt-1">of GDP primary balance adjustment</div>
            </div>
            <h3 className="text-md font-semibold mb-2 text-gray-300">Recommendations</h3>
            <ul className="space-y-2">
              {dsa.recommendations.map((rec, i) => (
                <li key={i} className="flex items-start gap-2 text-gray-300">
                  <span className="text-blue-400 mt-0.5">→</span>
                  {rec}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* MTDS Tab */}
      {tab === 'mtds' && mtds && !loading && (
        <div className="space-y-6">
          {/* Strategy Targets */}
          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">
              5-Year Strategy Targets — {mtds.country_name}
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="text-center p-4 bg-gray-700/50 rounded-lg">
                <div className="text-2xl font-bold text-blue-400">{mtds.targets.debt_to_gdp}%</div>
                <div className="text-xs text-gray-400 mt-1">Target Debt/GDP</div>
                {checkViolation(mtds.targets.debt_to_gdp, 70).level !== 'ok' && (
                  <div className="mt-2"><GlassPill level={checkViolation(mtds.targets.debt_to_gdp, 70).level} label={checkViolation(mtds.targets.debt_to_gdp, 70).label} /></div>
                )}
              </div>
              <div className="text-center p-4 bg-gray-700/50 rounded-lg">
                <div className="text-2xl font-bold text-green-400">{mtds.targets.avg_maturity}Y</div>
                <div className="text-xs text-gray-400 mt-1">Target Maturity</div>
              </div>
              <div className="text-center p-4 bg-gray-700/50 rounded-lg">
                <div className="text-2xl font-bold text-purple-400">{mtds.targets.domestic_share}%</div>
                <div className="text-xs text-gray-400 mt-1">Domestic Share</div>
              </div>
              <div className="text-center p-4 bg-gray-700/50 rounded-lg">
                <div className="text-2xl font-bold text-yellow-400">{mtds.targets.fixed_rate_share}%</div>
                <div className="text-xs text-gray-400 mt-1">Fixed Rate</div>
              </div>
              <div className="text-center p-4 bg-gray-700/50 rounded-lg">
                <div className="text-2xl font-bold text-orange-400">{mtds.issuance_plan.total_required >= 1000 ? `$${(mtds.issuance_plan.total_required / 1000).toFixed(1)}T` : `$${mtds.issuance_plan.total_required.toFixed(0)}B`}</div>
                <div className="text-xs text-gray-400 mt-1">Total Issuance</div>
              </div>
            </div>
          </div>

          {/* Annual Targets */}
          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Annual Targets</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-700">
                    <th className="text-left py-2 text-gray-400">Year</th>
                    <th className="text-right py-2 text-gray-400">Debt/GDP</th>
                    <th className="text-right py-2 text-gray-400">Avg Maturity</th>
                    <th className="text-right py-2 text-gray-400">Issuance</th>
                    <th className="text-right py-2 text-gray-400">Domestic %</th>
                  </tr>
                </thead>
                <tbody>
                  {mtds.annual_targets.map((t) => {
                    const lv = checkViolation(t.target_debt_to_gdp, 70);
                    return (
                      <tr key={t.year} className="border-b border-gray-700/50">
                        <td className="py-2 font-medium text-white">{t.year}</td>
                        <td className={`text-right py-2 font-mono ${lv.level==='red' ? 'text-red-400' : lv.level==='amber' ? 'text-amber-400' : 'text-blue-400'}`}>{t.target_debt_to_gdp}% {lv.level!=='ok' && `(${lv.label})`}</td>
                        <td className="text-right py-2 font-mono text-green-400">{t.target_avg_maturity}Y</td>
                        <td className="text-right py-2 font-mono text-yellow-400">${t.target_issuance_bn}B</td>
                        <td className="text-right py-2 font-mono text-purple-400">{t.target_domestic_pct}%</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Recommended Issuances */}
          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Recommended Issuances</h2>
            <div className="space-y-3">
              {mtds.issuance_plan.recommended_issuances.map((iss, i) => (
                <div key={i} className="flex items-center justify-between bg-gray-700/50 rounded-lg p-4">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-blue-600/20 rounded-lg flex items-center justify-center text-blue-400 font-bold text-sm">
                      {iss.tenor}
                    </div>
                    <div>
                      <div className="font-medium text-white">{iss.currency} {iss.tenor} Bond</div>
                      <div className="text-sm text-gray-400">{iss.purpose}</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-bold text-white">${iss.amount_bn >= 1000 ? `${(iss.amount_bn / 1000).toFixed(1)}T` : `${iss.amount_bn.toFixed(0)}B`}</div>
                    <div className="text-xs text-gray-400">
                      Target coupon: {mtds.issuance_plan.avg_target_coupon.toFixed(2)}%
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Currency Mix */}
          <div className="bg-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Target Currency Mix</h2>
            <div className="flex gap-2 h-8 rounded-lg overflow-hidden">
              {Object.entries(mtds.targets.currency_mix).map(([ccy, pct], i) => {
                const colors = ['#3b82f6', '#22c55e', '#eab308', '#ef4444', '#a855f7'];
                return (
                  <div
                    key={ccy}
                    className="flex items-center justify-center text-xs font-medium text-white"
                    style={{ width: `${pct}%`, backgroundColor: colors[i % colors.length] }}
                    title={`${ccy}: ${pct.toFixed(1)}%`}
                  >
                    {pct > 10 ? `${ccy} ${pct.toFixed(0)}%` : ''}
                  </div>
                );
              })}
            </div>
            <div className="flex gap-4 mt-3 flex-wrap">
              {Object.entries(mtds.targets.currency_mix).map(([ccy, pct], i) => {
                const colors = ['#3b82f6', '#22c55e', '#eab308', '#ef4444', '#a855f7'];
                return (
                  <div key={ccy} className="flex items-center gap-2 text-sm text-gray-300">
                    <span className="w-3 h-3 rounded" style={{ backgroundColor: colors[i % colors.length] }}></span>
                    {ccy}: {pct.toFixed(1)}%
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
