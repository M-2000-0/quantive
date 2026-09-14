// Qubo business-tax API client (ledger-backed deduction findings).
const API_BASE =
  typeof window !== 'undefined' && (window as unknown as { electronAPI?: { isElectron?: boolean } }).electronAPI?.isElectron
    ? 'http://127.0.0.1:8000/api'
    : '/api';

function csrfHeaders(method: string): Record<string, string> {
  const headers: Record<string, string> = {};
  if (method.toUpperCase() !== 'GET' && typeof document !== 'undefined') {
    const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/);
    if (match) headers['X-CSRF-Token'] = decodeURIComponent(match[1]);
  }
  return headers;
}

async function qRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const method = (options.method || 'GET').toUpperCase();
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...csrfHeaders(method),
      ...((options.headers as Record<string, string>) || {}),
    },
  });
  if (response.status === 401) {
    window.location.href = '/login';
    throw new Error('Unauthorized');
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof data?.detail === 'string' ? data.detail : 'Request failed';
    throw new Error(detail);
  }
  return data as T;
}

export interface QuboFinding {
  id: string;
  account_id: string | null;
  txn_id: string | null;
  rule_id: string;
  rules_version: string;
  jurisdiction: string;
  tax_year: number;
  category: string;
  title: string;
  detail: string;
  amount_cents: number;
  requirements: { requirements: string[]; docs: string[]; sources: string[] };
  status: 'new' | 'accepted' | 'dismissed';
  created_at: string | null;
}

export interface QuboOverview {
  counts: { new: number; accepted: number; dismissed: number };
  total: number;
  potential_new_cents: number;
  accepted_cents: number;
  rules_version: string;
  supported_jurisdictions: string[];
  note: string;
}

export interface QuboScanResult {
  scanned_transactions: number;
  created: number;
  total: number;
  rules_version: string;
  jurisdiction: string;
  generic_guidance: boolean;
}

export const quboApi = {
  overview: () => qRequest<QuboOverview>('/qubo/business/overview'),
  scan: (jurisdiction = 'US', tax_year = 2026) =>
    qRequest<QuboScanResult>('/qubo/business/scan', {
      method: 'POST',
      body: JSON.stringify({ jurisdiction, tax_year }),
    }),
  findings: (status?: string) =>
    qRequest<{ findings: QuboFinding[] }>(
      `/qubo/business/findings${status ? `?status=${status}` : ''}`,
    ),
  review: (id: string, status: 'accepted' | 'dismissed') =>
    qRequest<QuboFinding>(`/qubo/business/findings/${id}/review`, {
      method: 'POST',
      body: JSON.stringify({ status }),
    }),
};
