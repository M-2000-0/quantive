import { useState, useCallback, useRef } from 'react';
import type { Portfolio, DebtInstrument } from '../types';

/**
 * A single snapshot of portfolio state with metadata.
 */
export interface VersionSnapshot {
  id: string;
  timestamp: number;
  label: string;
  portfolio: Portfolio;
}

/**
 * A detected field change between two snapshots.
 */
export interface FieldDiff {
  field: string;
  label: string;
  oldValue: unknown;
  newValue: unknown;
  instrumentName?: string;
}

/**
 * A complete diff between two consecutive snapshots.
 */
export interface VersionDiff {
  from: VersionSnapshot;
  to: VersionSnapshot;
  changes: FieldDiff[];
}

const SNAPSHOT_KEY_PREFIX = 'quantive:version-history:';

function generateId(): string {
  return `v-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function deepClone<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj));
}

// Fields we track for changes on the portfolio itself
const PORTFOLIO_TRACKED_FIELDS: Array<{ key: keyof Portfolio; label: string }> = [
  { key: 'name', label: 'Portfolio Name' },
  { key: 'description', label: 'Description' },
];

// Fields we track for changes on instruments
const INSTRUMENT_TRACKED_FIELDS: Array<{ key: keyof DebtInstrument; label: string }> = [
  { key: 'name', label: 'Name' },
  { key: 'instrument_type', label: 'Type' },
  { key: 'currency', label: 'Currency' },
  { key: 'principal_outstanding', label: 'Principal' },
  { key: 'coupon_rate', label: 'Coupon Rate' },
  { key: 'maturity_date', label: 'Maturity Date' },
  { key: 'spread_bps', label: 'Spread (bps)' },
  { key: 'is_callable', label: 'Callable' },
];

/**
 * Compare two snapshots and return a list of field-level changes.
 */
export function computeDiff(from: Portfolio, to: Portfolio): FieldDiff[] {
  const changes: FieldDiff[] = [];

  // Portfolio-level fields
  for (const { key, label } of PORTFOLIO_TRACKED_FIELDS) {
    if (from[key] !== to[key]) {
      changes.push({ field: key, label, oldValue: from[key], newValue: to[key] });
    }
  }

  // Instrument changes: additions, removals, modifications
  const fromMap = new Map<string, DebtInstrument>(from.instruments.map(i => [i.id, i]));
  const toMap = new Map<string, DebtInstrument>(to.instruments.map(i => [i.id, i]));

  // Removed instruments
  for (const [id, inst] of fromMap) {
    if (!toMap.has(id)) {
      changes.push({
        field: `instrument:${id}`,
        label: 'Instrument Removed',
        oldValue: inst.name,
        newValue: null,
      });
    }
  }

  // Added instruments
  for (const [id, inst] of toMap) {
    if (!fromMap.has(id)) {
      changes.push({
        field: `instrument:${id}`,
        label: 'Instrument Added',
        oldValue: null,
        newValue: inst.name,
      });
    }
  }

  // Modified instruments
  for (const [id, toInst] of toMap) {
    const fromInst = fromMap.get(id);
    if (!fromInst) continue;

    for (const { key, label } of INSTRUMENT_TRACKED_FIELDS) {
      if (fromInst[key] !== toInst[key]) {
        changes.push({
          field: `instrument:${id}.${key}`,
          label,
          oldValue: fromInst[key],
          newValue: toInst[key],
          instrumentName: toInst.name,
        });
      }
    }
  }

  return changes;
}

/**
 * Format a diff value for display.
 */
export function formatDiffValue(value: unknown): string {
  if (value === null || value === undefined) return '(none)';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (typeof value === 'number') {
    if (Math.abs(value) >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
    if (Math.abs(value) >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
    if (Math.abs(value) < 1 && value > 0) return `${(value * 100).toFixed(2)}%`;
    return value.toLocaleString();
  }
  return String(value);
}

/**
 * Hook to manage version history for a portfolio.
 * Stores snapshots in state and optionally persists to localStorage.
 */
export function useVersionHistory(portfolioId: string | undefined) {
  const [snapshots, setSnapshots] = useState<VersionSnapshot[]>(() => {
    if (!portfolioId || typeof window === 'undefined') return [];
    try {
      const raw = localStorage.getItem(`${SNAPSHOT_KEY_PREFIX}${portfolioId}`);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  });

  const [selectedSnapshotId, setSelectedSnapshotId] = useState<string | null>(null);

  const persist = useCallback((next: VersionSnapshot[]) => {
    if (!portfolioId || typeof window === 'undefined') return;
    try {
      // Keep max 50 snapshots per portfolio
      const trimmed = next.slice(-50);
      localStorage.setItem(`${SNAPSHOT_KEY_PREFIX}${portfolioId}`, JSON.stringify(trimmed));
    } catch { /* quota exceeded */ }
  }, [portfolioId]);

  /**
   * Take a snapshot of the current portfolio state with a label.
   */
  const takeSnapshot = useCallback((portfolio: Portfolio, label: string) => {
    const snapshot: VersionSnapshot = {
      id: generateId(),
      timestamp: Date.now(),
      label,
      portfolio: deepClone(portfolio),
    };
    setSnapshots(prev => {
      const next = [...prev, snapshot];
      persist(next);
      return next;
    });
    return snapshot.id;
  }, [persist]);

  /**
   * Delete a snapshot by id.
   */
  const deleteSnapshot = useCallback((snapshotId: string) => {
    setSnapshots(prev => {
      const next = prev.filter(s => s.id !== snapshotId);
      persist(next);
      return next;
    });
  }, [persist]);

  /**
   * Get diffs between two consecutive snapshots.
   */
  const getDiffBetween = useCallback((fromId: string, toId: string): VersionDiff | null => {
    const fromSnap = snapshots.find(s => s.id === fromId);
    const toSnap = snapshots.find(s => s.id === toId);
    if (!fromSnap || !toSnap) return null;

    const changes = computeDiff(fromSnap.portfolio, toSnap.portfolio);
    return { from: fromSnap, to: toSnap, changes };
  }, [snapshots]);

  /**
   * Get diffs between the previous snapshot and the latest one.
   */
  const getLatestDiff = useCallback((): VersionDiff | null => {
    if (snapshots.length < 2) return null;
    return getDiffBetween(snapshots[snapshots.length - 2]!.id, snapshots[snapshots.length - 1]!.id);
  }, [snapshots, getDiffBetween]);

  /**
   * Get diffs for a specific snapshot vs the one before it.
   */
  const getSnapshotDiff = useCallback((snapshotId: string): VersionDiff | null => {
    const idx = snapshots.findIndex(s => s.id === snapshotId);
    if (idx <= 0) return null;
    return getDiffBetween(snapshots[idx - 1]!.id, snapshots[idx]!.id);
  }, [snapshots, getDiffBetween]);

  return {
    snapshots,
    takeSnapshot,
    deleteSnapshot,
    getDiffBetween,
    getLatestDiff,
    getSnapshotDiff,
    selectedSnapshotId,
    setSelectedSnapshotId,
    clearHistory: useCallback(() => {
      setSnapshots([]);
      if (portfolioId && typeof window !== 'undefined') {
        localStorage.removeItem(`${SNAPSHOT_KEY_PREFIX}${portfolioId}`);
      }
    }, [portfolioId]),
  };
}
