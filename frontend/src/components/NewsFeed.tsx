import { useState, useEffect, useCallback } from 'react';
import { api } from '../api';
import { GlassAreaChart } from './charts/GlassAreaChart';

interface NewsArticle {
  id: string;
  title: string;
  summary: string;
  url: string;
  author: string | null;
  published_at: string | null;
  tickers_json: string[] | null;
  sentiment_score: number | null;
  category: string;
  is_read: boolean;
  is_starred: boolean;
}

interface NewsSource {
  id: string;
  name: string;
  source_type: string;
  is_active: boolean;
  article_count: number;
  last_fetched_at: string | null;
}

interface DigestData {
  total_articles: number;
  categories: Record<string, NewsArticle[]>;
  top_tickers: { ticker: string; count: number }[];
}

const CATEGORY_COLORS: Record<string, string> = {
  macro: '#6366f1',
  rates: '#c8a951',
  fx: '#22c55e',
  equity: '#3b82f6',
  crypto: '#f59e0b',
  geopolitical: '#ef4444',
  green: '#10b981',
  general: '#6b7280' };

const CATEGORY_LABELS: Record<string, string> = {
  macro: 'Macro',
  rates: 'Rates',
  fx: 'FX',
  equity: 'Equity',
  crypto: 'Crypto',
  geopolitical: 'Geopolitical',
  green: 'Green/ESG',
  general: 'General' };

export function NewsFeed() {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [sources, setSources] = useState<NewsSource[]>([]);
  const [digest, setDigest] = useState<DigestData | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [ingesting, setIngesting] = useState(false);
  const [activeTab, setActiveTab] = useState<'feed' | 'digest' | 'sources'>('feed');

  const loadArticles = useCallback(async () => {
    try {
      const params: Record<string, string> = { limit: '100' };
      if (selectedCategory) params.category = selectedCategory;
      if (searchQuery) params.search = searchQuery;
      const data = await api.request('/news/articles', { params });
      setArticles(data);
    } catch (e) {
      console.error('Failed to load articles', e);
    }
  }, [selectedCategory, searchQuery]);

  const loadDigest = useCallback(async () => {
    try {
      const data = await api.request('/news/digest?hours=24');
      setDigest(data);
    } catch (e) {
      console.error('Failed to load digest', e);
    }
  }, []);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      await Promise.all([loadArticles(), loadDigest()]);
      try {
        const srcData = await api.request('/news/sources');
        setSources(srcData);
      } catch (e) { /* ignore */ }
      setLoading(false);
    };
    load();
  }, [loadArticles, loadDigest]);

  const handleIngest = async () => {
    setIngesting(true);
    try {
      await api.request('/news/ingest', { method: 'POST' });
      await loadArticles();
      await loadDigest();
    } catch (e) {
      console.error('Ingestion failed', e);
    }
    setIngesting(false);
  };

  const toggleStar = async (id: string) => {
    try {
      await api.request(`/news/articles/${id}/star`, { method: 'POST' });
      setArticles(prev => prev.map(a => a.id === id ? { ...a, is_starred: !a.is_starred } : a));
    } catch (e) { /* ignore */ }
  };

  const markRead = async (id: string) => {
    try {
      await api.request(`/news/articles/${id}/read`, { method: 'POST' });
      setArticles(prev => prev.map(a => a.id === id ? { ...a, is_read: true } : a));
    } catch (e) { /* ignore */ }
  };

  const sentimentLabel = (score: number | null) => {
    if (score === null) return null;
    if (score > 0.2) return <span className="text-green-400 text-xs font-medium">Positive</span>;
    if (score < -0.2) return <span className="text-red-400 text-xs font-medium">Negative</span>;
    return <span className="text-gray-400 text-xs font-medium">Neutral</span>;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">News Feed</h1>
          <p className="text-sm text-gray-400 mt-1">
            {digest?.total_articles || 0} articles in last 24h
          </p>
        </div>
        <button
          onClick={handleIngest}
          disabled={ingesting}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium disabled:opacity-50 transition-colors"
        >
          {ingesting ? 'Ingesting...' : 'Fetch News'}
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-white/5 rounded-lg p-1">
        {(['feed', 'digest', 'sources'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              activeTab === tab ? 'bg-white/10 text-white' : 'text-gray-400 hover:text-white'
            }`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {activeTab === 'feed' && (
        <>
          {/* Filters */}
          <div className="flex gap-3 flex-wrap">
            <input
              type="text"
              placeholder="Search articles..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder-gray-500 flex-1 min-w-[200px]"
            />
            <div className="flex gap-1 flex-wrap">
              {Object.keys(CATEGORY_COLORS).map(cat => (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(selectedCategory === cat ? '' : cat)}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                    selectedCategory === cat
                      ? 'text-white'
                      : 'bg-white/5 text-gray-400 hover:text-white'
                  }`}
                  style={selectedCategory === cat ? { backgroundColor: CATEGORY_COLORS[cat] } : {}}
                >
                  {CATEGORY_LABELS[cat] || cat}
                </button>
              ))}
            </div>
          </div>

          {/* Article List */}
          {loading ? (
            <div className="text-center text-gray-400 py-12">Loading...</div>
          ) : articles.length === 0 ? (
            <div className="text-center text-gray-400 py-12">
              No articles found. Click "Fetch News" to ingest from your sources.
            </div>
          ) : (
            <div className="space-y-3">
              {articles.map(article => (
                <div
                  key={article.id}
                  className={`p-4 rounded-xl border transition-colors ${
                    article.is_read
                      ? 'bg-white/[0.02] border-white/5'
                      : 'bg-white/[0.05] border-white/10 hover:bg-white/[0.08]'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span
                          className="px-2 py-0.5 rounded-full text-[10px] font-medium"
                          style={{ backgroundColor: CATEGORY_COLORS[article.category] + '30', color: CATEGORY_COLORS[article.category] }}
                        >
                          {CATEGORY_LABELS[article.category] || article.category}
                        </span>
                        {sentimentLabel(article.sentiment_score)}
                        {article.tickers_json && article.tickers_json.length > 0 && (
                          <div className="flex gap-1">
                            {article.tickers_json.slice(0, 3).map(t => (
                              <span key={t} className="px-1.5 py-0.5 bg-white/10 rounded text-[10px] text-gray-300">
                                ${t}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                      <a
                        href={article.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={() => markRead(article.id)}
                        className={`text-sm font-medium hover:text-indigo-400 transition-colors ${
                          article.is_read ? 'text-gray-400' : 'text-white'
                        }`}
                      >
                        {article.title}
                      </a>
                      {article.summary && (
                        <p className="text-xs text-gray-500 mt-1 line-clamp-2">{article.summary}</p>
                      )}
                      <div className="flex items-center gap-3 mt-2 text-[11px] text-gray-600">
                        {article.author && <span>{article.author}</span>}
                        {article.published_at && (
                          <span>{new Date(article.published_at).toLocaleDateString()}</span>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={() => toggleStar(article.id)}
                      className={`text-lg ${article.is_starred ? 'text-yellow-400' : 'text-gray-600 hover:text-yellow-400'}`}
                    >
                      {article.is_starred ? '\u2605' : '\u2606'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {activeTab === 'digest' && digest && (
        <div className="space-y-6">
          {/* Ticker Activity */}
          {digest.top_tickers.length > 0 && (
            <div className="bg-white/[0.03] rounded-xl p-4 border border-white/5">
              <h3 className="text-sm font-medium text-white mb-3">Most Mentioned Tickers</h3>
              <div className="flex gap-2 flex-wrap">
                {digest.top_tickers.map(({ ticker, count }) => (
                  <span
                    key={ticker}
                    className="px-3 py-1.5 bg-white/5 rounded-full text-xs text-gray-300"
                  >
                    ${ticker} ({count})
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Category Breakdown */}
          {Object.entries(digest.categories).map(([cat, arts]) => (
            <div key={cat} className="bg-white/[0.03] rounded-xl p-4 border border-white/5">
              <div className="flex items-center gap-2 mb-3">
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: CATEGORY_COLORS[cat] }}
                />
                <h3 className="text-sm font-medium text-white">
                  {CATEGORY_LABELS[cat] || cat} ({arts.length})
                </h3>
              </div>
              <div className="space-y-2">
                {arts.slice(0, 5).map((a, i) => (
                  <a
                    key={i}
                    href={a.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block text-xs text-gray-300 hover:text-indigo-400 transition-colors"
                  >
                    {a.title}
                  </a>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'sources' && (
        <div className="space-y-3">
          {sources.map(source => (
            <div key={source.id} className="p-4 bg-white/[0.03] rounded-xl border border-white/5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-white">{source.name}</p>
                  <p className="text-xs text-gray-500">{source.source_type} &middot; {source.article_count} articles</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${source.is_active ? 'bg-green-400' : 'bg-gray-600'}`} />
                  <span className="text-xs text-gray-500">{source.is_active ? 'Active' : 'Inactive'}</span>
                </div>
              </div>
            </div>
          ))}
          {sources.length === 0 && (
            <div className="text-center text-gray-400 py-8">
              No news sources configured. Add sources via the API.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
