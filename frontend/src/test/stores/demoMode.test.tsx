import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { DemoModeProvider, useDemoMode } from '../../stores/demoMode';
import { createElement } from 'react';

function wrapper({ children }: { children: React.ReactNode }) {
  return createElement(DemoModeProvider, null, children);
}

describe('demoMode store', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('starts in non-demo mode by default', () => {
    const { result } = renderHook(() => useDemoMode(), { wrapper });
    expect(result.current.isDemoMode).toBe(false);
  });

  it('enableDemoMode sets isDemoMode to true', () => {
    const { result } = renderHook(() => useDemoMode(), { wrapper });
    act(() => result.current.enableDemoMode());
    expect(result.current.isDemoMode).toBe(true);
  });

  it('disableDemoMode sets isDemoMode to false', () => {
    const { result } = renderHook(() => useDemoMode(), { wrapper });
    act(() => result.current.enableDemoMode());
    expect(result.current.isDemoMode).toBe(true);
    act(() => result.current.disableDemoMode());
    expect(result.current.isDemoMode).toBe(false);
  });

  it('persists to localStorage', () => {
    const { result } = renderHook(() => useDemoMode(), { wrapper });
    act(() => result.current.enableDemoMode());
    expect(localStorage.getItem('quantive_demo_mode')).toBe('true');
  });

  it('restores from localStorage on mount', () => {
    localStorage.setItem('quantive_demo_mode', 'true');
    const { result } = renderHook(() => useDemoMode(), { wrapper });
    expect(result.current.isDemoMode).toBe(true);
  });

  it('toggles correctly through full cycle', () => {
    const { result } = renderHook(() => useDemoMode(), { wrapper });
    expect(result.current.isDemoMode).toBe(false);
    act(() => result.current.enableDemoMode());
    expect(result.current.isDemoMode).toBe(true);
    act(() => result.current.disableDemoMode());
    expect(result.current.isDemoMode).toBe(false);
    act(() => result.current.enableDemoMode());
    expect(result.current.isDemoMode).toBe(true);
  });
});
