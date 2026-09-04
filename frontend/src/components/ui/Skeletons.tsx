// ── Skeleton Loading States ──────────────────────────────────────────
// Don't use spinners. Ever.
// Use context-aware skeletons that match the layout shape.

export function TableSkeleton({ rows = 5, cols = 6 }: { rows?: number; cols?: number }) {
  return (
    <div className="surface-1" style={{ padding: 0, overflow: 'hidden' }}>
      <table className="q-table">
        <thead>
          <tr>
            {Array.from({ length: cols }, (_, i) => (
              <th key={i}>
                <div className="skeleton" style={{ height: 12, width: `${60 + Math.random() * 40}%` }} />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }, (_, r) => (
            <tr key={r}>
              {Array.from({ length: cols }, (_, c) => (
                <td key={c}>
                  <div className="skeleton" style={{
                    height: 12,
                    width: c === 0 ? '80%' : c === cols - 1 ? '40%' : `${50 + Math.random() * 30}%`,
                    animationDelay: `${(r * cols + c) * 30}ms`,
                  }} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ChartSkeleton({ height = 200 }: { height?: number }) {
  return (
    <div className="surface-1" style={{ padding: '16px 20px' }}>
      <div className="skeleton" style={{ height: 14, width: '30%', marginBottom: 16 }} />
      <div style={{ height, display: 'flex', alignItems: 'flex-end', gap: 4, padding: '0 8px' }}>
        {Array.from({ length: 24 }, (_, i) => (
          <div
            key={i}
            className="skeleton"
            style={{
              flex: 1,
              height: `${20 + Math.random() * 60}%`,
              borderRadius: '2px 2px 0 0',
              animationDelay: `${i * 40}ms`,
            }}
          />
        ))}
      </div>
    </div>
  );
}

export function CardSkeleton() {
  return (
    <div className="surface-1" style={{ padding: '16px 20px' }}>
      <div className="skeleton" style={{ height: 12, width: '40%', marginBottom: 12 }} />
      <div className="skeleton" style={{ height: 28, width: '60%', marginBottom: 8 }} />
      <div className="skeleton" style={{ height: 10, width: '80%' }} />
    </div>
  );
}

export function StatCardSkeleton() {
  return (
    <div className="surface-1" style={{ padding: '12px 16px' }}>
      <div className="skeleton" style={{ height: 10, width: '50%', marginBottom: 8 }} />
      <div className="skeleton" style={{ height: 24, width: '40%', marginBottom: 6 }} />
      <div className="skeleton" style={{ height: 10, width: '60%' }} />
    </div>
  );
}

export function DashboardSkeleton() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
      {/* Stat cards row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 1 }}>
        {Array.from({ length: 4 }, (_, i) => <StatCardSkeleton key={i} />)}
      </div>
      {/* Main content */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 1 }}>
        <ChartSkeleton height={280} />
        <CardSkeleton />
      </div>
      {/* Table */}
      <TableSkeleton rows={8} cols={7} />
    </div>
  );
}
