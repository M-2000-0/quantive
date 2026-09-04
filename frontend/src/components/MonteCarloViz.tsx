import GlassAreaChart from './charts/GlassAreaChart';
import GlassLineChart from './charts/GlassLineChart';
import { StatCard } from './ui';

interface SimulationPath {
  [key: string]: number;
}

interface MonteCarloVizProps {
  paths: SimulationPath[];
  percentiles: { p5: number[]; p25: number[]; p50: number[]; p75: number[]; p95: number[] };
  labels: string[];
  title?: string;
  stats?: {
    mean: number;
    median: number;
    stdDev: number;
    var95: number;
  };
}

export default function MonteCarloViz({ paths, percentiles, labels, title = 'Monte Carlo Simulation', stats }: MonteCarloVizProps) {
  // Build percentile data
  const percentileData = labels.map((label, i) => ({
    date: label,
    p5: percentiles.p5[i],
    p25: percentiles.p25[i],
    p50: percentiles.p50[i],
    p75: percentiles.p75[i],
    p95: percentiles.p95[i] }));

  // Sample paths for display
  const samplePaths = paths.slice(0, Math.min(20, paths.length)).map((path, idx) => ({
    key: `sim_${idx}`,
    color: `hsl(${210 + idx * 8}, 70%, ${55 + idx * 2}%)`,
    name: `Path ${idx + 1}` }));

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-white/80">{title}</h3>

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard label="Mean" value={`$${stats.mean.toLocaleString()}`} />
          <StatCard label="Median" value={`$${stats.median.toLocaleString()}`} />
          <StatCard label="Std Dev" value={`$${stats.stdDev.toLocaleString()}`} />
          <StatCard label="VaR 95%" value={`$${stats.var95.toLocaleString()}`} trend="down" />
        </div>
      )}

      {/* Fan chart (percentiles) */}
      <GlassLineChart
        data={percentileData}
        xKey="date"
        yKeys={[
          { key: 'p5', color: '#1e40af', name: '5th Percentile', dashed: true },
          { key: 'p25', color: '#3b82f6', name: '25th Percentile' },
          { key: 'p50', color: '#10b981', name: 'Median' },
          { key: 'p75', color: '#3b82f6', name: '75th Percentile' },
          { key: 'p95', color: '#1e40af', name: '95th Percentile', dashed: true },
        ]}
        height={250}
        title="Percentile Fan Chart"
        showDots={false}
      />
    </div>
  );
}
