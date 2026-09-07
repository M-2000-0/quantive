/**
 * PostHog analytics — lazy-loaded, respects Do Not Track.
 *
 * Set VITE_POSTHOG_KEY in .env to enable.
 * In development, events are logged to console only.
 * The module is designed to never crash if posthog-js is not installed.
 */

let initialized = false;
let posthogInstance: { capture: (event: string, props?: Record<string, unknown>) => void; identify: (id: string, props?: Record<string, unknown>) => void; reset: () => void; init: (key: string, opts: Record<string, unknown>) => void } | null = null;

export function initAnalytics() {
  if (initialized) return;
  if (typeof window === 'undefined') return;

  // Respect Do Not Track
  if (navigator.doNotTrack === '1') return;

  if (import.meta.env.VITE_POSTHOG_KEY) {
    // Try dynamic import — gracefully degrade if package not installed
    try {
      import(/* @vite-ignore */ 'posthog-js').then((mod) => {
        const posthog = (mod.default || mod) as unknown as NonNullable<typeof posthogInstance>;
        if (posthog && typeof posthog.init === 'function') {
          posthog.init(import.meta.env.VITE_POSTHOG_KEY!, {
            api_host: import.meta.env.VITE_POSTHOG_HOST || 'https://us.i.posthog.com',
            autocapture: true,
            capture_pageleave: true,
            capture_pageview: true,
            disable_session_recording: false,
            session_recording: { maskTextSelector: '.ph-mask' },
            persistence: 'localStorage+cookie',
            property_denylist: ['$ip', 'email'],
          });
          posthogInstance = posthog;
          initialized = true;
        }
      }).catch(() => {});
    } catch {
      // Dynamic import not available (e.g. SSR) — silently skip
    }
  }
}

export function identify(userId: string, traits?: Record<string, string | number | boolean>) {
  if (!initialized || !posthogInstance) return;
  try { posthogInstance.identify(userId, traits as Record<string, unknown>); } catch {}
}

export function resetIdentity() {
  if (!initialized || !posthogInstance) return;
  try { posthogInstance.reset(); } catch {}
}

/**
 * Track a named event with optional properties.
 * Falls back to console.log in dev.
 */
export function track(
  event: string,
  properties?: Record<string, string | number | boolean | null>
) {
  if (import.meta.env.DEV) {
    console.log(`[Analytics] ${event}`, properties);
    return;
  }

  if (!initialized || !posthogInstance) return;
  try { posthogInstance.capture(event, properties as Record<string, unknown>); } catch {}
}

// ── Named event helpers ──────────────────────────────────────────────────────

export const events = {
  // Auth
  login: () => track('user_login'),
  register: () => track('user_register'),
  logout: () => track('user_logout'),

  // Portfolios
  portfolioCreated: (id: string) => track('portfolio_created', { portfolio_id: id }),
  portfolioViewed: (id: string) => track('portfolio_viewed', { portfolio_id: id }),
  portfolioDeleted: (id: string) => track('portfolio_deleted', { portfolio_id: id }),
  portfolioImported: (method: string, instrumentCount: number) =>
    track('portfolio_imported', { method, instrument_count: instrumentCount }),

  // Optimization
  optimizationStarted: (id: string, type: string) =>
    track('optimization_started', { optimization_id: id, type }),
  optimizationCompleted: (id: string, durationMs: number) =>
    track('optimization_completed', { optimization_id: id, duration_ms: durationMs }),
  optimizationFailed: (id: string, error: string) =>
    track('optimization_failed', { optimization_id: id, error }),

  // AI Advisor
  advisorQuery: (queryLength: number) =>
    track('advisor_query', { query_length: queryLength }),
  advisorRecommendationAccepted: () =>
    track('advisor_recommendation_accepted'),

  // Reports
  reportExported: (format: string) =>
    track('report_exported', { format }),

  // Templates
  templateCreated: (templateId: string) =>
    track('template_created', { template_id: templateId }),
  templateApplied: (templateId: string) =>
    track('template_applied', { template_id: templateId }),

  // Onboarding
  onboardingStarted: () => track('onboarding_started'),
  onboardingCompleted: (stepCount: number) =>
    track('onboarding_completed', { step_count: stepCount }),
  onboardingSkipped: (currentStep: number) =>
    track('onboarding_skipped', { current_step: currentStep }),

  // Theme
  themeChanged: (theme: string) =>
    track('theme_changed', { theme }),

  // Search
  commandPaletteOpened: () => track('command_palette_opened'),
  commandPaletteSelected: (category: string) =>
    track('command_palette_selected', { category }),

  // Version history
  undoUsed: () => track('undo_used'),
  redoUsed: () => track('redo_used'),
  versionRestored: (snapshotId: string) =>
    track('version_restored', { snapshot_id: snapshotId }),
};
