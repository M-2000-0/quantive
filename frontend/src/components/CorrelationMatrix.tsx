import GlassHeatmap from './charts/GlassHeatmap';

interface CorrelationMatrixProps {
  assets: string[];
  matrix: number[][];
  title?: string;
}

export default function CorrelationMatrix({ assets, matrix, title = 'Correlation Matrix' }: CorrelationMatrixProps) {
  const data = [];
  for (let i = 0; i < assets.length; i++) {
    for (let j = 0; j < assets.length; j++) {
      data.push({ x: assets[j], y: assets[i], value: matrix[i]?.[j] ?? 0 });
    }
  }

  return (
    <GlassHeatmap
      data={data}
      xLabels={assets}
      yLabels={assets}
      min={-1}
      max={1}
      title={title}
      formatValue={(v) => v.toFixed(2)}
      colorRange={['#3b82f6', '#0f172a', '#ef4444']}
    />
  );
}
