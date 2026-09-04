import { useState } from 'react';
import type { VersionSnapshot, VersionDiff, FieldDiff } from '../hooks/useVersionHistory';
import { formatDiffValue } from '../hooks/useVersionHistory';

interface VersionHistoryPanelProps {
  snapshots: VersionSnapshot[];
  selectedSnapshotId: string | null;
  onSelectSnapshot: (id: string | null) => void;
  getSnapshotDiff: (id: string) => VersionDiff | null;
  onDeleteSnapshot: (id: string) => void;
  onClearHistory: () => void;
}

function formatTimestamp(ts: number): string {
  const d = new Date(ts);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;

  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit' });
}

function DiffRow({ change }: { change: FieldDiff }) {
  const isInstrument = change.field.startsWith('instrument:');
  return (
    <div className="flex items-start gap-3 py-2 px-3 rounded-lg hover:bg-white/30 transition-colors">
      <div className="flex-shrink-0 mt-0.5">
        {change.oldValue === null ? (
          <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-emerald-100 text-emerald-600 text-xs font-bold">+</span>
        ) : change.newValue === null ? (
          <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-red-100 text-red-600 text-xs font-bold">−</span>
        ) : (
          <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-amber-100 text-amber-600 text-xs font-bold">~</span>
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-slate-700">{change.label}</span>
          {isInstrument && change.instrumentName && (
            <span className="text-[10px] text-slate-400 truncate max-w-[160px]">
              {change.instrumentName}
            </span>
          )}
        </div>
        {change.oldValue !== null && change.newValue !== null ? (
          <div className="flex items-center gap-1.5 mt-0.5 text-[11px]">
            <span className="text-red-500 line-through font-mono">{formatDiffValue(change.oldValue)}</span>
            <span className="text-slate-300">→</span>
            <span className="text-emerald-600 font-mono font-medium">{formatDiffValue(change.newValue)}</span>
          </div>
        ) : change.newValue !== null ? (
          <div className="mt-0.5 text-[11px] text-emerald-600 font-mono font-medium">
            {formatDiffValue(change.newValue)}
          </div>
        ) : (
          <div className="mt-0.5 text-[11px] text-red-500 font-mono">
            {formatDiffValue(change.oldValue)}
          </div>
        )}
      </div>
    </div>
  );
}

function SnapshotCard({
  snapshot,
  isSelected,
  diff,
  index,
  total,
  onSelect,
  onDelete }: {
  snapshot: VersionSnapshot;
  isSelected: boolean;
  diff: VersionDiff | null;
  index: number;
  total: number;
  onSelect: () => void;
  onDelete: () => void;
}) {
  const changeCount = diff?.changes.length ?? 0;

  return (
    <div
      className={`relative rounded-xl border transition-all cursor-pointer ${
        isSelected
          ? 'bg-white/70 border-blue-300/60 shadow-md ring-1 ring-blue-200/30'
          : 'bg-white/30 border-white/40 hover:bg-white/50 hover:border-white/60'
      }`}
      onClick={onSelect}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect(); } }}
      aria-pressed={isSelected}
    >
      <div className="px-3.5 py-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 min-w-0">
            <div className={`w-2 h-2 rounded-full flex-shrink-0 ${index === total - 1 ? 'bg-blue-500' : 'bg-slate-300'}`} />
            <span className="text-xs font-semibold text-slate-800 truncate">{snapshot.label}</span>
          </div>
          <button
            onClick={(e) => { e.stopPropagation(); onDelete(); }}
            className="text-slate-300 hover:text-red-500 transition-colors p-0.5 rounded"
            aria-label={`Delete snapshot: ${snapshot.label}`}
          >
            <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="flex items-center gap-2 mt-1">
          <span className="text-[10px] text-slate-400">{formatTimestamp(snapshot.timestamp)}</span>
          {changeCount > 0 && (
            <span className="text-[10px] font-medium text-blue-600 bg-blue-50/80 px-1.5 py-0.5 rounded-full">
              {changeCount} change{changeCount !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export default function VersionHistoryPanel({
  snapshots,
  selectedSnapshotId,
  onSelectSnapshot,
  getSnapshotDiff,
  onDeleteSnapshot,
  onClearHistory }: VersionHistoryPanelProps) {
  const [showClearConfirm, setShowClearConfirm] = useState(false);

  const selectedDiff = selectedSnapshotId ? getSnapshotDiff(selectedSnapshotId) : null;

  if (snapshots.length === 0) {
    return (
      <div className="glass-card p-6 text-center">
        <div className="w-10 h-10 rounded-xl bg-slate-100 flex items-center justify-center mx-auto mb-3">
          <svg className="h-5 w-5 text-slate-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <p className="text-sm font-medium text-slate-600">No version history yet</p>
        <p className="text-xs text-slate-400 mt-1">Changes will be tracked as you edit this portfolio</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Timeline */}
      <div className="space-y-2">
        {snapshots.map((snap, i) => {
          const diff = getSnapshotDiff(snap.id);
          return (
            <SnapshotCard
              key={snap.id}
              snapshot={snap}
              isSelected={snap.id === selectedSnapshotId}
              diff={diff}
              index={i}
              total={snapshots.length}
              onSelect={() => onSelectSnapshot(snap.id === selectedSnapshotId ? null : snap.id)}
              onDelete={() => onDeleteSnapshot(snap.id)}
            />
          );
        })}
      </div>

      {/* Diff View */}
      {selectedSnapshotId && selectedDiff && (
        <div className="glass-card overflow-hidden animate-glass-in">
          <div className="px-4 py-3 border-b border-white/40 bg-white/30">
            <h4 className="text-xs font-bold uppercase tracking-widest text-slate-500">
              Changes in "{selectedDiff.to.label}"
            </h4>
          </div>
          <div className="divide-y divide-white/20 max-h-[300px] overflow-y-auto">
            {selectedDiff.changes.length === 0 ? (
              <div className="px-4 py-6 text-center text-xs text-slate-400">
                No changes detected
              </div>
            ) : (
              selectedDiff.changes.map((change, ci) => (
                <DiffRow key={ci} change={change} />
              ))
            )}
          </div>
        </div>
      )}

      {/* Clear History */}
      <div className="flex justify-end">
        {showClearConfirm ? (
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">Clear all history?</span>
            <button
              onClick={() => { onClearHistory(); setShowClearConfirm(false); }}
              className="text-xs font-medium text-red-600 hover:text-red-700 transition-colors"
            >
              Yes
            </button>
            <button
              onClick={() => setShowClearConfirm(false)}
              className="text-xs text-slate-400 hover:text-slate-600 transition-colors"
            >
              Cancel
            </button>
          </div>
        ) : (
          <button
            onClick={() => setShowClearConfirm(true)}
            className="text-xs text-slate-400 hover:text-slate-600 transition-colors"
          >
            Clear history
          </button>
        )}
      </div>
    </div>
  );
}
