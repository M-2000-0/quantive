import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';

// Mock recharts to avoid SVG rendering issues in JSDOM
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div data-testid="responsive-container">{children}</div>,
  AreaChart: ({ children }: { children: React.ReactNode }) => <div data-testid="area-chart">{children}</div>,
  Area: () => null,
  BarChart: ({ children }: { children: React.ReactNode }) => <div data-testid="bar-chart">{children}</div>,
  Bar: () => null,
  Cell: () => null,
  PieChart: ({ children }: { children: React.ReactNode }) => <div data-testid="pie-chart">{children}</div>,
  Pie: () => null,
  LineChart: ({ children }: { children: React.ReactNode }) => <div data-testid="line-chart">{children}</div>,
  Line: () => null,
  RadarChart: ({ children }: { children: React.ReactNode }) => <div data-testid="radar-chart">{children}</div>,
  Radar: () => null,
  ScatterChart: ({ children }: { children: React.ReactNode }) => <div data-testid="scatter-chart">{children}</div>,
  Scatter: () => null,
  Treemap: () => <div data-testid="treemap" />,
  Tooltip: () => null,
  Legend: () => null,
  XAxis: () => null,
  YAxis: () => null,
  ZAxis: () => null,
  CartesianGrid: () => null,
  PolarGrid: () => null,
  PolarAngleAxis: () => null,
  PolarRadiusAxis: () => null,
}));

import GlassAreaChart from '../components/charts/GlassAreaChart';
import GlassBarChart from '../components/charts/GlassBarChart';
import GlassPieChart from '../components/charts/GlassPieChart';
import GlassLineChart from '../components/charts/GlassLineChart';
import GlassRadarChart from '../components/charts/GlassRadarChart';
import GlassScatterChart from '../components/charts/GlassScatterChart';
import GlassGaugeChart from '../components/charts/GlassGaugeChart';
import GlassHeatmap from '../components/charts/GlassHeatmap';

const sampleData = [
  { month: 'Jan', rate: 4.2, yield: 4.5 },
  { month: 'Feb', rate: 4.3, yield: 4.6 },
  { month: 'Mar', rate: 4.1, yield: 4.4 },
];

const pieData = [
  { name: 'USD', value: 60 },
  { name: 'EUR', value: 25 },
  { name: 'GBP', value: 15 },
];

describe('GlassAreaChart', () => {
  it('renders with title', () => {
    render(<GlassAreaChart data={sampleData} xKey="month" yKeys={[{ key: 'rate', color: '#3b82f6' }]} title="Yield Curve" />);
    expect(screen.getByText('Yield Curve')).toBeTruthy();
  });

  it('renders without title', () => {
    const { container } = render(<GlassAreaChart data={sampleData} xKey="month" yKeys={[{ key: 'rate', color: '#3b82f6' }]} />);
    expect(container.querySelector('[data-testid="responsive-container"]')).toBeTruthy();
  });

  it('handles stacked mode', () => {
    render(<GlassAreaChart data={sampleData} xKey="month" yKeys={[{ key: 'rate', color: '#3b82f6' }, { key: 'yield', color: '#10b981' }]} stacked title="Stacked" />);
    expect(screen.getByText('Stacked')).toBeTruthy();
  });
});

describe('GlassBarChart', () => {
  it('renders with title', () => {
    render(<GlassBarChart data={sampleData} xKey="month" yKeys={[{ key: 'rate', color: '#3b82f6' }]} title="Bar Chart" />);
    expect(screen.getByText('Bar Chart')).toBeTruthy();
  });

  it('renders horizontal bars', () => {
    render(<GlassBarChart data={sampleData} xKey="month" yKeys={[{ key: 'rate', color: '#3b82f6' }]} horizontal title="Horizontal" />);
    expect(screen.getByText('Horizontal')).toBeTruthy();
  });

  it('renders without grid', () => {
    render(<GlassBarChart data={sampleData} xKey="month" yKeys={[{ key: 'rate', color: '#3b82f6' }]} showGrid={false} />);
    expect(screen.getByTestId('responsive-container')).toBeTruthy();
  });
});

describe('GlassPieChart', () => {
  it('renders with title and data', () => {
    render(<GlassPieChart data={pieData} title="Allocation" />);
    expect(screen.getByText('Allocation')).toBeTruthy();
  });

  it('renders without legend', () => {
    render(<GlassPieChart data={pieData} showLegend={false} />);
    expect(screen.getByTestId('responsive-container')).toBeTruthy();
  });

  it('handles custom colors', () => {
    render(<GlassPieChart data={pieData} colors={['#ff0000', '#00ff00', '#0000ff']} />);
    expect(screen.getByTestId('responsive-container')).toBeTruthy();
  });
});

describe('GlassLineChart', () => {
  it('renders with title', () => {
    render(<GlassLineChart data={sampleData} xKey="month" yKeys={[{ key: 'rate', color: '#3b82f6', name: 'Rate' }]} title="Line Chart" />);
    expect(screen.getByText('Line Chart')).toBeTruthy();
  });

  it('renders with dashed line', () => {
    render(<GlassLineChart data={sampleData} xKey="month" yKeys={[{ key: 'rate', color: '#3b82f6', dashed: true }]} />);
    expect(screen.getByTestId('responsive-container')).toBeTruthy();
  });
});

describe('GlassRadarChart', () => {
  const radarData = [
    { factor: 'Risk', score: 7 },
    { factor: 'Return', score: 5 },
    { factor: 'Diversification', score: 8 },
  ];

  it('renders with title', () => {
    render(<GlassRadarChart data={radarData} angleKey="factor" radarKeys={[{ key: 'score', color: '#3b82f6' }]} title="Radar" />);
    expect(screen.getByText('Radar')).toBeTruthy();
  });

  it('renders with max value', () => {
    render(<GlassRadarChart data={radarData} angleKey="factor" radarKeys={[{ key: 'score', color: '#3b82f6' }]} max={10} />);
    expect(screen.getByTestId('responsive-container')).toBeTruthy();
  });
});

describe('GlassScatterChart', () => {
  const scatterData = [
    { name: 'A', risk: 3, ret: 5 },
    { name: 'B', risk: 7, ret: 8 },
  ];

  it('renders with title', () => {
    render(<GlassScatterChart data={scatterData} xKey="risk" yKey="ret" title="Scatter" />);
    expect(screen.getByText('Scatter')).toBeTruthy();
  });

  it('renders with labels', () => {
    render(<GlassScatterChart data={scatterData} xKey="risk" yKey="ret" xLabel="Risk" yLabel="Return" />);
    expect(screen.getByTestId('responsive-container')).toBeTruthy();
  });
});

describe('GlassGaugeChart', () => {
  it('renders with title', () => {
    const { container } = render(<GlassGaugeChart value={75} title="Risk Score" />);
    expect(screen.getByText('Risk Score')).toBeTruthy();
    // Value is rendered as SVG text
    const svgText = container.querySelectorAll('text');
    expect(svgText.length).toBeGreaterThan(0);
  });

  it('renders with subtitle', () => {
    render(<GlassGaugeChart value={50} title="Gauge" subtitle="Performance" />);
    expect(screen.getByText('Performance')).toBeTruthy();
  });

  it('renders with custom color', () => {
    const { container } = render(<GlassGaugeChart value={30} color="#10b981" />);
    const svgText = container.querySelectorAll('text');
    expect(svgText.length).toBeGreaterThan(0);
  });

  it('renders with custom format', () => {
    const { container } = render(<GlassGaugeChart value={0.85} formatValue={(v) => `${(v * 100).toFixed(0)}%`} />);
    // Custom format renders '85%' inside SVG
    const svgText = container.querySelectorAll('text');
    const texts = Array.from(svgText).map(t => t.textContent);
    expect(texts.some(t => t?.includes('85%'))).toBeTruthy();
  });

  it('handles min/max range', () => {
    const { container } = render(<GlassGaugeChart value={5} min={0} max={10} />);
    const svgText = container.querySelectorAll('text');
    expect(svgText.length).toBeGreaterThan(0);
  });
});

describe('GlassHeatmap', () => {
  const heatmapData = [
    { x: 'A', y: 'B', value: 0.8 },
    { x: 'A', y: 'C', value: -0.3 },
    { x: 'B', y: 'C', value: 0.5 },
  ];

  it('renders with title', () => {
    render(<GlassHeatmap data={heatmapData} xLabels={['A', 'B']} yLabels={['B', 'C']} title="Correlation" />);
    expect(screen.getByText('Correlation')).toBeTruthy();
  });

  it('renders heatmap cells', () => {
    const { container } = render(<GlassHeatmap data={heatmapData} xLabels={['A', 'B']} yLabels={['B', 'C']} />);
    // Should render grid cells with background colors
    const cells = container.querySelectorAll('[style]');
    expect(cells.length).toBeGreaterThan(0);
  });

  it('handles custom color range', () => {
    const { container } = render(<GlassHeatmap data={heatmapData} xLabels={['A', 'B']} yLabels={['B', 'C']} colorRange={['#22c55e', '#ffffff', '#ef4444']} />);
    const cells = container.querySelectorAll('[style]');
    expect(cells.length).toBeGreaterThan(0);
  });
});

describe('Chart barrel export', () => {
  it('exports all chart components', async () => {
    const charts = await import('../components/charts');
    expect(charts.GlassAreaChart).toBeDefined();
    expect(charts.GlassBarChart).toBeDefined();
    expect(charts.GlassPieChart).toBeDefined();
    expect(charts.GlassLineChart).toBeDefined();
    expect(charts.GlassRadarChart).toBeDefined();
    expect(charts.GlassScatterChart).toBeDefined();
    expect(charts.GlassGaugeChart).toBeDefined();
    expect(charts.GlassHeatmap).toBeDefined();
    expect(charts.GlassTreemap).toBeDefined();
    expect(charts.GlassWaterfallChart).toBeDefined();
    expect(charts.GlassBubbleChart).toBeDefined();
    expect(charts.GlassCandlestickChart).toBeDefined();
    expect(charts.GlassSankeyDiagram).toBeDefined();
    expect(charts.GlassBoxPlot).toBeDefined();
    expect(charts.GlassComposedChart).toBeDefined();
  });
});
