import { useState } from 'react';
import { Card } from './ui';
import { Badge } from './ui';

interface ComparisonItem {
  id: string;
  name: string;
  metrics: Record<string, { value: number; unit: string; format?: 'number' | 'percent' | 'currency' | 'years' }>;
}

interface ComparisonViewProps {
  items: ComparisonItem[];
  metrics: Array<{ key: string; label: string; higher?: 'better' | 'worse' }>;
  title?: string;
}

function formatMetric(value: number, format?: string, unit?: string): string {
  switch (format) {
    case 'percent': return `${(value * 100).toFixed(2)}%`;
    case 'currency': return `$${value.toLocaleString()}`;
    case 'years': return `${value.toFixed(1)} yrs`;
    default: return `${value}${unit || ''}`;
  }
}

export default function ComparisonView({ items, metrics, title = 'Comparison' }: ComparisonViewProps) {
  const [highlightBest, setHighlightBest] = useState(true);

  const getBestForMetric = (key: string, higher?: 'better' | 'worse') => {
    const values = items.map((item) => item.metrics[key]?.value ?? 0);
    if (higher === 'better') return Math.max(...values);
    if (higher === 'worse') return Math.min(...values);
    return null;
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white/80">{title}</h3>
        <label className="flex items-center gap-2 text-xs text-white/50 cursor-pointer">
          <input type="checkbox" checked={highlightBest} onChange={() => setHighlightBest(!highlightBest)} className="accent-blue-500" />
          Highlight best
        </label>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/10">
              <th className="p-3 text-left text-xs font-semibold text-white/50 uppercase">Metric</th>
              {items.map((item) => (
                <th key={item.id} className="p-3 text-center">
                  <Badge variant="info">{item.name}</Badge>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {metrics.map((m) => {
              const bestVal = getBestForMetric(m.key, m.higher);
              return (
                <tr key={m.key} className="border-b border-white/5 hover:bg-white/[0.02]">
                  <td className="p-3 text-sm text-white/70">{m.label}</td>
                  {items.map((item) => {
                    const metricData = item.metrics[m.key];
                    const val = metricData?.value ?? 0;
                    const isBest = highlightBest && bestVal !== null && val === bestVal;
                    return (
                      <td key={item.id} className={`p-3 text-center text-sm font-medium ${isBest ? 'text-green-400' : 'text-white/80'}`}>
                        {formatMetric(val, metricData?.format, metricData?.unit)}
                        {isBest && <span className="ml-1 text-[10px]">★</span>}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
