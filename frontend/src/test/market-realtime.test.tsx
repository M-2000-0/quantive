import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  setCache,
  getCache,
  getCacheAge,
  clearCache,
  isCacheStale,
} from '../lib/marketCache';
import {
  validatePriceUpdate,
  validateYield,
  validateFxRate,
  validateCreditSpread,
  isDataStale,
  filterAnomalies,
  rollingAverage,
  detectVolumeSpike,
  normalizeTimestamps,
} from '../lib/marketValidation';
import { getProviderStatus } from '../lib/marketProviders';

// ── marketCache Tests ────────────────────────────────────────────────

describe('marketCache', () => {
  beforeEach(() => {
    clearCache();
  });

  describe('setCache / getCache', () => {
    it('stores and retrieves data', () => {
      setCache('test_key', { price: 100 }, 60000);
      const result = getCache<{ price: number }>('test_key');
      expect(result).toEqual({ price: 100 });
    });

    it('returns null for expired cache', () => {
      setCache('expiring_key', { price: 100 }, 0); // 0ms TTL — already expired
      const result = getCache('expiring_key');
      expect(result).toBeNull();
    });

    it('returns null for non-existent key', () => {
      expect(getCache('nonexistent')).toBeNull();
    });

    it('handles multiple keys independently', () => {
      setCache('key1', 'value1', 60000);
      setCache('key2', 'value2', 60000);
      expect(getCache('key1')).toBe('value1');
      expect(getCache('key2')).toBe('value2');
    });

    it('overwrites existing keys', () => {
      setCache('key1', 'old_value', 60000);
      setCache('key1', 'new_value', 60000);
      expect(getCache('key1')).toBe('new_value');
    });
  });

  describe('clearCache', () => {
    it('clears a specific key', () => {
      setCache('to_clear', 'data', 60000);
      clearCache('to_clear');
      expect(getCache('to_clear')).toBeNull();
    });

    it('clears all keys when no argument', () => {
      setCache('k1', 'v1', 60000);
      setCache('k2', 'v2', 60000);
      clearCache();
      expect(getCache('k1')).toBeNull();
      expect(getCache('k2')).toBeNull();
    });
  });

  describe('getCacheAge', () => {
    it('returns age in milliseconds', () => {
      setCache('age_test', 'data', 60000);
      const age = getCacheAge('age_test');
      expect(age).not.toBeNull();
      expect(age!).toBeGreaterThanOrEqual(0);
      expect(age!).toBeLessThan(100);
    });

    it('returns null for non-existent key', () => {
      expect(getCacheAge('nonexistent')).toBeNull();
    });
  });

  describe('isCacheStale', () => {
    it('returns false for fresh cache', () => {
      setCache('fresh', 'data', 60000);
      expect(isCacheStale('fresh', 10000)).toBe(false);
    });

    it('returns true for non-existent cache', () => {
      expect(isCacheStale('nonexistent', 10000)).toBe(true);
    });
  });
});

// ── marketValidation Tests ───────────────────────────────────────────

describe('marketValidation', () => {
  describe('validatePriceUpdate', () => {
    it('accepts valid price changes', () => {
      const result = validatePriceUpdate(100, 102, 5);
      expect(result.valid).toBe(true);
    });

    it('rejects large price jumps', () => {
      const result = validatePriceUpdate(100, 150, 5);
      expect(result.valid).toBe(false);
      expect(result.reason).toContain('50.0%');
    });

    it('rejects zero or negative prices', () => {
      expect(validatePriceUpdate(0, 100, 5).valid).toBe(false);
      expect(validatePriceUpdate(100, 0, 5).valid).toBe(false);
      expect(validatePriceUpdate(100, -50, 5).valid).toBe(false);
    });

    it('rejects NaN values', () => {
      expect(validatePriceUpdate(NaN, 100, 5).valid).toBe(false);
      expect(validatePriceUpdate(100, NaN, 5).valid).toBe(false);
    });

    it('accepts unchanged price', () => {
      expect(validatePriceUpdate(100, 100, 5).valid).toBe(true);
    });

    it('respects custom threshold', () => {
      expect(validatePriceUpdate(100, 103, 5).valid).toBe(true);
      expect(validatePriceUpdate(100, 103, 2).valid).toBe(false);
    });
  });

  describe('validateYield', () => {
    it('accepts normal yields', () => {
      expect(validateYield(4.5).valid).toBe(true);
      expect(validateYield(0).valid).toBe(true);
      expect(validateYield(-0.5).valid).toBe(true);
    });

    it('rejects extreme yields', () => {
      expect(validateYield(35).valid).toBe(false);
      expect(validateYield(-10).valid).toBe(false);
    });

    it('rejects NaN', () => {
      expect(validateYield(NaN).valid).toBe(false);
    });
  });

  describe('validateFxRate', () => {
    it('accepts normal EUR/USD', () => {
      expect(validateFxRate('EUR/USD', 1.08).valid).toBe(true);
    });

    it('rejects extreme EUR/USD', () => {
      expect(validateFxRate('EUR/USD', 0.3).valid).toBe(false);
      expect(validateFxRate('EUR/USD', 3.0).valid).toBe(false);
    });

    it('accepts normal USD/JPY', () => {
      expect(validateFxRate('USD/JPY', 148).valid).toBe(true);
    });

    it('rejects extreme USD/JPY', () => {
      expect(validateFxRate('USD/JPY', 30).valid).toBe(false);
      expect(validateFxRate('USD/JPY', 300).valid).toBe(false);
    });

    it('rejects negative and zero', () => {
      expect(validateFxRate('EUR/USD', -1).valid).toBe(false);
      expect(validateFxRate('EUR/USD', 0).valid).toBe(false);
    });
  });

  describe('validateCreditSpread', () => {
    it('accepts normal spreads', () => {
      expect(validateCreditSpread(82).valid).toBe(true);
      expect(validateCreditSpread(310).valid).toBe(true);
      expect(validateCreditSpread(0).valid).toBe(true);
    });

    it('rejects extreme spreads', () => {
      expect(validateCreditSpread(-200).valid).toBe(false);
      expect(validateCreditSpread(6000).valid).toBe(false);
    });
  });

  describe('isDataStale', () => {
    it('returns false for fresh data', () => {
      expect(isDataStale(Date.now(), 10000)).toBe(false);
    });

    it('returns true for old data', () => {
      expect(isDataStale(Date.now() - 20000, 10000)).toBe(true);
    });
  });

  describe('filterAnomalies', () => {
    it('filters out bad ticks', () => {
      const updates = [
        { price: 100, previousPrice: 100 },
        { price: 200, previousPrice: 100 }, // 100% jump — anomaly
        { price: 102, previousPrice: 100 }, // 2% — normal
      ];
      const { valid, rejected } = filterAnomalies(updates, 5);
      expect(valid).toHaveLength(2);
      expect(rejected).toHaveLength(1);
      expect(rejected[0].item.price).toBe(200);
    });

    it('passes through items without previous price', () => {
      const updates = [{ price: 100 }];
      const { valid } = filterAnomalies(updates);
      expect(valid).toHaveLength(1);
    });
  });

  describe('rollingAverage', () => {
    it('calculates rolling average', () => {
      const values = [10, 20, 30, 40, 50];
      const avg = rollingAverage(values, 3);
      expect(avg[0]).toBe(10);
      expect(avg[2]).toBeCloseTo(20); // (10+20+30)/3
      expect(avg[4]).toBeCloseTo(40); // (30+40+50)/3
    });

    it('handles window size larger than data', () => {
      const values = [10, 20];
      const avg = rollingAverage(values, 5);
      expect(avg).toHaveLength(2);
      expect(avg[0]).toBe(10);
      expect(avg[1]).toBe(15);
    });
  });

  describe('detectVolumeSpike', () => {
    it('detects volume spikes', () => {
      expect(detectVolumeSpike(100000, 5000, 10)).toBe(true);
    });

    it('does not flag normal volume', () => {
      expect(detectVolumeSpike(8000, 5000, 10)).toBe(false);
    });

    it('handles zero average volume', () => {
      expect(detectVolumeSpike(100, 0, 10)).toBe(false);
    });
  });

  describe('normalizeTimestamps', () => {
    it('marks delayed data points', () => {
      const now = Date.now();
      const data = [
        { timestamp: now },
        { timestamp: now - 6000 }, // 6s old
        { timestamp: now - 1000 },
      ];
      const result = normalizeTimestamps(data);
      expect(result[0].isDelayed).toBe(false);
      expect(result[1].isDelayed).toBe(true);
      expect(result[2].isDelayed).toBe(false);
    });

    it('handles empty array', () => {
      expect(normalizeTimestamps([])).toHaveLength(0);
    });
  });
});

// ── marketProviders Tests ────────────────────────────────────────────

describe('marketProviders', () => {
  describe('getProviderStatus', () => {
    it('returns status for all providers', () => {
      const status = getProviderStatus();
      expect(status.yahoo).toBeDefined();
      expect(status.polygon).toBeDefined();
      expect(status.alphaVantage).toBeDefined();
      expect(status.fred).toBeDefined();
    });

    it('has remaining and ready fields', () => {
      const status = getProviderStatus();
      Object.values(status).forEach((provider) => {
        expect(typeof provider.remaining).toBe('number');
        expect(typeof provider.ready).toBe('boolean');
      });
    });
  });
});
