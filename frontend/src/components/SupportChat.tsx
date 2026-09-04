import { useState, useRef, useEffect } from 'react';
import { api } from '../api';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  type?: string;
  confidence?: number;
}

export function SupportChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: 'assistant', content: 'Hello! I can help you with common questions. What would you like to know?' },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEnd = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    const userMsg = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setLoading(true);

    try {
      const res = await api.request('/support/chat', {
        method: 'POST',
        body: JSON.stringify({ content: userMsg }) });
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: res.response,
        type: res.type,
        confidence: res.confidence }]);
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, something went wrong. Please try again.' }]);
    }
    setLoading(false);
  };

  return (
    <div className="flex flex-col h-[500px] bg-white/[0.03] rounded-xl border border-white/5">
      <div className="p-3 border-b border-white/5">
        <h3 className="text-sm font-medium text-white">Support Chat</h3>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] p-3 rounded-xl text-sm ${
              msg.role === 'user'
                ? 'bg-indigo-600/20 text-white'
                : 'bg-white/5 text-gray-300'
            }`}>
              <p>{msg.content}</p>
              {msg.type === 'ticket_suggestion' && (
                <button className="mt-2 px-3 py-1 bg-indigo-600/30 hover:bg-indigo-600/50 rounded-lg text-xs text-indigo-300 transition-colors">
                  Create Ticket
                </button>
              )}
              {msg.confidence !== undefined && (
                <p className="text-[10px] text-gray-600 mt-1">
                  Confidence: {Math.round(msg.confidence * 100)}%
                </p>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white/5 p-3 rounded-xl text-sm text-gray-400">Thinking...</div>
          </div>
        )}
        <div ref={messagesEnd} />
      </div>

      <div className="p-3 border-t border-white/5">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && sendMessage()}
            placeholder="Ask a question..."
            className="flex-1 px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder-gray-500"
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
