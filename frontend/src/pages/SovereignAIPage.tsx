import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources?: { text: string; source: string; score: number }[];
  timestamp: Date;
}

interface Stats {
  total_chunks: number;
  sources: { source: string; count: number; type: string }[];
}

const BG = '#08090c';
const CARD = '#111318';
const BORDER = '#23272e';
const TEXT = '#e5e7eb';
const DIM = '#9ca3af';
const ACCENT = '#e8e8ea';
const GREEN = '#22c55e';

export default function SovereignAIPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: 'Hello! I\'m Quantive AI — your sovereign debt intelligence advisor. I run entirely locally with no external API calls. Ask me anything about sovereign debt, bond optimization, or public finance.',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<Stats | null>(null);
  const [showSources, setShowSources] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch('/api/ai/stats').then(r => r.json()).then(setStats).catch(() => {});
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function handleSend() {
    if (!input.trim() || loading) return;
    const query = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: query, timestamp: new Date() }]);
    setLoading(true);

    try {
      // Include CSRF token — required by backend CSRFMiddleware on POST.
      const csrfMatch = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/);
      const csrfToken = csrfMatch ? decodeURIComponent(csrfMatch[1]) : '';
      const res = await fetch('/api/ai/query', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}),
        },
        body: JSON.stringify({ query, n_results: 5, use_local_model: true }),
      });
      const data = await res.json();
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.answer || 'I couldn\'t generate a response.',
        sources: data.sources || [],
        timestamp: new Date(),
      }]);
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Error connecting to the AI engine. Please try again.',
        timestamp: new Date(),
      }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ padding: 24, background: BG, minHeight: '100vh', fontFamily: "'Inter', -apple-system, sans-serif", display: 'flex', flexDirection: 'column' }}>
      <div style={{ maxWidth: 900, margin: '0 auto', width: '100%', display: 'flex', flexDirection: 'column', height: 'calc(100vh - 48px)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 700, color: TEXT, margin: 0 }}>
              <span style={{ color: ACCENT }}>{'{'}</span> Sovereign AI Advisor
            </h1>
            <p style={{ fontSize: 12, color: DIM, margin: '2px 0 0 0' }}>Local RAG + Fine-tuned model — zero external APIs</p>
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            {[
              { to: '/ai-governance', label: 'Governance' },
              { to: '/validation-vendor-risk', label: 'Validation' },
            ].map(l => (
              <Link key={l.to} to={l.to} style={{ padding: '5px 10px', borderRadius: 6, fontSize: 11, fontWeight: 500, background: CARD, border: `1px solid ${BORDER}`, color: DIM, textDecoration: 'none' }}>{l.label}</Link>
            ))}
          </div>
        </div>

        {stats && (
          <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
            <div style={{ padding: '8px 14px', borderRadius: 6, background: CARD, border: `1px solid ${BORDER}`, fontSize: 12, color: DIM }}>
              Knowledge: <span style={{ color: ACCENT, fontWeight: 600 }}>{stats.total_chunks}</span> chunks
            </div>
            <div style={{ padding: '8px 14px', borderRadius: 6, background: CARD, border: `1px solid ${BORDER}`, fontSize: 12, color: DIM }}>
              Sources: <span style={{ color: ACCENT, fontWeight: 600 }}>{stats.sources?.length || 0}</span>
            </div>
          </div>
        )}

        <div style={{ flex: 1, overflow: 'auto', padding: 16, borderRadius: 8, background: CARD, border: `1px solid ${BORDER}`, marginBottom: 12 }}>
          {messages.map((msg, i) => (
            <div key={i} style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                <div style={{
                  width: 28, height: 28, borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 12, fontWeight: 700, flexShrink: 0,
                  background: msg.role === 'assistant' ? '#e8e8ea20' : '#3b82f620',
                  color: msg.role === 'assistant' ? ACCENT : '#3b82f6',
                }}>
                  {msg.role === 'assistant' ? 'AI' : 'U'}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, color: TEXT, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                  {msg.sources && msg.sources.length > 0 && (
                    <div style={{ marginTop: 8 }}>
                      <button
                        onClick={() => setShowSources(showSources === i ? null : i)}
                        style={{ fontSize: 11, color: ACCENT, background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
                      >
                        {msg.sources.length} sources
                      </button>
                      {showSources === i && (
                        <div style={{ marginTop: 6, display: 'flex', flexDirection: 'column', gap: 4 }}>
                          {msg.sources.map((s, j) => (
                            <div key={j} style={{ padding: '6px 10px', borderRadius: 4, background: '#08090c', fontSize: 11 }}>
                              <span style={{ color: GREEN, fontWeight: 600 }}>{(s.score * 100).toFixed(0)}%</span>
                              <span style={{ color: DIM, marginLeft: 6 }}>{s.source}</span>
                              <div style={{ color: TEXT, marginTop: 2 }}>{s.text}</div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
          {loading && (
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <div style={{ width: 28, height: 28, borderRadius: 6, background: '#e8e8ea20', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 700, color: ACCENT }}>AI</div>
              <div style={{ fontSize: 13, color: DIM }}>Thinking...</div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div style={{ display: 'flex', gap: 8 }}>
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSend()}
            placeholder="Ask about sovereign debt, bonds, fiscal policy..."
            disabled={loading}
            style={{
              flex: 1, padding: '10px 14px', borderRadius: 8, border: `1px solid ${BORDER}`,
              background: '#08090c', color: TEXT, fontSize: 13, outline: 'none',
            }}
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            style={{
              padding: '10px 20px', borderRadius: 8, border: 'none',
              background: loading || !input.trim() ? '#23272e' : ACCENT,
              color: loading || !input.trim() ? DIM : '#08090c',
              fontSize: 13, fontWeight: 600, cursor: loading || !input.trim() ? 'default' : 'pointer',
            }}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
