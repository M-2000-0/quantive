import { describe, it, expect } from 'vitest';

describe('eventImpactData', () => {
  it('exports mock events', async () => {
    const { MOCK_EVENTS } = await import('../../lib/eventImpactData');
    expect(Array.isArray(MOCK_EVENTS)).toBe(true);
    expect(MOCK_EVENTS.length).toBeGreaterThan(0);
  });

  it('each event has required fields', async () => {
    const { MOCK_EVENTS } = await import('../../lib/eventImpactData');
    MOCK_EVENTS.forEach((event: any) => {
      expect(event).toHaveProperty('id');
      expect(event).toHaveProperty('title');
      expect(event).toHaveProperty('category');
      expect(event).toHaveProperty('severity');
    });
  });

  it('exports getEventImpactSummary function', async () => {
    const { getEventImpactSummary } = await import('../../lib/eventImpactData');
    expect(typeof getEventImpactSummary).toBe('function');
  });

  it('exports helper functions', async () => {
    const mod = await import('../../lib/eventImpactData');
    expect(typeof mod.getCategoryBreakdown).toBe('function');
    expect(typeof mod.getRegionBreakdown).toBe('function');
    expect(typeof mod.getMostImpactedAssets).toBe('function');
    expect(typeof mod.getSeverityColor).toBe('function');
    expect(typeof mod.getCategoryIcon).toBe('function');
  });

  it('getSeverityColor returns valid colors', async () => {
    const { getSeverityColor } = await import('../../lib/eventImpactData');
    ['low', 'medium', 'high', 'critical'].forEach(sev => {
      const color = getSeverityColor(sev);
      expect(color).toBeTruthy();
      expect(typeof color).toBe('string');
    });
  });
});

describe('demoData', () => {
  it('exports demo data arrays', async () => {
    const mod = await import('../../lib/demoData');
    expect(Array.isArray(mod.DEMO_PORTFOLIOS)).toBe(true);
    expect(Array.isArray(mod.DEMO_OPTIMIZATIONS)).toBe(true);
    expect(mod.DEMO_DASHBOARD_STATS).toBeDefined();
  });

  it('dashboard stats has totalAUM', async () => {
    const { DEMO_DASHBOARD_STATS } = await import('../../lib/demoData');
    expect(typeof DEMO_DASHBOARD_STATS.totalAUM).toBe('number');
  });
});
