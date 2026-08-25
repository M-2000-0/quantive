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
    <div className="glass-card p-5 glass-hover group">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-widest text-slate-500">{label}</span>
        {icon && (
          <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-white/60 border border-white/60 text-slate-600 shadow-sm backdrop-blur-md group-hover:bg-white/80 transition-colors">
            {icon}
          </span>
        )}
      </div>
      <div className="mt-3">
        <p className="text-2xl font-bold tracking-tight text-slate-900">{value}</p>
      </div>
      {(change !== undefined || changeLabel) && (
        <div className="mt-2.5 flex items-center gap-1.5">
          {change !== undefined && (
            <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold border border-white/50 bg-white/60 backdrop-blur-md shadow-sm ${color}`}>
              {arrow} {Math.abs(change).toFixed(1)}%
            </span>
          )}
          {changeLabel && (
            <span className="text-xs font-medium text-slate-500">{changeLabel}</span>
          )}
        </div>
      )}
    </div>
  );
}
