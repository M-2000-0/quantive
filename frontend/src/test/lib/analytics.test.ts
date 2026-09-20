import { describe, it, expect, vi, beforeEach } from 'vitest';
import { initAnalytics, identify, resetIdentity, track, events } from '../../lib/analytics';

describe('analytics', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('initAnalytics', () => {
    it('does not throw when called', () => {
      expect(() => initAnalytics()).not.toThrow();
    });

    it('is idempotent', () => {
      initAnalytics();
      initAnalytics();
    });
  });

  describe('identify', () => {
    it('does not throw when analytics not initialized', () => {
      expect(() => identify('user-123')).not.toThrow();
    });

    it('does not throw with traits', () => {
      expect(() => identify('user-123', { plan: 'enterprise' })).not.toThrow();
    });
  });

  describe('resetIdentity', () => {
    it('does not throw when analytics not initialized', () => {
      expect(() => resetIdentity()).not.toThrow();
    });
  });

  describe('track', () => {
    it('is a function', () => {
      expect(typeof track).toBe('function');
    });

    it('does not throw', () => {
      expect(() => track('test_event', { key: 'value' })).not.toThrow();
    });

    it('does not throw without properties', () => {
      expect(() => track('test_event')).not.toThrow();
    });
  });

  describe('events', () => {
    it('has named event helpers', () => {
      expect(typeof events.login).toBe('function');
      expect(typeof events.register).toBe('function');
      expect(typeof events.logout).toBe('function');
      expect(typeof events.portfolioCreated).toBe('function');
      expect(typeof events.optimizationStarted).toBe('function');
    });

    it('event helpers do not throw', () => {
      expect(() => events.login()).not.toThrow();
      expect(() => events.register()).not.toThrow();
      expect(() => events.portfolioCreated('test-id')).not.toThrow();
      expect(() => events.optimizationStarted('opt-id', 'mvo')).not.toThrow();
      expect(() => events.optimizationCompleted('opt-id', 1500)).not.toThrow();
      expect(() => events.advisorQuery(42)).not.toThrow();
      expect(() => events.themeChanged('dark')).not.toThrow();
    });
  });
});
