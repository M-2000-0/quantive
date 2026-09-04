import { useState, useEffect } from 'react';

interface Shortcut {
  keys: string;
  description: string;
  category: string;
}

const SHORTCUTS: Shortcut[] = [
  { keys: '⌘K / Ctrl+K', description: 'Open command palette', category: 'Navigation' },
  { keys: '?', description: 'Toggle shortcuts overlay', category: 'Navigation' },
  { keys: 'Esc', description: 'Close dialogs / overlays', category: 'Navigation' },
  { keys: 'g d', description: 'Go to Dashboard', category: 'Navigation' },
  { keys: 'g p', description: 'Go to Portfolios', category: 'Navigation' },
  { keys: 'g o', description: 'Go to Optimizations', category: 'Navigation' },
  { keys: 'g m', description: 'Go to Market Data', category: 'Navigation' },
  { keys: 'g r', description: 'Go to Risk Dashboard', category: 'Navigation' },
  { keys: '⌘Z / Ctrl+Z', description: 'Undo last edit', category: 'Editing' },
  { keys: '⌘⇧Z / Ctrl+⇧Z', description: 'Redo last edit', category: 'Editing' },
  { keys: '⌘S / Ctrl+S', description: 'Save current form', category: 'Editing' },
  { keys: '/', description: 'Focus search bar', category: 'Editing' },
  { keys: '1-4', description: 'Switch tab in comparison view', category: 'Editing' },
  { keys: 'S', description: 'Swap portfolios in comparison', category: 'Editing' },
  { keys: '← →', description: 'Navigate chart data points', category: 'Charts' },
  { keys: '+ / -', description: 'Zoom in / out on chart', category: 'Charts' },
  { keys: 'E', description: 'Export current chart', category: 'Charts' },
];

export default function KeyboardShortcutOverlay() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Don't trigger if user is typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement || e.target instanceof HTMLSelectElement) return;
      if (e.key === '?' || (e.key === '/' && e.shiftKey)) {
        e.preventDefault();
        setOpen(prev => !prev);
      }
      if (e.key === 'Escape' && open) {
        setOpen(false);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open]);

  if (!open) return null;

  const categories = [...new Set(SHORTCUTS.map(s => s.category))];

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={() => setOpen(false)}>
      <div
        className="glass-strong rounded-3xl shadow-2xl border border-white/30 w-full max-w-lg mx-4 overflow-hidden animate-glass-in"
        onClick={e => e.stopPropagation()}
      >
        <div className="px-6 py-4 border-b border-white/20 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-slate-900">Keyboard Shortcuts</h2>
            <p className="text-xs text-slate-500 mt-0.5">Navigate faster with your keyboard</p>
          </div>
          <button
            onClick={() => setOpen(false)}
            className="rounded-xl p-2 text-slate-400 hover:bg-white/60 hover:text-slate-600 transition-all"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="px-6 py-4 max-h-[60vh] overflow-y-auto space-y-5">
          {categories.map(category => (
            <div key={category}>
              <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-400 mb-2">{category}</h3>
              <div className="space-y-1.5">
                {SHORTCUTS.filter(s => s.category === category).map(shortcut => (
                  <div key={shortcut.keys} className="flex items-center justify-between py-1.5 px-2 rounded-lg hover:bg-white/40 transition-colors">
                    <span className="text-sm text-slate-700">{shortcut.description}</span>
                    <div className="flex items-center gap-1">
                      {shortcut.keys.split(' / ').map((key, i) => (
                        <span key={i} className="flex items-center gap-0.5">
                          {i > 0 && <span className="text-[10px] text-slate-400 mx-0.5">or</span>}
                          {key.split(' ').map((k, j) => (
                            <kbd key={j} className="inline-flex items-center justify-center min-w-[24px] h-6 px-1.5 rounded-lg bg-white/80 border border-slate-200/80 text-[11px] font-mono font-semibold text-slate-700 shadow-[0_1px_2px_rgba(0,0,0,0.06)]">
                              {k}
                            </kbd>
                          ))}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="px-6 py-3 border-t border-white/20 text-center">
          <p className="text-[11px] text-slate-400">Press <kbd className="inline-flex items-center justify-center min-w-[20px] h-5 px-1 rounded bg-white/80 border border-slate-200/80 text-[10px] font-mono font-semibold text-slate-600 shadow-sm">?</kbd> or <kbd className="inline-flex items-center justify-center min-w-[20px] h-5 px-1 rounded bg-white/80 border border-slate-200/80 text-[10px] font-mono font-semibold text-slate-600 shadow-sm">Esc</kbd> to close</p>
        </div>
      </div>
    </div>
  );
}
