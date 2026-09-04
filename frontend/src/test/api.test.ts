import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mockAdapter, useMock, setMockEnabled } from '../api/mockAdapter';
import { MOCK_PORTFOLIOS, MOCK_STRATEGIES, MOCK_BENCHMARKS, MOCK_AUDIT_EVENTS } from '../api/mock';

beforeEach(() => {
  setMockEnabled(true);
});

describe('mockAdapter.auth', () => {
  it('login returns tokens and user', async () => {
    const result = await mockAdapter.auth.login({ email: 'a@b.com', password: 'pass' });
    expect(result.access_token).toBe('mock-access-token');
    expect(result.refresh_token).toBe('mock-refresh-token');
    expect(result.user.email).toBe('admin@treasury.gov');
  });

  it('register returns tokens and user', async () => {
    const result = await mockAdapter.auth.register({ email: 'a@b.com', password: 'pass', name: 'Test' });
    expect(result.access_token).toBe('mock-access-token');
    expect(result.user.name).toBe('Treasury Admin');
  });

  it('me returns user', async () => {
    const result = await mockAdapter.auth.me();
    expect(result.id).toBe('user-001');
    expect(result.role).toBe('admin');
  });

  it('refresh returns new tokens', async () => {
    const result = await mockAdapter.auth.refresh('old-refresh');
    expect(result.access_token).toBe('mock-access-token');
  });
});

describe('mockAdapter.portfolios', () => {
  it('list returns all portfolios', async () => {
    const result = await mockAdapter.portfolios.list();
    expect(result.portfolios).toHaveLength(MOCK_PORTFOLIOS.length);
    expect(result.total).toBe(MOCK_PORTFOLIOS.length);
  });

  it('get returns portfolio by id', async () => {
    const result = await mockAdapter.portfolios.get('port-001');
    expect(result.id).toBe('port-001');
    expect(result.name).toBe('Sovereign Debt Portfolio - FY2026');
  });

  it('get throws for unknown id', async () => {
    await expect(mockAdapter.portfolios.get('unknown')).rejects.toThrow('Portfolio not found');
  });

  it('create returns new portfolio', async () => {
    const result = await mockAdapter.portfolios.create({ name: 'New', description: 'Desc' });
    expect(result.id).toBe('port-new');
    expect(result.name).toBe('New');
  });

  it('delete resolves without error', async () => {
    await expect(mockAdapter.portfolios.delete('port-001')).resolves.toBeUndefined();
  });

  it('upload returns first mock portfolio', async () => {
    const formData = new FormData();
    const result = await mockAdapter.portfolios.upload(formData);
    expect(result.id).toBe(MOCK_PORTFOLIOS[0].id);
  });
});

describe('mockAdapter.optimizations', () => {
  it('list returns jobs', async () => {
    const result = await mockAdapter.optimizations.list();
    expect(result).toHaveLength(1);
    expect(result[0].id).toBe('opt-001');
  });

  it('get returns job by id', async () => {
    const result = await mockAdapter.optimizations.get('opt-001');
    expect(result.status).toBe('completed');
  });

  it('get throws for unknown id', async () => {
    await expect(mockAdapter.optimizations.get('unknown')).rejects.toThrow('Optimization not found');
  });

  it('create returns new job', async () => {
    const result = await mockAdapter.optimizations.create({ name: 'Test' });
    expect(result.id).toBe('opt-new');
  });

  it('cancel resolves', async () => {
    await expect(mockAdapter.optimizations.cancel('opt-001')).resolves.toBeUndefined();
  });

  it('strategies returns mock strategies', async () => {
    const result = await mockAdapter.optimizations.strategies('opt-001');
    expect(result).toHaveLength(MOCK_STRATEGIES.length);
    expect(result[0].name).toBe('Strategy A');
  });

  it('benchmarks returns mock benchmarks', async () => {
    const result = await mockAdapter.optimizations.benchmarks('opt-001');
    expect(result).toHaveLength(MOCK_BENCHMARKS.length);
  });

  it('results returns allocation results', async () => {
    const result = await mockAdapter.optimizations.results('opt-001');
    expect(result).toHaveLength(3);
    expect(result[0].id).toBe('res-001');
  });

  it('report returns full report', async () => {
    const result = await mockAdapter.optimizations.report('opt-001');
    expect(result.job_id).toBe('opt-001');
    expect(result.strategies).toHaveLength(MOCK_STRATEGIES.length);
    expect(result.benchmarks).toHaveLength(MOCK_BENCHMARKS.length);
    expect(result.summary.best_strategy).toBe('Strategy A');
  });
});

describe('mockAdapter.audit', () => {
  it('list returns audit events', async () => {
    const result = await mockAdapter.audit.list();
    expect(result).toHaveLength(MOCK_AUDIT_EVENTS.length);
    expect(result[0].action).toBe('create');
  });
});

describe('mockAdapter.health', () => {
  it('returns healthy status', async () => {
    const result = await mockAdapter.health();
    expect(result.status).toBe('healthy');
    expect(result.version).toBe('2.1.0');
  });
});

describe('setMockEnabled', () => {
  it('toggles useMock flag', () => {
    expect(useMock).toBe(true);
    setMockEnabled(false);
    expect(useMock).toBe(false);
    setMockEnabled(true);
    expect(useMock).toBe(true);
  });
});
