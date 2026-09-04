interface GlassGaugeChartProps {
  value: number;
  min?: number;
  max?: number;
  title?: string;
  subtitle?: string;
  size?: number;
  color?: string;
  thresholds?: Array<{ value: number; color: string }>;
  formatValue?: (value: number) => string;
}

export default function GlassGaugeChart({
  value, min = 0, max = 100, title, subtitle, size = 180, color = '#c8a951', thresholds, formatValue,
}: GlassGaugeChartProps) {
  const normalized = Math.min(Math.max((value - min) / (max - min), 0), 1);
  const startAngle = -225;
  const endAngle = 45;
  const totalArc = endAngle - startAngle;
  const currentAngle = startAngle + normalized * totalArc;

  const r = size / 2 - 15;
  const cx = size / 2;
  const cy = size / 2;

  function polarToCartesian(angle: number) {
    const rad = (angle * Math.PI) / 180;
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
  }

  function describeArc(start: number, end: number) {
    const s = polarToCartesian(start);
    const e = polarToCartesian(end);
    const largeArc = end - start > 180 ? 1 : 0;
    return `M ${s.x} ${s.y} A ${r} ${r} 0 ${largeArc} 1 ${e.x} ${e.y}`;
  }

  const bgColor = 'rgba(255, 255, 255, 0.06)';
  const arcColor = thresholds
    ? [...thresholds].reverse().find((t) => value >= t.value)?.color || color
    : color;

  return (
    <div className="glass-card" style={{ padding: 16, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      {title && (
        <h3 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', marginBottom: 8, letterSpacing: '-0.01em' }}>
          {title}
        </h3>
      )}
      <svg width={size} height={size * 0.65} viewBox={`0 0 ${size} ${size * 0.75}`}>
        {/* Background arc */}
        <path d={describeArc(startAngle, endAngle)} fill="none" stroke={bgColor} strokeWidth={12} strokeLinecap="round" />
        {/* Value arc */}
        <path
          d={describeArc(startAngle, currentAngle)}
          fill="none"
          stroke={arcColor}
          strokeWidth={12}
          strokeLinecap="round"
          style={{ transition: 'all 0.6s cubic-bezier(0.16, 1, 0.3, 1)', filter: `drop-shadow(0 0 6px ${arcColor}40)` }}
        />
        {/* Needle dot */}
        {(() => {
          const needle = polarToCartesian(currentAngle);
          return (
            <circle cx={needle.x} cy={needle.y} r={5} fill="white" opacity={0.9} style={{ filter: 'drop-shadow(0 0 4px rgba(255,255,255,0.3))' }} />
          );
        })()}
        {/* Center value */}
        <text x={cx} y={cy - 5} textAnchor="middle" fill="var(--text)" fontSize={size * 0.15} fontWeight={700} letterSpacing="-0.03em">
          {formatValue ? formatValue(value) : value.toFixed(1)}
        </text>
        {/* Min/Max labels */}
        <text x={cx - r * 0.7} y={cy + 20} textAnchor="middle" fill="var(--text3)" fontSize={10}>{min}</text>
        <text x={cx + r * 0.7} y={cy + 20} textAnchor="middle" fill="var(--text3)" fontSize={10}>{max}</text>
      </svg>
      {subtitle && <p style={{ fontSize: 11, color: 'var(--text3)', marginTop: 4 }}>{subtitle}</p>}
    </div>
  );
}
