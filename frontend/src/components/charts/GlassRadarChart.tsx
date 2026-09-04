import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer, Tooltip, Legend } from 'recharts';

interface DataPoint {
  [key: string]: string | number;
}

interface GlassRadarChartProps {
  data: DataPoint[];
  angleKey: string;
  radarKeys: Array<{ key: string; color: string; name?: string }>;
  height?: number;
  title?: string;
  max?: number;
}

export default function GlassRadarChart({
  data, angleKey, radarKeys, height = 300, title, max,
}: GlassRadarChartProps) {
  return (
    <div className="glass-card p-4">
      {title && <h3 className="text-sm font-semibold text-white/80 mb-3">{title}</h3>}
      <ResponsiveContainer width="100%" height={height}>
        <RadarChart data={data} cx="50%" cy="50%" outerRadius="70%">
          <PolarGrid stroke="rgba(255,255,255,0.08)" />
          <PolarAngleAxis dataKey={angleKey} tick={{ fontSize: 11, fill: 'rgba(255,255,255,0.5)' }} />
          <PolarRadiusAxis tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.3)' }} domain={[0, max || 'auto']} />
          {radarKeys.map((rk) => (
            <Radar
              key={rk.key}
              name={rk.name || rk.key}
              dataKey={rk.key}
              stroke={rk.color}
              fill={rk.color}
              fillOpacity={0.15}
              strokeWidth={2}
            />
          ))}
          <Tooltip contentStyle={{ background: 'rgba(15,23,42,0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12 }} />
          <Legend wrapperStyle={{ fontSize: 12, color: 'rgba(255,255,255,0.6)' }} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
