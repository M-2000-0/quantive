import React from 'react';
import { TriangleAlert as AlertTriangle } from 'lucide-react';

interface InactionImpact {
  metric: string;
  currentValue: string;
  projectedValue: string;
  timeframe: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  description: string;
}

const IMPACTS: InactionImpact[] = [
  { metric: 'Additional Financing Costs', currentValue: '$0', projectedValue: '+$2.3B', timeframe: '5 years', severity: 'critical', description: 'Higher rates on new issuances due to deteriorating credit profile' },
  { metric: 'Liquidity Pressure', currentValue: '14.2%', projectedValue: '+17%', timeframe: '12 months', severity: 'critical', description: 'Liquidity buffer falls below 10% minimum threshold' },
  { metric: 'Refinancing Cliff', currentValue: 'Manageable', projectedValue: '$3.2B due 2029', timeframe: '3 years', severity: 'high', description: 'Concentration of maturities creates acute refinancing risk' },
  { metric: 'Rating Downgrade Probability', currentValue: '12%', projectedValue: '+24%', timeframe: '18 months', severity: 'high', description: 'Inaction increases likelihood of sovereign downgrade' },
  { metric: 'FX Exposure Risk', currentValue: '41%', projectedValue: '+48%', timeframe: '6 months', severity: 'medium', description: 'Currency depreciation increases local-currency debt burden' },
  { metric: 'Investor Confidence', currentValue: 'Stable', projectedValue: 'Deteriorating', timeframe: '12 months', severity: 'medium', description: 'Reduced demand at future auctions due to perceived complacency' },
];

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'bg-red-500/20 text-red-400 border-red-500/30',
  high: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  low: 'bg-green-500/20 text-green-400 border-green-500/30' };

export default function CostOfInaction() {
  const criticalCount = IMPACTS.filter(i => i.severity === 'critical').length;
  const highCount = IMPACTS.filter(i => i.severity === 'high').length;

  return (
    <div className="glass rounded-2xl p-6 border-l-4 border-red-500">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <AlertTriangle className="w-5 h-5" />
          <div>
            <h3 className="text-lg font-bold text-white">Cost of Doing Nothing</h3>
            <p className="text-sm text-slate-400">What happens if no action is taken</p>
          </div>
        </div>
        <div className="flex gap-2">
          <span className="px-3 py-1 bg-red-500/20 text-red-400 rounded-lg text-xs font-medium">
            {criticalCount} Critical
          </span>
          <span className="px-3 py-1 bg-orange-500/20 text-orange-400 rounded-lg text-xs font-medium">
            {highCount} High
          </span>
        </div>
      </div>

      <div className="space-y-3">
        {IMPACTS.map((impact, i) => (
          <div key={i} className={`p-4 rounded-xl border ${SEVERITY_COLORS[impact.severity]}`}>
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <h4 className="text-white font-medium">{impact.metric}</h4>
                  <span className="px-2 py-0.5 bg-white/10 rounded text-xs text-slate-400">
                    {impact.timeframe}
                  </span>
                </div>
                <p className="text-xs text-slate-400 mb-2">{impact.description}</p>
                <div className="flex items-center gap-3">
                  <span className="text-sm text-slate-400">Now: {impact.currentValue}</span>
                  <span className="text-slate-500">→</span>
                  <span className="text-sm font-bold text-white">{impact.projectedValue}</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 p-4 bg-red-500/10 border border-red-500/20 rounded-xl">
        <p className="text-sm text-red-300">
          🚨 <strong>Urgent:</strong> Without intervention, the sovereign faces a compounding fiscal deterioration. The combined cost of inaction over 5 years exceeds <strong>$4.8B</strong> in additional financing costs and risk exposure.
        </p>
      </div>
    </div>
  );
}
