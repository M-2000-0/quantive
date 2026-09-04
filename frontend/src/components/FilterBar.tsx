import { useState } from 'react';
import { Button } from './ui';
import { Search } from 'lucide-react';

interface FilterOption {
  key: string;
  label: string;
  type: 'text' | 'select' | 'date' | 'dateRange' | 'number' | 'tags';
  options?: Array<{ label: string; value: string }>;
  placeholder?: string;
}

interface FilterBarProps {
  filters: FilterOption[];
  values: Record<string, unknown>;
  onChange: (key: string, value: unknown) => void;
  onReset?: () => void;
  onApply?: () => void;
}

export default function FilterBar({ filters, values, onChange, onReset, onApply }: FilterBarProps) {
  const [expanded, setExpanded] = useState(false);
  const activeCount = Object.values(values).filter((v) => v !== '' && v !== null && v !== undefined && v !== 'all').length;

  return (
    <div className="glass-card p-3">
      <div className="flex items-center justify-between mb-2">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-2 text-xs text-white/60 hover:text-white/80"
        >
          <Search className="w-5 h-5" />
          <span>Filters</span>
          {activeCount > 0 && (
            <span className="px-1.5 py-0.5 rounded-full bg-blue-500 text-white text-[10px] font-bold">{activeCount}</span>
          )}
          <span className="text-white/30">{expanded ? '▲' : '▼'}</span>
        </button>
        {activeCount > 0 && onReset && (
          <button onClick={onReset} className="text-[10px] text-red-400/60 hover:text-red-400">Clear all</button>
        )}
      </div>

      {expanded && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-2 border-t border-white/5">
          {filters.map((f) => (
            <div key={f.key}>
              <label className="text-[10px] text-white/40 uppercase tracking-wider mb-1 block">{f.label}</label>
              {f.type === 'text' && (
                <input
                  type="text"
                  placeholder={f.placeholder || 'Search...'}
                  value={(values[f.key] as string) || ''}
                  onChange={(e) => onChange(f.key, e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-1.5 text-xs text-white placeholder:text-white/30 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
                />
              )}
              {f.type === 'select' && (
                <select
                  value={(values[f.key] as string) || 'all'}
                  onChange={(e) => onChange(f.key, e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none"
                >
                  <option value="all">All</option>
                  {f.options?.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              )}
              {f.type === 'date' && (
                <input
                  type="date"
                  value={(values[f.key] as string) || ''}
                  onChange={(e) => onChange(f.key, e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none"
                />
              )}
              {f.type === 'dateRange' && (
                <div className="flex gap-1">
                  <input
                    type="date"
                    value={(values[`${f.key}_start`] as string) || ''}
                    onChange={(e) => onChange(`${f.key}_start`, e.target.value)}
                    className="w-1/2 bg-white/5 border border-white/10 rounded-xl px-2 py-1.5 text-[10px] text-white focus:outline-none"
                  />
                  <input
                    type="date"
                    value={(values[`${f.key}_end`] as string) || ''}
                    onChange={(e) => onChange(`${f.key}_end`, e.target.value)}
                    className="w-1/2 bg-white/5 border border-white/10 rounded-xl px-2 py-1.5 text-[10px] text-white focus:outline-none"
                  />
                </div>
              )}
              {f.type === 'number' && (
                <input
                  type="number"
                  placeholder={f.placeholder || '0'}
                  value={(values[f.key] as number) || ''}
                  onChange={(e) => onChange(f.key, parseFloat(e.target.value) || 0)}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-1.5 text-xs text-white placeholder:text-white/30 focus:outline-none"
                />
              )}
              {f.type === 'tags' && f.options && (
                <div className="flex flex-wrap gap-1">
                  {f.options.map((opt) => (
                    <button
                      key={opt.value}
                      onClick={() => {
                        const current = (values[f.key] as string[]) || [];
                        const next = current.includes(opt.value)
                          ? current.filter((v) => v !== opt.value)
                          : [...current, opt.value];
                        onChange(f.key, next);
                      }}
                      className={`px-2 py-0.5 rounded-full text-[10px] border transition-colors ${
                        ((values[f.key] as string[]) || []).includes(opt.value)
                          ? 'bg-blue-500/20 border-blue-500/40 text-blue-300'
                          : 'bg-white/5 border-white/10 text-white/50'
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
          {onApply && (
            <div className="flex items-end">
              <Button variant="primary" size="sm" onClick={onApply}>Apply</Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
