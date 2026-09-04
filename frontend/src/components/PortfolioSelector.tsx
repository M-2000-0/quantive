import { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { usePortfolios } from '../stores/portfolio';
import { formatCurrency } from '../utils';

export default function PortfolioSelector() {
  const { portfolios, selectedPortfolio, recentPortfolios, selectPortfolio } = usePortfolios();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const displayList = recentPortfolios.length > 0
    ? recentPortfolios
    : portfolios.slice(0, 5);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-xl glass border border-white/40 hover:border-white/60 text-sm font-medium text-slate-700 hover:bg-white/40 transition-all backdrop-blur-md"
      >
        <svg className="h-4 w-4 text-slate-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 14.15v4.25c0 1.094-.787 2.036-1.872 2.18-2.087.277-4.216.42-6.378.42s-4.291-.143-6.378-.42c-1.085-.144-1.872-1.086-1.872-2.18v-4.25m16.5 0a2.18 2.18 0 00.75-1.661V8.706c0-1.081-.768-2.015-1.837-2.175a48.114 48.114 0 00-3.413-.387m4.5 8.006c-.194.165-.42.295-.673.38A23.978 23.978 0 0112 15.75c-2.648 0-5.195-.429-7.577-1.22a2.016 2.016 0 01-.673-.38m0 0A2.18 2.18 0 013 12.489V8.706c0-1.081.768-2.015 1.837-2.175a48.111 48.111 0 013.413-.387m7.5 0V5.25A2.25 2.25 0 0013.5 3h-3a2.25 2.25 0 00-2.25 2.25v.894m7.5 0a48.667 48.667 0 00-7.5 0" />
        </svg>
        <span className="truncate max-w-[160px]">
          {selectedPortfolio ? selectedPortfolio.name : 'Select Portfolio'}
        </span>
        <svg className={`h-3.5 w-3.5 text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
        </svg>
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 glass-strong rounded-2xl shadow-2xl border border-white/40 z-50 overflow-hidden animate-glass-in">
          {recentPortfolios.length > 0 && (
            <div className="px-3 py-2 border-b border-white/20">
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Recent</span>
            </div>
          )}
          <div className="max-h-64 overflow-y-auto">
            {displayList.map(p => {
              const total = (p.instruments ?? []).reduce((s, i) => s + i.principal_outstanding, 0);
              const isSelected = selectedPortfolio?.id === p.id;
              return (
                <button
                  key={p.id}
                  onClick={() => { selectPortfolio(p.id); setOpen(false); }}
                  className={`w-full text-left px-4 py-3 hover:bg-white/40 transition-colors flex items-center justify-between ${isSelected ? 'bg-blue-50/40' : ''}`}
                >
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-slate-900 truncate">{p.name}</div>
                    <div className="text-xs text-slate-500">{(p.instruments ?? []).length} instruments</div>
                  </div>
                  <div className="text-right ml-3">
                    <div className="text-xs font-bold text-slate-700 tabular-nums">{formatCurrency(total)}</div>
                    {isSelected && <div className="text-[10px] text-blue-600 font-medium">Active</div>}
                  </div>
                </button>
              );
            })}
          </div>
          <div className="border-t border-white/20 px-3 py-2">
            <Link
              to="/portfolios"
              onClick={() => setOpen(false)}
              className="text-xs font-medium text-blue-600 hover:text-blue-700 transition-colors"
            >
              View All Portfolios →
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
