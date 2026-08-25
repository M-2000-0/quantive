import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';

export type JobStatus = 'queued' | 'running' | 'completed' | 'failed';
export type ToastType = 'success' | 'error' | 'warning' | 'info' | JobStatus | `job-${JobStatus}`;

export interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
  jobStatus?: JobStatus;
  jobId?: string;
}

interface ToastContextValue {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
  success: (title: string, message?: string) => void;
  error: (title: string, message?: string) => void;
  warning: (title: string, message?: string) => void;
  info: (title: string, message?: string) => void;
  addJobToast: (status: JobStatus, opts?: { title?: string; message?: string; jobId?: string; duration?: number }) => void;
  notifyJobStatus: (status: JobStatus, jobId?: string, customMessage?: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const addToast = useCallback((toast: Omit<Toast, 'id'>) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    // Normalize job-prefixed types to plain JobStatus for styling
    const normalized = { ...toast } as Toast;
    if (normalized.type.startsWith('job-')) {
      const js = normalized.type.replace('job-', '') as JobStatus;
      normalized.jobStatus = js;
      normalized.type = js;
    }
    if (['queued','running','completed','failed'].includes(normalized.type)) {
      normalized.jobStatus = normalized.type as JobStatus;
    }
    const newToast: Toast = { ...normalized, id };
    setToasts(prev => [...prev.slice(-4), newToast]); // max 5 visible

    const defaultDurations: Record<string, number> = {
      queued: 4000,
      running: 5000,
      completed: 6000,
      failed: 7000,
      success: 4000,
      error: 6000,
      warning: 5000,
      info: 4000,
    };
    const duration = toast.duration ?? defaultDurations[normalized.type] ?? 4000;
    setTimeout(() => removeToast(id), duration);
  }, [removeToast]);

  const success = useCallback((title: string, message?: string) => addToast({ type: 'success', title, message }), [addToast]);
  const error = useCallback((title: string, message?: string) => addToast({ type: 'error', title, message }), [addToast]);
  const warning = useCallback((title: string, message?: string) => addToast({ type: 'warning', title, message }), [addToast]);
  const info = useCallback((title: string, message?: string) => addToast({ type: 'info', title, message }), [addToast]);

  const addJobToast = useCallback((status: JobStatus, opts?: { title?: string; message?: string; jobId?: string; duration?: number }) => {
    const titles: Record<JobStatus, string> = {
      queued: 'Job Queued',
      running: 'Job Running',
      completed: 'Job Completed',
      failed: 'Job Failed',
    };
    const messages: Record<JobStatus, string> = {
      queued: 'Your optimization is queued and will start shortly.',
      running: 'Optimization is in progress…',
      completed: 'Optimization completed successfully.',
      failed: 'Optimization failed. Check details.',
    };
    const typeMap: Record<JobStatus, ToastType> = {
      queued: 'queued',
      running: 'running',
      completed: 'completed',
      failed: 'failed',
    };
    addToast({
      type: typeMap[status],
      title: opts?.title ?? titles[status],
      message: opts?.message ?? messages[status],
      jobStatus: status,
      jobId: opts?.jobId,
      duration: opts?.duration,
    });
  }, [addToast]);

  const notifyJobStatus = useCallback((status: JobStatus, jobId?: string, customMessage?: string) => {
    addJobToast(status, { jobId, message: customMessage });
  }, [addJobToast]);

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast, success, error, warning, info, addJobToast, notifyJobStatus }}>
      {children}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}

const ICONS: Record<string, string> = {
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

const STYLES: Record<string, string> = {
  success: 'border-l-4 border-l-emerald-400 bg-emerald-50/90 dark:bg-emerald-950/40 dark:border-l-emerald-500',
  error: 'border-l-4 border-l-red-400 bg-red-50/90 dark:bg-red-950/40 dark:border-l-red-500',
  warning: 'border-l-4 border-l-amber-400 bg-amber-50/90 dark:bg-amber-950/40 dark:border-l-amber-500',
  info: 'border-l-4 border-l-blue-400 bg-blue-50/90 dark:bg-blue-950/40 dark:border-l-blue-500',
  queued: 'border-l-4 border-l-slate-400 bg-slate-50/90 dark:bg-slate-900/50 dark:border-l-slate-500',
  running: 'border-l-4 border-l-blue-400 bg-blue-50/90 dark:bg-blue-950/40 dark:border-l-blue-400',
  completed: 'border-l-4 border-l-emerald-400 bg-emerald-50/90 dark:bg-emerald-950/40 dark:border-l-emerald-500',
  failed: 'border-l-4 border-l-red-400 bg-red-50/90 dark:bg-red-950/40 dark:border-l-red-500',
  'job-queued': 'border-l-4 border-l-slate-400 bg-slate-50/90 dark:bg-slate-900/50',
  'job-running': 'border-l-4 border-l-blue-400 bg-blue-50/90 dark:bg-blue-950/40',
  'job-completed': 'border-l-4 border-l-emerald-400 bg-emerald-50/90 dark:bg-emerald-950/40',
  'job-failed': 'border-l-4 border-l-red-400 bg-red-50/90 dark:bg-red-950/40',
};

const ICON_COLORS: Record<string, string> = {
  success: 'text-emerald-500',
  error: 'text-red-500',
  warning: 'text-amber-500',
  info: 'text-blue-500',
  queued: 'text-slate-500',
  running: 'text-blue-500 animate-spin',
  completed: 'text-emerald-500',
  failed: 'text-red-500',
  'job-queued': 'text-slate-500',
  'job-running': 'text-blue-500 animate-spin',
  'job-completed': 'text-emerald-500',
  'job-failed': 'text-red-500',
};

function ToastContainer({ toasts, onRemove }: { toasts: Toast[]; onRemove: (id: string) => void }) {
  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-[9999] flex flex-col gap-3 max-w-sm w-full pointer-events-none">
      {toasts.map(toast => {
        const key = toast.jobStatus ?? toast.type;
        return (
        <div
          key={toast.id}
          role="status"
          aria-live="polite"
          className={`pointer-events-auto glass-strong backdrop-blur-xl animate-glass-in p-4 flex items-start gap-3 cursor-pointer rounded-[14px] border border-white/40 shadow-lg ${STYLES[toast.type] ?? STYLES[key] ?? STYLES.info}`}
          onClick={() => onRemove(toast.id)}
        >
          <span className={`text-lg font-bold mt-0.5 flex items-center justify-center w-6 h-6 rounded-full bg-white/60 backdrop-blur shadow-sm border border-white/40 ${ICON_COLORS[toast.type] ?? ICON_COLORS[key] ?? ICON_COLORS.info}`}>
            {ICONS[toast.type] ?? ICONS[key] ?? ICONS.info}
          </span>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 leading-none">{toast.title}</p>
            {toast.message && (
              <p className="text-xs text-gray-600 dark:text-gray-400 mt-1 leading-snug break-words">{toast.message}</p>
            )}
            {toast.jobId && (
              <p className="text-[10px] font-mono text-gray-400 mt-1 truncate">{toast.jobId}</p>
            )}
          </div>
          <button
            aria-label="Dismiss notification"
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 text-sm leading-none p-1 rounded-md hover:bg-white/40 transition-colors"
            onClick={e => { e.stopPropagation(); onRemove(toast.id); }}
          >
            ✕
          </button>
        </div>
        );
      })}
    </div>
  );
}
