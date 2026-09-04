import { useMemo } from 'react';

interface SkeletonLoaderProps {
  layout?: 'dashboard' | 'list' | 'detail' | 'chart' | 'form';
  rows?: number;
  className?: string;
}

function SkeletonBar({ width, height = 'h-3', className = '' }: { width: string; height?: string; className?: string }) {
  return <div className={`skeleton ${height} ${width} rounded-lg ${className}`} />;
}

function StatCardSkeleton() {
  return (
    <div className="glass p-5 space-y-3">
      <SkeletonBar width="w-20" height="h-3" />
      <SkeletonBar width="w-28" height="h-7" />
      <SkeletonBar width="w-16" height="h-2" />
    </div>
  );
}

function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="glass overflow-hidden">
      <div className="px-6 py-3 border-b border-white/20 bg-white/20">
        <SkeletonBar width="w-40" height="h-4" />
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="px-6 py-4 border-b border-white/10 flex items-center gap-4">
          <div className="w-8 h-8 rounded-lg bg-white/30 animate-pulse" />
          <div className="flex-1 space-y-2">
            <SkeletonBar width="w-48" height="h-3" />
            <SkeletonBar width="w-32" height="h-2" />
          </div>
          <SkeletonBar width="w-20" height="h-4" />
        </div>
      ))}
    </div>
  );
}

function ChartSkeleton() {
  return (
    <div className="glass p-6 space-y-4">
      <SkeletonBar width="w-36" height="h-4" />
      <div className="flex items-end gap-2 h-40 pt-4">
        {[40, 65, 55, 80, 45, 70, 60, 75, 50, 85, 55, 65].map((h, i) => (
          <div key={i} className="flex-1 bg-gradient-to-t from-blue-200/40 to-blue-100/20 rounded-t-lg animate-pulse" style={{ height: `${h}%` }} />
        ))}
      </div>
    </div>
  );
}

export default function SkeletonLoader({ layout = 'dashboard', rows = 5, className = '' }: SkeletonLoaderProps) {
  const content = useMemo(() => {
    switch (layout) {
      case 'dashboard':
        return (
          <>
            {/* Header */}
            <div className="flex items-center justify-between mb-8">
              <div className="space-y-2">
                <SkeletonBar width="w-48" height="h-7" />
                <SkeletonBar width="w-64" height="h-3" />
              </div>
              <SkeletonBar width="w-32" height="h-4" />
            </div>
            {/* Stat cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              {Array.from({ length: 4 }).map((_, i) => <StatCardSkeleton key={i} />)}
            </div>
            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-8">
              <ChartSkeleton />
              <ChartSkeleton />
            </div>
            {/* Table */}
            <TableSkeleton rows={rows} />
          </>
        );
      case 'list':
        return (
          <>
            <div className="flex items-center justify-between mb-6">
              <SkeletonBar width="w-40" height="h-7" />
              <SkeletonBar width="w-28" height="h-9" />
            </div>
            <TableSkeleton rows={rows} />
          </>
        );
      case 'detail':
        return (
          <>
            <div className="space-y-2 mb-6">
              <SkeletonBar width="w-20" height="h-3" />
              <SkeletonBar width="w-64" height="h-7" />
              <SkeletonBar width="w-96" height="h-3" />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              {Array.from({ length: 4 }).map((_, i) => <StatCardSkeleton key={i} />)}
            </div>
            <TableSkeleton rows={rows} />
          </>
        );
      case 'chart':
        return (
          <div className="space-y-4">
            <ChartSkeleton />
            <ChartSkeleton />
          </div>
        );
      case 'form':
        return (
          <div className="glass p-6 space-y-4">
            <SkeletonBar width="w-40" height="h-6" />
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="space-y-2">
                <SkeletonBar width="w-24" height="h-3" />
                <SkeletonBar width="w-full" height="h-10" />
              </div>
            ))}
            <SkeletonBar width="w-28" height="h-9" />
          </div>
        );
    }
  }, [layout, rows]);

  return (
    <div className={`px-8 py-6 max-w-[1440px] mx-auto animate-pulse ${className}`}>
      {content}
    </div>
  );
}
