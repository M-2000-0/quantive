// ── Peer Alignment Tracker Component ──────────────────────────────────
// Monitors how well the user's portfolio aligns with peer consensus.
// Shows a daily alignment score and drift warnings when diverging.

import { useState, useMemo } from 'react';
import {
  type ConsensusIndicator,
  type PeerBenchmark } from '../lib/peerIntelligence';

interface AlignmentDimension {
  id: string;
  label: string;
  userAlignment: number; // 0-100 (100 = fully aligned with consensus)
  consensusDirection: string;
  peerPercentage: number;
  trend: 'aligned' | 'diverging' | 'contrarian';
  risk: 'low' | 'medium' | 'high';
  insight: string;
}

interface PeerAlignmentTrackerProps {
  /** Current portfolio duration (years) */
  portfolioDuration?: number;
  /** Current FX hedge ratio (0-100%) */
  fxHedgeRatio?: number;
  /** Current HY exposure (0-100%) */
  hyExposure?: number;
  /** Current green bond allocation (0-100%) */
  greenBondPct?: number;
}

function calculateAlignment(
  userValue: number,
  consensusDirection: string,
  peerPercentage: number
): { alignment: number; trend: 'aligned' | 'diverging' | 'contrarian' } {
  // If user matches consensus direction, high alignment
  // If user opposes consensus, low alignment (contrarian)
  const consensusAlignment = peerPercentage;

  if (consensusDirection === 'increase') {
    // User should be increasing — alignment based on whether they are
    const diff = Math.abs(userValue - 50); // 50 = neutral
    const alignment = userValue > 50 ? consensusAlignment : 100 - consensusAlignment;
    const trend = alignment > 70 ? 'aligned' : alignment > 40 ? 'diverging' : 'contrarian';
    return { alignment, trend };
  }

  if (consensusDirection === 'decrease') {
    const alignment = userValue < 50 ? consensusAlignment : 100 - consensusAlignment;
    const trend = alignment > 70 ? 'aligned' : alignment > 40 ? 'diverging' : 'contrarian';
    return { alignment, trend };
  }

  // Neutral — alignment is based on proximity to median
  const alignment = 100 - Math.abs(userValue - 50);
  const trend = alignment > 70 ? 'aligned' : alignment > 40 ? 'diverging' : 'contrarian';
  return { alignment, trend };
}

export default function PeerAlignmentTracker({
  portfolioDuration = 4.8,
  fxHedgeRatio = 75,
  hyExposure = 18,
  greenBondPct = 12 }: PeerAlignmentTrackerProps) {
  const dimensions: AlignmentDimension[] = useMemo(() => {
    const durationConsensus = [].find((c) => c.category === 'duration');
    const hedgeConsensus = [].find((c) => c.category === 'hedging');
    const creditConsensus = [].find((c) => c.category === 'credit');
    const greenConsensus = [].find((c) => c.category === 'allocation');

    const durationBench = [].find((b) => b.metric === 'Average Duration');
    const hedgeBench = [].find((b) => b.metric === 'Floating Rate Exposure');

    return [
      {
        id: 'duration',
        label: 'Duration',
        userAlignment: Math.min(100, Math.max(0, 100 - Math.abs(portfolioDuration - (durationBench?.peerMedian || 5.2)) * 20)),
        consensusDirection: durationConsensus?.trend === 'increasing' ? 'increase' : 'decrease',
        peerPercentage: durationConsensus?.consensusPercentage || 0,
        trend: Math.abs(portfolioDuration - (durationBench?.peerMedian || 5.2)) < 1 ? 'aligned' : 'diverging',
        risk: Math.abs(portfolioDuration - (durationBench?.peerMedian || 5.2)) > 2 ? 'high' : 'low',
        insight: portfolioDuration < (durationBench?.peerMedian || 5.2)
          ? `Your duration is ${((durationBench?.peerMedian || 5.2) - portfolioDuration).toFixed(1)}yr shorter than median peers`
          : `Your duration is ${(portfolioDuration - (durationBench?.peerMedian || 5.2)).toFixed(1)}yr longer than median peers` },
      {
        id: 'hedging',
        label: 'FX Hedging',
        userAlignment: Math.min(100, Math.max(0, 100 - Math.abs(fxHedgeRatio - 80) * 2)),
        consensusDirection: hedgeConsensus?.trend === 'increasing' ? 'increase' : 'maintain',
        peerPercentage: hedgeConsensus?.consensusPercentage || 0,
        trend: fxHedgeRatio >= 70 ? 'aligned' : 'diverging',
        risk: fxHedgeRatio < 50 ? 'medium' : 'low',
        insight: fxHedgeRatio >= 80
          ? 'Well-aligned with peer consensus for increased hedging'
          : `Consider increasing hedge ratio to match the ${hedgeConsensus?.consensusPercentage || 0}% of peers hedging at 80%+` },
      {
        id: 'credit',
        label: 'Credit Exposure',
        userAlignment: Math.min(100, Math.max(0, 100 - Math.abs(hyExposure - 15) * 3)),
        consensusDirection: creditConsensus?.trend === 'increasing' ? 'decrease' : 'maintain',
        peerPercentage: creditConsensus?.consensusPercentage || 0,
        trend: hyExposure <= 25 ? 'aligned' : 'contrarian',
        risk: hyExposure > 40 ? 'high' : 'low',
        insight: hyExposure <= 25
          ? 'Your HY exposure is within peer norms'
          : `Your ${hyExposure}% HY exposure is above the ${creditConsensus?.consensusPercentage || 0}% of peers reducing` },
      {
        id: 'green',
        label: 'Green Bonds',
        userAlignment: Math.min(100, Math.max(0, 100 - Math.abs(greenBondPct - 20) * 3)),
        consensusDirection: greenConsensus?.trend === 'increasing' ? 'increase' : 'maintain',
        peerPercentage: greenConsensus?.consensusPercentage || 0,
        trend: greenBondPct >= 15 ? 'aligned' : 'diverging',
        risk: greenBondPct < 5 ? 'medium' : 'low',
        insight: greenBondPct >= 15
          ? 'Good progress on green bond allocation'
          : `Only ${greenBondPct}% green allocation — ${greenConsensus?.consensusPercentage || 0}% of peers are increasing` },
    ];
  }, [portfolioDuration, fxHedgeRatio, hyExposure, greenBondPct]);

  const overallScore = useMemo(() => {
    return Math.round(dimensions.reduce((sum, d) => sum + d.userAlignment, 0) / dimensions.length);
  }, [dimensions]);

  const alignedCount = dimensions.filter((d) => d.trend === 'aligned').length;
  const divergingCount = dimensions.filter((d) => d.trend === 'diverging').length;
  const contrarianCount = dimensions.filter((d) => d.trend === 'contrarian').length;

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-emerald-600';
    if (score >= 60) return 'text-blue-600';
    if (score >= 40) return 'text-amber-600';
    return 'text-red-600';
  };

  const getScoreBg = (score: number) => {
    if (score >= 80) return 'from-emerald-500 to-teal-500';
    if (score >= 60) return 'from-blue-500 to-indigo-500';
    if (score >= 40) return 'from-amber-500 to-orange-500';
    return 'from-red-500 to-rose-500';
  };

  const getTrendBadge = (trend: AlignmentDimension['trend']) => {
    switch (trend) {
      case 'aligned':
        return <span className="px-1.5 py-0.5 text-[9px] font-bold bg-emerald-50 text-emerald-600 rounded-full">✓ Aligned</span>;
      case 'diverging':
        return <span className="px-1.5 py-0.5 text-[9px] font-bold bg-amber-50 text-amber-600 rounded-full">⚠ Diverging</span>;
      case 'contrarian':
        return <span className="px-1.5 py-0.5 text-[9px] font-bold bg-red-50 text-red-600 rounded-full">✕ Contrarian</span>;
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-bold text-slate-900">Peer Alignment</h3>
          <p className="text-xs text-slate-500">How your portfolio compares to peer consensus</p>
        </div>
        <div className="text-right">
          <div className={`text-3xl font-bold ${getScoreColor(overallScore)}`}>{overallScore}%</div>
          <div className="text-[10px] text-slate-500">Overall Alignment</div>
        </div>
      </div>

      {/* Score Ring */}
      <div className="glass rounded-2xl p-4 flex items-center gap-6">
        <div className="relative w-20 h-20 flex-shrink-0">
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
              stroke={`url(#gradient-${overallScore})`}
              strokeWidth="3"
              strokeDasharray={`${overallScore}, 100`}
              strokeLinecap="round"
              className="transition-all duration-1000"
            />
            <defs>
              <linearGradient id={`gradient-${overallScore}`} x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor={overallScore >= 60 ? '#3b82f6' : '#f59e0b'} />
                <stop offset="100%" stopColor={overallScore >= 60 ? '#8b5cf6' : '#ef4444'} />
              </linearGradient>
            </defs>
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className={`text-lg font-bold ${getScoreColor(overallScore)}`}>{overallScore}</span>
          </div>
        </div>

        <div className="flex-1">
          <div className="flex items-center gap-4 mb-2">
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-emerald-500" />
              <span className="text-xs text-slate-600">{alignedCount} Aligned</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-amber-500" />
              <span className="text-xs text-slate-600">{divergingCount} Diverging</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-red-500" />
              <span className="text-xs text-slate-600">{contrarianCount} Contrarian</span>
            </div>
          </div>
          <p className="text-xs text-slate-500">
            {overallScore >= 80
              ? 'Your portfolio is well-aligned with peer consensus. Minimal drift.'
              : overallScore >= 60
              ? 'Mostly aligned with peers. A few areas to monitor.'
              : overallScore >= 40
              ? 'Some divergence from peer consensus. Review the dimensions below.'
              : 'Significant divergence from peers. This may be intentional or indicate risk.'}
          </p>
        </div>
      </div>

      {/* Dimension Breakdown */}
      <div className="space-y-3">
        {dimensions.map((dim) => (
          <div key={dim.id} className="glass rounded-xl p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-slate-900">{dim.label}</span>
                {getTrendBadge(dim.trend)}
                {dim.risk === 'high' && (
                  <span className="px-1.5 py-0.5 text-[9px] font-bold bg-red-50 text-red-600 rounded-full">High Risk</span>
                )}
              </div>
              <div className="text-right">
                <span className={`text-lg font-bold ${dim.userAlignment >= 70 ? 'text-emerald-600' : dim.userAlignment >= 40 ? 'text-amber-600' : 'text-red-600'}`}>
                  {Math.round(dim.userAlignment)}%
                </span>
                <span className="text-[10px] text-slate-500 ml-1">alignment</span>
              </div>
            </div>

            {/* Alignment bar */}
            <div className="relative h-2 rounded-full bg-slate-200 overflow-hidden mb-2">
              <div
                className={`h-full rounded-full bg-gradient-to-r ${
                  dim.userAlignment >= 70 ? 'from-emerald-400 to-teal-400' :
                  dim.userAlignment >= 40 ? 'from-amber-400 to-orange-400' :
                  'from-red-400 to-rose-400'
                }`}
                style={{ width: `${dim.userAlignment}%` }}
              />
              {/* Consensus marker */}
              <div
                className="absolute top-0 w-0.5 h-full bg-slate-600"
                style={{ left: `${dim.peerPercentage}%` }}
              />
            </div>

            <p className="text-xs text-slate-600">{dim.insight}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
