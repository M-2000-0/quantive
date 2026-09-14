import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider } from '../stores/theme';
import { AuthProvider } from '../stores/auth';
import { DemoModeProvider } from '../stores/demoMode';

// Mock react-router-dom useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

// Mock api module to avoid real fetch calls
vi.mock('../api', () => ({
  api: {
    auth: {
      login: vi.fn(async ({ email, password }: { email: string; password: string }) => {
        if (email === 'bad@example.com') throw new Error('Authentication failed. Verify credentials and try again.');
        return {
          access_token: 'mock-access-token',
          refresh_token: 'mock-refresh-token',
          token_type: 'bearer',
          user: { id: '1', email, name: 'Test User', role: 'admin', org_id: 'org-1', is_active: true, created_at: '2026-01-01' },
        };
      }),
      register: vi.fn(async ({ email }: { email: string; password: string; name: string; org_name?: string }) => {
        if (email === 'bad@example.com') throw new Error('Registration failed. Please try again.');
        return {
          access_token: 'mock-access-token',
          refresh_token: 'mock-refresh-token',
          token_type: 'bearer',
          user: { id: '1', email, name: 'Test User', role: 'analyst', org_id: 'org-1', is_active: true, created_at: '2026-01-01' },
        };
      }),
      me: vi.fn(async () => ({ id: '1', email: 'a@b.com', name: 'Test', role: 'admin', org_id: 'org-1', is_active: true, created_at: '2026-01-01' })),
    },
    portfolios: { list: vi.fn(async () => ({ data: [], meta: { total: 0 } })), get: vi.fn(), create: vi.fn() },
    optimizations: { list: vi.fn(async () => ({ data: [], meta: { total: 0 } })), get: vi.fn() },
    notifications: { unreadCount: vi.fn(async () => ({ count: 0 })), list: vi.fn(async () => ({ data: [] })), markRead: vi.fn(), markAllRead: vi.fn() },
    health: vi.fn(async () => ({ status: 'healthy', version: '1.0' })),
  },
}));

function pageWrapper({ children }: { children: React.ReactNode }) {
  return (
    <MemoryRouter>
      <ThemeProvider>
        <AuthProvider>
          <DemoModeProvider>{children}</DemoModeProvider>
        </AuthProvider>
      </ThemeProvider>
    </MemoryRouter>
  );
}

// ─── LoginPage ───
import LoginPage from '../pages/LoginPage';

describe('LoginPage', () => {
  beforeEach(() => {
    mockNavigate.mockClear();
    localStorage.clear();
  });

  it('renders the login form', () => {
    render(<LoginPage />, { wrapper: pageWrapper });
    expect(screen.getByText('Sign in to your account')).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('renders Quantive branding', () => {
    render(<LoginPage />, { wrapper: pageWrapper });
    expect(screen.getByText('Quantive')).toBeInTheDocument();
    expect(screen.getByText('Government Financial Optimization')).toBeInTheDocument();
  });

  it('renders link to register', () => {
    render(<LoginPage />, { wrapper: pageWrapper });
    expect(screen.getByText('Request access')).toBeInTheDocument();
  });

  it('updates email input on change', () => {
    render(<LoginPage />, { wrapper: pageWrapper });
    const emailInput = screen.getByLabelText(/email/i);
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    expect(emailInput).toHaveValue('test@example.com');
  });

  it('updates password input on change', () => {
    render(<LoginPage />, { wrapper: pageWrapper });
    const passwordInput = screen.getByLabelText(/password/i);
    fireEvent.change(passwordInput, { target: { value: 'secret123' } });
    expect(passwordInput).toHaveValue('secret123');
  });

  it('shows loading state during submission', async () => {
    render(<LoginPage />, { wrapper: pageWrapper });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'a@b.com' } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'pass1234' } });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));
    expect(screen.getByText('Authenticating...')).toBeInTheDocument();
  });

  it('shows error on failed login', async () => {
    render(<LoginPage />, { wrapper: pageWrapper });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'bad@example.com' } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'wrong' } });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));
    await waitFor(() => {
      expect(screen.getByText(/Authentication failed/)).toBeInTheDocument();
    });
  });

  it('navigates to / on successful login', async () => {
    render(<LoginPage />, { wrapper: pageWrapper });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'admin@treasury.gov' } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'pass1234' } });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/');
    });
  });

  it('renders liquid-orb background elements', () => {
    const { container } = render(<LoginPage />, { wrapper: pageWrapper });
    const orbs = container.querySelectorAll('.liquid-orb');
    expect(orbs.length).toBe(3);
  });
});

// ─── RegisterPage ───
import RegisterPage from '../pages/RegisterPage';

describe('RegisterPage', () => {
  beforeEach(() => {
    mockNavigate.mockClear();
    localStorage.clear();
  });

  it('renders the registration form', () => {
    render(<RegisterPage />, { wrapper: pageWrapper });
    expect(screen.getByText('Create your account')).toBeInTheDocument();
    expect(screen.getByLabelText(/full name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/organization/i)).toBeInTheDocument();
  });

  it('renders Quantive branding', () => {
    render(<RegisterPage />, { wrapper: pageWrapper });
    expect(screen.getByText('Quantive')).toBeInTheDocument();
  });

  it('renders link to login', () => {
    render(<RegisterPage />, { wrapper: pageWrapper });
    expect(screen.getByText('Sign In')).toBeInTheDocument();
  });

  it('shows loading state during submission', async () => {
    render(<RegisterPage />, { wrapper: pageWrapper });
    fireEvent.change(screen.getByLabelText(/full name/i), { target: { value: 'Test User' } });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'test@example.com' } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'pass123456' } });
    fireEvent.click(screen.getByRole('button', { name: /create account/i }));
    expect(screen.getByText(/creating account/i)).toBeInTheDocument();
  });

  it('shows error on failed registration', async () => {
    render(<RegisterPage />, { wrapper: pageWrapper });
    fireEvent.change(screen.getByLabelText(/full name/i), { target: { value: 'Bad' } });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'bad@example.com' } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'wrong' } });
    fireEvent.click(screen.getByRole('button', { name: /create account/i }));
    await waitFor(() => {
      expect(screen.getByText(/Registration failed/)).toBeInTheDocument();
    });
  });

  it('navigates to / on successful registration', async () => {
    render(<RegisterPage />, { wrapper: pageWrapper });
    fireEvent.change(screen.getByLabelText(/full name/i), { target: { value: 'Admin' } });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'admin@treasury.gov' } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'pass123456' } });
    fireEvent.click(screen.getByRole('button', { name: /create account/i }));
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/');
    });
  });

  it('renders liquid-orb background elements', () => {
    const { container } = render(<RegisterPage />, { wrapper: pageWrapper });
    const orbs = container.querySelectorAll('.liquid-orb');
    expect(orbs.length).toBe(3);
  });
});
