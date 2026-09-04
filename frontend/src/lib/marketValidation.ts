// ── Market Data Validation & Anomaly Detection ────────────────────────
// Validates price updates, detects anomalies, and checks data freshness.

export interface ValidationReason {
  valid: boolean;
  reason?: string;
}

/**
 * Validates a price update against the previous price.
 * Rejects jumps exceeding `maxChangePercent` as likely data errors.
 */
export function validatePriceUpdate(
  previousPrice: number,
  currentPrice: number,
  maxChangePercent: number = 5
): ValidationReason {
  if (!isFinite(previousPrice) || !isFinite(currentPrice)) {
    return { valid: false, reason: 'Non-finite price value' };
  }
  if (previousPrice <= 0 || currentPrice <= 0) {
    return { valid: false, reason: 'Price must be positive' };
  }
  if (currentPrice === previousPrice) {
    return { valid: true };
  }
  const changePercent = Math.abs((currentPrice - previousPrice) / previousPrice) * 100;
  if (changePercent > maxChangePercent) {
    return {
      valid: false,
      reason: `Price changed ${changePercent.toFixed(1)}% (max ${maxChangePercent}%) — likely bad tick`,
    };
  }
  return { valid: true };
}

/**
 * Validates a yield value (should be between -5% and 30%).
 */
export function validateYield(yieldValue: number): ValidationReason {
  if (!isFinite(yieldValue)) {
    return { valid: false, reason: 'Non-finite yield value' };
  }
  if (yieldValue < -5 || yieldValue > 30) {
    return { valid: false, reason: `Yield ${yieldValue}% outside plausible range (-5% to 30%)` };
  }
  return { valid: true };
}

/**
 * Validates an FX rate (must be positive and within reasonable bounds).
 */
export function validateFxRate(pair: string, rate: number): ValidationReason {
  if (!isFinite(rate) || rate <= 0) {
    return { valid: false, reason: `Invalid FX rate for ${pair}` };
  }
  // Extreme bounds for major pairs
  const bounds: Record<string, [number, number]> = {
    'EUR/USD': [0.5, 2.0],
    'GBP/USD': [0.8, 2.5],
    'USD/JPY': [50, 250],
    'AUD/USD': [0.3, 1.5],
    'USD/CHF': [0.5, 2.0],
  };
  const [min, max] = bounds[pair] || [0.01, 1000];
  if (rate < min || rate > max) {
    return { valid: false, reason: `FX rate ${rate} outside plausible range [${min}, ${max}] for ${pair}` };
  }
  return { valid: true };
}

/**
 * Validates a credit spread value (in basis points).
 */
export function validateCreditSpread(spreadBps: number): ValidationReason {
  if (!isFinite(spreadBps)) {
    return { valid: false, reason: 'Non-finite spread value' };
  }
  if (spreadBps < -100 || spreadBps > 5000) {
    return { valid: false, reason: `Spread ${spreadBps}bps outside plausible range` };
  }
  return { valid: true };
}

/**
 * Detects data staleness based on timestamp.
 * Returns true if data is older than maxAgeMs.
 */
export function isDataStale(timestamp: number, maxAgeMs: number = 10000): boolean {
  return Date.now() - timestamp > maxAgeMs;
}

/**
 * Validates a batch of price updates, filtering out anomalies.
 */
export function filterAnomalies<T extends { price: number; previousPrice?: number }>(
  updates: T[],
  maxChangePercent: number = 5
): { valid: T[]; rejected: Array<{ item: T; reason: string }> } {
  const valid: T[] = [];
  const rejected: Array<{ item: T; reason: string }> = [];

  updates.forEach((update) => {
    if (update.previousPrice !== undefined && update.previousPrice > 0) {
      const result = validatePriceUpdate(update.previousPrice, update.price, maxChangePercent);
      if (result.valid) {
        valid.push(update);
      } else {
        rejected.push({ item: update, reason: result.reason || 'Unknown' });
      }
    } else {
      valid.push(update);
    }
  });

  return { valid, rejected };
}

/**
 * Calculates a rolling average to smooth noisy data.
 */
export function rollingAverage(values: number[], windowSize: number = 5): number[] {
  const result: number[] = [];
  for (let i = 0; i < values.length; i++) {
    const start = Math.max(0, i - windowSize + 1);
    const window = values.slice(start, i + 1);
    result.push(window.reduce((s, v) => s + v, 0) / window.length);
  }
  return result;
}

/**
 * Detects sudden volume spikes that may indicate data errors or flash crashes.
 */
export function detectVolumeSpike(
  currentVolume: number,
  averageVolume: number,
  threshold: number = 10
): boolean {
  if (averageVolume <= 0) return false;
  return currentVolume / averageVolume > threshold;
}

/**
 * Normalizes timestamps across multiple data points to the latest one.
 * Marks any data point older than 5 seconds as delayed.
 */
export function normalizeTimestamps<T extends { timestamp: number }>(
  dataPoints: T[]
): Array<T & { isDelayed: boolean }> {
  if (dataPoints.length === 0) return [];
  const latestTimestamp = Math.max(...dataPoints.map((d) => d.timestamp));
  return dataPoints.map((d) => ({
    ...d,
    isDelayed: latestTimestamp - d.timestamp > 5000,
  }));
}
