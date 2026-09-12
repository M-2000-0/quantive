import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ZAxis, Cell } from 'recharts';

interface BubbleDataPoint {
  name: string;
  x: number;
  y: number;
  z: number;
  color?: string;
}

interface GlassBubbleChartProps {
  data: BubbleDataPoint[];
  height?: number;
  title?: string;
  xLabel?: string;
  yLabel?: string;
  formatX?: (value: number) => string;
  formatY?: (value: number) => string;
}

export default function GlassBubbleChart({
  data, height = 300, title, xLabel, yLabel, formatX, formatY,
}: GlassBubbleChartProps) {
  return (
    <div className="glass-card p-4">
      {title && <h3 className="text-sm font-semibold text-white/80 mb-3">{title}</h3>}
      <ResponsiveContainer width="100%" height={height}>
        <ScatterChart margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis
            dataKey="x"
            name={xLabel || 'X'}
            stroke="rgba(255,255,255,0.3)"
            tick={{ fontSize: 11, fill: 'rgba(255,255,255,0.5)' }}
            tickFormatter={formatX}
          />
          <YAxis
            dataKey="y"
            name={yLabel || 'Y'}
            stroke="rgba(255,255,255,0.3)"
            tick={{ fontSize: 11, fill: 'rgba(255,255,255,0.5)' }}
            tickFormatter={formatY}
          />
          <ZAxis dataKey="z" range={[20, 400]} />
          <Tooltip
            contentStyle={{ background: 'rgba(15,23,42,0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, backdropFilter: 'blur(20px)' }}
            formatter={(value: any, name: any) => [value, name]}
          />
          <Scatter data={data} fillOpacity={0.6}>
            {data.map((item, idx) => (
              <Cell key={idx} fill={item.color || '#3b82f6'} fillOpacity={0.6} stroke={item.color || '#3b82f6'} strokeWidth={1} />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
