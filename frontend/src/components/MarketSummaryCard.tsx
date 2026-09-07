import { useState, useEffect } from 'react';
import { api } from '../api';

interface MarketSection {
  title: string;
  content: string;
  severity: string;
}

interface MarketSignal {
  type: string;
  direction: string;
  spread_bps?: number;
}

interface MarketSummaryData {
  headline: string;
  sections: MarketSection[];
  signals: MarketSignal[];
  outlook: string;
  summary_text: string;
}

const SEVERITY_COLORS: Record<string, string> = {
  positive: 'text-green-400 bg-green-500/10 border-green-500/20',
  warning: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20',
  negative: 'text-red-400 bg-red-500/10 border-red-500/20',
  neutral: 'text-gray-400 bg-white/5 border-white/10',
  info: 'text-blue-400 bg-blue-500/10 border-blue-500/20' };

const OUTLOOK_LABELS: Record<string, { label: string; color: string }> = {
  positive: { label: 'Constructive', color: 'text-green-400' },
  negative: { label: 'Cautious', color: 'text-red-400' },
  neutral: { label: 'Mixed', color: 'text-yellow-400' } };

export function MarketSummaryCard() {
  const [data, setData] = useState<MarketSummaryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [useLLM, setUseLLM] = useState(false);

  useEffect(() => {
    loadSummary();
  }, [useLLM]);

  const loadSummary = async () => {
    setLoading(true);
    try {
      const result = await api.request<MarketSummaryData>(`/ai/market-summary?use_llm=${useLLM}`);
      setData(result);
    } catch (e) {
      console.error('Failed to load market summary', e);
    }
    setLoading(false);
  };

  if (loading) return (
    <div className="p-4 bg-white/[0.03] rounded-xl border border-white/5">
      <div className="text-gray-400 text-sm">Generating market summary...</div>
    </div>
  );

  if (!data) return null;

  const outlook = OUTLOOK_LABELS[data.outlook] || OUTLOOK_LABELS.neutral;

  return (
    <div className="p-4 bg-white/[0.03] rounded-xl border border-white/5 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-white">AI Market Summary</h3>
        <div className="flex items-center gap-2">
          <span className={`text-xs font-medium ${outlook.color}`}>{outlook.label}</span>
          <button
            onClick={() => setUseLLM(!useLLM)}
            className={`px-2 py-1 rounded text-[10px] transition-colors ${
              useLLM ? 'bg-indigo-600 text-white' : 'bg-white/5 text-gray-400 hover:text-white'
            }`}
          >
            {useLLM ? 'LLM' : 'Rule-based'}
          </button>
        </div>
      </div>

      <p className="text-sm text-gray-300">{data.headline}</p>

      {data.sections.length > 0 && (
        <div className="space-y-2">
          {data.sections.map((section, i) => (
            <div key={i} className={`p-3 rounded-lg border text-xs ${SEVERITY_COLORS[section.severity] || SEVERITY_COLORS.info}`}>
              <span className="font-medium">{section.title}:</span> {section.content}
            </div>
          ))}
        </div>
      )}

      {data.signals.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {data.signals.map((signal, i) => (
            <span key={i} className="px-2 py-1 bg-white/5 rounded-full text-[10px] text-gray-400">
              {signal.type.replace(/_/g, ' ')}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
