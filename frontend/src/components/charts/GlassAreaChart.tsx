import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface DataPoint {
  [key: string]: string | number;
}

interface GlassAreaChartProps {
  data: DataPoint[];
  xKey: string;
  yKeys: Array<{ key: string; color: string; name?: string }>;
  height?: number;
  title?: string;
  showGrid?: boolean;
  gradient?: boolean;
  stacked?: boolean;
  formatY?: (value: number) => string;
}

export default function GlassAreaChart({
  data, xKey, yKeys, height = 300, title, showGrid = true, gradient = true, stacked = false, formatY,
}: GlassAreaChartProps) {
  return (
    <div className="glass-card p-4">
      {title && <h3 className="text-sm font-semibold text-white/80 mb-3">{title}</h3>}
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <defs>
            {gradient && yKeys.map((yk) => (
              <linearGradient key={yk.key} id={`grad-${yk.key}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={yk.color} stopOpacity={0.4} />
                <stop offset="95%" stopColor={yk.color} stopOpacity={0.02} />
              </linearGradient>
            ))}
          </defs>
          {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />}
          <XAxis dataKey={xKey} stroke="rgba(255,255,255,0.3)" tick={{ fontSize: 11, fill: 'rgba(255,255,255,0.5)' }} />
          <YAxis stroke="rgba(255,255,255,0.3)" tick={{ fontSize: 11, fill: 'rgba(255,255,255,0.5)' }} tickFormatter={formatY} />
          <Tooltip
            contentStyle={{ background: 'rgba(15,23,42,0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, backdropFilter: 'blur(20px)' }}
            labelStyle={{ color: 'rgba(255,255,255,0.6)' }}
          />
          {yKeys.map((yk) => (
            <Area
              key={yk.key}
              type="monotone"
              dataKey={yk.key}
              name={yk.name || yk.key}
              stroke={yk.color}
              fill={gradient ? `url(#grad-${yk.key})` : yk.color}
              fillOpacity={0.3}
              strokeWidth={2}
              stackId={stacked ? 'stack' : undefined}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
