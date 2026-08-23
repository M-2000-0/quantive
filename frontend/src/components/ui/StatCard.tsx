import type { ReactNode } from 'react';

type Trend = 'up' | 'down' | 'neutral';

interface StatCardProps {
  label: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  icon?: ReactNode;
  trend?: Trend;
}

const trendConfig: Record<Trend, { color: string; arrow: string }> = {
  up: { color: 'text-emerald-600', arrow: '\u2191' },
  down: { color: 'text-red-600', arrow: '\u2193' },
  neutral: { color: 'text-slate-500', arrow: '\u2192' },
};

export default function StatCard({
  label,
  value,
  change,
  changeLabel,
  icon,
  trend = 'neutral',
}: StatCardProps) {
  const { color, arrow } = trendConfig[trend];

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-slate-500">{label}</span>
        {icon && (
          <span className="text-slate-400">{icon}</span>
        )}
      </div>
      <div className="mt-2">
        <p className="text-2xl font-bold text-slate-900 tracking-tight">{value}</p>
      </div>
      {(change !== undefined || changeLabel) && (
        <div className="mt-2 flex items-center gap-1.5">
          {change !== undefined && (
            <span className={`text-sm font-medium ${color}`}>
              {arrow} {Math.abs(change).toFixed(1)}%
            </span>
          )}
          {changeLabel && (
            <span className="text-xs text-slate-400">{changeLabel}</span>
          )}
        </div>
      )}
    </div>
  );
}
