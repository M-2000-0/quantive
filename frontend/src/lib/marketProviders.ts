// ── Market Data Provider Fallback Chain ────────────────────────────────
// Tries multiple providers in order, with rate limiting and timeout handling.

import { setCache, getCache } from './marketCache';
import { validatePriceUpdate, validateFxRate } from './marketValidation';

// ── Rate Limiter ──────────────────────────────────────────────────────

class RateLimiter {
  private requests: number[] = [];

  constructor(
    private maxRequests: number,
    private windowMs: number
  ) {}

  canMakeRequest(): boolean {
    const now = Date.now();
    this.requests = this.requests.filter((t) => now - t < this.windowMs);
    return this.requests.length < this.maxRequests;
  }

  recordRequest(): void {
    this.requests.push(Date.now());
  }

  getRemainingRequests(): number {
    const now = Date.now();
    this.requests = this.requests.filter((t) => now - t < this.windowMs);
    return Math.max(0, this.maxRequests - this.requests.length);
  }
}

// One limiter per provider
const limiters = {
  yahoo: new RateLimiter(60, 60000),      // 60/min — generous
  polygon: new RateLimiter(5, 60000),     // 5/min on free tier
  alphaVantage: new RateLimiter(25, 86400000), // 25/day on free tier
  fred: new RateLimiter(120, 60000),      // 120/min — very generous
};

// ── Provider Config ──────────────────────────────────────────────────

interface ProviderConfig {
  name: string;
  timeoutMs: number;
  limiterKey: keyof typeof limiters;
  baseUrl: string;
}

const PROVIDERS: ProviderConfig[] = [
  { name: 'yahoo', timeoutMs: 3000, limiterKey: 'yahoo', baseUrl: 'https://query1.finance.yahoo.com/v8/finance/chart' },
  { name: 'polygon', timeoutMs: 2000, limiterKey: 'polygon', baseUrl: 'https://api.polygon.io/v2' },
  { name: 'alphaVantage', timeoutMs: 5000, limiterKey: 'alphaVantage', baseUrl: 'https://www.alphavantage.co/query' },
];

const FRED_CONFIG: ProviderConfig = {
  name: 'fred',
  timeoutMs: 4000,
  limiterKey: 'fred',
  baseUrl: 'https://api.stlouisfed.org/fred/series/observations',
};

// ── Fetch with Timeout ───────────────────────────────────────────────

async function fetchWithTimeout(
  url: string,
  timeoutMs: number,
  options?: RequestInit
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    return response;
  } finally {
    clearTimeout(timer);
  }
}

// ── Individual Provider Fetchers ─────────────────────────────────────

interface MarketQuote {
  ticker: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  timestamp: number;
  provider: string;
}

interface FREDDataPoint {
  date: string;
  value: number;
}

async function fetchFromYahoo(ticker: string): Promise<MarketQuote> {
  const limiter = limiters.yahoo;
  if (!limiter.canMakeRequest()) {
    throw new Error('Yahoo rate limit reached');
  }
  limiter.recordRequest();

  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(ticker)}?interval=1d&range=1d`;
  const response = await fetchWithTimeout(url, 3000);
  if (!response.ok) throw new Error(`Yahoo HTTP ${response.status}`);

  const data = await response.json();
  const result = data.chart?.result?.[0];
  if (!result) throw new Error('No Yahoo data');

  const meta = result.meta;
  return {
    ticker,
    price: meta.regularMarketPrice,
    change: meta.regularMarketPrice - meta.previousClose,
    changePercent: ((meta.regularMarketPrice - meta.previousClose) / meta.previousClose) * 100,
    volume: meta.regularMarketVolume || 0,
    timestamp: Date.now(),
    provider: 'yahoo',
  };
}

async function fetchFromPolygon(ticker: string): Promise<MarketQuote> {
  const limiter = limiters.polygon;
  if (!limiter.canMakeRequest()) {
    throw new Error('Polygon rate limit reached');
  }
  limiter.recordRequest();

  // Use free snapshot endpoint (no API key needed for delayed quotes)
  const url = `https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers/${encodeURIComponent(ticker)}`;
  const response = await fetchWithTimeout(url, 2000);
  if (!response.ok) throw new Error(`Polygon HTTP ${response.status}`);

  const data = await response.json();
  const tickerData = data.ticker;
  if (!tickerData) throw new Error('No Polygon data');

  const day = tickerData.day || {};
  const prevClose = tickerData.prevDay?.c || day.o;
  const price = day.c || tickerData.lastTrade?.p || 0;

  return {
    ticker,
    price,
    change: price - prevClose,
    changePercent: prevClose > 0 ? ((price - prevClose) / prevClose) * 100 : 0,
    volume: day.v || 0,
    timestamp: Date.now(),
    provider: 'polygon',
  };
}

async function fetchFromAlphaVantage(ticker: string): Promise<MarketQuote> {
  const limiter = limiters.alphaVantage;
  if (!limiter.canMakeRequest()) {
    throw new Error('Alpha Vantage rate limit reached — 25 requests/day on free tier');
  }
  limiter.recordRequest();

  const url = `https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=${encodeURIComponent(ticker)}&apikey=demo`;
  const response = await fetchWithTimeout(url, 5000);
  if (!response.ok) throw new Error(`AlphaVantage HTTP ${response.status}`);

  const data = await response.json();
  const quote = data['Global Quote'];
  if (!quote) throw new Error('No AlphaVantage data');

  const price = parseFloat(quote['05. price']);
  const previousClose = parseFloat(quote['08. previous close']);

  return {
    ticker,
    price,
    change: price - previousClose,
    changePercent: previousClose > 0 ? ((price - previousClose) / previousClose) * 100 : 0,
    volume: parseInt(quote['06. volume'] || '0', 10),
    timestamp: Date.now(),
    provider: 'alphavantage',
  };
}

// ── FRED Fetcher (for rates and economic data) ───────────────────────

export async function fetchFREDData(
  seriesId: string,
  apiKey: string = 'demo'
): Promise<FREDDataPoint[]> {
  const limiter = limiters.fred;
  if (!limiter.canMakeRequest()) {
    throw new Error('FRED rate limit reached');
  }
  limiter.recordRequest();

  const url = `https://api.stlouisfed.org/fred/series/observations?series_id=${seriesId}&api_key=${apiKey}&file_type=json&sort_order=desc&limit=50`;
  const response = await fetchWithTimeout(url, 4000);
  if (!response.ok) throw new Error(`FRED HTTP ${response.status}`);

  const data = await response.json();
  return (data.observations || [])
    .filter((obs: { value: string }) => obs.value !== '.')
    .map((obs: { date: string; value: string }) => ({
      date: obs.date,
      value: parseFloat(obs.value),
    }));
}

// ── Yahoo FX Fetcher ─────────────────────────────────────────────────

export async function fetchFxRate(pair: string): Promise<{ pair: string; rate: number; change: number; timestamp: number; provider: string }> {
  const ticker = pair.replace('/', '') + '=X';
  const quote = await fetchFromYahoo(ticker);
  const validation = validateFxRate(pair, quote.price);
  if (!validation.valid) {
    throw new Error(validation.reason);
  }
  return {
    pair,
    rate: quote.price,
    change: quote.changePercent,
    timestamp: quote.timestamp,
    provider: 'yahoo',
  };
}

// ── Yahoo Yield Curve Data ───────────────────────────────────────────

const YIELD_TICKERS: Record<string, string> = {
  '1M': '^IRX',    // 13-week Treasury bill (proxy for short end)
  '3M': '^IRX',
  '6M': '6-month-treasury-bill-rate',
  '1Y': '1-year-treasury-bond-rate',
  '2Y': '2-year-treasury-bond-rate',
  '3Y': '3-year-treasury-bond-rate',
  '5Y': '5-year-treasury-bond-rate',
  '7Y': '7-year-treasury-bond-rate',
  '10Y': '^TNX',   // 10-Year Treasury Note Yield
  '20Y': '20-year-treasury-bond-rate',
  '30Y': '^TYX',   // 30-Year Treasury Bond Yield
};

export async function fetchYieldCurve(): Promise<Array<{ maturity: string; yield: number; timestamp: number }>> {
  const results: Array<{ maturity: string; yield: number; timestamp: number }> = [];

  for (const [maturity, ticker] of Object.entries(YIELD_TICKERS)) {
    try {
      if (ticker.startsWith('^')) {
        // Yahoo ticker for live yields
        const quote = await fetchFromYahoo(ticker);
        results.push({ maturity, yield: quote.price, timestamp: Date.now() });
      } else {
        // FRED series for historical
        const data = await fetchFREDData(ticker);
        if (data.length > 0) {
          results.push({ maturity, yield: data[0].value, timestamp: Date.now() });
        }
      }
    } catch {
      // Skip this maturity on failure
    }
  }

  return results;
}

// ── Main Fallback Chain ──────────────────────────────────────────────

const fetchFunctions: Record<string, (ticker: string) => Promise<MarketQuote>> = {
  yahoo: fetchFromYahoo,
  polygon: fetchFromPolygon,
  alphavantage: fetchFromAlphaVantage,
};

/**
 * Fetch a stock quote with automatic provider fallback.
 * Tries providers in order: Yahoo → Polygon → Alpha Vantage.
 * Uses cache as last resort if all providers fail.
 */
export async function fetchQuoteWithFallback(
  ticker: string,
  cacheKey?: string
): Promise<MarketQuote> {
  const key = cacheKey || `quote_${ticker}`;

  // Try each provider in order
  for (const provider of PROVIDERS) {
    try {
      const fetchFn = fetchFunctions[provider.name];
      if (!fetchFn) continue;

      const quote = await Promise.race([
        fetchFn(ticker),
        new Promise<never>((_, reject) =>
          setTimeout(() => reject(new Error(`${provider.name} timeout`)), provider.timeoutMs)
        ),
      ]);

      // Validate the quote
      if (quote.price > 0) {
        // Cache successful result
        setCache(key, quote, 15000); // 15-second cache
        return quote;
      }
    } catch (err) {
      console.warn(`[MarketData] ${provider.name} failed for ${ticker}:`, (err as Error).message);
      continue;
    }
  }

  // All providers failed — try cache
  const cached = getCache<MarketQuote>(key);
  if (cached) {
    console.info(`[MarketData] Using cached data for ${ticker} (age: ${Date.now() - cached.timestamp}ms)`);
    return { ...cached, provider: 'cache' };
  }

  throw new Error(`All providers failed for ${ticker} and no cache available`);
}

/**
 * Fetch multiple quotes in parallel with provider fallback.
 */
export async function fetchQuotesWithFallback(
  tickers: string[]
): Promise<MarketQuote[]> {
  const results = await Promise.allSettled(
    tickers.map((ticker) => fetchQuoteWithFallback(ticker))
  );

  return results
    .filter((r): r is PromiseFulfilledResult<MarketQuote> => r.status === 'fulfilled')
    .map((r) => r.value);
}

/**
 * Get rate limiter status for all providers.
 */
export function getProviderStatus(): Record<string, { remaining: number; ready: boolean }> {
  return {
    yahoo: { remaining: limiters.yahoo.getRemainingRequests(), ready: limiters.yahoo.canMakeRequest() },
    polygon: { remaining: limiters.polygon.getRemainingRequests(), ready: limiters.polygon.canMakeRequest() },
    alphaVantage: { remaining: limiters.alphaVantage.getRemainingRequests(), ready: limiters.alphaVantage.canMakeRequest() },
    fred: { remaining: limiters.fred.getRemainingRequests(), ready: limiters.fred.canMakeRequest() },
  };
}

