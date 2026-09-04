import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useVersionHistory, computeDiff, formatDiffValue } from '../hooks/useVersionHistory';
import { useUndoRedo } from '../hooks/useUndoRedo';
import type { Portfolio } from '../types';

// ─── Test Fixtures ──────────────────────────────────────────────────────────

const makePortfolio = (overrides?: Partial<Portfolio>): Portfolio => ({
  id: 'p-1',
  name: 'Test Portfolio',
  description: 'A test portfolio',
  org_id: 'org-1',
  created_by: 'user-1',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  instruments: [
    {
      id: 'i-1',
      name: 'Bond A',
      instrument_type: 'treasury_bond',
      currency: 'USD',
      principal_outstanding: 1e9,
      coupon_rate: 0.05,
      maturity_date: '2030-01-01',
      issue_date: '2020-01-01',
      is_callable: false,
      call_date: null,
      call_price: null,
      spread_bps: 50,
      created_at: '2024-01-01T00:00:00Z',
    },
    {
      id: 'i-2',
      name: 'Bond B',
      instrument_type: 'floating_rate_note',
      currency: 'EUR',
      principal_outstanding: 5e8,
      coupon_rate: 0.03,
      maturity_date: '2028-06-15',
      issue_date: '2021-06-15',
      is_callable: true,
      call_date: '2026-01-01',
      call_price: 101.5,
      spread_bps: 120,
      created_at: '2024-01-01T00:00:00Z',
    },
  ],
  ...overrides,
});

// ─── computeDiff ────────────────────────────────────────────────────────────

describe('computeDiff', () => {
  it('detects no changes for identical portfolios', () => {
    const p = makePortfolio();
    expect(computeDiff(p, p)).toHaveLength(0);
  });

  it('detects name change', () => {
    const from = makePortfolio();
    const to = makePortfolio({ name: 'Renamed Portfolio' });
    const diff = computeDiff(from, to);
    expect(diff).toHaveLength(1);
    expect(diff[0]!.field).toBe('name');
    expect(diff[0]!.oldValue).toBe('Test Portfolio');
    expect(diff[0]!.newValue).toBe('Renamed Portfolio');
  });

  it('detects description change', () => {
    const from = makePortfolio();
    const to = makePortfolio({ description: 'Updated description' });
    const diff = computeDiff(from, to);
    expect(diff).toHaveLength(1);
    expect(diff[0]!.field).toBe('description');
  });

  it('detects instrument added', () => {
    const from = makePortfolio();
    const to = makePortfolio({
      instruments: [...from.instruments, {
        id: 'i-3',
        name: 'Bond C',
        instrument_type: 'bond',
        currency: 'GBP',
        principal_outstanding: 3e8,
        coupon_rate: 0.04,
        maturity_date: '2032-01-01',
        issue_date: '2022-01-01',
        is_callable: false,
        call_date: null,
        call_price: null,
        spread_bps: 75,
        created_at: '2024-01-01T00:00:00Z',
      }],
    });
    const diff = computeDiff(from, to);
    expect(diff.some(c => c.field === 'instrument:i-3' && c.label === 'Instrument Added')).toBe(true);
  });

  it('detects instrument removed', () => {
    const from = makePortfolio();
    const to = makePortfolio({ instruments: [from.instruments[0]!] });
    const diff = computeDiff(from, to);
    expect(diff.some(c => c.field === 'instrument:i-2' && c.label === 'Instrument Removed')).toBe(true);
  });

  it('detects instrument field change', () => {
    const from = makePortfolio();
    const to = makePortfolio({
      instruments: from.instruments.map(i =>
        i.id === 'i-1' ? { ...i, coupon_rate: 0.06 } : i
      ),
    });
    const diff = computeDiff(from, to);
    expect(diff.some(c => c.field === 'instrument:i-1.coupon_rate' && c.instrumentName === 'Bond A')).toBe(true);
  });

  it('detects multiple instrument changes', () => {
    const from = makePortfolio();
    const to = makePortfolio({
      name: 'New Name',
      instruments: from.instruments.map(i =>
        i.id === 'i-1' ? { ...i, coupon_rate: 0.07, spread_bps: 100 } : i
      ),
    });
    const diff = computeDiff(from, to);
    expect(diff.length).toBeGreaterThanOrEqual(3); // name + 2 instrument changes
  });
});

// ─── formatDiffValue ────────────────────────────────────────────────────────

describe('formatDiffValue', () => {
  it('formats null/undefined', () => {
    expect(formatDiffValue(null)).toBe('(none)');
    expect(formatDiffValue(undefined)).toBe('(none)');
  });

  it('formats booleans', () => {
    expect(formatDiffValue(true)).toBe('Yes');
    expect(formatDiffValue(false)).toBe('No');
  });

  it('formats large numbers with B/M', () => {
    expect(formatDiffValue(1.5e9)).toBe('$1.50B');
    expect(formatDiffValue(250e6)).toBe('$250.00M');
  });

  it('formats small numbers as percentages', () => {
    expect(formatDiffValue(0.05)).toBe('5.00%');
  });

  it('formats regular numbers', () => {
    expect(formatDiffValue(42)).toBe('42');
    expect(formatDiffValue(50)).toBe('50');
  });

  it('formats strings', () => {
    expect(formatDiffValue('hello')).toBe('hello');
  });
});

// ─── useVersionHistory ──────────────────────────────────────────────────────

describe('useVersionHistory', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('starts with empty snapshots', () => {
    const { result } = renderHook(() => useVersionHistory('p-test'));
    expect(result.current.snapshots).toHaveLength(0);
  });

  it('takes snapshots', () => {
    const { result } = renderHook(() => useVersionHistory('p-test'));
    const portfolio = makePortfolio();

    act(() => {
      result.current.takeSnapshot(portfolio, 'Initial load');
    });

    expect(result.current.snapshots).toHaveLength(1);
    expect(result.current.snapshots[0]!.label).toBe('Initial load');
  });

  it('persists snapshots to localStorage', () => {
    const { result } = renderHook(() => useVersionHistory('p-test'));
    const portfolio = makePortfolio();

    act(() => {
      result.current.takeSnapshot(portfolio, 'Save 1');
    });

    const stored = JSON.parse(localStorage.getItem('quantive:version-history:p-test') || '[]');
    expect(stored).toHaveLength(1);
    expect(stored[0].label).toBe('Save 1');
  });

  it('restores snapshots from localStorage on mount', () => {
    const portfolio = makePortfolio();
    const snapshot = {
      id: 'v-existing',
      timestamp: Date.now(),
      label: 'Existing snapshot',
      portfolio,
    };
    localStorage.setItem('quantive:version-history:p-test', JSON.stringify([snapshot]));

    const { result } = renderHook(() => useVersionHistory('p-test'));
    expect(result.current.snapshots).toHaveLength(1);
    expect(result.current.snapshots[0]!.label).toBe('Existing snapshot');
  });

  it('generates diff between snapshots', () => {
    const { result } = renderHook(() => useVersionHistory('p-test'));
    const portfolio1 = makePortfolio();
    const portfolio2 = makePortfolio({ name: 'Updated' });

    act(() => {
      result.current.takeSnapshot(portfolio1, 'Before');
    });
    act(() => {
      result.current.takeSnapshot(portfolio2, 'After');
    });

    const diff = result.current.getLatestDiff();
    expect(diff).not.toBeNull();
    expect(diff!.changes).toHaveLength(1);
    expect(diff!.changes[0]!.field).toBe('name');
  });

  it('getSnapshotDiff returns null for first snapshot', () => {
    const { result } = renderHook(() => useVersionHistory('p-test'));
    const portfolio = makePortfolio();

    let snapshotId = '';
    act(() => {
      snapshotId = result.current.takeSnapshot(portfolio, 'First');
    });

    expect(result.current.getSnapshotDiff(snapshotId)).toBeNull();
  });

  it('deletes snapshots', () => {
    const { result } = renderHook(() => useVersionHistory('p-test'));
    const portfolio = makePortfolio();

    let id1 = '';
    let id2 = '';
    act(() => { id1 = result.current.takeSnapshot(portfolio, 'Snap 1'); });
    act(() => { id2 = result.current.takeSnapshot(portfolio, 'Snap 2'); });

    act(() => {
      result.current.deleteSnapshot(id1);
    });

    expect(result.current.snapshots).toHaveLength(1);
    expect(result.current.snapshots[0]!.id).toBe(id2);
  });

  it('clearHistory removes all snapshots', () => {
    const { result } = renderHook(() => useVersionHistory('p-test'));
    const portfolio = makePortfolio();

    act(() => { result.current.takeSnapshot(portfolio, 'One'); });
    act(() => { result.current.takeSnapshot(portfolio, 'Two'); });

    act(() => {
      result.current.clearHistory();
    });

    expect(result.current.snapshots).toHaveLength(0);
    expect(localStorage.getItem('quantive:version-history:p-test')).toBeNull();
  });
});

// ─── useUndoRedo ────────────────────────────────────────────────────────────

describe('useUndoRedo', () => {
  it('starts with initial state and empty history', () => {
    const { result } = renderHook(() => useUndoRedo('initial'));
    expect(result.current.state).toBe('initial');
    expect(result.current.canUndo).toBe(false);
    expect(result.current.canRedo).toBe(false);
    expect(result.current.historyLength).toBe(0);
  });

  it('push adds state to history', () => {
    const { result } = renderHook(() => useUndoRedo('a'));

    act(() => {
      result.current.push('b', 'Edit 1');
    });

    expect(result.current.state).toBe('b');
    expect(result.current.canUndo).toBe(true);
    expect(result.current.historyLength).toBe(1);
  });

  it('undo restores previous state', () => {
    const { result } = renderHook(() => useUndoRedo('a'));

    act(() => { result.current.push('b', 'Edit 1'); });
    act(() => { result.current.push('c', 'Edit 2'); });

    expect(result.current.state).toBe('c');
    expect(result.current.historyLength).toBe(2);

    act(() => { result.current.undo(); });

    expect(result.current.state).toBe('b');
    expect(result.current.historyLength).toBe(1);
    expect(result.current.redoLength).toBe(1);
  });

  it('redo restores undone state', () => {
    const { result } = renderHook(() => useUndoRedo('a'));

    act(() => { result.current.push('b', 'Edit 1'); });
    act(() => { result.current.push('c', 'Edit 2'); });
    act(() => { result.current.undo(); });

    expect(result.current.state).toBe('b');

    act(() => { result.current.redo(); });

    expect(result.current.state).toBe('c');
  });

  it('push clears redo stack', () => {
    const { result } = renderHook(() => useUndoRedo('a'));

    act(() => { result.current.push('b', 'Edit 1'); });
    act(() => { result.current.push('c', 'Edit 2'); });
    act(() => { result.current.undo(); }); // state = b, redo = [c]

    expect(result.current.canRedo).toBe(true);

    act(() => { result.current.push('d', 'New edit'); }); // clears redo

    expect(result.current.canRedo).toBe(false);
    expect(result.current.state).toBe('d');
  });

  it('undo returns null when nothing to undo', () => {
    const { result } = renderHook(() => useUndoRedo('a'));
    let undone: string | null = null;
    act(() => { undone = result.current.undo(); });
    expect(undone).toBeNull();
    expect(result.current.state).toBe('a');
  });

  it('redo returns null when nothing to redo', () => {
    const { result } = renderHook(() => useUndoRedo('a'));
    let redone: string | null = null;
    act(() => { redone = result.current.redo(); });
    expect(redone).toBeNull();
  });

  it('reset clears all history', () => {
    const { result } = renderHook(() => useUndoRedo('a'));

    act(() => { result.current.push('b', 'Edit 1'); });
    act(() => { result.current.push('c', 'Edit 2'); });

    act(() => { result.current.reset('x'); });

    expect(result.current.state).toBe('x');
    expect(result.current.canUndo).toBe(false);
    expect(result.current.canRedo).toBe(false);
    expect(result.current.historyLength).toBe(0);
  });

  it('respects maxHistory limit', () => {
    const { result } = renderHook(() => useUndoRedo('a', { maxHistory: 3 }));

    act(() => { result.current.push('b', '1'); });
    act(() => { result.current.push('c', '2'); });
    act(() => { result.current.push('d', '3'); });
    act(() => { result.current.push('e', '4'); }); // should evict oldest

    expect(result.current.historyLength).toBe(3);

    // Undo all should stop at 'b' (the oldest kept entry)
    act(() => { result.current.undo(); }); // d
    act(() => { result.current.undo(); }); // c
    act(() => { result.current.undo(); }); // b
    expect(result.current.state).toBe('b');

    act(() => { result.current.undo(); }); // nothing left, stays at b
    expect(result.current.state).toBe('b');
  });

  it('undo returns the label of the undone entry', () => {
    const { result } = renderHook(() => useUndoRedo('a'));

    act(() => { result.current.push('b', 'Edit instrument'); });

    expect(result.current.undoLabel).toBe('Edit instrument');
  });

  it('redo returns the label of the redone entry', () => {
    const { result } = renderHook(() => useUndoRedo('a'));

    act(() => { result.current.push('b', 'Edit instrument'); });
    act(() => { result.current.undo(); });

    expect(result.current.redoLabel).toBe('Edit instrument');
  });

  it('works with complex objects', () => {
    interface State { count: number; items: string[] }
    const initial: State = { count: 0, items: [] };
    const { result } = renderHook(() => useUndoRedo<State>(initial));

    act(() => { result.current.push({ count: 1, items: ['a'] }, 'Add a'); });
    act(() => { result.current.push({ count: 2, items: ['a', 'b'] }, 'Add b'); });

    expect(result.current.state.items).toEqual(['a', 'b']);

    act(() => { result.current.undo(); });
    expect(result.current.state.items).toEqual(['a']);

    act(() => { result.current.redo(); });
    expect(result.current.state.items).toEqual(['a', 'b']);
  });

  it('keyboard shortcut undo calls undo', () => {
    const { result } = renderHook(() => useUndoRedo('a', { enableKeyboardShortcuts: true }));

    act(() => { result.current.push('b', 'Edit 1'); });

    act(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'z', ctrlKey: true }));
    });

    expect(result.current.state).toBe('a');
  });

  it('keyboard shortcut redo calls redo', () => {
    const { result } = renderHook(() => useUndoRedo('a', { enableKeyboardShortcuts: true }));

    act(() => { result.current.push('b', 'Edit 1'); });
    act(() => { result.current.undo(); });

    act(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'z', ctrlKey: true, shiftKey: true }));
    });

    expect(result.current.state).toBe('b');
  });

  it('keyboard shortcuts ignore input elements', () => {
    const { result } = renderHook(() => useUndoRedo('a', { enableKeyboardShortcuts: true }));

    act(() => { result.current.push('b', 'Edit 1'); });

    const input = document.createElement('input');
    document.body.appendChild(input);
    input.focus();

    act(() => {
      input.dispatchEvent(new KeyboardEvent('keydown', { key: 'z', ctrlKey: true, bubbles: true }));
    });

    // Should NOT undo because target is an input
    expect(result.current.state).toBe('b');

    document.body.removeChild(input);
  });
});
