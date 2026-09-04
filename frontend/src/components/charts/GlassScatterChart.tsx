import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ZAxis } from 'recharts';

interface DataPoint {
  [key: string]: string | number;
}

interface GlassScatterChartProps {
  data: DataPoint[];
  xKey: string;
  yKey: string;
  zKey?: string;
  color?: string;
  height?: number;
  title?: string;
  xLabel?: string;
  yLabel?: string;
  formatX?: (value: number) => string;
  formatY?: (value: number) => string;
}

export default function GlassScatterChart({
  data, xKey, yKey, zKey, color = '#3b82f6', height = 300, title, xLabel, yLabel, formatX, formatY,
}: GlassScatterChartProps) {
  return (
    <div className="glass-card p-4">
      {title && <h3 className="text-sm font-semibold text-white/80 mb-3">{title}</h3>}
      <ResponsiveContainer width="100%" height={height}>
        <ScatterChart margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis
            dataKey={xKey}
            name={xLabel || xKey}
            stroke="rgba(255,255,255,0.3)"
            tick={{ fontSize: 11, fill: 'rgba(255,255,255,0.5)' }}
            tickFormatter={formatX}
            label={xLabel ? { value: xLabel, position: 'insideBottom', offset: -5, fill: 'rgba(255,255,255,0.4)', fontSize: 11 } : undefined}
          />
          <YAxis
            dataKey={yKey}
            name={yLabel || yKey}
            stroke="rgba(255,255,255,0.3)"
            tick={{ fontSize: 11, fill: 'rgba(255,255,255,0.5)' }}
            tickFormatter={formatY}
            label={yLabel ? { value: yLabel, angle: -90, position: 'insideLeft', fill: 'rgba(255,255,255,0.4)', fontSize: 11 } : undefined}
          />
          {zKey && <ZAxis dataKey={zKey} range={[40, 400]} />}
          <Tooltip
            contentStyle={{ background: 'rgba(15,23,42,0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, backdropFilter: 'blur(20px)' }}
            cursor={{ strokeDasharray: '3 3', stroke: 'rgba(255,255,255,0.2)' }}
          />
          <Scatter data={data} fill={color} fillOpacity={0.7} strokeWidth={1} stroke={color} />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
