import { ComposedChart, Bar, Line, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

interface DataPoint {
  [key: string]: string | number;
}

interface SeriesConfig {
  key: string;
  type: 'bar' | 'line' | 'area';
  color: string;
  name?: string;
  yAxisId?: string;
  dashed?: boolean;
}

interface GlassComposedChartProps {
  data: DataPoint[];
  xKey: string;
  series: SeriesConfig[];
  height?: number;
  title?: string;
  showGrid?: boolean;
  formatY?: (value: number) => string;
  showLegend?: boolean;
}

export default function GlassComposedChart({
  data, xKey, series, height = 300, title, showGrid = true, formatY, showLegend = true,
}: GlassComposedChartProps) {
  return (
    <div className="glass-card p-4">
      {title && <h3 className="text-sm font-semibold text-white/80 mb-3">{title}</h3>}
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />}
          <XAxis dataKey={xKey} stroke="rgba(255,255,255,0.3)" tick={{ fontSize: 11, fill: 'rgba(255,255,255,0.5)' }} />
          <YAxis stroke="rgba(255,255,255,0.3)" tick={{ fontSize: 11, fill: 'rgba(255,255,255,0.5)' }} tickFormatter={formatY} />
          <Tooltip
            contentStyle={{ background: 'rgba(15,23,42,0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, backdropFilter: 'blur(20px)' }}
            labelStyle={{ color: 'rgba(255,255,255,0.6)' }}
          />
          {showLegend && <Legend wrapperStyle={{ fontSize: 12, color: 'rgba(255,255,255,0.5)' }} />}
          {series.map((s) => {
            const commonProps = { key: s.key, dataKey: s.key, name: s.name || s.key, stroke: s.color, fill: s.color, yAxisId: s.yAxisId };
            if (s.type === 'bar') {
              return <Bar {...commonProps} radius={[4, 4, 0, 0]} fillOpacity={0.7} />;
            }
            if (s.type === 'line') {
              return <Line {...commonProps} strokeWidth={2} dot={{ r: 3 }} strokeDasharray={s.dashed ? '5 5' : undefined} />;
            }
            return <Area {...commonProps} fillOpacity={0.15} strokeWidth={2} />;
          })}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
