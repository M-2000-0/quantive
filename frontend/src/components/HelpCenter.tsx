import { useState, useEffect } from 'react';
import { api } from '../api';
import { SupportChat } from './SupportChat';

interface FAQItem {
  id: string;
  question: string;
  answer: string;
  helpful_count: number;
}

interface FAQCategory {
  id: string;
  name: string;
  description: string;
  items: FAQItem[];
}

export function HelpCenter() {
  const [categories, setCategories] = useState<FAQCategory[]>([]);
  const [activeTab, setActiveTab] = useState<'faq' | 'chat' | 'bugs'>('faq');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedItem, setExpandedItem] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadFAQ();
  }, []);

  const loadFAQ = async () => {
    try {
      const data = await api.request<FAQCategory[]>('/support/faq');
      setCategories(data);
    } catch (e) {
      console.error('Failed to load FAQ', e);
    }
    setLoading(false);
  };

  const markHelpful = async (itemId: string) => {
    try {
      await api.request(`/support/faq/items/${itemId}/helpful`, { method: 'POST' });
      setCategories(prev => prev.map(cat => ({
        ...cat,
        items: cat.items.map(item =>
          item.id === itemId ? { ...item, helpful_count: item.helpful_count + 1 } : item
        ) })));
    } catch (e) { /* ignore */ }
  };

  const filteredCategories = categories.map(cat => ({
    ...cat,
    items: cat.items.filter(item =>
      !searchQuery ||
      item.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.answer.toLowerCase().includes(searchQuery.toLowerCase())
    ) })).filter(cat => cat.items.length > 0);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Help Center</h1>

      {/* Tabs */}
      <div className="flex gap-1 bg-white/5 rounded-lg p-1">
        {(['faq', 'chat', 'bugs'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              activeTab === tab ? 'bg-white/10 text-white' : 'text-gray-400 hover:text-white'
            }`}
          >
            {tab === 'faq' ? 'FAQ' : tab === 'chat' ? 'AI Chat' : 'Report Bug'}
          </button>
        ))}
      </div>

      {activeTab === 'faq' && (
        <>
          <input
            type="text"
            placeholder="Search FAQ..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder-gray-500"
          />

          {loading ? (
            <div className="text-gray-400 text-center py-8">Loading...</div>
          ) : filteredCategories.length === 0 ? (
            <div className="text-gray-400 text-center py-8">
              {searchQuery ? 'No matching questions found.' : 'No FAQ items available yet.'}
            </div>
          ) : (
            <div className="space-y-4">
              {filteredCategories.map(cat => (
                <div key={cat.id} className="bg-white/[0.03] rounded-xl border border-white/5 p-4">
                  <h3 className="text-sm font-medium text-white mb-3">{cat.name}</h3>
                  <div className="space-y-2">
                    {cat.items.map(item => (
                      <div key={item.id} className="border-b border-white/5 last:border-0 pb-2">
                        <button
                          onClick={() => setExpandedItem(expandedItem === item.id ? null : item.id)}
                          className="w-full text-left text-sm text-gray-300 hover:text-white transition-colors py-1"
                        >
                          {item.question}
                        </button>
                        {expandedItem === item.id && (
                          <div className="mt-2 pl-4">
                            <p className="text-xs text-gray-400">{item.answer}</p>
                            <button
                              onClick={() => markHelpful(item.id)}
                              className="mt-2 text-[10px] text-gray-600 hover:text-green-400 transition-colors"
                            >
                              Helpful ({item.helpful_count})
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {activeTab === 'chat' && <SupportChat />}

      {activeTab === 'bugs' && (
        <div className="bg-white/[0.03] rounded-xl border border-white/5 p-4">
          <p className="text-sm text-gray-400 mb-3">Found a bug? Report it here and we'll investigate.</p>
          <p className="text-xs text-gray-600">
            You can also create a support ticket for any issue from the Tickets section.
          </p>
        </div>
      )}
    </div>
  );
}
