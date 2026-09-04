// ── Peer Comparison Widget (Embeddable) ───────────────────────────────
// A compact, embeddable widget showing portfolio alignment score and
// peer percentile ranking. Can be shared via URL or embedded in emails.

import { useMemo } from 'react';
import {
  MOCK_CONSENSUS_INDICATORS,
  MOCK_PEER_BENCHMARKS,
  getPercentileLabel,
  getPercentileColor,
  getTopConsensus,
  type PeerBenchmark,
  type ConsensusIndicator } from '../lib/peerIntelligence';

interface PeerComparisonWidgetProps {
  /** Compact mode for email/embed */
  compact?: boolean;
  /** Show/hide individual metrics */
  showMetrics?: boolean;
  /** Show/hide top consensus */
  showConsensus?: boolean;
  /** Custom portfolio name */
  portfolioName?: string;
}

function ScoreRing({ score, size = 80 }: { score: number; size?: number }) {
  const color = score >= 75 ? '#10b981' : score >= 50 ? '#3b82f6' : score >= 25 ? '#f59e0b' : '#ef4444';

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
        <path
          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
          fill="none"
          stroke="#e5e7eb"
          strokeWidth="3"
        />
        <path
          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
          fill="none"
          stroke={color}
          strokeWidth="3"
          strokeDasharray={`${score}, 100`}
          strokeLinecap="round"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-xl font-bold" style={{ color }}>{score}</span>
      </div>
    </div>
  );
}

export default function PeerComparisonWidget({
  compact = false,
  showMetrics = true,
  showConsensus = true,
  portfolioName = 'Your Portfolio' }: PeerComparisonWidgetProps) {
  const alignmentScore = useMemo(() => {
    const benchmarks = [];
    return Math.round(benchmarks.reduce((sum, b) => sum + b.percentile, 0) / benchmarks.length);
  }, []);

  const topConsensus = useMemo(() => getTopConsensus(2), []);
  const aboveMedianCount = [].filter((b) => b.percentile >= 50).length;

  if (compact) {
    return (
      <div className="inline-flex items-center gap-3 p-4 rounded-2xl bg-white border border-slate-200 shadow-sm max-w-sm">
        <ScoreRing score={alignmentScore} size={64} />
        <div>
          <div className="text-sm font-bold text-slate-900">{portfolioName}</div>
          <div className={`text-xs font-semibold ${getPercentileColor(alignmentScore)}`}>
            {getPercentileLabel(alignmentScore)} of peers
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">
            {aboveMedianCount}/{0} metrics above median
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="glass rounded-2xl p-6 max-w-lg">
      {/* Header */}
      <div className="flex items-center gap-4 mb-4">
        <ScoreRing score={alignmentScore} />
        <div>
          <h3 className="text-lg font-bold text-slate-900">{portfolioName}</h3>
          <div className={`text-sm font-semibold ${getPercentileColor(alignmentScore)}`}>
            {getPercentileLabel(alignmentScore)} of institutional peers
          </div>
          <div className="text-xs text-slate-500 mt-1">
            Based on {0} key metrics across {MOCK_CONSENSUS_INDICATORS[0]?.sampleSize.toLocaleString()}+ portfolios
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      {showMetrics && (
        <div className="grid grid-cols-2 gap-3 mb-4">
          {MOCK_PEER_BENCHMARKS.slice(0, 4).map((b) => (
            <div key={b.id} className="p-2 rounded-xl bg-white/50 border border-white/40">
              <div className="text-[10px] text-slate-500">{b.metric}</div>
              <div className="flex items-center justify-between mt-1">
                <span className="text-sm font-bold text-slate-900">{b.userValue}{b.unit}</span>
                <span className={`text-[10px] font-bold ${getPercentileColor(b.percentile)}`}>
                  P{b.percentile}
                </span>
              </div>
              {/* Mini bar */}
              <div className="h-1 rounded-full bg-slate-200 overflow-hidden mt-1">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-blue-400 to-purple-400"
                  style={{ width: `${b.percentile}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Top Consensus */}
      {showConsensus && (
        <div className="space-y-2">
          <h4 className="text-xs font-bold text-slate-700 uppercase tracking-widest">Top Peer Trends</h4>
          {topConsensus.map((c) => (
            <div key={c.id} className="flex items-center gap-2 p-2 rounded-lg bg-white/30">
              <div className="flex-1">
                <div className="text-xs font-medium text-slate-900">{c.title}</div>
                <div className="text-[10px] text-slate-500">{c.description.slice(0, 60)}...</div>
              </div>
              <div className="text-right">
                <div className="text-sm font-bold text-slate-900">{c.consensusPercentage}%</div>
                <div className={`text-[10px] font-bold ${c.trend === 'increasing' ? 'text-emerald-600' : 'text-slate-500'}`}>
                  {c.trend === 'increasing' ? '↑' : '→'}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Footer */}
      <div className="mt-4 pt-3 border-t border-white/20 flex items-center justify-between">
        <span className="text-[10px] text-slate-400">
          Updated: {new Date().toLocaleDateString()}
        </span>
        <button className="text-[10px] font-medium text-blue-600 hover:text-blue-700">
          View Full Report →
        </button>
      </div>
    </div>
  );
}
