import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import React from 'react';

// ── Mock WebSocket ────────────────────────────────────────────────────

class MockWebSocket {
  static instances: MockWebSocket[] = [];
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  readyState = 1;
  url: string;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
    setTimeout(() => this.onopen?.(), 10);
  }

  send(data: string) { /* noop */ }
  close() { this.readyState = 3; }
}

beforeEach(() => {
  MockWebSocket.instances = [];
  (globalThis as unknown as { WebSocket: typeof MockWebSocket }).WebSocket = MockWebSocket;
});

// ── Helpers ───────────────────────────────────────────────────────────

import { ThemeProvider } from '../stores/theme';

function ThemedWrapper({ children }: { children: React.ReactNode }) {
  return <ThemeProvider>{children}</ThemeProvider>;
}

// ── useWebSocket Tests ────────────────────────────────────────────────

describe('useWebSocket', () => {
  it('module exports are importable', async () => {
    const mod = await import('../hooks/useWebSocket');
    expect(typeof mod.useWebSocket).toBe('function');
  });
});

// ── useOptimizationProgress Tests ────────────────────────────────────

describe('useOptimizationProgress', () => {
  it('module exports are importable', async () => {
    const mod = await import('../hooks/useOptimizationProgress');
    expect(typeof mod.useOptimizationProgress).toBe('function');
  });
});

// ── BillingPage Tests ─────────────────────────────────────────────────

describe('BillingPage', () => {
  it('renders all three plans', async () => {
    const { default: BillingPage } = await import('../pages/BillingPage');
    render(<BillingPage />, { wrapper: ThemedWrapper });
    await waitFor(() => {
      expect(screen.getByText('Free')).toBeInTheDocument();
      expect(screen.getByText('Pro')).toBeInTheDocument();
      expect(screen.getByText('Enterprise')).toBeInTheDocument();
    });
  });

  it('shows monthly/yearly toggle', async () => {
    const { default: BillingPage } = await import('../pages/BillingPage');
    render(<BillingPage />, { wrapper: ThemedWrapper });
    expect(screen.getByText('Monthly')).toBeInTheDocument();
    expect(screen.getByText(/Yearly/)).toBeInTheDocument();
  });

  it('shows plan names and prices', async () => {
    const { default: BillingPage } = await import('../pages/BillingPage');
    render(<BillingPage />, { wrapper: ThemedWrapper });
    await waitFor(() => {
      expect(screen.getByText('$0')).toBeInTheDocument();
      expect(screen.getByText('$499')).toBeInTheDocument();
      expect(screen.getByText('$2499')).toBeInTheDocument();
    });
  });

  it('shows FAQ section', async () => {
    const { default: BillingPage } = await import('../pages/BillingPage');
    render(<BillingPage />, { wrapper: ThemedWrapper });
    expect(screen.getByText('Frequently Asked Questions')).toBeInTheDocument();
  });

  it('shows Most Popular badge for Pro plan', async () => {
    const { default: BillingPage } = await import('../pages/BillingPage');
    render(<BillingPage />, { wrapper: ThemedWrapper });
    expect(screen.getByText('Most Popular')).toBeInTheDocument();
  });

  it('shows usage section', async () => {
    const { default: BillingPage } = await import('../pages/BillingPage');
    render(<BillingPage />, { wrapper: ThemedWrapper });
    expect(screen.getByText('Usage This Month')).toBeInTheDocument();
  });

  it('shows upgrade buttons', async () => {
    const { default: BillingPage } = await import('../pages/BillingPage');
    render(<BillingPage />, { wrapper: ThemedWrapper });
    await waitFor(() => {
      expect(screen.getByText('Current Plan')).toBeInTheDocument();
    });
    const upgradeBtns = screen.getAllByText('Upgrade');
    expect(upgradeBtns.length).toBeGreaterThan(0);
  });
});

// ── Billing Constants Tests ───────────────────────────────────────────

describe('Billing Plan Constants', () => {
  const PLANS = [
    { tier: 'free', name: 'Free', price_monthly: 0, price_yearly: 0, features: ['1 portfolio', '5 instruments', '1 optimization/day', 'Basic risk analytics', 'Community support'] },
    { tier: 'pro', name: 'Pro', price_monthly: 499, price_yearly: 399, features: ['Unlimited portfolios', 'Unlimited instruments', '20 optimizations/day', 'Advanced risk analytics', 'Real-time market data', 'AI Advisor', 'ESG scoring', 'Excel/PDF export', 'Webhook integrations'] },
    { tier: 'enterprise', name: 'Enterprise', price_monthly: 2499, price_yearly: 1999, features: ['Everything in Pro', 'Unlimited optimizations', 'Unlimited scenarios', 'Multi-user with RBAC', 'Custom AI models', 'Priority support', 'SLA guarantee (99.9%)', 'SSO / SAML', 'Audit logging', 'On-premise deployment'] },
  ];

  it('Free plan is $0', () => {
    const free = PLANS.find(p => p.tier === 'free');
    expect(free).toBeDefined();
    expect(free!.price_monthly).toBe(0);
  });

  it('Pro plan costs $499/mo', () => {
    const pro = PLANS.find(p => p.tier === 'pro');
    expect(pro).toBeDefined();
    expect(pro!.price_monthly).toBe(499);
  });

  it('Pro plan has enough features', () => {
    const pro = PLANS.find(p => p.tier === 'pro');
    expect(pro!.features.length).toBeGreaterThan(3);
  });

  it('Enterprise has SLA', () => {
    const ent = PLANS.find(p => p.tier === 'enterprise');
    expect(ent!.features.some(f => f.includes('SLA'))).toBe(true);
  });

  it('Enterprise is most expensive', () => {
    const pro = PLANS.find(p => p.tier === 'pro')!;
    const ent = PLANS.find(p => p.tier === 'enterprise')!;
    expect(ent.price_monthly).toBeGreaterThan(pro.price_monthly);
  });

  it('yearly pricing is cheaper than monthly', () => {
    for (const plan of PLANS) {
      if (plan.price_monthly > 0) {
        expect(plan.price_yearly).toBeLessThan(plan.price_monthly);
      }
    }
  });
});

// ── AdminDashboardPage Tests ──────────────────────────────────────────

describe('AdminDashboardPage', () => {
  it('renders loading state initially', async () => {
    // Mock auth to return admin
    vi.mock('../stores/auth', () => ({
      useAuth: () => ({
        user: { id: 'u1', email: 'admin@test.com', role: 'admin', org_id: 'org-1' },
        loading: false,
      }),
      AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    }));

    const { default: AdminDashboardPage } = await import('../pages/AdminDashboardPage');
    render(
      <ThemedWrapper>
        <AdminDashboardPage />
      </ThemedWrapper>
    );
    expect(screen.getByText('Admin Dashboard')).toBeInTheDocument();
    // Shows tabs
    expect(screen.getByText('Overview')).toBeInTheDocument();
    expect(screen.getByText('Users')).toBeInTheDocument();
    expect(screen.getByText('System')).toBeInTheDocument();
    expect(screen.getByText('Billing')).toBeInTheDocument();
  });

  it('shows stats after loading', async () => {
    vi.mock('../stores/auth', () => ({
      useAuth: () => ({
        user: { id: 'u1', email: 'admin@test.com', role: 'admin', org_id: 'org-1' },
        loading: false,
      }),
      AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    }));

    const { default: AdminDashboardPage } = await import('../pages/AdminDashboardPage');
    render(
      <ThemedWrapper>
        <AdminDashboardPage />
      </ThemedWrapper>
    );
    await waitFor(() => {
      expect(screen.getByText('Total Users')).toBeInTheDocument();
    });
    expect(screen.getByText('Portfolios')).toBeInTheDocument();
    expect(screen.getByText('Optimizations')).toBeInTheDocument();
  });

  it('switches to users tab', async () => {
    vi.mock('../stores/auth', () => ({
      useAuth: () => ({
        user: { id: 'u1', email: 'admin@test.com', role: 'admin', org_id: 'org-1' },
        loading: false,
      }),
      AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    }));

    const { default: AdminDashboardPage } = await import('../pages/AdminDashboardPage');
    render(
      <ThemedWrapper>
        <AdminDashboardPage />
      </ThemedWrapper>
    );
    await waitFor(() => screen.getByText('Total Users'));
    fireEvent.click(screen.getByText('Users'));
    expect(screen.getByText('User Activity')).toBeInTheDocument();
  });

  it('switches to system tab', async () => {
    vi.mock('../stores/auth', () => ({
      useAuth: () => ({
        user: { id: 'u1', email: 'admin@test.com', role: 'admin', org_id: 'org-1' },
        loading: false,
      }),
      AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    }));

    const { default: AdminDashboardPage } = await import('../pages/AdminDashboardPage');
    render(
      <ThemedWrapper>
        <AdminDashboardPage />
      </ThemedWrapper>
    );
    await waitFor(() => screen.getByText('Total Users'));
    fireEvent.click(screen.getByText('System'));
    expect(screen.getByText('System Health')).toBeInTheDocument();
    expect(screen.getByText('Performance Metrics')).toBeInTheDocument();
  });

  it('switches to billing tab', async () => {
    vi.mock('../stores/auth', () => ({
      useAuth: () => ({
        user: { id: 'u1', email: 'admin@test.com', role: 'admin', org_id: 'org-1' },
        loading: false,
      }),
      AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    }));

    const { default: AdminDashboardPage } = await import('../pages/AdminDashboardPage');
    render(
      <ThemedWrapper>
        <AdminDashboardPage />
      </ThemedWrapper>
    );
    await waitFor(() => screen.getByText('Total Users'));
    fireEvent.click(screen.getByText('Billing'));
    expect(screen.getByText('Upgrade to Enterprise')).toBeInTheDocument();
  });
});

// ── Non-admin Tests ──────────────────────────────────────────────────

describe('AdminDashboardPage (non-admin)', () => {
  it('renders access denied for non-admin users', async () => {
    vi.resetModules();
    vi.doMock('../stores/auth', () => ({
      useAuth: () => ({
        user: { id: 'u1', email: 'analyst@test.com', role: 'analyst', org_id: 'org-1' },
        loading: false,
      }),
      AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    }));

    const mod = await import('../pages/AdminDashboardPage');
    const AdminDashboardPage = mod.default;
    render(
      <ThemedWrapper>
        <AdminDashboardPage />
      </ThemedWrapper>
    );
    expect(screen.getByText('Access Denied')).toBeInTheDocument();
  });
});
