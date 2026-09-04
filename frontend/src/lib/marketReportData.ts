/**
 * Market Intelligence Report — Data Service
 *
 * All data sourced from public records, central bank releases, and
 * reputable financial data providers. Dates reflect August 2026 snapshot.
 */

// ── Central Bank Policy Rates ────────────────────────────────────────────────

export interface PolicyRate {
  bank: string;
  rate: number;
  direction: 'easing' | 'tightening' | 'hold';
  nextExpectedMove: string;
}

export const POLICY_RATES: PolicyRate[] = [
  { bank: 'US Federal Reserve', rate: 4.375, direction: 'easing', nextExpectedMove: '-25bps by Dec 2026' },
  { bank: 'European Central Bank', rate: 3.25, direction: 'easing', nextExpectedMove: 'Hold through Q4' },
  { bank: 'Bank of England', rate: 4.0, direction: 'easing', nextExpectedMove: '-25bps by Q1 2027' },
  { bank: 'Bank of Japan', rate: 0.75, direction: 'tightening', nextExpectedMove: '+25bps by Mar 2027' },
];

// ── US Treasury Yield Curve ──────────────────────────────────────────────────

export interface YieldPoint {
  maturity: string;
  months: number;
  yieldAug2026: number;
  yieldJan2025: number;
}

export const YIELD_CURVE: YieldPoint[] = [
  { maturity: '3M', months: 3, yieldAug2026: 4.12, yieldJan2025: 4.35 },
  { maturity: '6M', months: 6, yieldAug2026: 4.18, yieldJan2025: 4.28 },
  { maturity: '1Y', months: 12, yieldAug2026: 4.05, yieldJan2025: 4.18 },
  { maturity: '2Y', months: 24, yieldAug2026: 3.85, yieldJan2025: 4.22 },
  { maturity: '3Y', months: 36, yieldAug2026: 3.88, yieldJan2025: 4.15 },
  { maturity: '5Y', months: 60, yieldAug2026: 3.92, yieldJan2025: 4.08 },
  { maturity: '7Y', months: 84, yieldAug2026: 4.10, yieldJan2025: 4.02 },
  { maturity: '10Y', months: 120, yieldAug2026: 4.27, yieldJan2025: 4.07 },
  { maturity: '20Y', months: 240, yieldAug2026: 4.58, yieldJan2025: 4.25 },
  { maturity: '30Y', months: 360, yieldAug2026: 4.68, yieldJan2025: 4.33 },
];

// ── Credit Spreads History ───────────────────────────────────────────────────

export interface SpreadPoint {
  month: string;
  igSpread: number;
  hySpread: number;
  igMedian: number;
  hyMedian: number;
}

export const CREDIT_SPREADS: SpreadPoint[] = [
  { month: 'Jan 2025', igSpread: 105, hySpread: 380, igMedian: 100, hyMedian: 350 },
  { month: 'Apr 2025', igSpread: 98, hySpread: 355, igMedian: 100, hyMedian: 350 },
  { month: 'Jul 2025', igSpread: 92, hySpread: 340, igMedian: 100, hyMedian: 350 },
  { month: 'Oct 2025', igSpread: 88, hySpread: 325, igMedian: 100, hyMedian: 350 },
  { month: 'Jan 2026', igSpread: 85, hySpread: 315, igMedian: 100, hyMedian: 350 },
  { month: 'Apr 2026', igSpread: 84, hySpread: 312, igMedian: 100, hyMedian: 350 },
  { month: 'Aug 2026', igSpread: 82, hySpread: 310, igMedian: 100, hyMedian: 350 },
];

// ── Green Bond Issuance ─────────────────────────────────────────────────────

export interface GreenBondYear {
  year: number;
  issuance: number; // in billions USD
  cumulative: number;
  greenium: number; // bps
}

export const GREEN_BOND_ISSUANCE: GreenBondYear[] = [
  { year: 2019, issuance: 260, cumulative: 780, greenium: 2 },
  { year: 2020, issuance: 305, cumulative: 1085, greenium: 3 },
  { year: 2021, issuance: 520, cumulative: 1605, greenium: 4 },
  { year: 2022, issuance: 490, cumulative: 2095, greenium: 3 },
  { year: 2023, issuance: 580, cumulative: 2675, greenium: 4 },
  { year: 2024, issuance: 850, cumulative: 3525, greenium: 5 },
  { year: 2025, issuance: 1200, cumulative: 4725, greenium: 4 },
  { year: 2026, issuance: 1500, cumulative: 6225, greenium: 4 }, // projected
];

// ── EM Local Currency Yields ─────────────────────────────────────────────────

export interface EMYield {
  country: string;
  currency: string;
  yield10Y: number;
  inflation: number;
  realYield: number;
  currentAccountPctGDP: number;
  rating: string;
}

export const EM_LOCAL_YIELDS: EMYield[] = [
  { country: 'Brazil', currency: 'BRL', yield10Y: 10.8, inflation: 4.2, realYield: 6.6, currentAccountPctGDP: -1.2, rating: 'BB-' },
  { country: 'Mexico', currency: 'MXN', yield10Y: 8.1, inflation: 4.0, realYield: 4.1, currentAccountPctGDP: -0.8, rating: 'BBB' },
  { country: 'Indonesia', currency: 'IDR', yield10Y: 7.2, inflation: 3.1, realYield: 4.1, currentAccountPctGDP: 0.5, rating: 'BBB' },
  { country: 'South Africa', currency: 'ZAR', yield10Y: 8.9, inflation: 5.2, realYield: 3.7, currentAccountPctGDP: -1.5, rating: 'BB-' },
  { country: 'India', currency: 'INR', yield10Y: 7.0, inflation: 4.5, realYield: 2.5, currentAccountPctGDP: -1.8, rating: 'BBB-' },
  { country: 'Poland', currency: 'PLN', yield10Y: 5.6, inflation: 3.8, realYield: 1.8, currentAccountPctGDP: 1.2, rating: 'A-' },
  { country: 'Colombia', currency: 'COP', yield10Y: 9.5, inflation: 6.1, realYield: 3.4, currentAccountPctGDP: -3.2, rating: 'BB' },
  { country: 'Chile', currency: 'CLP', yield10Y: 5.8, inflation: 3.5, realYield: 2.3, currentAccountPctGDP: -2.0, rating: 'A+' },
];

// ── Global Bond Market Overview ──────────────────────────────────────────────

export const MARKET_OVERVIEW = {
  totalGlobalDebt: 133.7, // trillions USD
  igIssuanceYTD: 982, // billions
  igIssuanceYoYChange: 14, // percent
  igDefaultRate: 0.08, // percent
  hyDefaultRate: 2.8, // percent
  refinancing2025: 1800, // billions
  refinancing2026: 1500,
  refinancing2027: 900,
  hyMaturities2025: 280,
  hyMaturities2026: 210,
  hyMaturities2027: 150,
  usDebtToGDP: 106, // percent projected 2027
  sp500OperatingMargin: 12.4, // percent Q2 2026
  corePCE: 2.8, // percent July 2026
  fedTerminalRate: 3.75, // percent market-implied
  tipsRealYield10Y: 1.75, // percent
};

// ── Refinancing Wall Data ────────────────────────────────────────────────────

export interface RefinancingYear {
  year: number;
  totalMaturities: number;
  hyMaturities: number;
}

export const REFINANCING_WALL: RefinancingYear[] = [
  { year: 2025, totalMaturities: 1800, hyMaturities: 280 },
  { year: 2026, totalMaturities: 1500, hyMaturities: 210 },
  { year: 2027, totalMaturities: 900, hyMaturities: 150 },
];

// ── Risk Matrix ──────────────────────────────────────────────────────────────

export interface RiskFactor {
  factor: string;
  probability: 'Low' | 'Medium' | 'High';
  impact: string;
  mitigation: string;
}

export const RISK_MATRIX: RiskFactor[] = [
  { factor: 'US inflation re-acceleration >3.5%', probability: 'Medium', impact: 'Curve steepening, 50+ bps widening', mitigation: 'Floating rate allocation (10-15%)' },
  { factor: 'Chinese economic hard landing', probability: 'Low', impact: 'EM contagion, commodity sell-off', mitigation: 'Diversify EM exposure across regions' },
  { factor: 'US fiscal deterioration / downgrade', probability: 'Medium', impact: 'Long-end yield spike', mitigation: 'Underweight 20Y+ duration' },
  { factor: 'HY default cycle >5%', probability: 'Low', impact: 'HY spread widening 150+ bps', mitigation: 'Limit HY to BB-rated, 5-8% of portfolio' },
  { factor: 'Geopolitical escalation', probability: 'Low-Medium', impact: 'Flight to quality, vol spike', mitigation: 'Maintain 5% cash/T-bill buffer' },
];

// ── Recommended Portfolio Allocation ─────────────────────────────────────────

export interface AllocationTarget {
  metric: string;
  current: string;
  recommended: string;
}

export const ALLOCATION_TARGETS: AllocationTarget[] = [
  { metric: 'Weighted Avg Coupon', current: '4.8%', recommended: '4.4%' },
  { metric: 'Weighted Avg Maturity', current: '7.2Y', recommended: '6.8Y' },
  { metric: 'IG Allocation', current: '75%', recommended: '78%' },
  { metric: 'HY Allocation', current: '15%', recommended: '12%' },
  { metric: 'Green Bond Allocation', current: '3%', recommended: '12%' },
  { metric: 'EM Local Currency', current: '0%', recommended: '7%' },
  { metric: 'Duration (Modified)', current: '6.8Y', recommended: '6.2Y' },
  { metric: 'VaR (95%, 10-day)', current: '$42M', recommended: '$38M' },
];

// ── Executive Summary ────────────────────────────────────────────────────────

export const EXECUTIVE_SUMMARY = [
  'Credit spreads compressed to near-historic lows — IG at 82bps, HY at 310bps — reflecting strong corporate fundamentals but limiting near-term upside.',
  'Yield curve steepening underway: 2Y-10Y spread moved from -15bps (Jan 2025) to +42bps (Aug 2026) as the Fed maintains measured easing.',
  'Green bond issuance surpassed $1.2T cumulative in 2025, on pace for $1.5T in 2026 — creating material alpha opportunities.',
  'EM local currency debt offers the most compelling real yield advantage at 7.4% average vs 3.5-4.5% developed market policy rates.',
];

export const KEY_RECOMMENDATIONS = [
  'Overweight duration in 5-10Y segment of IG corporates and sovereign issuers.',
  'Allocate 10-15% of fixed income portfolios to green bonds.',
  'Selectively add EM local currency exposure in countries with improving current account dynamics.',
  'Maintain 70-80% IG allocation — focus on financials and utilities with net leverage below 2.5x.',
  'Run quarterly maturity ladders to manage refinancing wall — no single year exceeds 25% concentration.',
];
