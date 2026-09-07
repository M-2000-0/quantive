import { Treemap, ResponsiveContainer, Tooltip } from 'recharts';

type TreemapData = {
  name: string;
  size: number;
  color?: string;
  children?: TreemapData[];
};

interface GlassTreemapProps {
  data: TreemapData[];
  height?: number;
  title?: string;
  colors?: string[];
  formatSize?: (value: number) => string;
}

const DEFAULT_COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#06b6d4', '#ec4899'];

const CustomContent = (props: Record<string, unknown>) => {
  const { x, y, width, height, name, colors, index } = props as {
    x: number; y: number; width: number; height: number;
    name: string; colors: string[]; index: number;
  };
  const color = colors[index % colors.length];

  return (
    <g>
      <rect x={x} y={y} width={width} height={height} rx={4} fill={color} fillOpacity={0.7} stroke="rgba(255,255,255,0.1)" strokeWidth={1} />
      {width > 60 && height > 30 && (
        <text x={x + width / 2} y={y + height / 2} textAnchor="middle" dominantBaseline="middle" fill="white" fontSize={12} fontWeight={600}>
          {name}
        </text>
      )}
    </g>
  );
};

export default function GlassTreemap({
  data, height = 300, title, colors = DEFAULT_COLORS, formatSize,
}: GlassTreemapProps) {
  return (
    <div className="glass-card p-4">
      {title && <h3 className="text-sm font-semibold text-white/80 mb-3">{title}</h3>}
      <ResponsiveContainer width="100%" height={height}>
        <Treemap
          data={data}
          dataKey="size"
          nameKey="name"
          content={<CustomContent colors={colors} index={0} x={0} y={0} width={0} height={0} name="" />}
        />
      </ResponsiveContainer>
    </div>
  );
}
