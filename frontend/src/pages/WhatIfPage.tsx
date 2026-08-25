import { useState, useEffect } from 'react';
import { api } from '../api';
import AppShell from '../components/layout/AppShell';
import Card, { CardHeader } from '../components/ui/Card';
import Button from '../components/ui/Button';
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

export default function WhatIfPage() {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [adjustments, setAdjustments] = useState<Adjustment[]>([]);
  const [result, setResult] = useState<WhatIfResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);

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
      setResult(res);
    } catch {
      // Silently handle
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

  if (loading) return <AppShell><LoadingSpinner message="Loading portfolios..." /></AppShell>;

  const impactData = result ? [
    { name: 'Before', cost: result.before.annual_cost },
    { name: 'After', cost: result.after.annual_cost },
  ] : [];

  return (
    <AppShell>
      <div className="px-8 py-6 max-w-[1440px] mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">What-If Playground</h1>
            <p className="text-sm text-slate-500 mt-0.5">Simulate portfolio adjustments and see the impact instantly</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Controls */}
          <div className="space-y-6">
            <Card>
              <CardHeader title="Portfolio" subtitle="Select a portfolio to modify" />
              <select
                value={selectedId || ''}
                onChange={e => { setSelectedId(e.target.value); setResult(null); setAdjustments([]); }}
                className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm text-slate-900 focus:ring-2 focus:ring-blue-500"
              >
                {portfolios.map(p => (
                  <option key={p.id} value={p.id}>{p.name} ({p.instruments.length} instruments)</option>
                ))}
              </select>
            </Card>

            <Card>
              <CardHeader title="Quick Scenarios" subtitle="Click to apply a preset adjustment" />
              <div className="space-y-2">
                {PRESET_SCENARIOS.map((preset, i) => (
                  <button
                    key={i}
                    onClick={() => applyPreset(preset)}
                    className="w-full text-left px-3 py-2 rounded-md border border-white/40 hover:border-blue-300 hover:bg-blue-50 transition-colors text-sm"
                  >
                    {preset.name}
                  </button>
                ))}
              </div>
            </Card>

            <Card>
              <CardHeader title="New Issuance" subtitle="Add a new bond to the portfolio" />
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs font-medium text-slate-500">Currency</label>
                    <select value={newCurrency} onChange={e => setNewCurrency(e.target.value)}
                      className="w-full px-2 py-1.5 border border-white/40 rounded text-sm mt-1">
                      <option>USD</option><option>EUR</option><option>GBP</option><option>JPY</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-slate-500">Tenor (years)</label>
                    <select value={newTenor} onChange={e => setNewTenor(e.target.value)}
                      className="w-full px-2 py-1.5 border border-white/40 rounded text-sm mt-1">
                      <option value="2">2Y</option><option value="5">5Y</option><option value="7">7Y</option>
                      <option value="10">10Y</option><option value="20">20Y</option><option value="30">30Y</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-500">Amount ($)</label>
                  <input type="number" value={newAmount} onChange={e => setNewAmount(e.target.value)}
                    className="w-full px-2 py-1.5 border border-white/40 rounded text-sm mt-1" />
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-500">Coupon Rate (%)</label>
                  <input type="number" value={newCoupon} onChange={e => setNewCoupon(e.target.value)}
                    step="0.1" className="w-full px-2 py-1.5 border border-white/40 rounded text-sm mt-1" />
                </div>
                <Button variant="secondary" size="sm" fullWidth onClick={addNewIssuance}>+ Add to Scenario</Button>
              </div>
            </Card>
          </div>

          {/* Middle: Adjustments */}
          <div className="space-y-6">
            <Card>
              <CardHeader
                title="Active Adjustments"
                subtitle={`${adjustments.length} adjustment(s) configured`}
              />
              {adjustments.length === 0 ? (
                <p className="text-sm text-slate-400 text-center py-6">
                  Use the quick scenarios or add a new issuance
                </p>
              ) : (
                <div className="space-y-2">
                  {adjustments.map((adj, i) => (
                    <div key={i} className="flex items-center justify-between p-2 bg-white/30 backdrop-blur-xl rounded-2xl border border-white/30 border border-white/25">
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
                  {analyzing ? 'Analyzing...' : 'Run Analysis'}
                </Button>
              </div>
            </Card>

            {result && (
              <>
                <Card>
                  <CardHeader title="Impact Summary" />
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
                  <div className="mt-3 p-2 bg-blue-50 rounded-md text-xs text-blue-700">
                    {result.recommendation}
                  </div>
                </Card>

                <Card>
                  <CardHeader title="Annual Cost Comparison" />
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={impactData} margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                      <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => `$${(v / 1e9).toFixed(1)}B`} />
                      <Tooltip formatter={(value) => [`$${(Number(value) / 1e9).toFixed(2)}B`, 'Annual Cost']} />
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

          {/* Right: Context */}
          <div className="space-y-6">
            <Card>
              <CardHeader title="How It Works" subtitle="Understanding what-if analysis" />
              <div className="space-y-3 text-xs text-slate-600 leading-relaxed">
                <p>
                  <strong>1. Select a portfolio</strong> — Choose the debt portfolio you want to simulate changes for.
                </p>
                <p>
                  <strong>2. Add adjustments</strong> — Use quick scenarios or manually add new issuances with specific currencies, tenors, and coupon rates.
                </p>
                <p>
                  <strong>3. Run analysis</strong> — See the impact on total principal, weighted average coupon, and annual financing cost.
                </p>
                <p>
                  <strong>4. Compare results</strong> — Before vs. After comparison with exact dollar amounts and percentage changes.
                </p>
              </div>
            </Card>

            {result && (
              <Card>
                <CardHeader title="Detailed Changes" />
                <div className="space-y-2">
                  {result.adjustments.map((adj, i) => (
                    <div key={i} className="text-xs p-2 bg-slate-50 rounded border border-white/25">
                      <p className="font-medium text-slate-900">{adj.impact}</p>
                    </div>
                  ))}
                </div>
                <div className="mt-4 space-y-2 text-xs">
                  <div className="flex justify-between py-1 border-b border-white/25">
                    <span className="text-slate-500">Principal Before</span>
                    <span className="font-semibold text-slate-900">{formatCurrency(result.before.total_principal)}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-white/25">
                    <span className="text-slate-500">Principal After</span>
                    <span className="font-semibold text-slate-900">{formatCurrency(result.after.total_principal)}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-white/25">
                    <span className="text-slate-500">Coupon Before</span>
                    <span className="font-semibold text-slate-900">{result.before.weighted_coupon_pct.toFixed(2)}%</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-white/25">
                    <span className="text-slate-500">Coupon After</span>
                    <span className="font-semibold text-slate-900">{result.after.weighted_coupon_pct.toFixed(2)}%</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-white/25">
                    <span className="text-slate-500">Annual Cost Before</span>
                    <span className="font-semibold text-slate-900">{formatCurrency(result.before.annual_cost)}</span>
                  </div>
                  <div className="flex justify-between py-1">
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
