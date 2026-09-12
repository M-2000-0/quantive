import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import PurchaseTrackerPage from '../pages/PurchaseTrackerPage';
import OpportunityFeedPage from '../pages/OpportunityFeedPage';
import ApiKeyManager from '../components/ApiKeyManager';
import AlertPreferences from '../components/AlertPreferences';
import {
  MOCK_PURCHASES,
  MOCK_OPPORTUNITIES,
  MOCK_API_KEYS,
  MOCK_ALERT_PREFERENCES,
  formatCurrency,
  formatNumber,
  getTotalPrincipal,
  getTotalUnrealizedPnl,
  getWeightedAverageYield,
  getMaturingWithin,
  getTopOpportunities,
} from '../lib/purchaseData';

const mockPurchases = [
  { id: 'p-1', instrument_name: 'US Treasury 10Y Note', issuer: 'US Treasury', principal: 50000000, coupon: 4.25, purchase_price: 99.5, yield_to_maturity: 4.3, maturity_date: '2036-09-04', days_to_maturity: 3650, unrealized_pnl: 1200000, type: 'bond', currency: 'USD' },
  { id: 'p-2', instrument_name: 'Apple Inc. Senior Note 2030', issuer: 'Apple Inc.', principal: 40000000, coupon: 3.5, purchase_price: 101.2, yield_to_maturity: 3.2, maturity_date: '2029-11-27', days_to_maturity: 1200, unrealized_pnl: 800000, type: 'note', currency: 'USD' },
  { id: 'p-3', instrument_name: 'Tesla Inc. Senior Note 2027', issuer: 'Tesla Inc.', principal: 35000000, coupon: 5.0, purchase_price: 98.0, yield_to_maturity: 5.4, maturity_date: '2027-10-16', days_to_maturity: 400, unrealized_pnl: -400000, type: 'note', currency: 'USD' },
  { id: 'p-4', instrument_name: 'Saudi Aramco Sukuk', issuer: 'Saudi Aramco', principal: 30000000, coupon: 4.75, purchase_price: 100.0, yield_to_maturity: 4.75, maturity_date: '2033-07-22', days_to_maturity: 2500, unrealized_pnl: 500000, type: 'bond', currency: 'USD' },
  { id: 'p-5', instrument_name: 'Bund 15Y Federal Loan', issuer: 'Germany', principal: 28000000, coupon: 2.5, purchase_price: 102.5, yield_to_maturity: 2.1, maturity_date: '2028-08-15', days_to_maturity: 700, unrealized_pnl: 300000, type: 'loan', currency: 'EUR' },
  { id: 'p-6', instrument_name: 'UK Gilt Commercial Paper', issuer: 'UK DMO', principal: 25000000, coupon: 0, purchase_price: 99.8, yield_to_maturity: 4.1, maturity_date: '2026-09-19', days_to_maturity: 12, unrealized_pnl: 50000, type: 'commercial_paper', currency: 'GBP' },
  { id: 'p-7', instrument_name: 'Aussie Infrastructure Convertible', issuer: 'Transurban', principal: 22000000, coupon: 3.0, purchase_price: 100.5, yield_to_maturity: 2.9, maturity_date: '2027-09-04', days_to_maturity: 300, unrealized_pnl: 220000, type: 'convertible', currency: 'AUD' },
  { id: 'p-8', instrument_name: 'EDF Preferred Perpetual', issuer: 'EDF', principal: 20000000, coupon: 6.5, purchase_price: 97.0, yield_to_maturity: 5.8, maturity_date: '2027-03-05', days_to_maturity: 180, unrealized_pnl: -150000, type: 'preferred', currency: 'EUR' },
  { id: 'p-9', instrument_name: 'EIB Climate Awareness Bond', issuer: 'EIB', principal: 15000000, coupon: 3.25, purchase_price: 99.0, yield_to_maturity: 3.4, maturity_date: '2026-12-06', days_to_maturity: 90, unrealized_pnl: 90000, type: 'bond', currency: 'EUR' },
  { id: 'p-10', instrument_name: 'NSW Treasury Note', issuer: 'NSW TCorp', principal: 13000000, coupon: 4.0, purchase_price: 100.2, yield_to_maturity: 3.9, maturity_date: '2026-10-22', days_to_maturity: 45, unrealized_pnl: 40000, type: 'note', currency: 'AUD' },
];

const mockOpportunities = [
  { id: 'o-1', name: 'Apple Inc.', ticker: 'AAPL', type: 'equity', current_price: 198.50, target_price: 225.00, upside: 13.3, relevance_score: 96, risk_score: 22, risk_level: 'Low', sector: 'Technology' },
  { id: 'o-2', name: 'Tesla Inc.', ticker: 'TSLA', type: 'equity', current_price: 175.20, target_price: 210.00, upside: 19.9, relevance_score: 91, risk_score: 68, risk_level: 'High', sector: 'Automotive' },
  { id: 'o-3', name: 'NVIDIA Corp', ticker: 'NVDA', type: 'equity', current_price: 131.88, target_price: 150.00, upside: 13.7, relevance_score: 89, risk_score: 55, risk_level: 'Medium', sector: 'Semiconductors' },
  { id: 'o-4', name: 'Treasury Bond ETF', ticker: 'TLT', type: 'etf', current_price: 92.40, target_price: 101.00, upside: 9.3, relevance_score: 84, risk_score: 30, risk_level: 'Low', sector: 'Fixed Income' },
  { id: 'o-5', name: 'Investment Grade ETF', ticker: 'LQD', type: 'etf', current_price: 108.15, target_price: 114.00, upside: 5.4, relevance_score: 78, risk_score: 25, risk_level: 'Low', sector: 'Fixed Income' },
  { id: 'o-6', name: 'Microsoft Corp', ticker: 'MSFT', type: 'equity', current_price: 428.15, target_price: 460.00, upside: 7.4, relevance_score: 75, risk_score: 28, risk_level: 'Low', sector: 'Technology' },
  { id: 'o-7', name: 'Saudi Aramco', ticker: 'ARAMCO', type: 'equity', current_price: 27.80, target_price: 30.50, upside: 9.7, relevance_score: 70, risk_score: 48, risk_level: 'Medium', sector: 'Energy' },
  { id: 'o-8', name: 'High Yield ETF', ticker: 'HYG', type: 'etf', current_price: 77.30, target_price: 80.00, upside: 3.5, relevance_score: 64, risk_score: 52, risk_level: 'Medium', sector: 'Fixed Income' },
  { id: 'o-9', name: 'ASML Holding', ticker: 'ASML', type: 'equity', current_price: 672.40, target_price: 730.00, upside: 8.6, relevance_score: 60, risk_score: 50, risk_level: 'Medium', sector: 'Semiconductors' },
  { id: 'o-10', name: 'Green Bond ETF', ticker: 'GRNB', type: 'etf', current_price: 45.10, target_price: 48.00, upside: 6.4, relevance_score: 55, risk_score: 32, risk_level: 'Low', sector: 'ESG' },
  { id: 'o-11', name: 'Coinbase Global', ticker: 'COIN', type: 'equity', current_price: 223.10, target_price: 250.00, upside: 12.1, relevance_score: 48, risk_score: 80, risk_level: 'High', sector: 'Crypto' },
  { id: 'o-12', name: 'Emerging Markets ETF', ticker: 'EEM', type: 'etf', current_price: 42.60, target_price: 45.00, upside: 5.6, relevance_score: 42, risk_score: 58, risk_level: 'High', sector: 'Emerging' },
];

vi.mock('../api', () => ({
  api: {
    intelligence: {
      purchases: vi.fn(async () => mockPurchases),
      opportunities: vi.fn(async () => mockOpportunities),
      events: vi.fn(async () => []),
      eventSummary: vi.fn(async () => ({})),
      impactedAssets: vi.fn(async () => []),
    },
    auth: { login: vi.fn(), register: vi.fn(), me: vi.fn(async () => ({ id: 'u1', email: 'test@test.com' })) },
    portfolios: { list: vi.fn(async () => ({ data: [], meta: { total: 0 } })) },
    optimizations: { list: vi.fn(async () => ({ data: [], meta: { total: 0 } })) },
    notifications: { unreadCount: vi.fn(async () => 0), list: vi.fn(async () => ({ data: [], meta: { total: 0 } })), markRead: vi.fn(), markAllRead: vi.fn() },
  },
}));

// ── purchaseData.ts Service Tests ────────────────────────────────────

describe('purchaseData service', () => {
  describe('MOCK_PURCHASES', () => {
    it('has 10 mock purchases', () => {
      expect(MOCK_PURCHASES).toHaveLength(10);
    });

    it('each purchase has required fields', () => {
      MOCK_PURCHASES.forEach((p) => {
        expect(p.id).toBeTruthy();
        expect(p.instrumentName).toBeTruthy();
        expect(p.issuer).toBeTruthy();
        expect(p.principal).toBeGreaterThan(0);
        expect(p.coupon).toBeGreaterThanOrEqual(0);
        expect(p.purchasePrice).toBeGreaterThan(0);
        expect(p.yieldToMaturity).toBeGreaterThanOrEqual(0);
        expect(p.maturityDate).toBeTruthy();
      });
    });

    it('contains bonds, loans, notes, commercial paper, convertibles, and preferred', () => {
      const types = new Set(MOCK_PURCHASES.map((p) => p.type));
      expect(types.has('bond')).toBe(true);
      expect(types.has('loan')).toBe(true);
      expect(types.has('note')).toBe(true);
      expect(types.has('commercial_paper')).toBe(true);
      expect(types.has('convertible')).toBe(true);
      expect(types.has('preferred')).toBe(true);
    });

    it('contains multiple currencies', () => {
      const currencies = new Set(MOCK_PURCHASES.map((p) => p.currency));
      expect(currencies.has('USD')).toBe(true);
      expect(currencies.has('EUR')).toBe(true);
      expect(currencies.has('GBP')).toBe(true);
      expect(currencies.has('AUD')).toBe(true);
    });
  });

  describe('MOCK_OPPORTUNITIES', () => {
    it('has 12 mock opportunities', () => {
      expect(MOCK_OPPORTUNITIES).toHaveLength(12);
    });

    it('each opportunity has a relevance score between 0-100', () => {
      MOCK_OPPORTUNITIES.forEach((o) => {
        expect(o.relevanceScore).toBeGreaterThanOrEqual(0);
        expect(o.relevanceScore).toBeLessThanOrEqual(100);
      });
    });

    it('contains equities and ETFs', () => {
      const types = new Set(MOCK_OPPORTUNITIES.map((o) => o.type));
      expect(types.has('equity')).toBe(true);
      expect(types.has('etf')).toBe(true);
    });

    it('some are linked to purchases', () => {
      const linked = MOCK_OPPORTUNITIES.filter((o) => o.relatedPurchaseId);
      expect(linked.length).toBeGreaterThan(0);
    });

    it('linked opportunities reference valid purchase IDs', () => {
      const purchaseIds = new Set(MOCK_PURCHASES.map((p) => p.id));
      MOCK_OPPORTUNITIES.filter((o) => o.relatedPurchaseId).forEach((o) => {
        expect(purchaseIds.has(o.relatedPurchaseId!)).toBe(true);
      });
    });
  });

  describe('MOCK_API_KEYS', () => {
    it('has 5 mock API key configs', () => {
      expect(MOCK_API_KEYS).toHaveLength(5);
    });

    it('has connected, expiring, failed, and not_configured statuses', () => {
      const statuses = new Set(MOCK_API_KEYS.map((k) => k.status));
      expect(statuses.has('connected')).toBe(true);
      expect(statuses.has('expiring')).toBe(true);
      expect(statuses.has('failed')).toBe(true);
      expect(statuses.has('not_configured')).toBe(true);
    });
  });

  describe('MOCK_ALERT_PREFERENCES', () => {
    it('has 12 mock alert preferences', () => {
      expect(MOCK_ALERT_PREFERENCES).toHaveLength(12);
    });

    it('spans 5 categories', () => {
      const categories = new Set(MOCK_ALERT_PREFERENCES.map((a) => a.category));
      expect(categories.size).toBe(5);
    });

    it('each has at least one notification channel', () => {
      MOCK_ALERT_PREFERENCES.forEach((a) => {
        expect(a.channels.length).toBeGreaterThan(0);
      });
    });
  });

  describe('formatCurrency', () => {
    it('formats millions correctly', () => {
      expect(formatCurrency(50_000_000)).toBe('$50M');
    });

    it('formats thousands correctly', () => {
      expect(formatCurrency(250_000)).toBe('$250K');
    });

    it('formats small values correctly', () => {
      expect(formatCurrency(100)).toBe('$100');
    });

    it('handles negative values', () => {
      const result = formatCurrency(-700_000);
      expect(result).toContain('-');
      expect(result).toContain('$');
    });
  });

  describe('formatNumber', () => {
    it('formats millions', () => {
      expect(formatNumber(48_200_000)).toBe('48.2M');
    });

    it('formats thousands', () => {
      expect(formatNumber(12_500)).toBe('12.5K');
    });

    it('formats small values', () => {
      expect(formatNumber(500)).toBe('500');
    });
  });

  describe('getTotalPrincipal', () => {
    it('sums all principal amounts', () => {
      const total = getTotalPrincipal(MOCK_PURCHASES);
      expect(total).toBe(278_000_000); // Sum of all principals
    });

    it('returns 0 for empty array', () => {
      expect(getTotalPrincipal([])).toBe(0);
    });
  });

  describe('getTotalUnrealizedPnl', () => {
    it('sums all unrealized P&L', () => {
      const total = getTotalUnrealizedPnl(MOCK_PURCHASES);
      expect(typeof total).toBe('number');
      expect(total).not.toBeNaN();
    });
  });

  describe('getWeightedAverageYield', () => {
    it('returns a positive yield', () => {
      const avgYield = getWeightedAverageYield(MOCK_PURCHASES);
      expect(avgYield).toBeGreaterThan(0);
      expect(avgYield).toBeLessThan(20);
    });

    it('returns 0 for empty array', () => {
      expect(getWeightedAverageYield([])).toBe(0);
    });
  });

  describe('getMaturingWithin', () => {
    it('finds instruments maturing within 30 days', () => {
      const maturing = getMaturingWithin(MOCK_PURCHASES, 30);
      expect(maturing.length).toBeGreaterThan(0);
      maturing.forEach((p) => {
        expect(p.daysToMaturity).toBeLessThanOrEqual(30);
      });
    });

    it('finds instruments maturing within 365 days', () => {
      const maturing = getMaturingWithin(MOCK_PURCHASES, 365);
      expect(maturing.length).toBeGreaterThan(0);
    });

    it('returns empty for 0 days', () => {
      expect(getMaturingWithin(MOCK_PURCHASES, 0)).toHaveLength(0);
    });
  });

  describe('getTopOpportunities', () => {
    it('returns opportunities sorted by relevance', () => {
      const top3 = getTopOpportunities(MOCK_OPPORTUNITIES, 3);
      expect(top3).toHaveLength(3);
      expect(top3[0].relevanceScore).toBeGreaterThanOrEqual(top3[1].relevanceScore);
      expect(top3[1].relevanceScore).toBeGreaterThanOrEqual(top3[2].relevanceScore);
    });

    it('respects count parameter', () => {
      expect(getTopOpportunities(MOCK_OPPORTUNITIES, 5)).toHaveLength(5);
      expect(getTopOpportunities(MOCK_OPPORTUNITIES, 100)).toHaveLength(MOCK_OPPORTUNITIES.length);
    });
  });
});

// ── PurchaseTrackerPage Tests ────────────────────────────────────────

const renderWithRouter = (component: React.ReactNode) =>
  render(<BrowserRouter>{component}</BrowserRouter>);

describe('PurchaseTrackerPage', () => {
  it('renders page title', async () => {
    renderWithRouter(<PurchaseTrackerPage />);
    await waitFor(() => expect(screen.getByText('Purchase Tracker')).toBeDefined());
  });

  it('renders summary stat cards', async () => {
    renderWithRouter(<PurchaseTrackerPage />);
    await waitFor(() => {
      expect(screen.getByText('Total Principal')).toBeDefined();
      expect(screen.getByText('Unrealized P&L')).toBeDefined();
    });
  });

  it('renders all 10 purchases in the table', async () => {
    renderWithRouter(<PurchaseTrackerPage />);
    await waitFor(() => {
      expect(screen.getByText('US Treasury 10Y Note')).toBeDefined();
      expect(screen.getByText('Apple Inc. Senior Note 2030')).toBeDefined();
      expect(screen.getByText('Tesla Inc. Senior Note 2027')).toBeDefined();
      expect(screen.getByText('Saudi Aramco Sukuk')).toBeDefined();
    });
  });

  it('has a search input', async () => {
    renderWithRouter(<PurchaseTrackerPage />);
    await waitFor(() => expect(screen.getByPlaceholderText('Search purchases...')).toBeDefined());
  });

  it('has currency filter buttons', async () => {
    renderWithRouter(<PurchaseTrackerPage />);
    await waitFor(() => {
      const allBtn = screen.getByText('All');
      expect(allBtn).toBeDefined();
    });
  });

  it('displays detail panel when purchase is selected', async () => {
    renderWithRouter(<PurchaseTrackerPage />);
    await waitFor(() => {
      expect(screen.getByText('US Treasury 10Y Note')).toBeDefined();
    });
    const rows = document.querySelectorAll('tbody tr');
    expect(rows.length).toBeGreaterThan(0);
    fireEvent.click(rows[0]);
    await waitFor(() => {
      const detail = document.querySelector('.panel');
      expect(detail).toBeTruthy();
    });
  });

  it('shows Export CSV button', async () => {
    renderWithRouter(<PurchaseTrackerPage />);
    await waitFor(() => expect(screen.getByText('Export CSV')).toBeDefined());
  });
});

// ── OpportunityFeedPage Tests ────────────────────────────────────────

describe('OpportunityFeedPage', () => {
  it('renders page title', async () => {
    renderWithRouter(<OpportunityFeedPage />);
    await waitFor(() => expect(screen.getByText('Opportunity Feed')).toBeDefined());
  });

  it('displays opportunities with tickers', async () => {
    renderWithRouter(<OpportunityFeedPage />);
    await waitFor(() => {
      expect(screen.getByText('AAPL')).toBeDefined();
      expect(screen.getByText('TSLA')).toBeDefined();
      expect(screen.getByText('NVDA')).toBeDefined();
    });
  });

  it('has risk filter buttons', async () => {
    renderWithRouter(<OpportunityFeedPage />);
    await waitFor(() => {
      expect(screen.getByText('All')).toBeDefined();
      expect(screen.getAllByText('Low').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Medium').length).toBeGreaterThan(0);
      expect(screen.getAllByText('High').length).toBeGreaterThan(0);
    });
  });

  it('has sort options', async () => {
    renderWithRouter(<OpportunityFeedPage />);
    await waitFor(() => {
      expect(screen.getByText('Relevance')).toBeDefined();
      const upside = screen.getAllByText('Upside');
      expect(upside.length).toBeGreaterThan(0);
    });
  });

  it('shows price, target, and upside for each card', async () => {
    renderWithRouter(<OpportunityFeedPage />);
    await waitFor(() => {
      expect(screen.getByText('$198.50')).toBeDefined();
      expect(screen.getByText('$225.00')).toBeDefined();
      expect(screen.getByText('+13.3%')).toBeDefined();
    });
  });
});

// ── ApiKeyManager Tests ──────────────────────────────────────────────

describe('ApiKeyManager', () => {
  it('renders all 5 API providers', () => {
    renderWithRouter(<ApiKeyManager />);
    expect(screen.getByText('Bloomberg Terminal')).toBeDefined();
    expect(screen.getByText('Refinitiv (Reuters)')).toBeDefined();
    expect(screen.getByText('FRED (Federal Reserve)')).toBeDefined();
    expect(screen.getByText('Morningstar Direct')).toBeDefined();
    expect(screen.getByText('ICE Data Services')).toBeDefined();
  });

  it('shows connection status', () => {
    renderWithRouter(<ApiKeyManager />);
    const connected = screen.getAllByText(/Connected/);
    expect(connected.length).toBeGreaterThan(0);
    const expiring = screen.getAllByText(/Expiring Soon/);
    expect(expiring.length).toBeGreaterThan(0);
    const failed = screen.getAllByText(/Failed/);
    expect(failed.length).toBeGreaterThan(0);
  });

  it('has Connect Service button', () => {
    renderWithRouter(<ApiKeyManager />);
    expect(screen.getByText('+ Connect Service')).toBeDefined();
  });

  it('shows Test Connection buttons for configured keys', () => {
    renderWithRouter(<ApiKeyManager />);
    const testButtons = screen.getAllByText('Test Connection');
    expect(testButtons.length).toBeGreaterThan(0);
  });

  it('shows Revoke buttons for configured keys', () => {
    renderWithRouter(<ApiKeyManager />);
    const revokeButtons = screen.getAllByText('Revoke');
    expect(revokeButtons.length).toBeGreaterThan(0);
  });

  it('shows Configure button for unconfigured keys', () => {
    renderWithRouter(<ApiKeyManager />);
    expect(screen.getByText('Configure')).toBeDefined();
  });

  it('displays API services for each provider', () => {
    renderWithRouter(<ApiKeyManager />);
    expect(screen.getByText('Market Data')).toBeDefined();
    expect(screen.getByText('FX Rates')).toBeDefined();
    expect(screen.getByText('Interest Rates')).toBeDefined();
  });
});

// ── AlertPreferences Tests ───────────────────────────────────────────

describe('AlertPreferences', () => {
  it('renders alert preferences title', () => {
    renderWithRouter(<AlertPreferences />);
    expect(screen.getByText('Alert Preferences')).toBeDefined();
  });

  it('shows active alert count', () => {
    renderWithRouter(<AlertPreferences />);
    expect(screen.getByText(/alerts active/)).toBeDefined();
  });

  it('renders all 12 alert types', () => {
    renderWithRouter(<AlertPreferences />);
    expect(screen.getByText('Large Price Swings')).toBeDefined();
    expect(screen.getByText('Maturity Window')).toBeDefined();
    expect(screen.getByText('Credit Rating Changes')).toBeDefined();
    expect(screen.getByText('Yield Curve Changes')).toBeDefined();
    expect(screen.getByText('New Opportunities')).toBeDefined();
  });

  it('shows alert categories', () => {
    renderWithRouter(<AlertPreferences />);
    expect(screen.getByText('Price Movements')).toBeDefined();
    expect(screen.getByText('Credit Events')).toBeDefined();
    expect(screen.getByText('Market Conditions')).toBeDefined();
    expect(screen.getByText('Opportunities')).toBeDefined();
    expect(screen.getByText('Portfolio Health')).toBeDefined();
  });

  it('has toggle switches for each alert', () => {
    renderWithRouter(<AlertPreferences />);
    // Toggle switches are buttons
    const switches = document.querySelectorAll('button[class*="rounded-full"]');
    expect(switches.length).toBeGreaterThan(0);
  });

  it('shows threshold values for alerts', () => {
    renderWithRouter(<AlertPreferences />);
    expect(screen.getByText('±2% daily change')).toBeDefined();
    expect(screen.getByText('>500bps CDS spread')).toBeDefined();
  });

  it('shows channel info note', () => {
    renderWithRouter(<AlertPreferences />);
    expect(screen.getByText(/SMS alerts are available on Pro plans/)).toBeDefined();
  });
});
