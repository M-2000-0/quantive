interface SkeletonTextProps {
  lines?: number;
  className?: string;
}

export function SkeletonText({ lines = 3, className = '' }: SkeletonTextProps) {
  return (
    <div className={`space-y-2 ${className}`} aria-busy="true" aria-label="Loading">
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className={`h-4 bg-slate-100 rounded animate-pulse ${
            i === lines - 1 ? 'w-3/4' : 'w-full'
          }`}
        />
      ))}
    </div>
  );
}

interface SkeletonCardProps {
  className?: string;
}

export function SkeletonCard({ className = '' }: SkeletonCardProps) {
  return (
    <div
      className={`bg-white border border-slate-200 rounded-lg p-6 shadow-sm ${className}`}
      aria-busy="true"
      aria-label="Loading"
    >
      <div className="flex items-center gap-3 mb-4">
        <div className="h-10 w-10 bg-slate-100 rounded-lg animate-pulse" />
        <div className="flex-1">
          <div className="h-4 bg-slate-100 rounded w-1/3 mb-2 animate-pulse" />
          <div className="h-3 bg-slate-100 rounded w-1/4 animate-pulse" />
        </div>
      </div>
      <div className="space-y-2">
        <div className="h-4 bg-slate-100 rounded w-full animate-pulse" />
        <div className="h-4 bg-slate-100 rounded w-5/6 animate-pulse" />
        <div className="h-4 bg-slate-100 rounded w-2/3 animate-pulse" />
      </div>
    </div>
  );
}

interface SkeletonTableProps {
  rows?: number;
  cols?: number;
  className?: string;
}

export function SkeletonTable({ rows = 5, cols = 4, className = '' }: SkeletonTableProps) {
  return (
    <div className={`bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden ${className}`} aria-busy="true" aria-label="Loading">
      <div className="border-b border-slate-200 bg-slate-50 px-4 py-3">
        <div className="flex gap-4">
          {Array.from({ length: cols }).map((_, i) => (
            <div key={i} className="h-4 bg-slate-200 rounded animate-pulse flex-1" />
          ))}
        </div>
      </div>
      {Array.from({ length: rows }).map((_, rowIdx) => (
        <div
          key={rowIdx}
          className="border-b border-slate-100 px-4 py-3 last:border-b-0"
        >
          <div className="flex gap-4">
            {Array.from({ length: cols }).map((_, colIdx) => (
              <div
                key={colIdx}
                className={`h-4 bg-slate-100 rounded animate-pulse flex-1 ${
                  colIdx === 0 ? 'w-1/4' : ''
                }`}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
