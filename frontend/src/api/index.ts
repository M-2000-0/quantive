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
    portfolioExcel: (portfolioId: string) => `${API_BASE}/exports/portfolio/${portfolioId}.xlsx`,
    optimizationExcel: (jobId: string) => `${API_BASE}/exports/optimization/${jobId}.xlsx`,
    riskExcel: (portfolioId: string) => `${API_BASE}/exports/risk/${portfolioId}.xlsx`,
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
};
