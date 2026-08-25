import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';

interface CommandItem {
  id: string;
  label: string;
  category: string;
  hint?: string;
  shortcut?: string;
  action: () => void;
}

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

const PAGE_ITEMS: Array<{ label: string; path: string; hint: string }> = [
  { label: 'Dashboard', path: '/', hint: 'Overview' },
  { label: 'Portfolios', path: '/portfolios', hint: 'Debt portfolios' },
  { label: 'New Portfolio', path: '/portfolios/new', hint: 'Create portfolio' },
  { label: 'Run Optimization', path: '/optimizations/new', hint: 'New optimization' },
  { label: 'Benchmarks', path: '/benchmarks', hint: 'Solver benchmarks' },
  { label: 'Reports', path: '/reports', hint: 'Export & reports' },
  { label: 'Market Data', path: '/market', hint: 'Yield curve, FX, rates' },
  { label: 'Risk Dashboard', path: '/risk', hint: 'Portfolio risk' },
  { label: 'What-If Playground', path: '/whatif', hint: 'Scenario analysis' },
  { label: 'AI Advisor', path: '/advisor', hint: 'Ask Quantive AI' },
  { label: 'Peer Comparison', path: '/peers', hint: 'Country peers' },
  { label: 'IMF Compliance', path: '/compliance', hint: 'DSA / MTDS / GFS' },
  { label: 'Explainability', path: '/explain', hint: 'Model explain' },
  { label: 'Risk Intelligence', path: '/risk-intel', hint: 'Sanctions, liquidity' },
  { label: 'Maturity Ladder', path: '/maturity', hint: 'Cashflow & ladder' },
  { label: 'ESG / Green', path: '/esg', hint: 'Green bonds' },
  { label: 'Rating Simulator', path: '/ratings', hint: 'S&P / Moody’s' },
  { label: 'Audit Log', path: '/audit', hint: 'Activity trail' },
  { label: 'Security', path: '/security', hint: 'Threats & health' },
  { label: 'System Status', path: '/status', hint: 'Health & version' },
  { label: 'Settings', path: '/settings', hint: 'Account & org' },
];

// ── Fuzzy scoring ──────────────────────────────────────────────────────────
function fuzzyScore(query: string, target: string): number {
  const q = query.toLowerCase();
  const t = target.toLowerCase();
  if (t.includes(q)) {
    // bonus for prefix / exact
    const idx = t.indexOf(q);
    return 100 - idx + q.length * 2;
  }
  // subsequence match
  let qi = 0;
  let score = 0;
  let consecutive = 0;
  for (let i = 0; i < t.length && qi < q.length; i++) {
    if (t[i] === q[qi]) {
      qi++;
      consecutive++;
      score += 5 + consecutive * 2;
      // bonus if at word boundary
      if (i === 0 || t[i - 1] === ' ' || t[i - 1] === '/' || t[i - 1] === '-') score += 3;
    } else {
      consecutive = 0;
      score -= 0.5;
    }
  }
  if (qi !== q.length) return -1;
  return score;
}

export default function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Dynamic data: portfolios & optimizations (loaded lazily)
  const [portfolioItems, setPortfolioItems] = useState<Array<{ id: string; name: string }>>([]);
  const [optimizationItems, setOptimizationItems] = useState<Array<{ id: string; name: string; status: string }>>([]);

  useEffect(() => {
    if (!isOpen) return;
    let cancelled = false;
    // Fetch portfolios
    api.portfolios.list({ page_size: 20 } as unknown as Record<string, string | number | undefined>).then((res: unknown) => {
      if (cancelled) return;
      const data = res as { data?: Array<{ id: string; name: string }> } | Array<{ id: string; name: string }>;
      const arr = Array.isArray(data) ? data : (data.data || []);
      setPortfolioItems(arr.slice(0, 8).map(p => ({ id: p.id, name: p.name })));
    }).catch(() => {
      if (!cancelled) setPortfolioItems([
        { id: 'demo-1', name: 'Sovereign Bond Portfolio' },
        { id: 'demo-2', name: 'External Debt — USD' },
      ]);
    });
    // Fetch optimizations
    api.optimizations.list({ page_size: 10 } as unknown as Record<string, string | number | undefined>).then((res: unknown) => {
      if (cancelled) return;
      const data = res as { data?: Array<{ id: string; name: string; status: string }> } | Array<{ id: string; name: string; status: string }>;
      const arr = Array.isArray(data) ? data : (data.data || []);
      setOptimizationItems(arr.slice(0, 8).map(o => ({ id: o.id, name: o.name || o.id.slice(0, 8), status: o.status })));
    }).catch(() => {
      if (!cancelled) setOptimizationItems([
        { id: 'opt-demo', name: 'Q4 Optimization', status: 'completed' },
      ]);
    });
    return () => { cancelled = true; };
  }, [isOpen]);

  const staticItems: CommandItem[] = useMemo(() => {
    const pages: CommandItem[] = PAGE_ITEMS.map(p => ({
      id: `page:${p.path}`,
      label: p.label,
      category: 'Pages',
      hint: p.hint,
      action: () => { navigate(p.path); onClose(); },
    }));
    const portfolios: CommandItem[] = portfolioItems.map(p => ({
      id: `portfolio:${p.id}`,
      label: p.name,
      category: 'Portfolios',
      hint: `Open portfolio ${p.name}`,
      action: () => { navigate(`/portfolios/${p.id}`); onClose(); },
    }));
    const optimizations: CommandItem[] = optimizationItems.map(o => ({
      id: `opt:${o.id}`,
      label: o.name,
      category: 'Optimizations',
      hint: o.status,
      action: () => { navigate(`/optimizations/${o.id}`); onClose(); },
    }));
    const actions: CommandItem[] = [
      {
        id: 'theme-toggle',
        label: 'Toggle theme',
        category: 'Actions',
        shortcut: '⌘⇧T',
        hint: 'Light / Dark',
        action: () => {
          document.documentElement.classList.toggle('dark');
          // also toggle via stored preference if available
          try {
            const cur = localStorage.getItem('quantive_theme') as string;
            if (cur === 'dark') localStorage.setItem('quantive_theme', 'light');
            else if (cur === 'light') localStorage.setItem('quantive_theme', 'dark');
          } catch { /* */ }
          onClose();
        },
      },
      {
        id: 'cmd-settings',
        label: 'Open Settings',
        category: 'Actions',
        hint: '⌘K → settings',
        action: () => { navigate('/settings'); onClose(); },
      },
    ];
    return [...pages, ...portfolios, ...optimizations, ...actions];
  }, [navigate, onClose, portfolioItems, optimizationItems]);

  const filtered = useMemo(() => {
    if (!query.trim()) return staticItems;
    const q = query.trim();
    const scored = staticItems
      .map(item => {
        const text = `${item.label} ${item.hint || ''} ${item.category}`;
        const s = fuzzyScore(q, text);
        // also keep raw label exact bonus
        const labelScore = fuzzyScore(q, item.label);
        const best = Math.max(s, labelScore);
        return { item, score: best };
      })
      .filter(x => x.score >= 0)
      .sort((a, b) => b.score - a.score)
      .map(x => x.item);
    return scored;
  }, [staticItems, query]);

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 40);
    }
  }, [isOpen]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  // Keep selected item in view
  useEffect(() => {
    if (!listRef.current) return;
    const el = listRef.current.querySelector(`[data-index="${selectedIndex}"]`);
    if (el) el.scrollIntoView({ block: 'nearest' });
  }, [selectedIndex]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => Math.min(prev + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => Math.max(prev - 1, 0));
    } else if (e.key === 'Enter' && filtered[selectedIndex]) {
      e.preventDefault();
      filtered[selectedIndex].action();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  }, [filtered, selectedIndex, onClose]);

  if (!isOpen) return null;

  const categories = ['Pages', 'Portfolios', 'Optimizations', 'Actions'] as const;

  return (
    <div className="fixed inset-0 z-[9999] flex items-start justify-center pt-[14vh] px-4" onClick={onClose} role="dialog" aria-modal="true" aria-label="Command palette">
      {/* backdrop */}
      <div className="fixed inset-0 bg-slate-900/30 backdrop-blur-[6px]" />
      {/* liquid orb decoration behind modal */}
      <div className="pointer-events-none fixed inset-0 flex items-start justify-center pt-[14vh] px-4">
        <div className="w-full max-w-[640px] h-[420px] -mt-10 rounded-[32px] bg-gradient-to-br from-blue-400/10 via-violet-400/10 to-cyan-400/10 blur-2xl" />
      </div>

      <div
        className="relative w-full max-w-[640px] glass-heavy overflow-hidden animate-glass-in shadow-[0_24px_64px_rgba(0,0,0,0.18)] border border-white/40 dark:border-white/10"
        onClick={e => e.stopPropagation()}
      >
        {/* search input */}
        <div className="flex items-center gap-3 px-5 border-b border-white/20 dark:border-white/10 bg-white/40 dark:bg-slate-900/30 backdrop-blur-xl">
          <svg className="h-5 w-5 text-slate-400 shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={1.7} stroke="currentColor" aria-hidden>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.2-5.2m0 0A7.5 7.5 0 105.2 5.2a7.5 7.5 0 0010.6 10.6z" />
          </svg>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search pages, portfolios, optimizations…"
            className="flex-1 py-4 text-[14px] bg-transparent text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none"
            aria-label="Search commands"
          />
          <kbd className="hidden sm:inline-flex items-center px-2 py-1 rounded-lg text-[10px] font-semibold tracking-wide text-slate-500 bg-white/70 dark:bg-white/10 border border-white/40 dark:border-white/10 backdrop-blur-md">
            ESC
          </kbd>
        </div>

        {/* results */}
        <div ref={listRef} className="max-h-[380px] overflow-y-auto py-2 bg-white/60 dark:bg-slate-900/50 backdrop-blur-xl">
          {filtered.length === 0 ? (
            <div className="px-5 py-10 text-center">
              <div className="mx-auto w-10 h-10 rounded-xl bg-white/60 dark:bg-white/10 flex items-center justify-center border border-white/40 text-slate-400 mb-3">⌘</div>
              <p className="text-sm text-slate-600 dark:text-slate-300">No results for “{query}”</p>
              <p className="text-xs text-slate-400 mt-1">Try pages, portfolio names, or optimization IDs</p>
            </div>
          ) : (
            categories.map(cat => {
              const catItems = filtered.filter(i => i.category === cat);
              if (catItems.length === 0) return null;
              return (
                <div key={cat} className="px-2">
                  <div className="px-3 py-2 text-[10px] font-bold tracking-[0.14em] text-slate-400 uppercase">
                    {cat} <span className="normal-case font-medium tracking-normal text-slate-400/70">— {catItems.length}</span>
                  </div>
                  <div className="space-y-1 pb-1">
                    {catItems.map(item => {
                      const globalIndex = filtered.indexOf(item);
                      const active = globalIndex === selectedIndex;
                      return (
                        <button
                          key={item.id}
                          data-index={globalIndex}
                          onClick={item.action}
                          onMouseEnter={() => setSelectedIndex(globalIndex)}
                          className={`w-full flex items-center justify-between gap-3 rounded-xl px-3 py-2.5 text-left transition-all border ${
                            active
                              ? 'bg-white/85 dark:bg-white/10 border-white/60 dark:border-white/15 shadow-sm backdrop-blur-md translate-x-[1px]'
                              : 'bg-transparent border-transparent hover:bg-white/50 dark:hover:bg-white/5 hover:border-white/30 text-slate-700 dark:text-slate-200'
                          }`}
                        >
                          <span className="flex items-center gap-3 min-w-0">
                            <span className={`h-7 w-7 rounded-lg flex items-center justify-center text-[11px] font-bold shrink-0 border ${active ? 'bg-gradient-to-br from-blue-500 to-indigo-500 text-white border-white/20 shadow' : 'bg-white/60 dark:bg-white/10 text-slate-500 border-white/40'}`}>
                              {item.category === 'Portfolios' ? '◧' : item.category === 'Optimizations' ? '⬢' : item.category === 'Pages' ? '◩' : '⚡'}
                            </span>
                            <span className="min-w-0">
                              <span className={`block text-sm font-medium truncate ${active ? 'text-slate-900 dark:text-white' : 'text-slate-800 dark:text-slate-100'}`}>{item.label}</span>
                              {item.hint && <span className="block text-xs text-slate-500 dark:text-slate-400 truncate">{item.hint}</span>}
                            </span>
                          </span>
                          {item.shortcut && (
                            <kbd className="hidden sm:inline-flex text-[10px] font-medium text-slate-500 bg-white/70 dark:bg-white/10 px-1.5 py-0.5 rounded border border-white/40 backdrop-blur-md shrink-0">
                              {item.shortcut}
                            </kbd>
                          )}
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })
          )}
        </div>

        <div className="border-t border-white/20 dark:border-white/10 px-4 py-2.5 flex items-center gap-4 text-[11px] text-slate-500 dark:text-slate-400 bg-white/50 dark:bg-slate-900/30 backdrop-blur-xl">
          <span className="inline-flex items-center gap-1.5"><kbd className="px-1.5 py-0.5 rounded border bg-white/70 dark:bg-white/10 text-[10px]">↑↓</kbd> navigate</span>
          <span className="inline-flex items-center gap-1.5"><kbd className="px-1.5 py-0.5 rounded border bg-white/70 dark:bg-white/10 text-[10px]">↵</kbd> select</span>
          <span className="inline-flex items-center gap-1.5"><kbd className="px-1.5 py-0.5 rounded border bg-white/70 dark:bg-white/10 text-[10px]">esc</kbd> close</span>
          <span className="ml-auto hidden sm:inline text-slate-400">⌘K to open anywhere</span>
        </div>
      </div>
    </div>
  );
}
