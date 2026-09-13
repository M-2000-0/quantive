// Quantive Personal — isolated API client. Separate storage keys, same auth cookies.
// Never imports sovereign api namespaces; only uses /api/personal prefix.
const API_BASE =
  typeof window !== 'undefined' && (window as any).electronAPI?.isElectron
    ? 'http://127.0.0.1:8000/api'
    : '/api';

function csrf(): string {
  if (typeof document === 'undefined') return '';
  const m = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/);
  return m ? decodeURIComponent(m[1]) : '';
}

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { ...(init.headers as any) };
  if (!(init.body instanceof FormData)) headers['Content-Type'] = 'application/json';
  if (init.method && init.method.toUpperCase() !== 'GET') {
    const t = csrf();
    if (t) headers['X-CSRF-Token'] = t;
  }
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers, credentials: 'include' });
  if (res.status === 401) {
    window.location.href = '/login';
    throw new Error('Unauthorized');
  }
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error((data as any).detail || 'Request failed');
  return data as T;
}

export interface PersonalScore {
  score: number; completeness: number; open_actions: number;
  opportunities: number; doc_gaps: number; needs_review: number; message: string;
  tier?: string; limits?: any; docs_total?: number; gov_access?: boolean;
}
export interface PersonalPlan {
  tier: string; name: string; price_yearly: number; features: string[]; limits: any;
}
export interface PersonalBilling {
  product: string; tier: string; status: string;
  plans?: PersonalPlan[]; current_limits?: any; gov_access?: boolean;
}
export interface PersonalQuestion {
  id: string; group: string; prompt: string; kind: 'single' | 'multi';
  options: string[];
}
export interface PersonalOnboarding {
  status: string; current: number; total: number; baseline_max: number;
  questions: PersonalQuestion[]; answers: Record<string, any>;
}
export interface PersonalOpp {
  id: string; title: string; category: string; relevance: string; status: string;
  why: string; needs_info: string[]; needs_docs: string[]; rule_refs: string[];
  next_action: string;
}
export interface PersonalTask {
  id: string; title: string; reason: string; priority: string; status: string;
  due: string; link: string;
}

export const personalApi = {
  score: () => req<PersonalScore>('/personal/score'),
  onboarding: () => req<PersonalOnboarding>('/personal/onboarding'),
  answer: (question_id: string, answer: any) =>
    req<PersonalOnboarding>('/personal/onboarding/answer', {
      method: 'POST', body: JSON.stringify({ question_id, answer }),
    }),
  completeOnboarding: () =>
    req<{ status: string }>('/personal/onboarding/complete', { method: 'POST', body: '{}' }),
  profile: () => req<{ groups: Record<string, any[]> }>('/personal/profile'),
  upsertFact: (f: { category: string; key: string; value?: string; value_json?: any; source?: string; confidence?: string; status?: string }) =>
    req('/personal/profile/facts', { method: 'PUT', body: JSON.stringify(f) }),
  deleteFact: (id: string) => req(`/personal/profile/facts/${id}`, { method: 'DELETE' }),
  opportunities: () => req<PersonalOpp[]>('/personal/opportunities'),
  reviewOpp: (id: string, action = 'reviewed') =>
    req(`/personal/opportunities/${id}/review`, { method: 'POST', body: JSON.stringify({ action }) }),
  tasks: () => req<PersonalTask[]>('/personal/tasks'),
  closeTask: (id: string) => req(`/personal/tasks/${id}/close`, { method: 'POST', body: '{}' }),
  documents: () => req<{ categories: Record<string, number>; total?: number; cap?: number | null; documents: any[] }>('/personal/documents'),
  registerDoc: (filename: string, category: string) =>
    req('/personal/documents', { method: 'POST', body: JSON.stringify({ filename, category }) }),
  ask: (question: string) =>
    req<any>('/personal/intelligence/ask', { method: 'POST', body: JSON.stringify({ question }) }),
  report: () => req<any>('/personal/report'),
  billing: () => req<PersonalBilling>('/personal/billing'),
  checkout: (tier: string, billing_cycle = 'yearly') =>
    req<any>('/personal/billing/checkout', { method: 'POST', body: JSON.stringify({ tier, billing_cycle }) }),
  govInsights: () => req<{ tier: string; bracket: string; trends: { segment: string; signal: string; direction: string }[]; how_to_use: string; privacy: string; is_live?: boolean; as_of?: string; contributors_total?: number; your_bracket?: string; note?: string }>('/personal/gov-insights'),
  quboStatus: () => req<{ opt_in: boolean; age_bracket: string | null; brackets: string[]; privacy: string }>('/personal/qubo/status'),
  quboConsent: (opt_in: boolean, age_bracket?: string) =>
    req<{ opt_in: boolean; age_bracket: string | null }>('/personal/qubo/consent', {
      method: 'POST', body: JSON.stringify({ opt_in, age_bracket }),
    }),
  quboTrends: () => req<{ is_live: boolean; trends: { segment: string; signal: string; direction: string }[]; contributors_total: number; your_bracket: string | null; opt_in: boolean }>('/personal/qubo/trends'),
};
