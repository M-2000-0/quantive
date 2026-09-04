// ── Sovereign Timeline ───────────────────────────────────────────────
// The signature Quantive element. A horizontal glass ribbon stretching
// 30 years into the future showing:
//   - Debt maturities
//   - Refinancing cliffs
//   - Risk zones
//   - Forecast overlays
//
// This becomes the screenshot everyone shares.

import { useMemo } from 'react';

interface TimelineEvent {
  year: number;
  quarter?: number;
  type: 'maturity' | 'issuance' | 'risk' | 'coupon' | 'forecast' | 'policy';
  amount?: number;
  label: string;
  severity?: 'low' | 'medium' | 'high' | 'critical';
  confidence?: number;
}

interface SovereignTimelineProps {
  events: TimelineEvent[];
  startYear?: number;
  endYear?: number;
  height?: number;
  selectedYear?: number;
  onYearSelect?: (year: number) => void;
}

export default function SovereignTimeline({
  events,
  startYear = 2024,
  endYear = 2054,
  height = 120,
  selectedYear,
  onYearSelect }: SovereignTimelineProps) {
  const totalYears = endYear - startYear;

  const yearEvents = useMemo(() => {
    const map = new Map<number, TimelineEvent[]>();
    for (const evt of events) {
      const existing = map.get(evt.year) || [];
      existing.push(evt);
      map.set(evt.year, existing);
    }
    return map;
  }, [events]);

  const maxAmount = useMemo(() => {
    return Math.max(...events.filter(e => e.amount).map(e => e.amount || 0), 1);
  }, [events]);

  // Find risk cliffs (3+ high/critical events in a 2-year window)
  const riskYears = useMemo(() => {
    const riskSet = new Set<number>();
    for (let y = startYear; y <= endYear; y++) {
      const nearby = events.filter(e =>
        e.year >= y - 1 && e.year <= y + 1 &&
        (e.severity === 'high' || e.severity === 'critical')
      );
      if (nearby.length >= 2) riskSet.add(y);
    }
    return riskSet;
  }, [events, startYear, endYear]);

  const getTypeColor = (type: TimelineEvent['type'], severity?: string) => {
    if (severity === 'critical') return '#b43535';
    if (severity === 'high') return '#9a7520';
    if (severity === 'medium') return '#c8a951';

    switch (type) {
      case 'maturity': return '#b43535';
      case 'issuance': return '#2d7a4f';
      case 'risk': return '#9a7520';
      case 'coupon': return '#515c6d';
      case 'forecast': return '#2563a8';
      case 'policy': return '#c8a951';
      default: return '#6b7280';
    }
  };

  const formatAmount = (amount?: number) => {
    if (!amount) return '';
    if (amount >= 1e9) return `$${(amount / 1e9).toFixed(1)}B`;
    if (amount >= 1e6) return `$${(amount / 1e6).toFixed(0)}M`;
    return `$${amount.toLocaleString()}`;
  };

  return (
    <div className="surface-1" style={{ padding: '16px 20px', overflow: 'hidden' }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 style={{ fontSize: '14px', fontWeight: 600 }}>Sovereign Timeline</h3>
          <p className="data-label" style={{ marginTop: 2 }}>
            {startYear} — {endYear} · {events.length} events · {riskYears.size} risk periods
          </p>
        </div>
        <div className="flex items-center gap-4" style={{ fontSize: '11px' }}>
          <span className="flex items-center gap-1">
            <span style={{ width: 8, height: 8, borderRadius: 2, background: '#b43535', display: 'inline-block' }} />
            Maturity
          </span>
          <span className="flex items-center gap-1">
            <span style={{ width: 8, height: 8, borderRadius: 2, background: '#2d7a4f', display: 'inline-block' }} />
            Issuance
          </span>
          <span className="flex items-center gap-1">
            <span style={{ width: 8, height: 8, borderRadius: 2, background: '#2563a8', display: 'inline-block' }} />
            Forecast
          </span>
          <span className="flex items-center gap-1">
            <span style={{ width: 8, height: 8, borderRadius: 2, background: '#c8a951', display: 'inline-block' }} />
            Policy
          </span>
        </div>
      </div>

      {/* Timeline */}
      <div style={{ position: 'relative', height, overflow: 'hidden' }}>
        {/* Year grid lines */}
        <svg width="100%" height={height} style={{ position: 'absolute', top: 0, left: 0 }}>
          {Array.from({ length: totalYears + 1 }, (_, i) => {
            const x = (i / totalYears) * 100;
            const year = startYear + i;
            const isMajor = year % 5 === 0;
            return (
              <g key={year}>
                <line
                  x1={`${x}%`} y1={0}
                  x2={`${x}%`} y2={height}
                  stroke={isMajor ? 'rgba(0,0,0,0.12)' : 'rgba(0,0,0,0.04)'}
                  strokeWidth={isMajor ? 1 : 0.5}
                />
                {isMajor && (
                  <text
                    x={`${x}%`} y={height - 4}
                    textAnchor="middle"
                    fill="var(--text-tertiary)"
                    fontSize="10"
                    fontFamily="var(--font-mono)"
                    fontWeight="500"
                  >
                    {year}
                  </text>
                )}
              </g>
            );
          })}

          {/* Risk zone shading */}
          {Array.from(riskYears).map(year => {
            const x = ((year - startYear) / totalYears) * 100;
            const w = (1 / totalYears) * 100;
            return (
              <rect
                key={`risk-${year}`}
                x={`${x - w}%`} y={0}
                width={`${w * 3}%`} height={height - 16}
                fill="rgba(180, 53, 53, 0.04)"
                rx={2}
              />
            );
          })}
        </svg>

        {/* Events as bars */}
        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 16 }}>
          {events.map((evt, i) => {
            const x = ((evt.year - startYear) / totalYears) * 100;
            const barHeight = evt.amount ? Math.max(8, (evt.amount / maxAmount) * (height - 40)) : 12;
            const color = getTypeColor(evt.type, evt.severity);
            const isSelected = selectedYear === evt.year;

            return (
              <div
                key={`${evt.year}-${i}`}
                style={{
                  position: 'absolute',
                  left: `${x}%`,
                  bottom: 0,
                  width: Math.max(3, (1 / totalYears) * 100 * 0.6),
                  height: barHeight,
                  background: color,
                  borderRadius: 2,
                  opacity: 0.8,
                  cursor: 'pointer',
                  transition: 'opacity 120ms ease, transform 120ms ease',
                  transform: isSelected ? 'scaleY(1.1)' : undefined,
                  zIndex: isSelected ? 2 : 1 }}
                title={`${evt.year}: ${evt.label}${evt.amount ? ` — ${formatAmount(evt.amount)}` : ''}`}
                onClick={() => onYearSelect?.(evt.year)}
              />
            );
          })}
        </div>

        {/* Now line */}
        <div
          style={{
            position: 'absolute',
            left: `${((2024 - startYear) / totalYears) * 100}%`,
            top: 0,
            bottom: 16,
            width: 2,
            background: 'var(--amber-gold)',
            zIndex: 3 }}
        >
          <div style={{
            position: 'absolute',
            top: -2,
            left: -4,
            width: 10,
            height: 10,
            borderRadius: '50%',
            background: 'var(--amber-gold)' }} />
        </div>
      </div>

      {/* Selected year detail */}
      {selectedYear && yearEvents.has(selectedYear) && (
        <div style={{
          marginTop: 8,
          padding: '8px 12px',
          background: 'var(--surface-2)',
          borderRadius: 4,
          borderLeft: '3px solid var(--amber-gold)' }}>
          <div style={{ fontSize: '12px', fontWeight: 600, marginBottom: 4 }}>
            {selectedYear} — {yearEvents.get(selectedYear)!.length} event{yearEvents.get(selectedYear)!.length > 1 ? 's' : ''}
          </div>
          {yearEvents.get(selectedYear)!.map((evt, i) => (
            <div key={i} style={{ fontSize: '11px', color: 'var(--text-secondary)', display: 'flex', justifyContent: 'space-between' }}>
              <span>
                <span style={{ color: getTypeColor(evt.type, evt.severity), fontWeight: 600 }}>
                  {evt.type.toUpperCase()}
                </span>
                {' · '}{evt.label}
              </span>
              <span className="data-value" style={{ fontSize: '11px' }}>{formatAmount(evt.amount)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
