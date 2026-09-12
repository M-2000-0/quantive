// ── Peer Intelligence ────────────────────────────────────────────────
// Aggregated peer consensus, benchmarks, sentiment, and actions.
// Mock data mirrors production API shapes for demo and test use.

export type ConsensusTrend = 'increasing' | 'decreasing' | 'stable';
export type ConsensusCategory =
  | 'duration'
  | 'allocation'
  | 'hedging'
  | 'credit'
  | 'refinancing'
  | 'risk';

export interface ConsensusIndicator {
  id: string;
  category: ConsensusCategory;
  title: string;
  description: string;
  consensusPercentage: number;
  sampleSize: number;
  confidence: number;
  trend: ConsensusTrend;
  trendDelta: number;
  actionable?: boolean;
}

export interface PeerBenchmark {
  id: string;
  metric: string;
  category?: string;
  insight?: string;
  userValue: number;
  peerMedian: number;
  peerP10: number;
  peerP25: number;
  peerP75: number;
  peerP90: number;
  unit: string;
  percentile: number;
}

export type MarketSentimentValue = 'bullish' | 'bearish' | 'neutral';

export interface MarketSentiment {
  id: string;
  indicator: string;
  score: number;
  sentiment: MarketSentimentValue;
  dataPoints: number;
  consensus: number;
  timeframe: string;
  sources: string[];
}

export interface PeerAction {
  id: string;
  peerGroup: string;
  action: string;
  percentage: number;
  rationale: string;
  timestamp: string;
  instrumentType?: string;
  peerCount?: number;
  avgSavings?: number;
  riskChange?: string;
  timeframe?: string;
}

export const MOCK_CONSENSUS_INDICATORS: ConsensusIndicator[] = [
  { id: 'ci-1', category: 'duration', title: 'Extending Duration', description: 'Peers are lengthening portfolio duration to lock in yields.', consensusPercentage: 78, sampleSize: 1240, confidence: 88, trend: 'increasing', trendDelta: 6, actionable: true },
  { id: 'ci-2', category: 'hedging', title: 'Adding FX Hedges', description: 'Currency hedging overlays are being added across USD exposures.', consensusPercentage: 71, sampleSize: 1180, confidence: 84, trend: 'increasing', trendDelta: 4, actionable: true },
  { id: 'ci-3', category: 'allocation', title: 'Green Bond Allocation', description: 'Dedicated green sleeves now average 12% of peer portfolios.', consensusPercentage: 64, sampleSize: 1090, confidence: 81, trend: 'increasing', trendDelta: 3, actionable: true },
  { id: 'ci-4', category: 'credit', title: 'Tightening Credit Standards', description: 'Peers are raising minimum rating thresholds for new paper.', consensusPercentage: 58, sampleSize: 980, confidence: 77, trend: 'stable', trendDelta: 0 },
  { id: 'ci-5', category: 'refinancing', title: 'Pre-funding 2027 Maturities', description: 'Early refinancing of 2027 walls is gaining traction.', consensusPercentage: 52, sampleSize: 870, confidence: 73, trend: 'decreasing', trendDelta: -2 },
  { id: 'ci-6', category: 'risk', title: 'Raising Liquidity Buffers', description: 'Overnight liquidity buffers are being rebuilt after drawdowns.', consensusPercentage: 47, sampleSize: 810, confidence: 70, trend: 'stable', trendDelta: 1 },
];

export const MOCK_PEER_BENCHMARKS: PeerBenchmark[] = [
  { id: 'pb-1', metric: 'Weighted Average Yield', userValue: 4.2, peerMedian: 4.0, peerP10: 3.1, peerP25: 3.6, peerP75: 4.5, peerP90: 5.0, unit: '%', percentile: 62 },
  { id: 'pb-2', metric: 'Average Duration', userValue: 7.1, peerMedian: 6.4, peerP10: 3.8, peerP25: 5.2, peerP75: 7.8, peerP90: 9.4, unit: 'yrs', percentile: 70 },
  { id: 'pb-3', metric: 'FX Exposure', userValue: 28, peerMedian: 22, peerP10: 8, peerP25: 15, peerP75: 30, peerP90: 41, unit: '%', percentile: 68 },
  { id: 'pb-4', metric: 'Green Share', userValue: 9, peerMedian: 12, peerP10: 2, peerP25: 6, peerP75: 18, peerP90: 27, unit: '%', percentile: 38 },
  { id: 'pb-5', metric: 'Liquidity Buffer', userValue: 6.5, peerMedian: 5.0, peerP10: 2.0, peerP25: 3.5, peerP75: 7.0, peerP90: 10.0, unit: '%', percentile: 74 },
  { id: 'pb-6', metric: 'Refinancing Risk', userValue: 44, peerMedian: 50, peerP10: 22, peerP25: 35, peerP75: 62, peerP90: 78, unit: '/100', percentile: 41 },
];

export const MOCK_MARKET_SENTIMENT: MarketSentiment[] = [
  { id: 'ms-1', indicator: 'Rate Outlook', score: 42, sentiment: 'bullish', dataPoints: 1240, consensus: 68, timeframe: '30d', sources: ['Desk surveys', 'Futures positioning'] },
  { id: 'ms-2', indicator: 'Credit Spreads', score: -18, sentiment: 'bearish', dataPoints: 980, consensus: 55, timeframe: '30d', sources: ['CDS moves', 'New-issue concessions'] },
  { id: 'ms-3', indicator: 'FX Volatility', score: 5, sentiment: 'neutral', dataPoints: 870, consensus: 51, timeframe: '30d', sources: ['Options desks'] },
  { id: 'ms-4', indicator: 'Green Demand', score: 61, sentiment: 'bullish', dataPoints: 760, consensus: 72, timeframe: '30d', sources: ['Order books', 'Fund flows'] },
];

export const MOCK_PEER_ACTIONS: PeerAction[] = [
  { id: 'pa-1', peerGroup: 'Sovereign peers', action: 'Extended duration past 7 years', percentage: 34, rationale: 'Lock in yields before cuts', timestamp: '2026-08-28' },
  { id: 'pa-2', peerGroup: 'Sovereign peers', action: 'Added cross-currency swaps', percentage: 27, rationale: 'Hedge USD exposure', timestamp: '2026-08-25' },
  { id: 'pa-3', peerGroup: 'Agency peers', action: 'Opened green bond tap', percentage: 22, rationale: 'Strong investor demand', timestamp: '2026-08-21' },
  { id: 'pa-4', peerGroup: 'Sovereign peers', action: 'Pre-funded 2027 maturities', percentage: 18, rationale: 'Avoid refinancing wall', timestamp: '2026-08-18' },
  { id: 'pa-5', peerGroup: 'Regional peers', action: 'Raised liquidity buffers', percentage: 15, rationale: 'Prepare for volatility', timestamp: '2026-08-15' },
];

export function getConsensusByCategory(category: string): ConsensusIndicator[] {
  return MOCK_CONSENSUS_INDICATORS.filter((c) => c.category === category);
}

export function getTopConsensus(count: number): ConsensusIndicator[] {
  return [...MOCK_CONSENSUS_INDICATORS]
    .sort((a, b) => b.consensusPercentage - a.consensusPercentage)
    .slice(0, count);
}

export function getIncreasingTrends(): ConsensusIndicator[] {
  return MOCK_CONSENSUS_INDICATORS.filter((c) => c.trend === 'increasing');
}

export function getPercentileLabel(percentile: number): string {
  if (percentile >= 90) return 'Top 10%';
  if (percentile >= 75) return 'Top 25%';
  if (percentile >= 50) return 'Above Median';
  if (percentile >= 25) return 'Below Median';
  return 'Bottom 25%';
}

export function getPercentileColor(percentile: number): string {
  if (percentile >= 75) return 'text-emerald-600';
  if (percentile >= 50) return 'text-blue-600';
  if (percentile >= 25) return 'text-amber-600';
  return 'text-red-600';
}

export function getSentimentColor(sentiment: MarketSentimentValue): string {
  if (sentiment === 'bullish') return 'text-emerald-600';
  if (sentiment === 'bearish') return 'text-red-600';
  return 'text-slate-600';
}

export function getSentimentIcon(sentiment: MarketSentimentValue): string {
  if (sentiment === 'bullish') return '📈';
  if (sentiment === 'bearish') return '📉';
  return '➡️';
}

export function getCategoryIcon(category: string): string {
  const icons: Record<string, string> = {
    duration: '⏱️',
    allocation: '📊',
    hedging: '🛡️',
    credit: '💳',
    refinancing: '🔄',
    risk: '⚠️',
    fx: '💱',
    rates: '📈',
  };
  return icons[category] || '📌';
}
