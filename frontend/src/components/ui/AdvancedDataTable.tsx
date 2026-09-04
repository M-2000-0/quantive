import { Settings } from 'lucide-react';
import { useState, useMemo, useCallback } from 'react';

interface Column<T> {
  key: string;
  label: string;
  sortable?: boolean;
  width?: string;
  render?: (value: unknown, row: T) => React.ReactNode;
  hidden?: boolean;
}

interface AdvancedDataTableProps<T extends Record<string, unknown>> {
  columns: Column<T>[];
  data: T[];
  pageSize?: number;
  selectable?: boolean;
  onSelectionChange?: (selected: T[]) => void;
  bulkActions?: Array<{ label: string; icon?: string; onClick: (selected: T[]) => void; variant?: 'default' | 'danger' }>;
  emptyMessage?: string;
  onExport?: (data: T[], format: string) => void;
  searchable?: boolean;
  searchPlaceholder?: string;
  onRowClick?: (row: T) => void;
  density?: 'compact' | 'normal' | 'comfortable';
}

export default function AdvancedDataTable<T extends Record<string, unknown>>({
  columns: allColumns, data, pageSize = 25, selectable = false, onSelectionChange, bulkActions = [],
  emptyMessage = 'No data found', searchable = false, searchPlaceholder = 'Search...', onRowClick, density = 'normal',
}: AdvancedDataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [search, setSearch] = useState('');
  const [hiddenCols, setHiddenCols] = useState<Set<string>>(new Set(allColumns.filter((c) => c.hidden).map((c) => c.key)));

  const densityPad = density === 'compact' ? 'px-3 py-1.5' : density === 'comfortable' ? 'px-4 py-3.5' : 'px-3 py-2.5';

  const columns = useMemo(() => allColumns.filter((c) => !hiddenCols.has(c.key)), [allColumns, hiddenCols]);

  const filteredData = useMemo(() => {
    if (!search) return data;
    const q = search.toLowerCase();
    return data.filter((row) => Object.values(row).some((v) => String(v).toLowerCase().includes(q)));
  }, [data, search]);

  const sortedData = useMemo(() => {
    if (!sortKey) return filteredData;
    return [...filteredData].sort((a, b) => {
      const av = a[sortKey], bv = b[sortKey];
      const cmp = String(av).localeCompare(String(bv), undefined, { numeric: true });
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [filteredData, sortKey, sortDir]);

  const totalPages = Math.ceil(sortedData.length / pageSize);
  const pagedData = sortedData.slice(page * pageSize, (page + 1) * pageSize);

  const toggleSort = useCallback((key: string) => {
    setSortKey((prev) => {
      if (prev === key) {
        setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
        return key;
      }
      setSortDir('asc');
      return key;
    });
  }, []);

  const toggleSelectAll = useCallback(() => {
    if (selected.size === pagedData.length) {
      setSelected(new Set());
      onSelectionChange?.([]);
    } else {
      const newSet = new Set(pagedData.map((_, i) => page * pageSize + i));
      setSelected(newSet);
      onSelectionChange?.(pagedData);
    }
  }, [pagedData, page, pageSize, selected.size, onSelectionChange]);

  const toggleSelectRow = useCallback((idx: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      const selectedRows = Array.from(next).map((i) => sortedData[i]).filter(Boolean);
      onSelectionChange?.(selectedRows);
      return next;
    });
  }, [sortedData, onSelectionChange]);

  const toggleColumn = (key: string) => {
    setHiddenCols((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  return (
    <div className="glass-card overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center justify-between p-3 border-b border-white/5">
        <div className="flex items-center gap-2">
          {searchable && (
            <input
              type="text"
              placeholder={searchPlaceholder}
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(0); }}
              className="bg-white/5 border border-white/10 rounded-xl px-3 py-1.5 text-sm text-white placeholder:text-white/30 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
            />
          )}
          {selected.size > 0 && bulkActions.length > 0 && (
            <div className="flex items-center gap-2 ml-2">
              <span className="text-xs text-white/50">{selected.size} selected</span>
              {bulkActions.map((action) => (
                <button
                  key={action.label}
                  onClick={() => {
                    const selectedRows = Array.from(selected).map((i) => sortedData[i]).filter(Boolean);
                    action.onClick(selectedRows);
                  }}
                  className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                    action.variant === 'danger'
                      ? 'bg-red-500/20 text-red-300 hover:bg-red-500/30'
                      : 'bg-white/10 text-white/70 hover:bg-white/20'
                  }`}
                >
                  {action.icon} {action.label}
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          {/* Column toggle */}
          <div className="relative group">
            <button className="p-1.5 rounded-lg bg-white/5 text-white/50 hover:text-white/80 text-xs"><Settings className="w-4 h-4" /></button>
            <div className="absolute right-0 top-full mt-1 bg-slate-900 border border-white/10 rounded-xl p-2 shadow-xl z-50 hidden group-hover:block min-w-[150px]">
              {allColumns.map((col) => (
                <label key={col.key} className="flex items-center gap-2 px-2 py-1 rounded hover:bg-white/5 cursor-pointer text-xs text-white/70">
                  <input
                    type="checkbox"
                    checked={!hiddenCols.has(col.key)}
                    onChange={() => toggleColumn(col.key)}
                    className="accent-blue-500"
                  />
                  {col.label}
                </label>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/10">
              {selectable && (
                <th className={`${densityPad} w-10`}>
                  <input type="checkbox" checked={selected.size === pagedData.length && pagedData.length > 0} onChange={toggleSelectAll} className="accent-blue-500" />
                </th>
              )}
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={`${densityPad} text-left text-xs font-semibold text-white/50 uppercase tracking-wider ${col.sortable ? 'cursor-pointer hover:text-white/80' : ''}`}
                  style={{ width: col.width }}
                  onClick={() => col.sortable && toggleSort(col.key)}
                >
                  <span className="flex items-center gap-1">
                    {col.label}
                    {col.sortable && sortKey === col.key && (
                      <span className="text-blue-400">{sortDir === 'asc' ? '↑' : '↓'}</span>
                    )}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pagedData.length === 0 ? (
              <tr>
                <td colSpan={columns.length + (selectable ? 1 : 0)} className={`${densityPad} text-center text-white/40 text-sm`}>
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              pagedData.map((row, idx) => {
                const globalIdx = page * pageSize + idx;
                return (
                  <tr
                    key={idx}
                    onClick={() => onRowClick?.(row)}
                    className={`border-b border-white/5 transition-colors ${
                      selected.has(globalIdx) ? 'bg-blue-500/10' : 'hover:bg-white/[0.03]'
                    } ${onRowClick ? 'cursor-pointer' : ''}`}
                  >
                    {selectable && (
                      <td className={densityPad} onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={selected.has(globalIdx)}
                          onChange={() => toggleSelectRow(globalIdx)}
                          className="accent-blue-500"
                        />
                      </td>
                    )}
                    {columns.map((col) => (
                      <td key={col.key} className={`${densityPad} text-sm text-white/80`}>
                        {col.render ? col.render(row[col.key], row) : String(row[col.key] ?? '')}
                      </td>
                    ))}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between p-3 border-t border-white/5">
          <span className="text-xs text-white/40">
            Showing {page * pageSize + 1}–{Math.min((page + 1) * pageSize, sortedData.length)} of {sortedData.length}
          </span>
          <div className="flex items-center gap-1">
            <button onClick={() => setPage(0)} disabled={page === 0} className="px-2 py-1 rounded text-xs text-white/50 hover:text-white disabled:opacity-30">‹‹</button>
            <button onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0} className="px-2 py-1 rounded text-xs text-white/50 hover:text-white disabled:opacity-30">‹</button>
            {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
              const start = Math.max(0, Math.min(page - 2, totalPages - 5));
              const p = start + i;
              if (p >= totalPages) return null;
              return (
                <button
                  key={p}
                  onClick={() => setPage(p)}
                  className={`px-2.5 py-1 rounded text-xs font-medium ${
                    p === page ? 'bg-white/10 text-white' : 'text-white/40 hover:text-white/70'
                  }`}
                >
                  {p + 1}
                </button>
              );
            })}
            <button onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1} className="px-2 py-1 rounded text-xs text-white/50 hover:text-white disabled:opacity-30">›</button>
            <button onClick={() => setPage(totalPages - 1)} disabled={page >= totalPages - 1} className="px-2 py-1 rounded text-xs text-white/50 hover:text-white disabled:opacity-30">››</button>
          </div>
        </div>
      )}
    </div>
  );
}
