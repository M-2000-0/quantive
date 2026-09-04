import { describe, it, expect } from 'vitest';
import {
  formatCurrency,
  formatPercent,
  formatNumber,
  formatDate,
  formatDateTime,
  formatRuntime,
  statusVariant,
  statusLabel,
} from '../utils';

// ── formatCurrency ──────────────────────────────────────────────────
describe('formatCurrency', () => {
  it('formats zero', () => {
    expect(formatCurrency(0)).toBe('$0');
  });

  it('formats small numbers without abbreviation', () => {
    expect(formatCurrency(1234)).toBe('$1,234');
    expect(formatCurrency(999999)).toBe('$999,999');
  });

  it('formats millions with M suffix', () => {
    expect(formatCurrency(1_000_000)).toBe('$1.0M');
    expect(formatCurrency(1_500_000)).toBe('$1.5M');
    expect(formatCurrency(12_345_678)).toBe('$12.3M');
  });

  it('formats billions with B suffix', () => {
    expect(formatCurrency(1_000_000_000)).toBe('$1.00B');
    expect(formatCurrency(2_500_000_000)).toBe('$2.50B');
  });

  it('formats trillions with T suffix', () => {
    expect(formatCurrency(1_000_000_000_000)).toBe('$1.00T');
    expect(formatCurrency(3_500_000_000_000)).toBe('$3.50T');
  });

  it('handles negative values', () => {
    expect(formatCurrency(-1_000_000)).toBe('$-1.0M');
    expect(formatCurrency(-500)).toBe('$-500');
  });

  it('handles very large numbers', () => {
    expect(formatCurrency(100_000_000_000_000)).toBe('$100.00T');
  });
});

// ── formatPercent ───────────────────────────────────────────────────
describe('formatPercent', () => {
  it('formats 0', () => {
    expect(formatPercent(0)).toBe('0.0%');
  });

  it('formats decimal to percentage', () => {
    expect(formatPercent(0.05)).toBe('5.0%');
    expect(formatPercent(0.1234)).toBe('12.3%');
    expect(formatPercent(1)).toBe('100.0%');
  });

  it('respects decimals parameter', () => {
    expect(formatPercent(0.12345, 2)).toBe('12.35%');
    expect(formatPercent(0.5, 0)).toBe('50%');
  });

  it('handles negative percentages', () => {
    expect(formatPercent(-0.05)).toBe('-5.0%');
  });
});

// ── formatNumber ────────────────────────────────────────────────────
describe('formatNumber', () => {
  it('formats with locale separators', () => {
    expect(formatNumber(1234567)).toBe('1,234,567');
    expect(formatNumber(100)).toBe('100');
    expect(formatNumber(0)).toBe('0');
  });
});

// ── formatDate ──────────────────────────────────────────────────────
describe('formatDate', () => {
  it('formats ISO date string', () => {
    const result = formatDate('2025-01-15T10:30:00Z');
    // en-GB format: 15 Jan 2025
    expect(result).toMatch(/\d{2} \w{3} \d{4}/);
  });

  it('handles different dates', () => {
    const result = formatDate('2024-12-25T00:00:00Z');
    expect(result).toMatch(/\d{2} \w{3} \d{4}/);
  });
});

// ── formatDateTime ──────────────────────────────────────────────────
describe('formatDateTime', () => {
  it('formats ISO datetime with time', () => {
    const result = formatDateTime('2025-01-15T10:30:00Z');
    expect(result).toMatch(/\d{2} \w{3} \d{4}, \d{2}:\d{2}/);
  });
});

// ── formatRuntime ───────────────────────────────────────────────────
describe('formatRuntime', () => {
  it('formats seconds', () => {
    expect(formatRuntime(5.5)).toBe('5.5s');
    expect(formatRuntime(30)).toBe('30.0s');
  });

  it('formats minutes', () => {
    expect(formatRuntime(60)).toBe('1.0m');
    expect(formatRuntime(125)).toBe('2.1m');
  });

  it('formats exactly 59 seconds as seconds', () => {
    expect(formatRuntime(59.9)).toBe('59.9s');
  });
});

// ── statusVariant ───────────────────────────────────────────────────
describe('statusVariant', () => {
  it('maps completed to success', () => {
    expect(statusVariant('completed')).toBe('success');
  });

  it('maps failed to danger', () => {
    expect(statusVariant('failed')).toBe('danger');
  });

  it('maps running/queued/solving to info', () => {
    expect(statusVariant('running')).toBe('info');
    expect(statusVariant('queued')).toBe('info');
    expect(statusVariant('solving')).toBe('info');
  });

  it('maps intermediate statuses to warning', () => {
    expect(statusVariant('scenario_generation')).toBe('warning');
    expect(statusVariant('benchmarking')).toBe('warning');
    expect(statusVariant('stress_testing')).toBe('warning');
  });

  it('maps unknown to default', () => {
    expect(statusVariant('unknown_status')).toBe('default');
    expect(statusVariant('')).toBe('default');
  });
});

// ── statusLabel ─────────────────────────────────────────────────────
describe('statusLabel', () => {
  it('capitalizes first letter of each word', () => {
    expect(statusLabel('completed')).toBe('Completed');
    expect(statusLabel('failed')).toBe('Failed');
  });

  it('replaces underscores with spaces', () => {
    expect(statusLabel('scenario_generation')).toBe('Scenario Generation');
    expect(statusLabel('stress_testing')).toBe('Stress Testing');
  });

  it('handles single word', () => {
    expect(statusLabel('running')).toBe('Running');
  });
});
