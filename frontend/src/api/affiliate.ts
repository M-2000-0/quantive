// Qubo Tax Affiliate Program API client.
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

async function aRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
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

export interface AffiliateInfo {
  id: string;
  referral_code: string;
  commission_rate: number;
  is_active: boolean;
  payout_email: string;
  created_at: string | null;
}

export interface AffiliateReferral {
  id: string;
  referred_user_id: string | null;
  referral_code: string;
  status: string;
  created_at: string | null;
  registered_at: string | null;
  converted_at: string | null;
}

export interface AffiliateCommission {
  id: string;
  referred_user_id: string;
  billing_period: string;
  subscription_amount_cents: number;
  commission_rate: number;
  commission_amount_cents: number;
  status: string;
  created_at: string | null;
  paid_at: string | null;
}

export interface AffiliateDashboard {
  affiliate: AffiliateInfo;
  stats: {
    total_clicks: number;
    total_referrals: number;
    referrals_by_status: Record<string, number>;
    total_commissions: number;
    total_commission_cents: number;
    paid_commission_cents: number;
    pending_commission_cents: number;
  };
  referrals: AffiliateReferral[];
  commissions: AffiliateCommission[];
}

export interface AffiliateLink {
  referral_code: string;
  referral_link: string;
  share_text: string;
}

export const affiliateApi = {
  join: (payoutEmail = '', commissionRate = 0.20) =>
    aRequest<AffiliateInfo>('/affiliate/join', {
      method: 'POST',
      body: JSON.stringify({ payout_email: payoutEmail, commission_rate: commissionRate }),
    }),

  getMe: () =>
    aRequest<AffiliateInfo>('/affiliate/me'),

  getDashboard: () =>
    aRequest<AffiliateDashboard>('/affiliate/dashboard'),

  getReferralLink: () =>
    aRequest<AffiliateLink>('/affiliate/link'),

  getReferrals: (limit = 50) =>
    aRequest<{ referrals: AffiliateReferral[] }>(`/affiliate/referrals?limit=${limit}`),

  getCommissions: (status?: string, limit = 50) =>
    aRequest<{ commissions: AffiliateCommission[] }>(
      `/affiliate/commissions${status ? `?status=${status}` : ''}${status ? '&' : '?'}limit=${limit}`,
    ),

  trackClick: (code: string) =>
    aRequest<{ status: string; code: string }>(`/affiliate/track/${code}`),

  registerReferral: () =>
    aRequest<{ referral: boolean; already_referred?: boolean }>('/affiliate/register', {
      method: 'POST',
    }),
};
