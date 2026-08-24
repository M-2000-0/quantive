import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';

interface CommandItem {
  id: string;
  label: string;
  category: string;
  shortcut?: string;
  action: () => void;
  icon?: React.ReactNode;
}

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

const NAV_ITEMS: Array<{ label: string; path: string; category: string }> = [
  { label: 'Dashboard', path: '/', category: 'Navigation' },
  { label: 'Portfolios', path: '/portfolios', category: 'Navigation' },
  { label: 'New Portfolio', path: '/portfolios/new', category: 'Navigation' },
  { label: 'Run Optimization', path: '/optimizations/new', category: 'Navigation' },
  { label: 'Benchmarks', path: '/benchmarks', category: 'Navigation' },
  { label: 'Reports', path: '/reports', category: 'Navigation' },
  { label: 'Audit Log', path: '/audit', category: 'Navigation' },
  { label: 'System Status', path: '/status', category: 'Navigation' },
];

export default function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const items: CommandItem[] = [
    ...NAV_ITEMS.map((item) => ({
      id: item.path,
      label: item.label,
      category: item.category,
      action: () => { navigate(item.path); onClose(); },
    })),
    {
      id: 'theme-toggle',
      label: 'Toggle Dark Mode',
      category: 'Appearance',
      shortcut: '⌘D',
      action: () => {
        const html = document.documentElement;
        html.classList.toggle('dark');
        onClose();
      },
    },
  ];

  const filtered = query
    ? items.filter((item) =>
        item.label.toLowerCase().includes(query.toLowerCase()) ||
        item.category.toLowerCase().includes(query.toLowerCase())
      )
    : items;

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => Math.min(prev + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => Math.max(prev - 1, 0));
    } else if (e.key === 'Enter' && filtered[selectedIndex]) {
      filtered[selectedIndex].action();
    } else if (e.key === 'Escape') {
      onClose();
    }
  }, [filtered, selectedIndex, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[9999] flex items-start justify-center pt-[20vh]" onClick={onClose}>
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" />
      <div
        className="relative w-full max-w-lg bg-white dark:bg-slate-800 rounded-xl shadow-2xl border border-slate-200 dark:border-slate-700 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center border-b border-slate-200 dark:border-slate-700 px-4">
          <svg className="h-5 w-5 text-slate-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
          </svg>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search commands, pages, actions..."
            className="flex-1 px-3 py-4 text-sm bg-transparent text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none"
          />
          <kbd className="hidden sm:inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium text-slate-400 bg-slate-100 dark:bg-slate-700">
            ESC
          </kbd>
        </div>

        <div className="max-h-80 overflow-y-auto py-2">
          {filtered.length === 0 ? (
            <div className="px-4 py-8 text-center text-sm text-slate-500">
              No results found for "{query}"
            </div>
          ) : (
            <>
              {['Navigation', 'Appearance'].map((category) => {
                const categoryItems = filtered.filter((item) => item.category === category);
                if (categoryItems.length === 0) return null;
                return (
                  <div key={category}>
                    <div className="px-4 py-1.5 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                      {category}
                    </div>
                    {categoryItems.map((item) => {
                      const globalIndex = filtered.indexOf(item);
                      return (
                        <button
                          key={item.id}
                          onClick={item.action}
                          className={`w-full flex items-center justify-between px-4 py-2.5 text-sm transition-colors ${
                            globalIndex === selectedIndex
                              ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                              : 'text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700/50'
                          }`}
                        >
                          <span>{item.label}</span>
                          {item.shortcut && (
                            <kbd className="text-[10px] text-slate-400 bg-slate-100 dark:bg-slate-700 px-1.5 py-0.5 rounded">
                              {item.shortcut}
                            </kbd>
                          )}
                        </button>
                      );
                    })}
                  </div>
                );
              })}
            </>
          )}
        </div>

        <div className="border-t border-slate-200 dark:border-slate-700 px-4 py-2 flex items-center gap-4 text-[10px] text-slate-400">
          <span>↑↓ navigate</span>
          <span>↵ select</span>
          <span>esc close</span>
        </div>
      </div>
    </div>
  );
}
