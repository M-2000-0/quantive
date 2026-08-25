import { useState, useRef, useEffect } from 'react';
import { api } from '../api';
import AppShell from '../components/layout/AppShell';
import Button from '../components/ui/Button';

interface Message {
  role: 'user' | 'advisor';
  content: string;
  suggestions?: string[];
  confidence?: number;
}

const QUICK_QUESTIONS = [
  { q: "Should we issue a bond now?", icon: "📈" },
  { q: "What are our biggest risks?", icon: "🛡️" },
  { q: "How do we compare to G7 peers?", icon: "🌍" },
  { q: "What's the optimal tenor mix?", icon: "⏱️" },
  { q: "Should we issue in USD or EUR?", icon: "💱" },
  { q: "How's our fiscal position?", icon: "📊" },
];

function renderMarkdown(text: string): string {
  return text
    .replace(/## (.*)/g, '<h2 class="text-lg font-bold text-slate-900 mt-4 mb-2">$1</h2>')
    .replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-slate-900">$1</strong>')
    .replace(/\n\n/g, '<br/><br/>')
    .replace(/\n/g, '<br/>')
    .replace(/- (.*)/g, '<li class="ml-4 text-slate-700">• $1</li>')
    .replace(/\|(.*)\|/g, (match) => {
      const cells = match.split('|').filter(Boolean);
      return '<tr>' + cells.map(c => `<td class="px-3 py-1 border border-white/40 text-sm">${c.trim()}</td>`).join('') + '</tr>';
    });
}

export default function AdvisorPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'advisor',
      content: "## 👋 Welcome to Quantive AI Advisor\n\nI'm your sovereign debt management advisor. Ask me about:\n\n• **Market Timing** — Should we issue now?\n• **Risk Analysis** — What are our risks?\n• **Peer Comparison** — How do we compare?\n• **Strategy** — What's the optimal approach?\n\nSelect a country and ask a question below.",
      suggestions: ["Should we issue a bond now?", "What are our biggest risks?", "Compare us to G7 peers"],
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [countryCode, setCountryCode] = useState('US');
  const messagesEnd = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async (question: string) => {
    if (!question.trim() || loading) return;

    const userMsg: Message = { role: 'user', content: question };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await api.advisor.ask(question, countryCode);
      setMessages(prev => [...prev, {
        role: 'advisor',
        content: res.answer,
        suggestions: res.suggestions,
        confidence: res.confidence,
      }]);
    } catch {
      setMessages(prev => [...prev, {
        role: 'advisor',
        content: "I'm sorry, I couldn't process that question. Please try again.",
        suggestions: ["Should we issue a bond now?"],
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell>
      <div className="flex flex-col h-[calc(100vh-4rem)] max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/40 bg-white">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center">
              <span className="text-white text-lg">🤖</span>
            </div>
            <div>
              <h1 className="text-lg font-bold text-slate-900">AI Debt Advisor</h1>
              <p className="text-xs text-slate-500">Sovereign debt management intelligence</p>
            </div>
          </div>
          <select
            value={countryCode}
            onChange={e => setCountryCode(e.target.value)}
            className="px-3 py-1.5 border border-slate-300 rounded-md text-sm text-slate-900 focus:ring-2 focus:ring-blue-500"
          >
            {['US', 'UK', 'JP', 'DE', 'FR', 'IT', 'CA', 'CN', 'IN', 'BR', 'AU', 'KR', 'MX', 'CH', 'SE', 'NO', 'SG'].map(c => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] rounded-2xl px-5 py-3 ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-100 text-slate-900'
              }`}>
                {msg.role === 'advisor' ? (
                  <div
                    className="text-sm leading-relaxed prose prose-sm max-w-none"
                    dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }}
                  />
                ) : (
                  <p className="text-sm">{msg.content}</p>
                )}

                {msg.confidence !== undefined && msg.confidence < 0.7 && (
                  <p className="text-xs text-slate-400 mt-2 italic">Confidence: {Math.round(msg.confidence * 100)}%</p>
                )}

                {msg.suggestions && msg.suggestions.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-3">
                    {msg.suggestions.map((s, j) => (
                      <button
                        key={j}
                        onClick={() => sendMessage(s)}
                        className="px-3 py-1 text-xs font-medium bg-white border border-white/40 rounded-full text-slate-600 hover:bg-blue-50 hover:border-blue-300 hover:text-blue-700 transition-colors"
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="bg-slate-100 rounded-2xl px-5 py-3">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEnd} />
        </div>

        {/* Quick Questions (show when few messages) */}
        {messages.length <= 2 && (
          <div className="px-6 pb-2">
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {QUICK_QUESTIONS.map((qq, i) => (
                <button
                  key={i}
                  onClick={() => sendMessage(qq.q)}
                  className="flex items-center gap-2 px-3 py-2 text-left text-sm text-slate-700 glass-card hover:border-blue-300 hover:bg-blue-50 transition-colors"
                >
                  <span>{qq.icon}</span>
                  <span className="truncate">{qq.q}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input */}
        <div className="px-6 py-4 border-t border-white/40 bg-white">
          <form onSubmit={(e) => { e.preventDefault(); sendMessage(input); }} className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Ask about sovereign debt management..."
              disabled={loading}
              className="flex-1 px-4 py-2.5 border border-slate-300 rounded-lg text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50"
            />
            <Button type="submit" variant="primary" size="md" disabled={loading || !input.trim()}>
              {loading ? 'Thinking...' : 'Ask'}
            </Button>
          </form>
        </div>
      </div>
    </AppShell>
  );
}
