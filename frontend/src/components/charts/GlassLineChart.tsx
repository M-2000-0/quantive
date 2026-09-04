import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

interface DataPoint {
  [key: string]: string | number;
}

interface GlassLineChartProps {
  data: DataPoint[];
  xKey: string;
  yKeys: Array<{ key: string; color: string; name?: string; dashed?: boolean }>;
  height?: number;
  title?: string;
  showGrid?: boolean;
  showDots?: boolean;
  smooth?: boolean;
  formatY?: (value: number) => string;
}

export default function GlassLineChart({
  data, xKey, yKeys, height = 300, title, showGrid = true, showDots = true, smooth = true, formatY,
}: GlassLineChartProps) {
  return (
    <div className="glass-card p-4">
      {title && <h3 className="text-sm font-semibold text-white/80 mb-3">{title}</h3>}
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />}
          <XAxis dataKey={xKey} stroke="rgba(255,255,255,0.3)" tick={{ fontSize: 11, fill: 'rgba(255,255,255,0.5)' }} />
          <YAxis stroke="rgba(255,255,255,0.3)" tick={{ fontSize: 11, fill: 'rgba(255,255,255,0.5)' }} tickFormatter={formatY} />
          <Tooltip
            contentStyle={{ background: 'rgba(15,23,42,0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, backdropFilter: 'blur(20px)' }}
            labelStyle={{ color: 'rgba(255,255,255,0.6)' }}
          />
          {yKeys.map((yk) => (
            <Line
              key={yk.key}
              type={smooth ? 'monotone' : 'linear'}
              dataKey={yk.key}
              name={yk.name || yk.key}
              stroke={yk.color}
              strokeWidth={2}
              dot={showDots ? { fill: yk.color, r: 3 } : false}
              strokeDasharray={yk.dashed ? '5 5' : undefined}
              activeDot={{ r: 5, strokeWidth: 2 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
