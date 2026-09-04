/**
 * Sentry error monitoring — lazy-initialized so it doesn't block initial load.
 *
 * In production, set VITE_SENTRY_DSN to enable.
 * In development, errors stay in console only.
 * Designed to never crash if @sentry/react is not installed.
 */

let initialized = false;
let sentryCaptureException: ((error: Error) => void) | null = null;
let sentryCaptureMessage: ((msg: string, level: string) => void) | null = null;
let sentrySetUser: ((user: { id: string; email: string } | null) => void) | null = null;

export function initSentry() {
  if (initialized) return;
  if (import.meta.env.PROD && import.meta.env.VITE_SENTRY_DSN) {
    try {
      import(/* @vite-ignore */ '@sentry/react').then((Sentry) => {
        Sentry.init({
          dsn: import.meta.env.VITE_SENTRY_DSN,
          environment: import.meta.env.MODE,
          release: import.meta.env.VITE_APP_VERSION || 'dev',
          tracesSampleRate: 0.2,
          replaysSessionSampleRate: 0.1,
          replaysOnErrorSampleRate: 1.0,
          integrations: [
            Sentry.browserTracingIntegration(),
            Sentry.replayIntegration({ maskAllText: true }),
          ],
          beforeSend(event) {
            if (event.request?.cookies) delete event.request.cookies;
            return event;
          },
        });
        sentryCaptureException = (error: Error) => Sentry.captureException(error);
        sentryCaptureMessage = (msg: string, level: string) => Sentry.captureMessage(msg, level as 'info' | 'warning' | 'error');
        sentrySetUser = (user: { id: string; email: string } | null) => Sentry.setUser(user);
        initialized = true;
      }).catch(() => {});
    } catch {
      // Dynamic import not available
    }
  }
}

export function captureError(error: Error, errorInfo?: { componentStack?: string }) {
  if (!initialized || !sentryCaptureException) return;
  try { sentryCaptureException(error); } catch {}
}

export function captureMessage(message: string, level: 'info' | 'warning' | 'error' = 'info') {
  if (!initialized || !sentryCaptureMessage) return;
  try { sentryCaptureMessage(message, level); } catch {}
}

export function setUser(user: { id: string; email: string; role?: string }) {
  if (!initialized || !sentrySetUser) return;
  try { sentrySetUser(user); } catch {}
}

export function clearUser() {
  if (!initialized || !sentrySetUser) return;
  try { sentrySetUser(null); } catch {}
}
