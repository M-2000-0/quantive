import { useState, useEffect, useMemo } from 'react';
import { api } from '../api';
import AppShell from '../components/layout/AppShell';
import Card, { CardHeader } from '../components/ui/Card';
import Button from '../components/ui/Button';
import Badge from '../components/ui/Badge';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import { formatCurrency } from '../utils';
import type { Portfolio } from '../types';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';

interface Adjustment {
  action: string;
  amount: number;
  coupon_rate?: number;
  tenor_years?: number;
  label: string;
}

interface WhatIfResult {
  before: {
    total_principal: number;
    weighted_coupon_pct: number;
    annual_cost: number;
    num_instruments: number;
    currency_breakdown: Record<string, { amount: number; pct: number }>;
  };
  after: {
    total_principal: number;
    weighted_coupon_pct: number;
    annual_cost: number;
    num_instruments: number;
  };
  impact: {
    total_change: number;
    total_change_pct: number;
    coupon_change_bps: number;
    annual_cost_change: number;
    annual_cost_change_pct: number;
  };
  adjustments: Array<{ type: string; amount: number; impact: string }>;
  recommendation: string;
}

const PRESET_SCENARIOS = [
  { name: 'Issue 10Y USD Bond ($2B)', adjustments: [{ action: 'new_issuance', amount: 2_000_000_000, coupon_rate: 0.045, tenor_years: 10, label: '10Y USD Bond' }] },
  { name: 'Issue 5Y EUR Bond ($1.5B)', adjustments: [{ action: 'new_issuance', amount: 1_500_000_000, coupon_rate: 0.035, tenor_years: 5, label: '5Y EUR Bond' }] },
  { name: 'Reduce Short-Term by $3B', adjustments: [{ action: 'decrease', amount: 3_000_000_000, label: 'Reduce Short-Term' }] },
  { name: 'Dual Tranche ($3B USD)', adjustments: [
    { action: 'new_issuance', amount: 1_500_000_000, coupon_rate: 0.042, tenor_years: 5, label: '5Y Tranche' },
    { action: 'new_issuance', amount: 1_500_000_000, coupon_rate: 0.048, tenor_years: 30, label: '30Y Tranche' },
  ] },
];

function ShockSlider({ label, value, min, max, step, unit, onChange }: { label: string; value: number; min: number; max: number; step: number; unit: string; onChange: (v: number) => void }) {
  const pct = ((value - min) / (max - min)) * 100;
  const isPositive = value > 0;
  const isNegative = value < 0;
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-700">{label}</span>
        <span className={`text-xs font-bold tabular-nums px-2 py-0.5 rounded-full border backdrop-blur ${isPositive ? 'bg-amber-500/10 text-amber-700 border-amber-500/20' : isNegative ? 'bg-emerald-500/10 text-emerald-700 border-emerald-500/20' : 'bg-slate-100 text-slate-600 border-slate-200'}`}>
          {value > 0 ? '+' : ''}{value}{unit}
        </span>
      </div>
      <div className="relative">
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={e => onChange(Number(e.target.value))}
          className="w-full h-2 rounded-full appearance-none cursor-pointer"
          style={{
            background: `linear-gradient(to right, #10b981 0%, #e2e8f0 ${((0 - min) / (max - min)) * 100}%, #f59e0b ${pct}%, #e2e8f0 ${pct}%, #e2e8f0 100%)`,
          }}
        />
        <div className="flex justify-between text-[10px] text-slate-400 mt-1">
          <span>{min}{unit}</span>
          <span>0</span>
          <span>+{max}{unit}</span>
        </div>
      </div>
    </div>
  );
}

export default function WhatIfPage() {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [adjustments, setAdjustments] = useState<Adjustment[]>([]);
  const [result, setResult] = useState<WhatIfResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);

  // Live interactive shocks
  const [rateShiftBps, setRateShiftBps] = useState(0); // -200 to +300
  const [fxShockPct, setFxShockPct] = useState(0); // -30 to +30
  const [inflationShockBps, setInflationShockBps] = useState(0); // -100 to +300
  const [duration, setDuration] = useState(7.2);
  const [fxExposure, setFxExposure] = useState(0.28);

  // New issuance form
  const [newCurrency, setNewCurrency] = useState('USD');
  const [newAmount, setNewAmount] = useState('2000000000');
  const [newCoupon, setNewCoupon] = useState('4.5');
  const [newTenor, setNewTenor] = useState('10');

  useEffect(() => {
    api.portfolios.list().then((res) => {
      const list = (res as { data: Portfolio[] }).data || [];
      setPortfolios(list);
      if (list.length) setSelectedId(list[0].id);
    }).finally(() => setLoading(false));
  }, []);

  const selectedPortfolio = useMemo(() => portfolios.find(p => p.id === selectedId) || null, [portfolios, selectedId]);

  // Derive base metrics from result or portfolio fallback
  const baseMetrics = useMemo(() => {
    if (result) {
      return {
        total: result.after.total_principal || result.before.total_principal,
        coupon: result.after.weighted_coupon_pct,
        annualCost: result.after.annual_cost,
        beforeCost: result.before.annual_cost,
        beforeCoupon: result.before.weighted_coupon_pct,
      };
    }
    if (selectedPortfolio) {
      const total = selectedPortfolio.instruments.reduce((s, i) => s + i.principal_outstanding, 0);
      const wCoupon = selectedPortfolio.instruments.reduce((s, i) => s + i.coupon_rate * i.principal_outstanding, 0) / (total || 1) * 100;
      const annual = selectedPortfolio.instruments.reduce((s, i) => s + i.principal_outstanding * i.coupon_rate, 0);
      return { total, coupon: wCoupon, annualCost: annual, beforeCost: annual, beforeCoupon: wCoupon };
    }
    return { total: 0, coupon: 0, annualCost: 0, beforeCost: 0, beforeCoupon: 0 };
  }, [result, selectedPortfolio]);

  // Live model: cost = base * (1 + rateShift* duration/10000 + fxExposure*fxShock + inflationShock*0.3/10000)
  const liveMetrics = useMemo(() => {
    const base = baseMetrics.annualCost || baseMetrics.beforeCost || 1;
    const rateImpact = (rateShiftBps * duration) / 10000;
    const fxImpact = fxExposure * (fxShockPct / 100);
    const inflImpact = (inflationShockBps * 0.5) / 10000; // inflation half weight
    const shockedCost = base * (1 + rateImpact + fxImpact + inflImpact);
    const shockedTotal = baseMetrics.total * (1 + fxImpact * 0.5);
    const shockedCoupon = baseMetrics.coupon + rateShiftBps / 100 + inflationShockBps / 200;
    return {
      shockedCost,
      shockedTotal,
      shockedCoupon,
      deltaCost: shockedCost - base,
      deltaPct: base ? ((shockedCost - base) / base) * 100 : 0,
      rateImpact,
      fxImpact,
      inflImpact,
    };
  }, [baseMetrics, rateShiftBps, fxShockPct, inflationShockBps, duration, fxExposure]);

  const breachWarnings = useMemo(() => {
    const warnings: Array<{ level: 'danger' | 'warning'; msg: string }> = [];
    if (liveMetrics.deltaPct > 15) warnings.push({ level: 'danger', msg: `Cost breach: +${liveMetrics.deltaPct.toFixed(1)}% exceeds 15% risk appetite` });
    else if (liveMetrics.deltaPct > 8) warnings.push({ level: 'warning', msg: `Cost alert: +${liveMetrics.deltaPct.toFixed(1)}% approaching limit` });
    if (rateShiftBps > 200) warnings.push({ level: 'warning', msg: 'Rate shock >200bps — consider hedging with caps or swaps' });
    if (Math.abs(fxShockPct) > 20) warnings.push({ level: 'danger', msg: `FX shock ${fxShockPct > 0 ? '+' : ''}${fxShockPct}% — material currency exposure` });
    if (inflationShockBps > 200) warnings.push({ level: 'warning', msg: 'Inflation shock >200bps — real cost of inflation-linked debt rising' });
    if (liveMetrics.shockedCoupon > 6) warnings.push({ level: 'danger', msg: `Coupon breached 6%: ${liveMetrics.shockedCoupon.toFixed(2)}% — refinancing may be needed` });
    return warnings;
  }, [liveMetrics, rateShiftBps, fxShockPct, inflationShockBps]);

  const analyze = async () => {
    if (!selectedId || adjustments.length === 0) return;
    setAnalyzing(true);
    try {
      const res = await api.whatif.analyze({
        portfolio_id: selectedId,
        adjustments: adjustments.map(a => ({
          action: a.action,
          amount: a.amount,
          coupon_rate: a.coupon_rate,
          tenor_years: a.tenor_years,
        })),
      });
      setResult(res as unknown as WhatIfResult);
      // infer duration/fxExposure from result or keep manual
      const coupon = (res as unknown as WhatIfResult).before.weighted_coupon_pct;
      if (coupon) setDuration(Math.max(2, Math.min(15, coupon * 1.2)));
    } catch {
      // silently handle
    } finally {
      setAnalyzing(false);
    }
  };

  const addNewIssuance = () => {
    setAdjustments(prev => [...prev, {
      action: 'new_issuance',
      amount: parseFloat(newAmount) || 0,
      coupon_rate: parseFloat(newCoupon) / 100 || 0.05,
      tenor_years: parseInt(newTenor) || 10,
      label: `${newTenor}Y ${newCurrency} Bond`,
    }]);
  };

  const applyPreset = (preset: typeof PRESET_SCENARIOS[0]) => {
    setAdjustments(preset.adjustments.map(a => ({ ...a })));
    setResult(null);
  };

  const removeAdjustment = (idx: number) => {
    setAdjustments(prev => prev.filter((_, i) => i !== idx));
    setResult(null);
  };

  const resetShocks = () => {
    setRateShiftBps(0);
    setFxShockPct(0);
    setInflationShockBps(0);
  };

  if (loading) return <AppShell><LoadingSpinner message="Loading portfolios..." /></AppShell>;

  const impactData = result ? [
    { name: 'Before', cost: result.before.annual_cost },
    { name: 'After', cost: result.after.annual_cost },
  ] : [];

  const liveData = [
    { name: 'Base', cost: baseMetrics.beforeCost, fill: '#64748b' },
    { name: 'Shocked', cost: liveMetrics.shockedCost, fill: liveMetrics.deltaPct > 10 ? '#ef4444' : liveMetrics.deltaPct > 5 ? '#f59e0b' : '#10b981' },
  ];

  return (
    <AppShell>
      <div className="px-4 lg:px-8 py-6 max-w-[1440px] mx-auto">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between mb-6 gap-3">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">What-If Playground — Live</h1>
            <p className="text-sm text-slate-500 mt-1">Sliders recompute cost/risk instantly • cost = base × (1 + rate×duration/10000 + fxExp×fxShock)</p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">Duration</span>
            <input type="number" value={duration} onChange={e => setDuration(Number(e.target.value))} step={0.1} className="glass-input !py-1.5 w-20 text-sm" />
            <span className="text-xs text-slate-500">FX exp</span>
            <input type="number" value={fxExposure} onChange={e => setFxExposure(Number(e.target.value))} step={0.01} min={0} max={1} className="glass-input !py-1.5 w-20 text-sm" />
            <Button variant="ghost" size="sm" onClick={resetShocks}>Reset shocks</Button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Controls */}
          <div className="space-y-6">
            <Card>
              <CardHeader title="Portfolio" subtitle="Select to calibrate base metrics" />
              <select
                value={selectedId || ''}
                onChange={e => { setSelectedId(e.target.value); setResult(null); setAdjustments([]); }}
                className="w-full px-3 py-2 border border-white/40 bg-white/60 backdrop-blur rounded-xl text-sm text-slate-900 focus:ring-2 focus:ring-blue-500/20 outline-none"
              >
                {portfolios.map(p => (
                  <option key={p.id} value={p.id}>{p.name} ({p.instruments.length} instr)</option>
                ))}
              </select>
              {selectedPortfolio && (
                <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                  <div className="glass-light p-2 text-center">
                    <p className="text-slate-500">Total</p>
                    <p className="font-bold text-slate-900">{formatCurrency(baseMetrics.total)}</p>
                  </div>
                  <div className="glass-light p-2 text-center">
                    <p className="text-slate-500">Annual cost</p>
                    <p className="font-bold text-slate-900 tabular-nums">{formatCurrency(baseMetrics.beforeCost)}</p>
                  </div>
                </div>
              )}
            </Card>

            {/* Live Shocks — glass cards with sliders */}
            <Card>
              <CardHeader title="Live Shocks" subtitle="Drag to recompute instantly" />
              <div className="space-y-5">
                <ShockSlider label="Rate shift" value={rateShiftBps} min={-200} max={300} step={25} unit=" bps" onChange={setRateShiftBps} />
                <ShockSlider label="FX shock" value={fxShockPct} min={-30} max={30} step={1} unit="%" onChange={setFxShockPct} />
                <ShockSlider label="Inflation shock" value={inflationShockBps} min={-100} max={300} step={25} unit=" bps" onChange={setInflationShockBps} />
              </div>
              <div className="mt-4 grid grid-cols-3 gap-2 text-[11px]">
                <div className="bg-white/50 backdrop-blur rounded-xl p-2 border border-white/30 text-center">
                  <p className="text-slate-500">Rate impact</p>
                  <p className={`font-bold tabular-nums ${liveMetrics.rateImpact > 0 ? 'text-amber-600' : liveMetrics.rateImpact < 0 ? 'text-emerald-600' : 'text-slate-700'}`}>{(liveMetrics.rateImpact * 100).toFixed(1)}%</p>
                </div>
                <div className="bg-white/50 backdrop-blur rounded-xl p-2 border border-white/30 text-center">
                  <p className="text-slate-500">FX impact</p>
                  <p className={`font-bold tabular-nums ${liveMetrics.fxImpact > 0 ? 'text-amber-600' : liveMetrics.fxImpact < 0 ? 'text-emerald-600' : 'text-slate-700'}`}>{(liveMetrics.fxImpact * 100).toFixed(1)}%</p>
                </div>
                <div className="bg-white/50 backdrop-blur rounded-xl p-2 border border-white/30 text-center">
                  <p className="text-slate-500">Infl impact</p>
                  <p className={`font-bold tabular-nums ${liveMetrics.inflImpact > 0 ? 'text-amber-600' : 'text-slate-700'}`}>{(liveMetrics.inflImpact * 100).toFixed(1)}%</p>
                </div>
              </div>
            </Card>

            <Card>
              <CardHeader title="Quick Scenarios" subtitle="Click to apply preset" />
              <div className="space-y-2">
                {PRESET_SCENARIOS.map((preset, i) => (
                  <button
                    key={i}
                    onClick={() => applyPreset(preset)}
                    className="w-full text-left px-3 py-2.5 rounded-xl border border-white/40 bg-white/40 backdrop-blur hover:border-blue-300 hover:bg-blue-50/60 transition-colors text-sm font-medium text-slate-700"
                  >
                    {preset.name}
                  </button>
                ))}
              </div>
            </Card>

            <Card>
              <CardHeader title="New Issuance" subtitle="Add a bond to scenario" />
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs font-medium text-slate-500">Currency</label>
                    <select value={newCurrency} onChange={e => setNewCurrency(e.target.value)}
                      className="w-full px-2 py-1.5 border border-white/40 bg-white/60 backdrop-blur rounded-xl text-sm mt-1">
                      <option>USD</option><option>EUR</option><option>GBP</option><option>JPY</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-slate-500">Tenor (years)</label>
                    <select value={newTenor} onChange={e => setNewTenor(e.target.value)}
                      className="w-full px-2 py-1.5 border border-white/40 bg-white/60 backdrop-blur rounded-xl text-sm mt-1">
                      <option value="2">2Y</option><option value="5">5Y</option><option value="7">7Y</option>
                      <option value="10">10Y</option><option value="20">20Y</option><option value="30">30Y</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-500">Amount ($)</label>
                  <input type="number" value={newAmount} onChange={e => setNewAmount(e.target.value)}
                    className="w-full px-2 py-1.5 border border-white/40 bg-white/60 backdrop-blur rounded-xl text-sm mt-1" />
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-500">Coupon Rate (%)</label>
                  <input type="number" value={newCoupon} onChange={e => setNewCoupon(e.target.value)}
                    step="0.1" className="w-full px-2 py-1.5 border border-white/40 bg-white/60 backdrop-blur rounded-xl text-sm mt-1" />
                </div>
                <Button variant="secondary" size="sm" fullWidth onClick={addNewIssuance}>+ Add to Scenario</Button>
              </div>
            </Card>
          </div>

          {/* Middle: Adjustments + Live results */}
          <div className="space-y-6">
            <Card>
              <CardHeader
                title="Active Adjustments"
                subtitle={`${adjustments.length} adjustment(s) configured`}
              />
              {adjustments.length === 0 ? (
                <p className="text-sm text-slate-400 text-center py-6">
                  Use quick scenarios or add issuance
                </p>
              ) : (
                <div className="space-y-2">
                  {adjustments.map((adj, i) => (
                    <div key={i} className="flex items-center justify-between p-3 bg-white/50 backdrop-blur-xl rounded-2xl border border-white/40">
                      <div>
                        <p className="text-sm font-medium text-slate-900">{adj.label}</p>
                        <p className="text-xs text-slate-500">
                          {adj.action === 'new_issuance' ? `${formatCurrency(adj.amount)} @ ${(adj.coupon_rate || 0) * 100}%` : `${adj.action} ${formatCurrency(adj.amount)}`}
                        </p>
                      </div>
                      <button onClick={() => removeAdjustment(i)} className="text-red-400 hover:text-red-600 p-1">
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  ))}
                </div>
              )}

              <div className="mt-4">
                <Button
                  variant="primary" size="md" fullWidth
                  onClick={analyze}
                  disabled={adjustments.length === 0 || analyzing}
                >
                  {analyzing ? 'Analyzing...' : 'Run Analysis (backend)'}
                </Button>
              </div>
            </Card>

            {/* Live shocked metrics — always visible */}
            <Card>
              <CardHeader title="Live Shock Impact" subtitle="Recomputed via: cost×(1+rate·dur/10000+fxExp·fxShock+infl·0.5/10000)" />
              <div className="grid grid-cols-2 gap-3">
                <div className="glass-light p-3">
                  <p className="text-xs text-slate-500">Annual cost (base)</p>
                  <p className="text-lg font-bold text-slate-900 tabular-nums">{formatCurrency(baseMetrics.beforeCost)}</p>
                </div>
                <div className={`p-3 rounded-2xl border backdrop-blur-xl ${liveMetrics.deltaPct > 10 ? 'bg-red-500/10 border-red-500/20' : liveMetrics.deltaPct > 5 ? 'bg-amber-500/10 border-amber-500/20' : 'bg-emerald-500/10 border-emerald-500/20'}`}>
                  <p className="text-xs text-slate-600">Annual cost (shocked)</p>
                  <p className="text-lg font-bold tabular-nums text-slate-900">{formatCurrency(liveMetrics.shockedCost)}</p>
                  <p className={`text-xs font-semibold tabular-nums ${liveMetrics.deltaPct > 0 ? 'text-red-600' : 'text-emerald-600'}`}>{liveMetrics.deltaPct > 0 ? '+' : ''}{liveMetrics.deltaPct.toFixed(2)}% ({liveMetrics.deltaCost > 0 ? '+' : ''}{formatCurrency(liveMetrics.deltaCost)})</p>
                </div>
                <div className="glass-light p-3">
                  <p className="text-xs text-slate-500">Coupon (base)</p>
                  <p className="text-sm font-bold text-slate-900 tabular-nums">{baseMetrics.beforeCoupon.toFixed(2)}%</p>
                </div>
                <div className="glass-light p-3">
                  <p className="text-xs text-slate-500">Coupon (shocked)</p>
                  <p className="text-sm font-bold text-slate-900 tabular-nums">{liveMetrics.shockedCoupon.toFixed(2)}%</p>
                </div>
              </div>
              <div className="mt-4">
                <ResponsiveContainer width="100%" height={160}>
                  <BarChart data={liveData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#64748b' }} />
                    <YAxis tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={(v: number) => `$${(v / 1e9).toFixed(1)}B`} />
                    <Tooltip formatter={(value) => [`$${(Number(value) / 1e9).toFixed(2)}B`, 'Annual Cost']} contentStyle={{ borderRadius: 12, background: 'rgba(255,255,255,0.9)', backdropFilter: 'blur(12px)' }} />
                    <Bar dataKey="cost" radius={[8, 8, 0, 0]}>
                      {liveData.map((entry, idx) => <Cell key={idx} fill={entry.fill} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>

            {/* Breach warnings — glass badges */}
            <Card>
              <CardHeader title="Breach Warnings" subtitle="Thresholds: cost +15% danger, +8% warn, coupon 6%, FX ±20%" />
              {breachWarnings.length === 0 ? (
                <div className="flex items-center gap-2 text-sm text-emerald-700 bg-emerald-500/10 border border-emerald-500/20 rounded-xl px-3 py-2.5 backdrop-blur">
                  ✓ All metrics within appetite — shocks are contained
                </div>
              ) : (
                <div className="space-y-2">
                  {breachWarnings.map((w, i) => (
                    <div key={i} className={`flex items-start gap-2 p-3 rounded-xl border backdrop-blur ${w.level === 'danger' ? 'bg-red-500/10 border-red-500/20 text-red-800' : 'bg-amber-500/10 border-amber-500/20 text-amber-800'}`}>
                      <Badge variant={w.level === 'danger' ? 'danger' : 'warning'}>{w.level.toUpperCase()}</Badge>
                      <span className="text-xs font-medium leading-snug">{w.msg}</span>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            {result && (
              <>
                <Card>
                  <CardHeader title="Backend Impact Summary" />
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-slate-600">Portfolio Change</span>
                      <span className={`text-sm font-bold tabular-nums ${result.impact.total_change >= 0 ? 'text-blue-700' : 'text-red-700'}`}>
                        {result.impact.total_change >= 0 ? '+' : ''}{formatCurrency(result.impact.total_change)} ({result.impact.total_change_pct >= 0 ? '+' : ''}{result.impact.total_change_pct.toFixed(1)}%)
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-slate-600">Coupon Change</span>
                      <span className={`text-sm font-bold tabular-nums ${result.impact.coupon_change_bps <= 0 ? 'text-emerald-700' : 'text-amber-700'}`}>
                        {result.impact.coupon_change_bps >= 0 ? '+' : ''}{result.impact.coupon_change_bps.toFixed(0)} bps
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-slate-600">Annual Cost Change</span>
                      <span className={`text-sm font-bold tabular-nums ${result.impact.annual_cost_change <= 0 ? 'text-emerald-700' : 'text-red-700'}`}>
                        {result.impact.annual_cost_change >= 0 ? '+' : ''}{formatCurrency(result.impact.annual_cost_change)} ({result.impact.annual_cost_change_pct >= 0 ? '+' : ''}{result.impact.annual_cost_change_pct.toFixed(1)}%)
                      </span>
                    </div>
                  </div>
                  <div className="mt-3 p-2.5 bg-blue-500/10 backdrop-blur border border-blue-500/20 rounded-xl text-xs text-blue-800">
                    {result.recommendation}
                  </div>
                </Card>

                <Card>
                  <CardHeader title="Annual Cost Comparison (backend)" />
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={impactData} margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#64748b' }} />
                      <YAxis tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={(v: number) => `$${(v / 1e9).toFixed(1)}B`} />
                      <Tooltip formatter={(value) => [`$${(Number(value) / 1e9).toFixed(2)}B`, 'Annual Cost']} contentStyle={{ borderRadius: 12 }} />
                      <Bar dataKey="cost" radius={[4, 4, 0, 0]}>
                        <Cell fill="#3b82f6" />
                        <Cell fill={result.impact.annual_cost_change <= 0 ? '#10b981' : '#ef4444'} />
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </Card>
              </>
            )}
          </div>

          {/* Right: Context + before/after table */}
          <div className="space-y-6">
            <Card>
              <CardHeader title="Before / After (Live)" subtitle="Shocked vs base" />
              <div className="overflow-hidden rounded-xl border border-white/40">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="bg-white/40 backdrop-blur">
                      <th className="text-left px-3 py-2 font-semibold text-slate-600">Metric</th>
                      <th className="text-right px-3 py-2 font-semibold text-slate-600">Base</th>
                      <th className="text-right px-3 py-2 font-semibold text-slate-600">Shocked</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/30">
                    <tr className="hover:bg-white/30">
                      <td className="px-3 py-2 text-slate-600">Total</td>
                      <td className="px-3 py-2 text-right font-semibold tabular-nums text-slate-900">{formatCurrency(baseMetrics.total)}</td>
                      <td className="px-3 py-2 text-right font-semibold tabular-nums text-slate-900">{formatCurrency(liveMetrics.shockedTotal)}</td>
                    </tr>
                    <tr className="hover:bg-white/30">
                      <td className="px-3 py-2 text-slate-600">Coupon</td>
                      <td className="px-3 py-2 text-right font-semibold tabular-nums text-slate-900">{baseMetrics.beforeCoupon.toFixed(2)}%</td>
                      <td className="px-3 py-2 text-right font-semibold tabular-nums text-slate-900">{liveMetrics.shockedCoupon.toFixed(2)}%</td>
                    </tr>
                    <tr className="hover:bg-white/30">
                      <td className="px-3 py-2 text-slate-600">Annual cost</td>
                      <td className="px-3 py-2 text-right font-semibold tabular-nums text-slate-900">{formatCurrency(baseMetrics.beforeCost)}</td>
                      <td className={`px-3 py-2 text-right font-bold tabular-nums ${liveMetrics.deltaPct > 10 ? 'text-red-600' : liveMetrics.deltaPct > 5 ? 'text-amber-600' : 'text-emerald-600'}`}>{formatCurrency(liveMetrics.shockedCost)}</td>
                    </tr>
                    <tr className="hover:bg-white/30">
                      <td className="px-3 py-2 text-slate-600">Δ Cost</td>
                      <td colSpan={2} className={`px-3 py-2 text-right font-bold tabular-nums ${liveMetrics.deltaPct > 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                        {liveMetrics.deltaPct > 0 ? '+' : ''}{liveMetrics.deltaPct.toFixed(2)}% • {liveMetrics.deltaCost > 0 ? '+' : ''}{formatCurrency(liveMetrics.deltaCost)}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div className="mt-3 p-2.5 rounded-xl bg-slate-900 text-white text-[11px] leading-relaxed">
                <span className="font-mono">cost = base × (1 + rate×dur/10000 + fxExp×fxShock + infl×0.5/10000)</span>
                <br />
                <span className="text-slate-300">dur={duration}y, fxExp={(fxExposure*100).toFixed(0)}% • rate={rateShiftBps}bps, fx={fxShockPct}%, infl={inflationShockBps}bps</span>
              </div>
            </Card>

            <Card>
              <CardHeader title="How It Works" subtitle="Understanding what-if analysis" />
              <div className="space-y-3 text-xs text-slate-600 leading-relaxed">
                <p><strong>1. Select portfolio</strong> — base total, coupon and annual cost calibrate the model.</p>
                <p><strong>2. Move shocks</strong> — rate (-200→+300bps), FX (-30→+30%), inflation (-100→+300bps) recompute live.</p>
                <p><strong>3. Check breaches</strong> — glass badges warn when cost &gt;15%, coupon &gt;6% or FX &gt;20%.</p>
                <p><strong>4. Run backend analysis</strong> — adjustments sent to <span className="font-mono">/whatif/analyze</span> for full revaluation.</p>
              </div>
            </Card>

            {result && (
              <Card>
                <CardHeader title="Backend Detailed Changes" />
                <div className="space-y-2">
                  {result.adjustments.map((adj, i) => (
                    <div key={i} className="text-xs p-2.5 bg-white/40 backdrop-blur rounded-xl border border-white/30">
                      <p className="font-medium text-slate-900">{adj.impact}</p>
                      <p className="text-[11px] text-slate-500 mt-0.5">{adj.type} • {formatCurrency(adj.amount)}</p>
                    </div>
                  ))}
                </div>
                <div className="mt-4 space-y-2 text-xs">
                  <div className="flex justify-between py-1.5 border-b border-white/30">
                    <span className="text-slate-500">Principal Before</span>
                    <span className="font-semibold text-slate-900">{formatCurrency(result.before.total_principal)}</span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-white/30">
                    <span className="text-slate-500">Principal After</span>
                    <span className="font-semibold text-slate-900">{formatCurrency(result.after.total_principal)}</span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-white/30">
                    <span className="text-slate-500">Coupon Before</span>
                    <span className="font-semibold text-slate-900">{result.before.weighted_coupon_pct.toFixed(2)}%</span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-white/30">
                    <span className="text-slate-500">Coupon After</span>
                    <span className="font-semibold text-slate-900">{result.after.weighted_coupon_pct.toFixed(2)}%</span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-white/30">
                    <span className="text-slate-500">Annual Cost Before</span>
                    <span className="font-semibold text-slate-900">{formatCurrency(result.before.annual_cost)}</span>
                  </div>
                  <div className="flex justify-between py-1.5">
                    <span className="text-slate-500">Annual Cost After</span>
                    <span className="font-semibold text-slate-900">{formatCurrency(result.after.annual_cost)}</span>
                  </div>
                </div>
              </Card>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
