import { useState } from 'react';

interface HeatmapCell {
  x: string;
  y: string;
  value: number;
}

interface GlassHeatmapProps {
  data: HeatmapCell[];
  xLabels: string[];
  yLabels: string[];
  min?: number;
  max?: number;
  height?: number;
  title?: string;
  formatValue?: (value: number) => string;
  colorRange?: [string, string, string]; // [low, mid, high]
}

function getHeatColor(value: number, min: number, max: number, colors: [string, string, string]): string {
  const normalized = max === min ? 0.5 : (value - min) / (max - min);
  if (normalized < 0.5) {
    const t = normalized * 2;
    return interpolateColor(colors[0], colors[1], t);
  }
  const t = (normalized - 0.5) * 2;
  return interpolateColor(colors[1], colors[2], t);
}

function interpolateColor(c1: string, c2: string, t: number): string {
  const r1 = parseInt(c1.slice(1, 3), 16), g1 = parseInt(c1.slice(3, 5), 16), b1 = parseInt(c1.slice(5, 7), 16);
  const r2 = parseInt(c2.slice(1, 3), 16), g2 = parseInt(c2.slice(3, 5), 16), b2 = parseInt(c2.slice(5, 7), 16);
  const r = Math.round(r1 + (r2 - r1) * t);
  const g = Math.round(g1 + (g2 - g1) * t);
  const b = Math.round(b1 + (b2 - b1) * t);
  return `rgb(${r},${g},${b})`;
}

export default function GlassHeatmap({
  data, xLabels, yLabels, min, max, height = 300, title, formatValue, colorRange = ['#1e40af', '#1e293b', '#dc2626'],
}: GlassHeatmapProps) {
  const [hoveredCell, setHoveredCell] = useState<string | null>(null);

  const values = data.map((d) => d.value);
  const dataMin = min ?? Math.min(...values);
  const dataMax = max ?? Math.max(...values);

  const cellSize = Math.min(Math.floor(500 / xLabels.length), Math.floor(height / yLabels.length));

  return (
    <div className="glass-card p-4 overflow-x-auto">
      {title && <h3 className="text-sm font-semibold text-white/80 mb-3">{title}</h3>}
      <div className="inline-block">
        {/* X-axis labels */}
        <div className="flex" style={{ marginLeft: cellSize + 8 }}>
          {xLabels.map((label) => (
            <div key={label} className="text-[10px] text-white/50 text-center" style={{ width: cellSize }}>
              {label}
            </div>
          ))}
        </div>

        {/* Rows */}
        {yLabels.map((yLabel, yi) => (
          <div key={yLabel} className="flex items-center">
            <div className="text-[10px] text-white/50 text-right pr-2 truncate" style={{ width: cellSize }}>
              {yLabel}
            </div>
            {xLabels.map((xLabel) => {
              const cell = data.find((d) => d.x === xLabel && d.y === yLabel);
              const value = cell?.value ?? 0;
              const bg = getHeatColor(value, dataMin, dataMax, colorRange);
              const cellId = `${xLabel}-${yLabel}`;

              return (
                <div
                  key={cellId}
                  className="relative flex items-center justify-center cursor-pointer transition-transform hover:scale-110 hover:z-10"
                  style={{
                    width: cellSize, height: cellSize,
                    backgroundColor: bg,
                    borderRadius: 4, margin: 1,
                  }}
                  onMouseEnter={() => setHoveredCell(cellId)}
                  onMouseLeave={() => setHoveredCell(null)}
                >
                  <span className="text-[10px] font-medium text-white/80">
                    {formatValue ? formatValue(value) : value.toFixed(2)}
                  </span>
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}
