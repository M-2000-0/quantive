import { useState, useMemo } from 'react';
import { api } from '../api';

type Tab = 'sanctions' | 'liquidity' | 'political' | 'contagion';

const TABS: { key: Tab; label: string; icon: string }[] = [
  { key: 'sanctions', label: 'Sanctions Screening', icon: '🚫' },
  { key: 'liquidity', label: 'Liquidity Risk', icon: '💧' },
  { key: 'political', label: 'Political Risk', icon: '🏛️' },
  { key: 'contagion', label: 'Contagion Risk', icon: '🌐' },
];

const DEMO_INSTRUMENTS = [
  { id: 'T1', issuer_name: 'US Treasury 10Y', issuer_country: 'US', currency: 'USD', instrument_type: 'treasury_bond', principal_outstanding: 5_000_000_000, coupon_rate: 4.25, maturity_date: '2034-06-15' },
  { id: 'T2', issuer_name: 'UK Gilt 5Y', issuer_country: 'GB', currency: 'GBP', instrument_type: 'treasury_bond', principal_outstanding: 3_000_000_000, coupon_rate: 3.8, maturity_date: '2029-09-07' },
  { id: 'E1', issuer_name: 'Brazil 5Y Eurobond', issuer_country: 'BR', currency: 'USD', instrument_type: 'eurobond', principal_outstanding: 2_000_000_000, coupon_rate: 6.5, maturity_date: '2029-03-15' },
  { id: 'E2', issuer_name: 'South Africa 7Y', issuer_country: 'ZA', currency: 'ZAR', instrument_type: 'eurobond', principal_outstanding: 1_500_000_000, coupon_rate: 8.25, maturity_date: '2031-09-15' },
  { id: 'F1', issuer_name: 'Turkey FRN', issuer_country: 'TR', currency: 'USD', instrument_type: 'floating_rate_note', principal_outstanding: 1_000_000_000, coupon_rate: 7.5, maturity_date: '2027-06-15' },
  { id: 'S1', issuer_name: 'Japan Samurai Bond', issuer_country: 'JP', currency: 'JPY', instrument_type: 'samurai_bond', principal_outstanding: 500_000_000, coupon_rate: 1.2, maturity_date: '2030-12-01' },
];

const SEVERITY_COLORS: Record<string, string> = {
  blocked: '#ef4444', restricted: '#f97316', advisory: '#eab308', clear: '#22c55e',
  low: '#22c55e', moderate: '#eab308', elevated: '#f97316', high: '#ef4444', critical: '#dc2626',
  tier1: '#22c55e', tier2: '#eab308', tier3: '#f97316', illiquid: '#ef4444',
};

function SeverityBadge({ level }: { level: string }) {
  return (
    <span className="inline-block px-2 py-1 rounded text-xs font-bold text-white" style={{ backgroundColor: SEVERITY_COLORS[level] || '#6b7280' }}>
      {level.toUpperCase()}
    </span>
  );
}

function ScoreBar({ score, max = 100, color }: { score: number; max?: number; color?: string }) {
  const pct = Math.min(100, (score / max) * 100);
  const barColor = color || (pct > 70 ? '#ef4444' : pct > 40 ? '#eab308' : '#22c55e');
  return (
    <div className="h-3 bg-gray-700 rounded-full overflow-hidden">
      <div className="h-full rounded-full transition-all duration-700" style={{ width: `${pct}%`, backgroundColor: barColor }} />
    </div>
  );
}

// ── New: Scenario-Weighted VaR, Regime Detection, Early-Warning Signals ──
type Regime = 'calm' | 'stressed' | 'risk-off' | 'crisis';

function detectRegime(impactSummary: Record<string, unknown> | null): { regime: Regime; label: string; color: string; description: string } {
  if (!impactSummary) return { regime: 'calm', label: 'Calm', color: '#22c55e', description: 'No stress detected — run analysis' };
  const spread = (impactSummary.spread_increase_pct as number) || 0;
  const volDrop = (impactSummary.volume_decrease_pct as number) || 0;
  const days = (impactSummary.days_to_liquidate_under_stress as number) || 0;
  const score = spread * 0.5 + volDrop * 0.3 + days * 2;
  if (score >= 80 || spread >= 60) return { regime: 'crisis', label: 'Crisis', color: '#dc2626', description: 'Extreme dislocation — bid/ask blowout, liquidity vacuum' };
  if (score >= 45 || spread >= 35) return { regime: 'risk-off', label: 'Risk-Off', color: '#ef4444', description: 'Broad de-risking — EM and high-yield under pressure' };
  if (score >= 20 || spread >= 15) return { regime: 'stressed', label: 'Stressed', color: '#f59e0b', description: 'Elevated volatility — spreads widening, volumes thinning' };
  return { regime: 'calm', label: 'Calm', color: '#22c55e', description: 'Normal market functioning — ample liquidity' };
}

function computeScenarioWeightedVaR(scenarios: Array<{ return_pct: number; probability: number }>): { weightedVaR95: number; weightedVaR99: number; expectedShortfall: number; tailProb: number } {
  if (scenarios.length === 0) return { weightedVaR95: 0, weightedVaR99: 0, expectedShortfall: 0, tailProb: 0 };
  const sorted = [...scenarios].sort((a, b) => a.return_pct - b.return_pct);
  // weighted quantile: find return where cumulative prob >= 1 - confidence
  const cumulative = (threshold: number) => {
    let cum = 0;
    for (const s of sorted) {
      cum += s.probability;
      if (cum >= 1 - threshold) return s.return_pct;
    }
    return sorted[0].return_pct;
  };
  const var95 = cumulative(0.95);
  const var99 = cumulative(0.99);
  // scenario-weighted expected loss (probability-weighted negative returns)
  const expectedShortfall = sorted.filter(s => s.return_pct <= var95).reduce((acc, s) => acc + (-s.return_pct / 100) * s.probability * 100, 0);
  const tailProb = sorted.filter(s => s.return_pct <= var99).reduce((a, s) => a + s.probability, 0);
  return { weightedVaR95: var95, weightedVaR99: var99, expectedShortfall, tailProb };
}

function EarlyWarningSignals({ impactSummary }: { impactSummary: Record<string, unknown> | null }) {
  const signals = useMemo(() => {
    if (!impactSummary) return [];
    const list: Array<{ level: 'amber' | 'red' | 'green'; label: string; detail: string }> = [];
    const spread = (impactSummary.spread_increase_pct as number) || 0;
    const volDrop = (impactSummary.volume_decrease_pct as number) || 0;
    const cost = (impactSummary.estimated_trading_cost_usd as number) || 0;
    const days = (impactSummary.days_to_liquidate_under_stress as number) || 0;
    if (spread > 40) list.push({ level: 'red', label: 'Spread Blowout', detail: `+${spread}% spread vs normal — execution slippage high` });
    else if (spread > 15) list.push({ level: 'amber', label: 'Widening Spreads', detail: `+${spread}% — monitor dealer inventory` });
    else list.push({ level: 'green', label: 'Spreads Stable', detail: `+${spread}% — within normal band` });

    if (volDrop > 40) list.push({ level: 'red', label: 'Liquidity Drain', detail: `-${volDrop}% volume — market depth collapsed` });
    else if (volDrop > 20) list.push({ level: 'amber', label: 'Volume Thinning', detail: `-${volDrop}% ADV — caution on large tickets` });
    else list.push({ level: 'green', label: 'Volume Adequate', detail: `-${volDrop}% — manageable flow` });

    if (days > 10) list.push({ level: 'red', label: 'Liquidation Risk', detail: `${days}d to liquidate — exceeds risk limits` });
    else if (days > 5) list.push({ level: 'amber', label: 'Slower Exit', detail: `${days}d — stage exits` });
    else list.push({ level: 'green', label: 'Exit Feasible', detail: `${days}d — within limits` });

    if (cost > 5_000_000) list.push({ level: 'red', label: 'High Trading Cost', detail: `$${(cost/1e6).toFixed(1)}M est. cost — pre-hedge` });
    else if (cost > 1_000_000) list.push({ level: 'amber', label: 'Elevated Cost', detail: `$${(cost/1e6).toFixed(1)}M — budget check` });
    else list.push({ level: 'green', label: 'Cost Contained', detail: `$${(cost/1e6).toFixed(1)}M` });

    return list;
  }, [impactSummary]);

  if (signals.length === 0) return (
    <div className="bg-white/40 backdrop-blur-xl rounded-2xl border border-white/30 p-4 text-center">
      <p className="text-sm text-slate-500">Run liquidity stress test to generate early-warning signals</p>
    </div>
  );

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {signals.map((s, i) => (
        <div key={i} className={`flex items-start gap-3 px-4 py-3 rounded-2xl backdrop-blur-xl border shadow-sm ${
          s.level === 'red' ? 'bg-red-500/10 border-red-500/20' : s.level === 'amber' ? 'bg-amber-500/10 border-amber-500/20' : 'bg-emerald-500/10 border-emerald-500/20'
        }`}>
          <span className={`mt-0.5 w-2 h-2 rounded-full flex-shrink-0 ${s.level === 'red' ? 'bg-red-600' : s.level === 'amber' ? 'bg-amber-500' : 'bg-emerald-500'}`} />
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <p className="text-sm font-semibold text-slate-900">{s.label}</p>
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border backdrop-blur-md ${
                s.level === 'red' ? 'bg-red-500/15 border-red-500/20 text-red-700' :
                s.level === 'amber' ? 'bg-amber-500/15 border-amber-500/20 text-amber-700' :
                'bg-emerald-500/15 border-emerald-500/20 text-emerald-700'
              }`}>{s.level === 'red' ? 'ALERT' : s.level === 'amber' ? 'WATCH' : 'OK'}</span>
            </div>
            <p className="text-xs text-slate-600 mt-0.5">{s.detail}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

function ScenarioWeightedVaRCard({ scenarios, investment = 100_000_000 }: { scenarios?: Array<{ return_pct: number; probability: number }>; investment?: number }) {
  // Default synthesize scenarios from DEMO distribution if none provided
  const effectiveScenarios = useMemo(() => {
    if (scenarios && scenarios.length > 0) return scenarios;
    // synthetic distribution: 7 scenarios with probabilities summing 1
    return [
      { return_pct: 4.5, probability: 0.10 },
      { return_pct: 2.1, probability: 0.20 },
      { return_pct: 0.8, probability: 0.30 },
      { return_pct: -1.2, probability: 0.20 },
      { return_pct: -3.5, probability: 0.12 },
      { return_pct: -6.8, probability: 0.06 },
      { return_pct: -11.2, probability: 0.02 },
    ];
  }, [scenarios]);

  const { weightedVaR95, weightedVaR99, expectedShortfall, tailProb } = useMemo(
    () => computeScenarioWeightedVaR(effectiveScenarios),
    [effectiveScenarios]
  );

  const var95Loss = Math.max(0, -weightedVaR95 / 100 * investment);
  const var99Loss = Math.max(0, -weightedVaR99 / 100 * investment);

  return (
    <div className="bg-white/40 backdrop-blur-xl rounded-2xl border border-white/30 p-5 shadow-sm">
      <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
        <span className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center text-white text-xs">VaR</span>
        Scenario-Weighted VaR <span className="text-xs font-normal text-slate-500">— probability-weighted tail (non-equal weights)</span>
      </h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
        <div className="bg-white/60 backdrop-blur-md rounded-xl border border-white/40 p-3 text-center">
          <div className="text-lg font-bold text-amber-700 tabular-nums">${(var95Loss/1e6).toFixed(1)}M</div>
          <div className="text-xs text-slate-500">Weighted VaR 95</div>
          <div className="text-[11px] text-slate-400 mt-0.5">{weightedVaR95.toFixed(2)}% return threshold</div>
          <span className="inline-flex mt-2 px-2 py-0.5 rounded-full bg-amber-500/15 border border-amber-500/20 text-amber-700 text-[10px] font-bold backdrop-blur-md">95% CONF</span>
        </div>
        <div className="bg-white/60 backdrop-blur-md rounded-xl border border-white/40 p-3 text-center">
          <div className="text-lg font-bold text-red-700 tabular-nums">${(var99Loss/1e6).toFixed(1)}M</div>
          <div className="text-xs text-slate-500">Weighted VaR 99</div>
          <div className="text-[11px] text-slate-400 mt-0.5">{weightedVaR99.toFixed(2)}% threshold</div>
          <span className="inline-flex mt-2 px-2 py-0.5 rounded-full bg-red-500/15 border border-red-500/20 text-red-700 text-[10px] font-bold backdrop-blur-md">99% CONF</span>
        </div>
        <div className="bg-white/60 backdrop-blur-md rounded-xl border border-white/40 p-3 text-center">
          <div className="text-lg font-bold text-red-600 tabular-nums">{expectedShortfall.toFixed(2)}%</div>
          <div className="text-xs text-slate-500">Expected Shortfall</div>
          <div className="text-[11px] text-slate-400 mt-0.5">Avg loss beyond VaR 95</div>
          <span className="inline-flex mt-2 px-2 py-0.5 rounded-full bg-red-500/10 border border-red-500/15 text-red-700 text-[10px] font-bold backdrop-blur-md">TAIL AVG</span>
        </div>
        <div className="bg-white/60 backdrop-blur-md rounded-xl border border-white/40 p-3 text-center">
          <div className="text-lg font-bold text-purple-700 tabular-nums">{(tailProb*100).toFixed(1)}%</div>
          <div className="text-xs text-slate-500">Extreme Tail Prob</div>
          <div className="text-[11px] text-slate-400 mt-0.5">Return &le; VaR 99</div>
          <span className="inline-flex mt-2 px-2 py-0.5 rounded-full bg-purple-500/15 border border-purple-500/20 text-purple-700 text-[10px] font-bold backdrop-blur-md">PROB</span>
        </div>
      </div>
      <div className="mt-4">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Scenario Distribution</p>
        <div className="flex gap-1 h-8 items-end">
          {effectiveScenarios.map((s, i) => {
            const h = Math.max(8, Math.min(32, Math.abs(s.return_pct) * 6 + s.probability * 40));
            const bg = s.return_pct <= weightedVaR99 ? '#dc2626' : s.return_pct <= weightedVaR95 ? '#f59e0b' : s.return_pct >= 0 ? '#22c55e' : '#64748b';
            return (
              <div key={i} className="flex-1 flex flex-col items-center gap-1">
                <div className="w-full rounded-t-md transition-all" style={{ height: `${h}px`, backgroundColor: bg, opacity: 0.9 }} title={`${s.return_pct}% (${(s.probability*100).toFixed(0)}%)`} />
                <span className="text-[10px] text-slate-500">{(s.probability*100).toFixed(0)}%</span>
              </div>
            );
          })}
        </div>
        <div className="flex gap-2 mt-2 text-[11px]">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-red-600 inline-block" /> &le;VaR99</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-amber-500 inline-block" /> &le;VaR95</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-emerald-500 inline-block" /> Positive</span>
        </div>
      </div>
    </div>
  );
}

function RegimeBadge({ impactSummary }: { impactSummary: Record<string, unknown> | null }) {
  const regime = detectRegime(impactSummary);
  return (
    <div className="inline-flex items-center gap-3 px-4 py-2 rounded-full backdrop-blur-xl border shadow-sm" style={{ backgroundColor: `${regime.color}14`, borderColor: `${regime.color}30` }}>
      <span className="w-2.5 h-2.5 rounded-full animate-pulse" style={{ backgroundColor: regime.color }} />
      <span className="text-sm font-bold" style={{ color: regime.color }}>{regime.label.toUpperCase()}</span>
      <span className="text-xs text-slate-600 hidden sm:inline">{regime.description}</span>
      <span className="px-2 py-0.5 rounded-full bg-white/60 border border-white/40 text-[11px] font-bold text-slate-700 backdrop-blur-md">
        REGIME DETECTION
      </span>
    </div>
  );
}

export default function RiskIntelPage() {
  const [activeTab, setActiveTab] = useState<Tab>('sanctions');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Sanctions state
  const [sanctionsResult, setSanctionsResult] = useState<Record<string, unknown> | null>(null);
  // Liquidity state
  const [liquidityResult, setLiquidityResult] = useState<Record<string, unknown> | null>(null);
  const [stressScenario, setStressScenario] = useState('global');
  // Political state
  const [politicalCountry, setPoliticalCountry] = useState('RU');
  const [politicalResult, setPoliticalResult] = useState<Record<string, unknown> | null>(null);
  // Contagion state
  const [contagionTrigger, setContagionTrigger] = useState('IT');
  const [contagionResult, setContagionResult] = useState<Record<string, unknown> | null>(null);

  const runSanctionsScreen = async () => {
    setLoading(true); setError('');
    try {
      const res = await api.riskIntel.sanctionsScreen(DEMO_INSTRUMENTS as unknown as Array<Record<string, unknown>>);
      setSanctionsResult(res.data);
    } catch { setError('Failed to run sanctions screening'); }
    finally { setLoading(false); }
  };

  const runLiquidityAnalysis = async (scenario?: string) => {
    setLoading(true); setError('');
    try {
      const res = await api.riskIntel.liquidityStressTest(DEMO_INSTRUMENTS as unknown as Array<Record<string, unknown>>, scenario || stressScenario);
      setLiquidityResult(res.data);
    } catch { setError('Failed to run liquidity analysis'); }
    finally { setLoading(false); }
  };

  const runPoliticalRisk = async () => {
    setLoading(true); setError('');
    try {
      const res = await api.riskIntel.politicalRisk(politicalCountry);
      setPoliticalResult(res.data);
    } catch { setError('Failed to load political risk'); }
    finally { setLoading(false); }
  };

  const runContagionSim = async () => {
    setLoading(true); setError('');
    try {
      const res = await api.riskIntel.contagionCascade(contagionTrigger, DEMO_INSTRUMENTS as unknown as Array<Record<string, unknown>>, 500);
      setContagionResult(res.data);
    } catch { setError('Failed to run contagion simulation'); }
    finally { setLoading(false); }
  };

  const liquidityImpact = (liquidityResult?.impact_summary as Record<string, unknown>) || null;

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">Risk Intelligence</h1>
      <p className="text-gray-400 mb-6">Sanctions screening, liquidity risk, political risk, and contagion analysis — scenario-weighted VaR & regime detection included.</p>

      {/* Global Intelligence Overlay: Scenario-Weighted VaR + Regime Badge + Early Warnings */}
      <div className="mb-6 space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <RegimeBadge impactSummary={liquidityImpact} />
          <span className="text-xs text-gray-400">Regime auto-detected from liquidity stress impact (spreads, volume, days-to-liquidate)</span>
        </div>
        <ScenarioWeightedVaRCard />
        <div>
          <h3 className="text-sm font-semibold text-gray-300 mb-2 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-amber-500" /> Early-Warning Signals
            <span className="text-xs font-normal text-gray-500">— auto-derived from stress test; amber = watch, red = action</span>
          </h3>
          <EarlyWarningSignals impactSummary={liquidityImpact} />
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 flex-wrap">
        {TABS.map((t) => (
          <button key={t.key} onClick={() => setActiveTab(t.key)}
            className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 ${activeTab === t.key ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'}`}>
            <span>{t.icon}</span> {t.label}
          </button>
        ))}
      </div>

      {error && <div className="bg-red-900/30 border border-red-500 rounded-lg p-3 mb-4 text-red-300">{error}</div>}

      {/* ── Sanctions Tab ─────────────────────────────────────────────── */}
      {activeTab === 'sanctions' && (
        <div className="space-y-6">
          <div className="bg-gray-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Portfolio Sanctions Screening</h2>
              <button onClick={runSanctionsScreen} disabled={loading}
                className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg disabled:opacity-50 text-sm">
                {loading ? 'Screening...' : 'Run Screening'}
              </button>
            </div>
            <p className="text-sm text-gray-400 mb-4">Checking {DEMO_INSTRUMENTS.length} instruments against OFAC SDN, EU, UN sanctions lists</p>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
              {DEMO_INSTRUMENTS.map((inst) => (
                <div key={inst.id} className="bg-gray-700/50 rounded-lg p-3 text-center">
                  <div className="text-sm font-medium text-white truncate">{inst.issuer_name}</div>
                  <div className="text-xs text-gray-400 mt-1">{inst.issuer_country} | {inst.currency}</div>
                  <div className="text-xs text-blue-400 mt-1">${(inst.principal_outstanding / 1e9).toFixed(1)}B</div>
                </div>
              ))}
            </div>
          </div>

          {sanctionsResult && (
            <div className="bg-gray-800 rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">Screening Results</h2>
                <SeverityBadge level={(sanctionsResult.overall_severity as string) || 'clear'} />
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-white">{(sanctionsResult.total_matches as number) || 0}</div>
                  <div className="text-xs text-gray-400">Total Matches</div>
                </div>
                <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-red-400">{(sanctionsResult.blocked as boolean) ? 'YES' : 'NO'}</div>
                  <div className="text-xs text-gray-400">Blocked</div>
                </div>
                <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-yellow-400">{((sanctionsResult.countries_flagged as string[]) || []).length}</div>
                  <div className="text-xs text-gray-400">Countries Flagged</div>
                </div>
                <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-orange-400">{((sanctionsResult.entities_flagged as string[]) || []).length}</div>
                  <div className="text-xs text-gray-400">Entities Flagged</div>
                </div>
              </div>

              {/* Matches list */}
              {((sanctionsResult.matches as Array<Record<string, unknown>>) || []).length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-sm font-medium text-gray-400 mb-2">Matches Found</h3>
                  {(sanctionsResult.matches as Array<Record<string, unknown>>).map((m, i) => (
                    <div key={i} className="bg-gray-700/50 rounded-lg p-3 flex items-center justify-between">
                      <div>
                        <span className="font-medium text-white">{String(m.entity)}</span>
                        <span className="text-xs text-gray-400 ml-2">({String(m.list)})</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-xs text-gray-400">{String(m.reason)}</span>
                        <SeverityBadge level={String(m.severity)} />
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div className="mt-4 bg-gray-700/30 rounded-lg p-3">
                <p className="text-sm text-gray-300">{String(sanctionsResult.recommendation)}</p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Liquidity Tab ─────────────────────────────────────────────── */}
      {activeTab === 'liquidity' && (
        <div className="space-y-6">
          <div className="bg-gray-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Liquidity Stress Test</h2>
              <div className="flex items-center gap-3">
                <select value={stressScenario} onChange={(e) => setStressScenario(e.target.value)}
                  className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm">
                  <option value="global">Global Risk-Off (2008/2020)</option>
                  <option value="em_crises">EM Sell-Off</option>
                  <option value="rate_shock">Rate Shock</option>
                  <option value="geopolitical">Geopolitical Crisis</option>
                </select>
                <button onClick={() => runLiquidityAnalysis()} disabled={loading}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg disabled:opacity-50 text-sm">
                  {loading ? 'Analyzing...' : 'Run Analysis'}
                </button>
              </div>
            </div>
            {/* Inline regime badge for this scenario */}
            <div className="mt-3">
              <RegimeBadge impactSummary={liquidityImpact} />
            </div>
          </div>

          {liquidityResult && (
            <div className="space-y-6">
              <ScenarioWeightedVaRCard investment={DEMO_INSTRUMENTS.reduce((a, inst) => a + inst.principal_outstanding, 0)} />
              <div>
                <h3 className="text-sm font-semibold text-gray-300 mb-2">Early-Warning — Current Stress Scenario</h3>
                <EarlyWarningSignals impactSummary={liquidityImpact} />
              </div>
              <div className="bg-gray-800 rounded-xl p-6">
                <h3 className="text-lg font-semibold mb-4">Stress Scenario: {String(liquidityResult.scenario)}</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-orange-400">
                      {((liquidityResult.impact_summary as Record<string, unknown>)?.spread_increase_pct as number) || 0}%
                    </div>
                    <div className="text-xs text-gray-400">Spread Increase</div>
                  </div>
                  <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-red-400">
                      {((liquidityResult.impact_summary as Record<string, unknown>)?.volume_decrease_pct as number) || 0}%
                    </div>
                    <div className="text-xs text-gray-400">Volume Drop</div>
                  </div>
                  <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-yellow-400">
                      ${(((liquidityResult.impact_summary as Record<string, unknown>)?.estimated_trading_cost_usd as number) || 0 / 1e6).toFixed(1)}M
                    </div>
                    <div className="text-xs text-gray-400">Trading Cost</div>
                  </div>
                  <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-purple-400">
                      {((liquidityResult.impact_summary as Record<string, unknown>)?.days_to_liquidate_under_stress as number) || 0}d
                    </div>
                    <div className="text-xs text-gray-400">Days to Liquidate</div>
                  </div>
                </div>
              </div>

              {/* Stressed Result */}
              {(liquidityResult.stressed_result as Record<string, unknown>) && (
                <div className="bg-gray-800 rounded-xl p-6">
                  <h3 className="text-lg font-semibold mb-4">Portfolio Under Stress</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                    <div className="bg-gray-700/50 rounded-lg p-3 text-center">
                      <div className="text-xl font-bold text-white">
                        {((liquidityResult.stressed_result as Record<string, unknown>).weighted_spread_bps as number)?.toFixed(1)}bps
                      </div>
                      <div className="text-xs text-gray-400">Weighted Spread</div>
                    </div>
                    <div className="bg-gray-700/50 rounded-lg p-3 text-center">
                      <div className="text-xl font-bold text-blue-400">
                        {((liquidityResult.stressed_result as Record<string, unknown>).weighted_liquidity_score as number)?.toFixed(1)}
                      </div>
                      <div className="text-xs text-gray-400">Liquidity Score</div>
                    </div>
                    <div className="bg-gray-700/50 rounded-lg p-3 text-center">
                      <div className="text-xl font-bold text-yellow-400">
                        ${((((liquidityResult.stressed_result as Record<string, unknown>).market_impact_cost_usd as number) || 0) / 1e6).toFixed(1)}M
                      </div>
                      <div className="text-xs text-gray-400">Market Impact</div>
                    </div>
                    <div className="bg-gray-700/50 rounded-lg p-3 text-center">
                      <div className="text-xl font-bold text-purple-400">
                        {((liquidityResult.stressed_result as Record<string, unknown>).days_to_liquidate_full as number)?.toFixed(0)}d
                      </div>
                      <div className="text-xs text-gray-400">Full Liquidation</div>
                    </div>
                  </div>

                  {/* Per-instrument liquidity */}
                  {((liquidityResult.stressed_result as Record<string, unknown>).instruments as Array<Record<string, unknown>>)?.map((inst, i) => {
                    const score = (inst.score as Record<string, unknown>)?.liquidity_score as number;
                    const tier = String((inst.score as Record<string, unknown>)?.liquidity_tier || '');
                    return (
                      <div key={i} className="flex items-center justify-between bg-gray-700/30 rounded-lg p-3 mb-2">
                        <div>
                          <span className="font-medium text-white text-sm">{String(inst.instrument_name)}</span>
                          <span className="text-xs text-gray-400 ml-2">{String(inst.currency)} | {String(inst.instrument_type)}</span>
                        </div>
                        <div className="flex items-center gap-4">
                          <div className="text-right">
                            <div className="text-xs text-gray-400">Spread</div>
                            <div className="text-sm font-mono text-white">{((inst.current as Record<string, unknown>)?.bid_ask_spread_bps as number)?.toFixed(1)}bps</div>
                          </div>
                          <div className="text-right">
                            <div className="text-xs text-gray-400">ADV</div>
                            <div className="text-sm font-mono text-white">${(((inst.current as Record<string, unknown>)?.average_daily_volume_usd as number) || 0 / 1e6).toFixed(0)}M</div>
                          </div>
                          <div className="text-right">
                            <div className="text-xs text-gray-400">Score</div>
                            <div className="text-sm font-mono text-white">{score?.toFixed(1)}</div>
                          </div>
                          <SeverityBadge level={tier} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Political Tab ─────────────────────────────────────────────── */}
      {activeTab === 'political' && (
        <div className="space-y-6">
          <div className="bg-gray-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Political Risk Analysis</h2>
              <div className="flex items-center gap-3">
                <select value={politicalCountry} onChange={(e) => setPoliticalCountry(e.target.value)}
                  className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm">
                  {['US','GB','JP','DE','FR','IT','CA','CN','IN','BR','RU','AU','KR','MX','ZA','SA','TR','AR','PL','NL','ES','SG','NO','SE','CH'].map(c => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
                <button onClick={runPoliticalRisk} disabled={loading}
                  className="bg-amber-600 hover:bg-amber-700 text-white px-4 py-2 rounded-lg disabled:opacity-50 text-sm">
                  {loading ? 'Analyzing...' : 'Analyze'}
                </button>
              </div>
            </div>
          </div>

          {politicalResult && (
            <div className="space-y-6">
              {/* Overall Score */}
              <div className="bg-gray-800 rounded-xl p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold">{String((politicalResult.country_name as string) || politicalCountry)}</h3>
                  <div className="flex items-center gap-3">
                    <span className="text-3xl font-bold" style={{ color: SEVERITY_COLORS[String((politicalResult.overall as Record<string, unknown>)?.risk_tier)] }}>
                      {String((politicalResult.overall as Record<string, unknown>)?.risk_score)}
                    </span>
                    <SeverityBadge level={String((politicalResult.overall as Record<string, unknown>)?.risk_tier)} />
                    {/* Regime-style badge for political risk tier */}
                    <span className="px-3 py-1 rounded-full backdrop-blur-xl border text-xs font-bold"
                      style={{
                        backgroundColor: `${SEVERITY_COLORS[String((politicalResult.overall as Record<string, unknown>)?.risk_tier)] || '#6b7280'}14`,
                        borderColor: `${SEVERITY_COLORS[String((politicalResult.overall as Record<string, unknown>)?.risk_tier)] || '#6b7280'}30`,
                        color: SEVERITY_COLORS[String((politicalResult.overall as Record<string, unknown>)?.risk_tier)] || '#6b7280'
                      }}>
                      {String((politicalResult.overall as Record<string, unknown>)?.risk_tier || '').toUpperCase()} REGIME
                    </span>
                  </div>
                </div>
                <ScoreBar score={Number((politicalResult.overall as Record<string, unknown>)?.risk_score) || 0} />
                <div className="mt-4">
                  <EarlyWarningSignals impactSummary={{
                    spread_increase_pct: Number((politicalResult.overall as Record<string, unknown>)?.risk_score) || 0,
                    volume_decrease_pct: 0, estimated_trading_cost_usd: 0, days_to_liquidate_under_stress: 0
                  } as Record<string, unknown>} />
                </div>
              </div>

              {/* Component Scores */}
              <div className="bg-gray-800 rounded-xl p-6">
                <h3 className="text-lg font-semibold mb-4">Risk Components</h3>
                <div className="space-y-3">
                  {Object.entries((politicalResult.component_scores as Record<string, number>) || {}).map(([key, val]) => (
                    <div key={key} className="flex items-center gap-4">
                      <div className="w-44 text-sm text-gray-300 capitalize">{key.replace(/_/g, ' ')}</div>
                      <div className="flex-1"><ScoreBar score={val} /></div>
                      <div className="w-12 text-right text-sm font-mono text-white">{val.toFixed(0)}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Indicators */}
              <div className="bg-gray-800 rounded-xl p-6">
                <h3 className="text-lg font-semibold mb-4">Governance Indicators</h3>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                  {Object.entries((politicalResult.indicators as Record<string, number>) || {}).map(([key, val]) => (
                    <div key={key} className="bg-gray-700/50 rounded-lg p-3 text-center">
                      <div className="text-xl font-bold text-blue-400">{val.toFixed(1)}</div>
                      <div className="text-xs text-gray-400 mt-1 capitalize">{key.replace(/_/g, ' ')}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Events */}
              {((politicalResult.likely_events as Array<Record<string, unknown>>) || []).length > 0 && (
                <div className="bg-gray-800 rounded-xl p-6">
                  <h3 className="text-lg font-semibold mb-4">Likely Political Events</h3>
                  <div className="space-y-3">
                    {(politicalResult.likely_events as Array<Record<string, unknown>>).map((ev, i) => (
                      <div key={i} className="bg-gray-700/50 rounded-lg p-4 border-l-4 border-amber-500">
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-medium text-white">{String(ev.event)}</span>
                          <div className="flex items-center gap-3">
                            <span className="text-sm text-gray-400">Timeline: {String(ev.timeline)}</span>
                            <span className="text-sm font-bold text-amber-400">{((ev.probability as number) * 100).toFixed(0)}%</span>
                          </div>
                        </div>
                        <p className="text-sm text-gray-300">{String(ev.impact)}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Contagion Tab ─────────────────────────────────────────────── */}
      {activeTab === 'contagion' && (
        <div className="space-y-6">
          <div className="bg-gray-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Default Cascade Simulation</h2>
              <div className="flex items-center gap-3">
                <select value={contagionTrigger} onChange={(e) => setContagionTrigger(e.target.value)}
                  className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm">
                  {['US','GB','JP','DE','FR','IT','CA','CN','IN','BR','RU','AU','KR','MX','ZA','SA','TR','AR'].map(c => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
                <button onClick={runContagionSim} disabled={loading}
                  className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg disabled:opacity-50 text-sm">
                  {loading ? 'Simulating...' : 'Simulate Default'}
                </button>
              </div>
            </div>
            <p className="text-sm text-gray-400">Simulate what happens if a country defaults — see how contagion spreads through trade, finance, and investor channels</p>
          </div>

          {contagionResult && (
            <div className="space-y-6">
              {/* Summary */}
              <div className="bg-gray-800 rounded-xl p-6">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                    <div className="text-3xl font-bold text-red-400">{String(contagionResult.trigger)}</div>
                    <div className="text-xs text-gray-400">Trigger Country</div>
                  </div>
                  <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                    <div className="text-3xl font-bold text-orange-400">
                      {((contagionResult.trigger_default_probability as number) * 100).toFixed(1)}%
                    </div>
                    <div className="text-xs text-gray-400">Default Probability</div>
                  </div>
                  <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                    <div className="text-3xl font-bold text-yellow-400">
                      {((contagionResult.affected_countries as Array<unknown>) || []).length}
                    </div>
                    <div className="text-xs text-gray-400">Countries Affected</div>
                  </div>
                  <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                    <div className="text-3xl font-bold text-red-400">
                      {String((contagionResult.total_portfolio_impact_bps as number)?.toFixed(0))}bps
                    </div>
                    <div className="text-xs text-gray-400">Portfolio Impact</div>
                  </div>
                </div>
              </div>

              {/* Affected Countries */}
              {((contagionResult.affected_countries as Array<Record<string, unknown>>) || []).length > 0 && (
                <div className="bg-gray-800 rounded-xl p-6">
                  <h3 className="text-lg font-semibold mb-4">Affected Countries</h3>
                  <div className="space-y-2">
                    {(contagionResult.affected_countries as Array<Record<string, unknown>>).map((ac, i) => (
                      <div key={i} className="flex items-center justify-between bg-gray-700/50 rounded-lg p-3">
                        <div className="flex items-center gap-3">
                          <span className="w-8 h-8 bg-gray-600 rounded flex items-center justify-center text-sm font-bold text-white">
                            {String(ac.country)}
                          </span>
                          <div>
                            <span className="font-medium text-white">{String(ac.country)}</span>
                            <span className="text-xs text-gray-400 ml-2">via {String(ac.channel)} (strength: {String(ac.link_strength)})</span>
                          </div>
                        </div>
                        <div className="flex items-center gap-4">
                          <span className="text-sm text-gray-400">{String(ac.speed)}</span>
                          <span className="font-mono text-sm text-orange-400">{String((ac.impact_bps as number)?.toFixed(0))}bps</span>
                          <ScoreBar score={Number(ac.impact_bps) || 0} max={500} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Cascade Timeline */}
              {((contagionResult.cascade_timeline as Array<Record<string, unknown>>) || []).length > 0 && (
                <div className="bg-gray-800 rounded-xl p-6">
                  <h3 className="text-lg font-semibold mb-4">Cascade Timeline</h3>
                  <div className="relative">
                    <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-gray-700" />
                    <div className="space-y-4">
                      {(contagionResult.cascade_timeline as Array<Record<string, unknown>>).map((step, i) => (
                        <div key={i} className="relative flex gap-4">
                          <div className="w-12 h-12 rounded-full bg-red-600/80 flex items-center justify-center text-white font-bold text-xs z-10 flex-shrink-0">
                            D{String(step.day)}
                          </div>
                          <div className="bg-gray-700/50 rounded-lg p-3 flex-1">
                            <div className="flex items-center justify-between">
                              <span className="font-medium text-white text-sm">{String(step.event)}</span>
                              <span className="text-sm font-mono text-orange-400">{String((step.impact_bps as number)?.toFixed(0))}bps</span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
