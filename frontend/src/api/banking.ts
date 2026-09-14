// Quantive Banking API client. Money crosses the wire as integer cents;
// centsToUsd() is the only place dollars are rendered.
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

async function bRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
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

export function centsToUsd(cents: number): string {
  return (cents / 100).toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
  });
}

export function dollarsToCents(dollars: string): number {
  const n = Number.parseFloat(dollars);
  if (!Number.isFinite(n) || n <= 0) throw new Error('Enter an amount greater than $0');
  return Math.round(n * 100);
}

export interface BankAccount {
  id: string;
  name: string;
  account_type: 'operating' | 'reserve' | 'yield';
  currency: string;
  balance_cents: number;
  status: string;
  created_at: string | null;
}

export interface BankTransaction {
  id: string;
  account_id: string;
  direction: 'in' | 'out';
  txn_type: string;
  amount_cents: number;
  fee_cents: number;
  counterparty: string;
  memo: string;
  category: string;
  tax_tag: string;
  status: 'posted' | 'pending';
  transfer_id: string | null;
  created_at: string | null;
}

export interface BankTransfer {
  id: string;
  from_account_id: string;
  to_account_id: string | null;
  amount_cents: number;
  fee_cents: number;
  status: string;
  counterparty: string;
  memo: string;
  idempotency_key: string | null;
  created_at: string | null;
  transactions: BankTransaction[];
}

export interface BankingOverview {
  total_balance_cents: number;
  fees_paid_30d_cents: number;
  moved_30d_cents: number;
  projected_net_90d_cents: number;
  forecast_basis: string;
  pending_count: number;
  pending_cents: number;
  accounts: BankAccount[];
  recent: BankTransaction[];
}

export interface BankingInsight {
  id: string;
  title: string;
  body: string;
  severity: 'info' | 'warn';
}

export interface BusinessProfile {
  org_id: string;
  legal_name: string;
  dba: string;
  entity_type: string;
  country: string;
  industry: string;
  tax_id_last4: string;
  kyb_status: 'draft' | 'pending' | 'verified' | 'rejected';
  kyb_notes: string;
  submitted_at: string | null;
  decided_at: string | null;
}

export const bankingApi = {
  overview: () => bRequest<BankingOverview>('/banking/overview'),
  accounts: () => bRequest<{ accounts: BankAccount[] }>('/banking/accounts'),
  openAccount: (body: { name: string; account_type: string }) =>
    bRequest<BankAccount>('/banking/accounts', { method: 'POST', body: JSON.stringify(body) }),
  accountTxns: (id: string, limit = 25) =>
    bRequest<{ account: BankAccount; transactions: BankTransaction[] }>(
      `/banking/accounts/${id}/transactions?limit=${limit}`,
    ),
  transfers: (limit = 25) =>
    bRequest<{ transfers: BankTransfer[] }>(`/banking/transfers?limit=${limit}`),
  createTransfer: (body: {
    from_account_id: string;
    to_account_id?: string | null;
    counterparty?: string;
    amount_cents: number;
    memo?: string;
    idempotency_key?: string;
  }) => bRequest<BankTransfer>('/banking/transfers', { method: 'POST', body: JSON.stringify(body) }),
  seed: () => bRequest<BankAccount>('/banking/seed', { method: 'POST' }),
  profile: () => bRequest<{ profile: BusinessProfile | null; kyb_status: string }>('/banking/profile'),
  saveProfile: (body: Partial<BusinessProfile>) =>
    bRequest<BusinessProfile>('/banking/profile', { method: 'PUT', body: JSON.stringify(body) }),
  submitProfile: () => bRequest<BusinessProfile>('/banking/profile/submit', { method: 'POST' }),
  insights: () => bRequest<{ insights: BankingInsight[]; disclaimer: string }>('/banking/insights'),
  categorize: (id: string, body: { category: string; tax_tag: string }) =>
    bRequest<BankTransaction>(`/banking/transactions/${id}/categorize`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
};
