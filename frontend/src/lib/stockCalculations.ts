// Pure math functions — no API calls, no side effects
export interface StockHistorical {
  date: string; open: number; high: number; low: number; close: number; volume: number; adjClose: number;
}

export function calculateSMA(prices: number[], period: number): number[] {
  const result: number[] = [];
  for (let i = 0; i < prices.length; i++) {
    if (i < period - 1) result.push(NaN);
    else result.push(prices.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0) / period);
  }
  return result;
}

export function calculateEMA(prices: number[], period: number): number[] {
  const k = 2 / (period + 1);
  const result: number[] = [prices[0]];
  for (let i = 1; i < prices.length; i++) {
    result.push(prices[i] * k + result[i - 1] * (1 - k));
  }
  return result;
}

export function calculateRSI(prices: number[], period: number = 14): number[] {
  const changes = prices.map((p, i) => (i === 0 ? 0 : p - prices[i - 1]));
  const gains = changes.map(c => (c > 0 ? c : 0));
  const losses = changes.map(c => (c < 0 ? -c : 0));
  const rsi: number[] = [];
  for (let i = 0; i < prices.length; i++) {
    if (i < period) { rsi.push(NaN); continue; }
    const avgGain = gains.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0) / period;
    const avgLoss = losses.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0) / period;
    rsi.push(avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss));
  }
  return rsi;
}

export function calculateATR(highs: number[], lows: number[], closes: number[], period: number = 14): number[] {
  const tr: number[] = [];
  for (let i = 0; i < highs.length; i++) {
    if (i === 0) tr.push(highs[i] - lows[i]);
    else tr.push(Math.max(highs[i] - lows[i], Math.abs(highs[i] - closes[i - 1]), Math.abs(lows[i] - closes[i - 1])));
  }
  return calculateSMA(tr, period);
}

export function generateHistoricalPrices(basePrice: number, days = 365, volatility = 0.02, drift = 0.0003): StockHistorical[] {
  const prices: StockHistorical[] = [];
  let price = basePrice * (1 - drift * days);
  for (let i = 0; i < days; i++) {
    const d = new Date();
    d.setDate(d.getDate() - (days - i));
    price = price * (1 + drift + volatility * (Math.random() * 2 - 1));
    prices.push({
      date: d.toISOString().split('T')[0],
      open: +(price * (1 + (Math.random() - 0.5) * volatility * 0.3)).toFixed(2),
      high: +(price * (1 + Math.random() * volatility * 0.5)).toFixed(2),
      low: +(price * (1 - Math.random() * volatility * 0.5)).toFixed(2),
      close: +price.toFixed(2),
      volume: Math.floor(1e7 + Math.random() * 4e7),
      adjClose: +price.toFixed(2),
    });
  }
  return prices;
}
