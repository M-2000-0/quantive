import { MOCK_PORTFOLIOS, MOCK_STRATEGIES, MOCK_BENCHMARKS, MOCK_AUDIT_EVENTS, MOCK_USER } from './mock';

export let useMock = false;

export function setMockEnabled(value: boolean) {
  useMock = value;
}

async function login({ email }: { email: string; password: string }) {
  return {
    access_token: 'mock-access-token',
    refresh_token: 'mock-refresh-token',
    token_type: 'bearer',
    user: { ...MOCK_USER, email: 'admin@treasury.gov' },
  };
}

async function register({ email, name }: { email: string; password: string; name: string }) {
  return {
    access_token: 'mock-access-token',
    refresh_token: 'mock-refresh-token',
    token_type: 'bearer',
    user: { ...MOCK_USER, email, name: name || 'Treasury Admin' },
  };
}

async function me() {
  return { ...MOCK_USER };
}

async function refresh(_token: string) {
  return {
    access_token: 'mock-access-token',
    refresh_token: 'mock-refresh-token',
    token_type: 'bearer',
    user: { ...MOCK_USER },
  };
}

const MOCK_JOBS = [
  { id: 'opt-001', name: 'Q1 Refinancing Pass', status: 'completed' },
];

export const mockAdapter = {
  auth: { login, register, me, refresh },
  portfolios: {
    list: async () => ({ portfolios: MOCK_PORTFOLIOS, total: MOCK_PORTFOLIOS.length }),
    get: async (id: string) => {
      const found = MOCK_PORTFOLIOS.find((p) => p.id === id);
      if (!found) throw new Error('Portfolio not found');
      return found;
    },
    create: async ({ name, description }: { name: string; description: string }) => ({
      id: 'port-new',
      name,
      description,
    }),
    delete: async (_id: string) => undefined as void,
    upload: async (_formData: FormData) => MOCK_PORTFOLIOS[0],
  },
  optimizations: {
    list: async () => [...MOCK_JOBS],
    get: async (id: string) => {
      const found = MOCK_JOBS.find((j) => j.id === id);
      if (!found) throw new Error('Optimization not found');
      return found;
    },
    create: async ({ name }: { name: string }) => ({ id: 'opt-new', name, status: 'queued' }),
    cancel: async (_id: string) => undefined as void,
    strategies: async (_id: string) => [...MOCK_STRATEGIES],
    benchmarks: async (_id: string) => [...MOCK_BENCHMARKS],
    results: async (_id: string) => [
      { id: 'res-001', metrics: {}, allocation: {} },
      { id: 'res-002', metrics: {}, allocation: {} },
      { id: 'res-003', metrics: {}, allocation: {} },
    ],
    report: async (id: string) => ({
      job_id: id,
      strategies: [...MOCK_STRATEGIES],
      benchmarks: [...MOCK_BENCHMARKS],
      summary: { best_strategy: 'Strategy A' },
    }),
  },
  audit: {
    list: async () => [...MOCK_AUDIT_EVENTS],
  },
  health: async () => ({ status: 'healthy', version: '2.1.0' }),
  knowledgeGraph: {
    search: async (query: string, _nodeTypes: string[]) => ({
      success: true as const,
      data: { nodes: [], edges: [], total: 0 },
      query,
    }),
  },
};
