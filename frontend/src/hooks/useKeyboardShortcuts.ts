import { useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';

interface ShortcutMap {
  [key: string]: () => void;
}

export function useKeyboardShortcuts(onCommandPaletteOpen: () => void) {
  const navigate = useNavigate();

  const shortcuts: ShortcutMap = {
    'Meta+k': onCommandPaletteOpen,
    'Control+k': onCommandPaletteOpen,
    'g d': () => navigate('/'),
    'g p': () => navigate('/portfolios'),
    'g o': () => navigate('/optimizations/new'),
    'g b': () => navigate('/benchmarks'),
    'g r': () => navigate('/reports'),
    'g a': () => navigate('/audit'),
    'g s': () => navigate('/status'),
    'n p': () => navigate('/portfolios/new'),
    'n o': () => navigate('/optimizations/new'),
  };

  // Track key sequence for multi-key shortcuts
  const pendingKeys = useCallback(() => {
    let buffer = '';
    let timeout: ReturnType<typeof setTimeout>;

    const handler = (e: KeyboardEvent) => {
      // Don't trigger in input/textarea
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        e.target instanceof HTMLSelectElement
      ) {
        return;
      }

      // Command palette shortcut
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        onCommandPaletteOpen();
        return;
      }

      // Build key sequence
      const key = e.key.toLowerCase();
      buffer += key;

      clearTimeout(timeout);
      timeout = setTimeout(() => { buffer = ''; }, 500);

      // Check for matching shortcut
      for (const [pattern, action] of Object.entries(shortcuts)) {
        if (pattern.startsWith('Meta+') || pattern.startsWith('Control+')) continue;
        if (buffer.endsWith(pattern)) {
          e.preventDefault();
          action();
          buffer = '';
          break;
        }
      }
    };

    return handler;
  }, [onCommandPaletteOpen, navigate]);

  useEffect(() => {
    const handler = pendingKeys();
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [pendingKeys]);
}
