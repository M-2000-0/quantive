import { useState, useMemo } from 'react';

interface Column<T> {
  key: string;
  label: string;
  render?: (value: unknown, row: T) => React.ReactNode;
  width?: string;
  align?: 'left' | 'center' | 'right';
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  onRowClick?: (row: T) => void;
  emptyMessage?: string;
  loading?: boolean;
  compact?: boolean;
}

export default function DataTable<T extends Record<string, unknown>>({
  columns,
  data,
  onRowClick,
  emptyMessage = 'No data available',
  loading = false,
  compact = false,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  const sortedData = useMemo(() => {
    if (!sortKey) return data;
    return [...data].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return 1;
      if (bVal == null) return -1;
      if (aVal < bVal) return sortDir === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
  }, [data, sortKey, sortDir]);

  const cellPadding = compact ? 'px-3 py-2.5' : 'px-4 py-3.5';
  const headerPadding = compact ? 'px-3 py-3' : 'px-4 py-3.5';

  if (loading) {
    return (
      <div className="glass-card overflow-hidden">
        <div className="px-4 py-10 text-center text-sm text-slate-500">Loading…</div>
      </div>
    );
  }

  return (
    <div className="glass-card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/50 bg-white/35 backdrop-blur-xl">
              {columns.map((col) => (
                <th
                  key={col.key}
                  onClick={() => handleSort(col.key)}
                  style={{ width: col.width }}
                  className={`
                    ${headerPadding} text-left text-[11px] font-bold uppercase tracking-widest text-slate-500
                    select-none cursor-pointer hover:bg-white/40 transition-colors
                    ${col.align === 'center' ? 'text-center' : ''}
                    ${col.align === 'right' ? 'text-right' : ''}
                  `}
                >
                  <span className="inline-flex items-center gap-1">
                    {col.label}
                    {sortKey === col.key && (
                      <span className="text-blue-600">
                        {sortDir === 'asc' ? '\u2191' : '\u2193'}
                      </span>
                    )}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-white/30">
            {sortedData.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className={`${cellPadding} text-center text-slate-400 bg-white/20`}
                >
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              sortedData.map((row, rowIdx) => (
                <tr
                  key={rowIdx}
                  onClick={() => onRowClick?.(row)}
                  className={`
                    ${onRowClick ? 'cursor-pointer hover:bg-white/45' : 'hover:bg-white/25'}
                    transition-colors bg-white/20 backdrop-blur-sm
                  `}
                >
                  {columns.map((col) => {
                    const value = row[col.key];
                    return (
                      <td
                        key={col.key}
                        className={`
                          ${cellPadding} text-slate-700
                          ${col.align === 'center' ? 'text-center' : ''}
                          ${col.align === 'right' ? 'text-right' : ''}
                        `}
                      >
                        {col.render ? col.render(value, row) : String(value ?? '')}
                      </td>
                    );
                  })}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
