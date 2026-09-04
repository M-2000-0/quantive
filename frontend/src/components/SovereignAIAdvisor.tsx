import React, { useState } from 'react';
import { FileText, TriangleAlert as AlertTriangle } from 'lucide-react';

interface AdvisorQuery {
 question: string;
 answer: string;
 confidence: number;
 recommendation: string;
 alternatives: string[];
 risks: string[];
 assumptions: string[];
 sources: string[];
}

const MOCK_QUERIES: Record<string, AdvisorQuery> = {
 'refinance': {
 question: 'What is the safest way to refinance $12B next year?',
 answer: 'Based on current market conditions and your debt profile, I recommend a staggered issuance strategy across 3 tranches: $4B in 5Y notes (4.1% yield), $4B in 10Y bonds (4.3% yield), and $4B in 15Y bonds (4.5% yield). This spreads refinancing risk and locks in favorable rates before potential increases.',
 confidence: 87,
 recommendation: 'Proceed with staggered $12B issuance: 33% in 5Y, 33% in 10Y, 33% in 15Y tranches. Target completion by Q2 2027.',
 alternatives: [
 'Lump-sum $12B issuance in 10Y (simpler but concentration risk)',
 'Green bond framework ($3B green + $9B conventional)',
 'Extend maturities with 20Y+ ultra-long bonds'
 ],
 risks: [
 'Interest rates may rise 50-100bps if Fed tightens further',
 'Geopolitical events could widen spreads',
 'Credit rating watch may affect pricing'
 ],
 assumptions: [
 'Current yield curve remains relatively stable',
 'No major credit events in next 6 months',
 'IMF program review proceeds on schedule'
 ],
 sources: ['IMF DSA Framework', 'Market conditions as of Aug 2026', 'Historical issuance data'] },
 'hedge': {
 question: 'Should we hedge our FX exposure?',
 answer: 'Yes, but selectively. Your current 35% USD exposure is above the recommended 25% for your risk profile. However, full hedging at current forward rates costs 1.8% annually. I recommend hedging 60% of USD exposure using a 12-month rolling forward strategy.',
 confidence: 82,
 recommendation: 'Hedge 60% of USD exposure ($210M notional) using 12-month rolling forwards. Review quarterly.',
 alternatives: [
 'Full hedge (80%+) - higher cost but maximum protection',
 'Options-based hedging - expensive but asymmetric payoff',
 'Natural hedge via USD-denominated revenue streams'
 ],
 risks: [
 'Forward hedging locks in rates that may be unfavorable',
 'Currency may move in your favor unhedged',
 'Hedge counterparty risk with major banks'
 ],
 assumptions: [
 'USD/EUR remains within 1.05-1.15 range',
 'No major currency crisis in next 12 months',
 'Counterparty credit quality remains stable'
 ],
 sources: ['FX forward curve data', 'BIS hedging guidelines', 'Portfolio risk analysis'] },
 'default': {
 question: 'What should the Minister know about our debt position?',
 answer: 'The sovereign debt position is stable but requires attention. Key metrics: Debt/GDP at 68.2% (below 75% warning), Debt Service/Revenue at 22.1% (approaching 25% ceiling), and FX reserves at 4.2 months (adequate). The main risks are the 2027 maturity wall ($3.2B) and rising global rates.',
 confidence: 91,
 recommendation: 'Present to Minister: (1) Approve $2.4B 2027 refinancing plan, (2) Authorize 60% FX hedge, (3) Initiate green bond framework update.',
 alternatives: [
 'Maintain current strategy with no changes',
 'Aggressive fiscal consolidation to build buffers',
 'Seek IMF Extended Fund Facility for additional support'
 ],
 risks: [
 'Global rate environment may deteriorate',
 'Rating agency review in Q4 2026',
 'Regional contagion from neighboring sovereign stress'
 ],
 assumptions: [
 'No major external shock in next 12 months',
 'IMF program remains on track',
 'Political stability maintained'
 ],
 sources: ['Treasury daily report', 'IMF Article IV consultation', 'Rating agency reports'] } };

const SUGGESTIONS = [
 { icon: 'DollarSign', text: 'What is the safest way to refinance $12B next year?' },
 { icon: '💱', text: 'Should we hedge our FX exposure?' },
 { icon: 'FileText', text: 'What should the Minister know about our debt position?' },
 { icon: 'BarChart3', text: 'Compare our debt metrics to regional peers' },
 { icon: 'AlertTriangle', text: 'What are the biggest risks to our fiscal position?' },
 { icon: 'Target', text: 'Recommend optimal issuance timing for next quarter' },
];

export default function SovereignAIAdvisor() {
 const [query, setQuery] = useState('');
 const [result, setResult] = useState<AdvisorQuery | null>(null);
 const [isThinking, setIsThinking] = useState(false);
 const [history, setHistory] = useState<AdvisorQuery[]>([]);

 const handleSubmit = (q?: string) => {
 const question = q || query;
 if (!question.trim()) return;

 setIsThinking(true);
 setQuery('');

 setTimeout(() => {
 const key = Object.keys(MOCK_QUERIES).find(k => question.toLowerCase().includes(k)) || 'default';
 const res = MOCK_QUERIES[key];
 setResult(res);
 setHistory(prev => [res, ...prev].slice(0, 5));
 setIsThinking(false);
 }, 1500);
 };

 return (
 <div className="space-y-6 animate-glass-in">
 <div className="flex items-center gap-3">
 <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-violet-600 rounded-xl flex items-center justify-center">
 <span className="text-lg">🧠</span>
 </div>
 <div>
 <h2 className="text-xl font-bold text-white">Sovereign AI Advisor</h2>
 <p className="text-sm text-slate-400">Ask anything about your sovereign debt position — get minister-grade recommendations</p>
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
 placeholder="Ask the AI advisor about debt strategy, risk, or recommendations..."
 className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500/50 transition-colors"
 />
 <button
 onClick={() => handleSubmit()}
 disabled={isThinking || !query.trim()}
 className="px-6 py-3 bg-gradient-to-r from-indigo-500 to-violet-600 rounded-xl text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50"
 >
 {isThinking ? 'Analyzing...' : 'Ask'}
 </button>
 </div>
 {!result && !isThinking && (
 <div className="mt-4 flex flex-wrap gap-2">
 {SUGGESTIONS.map((s, i) => (
 <button
 key={i}
 onClick={() => { setQuery(s.text); handleSubmit(s.text); }}
 className="px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-xs text-slate-300 hover:bg-white/10 transition-colors"
 >
 {s.icon} {s.text}
 </button>
 ))}
 </div>
 )}
 </div>

 {/* Thinking */}
 {isThinking && (
 <div className="glass rounded-2xl p-8 text-center">
 <div className="flex items-center justify-center gap-2 mb-3">
 <div className="w-2 h-2 bg-indigo-400 rounded-full animate-pulse" />
 <div className="w-2 h-2 bg-indigo-400 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }} />
 <div className="w-2 h-2 bg-indigo-400 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }} />
 </div>
 <p className="text-slate-400 text-sm">Consulting sovereign debt models, market data, and policy frameworks...</p>
 </div>
 )}

 {/* Result */}
 {result && !isThinking && (
 <div className="space-y-4">
 {/* Main Answer */}
 <div className="glass rounded-2xl p-6 space-y-4">
 <div className="flex items-start justify-between">
 <p className="text-slate-400 text-sm">Q: {result.question}</p>
 <span className={`px-3 py-1 rounded-full text-xs font-medium ${
 result.confidence >= 85 ? 'bg-green-500/20 text-green-400' :
 result.confidence >= 70 ? 'bg-yellow-500/20 text-yellow-400' :
 'bg-red-500/20 text-red-400'
 }`}>
 {result.confidence}% confidence
 </span>
 </div>
 <p className="text-white leading-relaxed">{result.answer}</p>
 </div>

 {/* Recommendation */}
 <div className="glass rounded-2xl p-6 border-l-4 border-indigo-500">
 <h3 className="text-sm font-medium text-indigo-400 mb-2"> <FileText className="w-4 h-4 inline" /> MINISTER RECOMMENDATION</h3>
 <p className="text-white">{result.recommendation}</p>
 </div>

 <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
 {/* Alternatives */}
 <div className="glass rounded-2xl p-5">
 <h3 className="text-sm font-medium text-slate-400 mb-3">ALTERNATIVES CONSIDERED</h3>
 <div className="space-y-2">
 {result.alternatives.map((a, i) => (
 <div key={i} className="flex items-start gap-2 text-sm text-slate-300">
 <span className="text-slate-500 mt-0.5">{i + 1}.</span>
 <span>{a}</span>
 </div>
 ))}
 </div>
 </div>

 {/* Risks */}
 <div className="glass rounded-2xl p-5">
 <h3 className="text-sm font-medium text-red-400 mb-3"> <AlertTriangle className="w-4 h-4 inline" /> KEY RISKS</h3>
 <div className="space-y-2">
 {result.risks.map((r, i) => (
 <div key={i} className="flex items-start gap-2 text-sm text-slate-300">
 <span className="text-red-400">•</span>
 <span>{r}</span>
 </div>
 ))}
 </div>
 </div>
 </div>

 {/* Assumptions */}
 <div className="glass rounded-2xl p-5">
 <h3 className="text-sm font-medium text-slate-400 mb-3">ASSUMPTIONS</h3>
 <div className="flex flex-wrap gap-2">
 {result.assumptions.map((a, i) => (
 <span key={i} className="px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-xs text-slate-300">
 {a}
 </span>
 ))}
 </div>
 </div>

 {/* Sources */}
 <div className="glass rounded-2xl p-4">
 <h3 className="text-xs font-medium text-slate-500 mb-2">SOURCES</h3>
 <div className="flex gap-2 flex-wrap">
 {result.sources.map((s, i) => (
 <span key={i} className="px-2 py-1 bg-indigo-500/10 text-indigo-300 rounded text-xs">{s}</span>
 ))}
 </div>
 </div>
 </div>
 )}
 </div>
 );
}
