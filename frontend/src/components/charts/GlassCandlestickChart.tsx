import { ComposedChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';

interface CandlestickData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

interface GlassCandlestickChartProps {
  data: CandlestickData[];
  height?: number;
  title?: string;
  formatValue?: (value: number) => string;
}

function CandlestickBar(props: Record<string, unknown>) {
  const { x, y, width, height: barHeight, payload } = props as {
    x: number; y: number; width: number; height: number; payload: CandlestickData;
  };
  if (!payload) return null;

  const { open, close, high, low } = payload;
  const bullish = close >= open;
  const color = bullish ? '#10b981' : '#ef4444';

  // Simple approximation for wick and body positions
  const bodyTop = Math.min(open, close);
  const bodyBottom = Math.max(open, close);
  const range = high - low || 1;

  return (
    <g>
      {/* Wick */}
      <line
        x1={x + width / 2}
        y1={y}
        x2={x + width / 2}
        y2={y + barHeight}
        stroke={color}
        strokeWidth={1}
      />
      {/* Body */}
      <rect
        x={x + 2}
        y={y + ((bodyBottom - high) / range) * barHeight}
        width={width - 4}
        height={Math.max(((bodyBottom - bodyTop) / range) * barHeight, 2)}
        fill={color}
        fillOpacity={0.85}
        rx={1}
      />
    </g>
  );
}

export default function GlassCandlestickChart({
  data, height = 300, title, formatValue,
}: GlassCandlestickChartProps) {
  const chartData = data.map((d) => ({
    ...d,
    range: d.high - d.low,
    mid: (d.high + d.low) / 2,
  }));

  const avgClose = data.reduce((sum, d) => sum + d.close, 0) / data.length;

  return (
    <div className="glass-card p-4">
      {title && <h3 className="text-sm font-semibold text-white/80 mb-3">{title}</h3>}
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis dataKey="date" stroke="rgba(255,255,255,0.3)" tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.5)' }} />
          <YAxis domain={['auto', 'auto']} stroke="rgba(255,255,255,0.3)" tick={{ fontSize: 11, fill: 'rgba(255,255,255,0.5)' }} tickFormatter={formatValue} />
          <Tooltip
            contentStyle={{ background: 'rgba(15,23,42,0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, backdropFilter: 'blur(20px)' }}
            formatter={(value: number, name: string) => [formatValue ? formatValue(value) : value, name]}
          />
          <ReferenceLine y={avgClose} stroke="rgba(255,255,255,0.2)" strokeDasharray="3 3" />
          <Bar dataKey="range" shape={<CandlestickBar />} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
