// ── Consensus Alert Component ──────────────────────────────────────────
// Shows live alerts when peer consensus trends cross significant thresholds.
// Displays pulse animations for critical shifts and action CTAs.

import { useState, useEffect } from 'react';
import {
  getCategoryIcon,
  type ConsensusIndicator } from '../lib/peerIntelligence';

interface ConsensusAlertProps {
  /** Threshold to trigger alerts (default: 60%) */
  threshold?: number;
  /** Maximum alerts to show (default: 3) */
  maxAlerts?: number;
  /** Whether alerts are enabled */
  enabled?: boolean;
}

interface AlertState {
  indicator: ConsensusIndicator;
  previousPercentage: number;
  crossedThreshold: boolean;
  timestamp: number;
}

const THRESHOLD_LABELS: Record<number, string> = {
  50: 'Majority',
  60: 'Strong Majority',
  70: 'Overwhelming',
  75: 'Supermajority',
  80: 'Near-Consensus',
  90: 'Consensus' };

function getThresholdLabel(percentage: number): string {
  if (percentage >= 90) return 'Consensus';
  if (percentage >= 80) return 'Near-Consensus';
  if (percentage >= 75) return 'Supermajority';
  if (percentage >= 70) return 'Overwhelming';
  if (percentage >= 60) return 'Strong Majority';
  if (percentage >= 50) return 'Majority';
  return 'Plurality';
}

export default function ConsensusAlert({
  threshold = 60,
  maxAlerts = 3,
  enabled = true }: ConsensusAlertProps) {
  const [alerts, setAlerts] = useState<AlertState[]>([]);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!enabled) return;

    // Check for consensus indicators above threshold
    const triggered = []
      .filter((ind) => ind.consensusPercentage >= threshold && !dismissed.has(ind.id))
      .sort((a, b) => b.consensusPercentage - a.consensusPercentage)
      .slice(0, maxAlerts)
      .map((ind) => ({
        indicator: ind,
        previousPercentage: ind.consensusPercentage - ind.trendDelta,
        crossedThreshold: ind.consensusPercentage >= threshold && (ind.consensusPercentage - ind.trendDelta) < threshold,
        timestamp: Date.now() }));

    setAlerts(triggered);
  }, [threshold, maxAlerts, enabled, dismissed]);

  const handleDismiss = (id: string) => {
    setDismissed((prev) => new Set(prev).add(id));
  };

  if (!enabled || alerts.length === 0) return null;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 mb-2">
        <span className="relative flex h-2.5 w-2.5">
          <span className="absolute inline-flex h-full w-full rounded-full bg-amber-400 animate-ping opacity-60" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-amber-500" />
        </span>
        <h3 className="text-sm font-bold text-slate-900">Peer Consensus Alerts</h3>
        <span className="text-[10px] text-slate-500">• {alerts.length} active</span>
      </div>

      {alerts.map((alert) => {
        const { indicator, previousPercentage, crossedThreshold } = alert;
        const isNewCrossing = crossedThreshold && previousPercentage < threshold;

        return (
          <div
            key={indicator.id}
            className={`glass rounded-xl p-4 transition-all ${
              isNewCrossing
                ? 'ring-2 ring-amber-400/50 shadow-lg shadow-amber-400/10 animate-glass-in'
                : 'hover:shadow-md'
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-3">
                <div className={`text-lg ${isNewCrossing ? 'animate-bounce' : ''}`}>
                  {getCategoryIcon(indicator.category)}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h4 className="text-sm font-semibold text-slate-900">{indicator.title}</h4>
                    {isNewCrossing && (
                      <span className="px-1.5 py-0.5 text-[9px] font-bold uppercase bg-amber-100 text-amber-700 rounded-full animate-pulse">
                        NEW
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-600 mt-0.5">{indicator.description}</p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <div className="text-right">
                  <div className="text-xl font-bold text-slate-900">{indicator.consensusPercentage}%</div>
                  <div className={`text-[10px] font-bold ${indicator.trend === 'increasing' ? 'text-emerald-600' : indicator.trend === 'decreasing' ? 'text-red-600' : 'text-slate-500'}`}>
                    {indicator.trend === 'increasing' ? '↑' : indicator.trend === 'decreasing' ? '↓' : '→'}
                    {indicator.trendDelta > 0 ? '+' : ''}{indicator.trendDelta}%
                  </div>
                </div>
                <button
                  onClick={() => handleDismiss(indicator.id)}
                  className="text-slate-400 hover:text-slate-600 text-xs"
                >
                  ✕
                </button>
              </div>
            </div>

            {/* Threshold indicator */}
            <div className="mt-3 flex items-center gap-2">
              <div className="flex-1 h-1.5 rounded-full bg-slate-200 overflow-hidden">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-amber-400 to-amber-500"
                  style={{ width: `${indicator.consensusPercentage}%` }}
                />
              </div>
              <span className="text-[10px] font-bold text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full">
                {getThresholdLabel(indicator.consensusPercentage)}
              </span>
            </div>

            {/* Context */}
            <div className="mt-2 flex items-center justify-between text-[10px] text-slate-500">
              <span>{indicator.sampleSize.toLocaleString()} portfolios • {indicator.confidence}% confidence</span>
              {indicator.actionable && (
                <span className="text-blue-600 font-medium cursor-pointer hover:underline">
                  View Recommendation →
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
