import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { type ReactNode } from 'react';

// ─── Theme Store ───
import { ThemeProvider, useTheme } from '../stores/theme';

function wrapper({ children }: { children: ReactNode }) {
  return <ThemeProvider>{children}</ThemeProvider>;
}

describe('ThemeProvider / useTheme', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove('light', 'dark');
  });

  it('defaults to system theme', () => {
    const { result } = renderHook(() => useTheme(), { wrapper });
    expect(result.current.theme).toBe('system');
  });

  it('resolves to light when system prefers light', () => {
    const { result } = renderHook(() => useTheme(), { wrapper });
    expect(result.current.resolvedTheme).toBe('light');
  });

  it('setTheme updates theme and persists to localStorage', () => {
    const { result } = renderHook(() => useTheme(), { wrapper });
    act(() => result.current.setTheme('dark'));
    expect(result.current.theme).toBe('dark');
    expect(result.current.resolvedTheme).toBe('dark');
    expect(localStorage.getItem('quantive_theme')).toBe('dark');
  });

  it('toggleTheme cycles: dark → light', () => {
    const { result } = renderHook(() => useTheme(), { wrapper });
    act(() => result.current.setTheme('dark'));
    act(() => result.current.toggleTheme());
    expect(result.current.theme).toBe('light');
  });

  it('toggleTheme cycles: light → dark', () => {
    const { result } = renderHook(() => useTheme(), { wrapper });
    act(() => result.current.setTheme('light'));
    act(() => result.current.toggleTheme());
    expect(result.current.theme).toBe('dark');
  });

  it('applies class to document.documentElement', () => {
    const { result } = renderHook(() => useTheme(), { wrapper });
    act(() => result.current.setTheme('dark'));
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });

  it('reads persisted theme from localStorage', () => {
    localStorage.setItem('quantive_theme', 'light');
    const { result } = renderHook(() => useTheme(), { wrapper });
    expect(result.current.theme).toBe('light');
  });

  it('throws when used outside ThemeProvider', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => renderHook(() => useTheme())).toThrow('useTheme must be used within ThemeProvider');
    consoleSpy.mockRestore();
  });
});

// ─── Toast Store ───
import { ToastProvider, useToast } from '../stores/toast';

function toastWrapper({ children }: { children: ReactNode }) {
  return <ToastProvider>{children}</ToastProvider>;
}

describe('ToastProvider / useToast', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('starts with empty toasts', () => {
    const { result } = renderHook(() => useToast(), { wrapper: toastWrapper });
    expect(result.current.toasts).toHaveLength(0);
  });

  it('success() adds a success toast', () => {
    const { result } = renderHook(() => useToast(), { wrapper: toastWrapper });
    act(() => result.current.success('Saved!', 'Data persisted'));
    expect(result.current.toasts).toHaveLength(1);
    expect(result.current.toasts[0].type).toBe('success');
    expect(result.current.toasts[0].title).toBe('Saved!');
    expect(result.current.toasts[0].message).toBe('Data persisted');
  });

  it('error() adds an error toast', () => {
    const { result } = renderHook(() => useToast(), { wrapper: toastWrapper });
    act(() => result.current.error('Oops', 'Something broke'));
    expect(result.current.toasts[0].type).toBe('error');
  });

  it('warning() and info() add correct types', () => {
    const { result } = renderHook(() => useToast(), { wrapper: toastWrapper });
    act(() => result.current.warning('Watch out'));
    act(() => result.current.info('FYI'));
    expect(result.current.toasts[0].type).toBe('warning');
    expect(result.current.toasts[1].type).toBe('info');
  });

  it('removeToast removes by id', () => {
    const { result } = renderHook(() => useToast(), { wrapper: toastWrapper });
    act(() => result.current.success('Test'));
    const id = result.current.toasts[0].id;
    act(() => result.current.removeToast(id));
    expect(result.current.toasts).toHaveLength(0);
  });

  it('auto-removes toast after duration', () => {
    const { result } = renderHook(() => useToast(), { wrapper: toastWrapper });
    act(() => result.current.success('Gone soon'));
    expect(result.current.toasts).toHaveLength(1);
    act(() => vi.advanceTimersByTime(4000));
    expect(result.current.toasts).toHaveLength(0);
  });

  it('limits to 5 visible toasts', () => {
    const { result } = renderHook(() => useToast(), { wrapper: toastWrapper });
    for (let i = 0; i < 7; i++) {
      act(() => result.current.info(`Toast ${i}`));
    }
    expect(result.current.toasts.length).toBeLessThanOrEqual(5);
  });

  it('addJobToast creates job-status toasts', () => {
    const { result } = renderHook(() => useToast(), { wrapper: toastWrapper });
    act(() => result.current.addJobToast('running'));
    expect(result.current.toasts[0].jobStatus).toBe('running');
    expect(result.current.toasts[0].title).toBe('Job Running');
  });

  it('addJobToast with custom title/message', () => {
    const { result } = renderHook(() => useToast(), { wrapper: toastWrapper });
    act(() => result.current.addJobToast('completed', { title: 'Done!', message: 'All good' }));
    expect(result.current.toasts[0].title).toBe('Done!');
    expect(result.current.toasts[0].message).toBe('All good');
  });

  it('addJobToast with jobId', () => {
    const { result } = renderHook(() => useToast(), { wrapper: toastWrapper });
    act(() => result.current.addJobToast('queued', { jobId: 'job-123' }));
    expect(result.current.toasts[0].jobId).toBe('job-123');
  });

  it('addToast normalizes job-prefixed types', () => {
    const { result } = renderHook(() => useToast(), { wrapper: toastWrapper });
    act(() => result.current.addToast({ type: 'job-completed', title: 'Done' }));
    expect(result.current.toasts[0].jobStatus).toBe('completed');
  });

  it('notifyJobStatus delegates to addJobToast', () => {
    const { result } = renderHook(() => useToast(), { wrapper: toastWrapper });
    act(() => result.current.notifyJobStatus('failed', 'job-456', 'Custom fail msg'));
    expect(result.current.toasts[0].jobStatus).toBe('failed');
    expect(result.current.toasts[0].jobId).toBe('job-456');
    expect(result.current.toasts[0].message).toBe('Custom fail msg');
  });

  it('throws when used outside ToastProvider', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => renderHook(() => useToast())).toThrow('useToast must be used within ToastProvider');
    consoleSpy.mockRestore();
  });
});

// ─── Auth Store ───
import { AuthProvider, useAuth } from '../stores/auth';

function authWrapper({ children }: { children: ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}

describe('AuthProvider / useAuth', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('starts with null user', () => {
    const { result } = renderHook(() => useAuth(), { wrapper: authWrapper });
    // After useEffect runs, loading is false and user is null
    expect(result.current.user).toBeNull();
  });

  it('reads stored user on mount', () => {
    const mockUser = { id: '1', email: 'a@b.com', name: 'Test', role: 'admin', org_id: 'org-1', is_active: true, created_at: '2026-01-01' };
    localStorage.setItem('user', JSON.stringify(mockUser));
    const { result } = renderHook(() => useAuth(), { wrapper: authWrapper });
    expect(result.current.user).toEqual(mockUser);
  });

  it('logout clears user and tokens', () => {
    const mockUser = { id: '1', email: 'a@b.com', name: 'Test', role: 'admin', org_id: 'org-1', is_active: true, created_at: '2026-01-01' };
    localStorage.setItem('user', JSON.stringify(mockUser));
    localStorage.setItem('access_token', 'abc');
    const { result } = renderHook(() => useAuth(), { wrapper: authWrapper });
    act(() => result.current.logout());
    expect(result.current.user).toBeNull();
    expect(localStorage.getItem('access_token')).toBeNull();
    expect(localStorage.getItem('user')).toBeNull();
  });

  it('handles invalid JSON in localStorage gracefully', () => {
    localStorage.setItem('user', 'NOT-JSON{{{');
    const { result } = renderHook(() => useAuth(), { wrapper: authWrapper });
    expect(result.current.user).toBeNull();
    expect(localStorage.getItem('user')).toBeNull();
  });

  it('throws when used outside AuthProvider', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => renderHook(() => useAuth())).toThrow('useAuth must be used within AuthProvider');
    consoleSpy.mockRestore();
  });
});
