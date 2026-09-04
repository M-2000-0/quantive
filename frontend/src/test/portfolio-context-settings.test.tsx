import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { PortfolioProvider, usePortfolios } from '../stores/portfolio';

// Mock API
vi.mock('../api', () => ({
  api: {
    portfolios: { list: vi.fn().mockResolvedValue([]) },
    auth: { updateMe: vi.fn().mockResolvedValue({}), changePassword: vi.fn().mockResolvedValue({}) },
    mfa: { status: vi.fn().mockResolvedValue({ enabled: false, configured: false }), setup: vi.fn(), enable: vi.fn(), disable: vi.fn() },
    organization: { settings: vi.fn().mockResolvedValue({ name: 'Test Org' }), updateSettings: vi.fn().mockResolvedValue({}) },
  },
}));

// Mock child stores
vi.mock('../stores/theme', () => ({
  useTheme: () => ({ theme: 'light', setTheme: vi.fn() }),
  ThemeProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock('../stores/toast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn() }),
  ToastProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock('../stores/auth', () => ({
  useAuth: () => ({
    user: { id: 'test', name: 'Test User', email: 'test@test.com', role: 'admin', org_id: 'org1' },
    loading: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock('../i18n', () => ({
  useI18n: () => ({ locale: 'en', setLocale: vi.fn() }),
  I18nProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock('../components/ApiKeyManager', () => ({
  default: () => <div>API Key Manager</div>,
}));

vi.mock('../components/AlertPreferences', () => ({
  default: () => <div>Alert Preferences</div>,
}));

// Helper to render within PortfolioProvider
function TestProvider({ children }: { children: React.ReactNode }) {
  return (
    <MemoryRouter initialEntries={['/test']}>
      <PortfolioProvider>{children}</PortfolioProvider>
    </MemoryRouter>
  );
}

function TestComponent() {
  const { portfolios, loading, error } = usePortfolios();
  return (
    <div>
      <span data-testid="loading">{loading.toString()}</span>
      <span data-testid="count">{portfolios.length}</span>
      <span data-testid="error">{error || 'none'}</span>
    </div>
  );
}

describe('PortfolioProvider', () => {
  it('provides initial state', async () => {
    render(
      <TestProvider>
        <TestComponent />
      </TestProvider>,
    );
    // Initially loading
    expect(screen.getByTestId('loading').textContent).toBe('true');
    // Wait for load to complete
    await waitFor(() => {
      expect(screen.getByTestId('loading').textContent).toBe('false');
    });
    expect(screen.getByTestId('count').textContent).toBe('0');
    expect(screen.getByTestId('error').textContent).toBe('none');
  });
});

describe('SettingsPage Tabs', () => {
  it('renders tabbed navigation with all tabs', async () => {
    const { default: SettingsPage } = await import('../pages/SettingsPage');
    render(
      <MemoryRouter initialEntries={['/settings']}>
        <PortfolioProvider>
          <Routes>
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </PortfolioProvider>
      </MemoryRouter>,
    );
    expect(screen.getByText('Settings')).toBeDefined();
    expect(screen.getByText('Profile')).toBeDefined();
    expect(screen.getByText('Security')).toBeDefined();
    expect(screen.getByText('Appearance')).toBeDefined();
    expect(screen.getByText('Notifications')).toBeDefined();
    expect(screen.getByText('API Keys')).toBeDefined();
    expect(screen.getByText('Organization')).toBeDefined();
    expect(screen.getByText('Team')).toBeDefined();
    expect(screen.getByText('Roles & Permissions')).toBeDefined();
    expect(screen.getByText('Shortcuts')).toBeDefined();
  });

  it('shows profile tab content by default', async () => {
    const { default: SettingsPage } = await import('../pages/SettingsPage');
    render(
      <MemoryRouter initialEntries={['/settings']}>
        <PortfolioProvider>
          <Routes>
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </PortfolioProvider>
      </MemoryRouter>,
    );
    expect(screen.getByText('Your Profile')).toBeDefined();
    expect(screen.getByText('Full Name')).toBeDefined();
  });

  it('switches to security tab', async () => {
    const { default: SettingsPage } = await import('../pages/SettingsPage');
    render(
      <MemoryRouter initialEntries={['/settings']}>
        <PortfolioProvider>
          <Routes>
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </PortfolioProvider>
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByText('Security'));
    await waitFor(() => {
      expect(screen.getByText('Change Password')).toBeDefined();
    });
  });

  it('switches to appearance tab', async () => {
    const { default: SettingsPage } = await import('../pages/SettingsPage');
    render(
      <MemoryRouter initialEntries={['/settings']}>
        <PortfolioProvider>
          <Routes>
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </PortfolioProvider>
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByText('Appearance'));
    await waitFor(() => {
      expect(screen.getByText('Theme')).toBeDefined();
      expect(screen.getByText('Language')).toBeDefined();
    });
  });

  it('switches to shortcuts tab', async () => {
    const { default: SettingsPage } = await import('../pages/SettingsPage');
    render(
      <MemoryRouter initialEntries={['/settings']}>
        <PortfolioProvider>
          <Routes>
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </PortfolioProvider>
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByText('Shortcuts'));
    await waitFor(() => {
      expect(screen.getByText('⌘K / Ctrl+K')).toBeDefined();
      expect(screen.getByText('Open command palette')).toBeDefined();
    });
  });
});
