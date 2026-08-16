import { describe, expect, it } from "vitest";
import { formatCurrency, formatPercent, formatCompact } from "./format";

describe("formatCurrency", () => {
  it("formats USD by default", () => {
    expect(formatCurrency(1234.5)).toBe("$1,234.50");
  });
  it("handles zero and null", () => {
    expect(formatCurrency(0)).toBe("$0.00");
    expect(formatCurrency(null)).toBe("$0.00");
  });
  it("returns a dash for non-finite values", () => {
    expect(formatCurrency(NaN)).toBe("—");
  });
});

describe("formatPercent", () => {
  it("scales a ratio to a percentage", () => {
    expect(formatPercent(0.125)).toBe("12.5%");
  });
  it("respects digit precision", () => {
    expect(formatPercent(1 / 3, 2)).toBe("33.33%");
  });
});

describe("formatCompact", () => {
  it("abbreviates large numbers", () => {
    expect(formatCompact(1_500_000)).toBe("1.5M");
  });
  it("passes through small numbers", () => {
    expect(formatCompact(42)).toBe("42");
  });
});
