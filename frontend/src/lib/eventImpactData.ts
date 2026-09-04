export interface ImpactEvent {
  id: string;
  title: string;
  description: string;
  category: 'economic' | 'political' | 'commercial' | 'geopolitical' | 'regulatory' | 'environmental';
  severity: 'critical' | 'high' | 'medium' | 'low';
  region: string;
  affectedAssets: Array<{ name: string; type: string; impact: number }>;
}

export interface ImpactCorrelation {
  eventIdA: string;
  eventIdB: string;
  correlation: number;
}

export const MOCK_EVENTS: ImpactEvent[] = [
  { id: 'evt-1', title: 'Fed Signals Pause on Rate Hikes', description: 'Federal Reserve holds rates steady, easing refinancing pressure.', category: 'economic', severity: 'high', region: 'North America', affectedAssets: [{ name: 'US 10Y Treasury', type: 'bond', impact: 0.8 }] },
  { id: 'evt-2', title: 'Tesla Robotaxi Launch Expands', description: 'Autonomous fleet rollout lifts commercial credit outlook.', category: 'commercial', severity: 'medium', region: 'North America', affectedAssets: [{ name: 'Auto ABS Index', type: 'abs', impact: 0.4 }] },
  { id: 'evt-3', title: 'EU Fiscal Pact Revision', description: 'New deficit flexibility for green investment.', category: 'political', severity: 'high', region: 'Europe', affectedAssets: [{ name: 'EU Green Bonds', type: 'bond', impact: 0.6 }] },
  { id: 'evt-4', title: 'Strait Shipping Disruption', description: 'Freight rerouting raises near-term inflation risk.', category: 'geopolitical', severity: 'critical', region: 'Middle East', affectedAssets: [{ name: 'Oil Futures', type: 'commodity', impact: -0.7 }] },
  { id: 'evt-5', title: 'Basel Endgame Capital Rules Finalized', description: 'Bank capital clarity supports sovereign issuance calendars.', category: 'regulatory', severity: 'medium', region: 'Global', affectedAssets: [{ name: 'Bank Senior Debt', type: 'bond', impact: 0.3 }] },
  { id: 'evt-6', title: 'Japan Yield Curve Shift', description: 'BOJ tolerance band widens, JPY volatility up.', category: 'economic', severity: 'medium', region: 'Asia Pacific', affectedAssets: [{ name: 'JPY Swap 10Y', type: 'derivative', impact: -0.4 }] },
  { id: 'evt-7', title: 'Election Coalition Talks Stall', description: 'Delayed budget approval pushes bill issuance.', category: 'political', severity: 'low', region: 'Europe', affectedAssets: [{ name: 'T-Bill 3M', type: 'bill', impact: -0.2 }] },
  { id: 'evt-8', title: 'Critical Minerals Export Quota', description: 'Supply constraints support commodity-linked notes.', category: 'geopolitical', severity: 'high', region: 'Africa', affectedAssets: [{ name: 'Copper Notes', type: 'commodity', impact: 0.5 }] },
  { id: 'evt-9', title: 'Climate Disclosure Mandate', description: 'Mandatory Scope 3 reporting for large issuers.', category: 'regulatory', severity: 'low', region: 'Global', affectedAssets: [{ name: 'ESG Fund Units', type: 'fund', impact: 0.2 }] },
  { id: 'evt-10', title: 'Drought Hits Grain Belt', description: 'Crop shortfall pressures food-linked subsidies.', category: 'environmental', severity: 'medium', region: 'South America', affectedAssets: [{ name: 'Agri Bonds', type: 'bond', impact: -0.5 }] },
];

export const MOCK_IMPACT_MATRIX: ImpactCorrelation[] = [
  { eventIdA: 'evt-1', eventIdB: 'evt-6', correlation: 0.62 },
  { eventIdA: 'evt-4', eventIdB: 'evt-10', correlation: 0.41 },
  { eventIdA: 'evt-3', eventIdB: 'evt-5', correlation: 0.35 },
  { eventIdA: 'evt-4', eventIdB: 'evt-8', correlation: -0.28 },
];

const SEVERITY_SCORE: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1 };

export function getEventImpactSummary(events: ImpactEvent[]) {
  const totalPositive = events.filter((e) =>
    e.affectedAssets.some((a) => a.impact > 0),
  ).length;
  const totalNegative = events.filter((e) =>
    e.affectedAssets.some((a) => a.impact < 0),
  ).length;
  const avg =
    events.reduce((sum, e) => sum + (SEVERITY_SCORE[e.severity] ?? 1), 0) /
    Math.max(1, events.length);
  const criticalCount = events.filter((e) => e.severity === 'critical').length;
  return {
    totalEvents: events.length,
    totalPositive,
    totalNegative,
    avgSeverity: avg.toFixed(1),
    criticalCount,
  };
}

export function getCategoryBreakdown(events: ImpactEvent[]): Record<string, number> {
  return events.reduce<Record<string, number>>((acc, e) => {
    acc[e.category] = (acc[e.category] ?? 0) + 1;
    return acc;
  }, {});
}

export function getRegionBreakdown(events: ImpactEvent[]): Record<string, number> {
  return events.reduce<Record<string, number>>((acc, e) => {
    acc[e.region] = (acc[e.region] ?? 0) + 1;
    return acc;
  }, {});
}

export function getMostImpactedAssets(events: ImpactEvent[]) {
  const byAsset = new Map<string, { name: string; type: string; impacts: number[] }>();
  for (const e of events) {
    for (const a of e.affectedAssets) {
      const entry = byAsset.get(a.name) ?? { name: a.name, type: a.type, impacts: [] };
      entry.impacts.push(a.impact);
      byAsset.set(a.name, entry);
    }
  }
  return [...byAsset.values()]
    .map((v) => ({
      name: v.name,
      type: v.type,
      avgImpact: v.impacts.reduce((s, x) => s + x, 0) / v.impacts.length,
    }))
    .sort((a, b) => Math.abs(b.avgImpact) - Math.abs(a.avgImpact));
}

export function getSeverityColor(severity: string): string {
  switch (severity) {
    case 'critical':
      return '#dc2626';
    case 'high':
      return '#ea580c';
    case 'medium':
      return '#d97706';
    default:
      return '#16a34a';
  }
}

export function getCategoryIcon(category: string): string {
  switch (category) {
    case 'political':
      return '🏛️';
    case 'economic':
      return '📈';
    case 'geopolitical':
      return '🌍';
    case 'commercial':
      return '🏢';
    case 'regulatory':
      return '📋';
    default:
      return '🌱';
  }
}
