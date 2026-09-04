import { useState, useRef, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';

interface SearchSuggestion {
  id: string;
  label: string;
  description: string;
  action: () => void;
  icon: React.ReactNode;
}

// Natural language patterns → route/filter actions
const NL_PATTERNS: Array<{ pattern: RegExp; label: string; route: string; description: string }> = [
  { pattern: /dashboard|home|overview/i, label: 'Dashboard', route: '/dashboard', description: 'Executive dashboard' },
  { pattern: /portfolios?|holdings?|positions?/i, label: 'Portfolios', route: '/portfolios', description: 'Manage portfolios' },
  { pattern: /optim(iz|is)/i, label: 'Optimization', route: '/optimizations/new', description: 'Run new optimization' },
  { pattern: /market|prices?|yield|rates?/i, label: 'Market Data', route: '/market', description: 'Live market data' },
  { pattern: /risk|exposure|var|stress/i, label: 'Risk Dashboard', route: '/risk', description: 'Risk analysis' },
  { pattern: /report|export|pdf|summary/i, label: 'Reports', route: '/reports', description: 'Generate reports' },
  { pattern: /peer|comparison|benchmark|competitor/i, label: 'Peer Comparison', route: '/peers', description: 'Compare with peers' },
  { pattern: /compliance|imf|regulat|audit/i, label: 'Compliance', route: '/compliance', description: 'IMF compliance checks' },
  { pattern: /esg|green|sustainab|climate/i, label: 'ESG / Green Bonds', route: '/esg', description: 'ESG scoring' },
  { pattern: /settings?|preferences?|config|account/i, label: 'Settings', route: '/settings', description: 'Account settings' },
  { pattern: /what.?if|scenario|simulate|model/i, label: 'What-If Analysis', route: '/whatif', description: 'Scenario modeling' },
  { pattern: /maturity|ladder|duration/i, label: 'Maturity Ladder', route: '/maturity', description: 'Maturity analysis' },
  { pattern: /event|news|impact|geopolit/i, label: 'Event Impact', route: '/events', description: 'Event impact analysis' },
  { pattern: /adaptive|cause.?effect|pipeline/i, label: 'Adaptive Dashboard', route: '/adaptive', description: 'Cause & effect view' },
  { pattern: /execut|trade|rollback/i, label: 'Execution Log', route: '/executions', description: 'Trade execution log' },
  { pattern: /notif|alert|bell/i, label: 'Notifications', route: '/notifications', description: 'Alert preferences' },
  { pattern: /billing|invoice|plan|subscription/i, label: 'Billing', route: '/billing', description: 'Billing & plans' },
  { pattern: /admin|team|users?|rbac/i, label: 'Admin Panel', route: '/admin', description: 'User management' },
  { pattern: /purchas|acquisition|buy/i, label: 'Purchases', route: '/purchases', description: 'Purchase tracker' },
  { pattern: /opportunit|refinanc|signal/i, label: 'Opportunities', route: '/opportunities', description: 'Refinance signals' },
  { pattern: /explain|interpret|why|reason/i, label: 'Explainability', route: '/explain', description: 'AI decision explanations' },
  { pattern: /rating|credit|moody|fitch|sp/i, label: 'Rating Simulator', route: '/ratings', description: 'Credit rating simulator' },
  { pattern: /intel|threat|cyber|attack/i, label: 'Risk Intelligence', route: '/risk-intel', description: 'Threat intelligence' },
  { pattern: /security|mfa|2fa|auth/i, label: 'Security', route: '/security', description: 'Security dashboard' },
];

function parseNaturalLanguage(query: string): SearchSuggestion[] {
  if (!query.trim()) return [];

  const suggestions: SearchSuggestion[] = [];
  const seen = new Set<string>();

  for (const np of NL_PATTERNS) {
    if (np.pattern.test(query) && !seen.has(np.route)) {
      seen.add(np.route);
      suggestions.push({
        id: np.route,
        label: np.label,
        description: np.description,
        action: () => {}, // handled externally
        icon: (
          <svg className="h-4 w-4 text-slate-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6z" />
          </svg>
        ) });
    }
  }

  return suggestions.slice(0, 6);
}

export default function SmartSearch() {
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const suggestions = useMemo(() => parseNaturalLanguage(query), [query]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.key === '/' && !e.shiftKey && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        inputRef.current?.focus();
        setOpen(true);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(i => Math.min(i + 1, suggestions.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(i => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && suggestions[selectedIndex]) {
      navigate(suggestions[selectedIndex].id);
      setQuery('');
      setOpen(false);
    } else if (e.key === 'Escape') {
      setOpen(false);
      inputRef.current?.blur();
    }
  };

  return (
    <div className="relative">
      <div
        className={`flex items-center gap-2 px-3 py-2 rounded-xl border transition-all duration-200 ${
          open
            ? 'glass border-blue-300/60 shadow-lg shadow-blue-500/10 ring-2 ring-blue-400/20'
            : 'glass border-white/40 hover:border-white/60'
        }`}
      >
        <svg className="h-4 w-4 text-slate-400 shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
        </svg>
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={e => { setQuery(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 200)}
          onKeyDown={handleKeyDown}
          placeholder='Search or type "show me USD bonds"...'
          className="flex-1 bg-transparent text-sm text-slate-700 placeholder:text-slate-400 outline-none"
        />
        <kbd className="hidden sm:inline-flex items-center justify-center min-w-[20px] h-5 px-1 rounded bg-white/80 border border-slate-200/80 text-[10px] font-mono font-semibold text-slate-400">/</kbd>
      </div>

      {open && suggestions.length > 0 && (
        <div className="absolute top-full left-0 right-0 mt-2 glass-strong rounded-2xl shadow-2xl border border-white/30 z-50 overflow-hidden animate-glass-in">
          <div className="px-3 py-2 border-b border-white/20">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
              {suggestions.length} result{suggestions.length !== 1 ? 's' : ''}
            </span>
          </div>
          <div className="max-h-80 overflow-y-auto">
            {suggestions.map((s, i) => (
              <button
                key={s.id}
                onClick={() => { navigate(s.id); setQuery(''); setOpen(false); }}
                className={`w-full text-left px-4 py-3 flex items-center gap-3 transition-colors ${
                  i === selectedIndex ? 'bg-blue-50/50' : 'hover:bg-white/40'
                }`}
              >
                {s.icon}
                <div className="min-w-0">
                  <div className="text-sm font-medium text-slate-900">{s.label}</div>
                  <div className="text-xs text-slate-500">{s.description}</div>
                </div>
                <svg className="h-4 w-4 text-slate-300 ml-auto shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                </svg>
              </button>
            ))}
          </div>
          <div className="px-4 py-2 border-t border-white/20 flex items-center gap-4 text-[10px] text-slate-400">
            <span>↑↓ navigate</span>
            <span>↵ select</span>
            <span>esc close</span>
          </div>
        </div>
      )}
    </div>
  );
}
