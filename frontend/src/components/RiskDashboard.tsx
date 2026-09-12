import React, { useState, useEffect, useCallback } from 'react';
import Card from './ui/Card';
import Badge from './ui/Badge';
import Button from './ui/Button';
import StatsCard from './ui/StatCard';
import { api } from '../api';
import { RiskCategory, RiskSeverity, TrendDirection } from '../types';

interface RiskCategoryPanel {
  id: RiskCategory;
  title: string;
  icon: string;
  color: string;
  summaryEndpoint?: string;
}

const CATEGORY_PANELS: RiskCategoryPanel[] = [
  { id: RiskCategory.CYBER, title: 'Cyber Risk', icon: 'Shield', color: 'cyan' },
  { id: RiskCategory.FISCAL, title: 'Fiscal Risk', icon: 'DollarSign', color: 'red' },
  { id: RiskCategory.CLIMATE, title: 'Climate Risk', icon: 'Sun', color: 'orange' },
  { id: RiskCategory.INFRASTRUCTURE, title: 'Infrastructure', icon: 'Building', color: 'amber' },
  { id: RiskCategory.GEOPOLITICAL, title: 'Geopolitical', icon: 'Globe', color: 'purple' },
  { id: RiskCategory.SUPPLY_CHAIN, title: 'Supply Chain', icon: 'Package', color: 'green' },
];

interface RiskSummaryData {
  overall: number;
  by_category: Record<RiskCategory, number>;
  category_counts: Record<RiskCategory, number>;
  entity_id: string;
  entity_type: string;
  trending?: string;
}

interface EarlyWarningSignal {
  id: string;
  name: string;
  category: string;
  indicator: string;
  currentValue: number;
  threshold: number;
  unit: string;
  direction: string;
  status: string;
  trend: string;
  description: string;
  lastUpdated: string;
}

export default function RiskDashboard() {
  const [panels, setPanels] = useState<RiskSummaryData[]>([]);
  const [signals, setSignals] = useState<EarlyWarningSignal[]>([]);
  const [loading, setLoading] = useState(true);
  const [entityId, setEntityId] = useState<string>('');

  const fetchRiskSummaries = useCallback(async () => {
    if (!entityId) return;
    setLoading(true);
    try {
      const results = await Promise.all([
        api.risk.cyberSummary(entityId),
        api.risk.fiscalSummary(entityId),
        api.risk.climateSummary(entityId),
        api.risk.infrastructureSummary(entityId),
        api.risk.geopoliticalSummary(entityId),
        api.risk.supplyChainSummary(entityId),
      ]);
      const data: RiskSummaryData[] = results.map((r) => ({
        overall: r.overall || 0,
        by_category: r.by_category || {},
        category_counts: r.category_counts || {},
        entity_id: entityId,
        entity_type: 'government' }));
      setPanels(data);
    } catch (err) {
      console.error('Failed to fetch risk summaries:', err);
    } finally {
      setLoading(false);
    }
  }, [entityId]);

  const fetchEarlyWarning = useCallback(async () => {
    if (!entityId) return;
    setLoading(true);
    try {
      const result = await api.risk.earlyWarning(entityId);
      const severityOrder: Record<string, number> = {
        critical: 0,
        high: 1,
        medium: 2,
        normal: 3 };
      const sorted = result.signals
        .sort((a: EarlyWarningSignal, b: EarlyWarningSignal) => {
          return severityOrder[a.status] - severityOrder[b.status];
        });
      setSignals(sorted);
    } catch (err) {
      console.error('Failed to fetch early warning signals:', err);
    } finally {
      setLoading(false);
    }
  }, [entityId]);

  return (
    <div className="space-y-6">
      {/* Entity selector */}
      <div className="flex items-center gap-3">
        <input
          type="text"
          placeholder="Enter entity ID (e.g., government-12345)"
          value={entityId}
          onChange={(e) => setEntityId(e.target.value)}
          className="glass px-4 py-2 rounded-xl text-white border border-slate-600 focus:outline-none focus:border-cyan-500"
        />
        <button
          onClick={() => {
            if (entityId) {
              fetchRiskSummaries();
              fetchEarlyWarning();
            }
          }}
          className="px-4 py-2 bg-cyan-600 text-white rounded-xl hover:bg-cyan-500 transition-colors disabled:opacity-50"
        >
          Load Risk Assessment
        </button>
      </div>

      {/* Risk Panels */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {panels.map((panel) => {
          const cat = panel.by_category
            ? Object.keys(panel.by_category).find(
                (k) => CATEGORY_PANELS.some((p) => p.id === k)
              )
            : null;
          const catPanel = CATEGORY_PANELS.find((p) => p.id === cat);
          if (!catPanel) return null;

          const overall = panel.overall;
          const severity =
            overall >= 90
              ? 'critical'
              : overall >= 75
                ? 'high'
                : overall >= 50
                  ? 'medium'
                  : 'low';

          return (
            <Card key={catPanel.id} className="glass">
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{catPanel.icon}</span>
                    <h3 className="text-lg font-bold text-white">{catPanel.title}</h3>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${getSeverityBadgeClass(severity)}`}>
                      {severity.toUpperCase()}
                    </span>
                  </div>
                </div>

                <div className="space-y-3">
                  {/* Overall Score */}
                  <div>
                    <p className="text-3xl font-bold text-white">{Math.round(overall)}</p>
                    <p className="text-sm text-slate-400">Composite Risk Score</p>
                  </div>

                  {/* Category breakdown */}
                  {catPanel.id !== 'supply_chain' && (
                    <div>
                      <p className="text-xs text-slate-400 mb-1">Category Scores</p>
                      <div className="grid grid-cols-2 gap-2">
                        {Object.entries(panel.by_category || {}).map(([key, value]) => {
                          const score = Math.round(value);
                          const catName =
                            key === 'fiscal'
                              ? 'Fiscal'
                              : key === 'cyber'
                                ? 'Cyber'
                                : key === 'climate'
                                  ? 'Climate'
                                  : key === 'infrastructure'
                                    ? 'Infra'
                                    : key === 'geopolitical'
                                      ? 'Geo'
                                      : 'SC';
                          const catColor =
                            key === 'fiscal'
                              ? 'red'
                              : key === 'cyber'
                                ? 'cyan'
                                : key === 'climate'
                                  ? 'orange'
                                  : key === 'infrastructure'
                                    ? 'amber'
                                    : key === 'geopolitical'
                                      ? 'purple'
                                      : 'green';
                          return (
                            <div key={key} className="flex items-center justify-between">
                              <span className="text-sm text-slate-300">{catName}</span>
                              <div>
                                <span className={`w-8 h-8 rounded-full ${catColor}-500`} />
                                <span className="text-xs font-medium text-white">{score}</span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Trend indicator */}
                  <div className="flex items-center justify-between">
                    <p className="text-xs text-slate-400">Trend: {panel.trending || 'stable'}</p>
                    <div className="flex items-center gap-1">
                      {panel.trending === 'improving' && (
                        <span className="text-green-400">📈</span>
                      )}
                      {panel.trending === 'stable' && (
                        <span className="text-yellow-400">➡️</span>
                      )}
                      {panel.trending === 'deteriorating' && (
                        <span className="text-red-400">📉</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          );
        })}
      </div>

      {/* Early Warning Signals */}
      <div>
        {signals.length > 0 && (
          <Card className="glass p-6">
            <h3 className="text-xl font-bold text-white mb-4">Early Warning Signals</h3>
            <div className="grid grid-cols-2 gap-3">
              {signals.map((signal) => {
                const statusColor =
                  signal.status === 'critical'
                    ? 'bg-red-500/20 text-red-400'
                    : signal.status === 'warning'
                      ? 'bg-orange-500/20 text-orange-400'
                      : signal.status === 'watch'
                        ? 'bg-yellow-500/20 text-yellow-400'
                        : 'bg-green-500/20 text-green-400';

                return (
                  <div
                    key={signal.id}
                    className={`glass rounded-xl p-4 transition-all hover:bg-white/5 ${isDangerZone(signal)}`}
                  >
                    <div className="flex items-start gap-3">
                      <span className="text-lg">{getCategoryIcon(signal.category)}</span>
                      <div>
                        <h4 className="text-white font-medium">{signal.name}</h4>
                        <p className="text-xs text-slate-400">{signal.indicator}</p>
                      </div>
                    </div>
                    <div className="mt-3 pt-3 border-t border-white/20">
                      <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${statusColor}`} />
                        <span className="text-sm text-slate-300">{signal.status.toUpperCase()}</span>
                      </div>
                      <p className="text-xs text-slate-500">Threshold: {signal.threshold}{signal.unit}</p>
                      <p className="text-xs text-slate-500">Trend: {signal.trend}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}

function getSeverityBadgeClass(severity: string) {
  return {
    critical: 'bg-red-500/20 text-red-400',
    high: 'bg-orange-500/20 text-orange-400',
    medium: 'bg-amber-500/20 text-amber-400',
    low: 'bg-green-500/20 text-green-400' }[severity];
}

function isDangerZone(signal: EarlyWarningSignal) {
  return signal.status === 'critical' || signal.status === 'warning'
    ? 'border-l-4 border-red-500'
    : '';
}

function getCategoryIcon(category: string) {
  const icons: Record<string, string> = {
    cyber: 'Shield',
    fiscal: 'DollarSign',
    climate: 'Sun',
    infrastructure: 'Building',
    geopolitical: 'Globe',
    supply_chain: 'Package' };
  return icons[category] || 'HelpCircle';
}