import { useState, useEffect } from 'react';

interface Shortcut {
  category: string;
  shortcuts: Array<{ keys: string[]; description: string }>;
}

const SHORTCUTS: Shortcut[] = [
  {
    category: 'Navigation',
    shortcuts: [
      { keys: ['⌘', 'K'], description: 'Open command palette' },
      { keys: ['⌘', '/'], description: 'Toggle sidebar' },
      { keys: ['G', 'D'], description: 'Go to Dashboard' },
      { keys: ['G', 'P'], description: 'Go to Portfolios' },
      { keys: ['G', 'O'], description: 'Go to Optimizations' },
      { keys: ['G', 'R'], description: 'Go to Reports' },
    ] },
  {
    category: 'Actions',
    shortcuts: [
      { keys: ['⌘', 'N'], description: 'New portfolio' },
      { keys: ['⌘', 'E'], description: 'Export data' },
      { keys: ['⌘', 'S'], description: 'Save changes' },
      { keys: ['⌘', 'Z'], description: 'Undo' },
      { keys: ['⌘', '⇧', 'Z'], description: 'Redo' },
    ] },
  {
    category: 'Table',
    shortcuts: [
      { keys: ['↑', '↓'], description: 'Navigate rows' },
      { keys: ['Enter'], description: 'Open selected row' },
      { keys: ['Space'], description: 'Toggle row selection' },
      { keys: ['⌘', 'A'], description: 'Select all rows' },
      { keys: ['Delete'], description: 'Delete selected rows' },
    ] },
  {
    category: 'General',
    shortcuts: [
      { keys: ['?'], description: 'Show keyboard shortcuts' },
      { keys: ['Escape'], description: 'Close dialog / cancel' },
      { keys: ['⌘', ','], description: 'Open settings' },
      { keys: ['⌘', '.'], description: 'Toggle dark mode' },
    ] },
];

export function useKeyboardShortcutHelp() {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === '?' && !e.metaKey && !e.ctrlKey && !(e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement)) {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      }
      if (e.key === 'Escape') setIsOpen(false);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  return { isOpen, setIsOpen };
}

export default function KeyboardShortcutHelp({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      <div
        className="relative w-full max-w-lg glass-card p-6 animate-glass-in"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-bold text-white">Keyboard Shortcuts</h2>
          <button onClick={onClose} className="text-white/40 hover:text-white text-xl">✕</button>
        </div>

        <div className="space-y-5 max-h-[60vh] overflow-y-auto">
          {SHORTCUTS.map((group) => (
            <div key={group.category}>
              <h3 className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-2">{group.category}</h3>
              <div className="space-y-1">
                {group.shortcuts.map((s) => (
                  <div key={s.description} className="flex items-center justify-between py-1.5">
                    <span className="text-sm text-white/70">{s.description}</span>
                    <div className="flex items-center gap-1">
                      {s.keys.map((key, i) => (
                        <span key={i}>
                          <kbd className="px-2 py-0.5 rounded-lg bg-white/10 border border-white/10 text-[11px] font-mono text-white/80 shadow-sm">
                            {key}
                          </kbd>
                          {i < s.keys.length - 1 && <span className="text-white/20 mx-0.5">+</span>}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        <p className="text-[10px] text-white/30 text-center mt-4">Press ? or Escape to toggle</p>
      </div>
    </div>
  );
}
