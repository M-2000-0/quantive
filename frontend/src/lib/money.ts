// Shared money utilities for Quantive frontend
// Money is stored as integer cents on the wire

export function centsToUsd(cents: number): string {
  return (cents / 100).toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
  });
}

export function dollarsToCents(dollars: string): number {
  const n = Number.parseFloat(dollars);
  if (!Number.isFinite(n) || n <= 0) throw new Error('Enter an amount greater than $0');
  return Math.round(n * 100);
}
