import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useOnboardingTour, DEFAULT_TOUR_STEPS } from '../hooks/useOnboardingTour';
import { track, events } from '../lib/analytics';

// ─── Analytics ──────────────────────────────────────────────────────────────

describe('Analytics', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('track logs to console in dev mode', () => {
    const spy = vi.spyOn(console, 'log').mockImplementation(() => {});
    track('test_event', { key: 'value' });
    expect(spy).toHaveBeenCalledWith('[Analytics] test_event', { key: 'value' });
    spy.mockRestore();
  });

  it('events object has all expected event helpers', () => {
    expect(typeof events.login).toBe('function');
    expect(typeof events.register).toBe('function');
    expect(typeof events.portfolioCreated).toBe('function');
    expect(typeof events.optimizationStarted).toBe('function');
    expect(typeof events.advisorQuery).toBe('function');
    expect(typeof events.reportExported).toBe('function');
    expect(typeof events.onboardingStarted).toBe('function');
    expect(typeof events.themeChanged).toBe('function');
    expect(typeof events.undoUsed).toBe('function');
    expect(typeof events.redoUsed).toBe('function');
  });
});

// ─── useOnboardingTour ──────────────────────────────────────────────────────

describe('useOnboardingTour', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('starts inactive and not completed', () => {
    const { result } = renderHook(() => useOnboardingTour());
    expect(result.current.isActive).toBe(false);
    expect(result.current.completed).toBe(false);
  });

  it('starts tour on call', () => {
    const { result } = renderHook(() => useOnboardingTour());
    act(() => { result.current.start(); });
    expect(result.current.isActive).toBe(true);
    expect(result.current.currentStepIndex).toBe(0);
    expect(result.current.totalSteps).toBe(DEFAULT_TOUR_STEPS.length);
  });

  it('advances to next step', () => {
    const { result } = renderHook(() => useOnboardingTour());
    act(() => { result.current.start(); });

    act(() => { result.current.next(); });
    expect(result.current.currentStepIndex).toBe(1);
  });

  it('goes back to previous step', () => {
    const { result } = renderHook(() => useOnboardingTour());
    act(() => { result.current.start(); });
    act(() => { result.current.next(); });
    act(() => { result.current.next(); });

    act(() => { result.current.prev(); });
    expect(result.current.currentStepIndex).toBe(1);
  });

  it('prev does not go below 0', () => {
    const { result } = renderHook(() => useOnboardingTour());
    act(() => { result.current.start(); });

    act(() => { result.current.prev(); });
    expect(result.current.currentStepIndex).toBe(0);
  });

  it('completes tour on last step', () => {
    const { result } = renderHook(() => useOnboardingTour());
    act(() => { result.current.start(); });

    // Go through all steps
    for (let i = 0; i < DEFAULT_TOUR_STEPS.length - 1; i++) {
      act(() => { result.current.next(); });
    }
    expect(result.current.isLast).toBe(true);

    act(() => { result.current.next(); }); // Complete
    expect(result.current.isActive).toBe(false);
    expect(result.current.completed).toBe(true);
  });

  it('skips tour and marks completed', () => {
    const { result } = renderHook(() => useOnboardingTour());
    act(() => { result.current.start(); });
    act(() => { result.current.skip(); });

    expect(result.current.isActive).toBe(false);
    expect(result.current.completed).toBe(true);
  });

  it('persists completion to localStorage', () => {
    const { result } = renderHook(() => useOnboardingTour());
    act(() => { result.current.start(); });
    act(() => { result.current.skip(); });

    expect(localStorage.getItem('quantive:onboarding-tour-completed')).toBe('true');
  });

  it('recognizes completed tour from localStorage', () => {
    localStorage.setItem('quantive:onboarding-tour-completed', 'true');
    const { result } = renderHook(() => useOnboardingTour());
    expect(result.current.completed).toBe(true);
  });

  it('reset clears completion', () => {
    localStorage.setItem('quantive:onboarding-tour-completed', 'true');
    const { result } = renderHook(() => useOnboardingTour());
    expect(result.current.completed).toBe(true);

    act(() => { result.current.reset(); });
    expect(result.current.completed).toBe(false);
    expect(localStorage.getItem('quantive:onboarding-tour-completed')).toBeNull();
  });

  it('isFirst and isLast reflect position', () => {
    const { result } = renderHook(() => useOnboardingTour());
    act(() => { result.current.start(); });

    expect(result.current.isFirst).toBe(true);
    expect(result.current.isLast).toBe(false);

    for (let i = 0; i < DEFAULT_TOUR_STEPS.length - 1; i++) {
      act(() => { result.current.next(); });
    }

    expect(result.current.isFirst).toBe(false);
    expect(result.current.isLast).toBe(true);
  });
});
