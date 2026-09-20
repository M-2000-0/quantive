// Qubo business-tax API client (ledger-backed deduction findings).
import { centsToUsd, dollarsToCents } from '../lib/money';

export { centsToUsd, dollarsToCents };

const API_BASE =
  typeof window !== 'undefined' && (window as unknown as { electronAPI?: { isElectron?: boolean } }).electronAPI?.isElectron
    ? 'http://127.0.0.1:8000/api'
    : (import.meta as any).env?.VITE_API_URL
      ? `${(import.meta as any).env.VITE_API_URL}/api`
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
  reviewFinding: (id: string, status: 'accepted' | 'dismissed') =>
    qRequest<QuboFinding>(`/qubo/business/findings/${id}/review`, {
      method: 'POST',
      body: JSON.stringify({ status }),
    }),
  getSettings: () =>
    qRequest<{ jurisdiction: string; supported_jurisdictions: string[] }>('/qubo/business/settings'),
  updateSettings: (jurisdiction: string) =>
    qRequest<{ jurisdiction: string }>('/qubo/business/settings', {
      method: 'PUT',
      body: JSON.stringify({ jurisdiction }),
    }),
  quarterlyEstimates: () =>
    qRequest<{ quarters: Record<string, { deductions_cents: number; estimated_set_aside_cents: number }>; total_deductions_cents: number; estimated_annual_set_aside_cents: number; effective_rate: number; note: string }>('/qubo/business/quarterly-estimates'),
  exportFindings: (format: 'csv' | 'json' = 'csv') =>
    qRequest<{ export_format: string; tax_year: number; rows?: Record<string, string | number>[]; findings?: QuboFinding[] }>(`/qubo/business/export?format=${format}`),
  uploadDocument: (findingId: string, file: File, category = 'other') => {
    const form = new FormData();
    form.append('file', file);
    return qRequest<{ id: string; filename: string; original_filename: string; mime_type: string; size_bytes: number; category: string; status: string }>(
      `/qubo/business/findings/${findingId}/documents?category=${category}`,
      { method: 'POST', body: form },
    );
  },
  listDocuments: (findingId: string) =>
    qRequest<{ documents: { id: string; finding_id: string; filename: string; original_filename: string; mime_type: string; size_bytes: number; category: string; notes: string; status: string; created_at: string }[] }>(`/qubo/business/findings/${findingId}/documents`),
  listAllDocuments: () =>
    qRequest<{ documents: { id: string; finding_id: string; filename: string; original_filename: string; mime_type: string; size_bytes: number; category: string; status: string; created_at: string }[] }>('/qubo/business/documents'),
  reviewDocument: (docId: string, status: 'reviewed' | 'rejected', notes = '') =>
    qRequest<{ id: string; status: string }>(`/qubo/business/documents/${docId}/review`, {
      method: 'POST',
      body: JSON.stringify({ status, notes }),
    }),
  downloadDocument: (docId: string) => {
    const csrfMatch = typeof document !== 'undefined'
      ? document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/)
      : null;
    const csrfHeader = csrfMatch ? { 'X-CSRF-Token': decodeURIComponent(csrfMatch[1]) } : {};
    return `${API_BASE}/qubo/business/documents/${docId}/download${csrfHeader['X-CSRF-Token'] ? '' : ''}`;
  },
  deleteDocument: (docId: string) =>
    qRequest<{ deleted: boolean }>(`/qubo/business/documents/${docId}`, {
      method: 'DELETE',
    }),
};
