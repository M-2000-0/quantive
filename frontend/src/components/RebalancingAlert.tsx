// ── Rebalancing Alert Component ─────────────────────────────────────
// Detects when portfolio allocation drifts more than 5% from target
// and suggests specific trades to rebalance back to target.

import { useState, useMemo } from 'react';
import {
  calculateDrift,
  generateRebalanceTrades,
  hasSignificantDrift,
  getDriftSeverity,
  type RiskProfile,
  type AssetAllocation,
  type RebalanceTrade } from '../lib/allocationTarget';

interface RebalancingAlertProps {
  /** Current allocation percentages keyed by asset class name */
  currentAllocation: Record<string, number>;
  /** User's risk profile */
  targetProfile: RiskProfile;
  /** Total portfolio value in USD */
  totalPortfolioValue: number;
  /** Callback when user clicks "Apply Rebalancing" */
  onApplyRebalance?: (trades: RebalanceTrade[]) => void;
}

export default function RebalancingAlert({
  currentAllocation,
  targetProfile,
  totalPortfolioValue,
  onApplyRebalance }: RebalancingAlertProps) {
  const [expanded, setExpanded] = useState(false);
  const [showTrades, setShowTrades] = useState(false);

  const allocations = useMemo(
    () => calculateDrift(currentAllocation, targetProfile),
    [currentAllocation, targetProfile],
  );

  const hasDrift = hasSignificantDrift(allocations);
  const severity = getDriftSeverity(allocations);
  const trades = useMemo(
    () => generateRebalanceTrades(allocations, totalPortfolioValue),
    [allocations, totalPortfolioValue],
  );

  const maxDrift = Math.max(...allocations.map((a) => Math.abs(a.drift)));
  const overweightAssets = allocations.filter((a) => a.drift > 2);
  const underweightAssets = allocations.filter((a) => a.drift < -2);

  if (!hasDrift && severity === 'none') return null;

  const severityConfig = {
    none: { bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-800', icon: 'CheckCircle', label: 'On Track' },
    minor: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-800', icon: '🔵', label: 'Minor Drift' },
    moderate: { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-800', icon: '🟡', label: 'Moderate Drift' },
    significant: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-800', icon: '🔴', label: 'Rebalance Now' } };

  const config = severityConfig[severity];

  const statusColor = (drift: number) => {
    const abs = Math.abs(drift);
    if (abs < 2) return 'text-slate-500';
    if (abs < 5) return 'text-amber-600';
    if (abs < 10) return 'text-orange-600';
    return 'text-red-600';
  };

  return (
    <div className={`rounded-2xl border ${config.bg} ${config.border} overflow-hidden animate-glass-in`}>
      {/* Alert Header */}
      <div
        className="p-4 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-xl">{config.icon}</span>
            <div>
              <div className={`text-sm font-bold ${config.text}`}>
                {config.label} — {targetProfile.charAt(0).toUpperCase() + targetProfile.slice(1)} Profile
              </div>
              <div className="text-xs text-slate-500 mt-0.5">
                {severity === 'none'
                  ? 'All asset classes within 5% of target'
                  : `Max drift: ${maxDrift.toFixed(1)}% — ${trades.length} trade${trades.length !== 1 ? 's' : ''} suggested`}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {trades.length > 0 && (
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-white/60 text-slate-600">
                {trades.length} trades
              </span>
            )}
            <svg
              className={`w-4 h-4 text-slate-400 transition-transform ${expanded ? 'rotate-180' : ''}`}
              fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
            </svg>
          </div>
        </div>
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div className="px-4 pb-4 space-y-4 border-t border-white/20 pt-4">
          {/* Allocation Drift Chart */}
          <div>
            <div className="text-xs font-bold text-slate-500 mb-2">Asset Class Drift</div>
            <div className="space-y-2">
              {allocations.map((alloc) => (
                <div key={alloc.assetClass} className="flex items-center gap-3">
                  <span className="text-xs font-medium text-slate-700 w-32 truncate">
                    {alloc.assetClass}
                  </span>
                  <div className="flex-1 relative h-6 bg-white/40 rounded-lg overflow-hidden">
                    {/* Target zone */}
                    <div
                      className="absolute top-0 bottom-0 bg-slate-200/50 rounded-lg"
                      style={{
                        left: `${Math.max(0, alloc.targetPct - 2)}%`,
                        width: '4%' }}
                    />
                    {/* Current bar */}
                    <div
                      className={`absolute top-0 bottom-0 rounded-lg transition-all ${
                        Math.abs(alloc.drift) < 2 ? 'bg-emerald-400' :
                        Math.abs(alloc.drift) < 5 ? 'bg-amber-400' :
                        Math.abs(alloc.drift) < 10 ? 'bg-orange-400' : 'bg-red-400'
                      }`}
                      style={{ width: `${alloc.currentPct}%` }}
                    />
                    {/* Target marker */}
                    <div
                      className="absolute top-0 bottom-0 w-0.5 bg-slate-800"
                      style={{ left: `${alloc.targetPct}%` }}
                    />
                  </div>
                  <div className="text-right w-20">
                    <span className="text-xs font-bold text-slate-900">{alloc.currentPct.toFixed(1)}%</span>
                    <span className={`text-[10px] font-medium ml-1 ${statusColor(alloc.drift)}`}>
                      {alloc.drift > 0 ? `+${alloc.drift.toFixed(1)}` : alloc.drift.toFixed(1)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
            <div className="flex items-center gap-4 mt-2 text-[10px] text-slate-400">
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-emerald-400" /> On target</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-amber-400" /> Minor drift</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-red-400" /> Significant drift</span>
              <span className="flex items-center gap-1"><span className="w-0.5 h-2 bg-slate-800" /> Target</span>
            </div>
          </div>

          {/* Summary */}
          <div className="grid grid-cols-2 gap-3">
            {overweightAssets.length > 0 && (
              <div className="p-3 rounded-xl bg-orange-50/50 border border-orange-200/50">
                <div className="text-[10px] font-bold text-orange-700 mb-1">Overweight</div>
                {overweightAssets.map((a) => (
                  <div key={a.assetClass} className="text-xs text-orange-900">
                    {a.assetClass}: +{a.drift.toFixed(1)}%
                  </div>
                ))}
              </div>
            )}
            {underweightAssets.length > 0 && (
              <div className="p-3 rounded-xl bg-blue-50/50 border border-blue-200/50">
                <div className="text-[10px] font-bold text-blue-700 mb-1">Underweight</div>
                {underweightAssets.map((a) => (
                  <div key={a.assetClass} className="text-xs text-blue-900">
                    {a.assetClass}: {a.drift.toFixed(1)}%
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Suggested Trades */}
          {trades.length > 0 && (
            <div>
              <button
                onClick={() => setShowTrades(!showTrades)}
                className="text-xs font-bold text-blue-600 hover:text-blue-700 transition-colors mb-2"
              >
                {showTrades ? 'Hide' : 'Show'} Suggested Trades ({trades.length}) →
              </button>

              {showTrades && (
                <div className="space-y-2">
                  {trades.map((trade, idx) => (
                    <div
                      key={idx}
                      className="flex items-center gap-3 p-3 rounded-xl bg-white/50 border border-white/40"
                    >
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold ${
                        trade.action === 'buy'
                          ? 'bg-emerald-100 text-emerald-700'
                          : 'bg-red-100 text-red-700'
                      }`}>
                        {trade.action === 'buy' ? '↑' : '↓'}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-medium text-slate-900">
                          {trade.action === 'buy' ? 'Buy' : 'Sell'} {trade.assetClass}
                        </div>
                        <div className="text-[10px] text-slate-500">{trade.rationale}</div>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-bold text-slate-900">
                          ${(trade.amount / 1e6).toFixed(1)}M
                        </div>
                        <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                          trade.priority === 'high' ? 'bg-red-100 text-red-700' :
                          trade.priority === 'medium' ? 'bg-amber-100 text-amber-700' :
                          'bg-slate-100 text-slate-600'
                        }`}>
                          {trade.priority.toUpperCase()}
                        </span>
                      </div>
                    </div>
                  ))}

                  {/* Apply Button */}
                  <button
                    onClick={() => onApplyRebalance?.(trades)}
                    className="w-full px-4 py-2.5 text-sm font-semibold rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-md hover:shadow-lg transition-all"
                  >
                    Apply Rebalancing ({trades.length} trades) →
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
