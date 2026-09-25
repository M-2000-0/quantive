import { useEffect, useRef, useState } from 'react';
import { MessageCircle, RotateCcw, Send, X } from 'lucide-react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources?: { text: string; source: string; score: number }[];
}

interface HistoryTurn {
  role: 'user' | 'assistant';
  content: string;
}

const SUGGESTIONS = [
  'How is the market doing today?',
  'What happens to my debt if rates rise 50bps?',
  'What is the price of Bitcoin?',
  'Explain debt sustainability analysis',
];

// Follow-up cues: short questions that only make sense with prior context
// ("what about 100bps?", "and for EUR?"). We still send the full recent
// history; the widget uses this only to show the contextual hint chip.
const FOLLOWUP_HINT_MAX_WORDS = 8;

function looksLikeFollowUp(q: string): boolean {
  const t = q.trim().toLowerCase();
  if (t.split(/\s+/).length <= FOLLOWUP_HINT_MAX_WORDS) return true;
  return /^(what about|and |how about|now |same |repeat|again|what if)/.test(t);
}

function csrfHeaders(): Record<string, string> {
  const m = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/);
  return {
    'Content-Type': 'application/json',
    ...(m ? { 'X-CSRF-Token': decodeURIComponent(m[1]) } : {}),
  };
}

export default function AIChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, loading]);

  async function send(text: string) {
    const q = text.trim();
    if (!q || loading) return;
    setInput('');
    setMessages((m) => [...m, { role: 'user', content: q }]);
    setLoading(true);

    // Send the recent exchange so follow-ups ("what about 100bps?") resolve
    // against prior context instead of starting cold.
    const history: HistoryTurn[] = messages
      .filter((m) => m.content.trim().length > 0)
      .slice(-6)
      .map((m) => ({ role: m.role, content: m.content.slice(0, 600) }));

    try {
      const res = await fetch('/api/ai/chat', {
        method: 'POST',
        credentials: 'include',
        headers: csrfHeaders(),
        body: JSON.stringify({ message: q, max_new_tokens: 150, history }),
      });
      const data = await res.json();
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          content: data.text || data.answer || "I couldn't generate a response.",
          sources: data.sources || [],
        },
      ]);
    } catch {
      setMessages((m) => [
        ...m,
        { role: 'assistant', content: 'Error connecting to the AI engine. Please try again.' },
      ]);
    } finally {
      setLoading(false);
    }
  }

  const lastAnswer = [...messages].reverse().find((m) => m.role === 'assistant');

  return (
    <>
      {/* Floating launcher — bottom right on every page */}
      {!open && (
        <button
          aria-label="Ask Quantive AI"
          onClick={() => setOpen(true)}
          style={{
            position: 'fixed', bottom: 24, right: 24, zIndex: 1000,
            width: 56, height: 56, borderRadius: '50%', border: 'none',
            background: 'linear-gradient(135deg, #c8a951, #a3863a)',
            color: '#0a0a0b', cursor: 'pointer',
            boxShadow: '0 4px 16px rgba(200, 169, 81, 0.4)',
            display: 'grid', placeItems: 'center',
          }}
        >
          <MessageCircle size={24} />
        </button>
      )}

      {/* Chat panel */}
      {open && (
        <div
          style={{
            position: 'fixed', bottom: 24, right: 24, zIndex: 1001,
            width: 380, maxWidth: 'calc(100vw - 32px)', height: 560, maxHeight: 'calc(100vh - 48px)',
            background: '#111318', border: '1px solid #23272e', borderRadius: 16,
            display: 'flex', flexDirection: 'column', overflow: 'hidden',
            boxShadow: '0 12px 40px rgba(0,0,0,0.5)',
          }}
        >
          {/* Header */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '12px 16px', borderBottom: '1px solid #23272e', background: '#0d0f13',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <MessageCircle size={16} color="#c8a951" />
              <div>
                <div style={{ color: '#e5e7eb', fontWeight: 600, fontSize: 13 }}>Quantive AI</div>
                <div style={{ color: '#22c55e', fontSize: 10, display: 'flex', alignItems: 'center', gap: 4 }}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#22c55e', display: 'inline-block' }} />
                  Live market data connected
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              {messages.length > 0 && (
                <button
                  aria-label="Reset conversation"
                  title="Reset conversation"
                  onClick={() => setMessages([])}
                  style={{ background: 'none', border: 'none', color: '#9ca3af', cursor: 'pointer', padding: 4 }}
                >
                  <RotateCcw size={15} />
                </button>
              )}
              <button
                aria-label="Close chat"
                onClick={() => setOpen(false)}
                style={{ background: 'none', border: 'none', color: '#9ca3af', cursor: 'pointer', padding: 4 }}
              >
                <X size={16} />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
            {messages.length === 0 && (
              <div>
                <p style={{ color: '#9ca3af', fontSize: 13, marginBottom: 12 }}>
                  Ask me about markets, stocks, Treasury yields, sovereign debt — I answer with live data and cite my sources. I remember our conversation, so follow-ups like “what about 100bps?” work too.
                </p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => send(s)}
                      style={{
                        textAlign: 'left', padding: '8px 12px', borderRadius: 8,
                        border: '1px solid #23272e', background: '#161a20',
                        color: '#c8a951', fontSize: 12, cursor: 'pointer',
                      }}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m, i) => (
              <div key={i} style={{ marginBottom: 12 }}>
                <div style={{
                  fontSize: 10, fontWeight: 700, letterSpacing: '0.06em',
                  color: m.role === 'user' ? '#9ca3af' : '#c8a951', marginBottom: 4,
                }}>
                  {m.role === 'user' ? 'YOU' : 'QUANTIVE AI'}
                </div>
                <div style={{
                  background: m.role === 'user' ? '#1a1f27' : '#141821',
                  border: '1px solid #23272e', borderRadius: 10,
                  padding: '10px 12px', color: '#e5e7eb', fontSize: 13,
                  whiteSpace: 'pre-wrap', lineHeight: 1.5,
                }}>
                  {m.content}
                </div>
                {m.sources && m.sources.length > 0 && (
                  <button
                    onClick={(e) => {
                      const el = e.currentTarget.nextElementSibling as HTMLElement | null;
                      if (el) el.style.display = el.style.display === 'none' ? 'block' : 'none';
                    }}
                    style={{
                      marginTop: 6, background: 'none', border: 'none',
                      color: '#6b7280', fontSize: 11, cursor: 'pointer', padding: 0,
                    }}
                  >
                    📚 {m.sources.length} sources
                  </button>
                )}
                {m.sources && m.sources.length > 0 && (
                  <div style={{ display: 'none', marginTop: 6 }}>
                    {m.sources.slice(0, 5).map((s, j) => (
                      <div key={j} style={{
                        fontSize: 11, color: '#9ca3af', padding: '6px 8px',
                        borderLeft: '2px solid #c8a951', marginBottom: 4, background: '#0d0f13',
                      }}>
                        <div style={{ color: '#c8a951', fontSize: 10, marginBottom: 2 }}>
                          {s.source || 'knowledge base'}
                        </div>
                        {s.text.slice(0, 120)}…
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div style={{ color: '#9ca3af', fontSize: 13, fontStyle: 'italic' }}>
                {lastAnswer ? 'Thinking about your follow-up…' : 'Analyzing market data…'}
              </div>
            )}
          </div>

          {/* Input */}
          <form
            onSubmit={(e) => { e.preventDefault(); send(input); }}
            style={{ display: 'flex', gap: 8, padding: 12, borderTop: '1px solid #23272e' }}
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={lastAnswer ? 'Ask a follow-up…' : 'Ask about stocks, yields, markets…'}
              style={{
                flex: 1, background: '#0d0f13', border: '1px solid #23272e',
                borderRadius: 8, padding: '9px 12px', color: '#e5e7eb', fontSize: 13, outline: 'none',
              }}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              style={{
                background: loading || !input.trim() ? '#23272e' : '#c8a951',
                color: loading || !input.trim() ? '#6b7280' : '#0a0a0b',
                border: 'none', borderRadius: 8, padding: '0 12px', cursor: 'pointer',
                display: 'grid', placeItems: 'center',
              }}
            >
              <Send size={15} />
            </button>
          </form>
        </div>
      )}
    </>
  );
}
