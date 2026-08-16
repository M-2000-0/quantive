/** Format a number as USD currency. */
export function formatCurrency(value: number | null | undefined, currency = "USD"): string {
  const n = Number(value ?? 0);
  if (!Number.isFinite(n)) return "—";
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(n);
}

/** Format a ratio (0..1) as a percentage. */
export function formatPercent(value: number | null | undefined, digits = 1): string {
  const n = Number(value ?? 0);
  if (!Number.isFinite(n)) return "—";
  return `${(n * 100).toFixed(digits)}%`;
}

/** Abbreviate a large number: 1_500_000 -> "1.5M". */
export function formatCompact(value: number | null | undefined): string {
  const n = Number(value ?? 0);
  if (!Number.isFinite(n)) return "—";
  return new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(n);
}
