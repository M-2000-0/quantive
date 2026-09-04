import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';

interface DataPoint {
  name: string;
  value: number;
  color?: string;
}

interface GlassPieChartProps {
  data: DataPoint[];
  height?: number;
  title?: string;
  innerRadius?: number;
  outerRadius?: number;
  colors?: string[];
  showLegend?: boolean;
  formatValue?: (value: number) => string;
}

const DEFAULT_COLORS = ['#c8a951', '#60a5fa', '#34d399', '#fbbf24', '#f87171', '#06b6d4', '#c084fc', '#fb923c'];

export default function GlassPieChart({
  data, height = 300, title, innerRadius = 60, outerRadius = 100, colors, showLegend = true, formatValue,
}: GlassPieChartProps) {
  const palette = colors || DEFAULT_COLORS;

  return (
    <div className="glass-card" style={{ padding: 16 }}>
      {title && (
        <h3 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', marginBottom: 12, letterSpacing: '-0.01em' }}>
          {title}
        </h3>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={innerRadius}
            outerRadius={outerRadius}
            paddingAngle={2}
            dataKey="value"
            stroke="none"
          >
            {data.map((_, idx) => (
              <Cell key={idx} fill={data[idx].color || palette[idx % palette.length]} fillOpacity={0.85} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              background: 'rgba(8, 9, 12, 0.95)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: 8,
              backdropFilter: 'blur(20px)',
              WebkitBackdropFilter: 'blur(20px)',
              fontSize: 12,
              color: '#ececef',
              boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
            }}
            formatter={formatValue ? (value: number) => [formatValue(value)] : undefined}
          />
          {showLegend && (
            <Legend
              wrapperStyle={{ fontSize: 11, color: 'var(--text2)' }}
              formatter={(value) => <span style={{ color: 'var(--text2)' }}>{value}</span>}
            />
          )}
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
