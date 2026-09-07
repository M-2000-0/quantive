import { useCallback, useEffect, useState } from 'react';
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  Bitcoin,
  Coins,
  DollarSign,
  Flame,
  Gem,
  Globe,
  Loader2,
  RefreshCw,
  TrendingDown,
  TrendingUp,
  Zap } from 'lucide-react';
import { api } from '../api';

// ── Types ──────────────────────────────────────────────────────────

interface CryptoPrice {
  id: string;
  symbol: string;
  name: string;
  current_price: number;
  market_cap: number;
  market_cap_rank: number;
  total_volume: number;
  price_change_percentage_24h: number;
  price_change_percentage_7d_in_currency: number;
  price_change_percentage_30d_in_currency: number;
  ath: number;
  ath_change_percentage: number;
  circulating_supply: number;
  total_supply: number;
}

interface Commodity {
  symbol: string;
  name: string;
  category: string;
  unit: string;
  price: number;
  previous_close: number;
  change_pct: number;
  market_state: string;
}

interface FxPair {
  pair: string;
  name: string;
  category: string;
  rate: number;
  previous_close: number;
  change_pct: number;
  market_state: string;
}

interface FearGreed {
  current_value: number;
  current_label: string;
  history: Array<{ value: number; label: string; date: string }>;
  interpretation: string;
}

interface AssetData {
  crypto: {
    prices: CryptoPrice[];
    total_market_cap_usd: number;
    total_volume_24h_usd: number;
    btc_dominance_pct: number;
    tracked_count: number;
  };
  commodities: {
    commodities: Commodity[];
    categories: Record<string, Commodity[]>;
    tracked_count: number;
  };
  fx: {
    pairs: FxPair[];
    categories: Record<string, FxPair[]>;
    tracked_count: number;
  };
  fear_greed_index: FearGreed;
  summary: {
    crypto_market_cap: number;
    btc_dominance: number;
    tracked_assets: number;
    fear_greed_value: number;
    fear_greed_label: string;
  };
  fetched_at: string;
}

// ── Helpers ─────────────────────────────────────────────────────────

function formatPrice(value: number): string {
  if (value >= 1e12) return `$${(value / 1e12).toFixed(2)}T`;
  if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
  if (value >= 1000) return `$${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
  if (value >= 1) return `$${value.toFixed(2)}`;
  return `$${value.toFixed(4)}`;
}

function formatCompact(value: number): string {
  if (value >= 1e12) return `${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function changeColor(pct: number): string {
  if (pct > 0) return '#10b981';
  if (pct < 0) return '#ef4444';
  return '#6b7280';
}

function fearGreedColor(value: number): string {
  if (value <= 20) return '#ef4444';
  if (value <= 40) return '#f97316';
  if (value <= 60) return '#eab308';
  if (value <= 80) return '#22c55e';
  return '#10b981';
}

function fearGreedBg(value: number): string {
  if (value <= 20) return '#fef2f2';
  if (value <= 40) return '#fff7ed';
  if (value <= 60) return '#fefce8';
  if (value <= 80) return '#f0fdf4';
  return '#ecfdf5';
}

type Tab = 'crypto' | 'commodities' | 'fx' | 'fear-greed';

// ── Component ───────────────────────────────────────────────────────

export default function AssetTracker() {
  const [data, setData] = useState<AssetData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>('crypto');

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.assets.getAll() as unknown as AssetData;
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load asset data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void loadData(); }, [loadData]);

  if (loading && !data) {
    return (
      <div style={containerStyle}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 60 }}>
          <Loader2 size={28} style={{ animation: 'spin 1s linear infinite', color: '#6366f1' }} />
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div style={containerStyle}>
        <div style={{ textAlign: 'center', padding: 40 }}>
          <p style={{ color: '#dc2626', fontSize: 15, marginBottom: 12 }}>{error}</p>
          <button type="button" onClick={loadData} style={retryButtonStyle}>
            <RefreshCw size={14} /> Retry
          </button>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="asset-tracker" style={containerStyle}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <h2 style={{ fontSize: 22, fontWeight: 700, color: '#111827', display: 'flex', alignItems: 'center', gap: 8 }}>
            <Activity size={22} color="#6366f1" />
            Asset Tracker
          </h2>
          <p style={{ color: '#6b7280', fontSize: 13, marginTop: 4 }}>
            Track {data.summary.tracked_assets} assets — crypto, commodities, FX
          </p>
        </div>
        <button type="button" onClick={loadData} style={refreshButtonStyle} disabled={loading}>
          <RefreshCw size={14} className={loading ? 'spin' : ''} /> Refresh
        </button>
      </div>

      {/* Summary Cards */}
      <div className="qa-grid-4" style={{ display: 'grid', gap: 12, marginBottom: 20 }}>
        <SummaryCard
          icon={<Bitcoin size={16} color="#f7931a" />}
          label="Crypto Market Cap"
          value={formatPrice(data.summary.crypto_market_cap)}
          sub={`BTC Dominance: ${data.summary.btc_dominance}%`}
          bg="#fff7ed"
        />
        <SummaryCard
          icon={<Gem size={16} color="#d97706" />}
          label="Commodities"
          value={`${data.commodities.tracked_count}`}
          sub="Gold, Oil, Silver & more"
          bg="#fefce8"
        />
        <SummaryCard
          icon={<Globe size={16} color="#2563eb" />}
          label="FX Pairs"
          value={`${data.fx.tracked_count}`}
          sub="Major + Emerging markets"
          bg="#eff6ff"
        />
        <SummaryCard
          icon={<Flame size={16} color={fearGreedColor(data.summary.fear_greed_value)} />}
          label="Fear & Greed"
          value={data.summary.fear_greed_value.toString()}
          sub={data.summary.fear_greed_label}
          bg={fearGreedBg(data.summary.fear_greed_value)}
          valueColor={fearGreedColor(data.summary.fear_greed_value)}
        />
      </div>

      {/* Tab Navigation */}
      <div style={tabBarStyle}>
        {(['crypto', 'commodities', 'fx', 'fear-greed'] as Tab[]).map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setActiveTab(tab)}
            style={{
              ...tabStyle,
              background: activeTab === tab ? '#6366f1' : 'transparent',
              color: activeTab === tab ? '#fff' : '#6b7280' }}
          >
            {tab === 'crypto' && <Bitcoin size={14} />}
            {tab === 'commodities' && <Gem size={14} />}
            {tab === 'fx' && <Globe size={14} />}
            {tab === 'fear-greed' && <Flame size={14} />}
            {tab === 'fear-greed' ? 'Fear & Greed' : tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'crypto' && <CryptoTab prices={data.crypto.prices} />}
      {activeTab === 'commodities' && <CommoditiesTab commodities={data.commodities.commodities} />}
      {activeTab === 'fx' && <FxTab pairs={data.fx.pairs} />}
      {activeTab === 'fear-greed' && <FearGreedTab data={data.fear_greed_index} />}

      <div style={{ marginTop: 12, fontSize: 11, color: '#9ca3af', textAlign: 'center' }}>
        Last updated: {new Date(data.fetched_at).toLocaleTimeString()} • Data from CoinGecko, Yahoo Finance, alternative.me
      </div>
    </div>
  );
}

// ── Summary Card ─────────────────────────────────────────────────

function SummaryCard({ icon, label, value, sub, bg, valueColor }: {
  icon: React.ReactNode; label: string; value: string; sub: string; bg: string; valueColor?: string;
}) {
  return (
    <div style={{ ...summaryCardStyle, background: bg }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
        {icon}
        <span style={{ fontSize: 12, color: '#6b7280', fontWeight: 500 }}>{label}</span>
      </div>
      <div style={{ fontSize: 22, fontWeight: 700, color: valueColor || '#111827' }}>{value}</div>
      <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 2 }}>{sub}</div>
    </div>
  );
}

// ── Crypto Tab ───────────────────────────────────────────────────

function CryptoTab({ prices }: { prices: CryptoPrice[] }) {
  return (
    <div>
      <div style={tableHeaderStyle}>
        <span style={{ flex: 1 }}>Asset</span>
        <span style={{ width: 100, textAlign: 'right' }}>Price</span>
        <span style={{ width: 80, textAlign: 'right' }}>24h</span>
        <span style={{ width: 80, textAlign: 'right' }}>7d</span>
        <span style={{ width: 80, textAlign: 'right' }}>30d</span>
        <span style={{ width: 100, textAlign: 'right' }}>Market Cap</span>
        <span style={{ width: 80, textAlign: 'right' }}>Volume</span>
      </div>
      {prices.map((coin) => (
        <div key={coin.id} style={tableRowStyle}>
          <span style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={rankBadgeStyle}>#{coin.market_cap_rank}</span>
            <span style={{ fontWeight: 600, color: '#111827', fontSize: 14 }}>{coin.symbol}</span>
            <span style={{ color: '#9ca3af', fontSize: 12 }}>{coin.name}</span>
          </span>
          <span style={{ width: 100, textAlign: 'right', fontWeight: 600, color: '#111827' }}>
            {formatPrice(coin.current_price)}
          </span>
          <span style={{ width: 80, textAlign: 'right', color: changeColor(coin.price_change_percentage_24h), fontWeight: 500, fontSize: 13 }}>
            {coin.price_change_percentage_24h > 0 ? '+' : ''}{coin.price_change_percentage_24h.toFixed(1)}%
          </span>
          <span style={{ width: 80, textAlign: 'right', color: changeColor(coin.price_change_percentage_7d_in_currency), fontSize: 13 }}>
            {coin.price_change_percentage_7d_in_currency > 0 ? '+' : ''}{coin.price_change_percentage_7d_in_currency.toFixed(1)}%
          </span>
          <span style={{ width: 80, textAlign: 'right', color: changeColor(coin.price_change_percentage_30d_in_currency), fontSize: 13 }}>
            {coin.price_change_percentage_30d_in_currency > 0 ? '+' : ''}{coin.price_change_percentage_30d_in_currency.toFixed(1)}%
          </span>
          <span style={{ width: 100, textAlign: 'right', color: '#6b7280', fontSize: 12 }}>
            {formatPrice(coin.market_cap)}
          </span>
          <span style={{ width: 80, textAlign: 'right', color: '#9ca3af', fontSize: 12 }}>
            {formatPrice(coin.total_volume)}
          </span>
        </div>
      ))}
    </div>
  );
}

// ── Commodities Tab ──────────────────────────────────────────────

function CommoditiesTab({ commodities }: { commodities: Commodity[] }) {
  const grouped: Record<string, Commodity[]> = {};
  commodities.forEach((c) => {
    if (!grouped[c.category]) grouped[c.category] = [];
    grouped[c.category].push(c);
  });

  const categoryLabels: Record<string, string> = {
    precious_metal: 'Precious Metals',
    energy: 'Energy',
    industrial: 'Industrial Metals',
    agriculture: 'Agriculture' };

  return (
    <div>
      {Object.entries(grouped).map(([category, items]) => (
        <div key={category} style={{ marginBottom: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: '#374151', marginBottom: 8 }}>
            {categoryLabels[category] || category}
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 10 }}>
            {items.map((c) => (
              <div key={c.symbol} style={commodityCardStyle}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, color: '#111827', fontSize: 14 }}>{c.name}</span>
                  <span style={{ fontSize: 10, color: '#9ca3af' }}>{c.unit}</span>
                </div>
                <div style={{ fontSize: 20, fontWeight: 700, color: '#111827' }}>
                  {formatPrice(c.price)}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginTop: 4 }}>
                  {c.change_pct > 0 ? <ArrowUpRight size={12} color="#10b981" /> : c.change_pct < 0 ? <ArrowDownRight size={12} color="#ef4444" /> : null}
                  <span style={{ fontSize: 12, color: changeColor(c.change_pct), fontWeight: 500 }}>
                    {c.change_pct > 0 ? '+' : ''}{c.change_pct.toFixed(2)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── FX Tab ───────────────────────────────────────────────────────

function FxTab({ pairs }: { pairs: FxPair[] }) {
  const grouped: Record<string, FxPair[]> = {};
  pairs.forEach((p) => {
    if (!grouped[p.category]) grouped[p.category] = [];
    grouped[p.category].push(p);
  });

  const categoryLabels: Record<string, string> = {
    major: 'Major Pairs',
    emerging: 'Emerging Markets',
    crypto_fiat: 'Crypto/Fiat' };

  return (
    <div>
      {Object.entries(grouped).map(([category, items]) => (
        <div key={category} style={{ marginBottom: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: '#374151', marginBottom: 8 }}>
            {categoryLabels[category] || category}
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 8 }}>
            {items.map((p) => (
              <div key={p.pair} style={fxCardStyle}>
                <div style={{ fontWeight: 600, color: '#111827', fontSize: 13 }}>{p.name}</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: '#111827', marginTop: 4 }}>
                  {p.rate > 0 ? p.rate.toFixed(p.rate > 100 ? 1 : 4) : '—'}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginTop: 4 }}>
                  {p.change_pct > 0 ? <ArrowUpRight size={12} color="#10b981" /> : p.change_pct < 0 ? <ArrowDownRight size={12} color="#ef4444" /> : null}
                  <span style={{ fontSize: 11, color: changeColor(p.change_pct), fontWeight: 500 }}>
                    {p.change_pct > 0 ? '+' : ''}{p.change_pct.toFixed(2)}%
                  </span>
                  {p.market_state !== 'REGULAR' && (
                    <span style={{ fontSize: 9, color: '#9ca3af', marginLeft: 4 }}>
                      {p.market_state}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Fear & Greed Tab ─────────────────────────────────────────────

function FearGreedTab({ data }: { data: FearGreed }) {
  const color = fearGreedColor(data.current_value);

  return (
    <div className="qa-grid-2" style={{ display: 'grid', gap: 20 }}>
      {/* Current Reading */}
      <div style={{ ...panelStyle, display: 'flex', flexDirection: 'column', alignItems: 'center', padding: 40 }}>
        <div style={{
          width: 120, height: 120, borderRadius: '50%',
          background: `conic-gradient(${color} ${data.current_value * 3.6}deg, #e5e7eb 0deg)`,
          display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{
            width: 96, height: 96, borderRadius: '50%', background: '#fff',
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
            <span style={{ fontSize: 32, fontWeight: 700, color }}>{data.current_value}</span>
            <span style={{ fontSize: 11, color: '#6b7280' }}>/ 100</span>
          </div>
        </div>
        <h3 style={{ fontSize: 18, fontWeight: 700, color, marginTop: 16 }}>{data.current_label}</h3>
        <p style={{ fontSize: 13, color: '#6b7280', textAlign: 'center', marginTop: 8, lineHeight: 1.5, maxWidth: 300 }}>
          {data.interpretation}
        </p>

        {/* Scale */}
        <div style={{ width: '100%', marginTop: 20 }}>
          <div style={{ height: 8, borderRadius: 4, background: 'linear-gradient(90deg, #ef4444, #f97316, #eab308, #22c55e, #10b981)', position: 'relative' }}>
            <div style={{
              position: 'absolute', left: `${data.current_value}%`, top: -4,
              width: 16, height: 16, borderRadius: '50%', background: '#fff',
              border: `3px solid ${color}`, transform: 'translateX(-50%)' }} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6, fontSize: 10, color: '#9ca3af' }}>
            <span>Extreme Fear</span>
            <span>Fear</span>
            <span>Neutral</span>
            <span>Greed</span>
            <span>Extreme Greed</span>
          </div>
        </div>
      </div>

      {/* History */}
      <div style={panelStyle}>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: '#111827', marginBottom: 12 }}>7-Day History</h3>
        {data.history.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {data.history.map((entry, idx) => (
              <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 12px', background: '#f9fafb', borderRadius: 8 }}>
                <div style={{ width: 40, height: 40, borderRadius: 8, background: fearGreedBg(entry.value), display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <span style={{ fontSize: 14, fontWeight: 700, color: fearGreedColor(entry.value) }}>{entry.value}</span>
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 500, color: '#374151', fontSize: 13 }}>{entry.label}</div>
                  <div style={{ fontSize: 11, color: '#9ca3af' }}>{entry.date}</div>
                </div>
                <div style={{ width: 60, height: 6, borderRadius: 3, background: '#e5e7eb', overflow: 'hidden' }}>
                  <div style={{ width: `${entry.value}%`, height: '100%', background: fearGreedColor(entry.value), borderRadius: 3 }} />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ color: '#9ca3af', textAlign: 'center', padding: 20 }}>No history available</p>
        )}
      </div>
    </div>
  );
}

// ── Styles ───────────────────────────────────────────────────────

const containerStyle: React.CSSProperties = {
  padding: 24,
  maxWidth: 1200,
  margin: '0 auto' };

const summaryCardStyle: React.CSSProperties = {
  borderRadius: 12,
  padding: 16,
  border: '1px solid #f3f4f6' };

const tabBarStyle: React.CSSProperties = {
  display: 'flex',
  gap: 4,
  padding: 4,
  background: '#f3f4f6',
  borderRadius: 10,
  marginBottom: 20 };

const tabStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 6,
  padding: '8px 16px',
  borderRadius: 8,
  border: 'none',
  fontSize: 13,
  fontWeight: 500,
  cursor: 'pointer',
  transition: 'all 0.15s' };

const tableHeaderStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  padding: '8px 12px',
  fontSize: 11,
  fontWeight: 600,
  color: '#9ca3af',
  textTransform: 'uppercase',
  borderBottom: '1px solid #e5e7eb' };

const tableRowStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  padding: '10px 12px',
  borderBottom: '1px solid #f3f4f6',
  fontSize: 13 };

const rankBadgeStyle: React.CSSProperties = {
  fontSize: 10,
  color: '#9ca3af',
  fontWeight: 500,
  minWidth: 24 };

const commodityCardStyle: React.CSSProperties = {
  background: '#f9fafb',
  borderRadius: 10,
  padding: 14,
  border: '1px solid #f3f4f6' };

const fxCardStyle: React.CSSProperties = {
  background: '#f9fafb',
  borderRadius: 8,
  padding: 12,
  border: '1px solid #f3f4f6' };

const panelStyle: React.CSSProperties = {
  background: '#fff',
  borderRadius: 12,
  padding: 20,
  border: '1px solid #e5e7eb' };

const refreshButtonStyle: React.CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 6,
  padding: '6px 14px', borderRadius: 8, border: '1px solid #e5e7eb',
  background: '#fff', color: '#374151', fontSize: 13, cursor: 'pointer' };

const retryButtonStyle: React.CSSProperties = {
  display: 'inline-flex', alignItems: 'center', gap: 6,
  padding: '8px 16px', borderRadius: 8, border: '1px solid #e5e7eb',
  background: '#fff', color: '#374151', fontSize: 13, cursor: 'pointer' };
