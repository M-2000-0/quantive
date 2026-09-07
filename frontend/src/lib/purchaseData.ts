// ── Purchase & Opportunity Data ──────────────────────────────────────
// Portfolio purchases, refinancing opportunities, API keys, and alerts.
// Mock data mirrors production API shapes for demo and test use.

export interface AlertPreference {
  id: string;
  name: string;
  category: string;
  condition: string;
  threshold: string;
  channels: string[];
  enabled: boolean;
}

export interface ApiKeyConfig {
  id: string;
  name: string;
  provider: string;
  displayName?: string;
  description?: string;
  icon?: string;
  services?: string[];
  keyPrefix?: string;
  lastSync?: string;
  status: 'connected' | 'expiring' | 'failed' | 'not_configured';
  lastUsed?: string;
  expiresAt?: string;
}

export interface Purchase {
  id: string;
  instrumentName: string;
  issuer: string;
  principal: number;
  coupon: number;
  purchasePrice: number;
  yieldToMaturity: number;
  maturityDate: string;
  daysToMaturity: number;
  unrealizedPnl: number;
  type: 'bond' | 'loan' | 'note' | 'commercial_paper' | 'convertible' | 'preferred';
  currency: 'USD' | 'EUR' | 'GBP' | 'AUD';
}

export interface Opportunity {
  id: string;
  name: string;
  ticker: string;
  type: 'equity' | 'etf' | 'bond' | 'fund';
  currentPrice: number;
  targetPrice: number;
  upside: number;
  relevanceScore: number;
  riskScore: number;
  riskLevel: 'Low' | 'Medium' | 'High';
  sector: string;
  relatedPurchaseId?: string;
}

function maturityFromNow(days: number): string {
  return new Date(Date.now() + days * 86_400_000).toISOString().slice(0, 10);
}

export const MOCK_PURCHASES: Purchase[] = [
  { id: 'p-1', instrumentName: 'US Treasury 10Y Note', issuer: 'US Treasury', principal: 50_000_000, coupon: 4.25, purchasePrice: 99.5, yieldToMaturity: 4.3, maturityDate: maturityFromNow(3650), daysToMaturity: 3650, unrealizedPnl: 1_200_000, type: 'bond', currency: 'USD' },
  { id: 'p-2', instrumentName: 'Apple Inc. Senior Note 2030', issuer: 'Apple Inc.', principal: 40_000_000, coupon: 3.5, purchasePrice: 101.2, yieldToMaturity: 3.2, maturityDate: maturityFromNow(1200), daysToMaturity: 1200, unrealizedPnl: 800_000, type: 'note', currency: 'USD' },
  { id: 'p-3', instrumentName: 'Tesla Inc. Senior Note 2027', issuer: 'Tesla Inc.', principal: 35_000_000, coupon: 5.0, purchasePrice: 98.0, yieldToMaturity: 5.4, maturityDate: maturityFromNow(400), daysToMaturity: 400, unrealizedPnl: -400_000, type: 'note', currency: 'USD' },
  { id: 'p-4', instrumentName: 'Saudi Aramco Sukuk', issuer: 'Saudi Aramco', principal: 30_000_000, coupon: 4.75, purchasePrice: 100.0, yieldToMaturity: 4.75, maturityDate: maturityFromNow(2500), daysToMaturity: 2500, unrealizedPnl: 500_000, type: 'bond', currency: 'USD' },
  { id: 'p-5', instrumentName: 'Bund 15Y Federal Loan', issuer: 'Germany', principal: 28_000_000, coupon: 2.5, purchasePrice: 102.5, yieldToMaturity: 2.1, maturityDate: maturityFromNow(700), daysToMaturity: 700, unrealizedPnl: 300_000, type: 'loan', currency: 'EUR' },
  { id: 'p-6', instrumentName: 'UK Gilt Commercial Paper', issuer: 'UK DMO', principal: 25_000_000, coupon: 0, purchasePrice: 99.8, yieldToMaturity: 4.1, maturityDate: maturityFromNow(12), daysToMaturity: 12, unrealizedPnl: 50_000, type: 'commercial_paper', currency: 'GBP' },
  { id: 'p-7', instrumentName: 'Aussie Infrastructure Convertible', issuer: 'Transurban', principal: 22_000_000, coupon: 3.0, purchasePrice: 100.5, yieldToMaturity: 2.9, maturityDate: maturityFromNow(300), daysToMaturity: 300, unrealizedPnl: 220_000, type: 'convertible', currency: 'AUD' },
  { id: 'p-8', instrumentName: 'EDF Preferred Perpetual', issuer: 'EDF', principal: 20_000_000, coupon: 6.5, purchasePrice: 97.0, yieldToMaturity: 5.8, maturityDate: maturityFromNow(180), daysToMaturity: 180, unrealizedPnl: -150_000, type: 'preferred', currency: 'EUR' },
  { id: 'p-9', instrumentName: 'EIB Climate Awareness Bond', issuer: 'EIB', principal: 15_000_000, coupon: 3.25, purchasePrice: 99.0, yieldToMaturity: 3.4, maturityDate: maturityFromNow(90), daysToMaturity: 90, unrealizedPnl: 90_000, type: 'bond', currency: 'EUR' },
  { id: 'p-10', instrumentName: 'NSW Treasury Note', issuer: 'NSW TCorp', principal: 13_000_000, coupon: 4.0, purchasePrice: 100.2, yieldToMaturity: 3.9, maturityDate: maturityFromNow(45), daysToMaturity: 45, unrealizedPnl: 40_000, type: 'note', currency: 'AUD' },
];

export const MOCK_OPPORTUNITIES: Opportunity[] = [
  { id: 'o-1', name: 'Apple Inc.', ticker: 'AAPL', type: 'equity', currentPrice: 198.50, targetPrice: 225.00, upside: 13.3, relevanceScore: 96, riskScore: 22, riskLevel: 'Low', sector: 'Technology', relatedPurchaseId: 'p-2' },
  { id: 'o-2', name: 'Tesla Inc.', ticker: 'TSLA', type: 'equity', currentPrice: 175.20, targetPrice: 210.00, upside: 19.9, relevanceScore: 91, riskScore: 68, riskLevel: 'High', sector: 'Automotive', relatedPurchaseId: 'p-3' },
  { id: 'o-3', name: 'NVIDIA Corp', ticker: 'NVDA', type: 'equity', currentPrice: 131.88, targetPrice: 150.00, upside: 13.7, relevanceScore: 89, riskScore: 55, riskLevel: 'Medium', sector: 'Semiconductors' },
  { id: 'o-4', name: 'Treasury Bond ETF', ticker: 'TLT', type: 'etf', currentPrice: 92.40, targetPrice: 101.00, upside: 9.3, relevanceScore: 84, riskScore: 30, riskLevel: 'Low', sector: 'Fixed Income', relatedPurchaseId: 'p-1' },
  { id: 'o-5', name: 'Investment Grade ETF', ticker: 'LQD', type: 'etf', currentPrice: 108.15, targetPrice: 114.00, upside: 5.4, relevanceScore: 78, riskScore: 25, riskLevel: 'Low', sector: 'Fixed Income' },
  { id: 'o-6', name: 'Microsoft Corp', ticker: 'MSFT', type: 'equity', currentPrice: 428.15, targetPrice: 460.00, upside: 7.4, relevanceScore: 75, riskScore: 28, riskLevel: 'Low', sector: 'Technology' },
  { id: 'o-7', name: 'Saudi Aramco', ticker: 'ARAMCO', type: 'equity', currentPrice: 27.80, targetPrice: 30.50, upside: 9.7, relevanceScore: 70, riskScore: 48, riskLevel: 'Medium', sector: 'Energy', relatedPurchaseId: 'p-4' },
  { id: 'o-8', name: 'High Yield ETF', ticker: 'HYG', type: 'etf', currentPrice: 77.30, targetPrice: 80.00, upside: 3.5, relevanceScore: 64, riskScore: 52, riskLevel: 'Medium', sector: 'Fixed Income' },
  { id: 'o-9', name: 'ASML Holding', ticker: 'ASML', type: 'equity', currentPrice: 672.40, targetPrice: 730.00, upside: 8.6, relevanceScore: 60, riskScore: 50, riskLevel: 'Medium', sector: 'Semiconductors' },
  { id: 'o-10', name: 'Green Bond ETF', ticker: 'GRNB', type: 'etf', currentPrice: 45.10, targetPrice: 48.00, upside: 6.4, relevanceScore: 55, riskScore: 32, riskLevel: 'Low', sector: 'ESG' },
  { id: 'o-11', name: 'Coinbase Global', ticker: 'COIN', type: 'equity', currentPrice: 223.10, targetPrice: 250.00, upside: 12.1, relevanceScore: 48, riskScore: 80, riskLevel: 'High', sector: 'Crypto' },
  { id: 'o-12', name: 'Emerging Markets ETF', ticker: 'EEM', type: 'etf', currentPrice: 42.60, targetPrice: 45.00, upside: 5.6, relevanceScore: 42, riskScore: 58, riskLevel: 'High', sector: 'Emerging' },
];

export const MOCK_API_KEYS: ApiKeyConfig[] = [
  { id: 'k-1', name: 'Bloomberg Terminal', provider: 'bloomberg', displayName: 'Bloomberg Terminal', services: ['Market Data'], status: 'connected', lastUsed: '2026-09-01' },
  { id: 'k-2', name: 'Refinitiv (Reuters)', provider: 'refinitiv', displayName: 'Refinitiv (Reuters)', services: ['FX Rates'], status: 'connected', lastUsed: '2026-08-30' },
  { id: 'k-3', name: 'FRED (Federal Reserve)', provider: 'fred', displayName: 'FRED (Federal Reserve)', services: ['Interest Rates'], status: 'expiring', expiresAt: new Date(Date.now() + 5 * 86_400_000).toISOString() },
  { id: 'k-4', name: 'Morningstar Direct', provider: 'morningstar', displayName: 'Morningstar Direct', services: ['Fundamentals'], status: 'failed' },
  { id: 'k-5', name: 'ICE Data Services', provider: 'ice', displayName: 'ICE Data Services', services: ['Reference Data'], status: 'not_configured' },
];

export const MOCK_ALERT_PREFERENCES: AlertPreference[] = [
  { id: 'a-1', name: 'Large Price Swings', category: 'Price Movements', condition: 'Daily move beyond band', threshold: '±2% daily change', channels: ['email'], enabled: true },
  { id: 'a-2', name: 'Intraday Volatility', category: 'Price Movements', condition: 'Intraday range expansion', threshold: '±1.5% intraday', channels: ['dashboard'], enabled: true },
  { id: 'a-3', name: 'Gap Open', category: 'Price Movements', condition: 'Open gaps over threshold', threshold: '±1% gap', channels: ['email'], enabled: false },
  { id: 'a-4', name: 'Credit Rating Changes', category: 'Credit Events', condition: 'CDS spread widening', threshold: '>500bps CDS spread', channels: ['email', 'sms'], enabled: true },
  { id: 'a-5', name: 'Downgrade Watch', category: 'Credit Events', condition: 'Agency negative watch', threshold: 'Any watch listing', channels: ['email'], enabled: true },
  { id: 'a-6', name: 'Yield Curve Changes', category: 'Market Conditions', condition: 'Curve slope shift', threshold: '>25bps slope move', channels: ['email'], enabled: true },
  { id: 'a-7', name: 'Rate Decision', category: 'Market Conditions', condition: 'Central bank meetings', threshold: 'Any policy change', channels: ['dashboard'], enabled: true },
  { id: 'a-8', name: 'New Opportunities', category: 'Opportunities', condition: 'Relevance above bar', threshold: '>80 relevance', channels: ['email', 'dashboard'], enabled: true },
  { id: 'a-9', name: 'Upside Alert', category: 'Opportunities', condition: 'Upside crosses target', threshold: '>10% upside', channels: ['email'], enabled: false },
  { id: 'a-10', name: 'Maturity Window', category: 'Portfolio Health', condition: 'Maturity within window', threshold: '<30d to maturity', channels: ['email', 'sms'], enabled: true },
  { id: 'a-11', name: 'Concentration Risk', category: 'Portfolio Health', condition: 'Single-name weight', threshold: '>15% weight', channels: ['email'], enabled: true },
  { id: 'a-12', name: 'Weekly Digest', category: 'Portfolio Health', condition: 'Weekly schedule', threshold: 'Every Monday', channels: ['email'], enabled: true },
];

export function formatCurrency(value: number): string {
  const sign = value < 0 ? '-' : '';
  const abs = Math.abs(value);
  if (abs >= 1e6) return `${sign}$${parseFloat((abs / 1e6).toFixed(1))}M`;
  if (abs >= 1e3) return `${sign}$${parseFloat((abs / 1e3).toFixed(1))}K`;
  return `${sign}$${abs}`;
}

export function formatNumber(value: number): string {
  if (value >= 1e6) return `${parseFloat((value / 1e6).toFixed(1))}M`;
  if (value >= 1e3) return `${parseFloat((value / 1e3).toFixed(1))}K`;
  return `${value}`;
}

export function getTotalPrincipal(purchases: Purchase[]): number {
  return purchases.reduce((sum, p) => sum + p.principal, 0);
}

export function getTotalUnrealizedPnl(purchases: Purchase[]): number {
  return purchases.reduce((sum, p) => sum + p.unrealizedPnl, 0);
}

export function getWeightedAverageYield(purchases: Purchase[]): number {
  const total = getTotalPrincipal(purchases);
  if (total === 0) return 0;
  return purchases.reduce((sum, p) => sum + p.yieldToMaturity * p.principal, 0) / total;
}

export function getMaturingWithin(purchases: Purchase[], days: number): Purchase[] {
  if (days <= 0) return [];
  return purchases.filter((p) => p.daysToMaturity <= days);
}

export function getTopOpportunities(opportunities: Opportunity[], count: number): Opportunity[] {
  return [...opportunities]
    .sort((a, b) => b.relevanceScore - a.relevanceScore)
    .slice(0, count);
}
