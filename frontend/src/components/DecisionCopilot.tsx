import React, { useState } from 'react';

interface ReasoningResult {
  question: string;
  answer: string;
  confidence: number;
  sources: string[];
  followUp: string[];
}

const MOCK_REASONS: Record<string, ReasoningResult> = {
  'why': {
    question: 'Why was this allocation chosen?',
    answer: 'The solver selected this allocation because it dominates the efficient frontier for your risk-adjusted return objective. The binding constraint was FX exposure (USD capped at 35%), which forced 12% into local-currency instruments. The maturity profile was optimized to avoid the 2027 refinancing cliff, which would have increased rollover risk by 2.3x.',
    confidence: 94,
    sources: ['Optimization #847', 'Constraint: FX ≤ 35%', 'Maturity structure analysis'],
    followUp: ['Show binding constraints', 'Compare with alternative allocations', 'What if FX constraint relaxed?']
  },
  'explain': {
    question: 'Explain this result to a Minister of Finance',
    answer: 'Minister, this strategy saves $14.2M annually in debt servicing costs while reducing refinancing risk by 18%. The trade-off is a modest increase in floating-rate exposure (from 22% to 28%), which we mitigate with interest rate swaps. In plain terms: we lock in lower rates today, push maturities further out, and keep our options open for when rates drop.',
    confidence: 91,
    sources: ['Board report #2024-Q4', 'Cost-benefit analysis', 'Risk decomposition'],
    followUp: ['Generate board summary', 'Show savings breakdown', 'What are the risks?']
  },
  'compare': {
    question: 'What changed between Optimization #341 and #342?',
    answer: 'Two key differences: (1) The credit rating constraint tightened from BBB- to BBB+, eliminating 3 instruments from the feasible set. (2) The objective shifted from pure cost minimization to include a liquidity term. This changed the allocation by $47M — moving from concentrated Treasury positions to a more diversified mix including green bonds.',
    confidence: 88,
    sources: ['Optimization #341 config', 'Optimization #342 config', 'Delta analysis'],
    followUp: ['Show side-by-side comparison', 'Which performed better?', 'Apply #341 constraints to current portfolio']
  },
  'cheapest': {
    question: 'Show me the cheapest strategy that improves duration by 10%',
    answer: 'Strategy "Extend & Diversify" achieves a 10.2% duration improvement at $8.1M annual cost (lowest among 12 feasible strategies). It works by: (1) Swapping $120M of 2-year paper for 7-year paper via a $3.2M swap, (2) Issuing a $80M 5-year green bond at 4.1% (below market by 40bps), (3) Reducing FX hedging from 80% to 65%, saving $2.1M annually.',
    confidence: 96,
    sources: ['Strategy comparison matrix', 'Cost analysis', 'Market rates'],
    followUp: ['Run this strategy', 'Show alternatives ranked by cost', 'What are the risks?']
  },
  'board': {
    question: 'Generate board-ready summary',
    answer: 'EXECUTIVE SUMMARY: The portfolio optimization recommends reallocating $420M across 8 instruments to achieve: 12bps yield improvement ($18.6M annually), 18% reduction in refinancing risk, and 23% improvement in liquidity coverage ratio. KEY TRADE-OFFS: Floating-rate exposure increases from 22% to 28% (mitigated by $180M in interest rate swaps). GREEN BONDS: 15% of allocation achieves ESG target. TIMELINE: Execution over 60 days with weekly milestones.',
    confidence: 89,
    sources: ['Optimization report', 'Risk analysis', 'Market data', 'ESG compliance'],
    followUp: ['Export as PDF', 'Share with team', 'Schedule review meeting']
  }
};

export default function DecisionCopilot() {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<ReasoningResult | null>(null);
  const [isThinking, setIsThinking] = useState(false);
  const [history, setHistory] = useState<ReasoningResult[]>([]);

  const SUGGESTIONS = [
    { icon: 'Target', text: 'Why was this allocation chosen?' },
    { icon: 'BarChart3', text: 'Compare Optimization #341 and #342' },
    { icon: 'DollarSign', text: 'Show cheapest strategy for 10% duration improvement' },
    { icon: 'FileText', text: 'Generate board-ready summary' },
    { icon: 'Globe', text: 'Explain this to a Minister of Finance' },
    { icon: 'AlertTriangle', text: 'What are the binding constraints?' }
  ];

  const handleSubmit = (q?: string) => {
    const question = q || query;
    if (!question.trim()) return;

    setIsThinking(true);
    setQuery('');

    // Simulate AI thinking
    setTimeout(() => {
      const key = Object.keys(MOCK_REASONS).find(k => 
        question.toLowerCase().includes(k)
      ) || 'why';
      
      const res: ReasoningResult = {
        ...MOCK_REASONS[key],
        question: question
      };

      setResult(res);
      setHistory(prev => [res, ...prev].slice(0, 10));
      setIsThinking(false);
    }, 1200);
  };

  return (
    <div className="space-y-6 animate-glass-in">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center">
          <span className="text-lg">🧠</span>
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">AI Decision Copilot</h2>
          <p className="text-sm text-slate-400">Ask anything about your portfolio and optimization results</p>
        </div>
      </div>

      {/* Input */}
      <div className="glass rounded-2xl p-4">
        <div className="flex gap-3">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
            placeholder="Ask a question about your portfolio..."
            className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500/50 transition-colors"
          />
          <button
            onClick={() => handleSubmit()}
            disabled={isThinking || !query.trim()}
            className="px-6 py-3 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-xl text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {isThinking ? 'Thinking...' : 'Ask'}
          </button>
        </div>

        {/* Suggestions */}
        {!result && !isThinking && (
          <div className="mt-4 flex flex-wrap gap-2">
            {SUGGESTIONS.map((s, i) => (
              <button
                key={i}
                onClick={() => {
                  setQuery(s.text);
                  handleSubmit(s.text);
                }}
                className="px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-sm text-slate-300 hover:bg-white/10 transition-colors"
              >
                {s.icon} {s.text}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Thinking animation */}
      {isThinking && (
        <div className="glass rounded-2xl p-6 text-center">
          <div className="flex items-center justify-center gap-2 mb-3">
            <div className="w-2 h-2 bg-indigo-400 rounded-full animate-pulse" />
            <div className="w-2 h-2 bg-indigo-400 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }} />
            <div className="w-2 h-2 bg-indigo-400 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }} />
          </div>
          <p className="text-slate-400 text-sm">Analyzing portfolio data, constraints, and optimization history...</p>
        </div>
      )}

      {/* Result */}
      {result && !isThinking && (
        <div className="glass rounded-2xl p-6 space-y-4">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <p className="text-slate-400 text-sm mb-1">Q: {result.question}</p>
              <p className="text-white leading-relaxed">{result.answer}</p>
            </div>
            <div className="ml-4 flex-shrink-0">
              <div className={`px-3 py-1 rounded-full text-xs font-medium ${
                result.confidence >= 90 ? 'bg-green-500/20 text-green-400' :
                result.confidence >= 75 ? 'bg-yellow-500/20 text-yellow-400' :
                'bg-red-500/20 text-red-400'
              }`}>
                {result.confidence}% confidence
              </div>
            </div>
          </div>

          {/* Sources */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-slate-500">Sources:</span>
            {result.sources.map((s, i) => (
              <span key={i} className="px-2 py-0.5 bg-white/5 rounded text-xs text-slate-400">
                {s}
              </span>
            ))}
          </div>

          {/* Follow-up questions */}
          {result.followUp.length > 0 && (
            <div className="border-t border-white/10 pt-4">
              <p className="text-xs text-slate-500 mb-2">Follow-up questions:</p>
              <div className="flex flex-wrap gap-2">
                {result.followUp.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => handleSubmit(q)}
                    className="px-3 py-1.5 bg-indigo-500/10 border border-indigo-500/20 rounded-lg text-xs text-indigo-400 hover:bg-indigo-500/20 transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* History */}
      {history.length > 1 && (
        <div className="glass rounded-2xl p-4">
          <h3 className="text-sm font-medium text-slate-400 mb-3">Recent Questions</h3>
          <div className="space-y-2">
            {history.slice(1, 5).map((h, i) => (
              <button
                key={i}
                onClick={() => setResult(h)}
                className="w-full text-left px-3 py-2 bg-white/5 rounded-lg text-sm text-slate-300 hover:bg-white/10 transition-colors truncate"
              >
                {h.question}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
