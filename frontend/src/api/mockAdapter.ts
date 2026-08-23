import type { User, Portfolio, OptimizationJob, Strategy, BenchmarkResult, AuditEvent, Report } from '../types';
import {
  MOCK_PORTFOLIOS,
  MOCK_OPTIMIZATION_JOB,
  MOCK_STRATEGIES,
  MOCK_BENCHMARKS,
  MOCK_AUDIT_EVENTS,
} from './mock';

const MOCK_USER: User = {
  id: 'user-001',
  email: 'admin@treasury.gov',
  name: 'Treasury Admin',
  role: 'admin',
  org_id: 'org-001',
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
};

const MOCK_REPORT: Report = {
  job_id: MOCK_OPTIMIZATION_JOB.id,
  job_name: MOCK_OPTIMIZATION_JOB.name,
  status: 'completed',
  optimization_type: MOCK_OPTIMIZATION_JOB.optimization_type,
  created_at: MOCK_OPTIMIZATION_JOB.created_at,
  completed_at: MOCK_OPTIMIZATION_JOB.completed_at,
  random_seed: MOCK_OPTIMIZATION_JOB.random_seed,
  model_version: MOCK_OPTIMIZATION_JOB.model_version,
  portfolio: {
    name: MOCK_PORTFOLIOS[0].name,
    num_instruments: MOCK_PORTFOLIOS[0].instruments.length,
  },
  strategies: MOCK_STRATEGIES.map((s) => ({
    name: s.name,
    description: s.description,
    rank: s.rank,
    metrics: s.metrics,
    stress_test_results: s.stress_test_results,
  })),
  benchmarks: MOCK_BENCHMARKS.map((b) => ({
    solver_name: b.solver_name,
    execution_time_seconds: b.execution_time_seconds,
    objective_value: b.objective_value,
    feasible: b.feasible,
    iterations: b.iterations,
    metrics: b.metrics,
  })),
  summary: {
    best_strategy: MOCK_STRATEGIES[0].name,
    total_instruments: MOCK_PORTFOLIOS[0].instruments.length,
    solver_count: MOCK_BENCHMARKS.length,
    scenario_count: 6,
  },
};

export let useMock = true;

export function setMockEnabled(enabled: boolean) {
  useMock = enabled;
}

function delay(ms = 300): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export const mockAdapter = {
  auth: {
    me: async (): Promise<User> => {
      await delay(200);
      return MOCK_USER;
    },
    login: async (_data: { email: string; password: string }) => {
      await delay(400);
      return {
        access_token: 'mock-access-token',
        refresh_token: 'mock-refresh-token',
        token_type: 'bearer',
        user: MOCK_USER,
      };
    },
    register: async (_data: { email: string; password: string; name: string; org_name?: string }) => {
      await delay(400);
      return {
        access_token: 'mock-access-token',
        refresh_token: 'mock-refresh-token',
        token_type: 'bearer',
        user: MOCK_USER,
      };
    },
    refresh: async (_refresh_token: string) => {
      await delay(200);
      return {
        access_token: 'mock-access-token',
        refresh_token: 'mock-refresh-token',
        token_type: 'bearer',
        user: MOCK_USER,
      };
    },
  },

  portfolios: {
    list: async (): Promise<{ portfolios: Portfolio[]; total: number }> => {
      await delay(300);
      return { portfolios: MOCK_PORTFOLIOS, total: MOCK_PORTFOLIOS.length };
    },
    get: async (id: string): Promise<Portfolio> => {
      await delay(200);
      const portfolio = MOCK_PORTFOLIOS.find((p) => p.id === id);
      if (!portfolio) throw new Error('Portfolio not found');
      return portfolio;
    },
    create: async (data: { name: string; description: string; instruments?: Array<Record<string, unknown>> }) => {
      await delay(400);
      return {
        id: 'port-new',
        name: data.name,
        description: data.description,
        org_id: 'org-001',
        created_by: 'user-001',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        instruments: (data.instruments || []) as unknown as Portfolio['instruments'],
      };
    },
    delete: async (_id: string): Promise<void> => {
      await delay(300);
    },
    upload: async (_formData: FormData): Promise<Portfolio> => {
      await delay(500);
      return MOCK_PORTFOLIOS[0];
    },
  },

  optimizations: {
    list: async (): Promise<OptimizationJob[]> => {
      await delay(300);
      return [MOCK_OPTIMIZATION_JOB];
    },
    get: async (id: string): Promise<OptimizationJob> => {
      await delay(200);
      if (id !== MOCK_OPTIMIZATION_JOB.id) throw new Error('Optimization not found');
      return MOCK_OPTIMIZATION_JOB;
    },
    create: async (data: Record<string, unknown>): Promise<OptimizationJob> => {
      await delay(500);
      return { ...MOCK_OPTIMIZATION_JOB, ...data, id: 'opt-new', created_at: new Date().toISOString() } as OptimizationJob;
    },
    cancel: async (_id: string): Promise<void> => {
      await delay(200);
    },
    strategies: async (_id: string): Promise<Strategy[]> => {
      await delay(400);
      return MOCK_STRATEGIES;
    },
    benchmarks: async (_id: string): Promise<BenchmarkResult[]> => {
      await delay(300);
      return MOCK_BENCHMARKS;
    },
    results: async (_id: string) => {
      await delay(300);
      return [
        { id: 'res-001', metrics: MOCK_STRATEGIES[0].metrics, allocation: MOCK_STRATEGIES[0].allocations },
        { id: 'res-002', metrics: MOCK_STRATEGIES[1].metrics, allocation: MOCK_STRATEGIES[1].allocations },
        { id: 'res-003', metrics: MOCK_STRATEGIES[2].metrics, allocation: MOCK_STRATEGIES[2].allocations },
      ];
    },
    report: async (_id: string): Promise<Report> => {
      await delay(400);
      return MOCK_REPORT;
    },
  },

  audit: {
    list: async (_params?: { limit?: number; offset?: number; action?: string; resource_type?: string }): Promise<AuditEvent[]> => {
      await delay(300);
      return MOCK_AUDIT_EVENTS;
    },
  },

  health: async (): Promise<{ status: string; version: string }> => {
    await delay(100);
    return { status: 'healthy', version: '2.1.0' };
  },
};
