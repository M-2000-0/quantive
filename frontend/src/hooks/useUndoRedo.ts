import { useState, useCallback, useEffect, useRef } from 'react';

interface HistoryEntry<T> {
  state: T;
  label: string;
}

interface UseUndoRedoOptions {
  maxHistory?: number;
  /** If true, registers global Cmd+Z / Cmd+Shift+Z keyboard shortcuts */
  enableKeyboardShortcuts?: boolean;
}

interface UseUndoRedoReturn<T> {
  state: T;
  canUndo: boolean;
  canRedo: boolean;
  undoLabel: string | null;
  redoLabel: string | null;
  push: (newState: T, label?: string) => void;
  undo: () => T | null;
  redo: () => T | null;
  reset: (newState: T) => void;
  historyLength: number;
  redoLength: number;
}

/**
 * Generic undo/redo state manager using a linear history stack.
 *
 * Usage:
 *   const { state, push, undo, redo, canUndo, canRedo } = useUndoRedo(initialState);
 *   // When user makes a change:
 *   push(updatedState, 'Edit instrument');
 *   // Keyboard shortcuts: Cmd+Z to undo, Cmd+Shift+Z to redo
 */
export function useUndoRedo<T>(
  initialState: T,
  options: UseUndoRedoOptions = {}
): UseUndoRedoReturn<T> {
  const { maxHistory = 50, enableKeyboardShortcuts = true } = options;

  const [undoStack, setUndoStack] = useState<HistoryEntry<T>[]>([]);
  const [redoStack, setRedoStack] = useState<HistoryEntry<T>[]>([]);
  const [currentState, setCurrentState] = useState<T>(initialState);

  // Keep a ref to current state for keyboard handler closure
  const stateRef = useRef({ undoStack, redoStack, currentState });
  stateRef.current = { undoStack, redoStack, currentState };

  /**
   * Push a new state onto the history, clearing redo stack.
   */
  const push = useCallback((newState: T, label: string = 'Edit') => {
    setUndoStack(prev => {
      const next = [...prev, { state: stateRef.current.currentState, label }];
      return next.length > maxHistory ? next.slice(-maxHistory) : next;
    });
    setRedoStack([]);
    setCurrentState(newState);
  }, [maxHistory]);

  /**
   * Undo: pop from undo stack, push current to redo, return new current state.
   */
  const undo = useCallback((): T | null => {
    let undone: T | null = null;
    setUndoStack(prev => {
      if (prev.length === 0) return prev;
      const entry = prev[prev.length - 1];
      if (!entry) return prev;

      setCurrentState(entry.state);
      undone = entry.state;

      setRedoStack(redo => [...redo, { state: stateRef.current.currentState, label: entry.label }]);
      return prev.slice(0, -1);
    });
    return undone;
  }, []);

  /**
   * Redo: pop from redo stack, push current to undo, return new current state.
   */
  const redo = useCallback((): T | null => {
    let redone: T | null = null;
    setRedoStack(prev => {
      if (prev.length === 0) return prev;
      const entry = prev[prev.length - 1];
      if (!entry) return prev;

      setCurrentState(entry.state);
      redone = entry.state;

      setUndoStack(undo => [...undo, { state: stateRef.current.currentState, label: entry.label }]);
      return prev.slice(0, -1);
    });
    return redone;
  }, []);

  /**
   * Reset history entirely with a new initial state.
   */
  const reset = useCallback((newState: T) => {
    setUndoStack([]);
    setRedoStack([]);
    setCurrentState(newState);
  }, []);

  // Keyboard shortcuts
  useEffect(() => {
    if (!enableKeyboardShortcuts) return;

    const handler = (e: KeyboardEvent) => {
      // Don't trigger in inputs
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        e.target instanceof HTMLSelectElement
      ) return;

      const isMod = e.metaKey || e.ctrlKey;

      // Cmd+Z / Ctrl+Z = undo
      if (isMod && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        stateRef.current.undoStack.length > 0 && undo();
      }

      // Cmd+Shift+Z / Ctrl+Shift+Z = redo
      if (isMod && e.key === 'z' && e.shiftKey) {
        e.preventDefault();
        stateRef.current.redoStack.length > 0 && redo();
      }

      // Cmd+Y / Ctrl+Y = redo (Windows convention)
      if (isMod && e.key === 'y') {
        e.preventDefault();
        stateRef.current.redoStack.length > 0 && redo();
      }
    };

    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [enableKeyboardShortcuts, undo, redo]);

  const canUndo = undoStack.length > 0;
  const canRedo = redoStack.length > 0;
  const undoLabel = canUndo ? undoStack[undoStack.length - 1]!.label : null;
  const redoLabel = canRedo ? redoStack[redoStack.length - 1]!.label : null;

  return {
    state: currentState,
    canUndo,
    canRedo,
    undoLabel,
    redoLabel,
    push,
    undo,
    redo,
    reset,
    historyLength: undoStack.length,
    redoLength: redoStack.length,
  };
}
