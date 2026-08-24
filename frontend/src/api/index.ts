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

// ── Helper for paginated list responses ──────────────────────────────
type PaginatedResponse<T> = { data: T[]; meta: { total: number; page_size: number; has_more: boolean; next_cursor: string | null } };

async function paginatedRequest<T>(path: string, params?: Record<string, string | number | undefined>): Promise<PaginatedResponse<T>> {
  const qs = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== '') qs.set(k, String(v));
    });
  }
  return request<PaginatedResponse<T>>(`${path}?${qs.toString()}`);
}

import type {
  User, TokenResponse, Portfolio, DebtInstrument, OptimizationJob,
  Strategy, BenchmarkResult, AuditEvent, Report,
  YieldCurve, FxRate, InterestRate, EconomicIndicator, MarketSnapshot,
  RiskSummary, InvestmentScenario, RiskScore, VaRResult,
  Notification, Watchlist, WatchlistItem, Tag, ActivityEvent, Comment,
  ExportJob,
} from '../types';

export const api = {
  // ── Auth ────────────────────────────────────────────────────────────
  auth: {
    register: (data: { email: string; password: string; name: string; org_name?: string }) =>
      request<TokenResponse>('/auth/register', { method: 'POST', body: JSON.stringify(data) }),
    login: (data: { email: string; password: string }) =>
      request<TokenResponse>('/auth/login', { method: 'POST', body: JSON.stringify(data) }),
    refresh: (refresh_token: string) =>
      request<TokenResponse>('/auth/refresh', { method: 'POST', body: JSON.stringify({ refresh_token }) }),
    logout: () => request<void>('/auth/logout', { method: 'POST' }),
    me: () => request<User>('/auth/me'),
    updateMe: (data: { name?: string; email?: string }) =>
      request<User>('/auth/me', { method: 'PUT', body: JSON.stringify(data) }),
    changePassword: (data: { current_password: string; new_password: string }) =>
      request<void>('/auth/password/change', { method: 'POST', body: JSON.stringify(data) }),
    forgotPassword: (email: string) =>
      request<void>('/auth/forgot-password', { method: 'POST', body: JSON.stringify({ email }) }),
    resetPassword: (token: string, password: string) =>
      request<void>('/auth/reset-password', { method: 'POST', body: JSON.stringify({ token, password }) }),
    verifyEmail: (token: string) =>
      request<void>('/auth/verify-email', { method: 'POST', body: JSON.stringify({ token }) }),
  },

  // ── MFA ─────────────────────────────────────────────────────────────
  mfa: {
    setup: () => request<{ qr_code_svg: string; secret: string; backup_codes: string[] }>('/auth/mfa/setup', { method: 'POST' }),
    enable: (code: string) => request<{ backup_codes: string[] }>('/auth/mfa/enable', { method: 'POST', body: JSON.stringify({ code }) }),
    disable: (code: string) => request<void>('/auth/mfa/disable', { method: 'POST', body: JSON.stringify({ code }) }),
    verify: (code: string) => request<{ verified: boolean }>('/auth/mfa/verify', { method: 'POST', body: JSON.stringify({ code }) }),
    status: () => request<{ enabled: boolean; configured: boolean; backup_codes_remaining: number }>('/auth/mfa/status'),
  },

  // ── Portfolios ──────────────────────────────────────────────────────
  portfolios: {
    list: (params?: { search?: string; page?: number; page_size?: number; sort_by?: string; sort_order?: string }) =>
      paginatedRequest<Portfolio>('/portfolios', params),
    get: (id: string) => request<Portfolio>(`/portfolios/${id}`),
    create: (data: { name: string; description: string; instruments?: Array<Record<string, unknown>> }) =>
      request<Portfolio>('/portfolios', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: string, data: { name?: string; description?: string }) =>
      request<Portfolio>(`/portfolios/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    delete: (id: string) => request<void>(`/portfolios/${id}`, { method: 'DELETE' }),
    upload: (formData: FormData) =>
      request<Portfolio>('/portfolios/upload', { method: 'POST', body: formData }),
    clone: (id: string, data?: { name?: string }) =>
      request<Portfolio>(`/portfolios/${id}/clone`, { method: 'POST', body: JSON.stringify(data || {}) }),
    addInstrument: (portfolioId: string, data: Record<string, unknown>) =>
      request<DebtInstrument>(`/portfolios/${portfolioId}/instruments`, { method: 'POST', body: JSON.stringify(data) }),
    updateInstrument: (portfolioId: string, instrumentId: string, data: Record<string, unknown>) =>
      request<DebtInstrument>(`/portfolios/${portfolioId}/instruments/${instrumentId}`, { method: 'PUT', body: JSON.stringify(data) }),
    deleteInstrument: (portfolioId: string, instrumentId: string) =>
      request<void>(`/portfolios/${portfolioId}/instruments/${instrumentId}`, { method: 'DELETE' }),
    analytics: (id: string) => request<Record<string, unknown>>(`/portfolios/${id}/analytics`),
    riskSummary: (id: string) => request<RiskSummary>(`/portfolios/${id}/risk-summary`),
    investmentScenarios: (id: string, amount: number) =>
      request<{ investment_amount: number; scenarios: InvestmentScenario[] }>(`/portfolios/${id}/investment-scenarios?investment_amount=${amount}`),
    riskScore: (id: string) => request<RiskScore>(`/portfolios/${id}/risk-score`),
    var: (id: string, confidence?: number) =>
      request<VaRResult[]>(`/portfolios/${id}/var?confidence=${confidence || 0.95}`),
  },

  // ── Portfolio Access (RBAC) ─────────────────────────────────────────
  portfolioAccess: {
    list: (portfolioId: string) => request<Array<{ user_id: string; role: string; user_email: string }>>(`/portfolios/${portfolioId}/access`),
    grant: (portfolioId: string, data: { user_id: string; role: string }) =>
      request<void>(`/portfolios/${portfolioId}/access`, { method: 'POST', body: JSON.stringify(data) }),
    update: (portfolioId: string, userId: string, data: { role: string }) =>
      request<void>(`/portfolios/${portfolioId}/access/${userId}`, { method: 'PUT', body: JSON.stringify(data) }),
    revoke: (portfolioId: string, userId: string) =>
      request<void>(`/portfolios/${portfolioId}/access/${userId}`, { method: 'DELETE' }),
  },

  // ── Optimizations ───────────────────────────────────────────────────
  optimizations: {
    list: (params?: { search?: string; page?: number; page_size?: number; status?: string }) =>
      paginatedRequest<OptimizationJob>('/optimizations', params),
    get: (id: string) => request<OptimizationJob>(`/optimizations/${id}`),
    create: (data: Record<string, unknown>) =>
      request<OptimizationJob>('/optimizations', { method: 'POST', body: JSON.stringify(data) }),
    cancel: (id: string) => request<void>(`/optimizations/${id}`, { method: 'DELETE' }),
    strategies: (id: string) => request<Strategy[]>(`/optimizations/${id}/strategies`),
    benchmarks: (id: string) => request<BenchmarkResult[]>(`/optimizations/${id}/benchmarks`),
    results: (id: string) => request<Array<{ id: string; metrics: Record<string, unknown>; allocation: Record<string, number> }>>(`/optimizations/${id}/results`),
    report: (id: string) => request<Report>(`/optimizations/${id}/report`),
    progress: (id: string) => request<{ progress: number; status: string; message?: string }>(`/optimizations/${id}/progress`),
  },

  // ── Audit ───────────────────────────────────────────────────────────
  audit: {
    list: (params?: { limit?: number; offset?: number; action?: string; resource_type?: string; search?: string }) => {
      const qs = new URLSearchParams();
      if (params?.limit) qs.set('limit', String(params.limit));
      if (params?.offset) qs.set('offset', String(params.offset));
      if (params?.action) qs.set('action', params.action);
      if (params?.resource_type) qs.set('resource_type', params.resource_type);
      if (params?.search) qs.set('search', params.search);
      return request<AuditEvent[]>(`/audit?${qs.toString()}`);
    },
  },

  // ── Market Data (Live — Zero API Keys) ──────────────────────────────
  market: {
    yieldCurve: () => request<YieldCurve>('/market/yield-curve'),
    yieldCurveComparison: () => request<{ current: YieldCurve | null; one_month_ago: YieldCurve | null; one_year_ago: YieldCurve | null }>('/market/yield-curve/comparison'),
    fxRates: () => request<Record<string, FxRate>>('/market/fx'),
    fxPair: (pair: string) => request<FxRate>(`/market/fx/${pair}`),
    rates: () => request<{ rates: InterestRate[]; summary: Record<string, number> }>('/market/rates'),
    sofr: () => request<InterestRate>('/market/rates/sofr'),
    ecb: () => request<InterestRate>('/market/rates/ecb'),
    economic: (country: string) => request<EconomicIndicator[]>(`/market/economic/${country}`),
    economicMulti: (countries: string[]) => request<Record<string, EconomicIndicator[]>>(`/market/economic?countries=${countries.join(',')}`),
    snapshot: () => request<MarketSnapshot>('/market/snapshot'),
    cacheStats: () => request<{ cache: Record<string, { size: number; ttl_seconds: number; hit_rate: number }> }>('/market/cache/stats'),
    cacheClear: () => request<{ cleared: number }>('/market/cache/clear', { method: 'POST' }),
  },

  // ── Risk Probabilities ──────────────────────────────────────────────
  risk: {
    summary: (portfolioId: string) => request<RiskSummary>(`/portfolios/${portfolioId}/risk-summary`),
    investmentScenarios: (portfolioId: string, amount: number) =>
      request<{ investment_amount: number; scenarios: InvestmentScenario[] }>(`/portfolios/${portfolioId}/investment-scenarios?investment_amount=${amount}`),
    score: (portfolioId: string) => request<RiskScore>(`/portfolios/${portfolioId}/risk-score`),
    var: (portfolioId: string, confidence?: number) =>
      request<VaRResult[]>(`/portfolios/${portfolioId}/var?confidence=${confidence || 0.95}`),
  },

  // ── Watchlists ──────────────────────────────────────────────────────
  watchlists: {
    list: () => request<Watchlist[]>('/watchlists'),
    get: (id: string) => request<Watchlist>(`/watchlists/${id}`),
    create: (data: { name: string; description: string }) =>
      request<Watchlist>('/watchlists', { method: 'POST', body: JSON.stringify(data) }),
    delete: (id: string) => request<void>(`/watchlists/${id}`, { method: 'DELETE' }),
    addItem: (id: string, data: { instrument_id: string; instrument_name: string; alert_above_pct?: number; alert_below_pct?: number }) =>
      request<WatchlistItem>(`/watchlists/${id}/items`, { method: 'POST', body: JSON.stringify(data) }),
    removeItem: (watchlistId: string, itemId: string) =>
      request<void>(`/watchlists/${watchlistId}/items/${itemId}`, { method: 'DELETE' }),
  },

  // ── Tags ────────────────────────────────────────────────────────────
  tags: {
    list: () => request<Tag[]>('/tags'),
    create: (data: { name: string; color: string }) =>
      request<Tag>('/tags', { method: 'POST', body: JSON.stringify(data) }),
    delete: (id: string) => request<void>(`/tags/${id}`, { method: 'DELETE' }),
    addResource: (tagId: string, data: { resource_type: string; resource_id: string }) =>
      request<void>(`/tags/${tagId}/resources`, { method: 'POST', body: JSON.stringify(data) }),
    removeResource: (tagId: string, resourceType: string, resourceId: string) =>
      request<void>(`/tags/${tagId}/resources/${resourceType}/${resourceId}`, { method: 'DELETE' }),
  },

  // ── Comments ────────────────────────────────────────────────────────
  comments: {
    list: (resourceType: string, resourceId: string) =>
      request<Comment[]>(`/${resourceType}/${resourceId}/comments`),
    create: (resourceType: string, resourceId: string, data: { content: string; parent_id?: string }) =>
      request<Comment>(`/${resourceType}/${resourceId}/comments`, { method: 'POST', body: JSON.stringify(data) }),
    update: (resourceType: string, resourceId: string, commentId: string, data: { content: string }) =>
      request<Comment>(`/${resourceType}/${resourceId}/comments/${commentId}`, { method: 'PUT', body: JSON.stringify(data) }),
    delete: (resourceType: string, resourceId: string, commentId: string) =>
      request<void>(`/${resourceType}/${resourceId}/comments/${commentId}`, { method: 'DELETE' }),
  },

  // ── Notifications ───────────────────────────────────────────────────
  notifications: {
    list: (params?: { unread_only?: boolean; limit?: number; offset?: number }) => {
      const qs = new URLSearchParams();
      if (params?.unread_only) qs.set('unread_only', 'true');
      if (params?.limit) qs.set('limit', String(params.limit));
      if (params?.offset) qs.set('offset', String(params.offset));
      return request<{ data: Notification[]; unread_count: number }>(`/notifications?${qs.toString()}`);
    },
    unreadCount: () => request<{ count: number }>('/notifications/unread-count'),
    markRead: (id: string) => request<void>(`/notifications/${id}/read`, { method: 'POST' }),
    markAllRead: () => request<void>('/notifications/read-all', { method: 'POST' }),
  },

  // ── Activity Log ────────────────────────────────────────────────────
  activity: {
    list: (params?: { user_id?: string; resource_type?: string; action?: string; limit?: number; offset?: number }) => {
      const qs = new URLSearchParams();
      if (params?.user_id) qs.set('user_id', params.user_id);
      if (params?.resource_type) qs.set('resource_type', params.resource_type);
      if (params?.action) qs.set('action', params.action);
      if (params?.limit) qs.set('limit', String(params.limit));
      if (params?.offset) qs.set('offset', String(params.offset));
      return request<{ data: ActivityEvent[]; total: number }>(`/activity?${qs.toString()}`);
    },
    stats: () => request<{ by_action: Record<string, number>; by_resource: Record<string, number>; total: number }>('/activity/stats'),
  },

  // ── Exports ─────────────────────────────────────────────────────────
  exports: {
    list: () => request<ExportJob[]>('/exports'),
    create: (data: { format: string; resource_type: string; resource_id?: string; options?: Record<string, unknown> }) =>
      request<ExportJob>('/exports', { method: 'POST', body: JSON.stringify(data) }),
    status: (id: string) => request<ExportJob>(`/exports/${id}`),
    download: (id: string) => `${API_BASE}/exports/${id}/download`,
  },

  // ── Webhooks ────────────────────────────────────────────────────────
  webhooks: {
    list: () => request<Array<{ id: string; url: string; events: string[]; active: boolean }>>('/webhooks'),
    create: (data: { url: string; events: string[]; secret?: string }) =>
      request<{ id: string; url: string; events: string[]; active: boolean }>('/webhooks', { method: 'POST', body: JSON.stringify(data) }),
    test: (id: string) => request<{ success: boolean; status_code?: number; response_time_ms?: number }>(`/webhooks/${id}/test`, { method: 'POST' }),
    delete: (id: string) => request<void>(`/webhooks/${id}`, { method: 'DELETE' }),
    events: () => request<{ events: Array<{ name: string; description: string }> }>('/webhooks/events'),
  },

  // ── Preferences ─────────────────────────────────────────────────────
  preferences: {
    get: () => request<Record<string, unknown>>('/preferences'),
    update: (data: Record<string, unknown>) =>
      request<Record<string, unknown>>('/preferences', { method: 'PUT', body: JSON.stringify(data) }),
  },

  // ── Organization ────────────────────────────────────────────────────
  organization: {
    settings: () => request<Record<string, unknown>>('/organization/settings'),
    updateSettings: (data: Record<string, unknown>) =>
      request<Record<string, unknown>>('/organization/settings', { method: 'PUT', body: JSON.stringify(data) }),
  },

  // ── Dashboard ───────────────────────────────────────────────────────
  dashboard: {
    summary: () => request<Record<string, unknown>>('/dashboard/summary'),
  },

  // ── Health ──────────────────────────────────────────────────────────
  health: () => request<{ status: string; version: string; database?: string }>('/health'),
};
