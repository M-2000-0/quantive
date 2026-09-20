const API_BASE = typeof window !== 'undefined' && (window as any).electronAPI?.isElectron
  ? 'http://127.0.0.1:8000/api'
  : (import.meta as any).env?.VITE_API_URL
    ? `${(import.meta as any).env.VITE_API_URL}/api`
    : '/api';

function getCsrfToken(): string {
  if (typeof document === 'undefined') return '';
  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : '';
}

function requestInit(options: RequestInit = {}): RequestInit {
  const init = { ...options, credentials: 'include' as RequestCredentials };
  if (init.method && init.method.toUpperCase() !== 'GET') {
    const csrfToken = getCsrfToken();
    if (csrfToken) {
      init.headers = {
        ...(init.headers as Record<string, string> || {}),
        'X-CSRF-Token': csrfToken,
      };
    }
  }
  return init;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  // SECURITY: Tokens are in httpOnly/session cookies (sent automatically by browser)
  const init = requestInit(options);
  const headers: Record<string, string> = {
    ...(init.headers as Record<string, string> || {}),
  };
// Cookies are sent automatically — no need for Authorization header
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });

  if (response.status === 403 && !(options as RequestInit & { _retriedCsrf?: boolean })._retriedCsrf) {
    // CSRF token may be missing/expired (e.g. cold start). Refresh the cookie
    // via a GET (middleware issues csrf_token on every GET) and retry once.
    await fetch(`${API_BASE}/health`, { credentials: 'include' }).catch(() => {});
    const retryOptions = { ...options, _retriedCsrf: true } as RequestInit & { _retriedCsrf?: boolean };
    const retryInit = requestInit(retryOptions);
    const retryHeaders: Record<string, string> = {
      ...(retryInit.headers as Record<string, string> || {}),
    };
    if (!(retryOptions.body instanceof FormData)) {
      retryHeaders['Content-Type'] = 'application/json';
    }
    const retry = await fetch(`${API_BASE}${path}`, { ...retryInit, headers: retryHeaders });
    return handleResponse<T>(retry, path);
  }

  return handleResponse<T>(response, path);
}

async function handleResponse<T>(response: Response, path: string): Promise<T> {
  if (response.status === 401) {
    // Clear cookies via logout endpoint
    fetch('/api/auth/logout', { method: 'POST', credentials: 'include' }).catch(() => {});
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
  ExportJob, DashboardSummary, DashboardTask, PortfolioDetail, BenchmarkRow,
  ImpactEvent, EventImpactSummary, ImpactedAsset, Opportunity, PurchaseRecord,
  NewsSource, NewsArticle, NewsDigest, NewsStats,
  Task, TaskComment,
  Deal, PipelineSummary, Campaign, Revenue, Customer, ChurnData,
  Webhook, BackupStatus, PricingResult,
  PilotProgram, GovernmentOpportunity, RFP, GovernmentContact,
  ImmutableAuditEvent, ApprovalRequest, ValidationResult,
  SLACompliance, SLABreach, EscrowAgreement, DRStatus, DRBackup,
  AgentRun, AgentTool, ProjectSummary,
} from '../types';

// Re-export money utilities from shared lib for backward compatibility
export { centsToUsd, dollarsToCents } from '../lib/money';

export const api = {
  // ── Generic request helper (used by feature components) ─────────
  request: <T,>(path: string, options?: RequestInit & { params?: Record<string, string> }): Promise<T> => {
    let url = path;
    if (options?.params) {
      const qs = new URLSearchParams(options.params);
      url += (path.includes('?') ? '&' : '?') + qs.toString();
    }
    const { params: _params, ...init } = options || {};
    return request<T>(url, init);
  },
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
    bulkImport: (formData: FormData) =>
      request<Portfolio>('/portfolios/upload', { method: 'POST', body: formData }),
    importCsv: (file: File, name: string, description?: string) => {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('name', name);
      if (description) fd.append('description', description);
      return request<Portfolio>('/portfolios/upload', { method: 'POST', body: fd });
    },
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
    // NOTE: `/progress` is SSE (text/event-stream). Use `/progress/poll` for JSON polling.
    progress: (id: string) => request<{ job_id: string; progress: number; status: string; error_message?: string | null }>(`/optimizations/${id}/progress/poll`),
    /**
     * Subscribe to job updates via SSE (EventSource) with polling fallback.
     * Returns an unsubscribe function.
     */
    subscribeToJob: (
      id: string,
      onUpdate: (job: OptimizationJob) => void,
      opts?: { intervalMs?: number; onError?: (err: Error) => void }
    ): (() => void) => {
      const intervalMs = opts?.intervalMs ?? 2000;
      let es: EventSource | null = null;
      let intervalId: number | null = null;
      let closed = false;

      const startPolling = () => {
        if (closed) return;
        const tick = async () => {
          try {
            const job = await request<OptimizationJob>(`/optimizations/${id}`);
            if (closed) return;
            onUpdate(job);
            if (['completed', 'failed', 'cancelled'].includes(job.status)) {
              if (intervalId !== null) window.clearInterval(intervalId);
              intervalId = null;
            }
          } catch (e) {
            opts?.onError?.(e instanceof Error ? e : new Error(String(e)));
          }
        };
        void tick();
        intervalId = window.setInterval(tick, intervalMs);
      };

      const canUseSSE = typeof window !== 'undefined' && 'EventSource' in window;
      if (canUseSSE) {
        try {
          const base = `${API_BASE}/optimizations/${encodeURIComponent(id)}/progress`;
          es = new EventSource(base, { withCredentials: true });
          let fallbackDone = false;
          const fallback = () => {
            if (fallbackDone || closed) return;
            fallbackDone = true;
            if (es) { es.close(); es = null; }
            startPolling();
          };
          es.onmessage = (event: MessageEvent) => {
            try {
              const data = JSON.parse(event.data) as Record<string, unknown>;
              if (data['error']) {
                opts?.onError?.(new Error(String(data['error'])));
                fallback();
                return;
              }
              if (data['event'] === 'done') {
                es?.close();
                es = null;
                return;
              }
              const status = (data['status'] as string) ?? (data['state'] as string) ?? 'running';
              const progress = typeof data['progress'] === 'number' ? (data['progress'] as number) : 0;
              // If payload already looks like OptimizationJob (has id), use it directly
              if (data['id'] && data['portfolio_id']) {
                onUpdate(data as unknown as OptimizationJob);
              } else {
                const job: OptimizationJob = {
                  id,
                  portfolio_id: (data['portfolio_id'] as string) ?? '',
                  org_id: (data['org_id'] as string) ?? '',
                  created_by: (data['created_by'] as string) ?? '',
                  name: (data['name'] as string) ?? '',
                  status,
                  optimization_type: (data['optimization_type'] as string) ?? '',
                  objectives: (data['objectives'] as Record<string, unknown>) ?? {},
                  constraints: (data['constraints'] as Record<string, unknown>) ?? {},
                  solver_config: (data['solver_config'] as Record<string, unknown>) ?? {},
                  scenario_config: (data['scenario_config'] as Record<string, unknown>) ?? {},
                  random_seed: (data['random_seed'] as number) ?? 0,
                  model_version: (data['model_version'] as string) ?? '',
                  progress,
                  error_message: (data['error_message'] as string | null) ?? (data['error'] as string | null) ?? null,
                  started_at: (data['started_at'] as string | null) ?? null,
                  completed_at: (data['completed_at'] as string | null) ?? null,
                  created_at: (data['created_at'] as string) ?? new Date().toISOString(),
                  updated_at: (data['updated_at'] as string) ?? new Date().toISOString(),
                };
                onUpdate(job);
              }
              if (['completed', 'failed', 'cancelled'].includes(status)) {
                es?.close();
                es = null;
              }
            } catch {
              // ignore parse errors
            }
          };
          es.onerror = () => {
            fallback();
          };
        } catch {
          startPolling();
        }
      } else {
        startPolling();
      }

      return () => {
        closed = true;
        if (es) { es.close(); es = null; }
        if (intervalId !== null) { window.clearInterval(intervalId); intervalId = null; }
      };
    },
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
    yieldCurveComparison: () => request<{ current: { date: string; rates: Record<string, number> } | null; one_month_ago: { date: string; rates: Record<string, number> } | null; one_year_ago: { date: string; rates: Record<string, number> } | null; fetched_at: string }>('/market/yield-curve/comparison'),
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

  // ── Risk ────────────────────────────────────────────────────────────
  risk: {
    cyberSummary: (entityId: string) => request<{ overall: number; by_category: Record<string, number>; category_counts: Record<string, number> }>(`/risk/cyber/summary?entity_id=${entityId}`),
    fiscalSummary: (entityId: string) => request<{ overall: number; by_category: Record<string, number>; category_counts: Record<string, number> }>(`/risk/fiscal/summary?entity_id=${entityId}`),
    climateSummary: (entityId: string) => request<{ overall: number; by_category: Record<string, number>; category_counts: Record<string, number> }>(`/risk/climate/summary?entity_id=${entityId}`),
    infrastructureSummary: (entityId: string) => request<{ overall: number; by_category: Record<string, number>; category_counts: Record<string, number> }>(`/risk/infrastructure/summary?entity_id=${entityId}`),
    geopoliticalSummary: (entityId: string) => request<{ overall: number; by_category: Record<string, number>; category_counts: Record<string, number> }>(`/risk/geopolitical/summary?entity_id=${entityId}`),
    supplyChainSummary: (entityId: string) => request<{ overall: number; by_category: Record<string, number>; category_counts: Record<string, number> }>(`/risk/supply-chain/summary?entity_id=${entityId}`),
    aggregate: (entityId: string, entityType?: string, weights?: Record<string, number>) => request<{ overall_score: number; by_category: Record<string, number>; category_counts: Record<string, number> }>(`/risk/aggregate/${entityId}?entity_type=${entityType || 'government'}`),
    earlyWarning: (entityId: string) => request<{ signals: Array<{ id: string; name: string; category: string; indicator: string; currentValue: number; threshold: number; unit: string; direction: string; status: string; trend: string; description: string; lastUpdated: string }>; total_signals: number; critical_signals: number }>(`/risk/early-warning/${entityId}`),
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
    portfolioExcel: (portfolioId: string) => `${API_BASE}/exports/portfolio/${portfolioId}.xlsx`,
    optimizationExcel: (jobId: string) => `${API_BASE}/exports/optimization/${jobId}.xlsx`,
    riskExcel: (portfolioId: string) => `${API_BASE}/exports/risk/${portfolioId}.xlsx`,
    riskPdf: (portfolioId: string) => `${API_BASE}/pdf/risk/${portfolioId}.pdf`,
    optimizationPdf: (jobId: string) => `${API_BASE}/pdf/optimization/${jobId}.pdf`,
  },

  // ── Webhooks ────────────────────────────────────────────────────────
  webhooks: {
    list: () => request<Webhook[]>('/webhooks'),
    create: (data: { url: string; events: string[]; secret?: string }) =>
      request<Webhook>('/webhooks', { method: 'POST', body: JSON.stringify(data) }),
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
    summary: () => request<DashboardSummary>('/dashboard/summary'),
    tasks: (limit?: number) => request<DashboardTask[]>(`/dashboard/tasks${limit ? `?limit=${limit}` : ''}`),
  },

  // ── Portfolio Detail ──────────────────────────────────────────────
  portfolioDetail: {
    get: (id: string, params?: { sort_by?: string; sort_order?: string; currency?: string }) => {
      const qs = new URLSearchParams();
      if (params?.sort_by) qs.set('sort_by', params.sort_by);
      if (params?.sort_order) qs.set('sort_order', params.sort_order);
      if (params?.currency) qs.set('currency', params.currency);
      const query = qs.toString();
      return request<PortfolioDetail>(`/portfolio-detail/${id}${query ? `?${query}` : ''}`);
    },
  },

  // ── Solver Leaderboard ────────────────────────────────────────────
  solvers: {
    leaderboard: () => request<BenchmarkRow[]>('/solvers/leaderboard'),
  },

  // ── Procurement Intelligence (Layer 7) ─────────────────────────────
  procurement: {
    listRequests: () => request<{ data: Array<{ id: string; name: string; status: string; value: number; created_at: string }>; meta: { total: number } }>('/procurement'),
    getRequest: (id: string) => request<{ id: string; name: string; status: string; value: number; items: Array<{ name: string; quantity: number; unit_price: number }> }>(`/procurement/${id}`),
    createRequest: (data: { name: string; description?: string; items?: Array<{ name: string; quantity: number; unit_price: number }> }) =>
      request<{ id: string; name: string; status: string; created_at: string }>('/procurement', { method: 'POST', body: JSON.stringify(data) }),
    detectWaste: (requestId: string) =>
      request<{ waste_items: Array<{ type: string; description: string; estimated_savings: number; confidence: number }>; total_waste: number; waste_pct: number }>(`/procurement/${requestId}/waste`),
    wasteSummary: (requestId: string) =>
      request<{ total_waste: number; waste_pct: number; by_type: Record<string, number>; recommendations: string[] }>(`/procurement/${requestId}/waste/summary`),
    detectBottlenecks: (requestId: string) =>
      request<{ bottlenecks: Array<{ stage: string; avg_days: number; count: number; severity: string }>; total_bottlenecks: number }>(`/procurement/${requestId}/bottlenecks`),
    bottlenecksSummary: (requestId: string) =>
      request<{ total_bottlenecks: number; avg_delay_days: number; by_stage: Record<string, number> }>(`/procurement/${requestId}/bottlenecks/summary`),
    benchmarkVendors: (requestId: string, vendorMetrics?: Record<string, unknown>) => {
      const qs = new URLSearchParams();
      if (vendorMetrics) {
        qs.set("vendorMetrics", JSON.stringify(vendorMetrics));
      }
      return request<{ vendors: Array<{ name: string; score: number; price: number; delivery_days: number; quality: number }>; rankings: Array<{ rank: number; vendor: string; score: number }> }>(`/procurement/${requestId}/benchmarks?${qs.toString()}`);
    },
    benchmarksSummary: (requestId: string) =>
      request<{ total_vendors: number; avg_score: number; best_vendor: string; price_range: { min: number; max: number; avg: number } }>(`/procurement/${requestId}/benchmarks/summary`),
    forecastOutcomes: (requestId: string) =>
      request<{ scenarios: Array<{ name: string; probability: number; outcome: string; impact: number }>; expected_savings: number; risk_score: number }>(`/procurement/${requestId}/forecast`),
    forecastSummary: (requestId: string) =>
      request<{ expected_savings: number; risk_score: number; confidence: number; scenarios_count: number }>(`/procurement/${requestId}/forecast/summary`),
    integrate: (requestId: string, problemId?: string) => {
      const qs = new URLSearchParams();
      if (problemId) qs.set("problemId", problemId);
      return request<{ integrated: boolean; optimization_id: string; status: string }>(
        `/procurement/${requestId}/integrate?${qs.toString()}`
      );
    },
    healthCheck: () => request<{ status: string; latency_ms: number; last_check: string }>("/procurement/health/check"),
    // snake_case aliases used by ProcurementDashboard — same endpoints.
    list_requests: () => request<{ data: Array<{ id: string; name: string; status: string; value: number; created_at: string }>; meta: { total: number } }>('/procurement'),
    get_request: (id: string) => request<{ id: string; name: string; status: string; value: number; items: Array<{ name: string; quantity: number; unit_price: number }> }>(`/procurement/${id}`),
    create_request: (data: { name: string; description?: string; items?: Array<{ name: string; quantity: number; unit_price: number }> }) =>
      request<{ id: string; name: string; status: string; created_at: string }>('/procurement', { method: 'POST', body: JSON.stringify(data) }),
    waste_summary: (requestId: string) =>
      request<{ total_waste: number; waste_pct: number; by_type: Record<string, number>; recommendations: string[] }>(`/procurement/${requestId}/waste/summary`),
    bottlenecks_summary: (requestId: string) =>
      request<{ total_bottlenecks: number; avg_delay_days: number; by_stage: Record<string, number> }>(`/procurement/${requestId}/bottlenecks/summary`),
    benchmarks_summary: (requestId: string) =>
      request<{ total_vendors: number; avg_score: number; best_vendor: string; price_range: { min: number; max: number; avg: number } }>(`/procurement/${requestId}/benchmarks/summary`),
    forecast_summary: (requestId: string) =>
      request<{ expected_savings: number; risk_score: number; confidence: number; scenarios_count: number }>(`/procurement/${requestId}/forecast/summary`),
  },

  // ── Security ──────────────────────────────────────────────────────
  security: {
    dashboard: () => request<{ security_score: number; threat_status: { blocked_ips: number; failed_logins: number; status: string }; audit_events_24h: Record<string, number>; user_stats: { total: number; active: number; inactive: number }; recommendations: Array<{ severity: string; message: string; action: string }> }>('/security/dashboard'),
    auditTrail: (params?: { hours?: number; action?: string; user_id?: string }) => {
      const qs = new URLSearchParams();
      if (params?.hours) qs.set('hours', String(params.hours));
      if (params?.action) qs.set('action', params.action);
      if (params?.user_id) qs.set('user_id', params.user_id);
      return request<{ events: Array<{ id: string; actor_email: string; action: string; ip_address: string; created_at: string }>; total: number }>(`/security/audit-trail?${qs.toString()}`);
    },
    blockedIps: () => request<{ blocked_ips: Array<{ ip: string; unblocks_at: string; remaining_seconds: number }>; count: number }>('/security/threats/blocked-ips'),
    unblockIp: (ip: string) => request<{ detail: string }>(`/security/threats/unblock/${ip}`, { method: 'POST' }),
    failedLogins: (hours?: number) => request<{ failed_logins: Array<{ ip: string; attempts: number; emails_targeted: string[]; last_attempt: string }> }>(`/security/threats/failed-logins?hours=${hours || 24}`),
    passwordPolicy: () => request<{ min_length: number; requirements: string[]; lockout_threshold: number; lockout_duration_minutes: number }>('/security/password-policy'),
    healthCheck: () => request<{ status: string; checks: Record<string, string> }>('/security/health'),
  },

  // ── Narrative Engine ───────────────────────────────────────────────
  narrative: {
    report: (jobId: string) => request<{ title: string; date: string; executive_summary: string; market_brief: string; strategies: Array<{ rank: number; name: string; label: string; headline: string; key_metrics: Record<string, string>; strengths: string[]; risks: string[]; recommendation: string }>; risk_assessment: string; peer_comparison: string; implementation_roadmap: string; key_recommendations: string[]; next_steps: string[] }>(`/narrative/report/${jobId}`),
  },

  // ── Country Data ───────────────────────────────────────────────────
  countries: {
    list: (params?: { region?: string; group?: string; min_rating?: string }) => {
      const qs = new URLSearchParams();
      if (params?.region) qs.set('region', params.region);
      if (params?.group) qs.set('group', params.group);
      if (params?.min_rating) qs.set('min_rating', params.min_rating);
      return request<{ countries: Array<{ code: string; name: string; debt_to_gdp: number; rating_sp: string; gdp_growth_pct: number }>; total: number }>(`/countries?${qs.toString()}`);
    },
    get: (code: string) => request<Record<string, unknown>>(`/countries/${code}`),
    compare: (code: string, group?: string) => request<{ countries: Record<string, unknown>[]; averages: Record<string, number>; best_in_class: Record<string, string> }>(`/countries/${code}/compare?group=${group || ''}`),
    stats: () => request<{ total_countries: number; total_gdp_trillions: number; total_debt_trillions: number; avg_debt_to_gdp: number; investment_grade: number; high_yield: number }>(`/countries/stats`),
  },

  // ── AI Advisor ──────────────────────────────────────────────────────
  advisor: {
    ask: (question: string, countryCode?: string) => request<{ answer: string; data: Record<string, unknown>; confidence: number; sources: string[]; suggestions: string[] }>('/advisor/ask', { method: 'POST', body: JSON.stringify({ question, country_code: countryCode || 'US' }) }),
    capabilities: () => request<{ capabilities: Array<{ category: string; examples: string[] }>; supported_countries: string[] }>('/advisor/capabilities'),
  },

  // ── What-If Playground ─────────────────────────────────────────────
  whatif: {
    analyze: (data: { portfolio_id: string; adjustments: Array<{ action: string; amount: number; coupon_rate?: number; tenor_years?: number }> }) =>
      request<{ before: { total_principal: number; weighted_coupon_pct: number; annual_cost: number; num_instruments: number; currency_breakdown: Record<string, { amount: number; pct: number }> }; after: { total_principal: number; weighted_coupon_pct: number; annual_cost: number; num_instruments: number }; impact: { total_change: number; total_change_pct: number; coupon_change_bps: number; annual_cost_change: number; annual_cost_change_pct: number }; adjustments: Array<{ type: string; amount: number; impact: string }>; recommendation: string }>('/whatif/analyze', { method: 'POST', body: JSON.stringify(data) }),
  },

  // ── Compliance (IMF) ────────────────────────────────────────────────
  compliance: {
    dsa: (countryCode: string) =>
      request<{ success: boolean; data: Record<string, unknown> }>(`/compliance/dsa/${countryCode}`),
    mtds: (countryCode: string) =>
      request<{ success: boolean; data: Record<string, unknown> }>(`/compliance/mtds/${countryCode}`),
    gfs: (countryCode: string) =>
      request<{ success: boolean; data: Record<string, unknown> }>(`/compliance/gfs/${countryCode}`),
    debtCeiling: (countryCode: string) =>
      request<{ success: boolean; data: Record<string, unknown> }>(`/compliance/debt-ceiling/${countryCode}`),
    allReports: (countryCode: string) =>
      request<{ success: boolean; data: Record<string, unknown> }>(`/compliance/reports/${countryCode}`),
  },

  // ── Explainability ──────────────────────────────────────────────────
  explain: {
    strategy: (data: { strategy: Record<string, unknown>; portfolio_data: Record<string, unknown>; country_code: string }) =>
      request<{ success: boolean; data: Record<string, unknown> }>('/explain/strategy', { method: 'POST', body: JSON.stringify(data) }),
    methodology: () =>
      request<{ success: boolean; data: Record<string, unknown> }>('/explain/methodology'),
  },

  // ── Risk Intelligence ──────────────────────────────────────────────
  riskIntel: {
    sanctionsScreen: (instruments: Array<Record<string, unknown>>) =>
      request<{ success: boolean; data: Record<string, unknown> }>('/risk-intel/sanctions/screen', { method: 'POST', body: JSON.stringify({ instruments }) }),
    sanctionsCountry: (countryCode: string) =>
      request<{ success: boolean; data: Record<string, unknown> }>(`/risk-intel/sanctions/country/${countryCode}`),
    sanctionsEntity: (name: string, country?: string) =>
      request<{ success: boolean; data: Record<string, unknown> }>(`/risk-intel/sanctions/entity/${name}${country ? `?country=${country}` : ''}`),
    liquidityPortfolio: (instruments: Array<Record<string, unknown>>) =>
      request<{ success: boolean; data: Record<string, unknown> }>('/risk-intel/liquidity/portfolio', { method: 'POST', body: JSON.stringify({ instruments }) }),
    liquidityStressTest: (instruments: Array<Record<string, unknown>>, scenario?: string) =>
      request<{ success: boolean; data: Record<string, unknown> }>(`/risk-intel/liquidity/stress-test?scenario=${scenario || 'global'}`, { method: 'POST', body: JSON.stringify({ instruments }) }),
    politicalRisk: (countryCode: string) =>
      request<{ success: boolean; data: Record<string, unknown> }>(`/risk-intel/political/${countryCode}`),
    portfolioPoliticalRisk: (instruments: Array<Record<string, unknown>>) =>
      request<{ success: boolean; data: Record<string, unknown> }>('/risk-intel/political/portfolio', { method: 'POST', body: JSON.stringify({ instruments }) }),
    contagionCascade: (triggerCountry: string, instruments: Array<Record<string, unknown>>, severityBps?: number) =>
      request<{ success: boolean; data: Record<string, unknown> }>(`/risk-intel/contagion/cascade?trigger_country=${triggerCountry}&severity_bps=${severityBps || 500}`, { method: 'POST', body: JSON.stringify({ instruments }) }),
    contagionLinkages: (countryCode: string) =>
      request<{ success: boolean; data: Record<string, unknown> }>(`/risk-intel/contagion/linkages/${countryCode}`),
    systemicRisk: (instruments: Array<Record<string, unknown>>) =>
      request<{ success: boolean; data: Record<string, unknown> }>('/risk-intel/contagion/systemic', { method: 'POST', body: JSON.stringify({ instruments }) }),
  },

  // ── Market Health ────────────────────────────────────────────────
  marketHealth: {
    checkAll: () => request<{ status: string; summary: { live: number; fallback: number; error: number; total: number; avg_latency_ms: number }; sources: Array<{ name: string; provider: string; url: string; status: string; latency_ms: number | null; last_value: string | null; error: string | null; tested_at: string }> }>('/market/health'),
    checkSource: (source: string) => request<{ name: string; provider: string; url: string; status: string; latency_ms: number | null; last_value: string | null; error: string | null; tested_at: string }>(`/market/health/${source}`),
  },

  // ── First-Run Wizard ────────────────────────────────────────────────
  firstRun: {
    status: () => request<{ completed: boolean; steps: Array<{ name: string; status: string; completed_at: string | null }> }>('/first-run/status'),
    createDemoPortfolio: () => request<{ id: string; name: string; instruments_count: number }>('/first-run/demo-portfolio', { method: 'POST' }),
    quickOptimize: (portfolioId?: string) => {
      const qs = portfolioId ? `?portfolio_id=${portfolioId}` : '';
      return request<{ job_id: string; status: string; strategies_count: number }>(`/first-run/quick-optimize${qs}`, { method: 'POST' });
    },
    savingsOpportunity: (portfolioId?: string) => {
      const qs = portfolioId ? `?portfolio_id=${portfolioId}` : '';
      return request<{ annual_savings: number; savings_pct: number; recommendations: string[] }>(`/first-run/savings-opportunity${qs}`);
    },
    quickStartData: () => request<{ portfolios: Array<{ id: string; name: string }>; recent_jobs: Array<{ id: string; name: string; status: string }> }>('/first-run/quick-start-data'),
  },

  // ── Savings Dashboard ────────────────────────────────────────────────
  savings: {
    summary: () => request<{ total_savings: number; monthly_savings: number; ytd_savings: number; by_category: Record<string, number> }>('/savings/summary'),
    history: (days?: number) => request<{ entries: Array<{ date: string; amount: number; category: string }>; total: number }>(`/savings/history${days ? `?days=${days}` : ''}`),
    comparison: (portfolioId?: string) => {
      const qs = portfolioId ? `?portfolio_id=${portfolioId}` : '';
      return request<{ before: { annual_cost: number }; after: { annual_cost: number }; savings: number; savings_pct: number }>(`/savings/comparison${qs}`);
    },
    milestones: () => request<{ milestones: Array<{ name: string; target: number; current: number; achieved: boolean; achieved_at: string | null }>; total_achieved: number }>('/savings/milestones'),
  },

  // ── Market Pulse ─────────────────────────────────────────────────────
  marketPulse: {
    get: () => request<{ sentiment: string; fear_greed_index: number; key_events: Array<{ title: string; impact: string; category: string }>; updated_at: string }>('/market-pulse'),
    yieldCurve: () => request<{ current: Record<string, number>; change_1w: Record<string, number>; change_1m: Record<string, number>; inversion: boolean; updated_at: string }>('/market-pulse/yield-curve'),
    refinancingWindows: () => request<{ windows: Array<{ currency: string; window: string; rate_advantage_bps: number; expiry: string; confidence: number }>; best_opportunity: { currency: string; savings_bps: number } }>('/market-pulse/refinancing-windows'),
  },

  // ── Daily Briefing ───────────────────────────────────────────────────
  briefing: {
    get: () => request<{ date: string; summary: string; key_metrics: Record<string, string>; action_items: Array<{ title: string; priority: string; due_date: string | null }>; market_overview: string }>('/briefing'),
    actionItems: () => request<{ items: Array<{ id: string; title: string; description: string; priority: string; due_date: string | null; status: string }>; total: number; overdue: number }>('/briefing/action-items'),
    maturityTimeline: (days?: number) => request<{ events: Array<{ date: string; instrument: string; amount: number; type: string }>; total_maturities: number; total_amount: number }>(`/briefing/maturity-timeline${days ? `?horizon_days=${days}` : ''}`),
  },

  // ── Asset Tracker ────────────────────────────────────────────────────
  assets: {
    getAll: () => request<Record<string, unknown>>('/assets/all'),
    crypto: {
      list: () => request<Record<string, unknown>>('/assets/crypto'),
      detail: (coinId: string) => request<Record<string, unknown>>(`/assets/crypto/${coinId}`),
      history: (coinId: string, days?: number) => request<Record<string, unknown>>(`/assets/crypto/${coinId}/history?days=${days || 30}`),
      fearGreed: () => request<Record<string, unknown>>('/assets/crypto/fear-greed'),
    },
    commodities: {
      list: () => request<Record<string, unknown>>('/assets/commodities'),
      detail: (symbol: string) => request<Record<string, unknown>>(`/assets/commodities/${encodeURIComponent(symbol)}`),
    },
    fx: {
      list: () => request<Record<string, unknown>>('/assets/fx'),
      detail: (pair: string) => request<Record<string, unknown>>(`/assets/fx/${pair}`),
    },
    correlation: (assets?: string, days?: number) => {
      const qs = new URLSearchParams();
      if (assets) qs.set('assets', assets);
      if (days) qs.set('days', String(days));
      return request<Record<string, unknown>>(`/assets/correlation?${qs.toString()}`);
    },
    allocation: (portfolioId?: string) => {
      const qs = portfolioId ? `?portfolio_id=${portfolioId}` : '';
      return request<Record<string, unknown>>(`/assets/allocation${qs}`);
    },
  },

  // ── Health ──────────────────────────────────────────────────────────
  health: () => request<{ status: string; version: string; database?: string }>('/health'),

  // ── Maturity Ladder ──────────────────────────────────────────────
  getMaturityLadder: (portfolioId: string, horizon?: number) =>
    request<unknown>(`/maturity/ladder/${portfolioId}?horizon_years=${horizon || 20}`),
  getCashFlowProjection: (portfolioId: string, horizon?: number, budget?: number) =>
    request<unknown>(`/maturity/cashflow/${portfolioId}?horizon_years=${horizon || 15}&annual_budget=${budget || 0}`),
  getRefinancingRecommendations: (portfolioId: string) =>
    request<unknown>(`/maturity/recommendations/${portfolioId}`),
  getFullMaturityAnalysis: (portfolioId: string, horizon?: number, budget?: number) =>
    request<unknown>(`/maturity/analyze/${portfolioId}?horizon_years=${horizon || 20}&annual_budget=${budget || 0}`),

  // ── ESG / Green Bonds ────────────────────────────────────────────
  getESGScores: (portfolioId: string, countryCode?: string) =>
    request<unknown>(`/esg/score/${portfolioId}?country_code=${countryCode || 'US'}`),
  getCarbonScenarios: (countryCode: string) =>
    request<unknown>(`/esg/carbon-scenarios/${countryCode}`),
  getGreenCriteria: () =>
    request<unknown>('/esg/green-criteria'),
  getCountryESGScores: () =>
    request<unknown>('/esg/country-scores'),

  // ── Rating Simulator ─────────────────────────────────────────────
  simulateRatings: (countryCode: string) =>
    request<unknown>(`/ratings/simulate/${countryCode}`),
  simulateRatingsWithShocks: (countryCode: string, shocks: Record<string, number>) =>
    request<unknown>(`/ratings/simulate/${countryCode}`, { method: 'POST', body: JSON.stringify(shocks) }),
  getRatingScales: () =>
    request<unknown>('/ratings/scale'),
  getRatingCountryData: (countryCode: string) =>
    request<unknown>(`/ratings/country/${countryCode}`),
  getRatingCountries: () =>
    request<unknown>('/ratings/countries'),

  // SOC 2 Compliance
  soc2PentestScan: () =>
    request<{ scan_date: string; total_findings: number; by_category: Record<string, { name: string; count: number; findings: unknown[] }>; severity_summary: Record<string, number>; readiness_score: number; recommendations: { priority: string; action: string }[] }>('/soc2/pentest/scan'),

  soc2DRRunbooks: () =>
    request<{ generated_at: string; scenarios: Record<string, unknown>; total: number }>('/soc2/dr/runbooks'),

  soc2DRRunbook: (scenario: string) =>
    request<{ scenario: string; severity: string; rto_hours: number; rpo_hours: number; steps: unknown[]; rollback: string; communication: string[]; verification: string[] }>(`/soc2/dr/runbook/${scenario}`),

  soc2EvidenceSummary: () =>
    request<{ total_evidence_items: number; verified: number; verification_rate: string; by_category: Record<string, number>; criteria_covered: number; criteria_missing: string[]; readiness_score: number }>('/soc2/evidence/summary'),

  soc2ComplianceOverview: () =>
    request<{ criteria: { id: string; name: string; score: number; status: string; controls: { name: string; implemented: boolean }[] }[]; overall_score: number; total_controls: number; implemented_controls: number }>('/soc2/compliance/overview'),

  quantumReadiness: () =>
    request<{ overall_score: number; dimensions: { name: string; score: number; target: number; modules: string[]; status: string; details: string }[]; total_modules: number; active_modules: number; last_scan: string }>('/quantum/readiness'),

  quantumModules: () =>
    request<{ total: number; active: number; modules: { path: string; name: string; pillar: string; status: string }[] }>('/quantum/modules'),

  quantumCircuit: (params: { num_qubits?: number; theta?: number; circuit_type?: string; layers?: number }) => {
    const qs = new URLSearchParams();
    if (params.num_qubits) qs.set('num_qubits', String(params.num_qubits));
    if (params.theta) qs.set('theta', String(params.theta));
    if (params.circuit_type) qs.set('circuit_type', params.circuit_type);
    if (params.layers) qs.set('layers', String(params.layers));
    return request<{ qasm3: string; circuit_id: string; num_qubits: number; depth: number; gate_count: Record<string, number> }>(`/quantum/openqasm3/circuit?${qs.toString()}`);
  },

  quantumBackends: () =>
    request<{ backends: { key: string; name: string; status: string; max_qubits: number; avg_gate_error: number; cost_per_shot: number; uptime: number }[] }>('/quantum/openqasm3/backends'),

  quantumDispatch: (body: { qasm3_code: string; shots?: number; noise_mitigation?: boolean; backend_override?: string }) =>
    request<Record<string, unknown>>('/quantum/openqasm3/dispatch', { method: 'POST', body: JSON.stringify(body) }),

  quantumZKProve: (body: { total_debt_usd: number; foreign_currency_debt_usd: number; max_single_year_refinance_usd: number; liquid_reserves_usd: number; total_revenue_usd: number; margin_usd: number; statutory_ceiling_usd: number; jurisdiction?: string }) =>
    request<{ proof_id: string; all_satisfied: boolean; constraints_proven: string[]; constraints_total: number; verification_key: string; proof_hash: string; generation_time_ms: number }>('/quantum/zk/prove', { method: 'POST', body: JSON.stringify(body) }),

  quantumZKReport: (body: { total_debt_usd: number; foreign_currency_debt_usd: number; max_single_year_refinance_usd: number; liquid_reserves_usd: number; total_revenue_usd: number; margin_usd: number; statutory_ceiling_usd: number; jurisdiction?: string }) =>
    request<{ compliance_score: number; constraints: Record<string, { status: string; actual: number; limit: number }>; violations: { type: string; description: string; severity: string }[] }>('/quantum/zk/report', { method: 'POST', body: JSON.stringify(body) }),

  quantumQAESimulate: (body: { shock_probability?: number; shots?: number; num_evaluation_qubits?: number }) =>
    request<{ estimated_probability: number; confidence_interval: [number, number]; circuit_depth: number; total_qubits: number; metadata: Record<string, unknown> }>('/quantum/qae/simulate', { method: 'POST', body: JSON.stringify(body) }),

  quantumQAEVaR: (body: { shock_probability?: number; portfolio_value?: number; confidence_level?: number; num_evaluation_qubits?: number }) =>
    request<{ var_estimate: number; expected_shortfall: number; confidence_level: number; loss_distribution: Record<string, number>; qae_precision: number; speedup_vs_classical: number; num_scenarios_evaluated: number }>('/quantum/qae/tail-risk', { method: 'POST', body: JSON.stringify(body) }),

  quantumQAEAnalyze: (params: { shock_probability?: number; num_evaluation_qubits?: number }) => {
    const qs = new URLSearchParams();
    if (params.shock_probability) qs.set('shock_probability', String(params.shock_probability));
    if (params.num_evaluation_qubits) qs.set('num_evaluation_qubits', String(params.num_evaluation_qubits));
    return request<{ circuit_id: string; num_evaluation_qubits: number; total_qubits: number; circuit_depth: number; precision: number; rotation_angle: number; total_gates: number; performance_comparison: Record<string, number> }>(`/quantum/qae/analyze?${qs.toString()}`);
  },

  // ── News ─────────────────────────────────────────────────────────────
  news: {
    listSources: () => request<NewsSource[]>('/news/sources'),
    createSource: (data: { name: string; source_type: string; url?: string; config_json?: Record<string, unknown> }) =>
      request<NewsSource>('/news/sources', { method: 'POST', body: JSON.stringify(data) }),
    deleteSource: (id: string) => request<void>(`/news/sources/${id}`, { method: 'DELETE' }),
    toggleSource: (id: string) => request<{ is_active: boolean }>(`/news/sources/${id}/toggle`, { method: 'POST' }),
    listArticles: (params?: { category?: string; ticker?: string; search?: string; starred_only?: boolean; limit?: number; offset?: number }) => {
      const qs = new URLSearchParams();
      if (params) Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') qs.set(k, String(v)); });
      return request<NewsArticle[]>(`/news/articles?${qs.toString()}`);
    },
    getArticle: (id: string) => request<NewsArticle>(`/news/articles/${id}`),
    markRead: (id: string) => request<void>(`/news/articles/${id}/read`, { method: 'POST' }),
    toggleStar: (id: string) => request<{ is_starred: boolean }>(`/news/articles/${id}/star`, { method: 'POST' }),
    getDigest: (hours?: number) => request<NewsDigest>(`/news/digest${hours ? `?hours=${hours}` : ''}`),
    ingest: () => request<{ ingested: number; errors: number }>('/news/ingest', { method: 'POST' }),
    getStats: () => request<NewsStats>('/news/stats'),
  },

  // ── Tasks ────────────────────────────────────────────────────────────
  tasks: {
    list: (params?: { status?: string; priority?: string; assigned_to?: string; limit?: number; offset?: number }) => {
      const qs = new URLSearchParams();
      if (params) Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') qs.set(k, String(v)); });
      return request<Task[]>(`/tasks?${qs.toString()}`);
    },
    create: (data: { title: string; description?: string; priority?: string; assigned_to?: string; due_date?: string }) =>
      request<Task>('/tasks', { method: 'POST', body: JSON.stringify(data) }),
    get: (id: string) => request<Task>(`/tasks/${id}`),
    update: (id: string, data: Record<string, unknown>) =>
      request<Task>(`/tasks/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    delete: (id: string) => request<void>(`/tasks/${id}`, { method: 'DELETE' }),
    listComments: (id: string) => request<TaskComment[]>(`/tasks/${id}/comments`),
    addComment: (id: string, content: string) =>
      request<TaskComment>(`/tasks/${id}/comments`, { method: 'POST', body: JSON.stringify({ content }) }),
  },

  // ── Meetings ─────────────────────────────────────────────────────────
  meetings: {
    list: (params?: { start_after?: string; limit?: number; offset?: number }) => {
      const qs = new URLSearchParams();
      if (params) Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') qs.set(k, String(v)); });
      return request<Array<{ id: string; title: string; description: string; start_time: string; end_time: string; location: string | null; meeting_url: string | null; created_at: string }>>(`/meetings?${qs.toString()}`);
    },
    create: (data: { title: string; description?: string; start_time: string; end_time: string; location?: string; meeting_url?: string; attendee_ids?: string[] }) =>
      request<{ id: string; title: string; description: string; start_time: string; end_time: string; created_at: string }>('/meetings', { method: 'POST', body: JSON.stringify(data) }),
    get: (id: string) => request<{ id: string; title: string; description: string; start_time: string; end_time: string; location: string | null; meeting_url: string | null; attendees: Array<{ user_id: string; name: string; email: string; status: string }> }>(`/meetings/${id}`),
    update: (id: string, data: Record<string, unknown>) =>
      request<{ id: string; title: string; updated_at: string }>(`/meetings/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    delete: (id: string) => request<void>(`/meetings/${id}`, { method: 'DELETE' }),
    rsvp: (id: string, status: string) => request<{ status: string }>(`/meetings/${id}/rsvp?status=${status}`, { method: 'POST' }),
    listAttendees: (id: string) => request<Array<{ user_id: string; name: string; email: string; status: string }>>(`/meetings/${id}/attendees`),
  },

  // ── AI Intelligence ──────────────────────────────────────────────────
  ai: {
    getMarketSummary: (useLlm?: boolean) => request<{ summary: string; sentiment: string; key_points: string[]; confidence: number; sources: string[] }>(`/ai/market-summary${useLlm ? '?use_llm=true' : ''}`),
    getNewsSummary: (hours?: number) => request<{ summary: string; articles_analyzed: number; sentiment: number; key_themes: string[] }>(`/ai/news-summary${hours ? `?hours=${hours}` : ''}`),
    getArticleSummary: (id: string) => request<{ summary: string; sentiment: number; key_points: string[]; entities: string[] }>(`/ai/news-summary/${id}`),
    explainStock: (symbol: string) => request<{ symbol: string; name: string; explanation: string; metrics: Record<string, number>; risks: string[]; opportunities: string[] }>(`/ai/explain-stock/${symbol}`),
    getSignalConflicts: (symbol: string) => request<{ symbol: string; conflicts: Array<{ signal_a: string; signal_b: string; conflict_type: string; description: string; severity: string }> }>(`/ai/signal-conflicts/${symbol}`),
    getModelPerformance: (params?: { model_name?: string; hours?: number }) => {
      const qs = new URLSearchParams();
      if (params) Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') qs.set(k, String(v)); });
      return request<{ models: Array<{ name: string; accuracy: number; latency_ms: number; predictions: number; last_trained: string }>; overall_accuracy: number }>(`/ai/model-performance?${qs.toString()}`);
    },
    getDriftAlerts: () => request<{ alerts: Array<{ id: string; model: string; metric: string; current_value: number; threshold: number; severity: string; detected_at: string }>; total: number; critical: number }>('/ai/drift-alerts'),
  },

  // ── Support ──────────────────────────────────────────────────────────
  support: {
    listTickets: (params?: { status?: string; priority?: string; category?: string; limit?: number; offset?: number }) => {
      const qs = new URLSearchParams();
      if (params) Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') qs.set(k, String(v)); });
      return request<Array<{ id: string; subject: string; description: string; status: string; priority: string; category: string; created_at: string; updated_at: string }>>(`/support/tickets?${qs.toString()}`);
    },
    createTicket: (data: { subject: string; description: string; category?: string; priority?: string }) =>
      request<{ id: string; subject: string; status: string; created_at: string }>('/support/tickets', { method: 'POST', body: JSON.stringify(data) }),
    getTicket: (id: string) => request<{ id: string; subject: string; description: string; status: string; priority: string; category: string; messages: Array<{ id: string; content: string; is_internal: boolean; created_by: string; created_at: string }>; created_at: string }>(`/support/tickets/${id}`),
    updateTicket: (id: string, data: Record<string, unknown>) =>
      request<{ id: string; status: string; updated_at: string }>(`/support/tickets/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    listTicketMessages: (id: string) => request<Array<{ id: string; content: string; is_internal: boolean; created_by: string; created_at: string }>>(`/support/tickets/${id}/messages`),
    addTicketMessage: (id: string, content: string, isInternal?: boolean) =>
      request<{ id: string; content: string; is_internal: boolean; created_at: string }>(`/support/tickets/${id}/messages`, { method: 'POST', body: JSON.stringify({ content, is_internal: isInternal }) }),
    listFaq: () => request<Array<{ id: string; question: string; answer: string; category: string; helpful_count: number; created_at: string }>>('/support/faq'),
    createFaqCategory: (data: { name: string; description?: string }) =>
      request<{ id: string; name: string; description: string }>('/support/faq/categories', { method: 'POST', body: JSON.stringify(data) }),
    createFaqItem: (data: { category_id: string; question: string; answer: string }) =>
      request<{ id: string; question: string; answer: string; category_id: string }>('/support/faq/items', { method: 'POST', body: JSON.stringify(data) }),
    markFaqHelpful: (id: string) => request<{ helpful_count: number }>(`/support/faq/items/${id}/helpful`, { method: 'POST' }),
    listBugs: (params?: { status?: string; severity?: string; limit?: number }) => {
      const qs = new URLSearchParams();
      if (params) Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') qs.set(k, String(v)); });
      return request<Array<{ id: string; title: string; description: string; status: string; severity: string; steps_to_reproduce: string | null; expected_behavior: string | null; actual_behavior: string | null; environment: string | null; created_at: string }>>(`/support/bugs?${qs.toString()}`);
    },
    createBug: (data: { title: string; description: string; severity?: string; steps_to_reproduce?: string; expected_behavior?: string; actual_behavior?: string; environment?: string }) =>
      request<{ id: string; title: string; status: string; created_at: string }>('/support/bugs', { method: 'POST', body: JSON.stringify(data) }),
    updateBug: (id: string, data: Record<string, unknown>) =>
      request<{ id: string; status: string; updated_at: string }>(`/support/bugs/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    chat: (content: string) =>
      request<{ response: string; suggestions: string[] }>('/support/chat', { method: 'POST', body: JSON.stringify({ content }) }),
  },

  // ── Management ───────────────────────────────────────────────────────
  management: {
    getRevenue: () => request<Revenue>('/management/revenue'),
    getMRR: () => request<{ mrr: number; growth: number }>('/management/mrr'),
    getCustomers: () => request<Customer[]>('/management/customers'),
    getChurn: () => request<ChurnData>('/management/churn'),
    listDeals: (params?: { stage?: string; limit?: number }) => {
      const qs = new URLSearchParams();
      if (params) Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') qs.set(k, String(v)); });
      return request<Deal[]>(`/management/pipeline?${qs.toString()}`);
    },
    createDeal: (data: { name: string; company?: string; value?: number; stage?: string; probability?: number; expected_close_date?: string; notes?: string }) =>
      request<Deal>('/management/pipeline', { method: 'POST', body: JSON.stringify(data) }),
    updateDeal: (id: string, data: Record<string, unknown>) =>
      request<Deal>(`/management/pipeline/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    deleteDeal: (id: string) => request<void>(`/management/pipeline/${id}`, { method: 'DELETE' }),
    getPipelineSummary: () => request<PipelineSummary>('/management/pipeline/summary'),
    listCampaigns: () => request<Campaign[]>('/management/campaigns'),
    createCampaign: (data: { name: string; subject: string; body: string }) =>
      request<Campaign>('/management/campaigns', { method: 'POST', body: JSON.stringify(data) }),
    getActivity: (hours?: number) => request<Array<{ type: string; description: string; timestamp: string }>>(`/management/activity${hours ? `?hours=${hours}` : ''}`),
  },

  // ── Backup ───────────────────────────────────────────────────────────
  backup: {
    getStatus: () => request<BackupStatus>('/backup/status'),
    trigger: () => request<{ backup_id: string; status: string }>('/backup/trigger', { method: 'POST' }),
    verify: () => request<{ verified: boolean; integrity: string }>('/backup/verify'),
  },

  // ── Sovereign Debt Transparency Index ─────────────────────────────────
  transparencyIndex: {
    country: (countryCode: string) => request<{ code: string; name: string; overall_score: number; rank: number; categories: Record<string, { score: number; rank: number }>; data_quality: string; last_updated: string }>(`/transparency-index/countries/${countryCode}`),
    allCountries: () => request<Array<{ code: string; name: string; overall_score: number; rank: number; data_quality: string }>>('/transparency-index/countries'),
    calculate: (countryCode: string) => request<{ code: string; overall_score: number; categories: Record<string, number>; calculated_at: string }>(`/transparency-index/calculate/${countryCode}`, { method: 'POST' }),
    globalStats: () => request<{ total_countries: number; avg_score: number; top_performers: Array<{ code: string; name: string; score: number }>; bottom_performers: Array<{ code: string; name: string; score: number }> }>('/transparency-index/stats'),
    batchCalculate: (countryCodes: string[]) =>
      request<{ results: Array<{ code: string; score: number; status: string }>; total: number }>('/transparency-index/batch-calculate', { method: 'POST', body: JSON.stringify({ country_codes: countryCodes }) }),
    compare: (countryCodes: string[]) =>
      request<{ countries: Record<string, { score: number; rank: number; categories: Record<string, number> }>; averages: Record<string, number>; best_in_class: Record<string, string> }>('/transparency-index/compare', { method: 'POST', body: JSON.stringify({ country_codes: countryCodes }) }),
  },

  // ── Outcome-Based Pricing ────────────────────────────────────────────
  pricing: {
    calculate: (debtOutstanding: number, currency: string, optimizationType: string) =>
      request<PricingResult>('/pricing/calculate', {
        method: 'POST',
        body: JSON.stringify({ debt_outstanding_usd: debtOutstanding, currency, optimization_type: optimizationType }),
      }),
    customize: (config: Record<string, unknown>) =>
      request<PricingResult>('/pricing/customize', { method: 'POST', body: JSON.stringify(config) }),
    availableOptimizations: () => request<Array<{ id: string; name: string; description: string; base_price: number }>>('/pricing/optimizations'),
  },

  // ── Sovereign Mode ───────────────────────────────────────────────────
  sovereignMode: {
    status: () => request<{ enabled: boolean; activated_at: string | null; security_level: string; features: string[] }>('/sovereign-mode/status'),
    enable: () => request<{ enabled: boolean; activated_at: string; security_level: string }>('/sovereign-mode/enable', { method: 'POST' }),
    disable: () => request<{ enabled: boolean; deactivated_at: string }>('/sovereign-mode/disable', { method: 'POST' }),
    securityChecklist: () => request<{ items: Array<{ id: string; name: string; description: string; status: string; last_verified: string | null }>; score: number; total: number; passed: number }>('/sovereign-mode/security-checklist'),
  },

  // ── Pilot Program ────────────────────────────────────────────────────
  pilotProgram: {
    dashboard: () => request<{ total_programs: number; active: number; completed: number; metrics: Record<string, number> }>('/pilot-programs/dashboard'),
    list: () => request<{ programs: PilotProgram[] }>('/pilot-programs/list'),
    create: (data: { name: string; description?: string; start_date?: string }) =>
      request<PilotProgram>('/pilot-programs/create', { method: 'POST', body: JSON.stringify(data) }),
    status: (programId: string) => request<PilotProgram>(`/pilot-programs/${programId}/status`),
    transition: (programId: string, status: string, data?: Record<string, unknown>) =>
      request<PilotProgram>(`/pilot-programs/${programId}/transition`, {
        method: 'POST',
        body: JSON.stringify({ new_status: status, ...data }),
      }),
    caseStudy: (programId: string) => request<{ title: string; summary: string; metrics: Record<string, unknown>; lessons: string[] }>(`/pilot-programs/${programId}/case-study`),
  },

  // ── Government Relations ─────────────────────────────────────────────
  governmentRelations: {
    dashboard: () => request<{ total_opportunities: number; total_value: number; by_status: Record<string, number>; recent_activity: Array<{ type: string; description: string; timestamp: string }> }>('/government-relations/dashboard'),
    createOpportunity: (data: { title: string; agency: string; value?: number; deadline?: string }) =>
      request<GovernmentOpportunity>('/government-relations/opportunities', { method: 'POST', body: JSON.stringify(data) }),
    listOpportunities: (params?: { status?: string; agency?: string; limit?: number }) => {
      const qs = new URLSearchParams();
      if (params) Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') qs.set(k, String(v)); });
      return request<GovernmentOpportunity[]>(`/government-relations/opportunities?${qs.toString()}`);
    },
    createRFP: (data: { title: string; agency: string; deadline?: string; requirements?: string[] }) =>
      request<RFP>('/government-relations/rfp', { method: 'POST', body: JSON.stringify(data) }),
    listRFPs: () => request<RFP[]>('/government-relations/rfp'),
    addContact: (data: { name: string; title: string; agency: string; email: string; phone?: string }) =>
      request<GovernmentContact>('/government-relations/contacts', { method: 'POST', body: JSON.stringify(data) }),
    listContacts: () => request<GovernmentContact[]>('/government-relations/contacts'),
  },

  // ── Immutable Audit Trail ────────────────────────────────────────────
  immutableAudit: {
    record: (data: { event_type: string; actor_id: string; data: Record<string, unknown> }) =>
      request<ImmutableAuditEvent>('/immutable-audit/record', { method: 'POST', body: JSON.stringify(data) }),
    verify: (eventId: string) => request<ImmutableAuditEvent>(`/immutable-audit/verify/${eventId}`),
    verifyChain: (start: string, end: string) =>
      request<{ valid: boolean; chain_length: number; broken_at: string | null }>('/immutable-audit/verify-chain', { method: 'POST', body: JSON.stringify({ start_event_id: start, end_event_id: end }) }),
    query: (params: { event_type?: string; actor_id?: string; start_date?: string; end_date?: string; limit?: number }) => {
      const qs = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') qs.set(k, String(v)); });
      return request<ImmutableAuditEvent[]>(`/immutable-audit/events?${qs.toString()}`);
    },
    export: (eventId: string) => request<{ event: ImmutableAuditEvent; certificate: string }>(`/immutable-audit/export/${eventId}`),
  },

  // ── Approval Workflow ────────────────────────────────────────────────
  approvalWorkflow: {
    request: (data: { type: string; data: Record<string, unknown>; justification?: string }) =>
      request<ApprovalRequest>('/approval-workflow/request', { method: 'POST', body: JSON.stringify(data) }),
    pending: () => request<ApprovalRequest[]>('/approval-workflow/pending'),
    approve: (requestId: string, data: { comments?: string }) =>
      request<ApprovalRequest>(`/approval-workflow/${requestId}/approve`, { method: 'POST', body: JSON.stringify(data) }),
    deny: (requestId: string, data: { reason: string; comments?: string }) =>
      request<ApprovalRequest>(`/approval-workflow/${requestId}/deny`, { method: 'POST', body: JSON.stringify(data) }),
    cancel: (requestId: string) =>
      request<ApprovalRequest>(`/approval-workflow/${requestId}/cancel`, { method: 'POST' }),
    history: (requestId: string) => request<Array<{ action: string; by: string; timestamp: string; comments: string | null }>>(`/approval-workflow/${requestId}/history`),
  },

  // ── Model Validation ─────────────────────────────────────────────────
  modelValidation: {
    validate: (data: { strategy_id: string; portfolio_data: Record<string, unknown>; validation_type?: string }) =>
      request<ValidationResult>('/model-validation/validate', { method: 'POST', body: JSON.stringify(data) }),
    validateOptimality: (solutionId: string) =>
      request<ValidationResult>(`/model-validation/${solutionId}/validate-optimality`, { method: 'POST' }),
    validateStability: (solutionId: string) =>
      request<ValidationResult>(`/model-validation/${solutionId}/validate-stability`, { method: 'POST' }),
    backtest: (solutionId: string) =>
      request<{ results: ValidationResult[]; summary: Record<string, unknown> }>(`/model-validation/${solutionId}/backtest`, { method: 'POST' }),
    history: (solutionId: string) => request<ValidationResult[]>(`/model-validation/${solutionId}/history`),
  },

  // ── Interoperability ─────────────────────────────────────────────────
  interoperability: {
    convert: (data: { content: string; from_format: string; to_format: string }) =>
      request<{ result: string; format: string }>('/interoperability/convert', { method: 'POST', body: JSON.stringify(data) }),
    validate: (data: { content: string; format: string }) =>
      request<{ valid: boolean; errors: string[] }>('/interoperability/validate', { method: 'POST', body: JSON.stringify(data) }),
    parseFpML: (content: string) =>
      request<{ trades: Record<string, unknown>[]; validation: { valid: boolean; errors: string[] } }>('/interoperability/parse/fpml', { method: 'POST', body: JSON.stringify({ content }) }),
    parseXBRL: (content: string) =>
      request<{ facts: Record<string, unknown>[]; validation: { valid: boolean; errors: string[] } }>('/interoperability/parse/xbrl', { method: 'POST', body: JSON.stringify({ content }) }),
    supportedFormats: () => request<Array<{ id: string; name: string; extension: string; mime_type: string }>>('/interoperability/supported-formats'),
  },

  // ── Disaster Recovery ────────────────────────────────────────────────
  disasterRecovery: {
    status: () => request<DRStatus>('/disaster-recovery/status'),
    createBackup: (backupType: string, location?: string) =>
      request<DRBackup>('/disaster-recovery/backup', {
        method: 'POST',
        body: JSON.stringify({ backup_type: backupType, location: location || 'primary' }),
      }),
    verifyBackup: (backupId: string) =>
      request<{ verified: boolean; integrity: string }>(`/disaster-recovery/backup/${backupId}/verify`, { method: 'POST' }),
    listBackups: (limit?: number) => request<DRBackup[]>(`/disaster-recovery/backups?limit=${limit || 50}`),
    runTest: (testType: string) =>
      request<{ success: boolean; duration_seconds: number; details: Record<string, unknown> }>('/disaster-recovery/test', { method: 'POST', body: JSON.stringify({ test_type: testType }) }),
    getPlan: () => request<{ rto_hours: number; rpo_hours: number; procedures: Array<{ step: string; description: string; estimated_time: string }>; contacts: Array<{ name: string; role: string; phone: string; email: string }> }>('/disaster-recovery/plan'),
    getComplianceChecklist: () => request<{ items: Array<{ id: string; description: string; status: string; last_verified: string | null }>; score: number }>('/disaster-recovery/compliance'),
  },

  // ── SLA Monitoring ───────────────────────────────────────────────────
  sla: {
    compliance: () => request<SLACompliance>('/sla/compliance'),
    recordUptime: (data: { service: string; uptime_pct: number; response_time_ms: number }) =>
      request<{ recorded: boolean; timestamp: string }>('/sla/uptime', { method: 'POST', body: JSON.stringify(data) }),
    reportIncident: (data: { type: string; severity: string; description: string; affected_services: string[] }) =>
      request<SLABreach>('/sla/incident', { method: 'POST', body: JSON.stringify(data) }),
    resolveIncident: (breachId: string, remediation: string) =>
      request<SLABreach>(`/sla/incident/${breachId}/resolve`, {
        method: 'POST',
        body: JSON.stringify({ remediation }),
      }),
    getBreaches: (days?: number) => request<SLABreach[]>(`/sla/breaches?days=${days || 30}`),
    getCredits: () => request<{ credits: Array<{ id: string; amount: number; reason: string; date: string }>; total_owed: number }>('/sla/credits'),
    documentation: () => request<{ services: Array<{ name: string; uptime_target: number; response_time_target: number; penalties: string }> }>('/sla/documentation'),
  },

  // ── Escrow ───────────────────────────────────────────────────────────
  escrow: {
    createAgreement: (data: { name: string; source_code_url?: string; version?: string }) =>
      request<EscrowAgreement>('/escrow/agreements', { method: 'POST', body: JSON.stringify(data) }),
    listAgreements: () => request<EscrowAgreement[]>('/escrow/agreements'),
    getAgreement: (agreementId: string) => request<EscrowAgreement & { releases: Array<{ condition: string; evidence: string; released_at: string }> }>(`/escrow/agreements/${agreementId}`),
    triggerRelease: (agreementId: string, condition: string, evidence: string) =>
      request<{ released: boolean; timestamp: string }>(`/escrow/agreements/${agreementId}/trigger`, {
        method: 'POST',
        body: JSON.stringify({ condition, evidence }),
      }),
    updateSourceCode: (agreementId: string, version: string, commitHash: string, changelog: string) =>
      request<EscrowAgreement>(`/escrow/agreements/${agreementId}/update`, {
        method: 'POST',
        body: JSON.stringify({ version, commit_hash: commitHash, changelog }),
      }),
    getAgreementDocument: (agreementId: string) => request<{ document_url: string; format: string; generated_at: string }>(`/escrow/agreements/${agreementId}/document`),
  },

  // ── Intelligence Feed ──────────────────────────────────────────────
  intelligence: {
    events: (params?: { category?: string; severity?: string }) => {
      const qs = new URLSearchParams();
      if (params?.category) qs.set('category', params.category);
      if (params?.severity) qs.set('severity', params.severity);
      const query = qs.toString();
      return request<ImpactEvent[]>(`/intelligence/events${query ? `?${query}` : ''}`);
    },
    eventSummary: () => request<EventImpactSummary>('/intelligence/events/summary'),
    impactedAssets: () => request<ImpactedAsset[]>('/intelligence/events/assets'),
    opportunities: () => request<Opportunity[]>('/intelligence/opportunities'),
    purchases: () => request<PurchaseRecord[]>('/intelligence/purchases'),
  },

  // ── Agent Runs (plan → execute → verify, human approvals) ───────────
  agent: {
    tools: () => request<{ tools: AgentTool[] }>('/agent/tools'),
    start: (data: { goal: string; steps: Array<{ tool: string; args?: Record<string, unknown> }> }) =>
      request<AgentRun>('/agent/runs', { method: 'POST', body: JSON.stringify(data) }),
    list: () => request<{ runs: Array<{ id: string; goal: string; status: string }> }>('/agent/runs'),
    get: (runId: string) => request<AgentRun>(`/agent/runs/${runId}`),
    approve: (runId: string, seq: number, approved: boolean, comment?: string) =>
      request<AgentRun>(`/agent/runs/${runId}/steps/${seq}/approve`, {
        method: 'POST',
        body: JSON.stringify({ approved, comment: comment ?? '' }),
      }),
    cancel: (runId: string) =>
      request<AgentRun>(`/agent/runs/${runId}/cancel`, { method: 'POST' }),
  },

  // ── Project Workspaces ─────────────────────────────────────────────
  projects: {
    create: (data: { name: string; description?: string }) =>
      request<ProjectSummary>('/projects', { method: 'POST', body: JSON.stringify(data) }),
    list: () => request<{ projects: ProjectSummary[] }>('/projects'),
    get: (projectId: string) => request<ProjectSummary & {
      description: string;
      runs: Array<{ id: string; goal: string; status: string }>;
      documents: number;
      documents_by_folder: Record<string, number>;
    }>(`/projects/${projectId}`),
  },
};

// ── Standalone SSE / polling helper (task-required named export) ───────
export function subscribeToJob(
  id: string,
  onUpdate: (job: OptimizationJob) => void,
  opts?: { intervalMs?: number; onError?: (err: Error) => void }
): () => void {
  return api.optimizations.subscribeToJob(id, onUpdate, opts);
}
