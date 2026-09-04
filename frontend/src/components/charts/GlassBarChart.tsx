import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

interface DataPoint {
  [key: string]: string | number;
}

interface GlassBarChartProps {
  data: DataPoint[];
  xKey: string;
  yKeys: Array<{ key: string; color: string; name?: string }>;
  height?: number;
  title?: string;
  showGrid?: boolean;
  horizontal?: boolean;
  formatY?: (value: number) => string;
  colors?: string[];
  layout?: 'vertical' | 'horizontal';
}

export default function GlassBarChart({
  data, xKey, yKeys, height = 300, title, showGrid = true, horizontal = false, formatY, colors,
}: GlassBarChartProps) {
  const defaultColors = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#06b6d4', '#ec4899'];

  return (
    <div className="glass-card p-4">
      {title && <h3 className="text-sm font-semibold text-white/80 mb-3">{title}</h3>}
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={data}
          layout={horizontal ? 'vertical' : 'horizontal'}
          margin={{ top: 5, right: 10, left: horizontal ? 80 : 0, bottom: 5 }}
        >
          {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />}
          <XAxis
            type={horizontal ? 'number' : 'category'}
            dataKey={horizontal ? undefined : xKey}
            stroke="rgba(255,255,255,0.3)"
            tick={{ fontSize: 11, fill: 'rgba(255,255,255,0.5)' }}
          />
          <YAxis
            type={horizontal ? 'category' : 'number'}
            dataKey={horizontal ? xKey : undefined}
            stroke="rgba(255,255,255,0.3)"
            tick={{ fontSize: 11, fill: 'rgba(255,255,255,0.5)' }}
            tickFormatter={formatY}
          />
          <Tooltip
            contentStyle={{ background: 'rgba(15,23,42,0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, backdropFilter: 'blur(20px)' }}
            labelStyle={{ color: 'rgba(255,255,255,0.6)' }}
          />
          {yKeys.map((yk, i) => (
            <Bar key={yk.key} dataKey={yk.key} name={yk.name || yk.key} radius={[4, 4, 0, 0]}>
              {colors && data.map((_, idx) => (
                <Cell key={idx} fill={colors[idx % colors.length]} fillOpacity={0.85} />
              ))}
            </Bar>
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
