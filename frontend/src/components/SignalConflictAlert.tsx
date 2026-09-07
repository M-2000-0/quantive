import { useState, useEffect } from 'react';
import { api } from '../api';

interface SignalConflict {
  indicator_a: string;
  signal_a: string;
  indicator_b: string;
  signal_b: string;
  severity: string;
  description: string;
  recommendation: string;
}

interface ConflictData {
  has_conflict: boolean;
  conflict_count: number;
  conflicts: SignalConflict[];
  agreement_score: number;
  bullish_count: number;
  bearish_count: number;
  neutral_count: number;
  recommendation: string;
}

export function SignalConflictAlert({ symbol }: { symbol: string }) {
  const [data, setData] = useState<ConflictData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const result = await api.request<ConflictData>(`/ai/signal-conflicts/${symbol}`);
        setData(result);
      } catch (e) {
        console.error('Failed to load signal conflicts', e);
      }
      setLoading(false);
    };
    load();
  }, [symbol]);

  if (loading) return <div className="text-gray-400 text-xs">Analyzing signals...</div>;
  if (!data || !data.has_conflict) return null;

  const scoreColor = data.agreement_score > 70 ? 'text-green-400' :
                     data.agreement_score > 40 ? 'text-yellow-400' : 'text-red-400';

  return (
    <div className="p-3 bg-yellow-500/5 rounded-lg border border-yellow-500/20 space-y-2">
      <div className="flex items-center gap-2">
        <span className="text-yellow-400 text-sm">!</span>
        <span className="text-xs font-medium text-yellow-400">
          {data.conflict_count} Signal Conflict{data.conflict_count > 1 ? 's' : ''} Detected
        </span>
        <span className={`text-[10px] ${scoreColor}`}>
          Agreement: {data.agreement_score}%
        </span>
      </div>

      <div className="space-y-1.5">
        {data.conflicts.map((c, i) => (
          <div key={i} className="text-[11px] text-gray-400">
            <span className="text-gray-300">{c.indicator_a}</span> ({c.signal_a}) vs{' '}
            <span className="text-gray-300">{c.indicator_b}</span> ({c.signal_b})
            <span className="text-gray-600 ml-1">— {c.severity}</span>
          </div>
        ))}
      </div>

      <p className="text-[11px] text-gray-500 italic">{data.recommendation}</p>

      <div className="flex gap-3 text-[10px] text-gray-600">
        <span>{data.bullish_count} bullish</span>
        <span>{data.bearish_count} bearish</span>
        <span>{data.neutral_count} neutral</span>
      </div>
    </div>
  );
}
