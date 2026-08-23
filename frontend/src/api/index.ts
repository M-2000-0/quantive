const API_BASE = '/api';

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('access_token');
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> || {}),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (response.status === 401) {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    window.location.href = '/login';
    throw new Error('Unauthorized');
  }

  if (response.status === 204) return undefined as T;

  const data = await response.json();
  if (!response.ok) {
    const msg = data.detail || 'Request failed';
    if (data.errors) {
      const fieldErrors = data.errors.map((e: { field: string; message: string }) => `${e.field}: ${e.message}`).join('; ');
      throw new Error(`${msg} — ${fieldErrors}`);
    }
    throw new Error(msg);
  }
  return data as T;
}

export const api = {
  auth: {
    register: (data: { email: string; password: string; name: string; org_name?: string }) =>
      request<import('../types').TokenResponse>('/auth/register', { method: 'POST', body: JSON.stringify(data) }),
    login: (data: { email: string; password: string }) =>
      request<import('../types').TokenResponse>('/auth/login', { method: 'POST', body: JSON.stringify(data) }),
    refresh: (refresh_token: string) =>
      request<import('../types').TokenResponse>('/auth/refresh', { method: 'POST', body: JSON.stringify({ refresh_token }) }),
    logout: () => request<void>('/auth/logout', { method: 'POST' }),
    me: () => request<import('../types').User>('/auth/me'),
    updateMe: (data: { name?: string; email?: string }) =>
      request<import('../types').User>('/auth/me', { method: 'PUT', body: JSON.stringify(data) }),
    changePassword: (data: { current_password: string; new_password: string }) =>
      request<void>('/auth/password/change', { method: 'POST', body: JSON.stringify(data) }),
  },
  portfolios: {
    list: () => request<{ portfolios: import('../types').Portfolio[]; total: number }>('/portfolios'),
    get: (id: string) => request<import('../types').Portfolio>(`/portfolios/${id}`),
    create: (data: { name: string; description: string; instruments?: Array<Record<string, unknown>> }) =>
      request<import('../types').Portfolio>('/portfolios', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: string, data: { name?: string; description?: string }) =>
      request<import('../types').Portfolio>(`/portfolios/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    delete: (id: string) => request<void>(`/portfolios/${id}`, { method: 'DELETE' }),
    upload: (formData: FormData) =>
      request<import('../types').Portfolio>('/portfolios/upload', { method: 'POST', body: formData }),
    addInstrument: (portfolioId: string, data: Record<string, unknown>) =>
      request<import('../types').DebtInstrument>(`/portfolios/${portfolioId}/instruments`, { method: 'POST', body: JSON.stringify(data) }),
    updateInstrument: (portfolioId: string, instrumentId: string, data: Record<string, unknown>) =>
      request<import('../types').DebtInstrument>(`/portfolios/${portfolioId}/instruments/${instrumentId}`, { method: 'PUT', body: JSON.stringify(data) }),
    deleteInstrument: (portfolioId: string, instrumentId: string) =>
      request<void>(`/portfolios/${portfolioId}/instruments/${instrumentId}`, { method: 'DELETE' }),
  },
  optimizations: {
    list: () => request<import('../types').OptimizationJob[]>('/optimizations'),
    get: (id: string) => request<import('../types').OptimizationJob>(`/optimizations/${id}`),
    create: (data: Record<string, unknown>) =>
      request<import('../types').OptimizationJob>('/optimizations', { method: 'POST', body: JSON.stringify(data) }),
    cancel: (id: string) => request<void>(`/optimizations/${id}`, { method: 'DELETE' }),
    strategies: (id: string) => request<import('../types').Strategy[]>(`/optimizations/${id}/strategies`),
    benchmarks: (id: string) => request<import('../types').BenchmarkResult[]>(`/optimizations/${id}/benchmarks`),
    results: (id: string) => request<Array<{ id: string; metrics: Record<string, unknown>; allocation: Record<string, number> }>>(`/optimizations/${id}/results`),
    report: (id: string) => request<import('../types').Report>(`/optimizations/${id}/report`),
  },
  audit: {
    list: (params?: { limit?: number; offset?: number; action?: string; resource_type?: string }) => {
      const qs = new URLSearchParams();
      if (params?.limit) qs.set('limit', String(params.limit));
      if (params?.offset) qs.set('offset', String(params.offset));
      if (params?.action) qs.set('action', params.action);
      if (params?.resource_type) qs.set('resource_type', params.resource_type);
      return request<import('../types').AuditEvent[]>(`/audit?${qs.toString()}`);
    },
  },
  health: () => request<{ status: string; version: string }>('/health'),
};
