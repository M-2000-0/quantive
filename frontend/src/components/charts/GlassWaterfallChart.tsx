import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

interface WaterfallDataPoint {
  label: string;
  value: number;
  isTotal?: boolean;
  isSubtotal?: boolean;
}

interface GlassWaterfallChartProps {
  data: WaterfallDataPoint[];
  height?: number;
  title?: string;
  formatValue?: (value: number) => string;
}

function buildWaterfallData(data: WaterfallDataPoint[]) {
  let running = 0;
  return data.map((item) => {
    if (item.isTotal || item.isSubtotal) {
      const bottom = 0;
      running = item.value;
      return { ...item, bottom, height: item.value, display: item.value };
    }
    const bottom = running;
    running += item.value;
    return {
      ...item,
      bottom: item.value >= 0 ? bottom : running,
      height: Math.abs(item.value),
      display: item.value,
    };
  });
}

export default function GlassWaterfallChart({
  data, height = 300, title, formatValue,
}: GlassWaterfallChartProps) {
  const chartData = buildWaterfallData(data);

  return (
    <div className="glass-card p-4">
      {title && <h3 className="text-sm font-semibold text-white/80 mb-3">{title}</h3>}
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis dataKey="label" stroke="rgba(255,255,255,0.3)" tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.5)' }} angle={-45} textAnchor="end" />
          <YAxis stroke="rgba(255,255,255,0.3)" tick={{ fontSize: 11, fill: 'rgba(255,255,255,0.5)' }} tickFormatter={formatValue} />
          <Tooltip
            contentStyle={{ background: 'rgba(15,23,42,0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, backdropFilter: 'blur(20px)' }}
            formatter={(value, name, props) => [formatValue ? formatValue(value as number) : value, (props as unknown as { payload?: { label?: string } })?.payload?.label]}
          />
          <Bar dataKey="bottom" stackId="waterfall" fill="transparent" />
          <Bar dataKey="height" stackId="waterfall" radius={[4, 4, 0, 0]}>
            {chartData.map((item, idx) => (
              <Cell
                key={idx}
                fill={item.isTotal ? '#8b5cf6' : item.isSubtotal ? '#6366f1' : item.value >= 0 ? '#10b981' : '#ef4444'}
                fillOpacity={0.8}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
