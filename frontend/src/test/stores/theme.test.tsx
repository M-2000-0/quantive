import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { ThemeProvider, useTheme } from '../../stores/theme';
import { createElement } from 'react';

function wrapper({ children }: { children: React.ReactNode }) {
  return createElement(ThemeProvider, null, children);
}

describe('theme store', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('defaults to system theme', () => {
    const { result } = renderHook(() => useTheme(), { wrapper });
    expect(['light', 'dark']).toContain(result.current.resolvedTheme);
  });

  it('setTheme changes theme', () => {
    const { result } = renderHook(() => useTheme(), { wrapper });
    act(() => result.current.setTheme('dark'));
    expect(result.current.resolvedTheme).toBe('dark');
  });

  it('toggleTheme toggles between light and dark', () => {
    const { result } = renderHook(() => useTheme(), { wrapper });
    const initial = result.current.resolvedTheme;
    act(() => result.current.toggleTheme());
    expect(result.current.resolvedTheme).toBe(initial === 'dark' ? 'light' : 'dark');
  });

  it('persists theme to localStorage', () => {
    const { result } = renderHook(() => useTheme(), { wrapper });
    act(() => result.current.setTheme('dark'));
    expect(localStorage.getItem('quantive_theme')).toBeTruthy();
  });

  it('restores theme from localStorage', () => {
    localStorage.setItem('quantive_theme', 'dark');
    const { result } = renderHook(() => useTheme(), { wrapper });
    expect(result.current.resolvedTheme).toBe('dark');
  });

  it('setTheme accepts system option', () => {
    const { result } = renderHook(() => useTheme(), { wrapper });
    act(() => result.current.setTheme('system'));
    expect(['light', 'dark']).toContain(result.current.resolvedTheme);
  });
});
