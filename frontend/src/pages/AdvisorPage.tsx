import { useState, useRef, useEffect, useCallback } from 'react';
import { api } from '../api';
import AppShell from '../components/layout/AppShell';
import Button from '../components/ui/Button';

// ── Types ──────────────────────────────────────────────────────────────────
interface Message {
  role: 'user' | 'advisor';
  content: string;
  displayedContent?: string;
  typing?: boolean;
  suggestions?: string[];
  confidence?: number;
  sources?: string[];
  ragDocs?: KnowledgeSnippet[];
  timestamp?: string;
}

interface KnowledgeSnippet {
  id: string;
  title: string;
  content: string;
  tags: string[];
  source: string;
  badge: string;
}

// ── Local RAG Knowledge Base ───────────────────────────────────────────────
const KNOWLEDGE_SNIPPETS: KnowledgeSnippet[] = [
  {
    id: 'milp',
    title: 'MILP (CBC) — Mixed-Integer Linear Programming',
    content: 'MILP formulates sovereign debt optimization as a linear program with integer constraints (cardinality, maturity buckets). CBC proves global optimality via branch-and-bound. Best for exact solutions when horizon ≤20 tenors and portfolio ≤50 instruments.',
    tags: ['milp', 'cbc', 'optimization', 'exact', 'branch-and-bound', 'strategy', 'tradeoff'],
    source: 'docs/optimization-model.md',
    badge: 'MILP',
  },
  {
    id: 'sa',
    title: 'Simulated Annealing — Heuristic Search',
    content: 'SA is a stochastic heuristic that explores allocation space via temperature-cooled random moves. No optimality guarantee but fast and robust to non-convex constraints. Ideal for large portfolios or when time limit <30s. Penalty-weighted energy + repair step.',
    tags: ['simulated_annealing', 'heuristic', 'annealing', 'non-convex', 'fast', 'tradeoff', 'reduce'],
    source: 'quantive/solvers/heuristic.py',
    badge: 'SA',
  },
  {
    id: 'qubo',
    title: 'QUBO Annealing — Quantum-Inspired',
    content: 'QUBO encodes continuous allocation as binary expansion (B bits per instrument). Energy is quadratic in bits; annealed classically on SIMULATOR backend. Useful for quantum-readiness benchmarking, not claimed superior to MILP. Includes deterministic feasibility repair.',
    tags: ['qubo', 'quantum', 'annealing', 'binary', 'simulator', 'strategy', 'fx'],
    source: 'quantive/solvers/qubo.py',
    badge: 'QUBO',
  },
  {
    id: 'imf-dsa',
    title: 'IMF DSA — Debt Sustainability Analysis',
    content: 'IMF DSA framework assesses debt sustainability via baseline + stress scenarios (growth, rates, FX, contingent liabilities). Thresholds: debt-to-GDP <70% for EMs, gross financing needs <15% GDP. Required for program engagement.',
    tags: ['imf', 'dsa', 'sustainability', 'threshold', 'stress', 'fiscal'],
    source: 'IMF Guidance Note on DSA',
    badge: 'IMF DSA',
  },
  {
    id: 'imf-mtds',
    title: 'IMF MTDS — Medium-Term Debt Strategy',
    content: 'MTDS helps sovereigns choose financing mix across currency, maturity, and instrument type to minimize cost at acceptable risk. Cost-risk frontier, refinancing risk (ATM, % maturing in 12M), interest-rate risk (% refixing), FX risk (% foreign currency).',
    tags: ['imf', 'mtds', 'cost-risk', 'maturity', 'refinancing', 'fx', 'currency', 'strategy', 'tradeoff'],
    source: 'IMF MTDS Guidance',
    badge: 'MTDS',
  },
  {
    id: 'risk-fx',
    title: 'FX Risk & Currency Diversification',
    content: 'FX risk rises with foreign-currency share and volatility. Mitigation: limit FX to <30% of portfolio, hedge 30-50% via swaps, favor local-currency long tenors when curve is normal. Shock scenario: +15% USD appreciation → debt service +~$500M.',
    tags: ['fx', 'currency', 'hedge', 'risk', 'reduce', 'exposure'],
    source: 'IMF FX Risk Note + Quantive scenario_config',
    badge: 'FX',
  },
  {
    id: 'refi-risk',
    title: 'Refinancing & Rollover Risk',
    content: 'Refinancing risk = peak share maturing in any year. Cap at 20-30% to avoid cliff. Mitigated by smoothing maturity ladder, maintaining liquidity buffer ≥12M debt service, and ladder_initial diversification.',
    tags: ['refinancing', 'rollover', 'maturity', 'liquidity', 'risk', 'reduce'],
    source: 'quantive/objectives/spec.py',
    badge: 'Refi',
  },
  {
    id: 'tradeoff',
    title: 'Cost vs Risk Tradeoff',
    content: 'Lowest-cost strategy concentrates in cheap short FX debt but raises refinancing/FX risk. Lowest-risk diversifies across currencies/tenors at +3-7% higher cost. Best-overall sits near efficient frontier knee. Stress-resilient uses minimax (worst-scenario) objective.',
    tags: ['tradeoff', 'cost', 'risk', 'frontier', 'strategy', 'explain'],
    source: 'quantive/strategies.py',
    badge: 'Tradeoff',
  },
];

// Simple keyword RAG: score snippet by tag/token overlap
function retrieveDocs(query: string, topK = 3): KnowledgeSnippet[] {
  const tokens = query.toLowerCase().split(/[^a-z0-9]+/).filter(Boolean);
  const scored = KNOWLEDGE_SNIPPETS.map((doc) => {
    let score = 0;
    for (const t of tokens) {
      if (doc.tags.some((tag) => tag.includes(t) || t.includes(tag))) score += 2;
      if (doc.title.toLowerCase().includes(t)) score += 1;
      if (doc.content.toLowerCase().includes(t)) score += 0.5;
    }
    // boost IMF if query mentions IMF/dsa/mtds
    if (tokens.some((x) => ['imf','dsa','mtds'].includes(x)) && doc.id.startsWith('imf')) score += 3;
    return { doc, score };
  });
  scored.sort((a, b) => b.score - a.score);
  const filtered = scored.filter((s) => s.score > 0).slice(0, topK).map((s) => s.doc);
  return filtered.length ? filtered : KNOWLEDGE_SNIPPETS.slice(0, 1);
}

// ── Prompt Templates ───────────────────────────────────────────────────────
const PROMPT_TEMPLATES: Array<{ label: string; icon: string; prompt: string; hint: string }> = [
  { label: 'Why this strategy?', icon: '🧭', prompt: 'Why was this strategy selected? Explain the tradeoff between cost and risk.', hint: 'Explain selection rationale' },
  { label: 'Reduce FX risk', icon: '💱', prompt: 'How can we reduce FX risk to under 10%? What is the delta in cost and exposure?', hint: 'Cut FX to 10%' },
  { label: 'Explain tradeoff', icon: '⚖️', prompt: 'Explain the tradeoff between the lowest-cost and lowest-risk strategies.', hint: 'Cost vs risk frontier' },
  { label: 'MILP vs SA vs QUBO', icon: '⚙️', prompt: 'When should we use MILP vs Simulated Annealing vs QUBO? Which is best for our portfolio?', hint: 'Solver choice' },
  { label: 'IMF DSA check', icon: '🏛️', prompt: 'Does our current debt level pass the IMF DSA sustainability thresholds?', hint: 'IMF guidance' },
  { label: 'Refi cliff', icon: '📉', prompt: 'Where is our refinancing cliff and how do we smooth it?', hint: 'Maturity ladder' },
];

const QUICK_QUESTIONS = [
  { q: 'Should we issue a bond now?', icon: '📈' },
  { q: 'What are our biggest risks?', icon: '🛡️' },
  { q: 'How do we compare to G7 peers?', icon: '🌍' },
  { q: "What's the optimal tenor mix?", icon: '⏱️' },
  { q: 'Should we issue in USD or EUR?', icon: '💱' },
  { q: "How's our fiscal position?", icon: '📊' },
];

function renderMarkdown(text: string): string {
  return text
    .replace(/## (.*)/g, '<h2 class="text-[14px] font-bold text-slate-900 mt-3 mb-1.5">$1</h2>')
    .replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-slate-900">$1</strong>')
    .replace(/\n\n/g, '<br/><br/>')
    .replace(/\n/g, '<br/>')
    .replace(/- (.*)/g, '<li class="ml-4 text-slate-700">• $1</li>')
    .replace(/\|(.*)\|/g, (match) => {
      const cells = match.split('|').filter(Boolean);
      return '<tr>' + cells.map((c) => `<td class="px-3 py-1 border border-white/40 text-sm">${c.trim()}</td>`).join('') + '</tr>';
    });
}

// Local fallback mock that fuses RAG docs + portfolio context
function buildFallbackAnswer(question: string, countryCode: string, ctx: string, ragDocs: KnowledgeSnippet[]): { answer: string; suggestions: string[]; confidence: number; sources: string[] } {
  const q = question.toLowerCase();
  const docsBlock = ragDocs.map((d) => `**[${d.badge}] ${d.title}** — ${d.content} _(${d.source})_`).join('\n\n');
  let core = '';
  if (q.includes('fx') || q.includes('currency') || q.includes('dollar') || q.includes('eur')) {
    core = `### FX Risk — ${countryCode}\n\nForeign-currency share drives FX exposure. ${ctx ? `\n\n**Your portfolio context:** ${ctx}` : ''}\n\nReducing FX to 10% typically lifts expected financing cost by ~50–90 bps (≈ $150–300M on a $30B portfolio) but cuts 1-yr 15% shock loss by ~$500M. Recommended: cap FX at 30%, hedge 30–50% via cross-currency swaps, and lengthen local-currency tenors when 2s10s > +50bps.`;
  } else if (q.includes('tradeoff') || q.includes('lowest cost') || q.includes('lowest risk')) {
    core = `### Cost vs Risk Tradeoff\n\nThe efficient frontier knees near **Best-Overall**: Lowest-cost saves ~$200M/yr but refinancing risk rises to ~0.28; Lowest-risk cuts refi to ~0.12 at +$170M cost. ${ctx ? `\n\n**Context:** ${ctx}` : ''}\n\nStress-resilient (minimax) optimizes worst-scenario cost — best when VIX >25 or curve inverted.`;
  } else if (q.includes('why') && q.includes('strategy')) {
    core = `### Why this strategy was selected\n\nOptimization weighted cost 35%, refi 25%, rate 20%, FX 20%. The winner minimized weighted sum while respecting refi-cap and FX limits. ${ctx ? `\n\n**Context:** ${ctx}` : ''}\n\nSee waterfall in Explainability for SHAP contributions and the solver-rationale card for MILP/SA/QUBO choice.`;
  } else if (q.includes('milp') || q.includes('sa') || q.includes('qubo') || q.includes('solver') || q.includes('quantum')) {
    core = `### MILP vs SA vs QUBO\n\n- **MILP (CBC)**: exact, proves optimality; prefer when ≤50 instruments, linear objectives, need audit-proof bound.\n- **SA**: fast heuristic, penalty + repair; prefer when time <30s, non-convex/cardinality, need diverse seeds.\n- **QUBO (simulator)**: binary-expansion quantum-inspired; use for quantum-readiness, not default production.\n\nAll three should converge within ~5% on feasible portfolios; divergence signals infeasibility or tight caps.`;
  } else if (q.includes('imf') || q.includes('dsa') || q.includes('mtds') || q.includes('sustainability')) {
    core = `### IMF DSA / MTDS Check\n\nDSA baseline: debt/GDP <70% (EM) and GFN <15% GDP; stress tests for growth, rates, FX, contingent liabilities. MTDS picks currency/maturity mix on cost-risk frontier. ${ctx ? `\n\n**Context:** ${ctx}` : ''}\n\nIf debt/GDP >100% or FX >40%, flag sustainability — recommend fiscal consolidation + extending ATM >6y.`;
  } else {
    core = `### Advisor — ${countryCode}\n\n${question.trim() ? `You asked: **${question}**\n\n` : ''}Based on current market and your portfolio, here's a data-backed view. ${ctx ? `\n\n**Portfolio context:** ${ctx}` : ''}\n\nUse the prompt templates below or ask about issuance timing, risk, peers, or tenor.`;
  }
  const answer = `${core}\n\n---\n\n**Retrieved knowledge (RAG):**\n\n${docsBlock}\n\n*Fallback mock — no LLM key / API unreachable. Connect backend /advisor for live answers.*`;
  return {
    answer,
    suggestions: ['Why was this strategy selected? Explain the tradeoff', 'How can we reduce FX risk to under 10%?', 'When should we use MILP vs SA vs QUBO?'],
    confidence: 0.62,
    sources: ragDocs.map((d) => d.source),
  };
}

export default function AdvisorPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'advisor',
      content:
        '## 👋 Welcome to Quantive AI Advisor\n\nI\'m your sovereign debt management advisor with **RAG over MILP/SA/QUBO + IMF guidance** and live portfolio context. Ask me about:\n\n• **Market Timing** — Should we issue now?\n• **Risk Analysis** — What are our risks?\n• **Peer Comparison** — How do we compare?\n• **Strategy** — What\'s the optimal approach?\n\nSelect a country and try a prompt template below.',
      displayedContent:
        '## 👋 Welcome to Quantive AI Advisor\n\nI\'m your sovereign debt management advisor with **RAG over MILP/SA/QUBO + IMF guidance** and live portfolio context. Ask me about:\n\n• **Market Timing** — Should we issue now?\n• **Risk Analysis** — What are our risks?\n• **Peer Comparison** — How do we compare?\n• **Strategy** — What\'s the optimal approach?\n\nSelect a country and try a prompt template below.',
      suggestions: ['Should we issue a bond now?', 'What are our biggest risks?', 'Compare us to G7 peers'],
      confidence: 1,
      sources: ['local-knowledge-base'],
      ragDocs: KNOWLEDGE_SNIPPETS.slice(0, 2),
      timestamp: new Date().toLocaleTimeString(),
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [countryCode, setCountryCode] = useState('US');
  const [portfolioCtx, setPortfolioCtx] = useState<string>('');
  const [optCtx, setOptCtx] = useState<string>('');
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
  const messagesEnd = useRef<HTMLDivElement>(null);
  const typingTimers = useRef<number[]>([]);

  // Fetch context-aware data: portfolios + optimizations + market
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const [portRes, optRes] = await Promise.allSettled([
          api.portfolios.list({ page_size: 3 } as never),
          api.optimizations.list({ page_size: 3 } as never),
        ]);
        if (cancelled) return;
        if (portRes.status === 'fulfilled') {
          const v: unknown = portRes.value;
          // support both paginated shape {data: Portfolio[]} and {portfolios: Portfolio[]}
          const list: unknown[] =
            (v as { data?: unknown[] })?.data ??
            (v as { portfolios?: unknown[] })?.portfolios ??
            [];
          if (Array.isArray(list) && list.length) {
            const first = list[0] as Record<string, unknown>;
            const inst = (first['instruments'] as unknown[]) ?? [];
            const name = (first['name'] as string) ?? 'Portfolio';
            setPortfolioCtx(`${name} — ${inst.length} instruments; currencies include ${(inst as Array<Record<string,string>>).slice(0,3).map((x)=>x['currency']).join(', ') || 'USD'}`);
          }
        }
        if (optRes.status === 'fulfilled') {
          const v: unknown = optRes.value;
          const list: unknown[] =
            (v as { data?: unknown[] })?.data ??
            (Array.isArray(v) ? v as unknown[] : []);
          if (Array.isArray(list) && list.length) {
            const j = list[0] as Record<string, unknown>;
            setOptCtx(`Last optimization: ${String(j['name'] ?? j['id'] ?? 'job')} — status ${String(j['status'] ?? 'unknown')}`);
          }
        }
      } catch {
        // silent — keep fallback context empty
      }
    };
    void load();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // typing effect for last advisor message
  const streamIn = useCallback((full: string, idx: number) => {
    // clear previous timers
    typingTimers.current.forEach((t) => window.clearInterval(t));
    typingTimers.current = [];
    let pos = 0;
    const step = Math.max(1, Math.ceil(full.length / 220));
    const timer = window.setInterval(() => {
      pos = Math.min(full.length, pos + step);
      setMessages((prev) =>
        prev.map((m, i) => (i === idx ? { ...m, displayedContent: full.slice(0, pos), typing: pos < full.length } : m))
      );
      if (pos >= full.length) {
        window.clearInterval(timer);
        setMessages((prev) => prev.map((m, i) => (i === idx ? { ...m, typing: false } : m)));
      }
    }, 14);
    typingTimers.current.push(timer);
  }, []);

  useEffect(() => {
    return () => { typingTimers.current.forEach((t) => window.clearInterval(t)); };
  }, []);

  const sendMessage = async (question: string) => {
    if (!question.trim() || loading) return;
    const ragDocs = retrieveDocs(question);
    const ctx = [portfolioCtx, optCtx].filter(Boolean).join(' · ');
    const userMsg: Message = { role: 'user', content: question, displayedContent: question, timestamp: new Date().toLocaleTimeString() };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    // placeholder advisor message for streaming
    const placeholderIdxRef = { current: 0 };
    setMessages((prev) => {
      placeholderIdxRef.current = prev.length;
      return [...prev, { role: 'advisor', content: '', displayedContent: '', typing: true, timestamp: new Date().toLocaleTimeString() } as Message];
    });

    try {
      const res = await api.advisor.ask(question, countryCode);
      const answer = (res as { answer: string }).answer ?? String(res);
      const suggestions = (res as { suggestions?: string[] }).suggestions;
      const confidence = (res as { confidence?: number }).confidence;
      const sources = (res as { sources?: string[] }).sources;
      setMessages((prev) =>
        prev.map((m, i) =>
          i === placeholderIdxRef.current
            ? {
                role: 'advisor',
                content: answer,
                displayedContent: '',
                typing: true,
                suggestions: suggestions ?? ragDocs.map((d) => d.title),
                confidence,
                sources: sources ?? ragDocs.map((d) => d.source),
                ragDocs,
                timestamp: new Date().toLocaleTimeString(),
              }
            : m
        )
      );
      // defer streaming to next tick so state has placeholder
      setTimeout(() => streamIn(answer, placeholderIdxRef.current), 0);
    } catch {
      // fallback mock
      const fallback = buildFallbackAnswer(question, countryCode, ctx, ragDocs);
      setMessages((prev) =>
        prev.map((m, i) =>
          i === placeholderIdxRef.current
            ? {
                role: 'advisor',
                content: fallback.answer,
                displayedContent: '',
                typing: true,
                suggestions: fallback.suggestions,
                confidence: fallback.confidence,
                sources: fallback.sources,
                ragDocs,
                timestamp: new Date().toLocaleTimeString(),
              }
            : m
        )
      );
      setTimeout(() => streamIn(fallback.answer, placeholderIdxRef.current), 0);
    } finally {
      setLoading(false);
    }
  };

  const copyMessage = async (text: string, idx: number) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedIdx(idx);
      setTimeout(() => setCopiedIdx(null), 1400);
    } catch {
      // ignore
    }
  };

  const contextLine = [portfolioCtx, optCtx].filter(Boolean).join(' · ') || 'No live portfolio context — using mock demo. Connect backend for real data.';

  return (
    <AppShell>
      <div className="flex flex-col h-[calc(100vh-4rem)] max-w-5xl mx-auto">
        {/* Header — liquid glass */}
        <div className="flex flex-col gap-2 px-2 sm:px-0">
          <div className="flex items-center justify-between glass-card px-5 py-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-blue-600 via-indigo-600 to-violet-600 flex items-center justify-center shadow-[0_8px_24px_rgba(59,130,246,0.35)] ring-1 ring-white/30">
                <span className="text-white text-lg">🤖</span>
              </div>
              <div>
                <h1 className="text-[15px] font-bold tracking-tight text-slate-900">AI Debt Advisor</h1>
                <p className="text-xs text-slate-500">RAG · MILP / SA / QUBO · IMF DSA/MTDS · streaming</p>
              </div>
              <span className="hidden sm:inline-flex ml-2 glass-badge text-[10px] tracking-widest uppercase bg-white/70 text-slate-700 ring-1 ring-white/40">Phase 4</span>
            </div>
            <div className="flex items-center gap-2">
              <select
                value={countryCode}
                onChange={(e) => setCountryCode(e.target.value)}
                className="px-3 py-1.5 glass-input w-auto text-sm !py-1.5 !px-3 rounded-xl border-white/50 bg-white/70"
              >
                {['US', 'UK', 'JP', 'DE', 'FR', 'IT', 'CA', 'CN', 'IN', 'BR', 'AU', 'KR', 'MX', 'CH', 'SE', 'NO', 'SG'].map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Context-aware banner */}
          <div className="glass-card px-4 py-2.5 flex flex-col sm:flex-row sm:items-center gap-2 text-xs text-slate-600">
            <span className="inline-flex items-center gap-1.5 font-semibold text-slate-700"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /> Live context</span>
            <span className="text-slate-500 truncate">{contextLine}</span>
            <span className="ml-auto hidden sm:inline-flex gap-1.5">
              <span className="glass-badge bg-blue-500/10 text-blue-700 ring-blue-500/15">MILP</span>
              <span className="glass-badge bg-violet-500/10 text-violet-700 ring-violet-500/15">SA</span>
              <span className="glass-badge bg-cyan-500/10 text-cyan-700 ring-cyan-500/15">QUBO</span>
            </span>
          </div>

          {/* Prompt templates */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {PROMPT_TEMPLATES.map((t) => (
              <button
                key={t.label}
                onClick={() => sendMessage(t.prompt)}
                className="text-left glass-card px-3.5 py-2.5 hover:shadow-lg hover:border-white/70 transition-all group"
              >
                <div className="flex items-center gap-2">
                  <span className="w-7 h-7 rounded-xl bg-white/80 ring-1 ring-white/50 flex items-center justify-center text-sm shadow-sm group-hover:scale-105 transition-transform">{t.icon}</span>
                  <span className="text-sm font-semibold text-slate-900">{t.label}</span>
                  <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded-full bg-slate-900 text-white opacity-80">{t.hint}</span>
                </div>
                <p className="text-xs text-slate-500 mt-1 line-clamp-2">{t.prompt}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-2 sm:px-0 py-4 space-y-4">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`relative max-w-[86%] sm:max-w-[80%] rounded-[18px] px-4 sm:px-5 py-3.5 shadow-[0_8px_24px_rgba(0,0,0,0.06)] backdrop-blur-xl border ${
                  msg.role === 'user'
                    ? 'bg-gradient-to-br from-blue-600 to-indigo-600 text-white border-white/20 rounded-br-[8px]'
                    : 'glass-card !bg-white/75 text-slate-900 border-white/60 rounded-bl-[8px]'
                }`}
              >
                {msg.role === 'advisor' ? (
                  <div
                    className="text-sm leading-relaxed prose prose-sm max-w-none prose-p:my-1.5"
                    dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.displayedContent ?? msg.content) }}
                  />
                ) : (
                  <p className="text-sm leading-relaxed">{msg.content}</p>
                )}

                {/* RAG docs */}
                {msg.role === 'advisor' && msg.ragDocs && msg.ragDocs.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {msg.ragDocs.map((d) => (
                      <span key={d.id} title={d.content} className="inline-flex items-center gap-1.5 text-[11px] px-2.5 py-1 rounded-full bg-white/85 border border-white/60 text-slate-700 backdrop-blur-md">
                        <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />{d.badge} — {d.title.split('—')[0].trim()}
                      </span>
                    ))}
                  </div>
                )}

                {msg.confidence !== undefined && (
                  <div className="mt-2 flex items-center gap-2">
                    <span className={`text-[11px] px-2 py-0.5 rounded-full border backdrop-blur-md ${msg.confidence >= 0.8 ? 'bg-emerald-500/15 text-emerald-700 border-emerald-500/20' : msg.confidence >= 0.6 ? 'bg-amber-500/15 text-amber-700 border-amber-500/20' : 'bg-red-500/15 text-red-700 border-red-500/20'}`}>
                      Confidence {(msg.confidence * 100).toFixed(0)}%
                      {msg.confidence < 0.7 ? ' — verify' : ''}
                    </span>
                    {msg.sources && msg.sources.length > 0 && (
                      <span className="text-[11px] text-slate-400 truncate max-w-[180px]">via {msg.sources.slice(0,2).join(', ')}</span>
                    )}
                  </div>
                )}

                {msg.suggestions && msg.suggestions.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-3">
                    {msg.suggestions.slice(0, 4).map((s, j) => (
                      <button
                        key={j}
                        onClick={() => sendMessage(s)}
                        className="px-3 py-1 text-xs font-medium bg-white/90 border border-white/60 rounded-full text-slate-700 hover:bg-blue-50 hover:border-blue-200 hover:text-blue-700 transition-colors shadow-sm"
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                )}

                {/* bottom meta row */}
                <div className="mt-2.5 flex items-center gap-2 text-[11px] text-slate-400">
                  {msg.timestamp && <span>{msg.timestamp}</span>}
                  {msg.role === 'advisor' && msg.typing && <span className="inline-flex items-center gap-1"><span className="w-1 h-1 rounded-full bg-slate-400 animate-bounce" /><span className="w-1 h-1 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '150ms' }} /><span className="w-1 h-1 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '300ms' }} /> typing…</span>}
                  <button
                    onClick={() => copyMessage(msg.content, i)}
                    className={`ml-auto inline-flex items-center gap-1 px-2 py-1 rounded-full border text-xs font-medium transition-colors ${msg.role === 'user' ? 'bg-white/15 text-white border-white/25 hover:bg-white/25' : 'bg-white/80 text-slate-600 border-white/60 hover:bg-white'}`}
                    title="Copy message"
                  >
                    {copiedIdx === i ? '✓ Copied' : '⎘ Copy'}
                  </button>
                </div>
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="glass-card px-5 py-3.5 bg-white/70">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                  <span className="text-xs text-slate-500 ml-1">Consulting RAG + market + portfolio…</span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEnd} />
        </div>

        {/* Quick Questions (when few messages) */}
        {messages.length <= 2 && (
          <div className="px-2 sm:px-0 pb-2">
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {QUICK_QUESTIONS.map((qq, idx) => (
                <button
                  key={idx}
                  onClick={() => sendMessage(qq.q)}
                  className="flex items-center gap-2 px-3 py-2 text-left text-sm text-slate-700 glass-card hover:border-blue-200 hover:bg-blue-50/70 transition-colors"
                >
                  <span>{qq.icon}</span>
                  <span className="truncate">{qq.q}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input — glass */}
        <div className="px-2 sm:px-0 pb-3">
          <form onSubmit={(e) => { e.preventDefault(); sendMessage(input); }} className="glass-card p-2 flex gap-2 items-center">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about strategy, FX, tenor, IMF thresholds… (RAG-enabled)"
              disabled={loading}
              className="flex-1 px-4 py-2.5 bg-white/80 border border-white/60 rounded-xl text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400/50 disabled:opacity-50 backdrop-blur-md"
            />
            <Button type="submit" variant="primary" size="md" disabled={loading || !input.trim()}>
              {loading ? 'Thinking…' : 'Ask'}
            </Button>
          </form>
          <p className="text-[11px] text-slate-400 text-center mt-1.5">Streaming typing · RAG snippets shown as badges · Falls back to local mock if API unreachable.</p>
        </div>
      </div>
    </AppShell>
  );
}
