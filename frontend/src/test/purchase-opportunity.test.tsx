import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
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
  it('renders page title', () => {
    renderWithRouter(<PurchaseTrackerPage />);
    expect(screen.getByText('Purchase Tracker')).toBeDefined();
  });

  it('renders summary stat cards', () => {
    renderWithRouter(<PurchaseTrackerPage />);
    expect(screen.getByText('Total Principal')).toBeDefined();
    expect(screen.getByText('Unrealized P&L')).toBeDefined();
  });

  it('renders all 10 purchases in the table', () => {
    renderWithRouter(<PurchaseTrackerPage />);
    expect(screen.getByText('US Treasury 10Y Note')).toBeDefined();
    expect(screen.getByText('Apple Inc. Senior Note 2030')).toBeDefined();
    expect(screen.getByText('Tesla Inc. Senior Note 2027')).toBeDefined();
    expect(screen.getByText('Saudi Aramco Sukuk')).toBeDefined();
  });

  it('has a search input', () => {
    renderWithRouter(<PurchaseTrackerPage />);
    expect(screen.getByPlaceholderText('Search purchases...')).toBeDefined();
  });

  it('has status filter buttons', () => {
    renderWithRouter(<PurchaseTrackerPage />);
    const allBtn = screen.getByText('All');
    expect(allBtn).toBeDefined();
  });

  it('displays detail panel when purchase is selected', () => {
    renderWithRouter(<PurchaseTrackerPage />);
    // Click on the first table row
    const rows = document.querySelectorAll('tbody tr');
    expect(rows.length).toBeGreaterThan(0);
    fireEvent.click(rows[0]);
    // After clicking, the detail panel should show
    const detail = document.querySelector('.animate-glass-in');
    expect(detail).toBeTruthy();
  });

  it('shows Export CSV and Add Purchase buttons', () => {
    renderWithRouter(<PurchaseTrackerPage />);
    expect(screen.getByText('Export CSV')).toBeDefined();
    expect(screen.getByText('+ Add Purchase')).toBeDefined();
  });
});

// ── OpportunityFeedPage Tests ────────────────────────────────────────

describe('OpportunityFeedPage', () => {
  it('renders page title', () => {
    renderWithRouter(<OpportunityFeedPage />);
    expect(screen.getByText('Opportunity Feed')).toBeDefined();
  });

  it('displays opportunities with tickers', () => {
    renderWithRouter(<OpportunityFeedPage />);
    expect(screen.getByText('AAPL')).toBeDefined();
    expect(screen.getByText('TSLA')).toBeDefined();
    expect(screen.getByText('NVDA')).toBeDefined();
  });

  it('has risk filter buttons', () => {
    renderWithRouter(<OpportunityFeedPage />);
    expect(screen.getByText('All Risk')).toBeDefined();
    expect(screen.getByText('Low')).toBeDefined();
    expect(screen.getByText('Medium')).toBeDefined();
    expect(screen.getByText('High')).toBeDefined();
  });

  it('has sort options', () => {
    renderWithRouter(<OpportunityFeedPage />);
    expect(screen.getByText('Relevance')).toBeDefined();
    const upside = screen.getAllByText('Upside');
    expect(upside.length).toBeGreaterThan(0);
  });

  it('shows linked holdings filter', () => {
    renderWithRouter(<OpportunityFeedPage />);
    expect(screen.getByText('Linked to holdings only')).toBeDefined();
  });

  it('shows price, target, and upside for each card', () => {
    renderWithRouter(<OpportunityFeedPage />);
    expect(screen.getByText('$198.50')).toBeDefined(); // AAPL price
    expect(screen.getByText('$225.00')).toBeDefined(); // AAPL target
    expect(screen.getByText('+13.3%')).toBeDefined(); // AAPL upside
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
