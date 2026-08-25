import { useState, useCallback, createContext, useContext } from 'react';

export type JobStatus = 'queued' | 'running' | 'completed' | 'failed';
type ToastVariant = 'success' | 'error' | 'info' | 'warning' | JobStatus | `job-${JobStatus}`;

interface Toast {
  id: string;
  message: string;
  title?: string;
  variant: ToastVariant;
  jobStatus?: JobStatus;
  jobId?: string;
}

interface ToastContextValue {
  toasts: Toast[];
  addToast: (message: string, variant?: ToastVariant) => void;
  removeToast: (id: string) => void;
  addJobToast: (status: JobStatus, opts?: { title?: string; message?: string; jobId?: string }) => void;
  notifyJobStatus: (status: JobStatus, jobId?: string, customMessage?: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}

const VARIANT_STYLES: Record<string, string> = {
  success: 'border-l-4 border-l-emerald-400 bg-emerald-50/90 text-emerald-900',
  error: 'border-l-4 border-l-red-400 bg-red-50/90 text-red-900',
  warning: 'border-l-4 border-l-amber-400 bg-amber-50/90 text-amber-900',
  info: 'border-l-4 border-l-blue-400 bg-blue-50/90 text-slate-800',
  queued: 'border-l-4 border-l-slate-400 bg-slate-50/90 text-slate-800',
  running: 'border-l-4 border-l-blue-400 bg-blue-50/90 text-slate-800',
  completed: 'border-l-4 border-l-emerald-400 bg-emerald-50/90 text-emerald-900',
  failed: 'border-l-4 border-l-red-400 bg-red-50/90 text-red-900',
  'job-queued': 'border-l-4 border-l-slate-400 bg-slate-50/90 text-slate-800',
  'job-running': 'border-l-4 border-l-blue-400 bg-blue-50/90 text-slate-800',
  'job-completed': 'border-l-4 border-l-emerald-400 bg-emerald-50/90 text-emerald-900',
  'job-failed': 'border-l-4 border-l-red-400 bg-red-50/90 text-red-900',
};

const VARIANT_ICONS: Record<string, string> = {
  success: '✓',
  error: '✕',
  warning: '⚠',
  info: 'ℹ',
  queued: '⏳',
  running: '⟳',
  completed: '✓',
  failed: '✕',
  'job-queued': '⏳',
  'job-running': '⟳',
  'job-completed': '✓',
  'job-failed': '✕',
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback((message: string, variant: ToastVariant = 'info') => {
    const id = Math.random().toString(36).slice(2);
    const normalized: ToastVariant = variant.startsWith('job-') ? (variant.replace('job-', '') as ToastVariant) : variant;
    const jobStatus = (['queued','running','completed','failed'] as const).includes(normalized as JobStatus) ? (normalized as JobStatus) : undefined;
    setToasts((prev) => [...prev.slice(-4), { id, message, variant: normalized, jobStatus }]);
    const durations: Record<string, number> = { queued: 4000, running: 5000, completed: 6000, failed: 7000, success: 4000, error: 6000, warning: 5000, info: 4000 };
    const ms = durations[normalized] ?? 5000;
    setTimeout(() => removeToast(id), ms);
  }, [removeToast]);

  const addJobToast = useCallback((status: JobStatus, opts?: { title?: string; message?: string; jobId?: string }) => {
    const titles: Record<JobStatus, string> = {
      queued: 'Job Queued',
      running: 'Job Running',
      completed: 'Job Completed',
      failed: 'Job Failed',
    };
    const defaults: Record<JobStatus, string> = {
      queued: 'Your optimization is queued and will start shortly.',
      running: 'Optimization is in progress…',
      completed: 'Optimization completed successfully.',
      failed: 'Optimization failed. Check details.',
    };
    const title = opts?.title ?? titles[status];
    const msg = opts?.message ?? defaults[status];
    const full = opts?.jobId ? `${title}${msg ? `: ${msg}` : ''} (${opts.jobId.slice(0,8)})` : (msg ? `${title}: ${msg}` : title);
    // Use addToast internally but preserve job metadata
    const id = Math.random().toString(36).slice(2);
    setToasts((prev) => [...prev.slice(-4), { id, message: full, title, variant: status, jobStatus: status, jobId: opts?.jobId }]);
    const durations: Record<JobStatus, number> = { queued: 4000, running: 5000, completed: 6000, failed: 7000 };
    setTimeout(() => removeToast(id), durations[status]);
  }, [removeToast]);

  const notifyJobStatus = useCallback((status: JobStatus, jobId?: string, customMessage?: string) => {
    addJobToast(status, { jobId, message: customMessage });
  }, [addJobToast]);

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast, addJobToast, notifyJobStatus }}>
      {children}
      <div className="fixed top-4 right-4 z-[9999] flex flex-col gap-3 max-w-sm w-full pointer-events-none">
        {toasts.map((t) => {
          const style = VARIANT_STYLES[t.variant] ?? VARIANT_STYLES[t.jobStatus ?? 'info'];
          const icon = VARIANT_ICONS[t.variant] ?? VARIANT_ICONS[t.jobStatus ?? 'info'] ?? 'ℹ';
          return (
          <div
            key={t.id}
            role="status"
            aria-live="polite"
            className={`pointer-events-auto glass-strong backdrop-blur-xl rounded-[14px] px-4 py-3 text-sm shadow-lg border border-white/40 flex items-start gap-3 animate-glass-in transition-all ${style}`}
            onClick={() => removeToast(t.id)}
          >
            <span className="w-6 h-6 rounded-full bg-white/60 backdrop-blur border border-white/40 flex items-center justify-center text-xs font-bold flex-shrink-0 shadow-sm">
              {icon}
            </span>
            <div className="flex-1 min-w-0">
              {t.title && <p className="font-semibold leading-none text-sm">{t.title}</p>}
              <p className={`break-words ${t.title ? 'text-xs mt-1 opacity-90' : 'text-sm'}`}>{t.message}</p>
              {t.jobId && <p className="text-[10px] font-mono opacity-60 mt-1 truncate">{t.jobId}</p>}
            </div>
            <button
              aria-label="Dismiss"
              className="text-xs opacity-50 hover:opacity-100 p-1 rounded hover:bg-white/40 transition-colors"
              onClick={(e) => { e.stopPropagation(); removeToast(t.id); }}
            >
              ✕
            </button>
          </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}
