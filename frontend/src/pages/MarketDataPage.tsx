import { useState, useEffect, useCallback } from 'react';
import { api } from '../api';
import AppShell from '../components/layout/AppShell';
import Card, { CardHeader } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import Button from '../components/ui/Button';
import type { YieldCurve, FxRate, InterestRate, EconomicIndicator } from '../types';
import {
  BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  AreaChart, Area, Cell,
} from 'recharts';

type Tab = 'yield' | 'fx' | 'rates' | 'economic';

const CURRENCY_COLORS: Record<string, string> = {
  USD: '#3b82f6', EUR: '#10b981', GBP: '#8b5cf6', JPY: '#f59e0b', CHF: '#ef4444', CAD: '#06b6d4', AUD: '#f97316', CNY: '#ec4899',
};

function YieldCurveChart({ data }: { data: YieldCurve }) {
  const chartData = data.maturities.map(m => ({
    label: m.label,
    rate: m.rate_pct,
    months: m.months,
  }));

  return (
    <Card>
      <CardHeader
        title="US Treasury Yield Curve"
        subtitle={`As of ${data.date} — Source: ${data.source}`}
      />
      {data.twoTenSpreadBps !== null && (
        <div className="px-6 pb-2 flex items-center gap-3">
          <span className="text-xs font-medium text-slate-500">2Y-10Y Spread:</span>
          <Badge variant={data.twoTenSpreadBps > 0 ? 'success' : 'danger'}>
            {data.twoTenSpreadBps > 0 ? '+' : ''}{data.twoTenSpreadBps.toFixed(0)} bps
          </Badge>
        </div>
      )}
      <div className="px-4 pb-4">
        <ResponsiveContainer width="100%" height={320}>
          <AreaChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="yieldGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.01} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="label" tick={{ fontSize: 12, fill: '#64748b' }} />
            <YAxis tick={{ fontSize: 12, fill: '#64748b' }} tickFormatter={(v: number) => `${v}%`} />
            <Tooltip
              contentStyle={{ borderRadius: 8, border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
              formatter={(value) => [`${Number(value).toFixed(2)}%`, 'Yield']}
              labelFormatter={(label) => `Maturity: ${String(label)}`}
            />
            <Area type="monotone" dataKey="rate" stroke="#3b82f6" strokeWidth={2.5} fill="url(#yieldGradient)" dot={{ r: 4, fill: '#3b82f6' }} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}

function FxRatesCard({ rates }: { rates: Record<string, FxRate> }) {
  const entries = Object.entries(rates).sort((a, b) => b[1].rate - a[1].rate);
  return (
    <Card>
      <CardHeader title="Foreign Exchange Rates" subtitle={`Base: USD — ${entries[0]?.[1].date || ''}`} />
      <div className="px-6 pb-4">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {entries.slice(0, 12).map(([pair, data]) => {
            const displayPair = pair.replace('USD', '').replace('USD_', '');
            const color = CURRENCY_COLORS[displayPair] || '#64748b';
            return (
              <div key={pair} className="bg-white/30 backdrop-blur-xl rounded-2xl border border-white/30 p-3 border border-white/25">
                <div className="flex items-center gap-2 mb-1">
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
                  <span className="text-xs font-semibold text-slate-600 uppercase">{displayPair}</span>
                </div>
                <p className="text-lg font-bold text-slate-900 tabular-nums">
                  {data.rate.toFixed(displayPair === 'JPY' ? 2 : 4)}
                </p>
                <p className="text-[10px] text-slate-400 mt-0.5">{data.name}</p>
              </div>
            );
          })}
        </div>
        {entries.length > 12 && (
          <div className="mt-4 overflow-x-auto">
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={entries.slice(12).map(([pair, data]) => ({
                pair: pair.replace('USD', '').replace('USD_', ''),
                rate: data.rate,
              }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="pair" tick={{ fontSize: 11, fill: '#64748b' }} />
                <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
                <Tooltip contentStyle={{ borderRadius: 8, border: '1px solid #e2e8f0' }} />
                <Bar dataKey="rate" radius={[4, 4, 0, 0]}>
                  {entries.slice(12).map(([pair]) => (
                    <Cell key={pair} fill={CURRENCY_COLORS[pair.replace('USD', '').replace('USD_', '')] || '#94a3b8'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </Card>
  );
}

function InterestRatesCard({ rates, summary }: { rates: InterestRate[]; summary: Record<string, number> }) {
  return (
    <Card>
      <CardHeader title="Benchmark Interest Rates" subtitle="Key policy and market rates" />
      <div className="px-6 pb-4 space-y-3">
        {summary && Object.entries(summary).length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
            {Object.entries(summary).slice(0, 8).map(([key, value]) => (
              <div key={key} className="bg-white/30 backdrop-blur-xl rounded-2xl border border-white/30 p-3 border border-white/25">
                <p className="text-xs font-medium text-slate-500 uppercase truncate">{key.replace(/_/g, ' ')}</p>
                <p className="text-xl font-bold text-slate-900 tabular-nums mt-1">{value.toFixed(2)}%</p>
              </div>
            ))}
          </div>
        )}
        <div className="space-y-2">
          {rates.map((rate, i) => (
            <div key={i} className="flex items-center justify-between py-2 border-b border-white/25 last:border-0">
              <div>
                <p className="text-sm font-medium text-slate-800">{rate.name}</p>
                <p className="text-xs text-slate-400">{rate.source} — {rate.date}</p>
              </div>
              <div className="text-right">
                <span className="text-lg font-bold text-slate-900 tabular-nums">{rate.value.toFixed(2)}%</span>
                <p className="text-[10px] text-slate-400">{rate.unit}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}

function EconomicCard({ data, country }: { data: EconomicIndicator[]; country: string }) {
  return (
    <Card>
      <CardHeader
        title={`Economic Indicators — ${country.toUpperCase()}`}
        subtitle="Key macroeconomic metrics"
      />
      <div className="px-6 pb-4">
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data.map(d => ({ name: d.name.substring(0, 20), value: d.value, unit: d.unit }))} layout="vertical" margin={{ left: 100 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis type="number" tick={{ fontSize: 11, fill: '#64748b' }} />
            <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: '#64748b' }} width={100} />
            <Tooltip
              contentStyle={{ borderRadius: 8, border: '1px solid #e2e8f0' }}
              formatter={(value, _name, props) => [`${Number(value).toLocaleString()} ${props?.payload?.unit ?? ''}`, 'Value']}
            />
            <Bar dataKey="value" radius={[0, 4, 4, 0]} fill="#3b82f6" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}

export default function MarketDataPage() {
  const [activeTab, setActiveTab] = useState<Tab>('yield');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [yieldCurve, setYieldCurve] = useState<YieldCurve | null>(null);
  const [fxRates, setFxRates] = useState<Record<string, FxRate> | null>(null);
  const [interestRates, setInterestRates] = useState<{ rates: InterestRate[]; summary: Record<string, number> } | null>(null);
  const [economicData, setEconomicData] = useState<Record<string, EconomicIndicator[]> | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const snap = await api.market.snapshot();
      if (snap.yield_curve) setYieldCurve(snap.yield_curve as YieldCurve);
      if (snap.interest_rates) setInterestRates(snap.interest_rates as { rates: InterestRate[]; summary: Record<string, number> });
      if (snap.fx_rates) {
        const ratesObj: Record<string, FxRate> = {};
        Object.entries(snap.fx_rates).forEach(([k, v]) => {
          if (typeof v === 'number') {
            ratesObj[k] = { currency: k, rate: v, name: k, source: 'ECB', date: new Date().toISOString().split('T')[0] };
          }
        });
        setFxRates(ratesObj);
      }
      setLastRefresh(new Date());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to fetch market data');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchEconomic = useCallback(async (country: string) => {
    try {
      const data = await api.market.economic(country);
      setEconomicData(prev => ({ ...prev, [country]: data }));
    } catch {
      // silently fail
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);
  useEffect(() => {
    if (activeTab === 'economic' && !economicData?.US) {
      fetchEconomic('US');
    }
  }, [activeTab, economicData, fetchEconomic]);

  const tabs: { key: Tab; label: string; icon: string }[] = [
    { key: 'yield', label: 'Yield Curve', icon: '📈' },
    { key: 'fx', label: 'FX Rates', icon: '💱' },
    { key: 'rates', label: 'Interest Rates', icon: '🏦' },
    { key: 'economic', label: 'Economic', icon: '🌍' },
  ];

  return (
    <AppShell>
      <div className="px-8 py-6 max-w-[1440px] mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Live Market Data</h1>
            <p className="text-sm text-slate-500 mt-0.5">
              Real-time data from free government sources — no API keys required
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-400">
              Last updated: {lastRefresh.toLocaleTimeString()}
            </span>
            <Button variant="secondary" size="sm" onClick={fetchData} leftIcon={<span>↻</span>}>
              Refresh
            </Button>
          </div>
        </div>

        {/* Connection Status */}
        <div className="flex items-center gap-2 mb-6">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
          </span>
          <span className="text-xs font-medium text-emerald-700">Live Connection — US Treasury, ECB, NY Fed, World Bank</span>
        </div>

        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
            <strong>Error:</strong> {error}
            <button onClick={fetchData} className="ml-3 underline font-medium">Retry</button>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-1 mb-6 bg-slate-100 rounded-lg p-1 w-fit">
          {tabs.map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-all ${
                activeTab === tab.key
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              {tab.icon} {tab.label}
            </button>
          ))}
        </div>

        {loading && !yieldCurve && (
          <LoadingSpinner message="Fetching live market data..." />
        )}

        {/* Content */}
        {!loading && (
          <div className="space-y-6">
            {activeTab === 'yield' && (
              <>
                {yieldCurve ? (
                  <YieldCurveChart data={yieldCurve} />
                ) : (
                  <Card>
                    <div className="p-12 text-center text-slate-400">
                      <p className="text-lg mb-2">📉</p>
                      <p>Yield curve data unavailable. The US Treasury may be experiencing downtime.</p>
                      <Button variant="secondary" size="sm" onClick={fetchData} className="mt-4">Retry</Button>
                    </div>
                  </Card>
                )}
                {/* Quick Stats */}
                {yieldCurve && (
                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                    {yieldCurve.maturities.filter(m => ['3M', '1Y', '2Y', '10Y', '30Y'].includes(m.label)).map(m => (
                      <div key={m.label} className="glass-card p-3 text-center">
                        <p className="text-xs font-medium text-slate-500">{m.label}</p>
                        <p className="text-xl font-bold text-slate-900 tabular-nums mt-1">{m.rate_pct.toFixed(2)}%</p>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}

            {activeTab === 'fx' && fxRates && (
              <FxRatesCard rates={fxRates} />
            )}

            {activeTab === 'rates' && interestRates && (
              <InterestRatesCard rates={interestRates.rates} summary={interestRates.summary} />
            )}

            {activeTab === 'economic' && (
              <>
                <div className="flex gap-2 mb-4">
                  {['US', 'GB', 'JP', 'DE'].map(country => (
                    <button
                      key={country}
                      onClick={() => fetchEconomic(country)}
                      className={`px-3 py-1.5 text-xs font-medium rounded-md border transition-all ${
                        economicData?.[country]
                          ? 'bg-blue-50 border-blue-200 text-blue-700'
                          : 'bg-white border-white/40 text-slate-600 hover:border-slate-300'
                      }`}
                    >
                      {country}
                    </button>
                  ))}
                </div>
                {economicData?.US ? (
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {Object.entries(economicData).map(([country, data]) => (
                      <EconomicCard key={country} data={data} country={country} />
                    ))}
                  </div>
                ) : (
                  <Card>
                    <div className="p-12 text-center text-slate-400">
                      <p className="text-lg mb-2">🌍</p>
                      <p>Select a country above to view economic indicators.</p>
                    </div>
                  </Card>
                )}
              </>
            )}
          </div>
        )}

        {/* Data Sources */}
        <div className="mt-8 pt-6 border-t border-white/40">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Data Sources (Free, No API Keys)</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { name: 'US Treasury', url: 'home.treasury.gov', data: 'Yield Curve' },
              { name: 'ECB', url: 'ecb.europa.eu', data: 'EUR FX Rates' },
              { name: 'NY Fed', url: 'newyorkfed.org', data: 'SOFR, Fed Funds' },
              { name: 'World Bank', url: 'data.worldbank.org', data: 'CPI, GDP' },
            ].map(src => (
              <div key={src.name} className="bg-white/30 backdrop-blur-xl rounded-2xl border border-white/30 p-3 border border-white/25">
                <p className="text-xs font-semibold text-slate-700">{src.name}</p>
                <p className="text-[10px] text-slate-400 mt-0.5">{src.data}</p>
                <p className="text-[10px] text-blue-500 mt-1">{src.url}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
