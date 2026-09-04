interface BoxPlotData {
  label: string;
  min: number;
  q1: number;
  median: number;
  q3: number;
  max: number;
  outliers?: number[];
}

interface GlassBoxPlotProps {
  data: BoxPlotData[];
  height?: number;
  title?: string;
  formatValue?: (value: number) => string;
}

export default function GlassBoxPlot({
  data, height = 250, title, formatValue,
}: GlassBoxPlotProps) {
  const allValues = data.flatMap((d) => [d.min, d.max, ...(d.outliers || [])]);
  const dataMin = Math.min(...allValues);
  const dataMax = Math.max(...allValues);
  const range = dataMax - dataMin || 1;

  const padding = 40;
  const chartWidth = 600;
  const chartHeight = height - padding * 2;
  const boxWidth = Math.min(Math.floor((chartWidth - padding * 2) / data.length) * 0.6, 60);

  function yScale(value: number): number {
    return padding + chartHeight - ((value - dataMin) / range) * chartHeight;
  }

  return (
    <div className="glass-card p-4 overflow-x-auto">
      {title && <h3 className="text-sm font-semibold text-white/80 mb-3">{title}</h3>}
      <svg width="100%" viewBox={`0 0 ${chartWidth} ${height}`} className="overflow-visible">
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((pct) => {
          const val = dataMin + pct * range;
          const y = yScale(val);
          return (
            <g key={pct}>
              <line x1={padding} y1={y} x2={chartWidth - padding} y2={y} stroke="rgba(255,255,255,0.06)" strokeDasharray="3 3" />
              <text x={padding - 5} y={y + 4} textAnchor="end" fill="rgba(255,255,255,0.3)" fontSize={10}>
                {formatValue ? formatValue(val) : val.toFixed(1)}
              </text>
            </g>
          );
        })}

        {/* Box plots */}
        {data.map((d, idx) => {
          const cx = padding + ((idx + 0.5) / data.length) * (chartWidth - padding * 2);
          const halfBox = boxWidth / 2;

          return (
            <g key={d.label}>
              {/* Whiskers */}
              <line x1={cx} y1={yScale(d.max)} x2={cx} y2={yScale(d.q3)} stroke="rgba(255,255,255,0.4)" strokeWidth={1} />
              <line x1={cx} y1={yScale(d.q1)} x2={cx} y2={yScale(d.min)} stroke="rgba(255,255,255,0.4)" strokeWidth={1} />

              {/* Whisker caps */}
              <line x1={cx - halfBox * 0.4} y1={yScale(d.max)} x2={cx + halfBox * 0.4} y2={yScale(d.max)} stroke="rgba(255,255,255,0.4)" strokeWidth={1} />
              <line x1={cx - halfBox * 0.4} y1={yScale(d.min)} x2={cx + halfBox * 0.4} y2={yScale(d.min)} stroke="rgba(255,255,255,0.4)" strokeWidth={1} />

              {/* IQR Box */}
              <rect
                x={cx - halfBox}
                y={yScale(d.q3)}
                width={boxWidth}
                height={yScale(d.q1) - yScale(d.q3)}
                rx={4}
                fill="#3b82f6"
                fillOpacity={0.25}
                stroke="#3b82f6"
                strokeWidth={1.5}
                strokeOpacity={0.6}
              />

              {/* Median line */}
              <line
                x1={cx - halfBox}
                y1={yScale(d.median)}
                x2={cx + halfBox}
                y2={yScale(d.median)}
                stroke="white"
                strokeWidth={2}
                strokeOpacity={0.8}
              />

              {/* Outliers */}
              {(d.outliers || []).map((val, oi) => (
                <circle key={oi} cx={cx} cy={yScale(val)} r={3} fill="#ef4444" fillOpacity={0.8} />
              ))}

              {/* Label */}
              <text x={cx} y={height - 8} textAnchor="middle" fill="rgba(255,255,255,0.5)" fontSize={10}>
                {d.label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
