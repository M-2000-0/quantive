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
