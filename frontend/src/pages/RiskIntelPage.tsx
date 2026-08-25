import { useState } from 'react';
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
    } catch (e) { setError('Failed to run sanctions screening'); }
    finally { setLoading(false); }
  };

  const runLiquidityAnalysis = async (scenario?: string) => {
    setLoading(true); setError('');
    try {
      const res = await api.riskIntel.liquidityStressTest(DEMO_INSTRUMENTS as unknown as Array<Record<string, unknown>>, scenario || stressScenario);
      setLiquidityResult(res.data);
    } catch (e) { setError('Failed to run liquidity analysis'); }
    finally { setLoading(false); }
  };

  const runPoliticalRisk = async () => {
    setLoading(true); setError('');
    try {
      const res = await api.riskIntel.politicalRisk(politicalCountry);
      setPoliticalResult(res.data);
    } catch (e) { setError('Failed to load political risk'); }
    finally { setLoading(false); }
  };

  const runContagionSim = async () => {
    setLoading(true); setError('');
    try {
      const res = await api.riskIntel.contagionCascade(contagionTrigger, DEMO_INSTRUMENTS as unknown as Array<Record<string, unknown>>, 500);
      setContagionResult(res.data);
    } catch (e) { setError('Failed to run contagion simulation'); }
    finally { setLoading(false); }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">Risk Intelligence</h1>
      <p className="text-gray-400 mb-6">Sanctions screening, liquidity risk, political risk, and contagion analysis — all in one place.</p>

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
          </div>

          {liquidityResult && (
            <div className="space-y-6">
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
                  </div>
                </div>
                <ScoreBar score={Number((politicalResult.overall as Record<string, unknown>)?.risk_score) || 0} />
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
