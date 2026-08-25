import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';

export interface Toast {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message?: string;
  duration?: number;
}

interface ToastContextValue {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
  success: (title: string, message?: string) => void;
  error: (title: string, message?: string) => void;
  warning: (title: string, message?: string) => void;
  info: (title: string, message?: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const addToast = useCallback((toast: Omit<Toast, 'id'>) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    const newToast = { ...toast, id };
    setToasts(prev => [...prev.slice(-4), newToast]); // max 5 visible

    const duration = toast.duration ?? (toast.type === 'error' ? 6000 : 4000);
    setTimeout(() => removeToast(id), duration);
  }, [removeToast]);

  const success = useCallback((title: string, message?: string) => addToast({ type: 'success', title, message }), [addToast]);
  const error = useCallback((title: string, message?: string) => addToast({ type: 'error', title, message }), [addToast]);
  const warning = useCallback((title: string, message?: string) => addToast({ type: 'warning', title, message }), [addToast]);
  const info = useCallback((title: string, message?: string) => addToast({ type: 'info', title, message }), [addToast]);

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast, success, error, warning, info }}>
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
};

const STYLES: Record<string, string> = {
  success: 'border-l-4 border-l-green-400 bg-green-50 dark:bg-green-950/50 dark:border-l-green-500',
  error: 'border-l-4 border-l-red-400 bg-red-50 dark:bg-red-950/50 dark:border-l-red-500',
  warning: 'border-l-4 border-l-yellow-400 bg-yellow-50 dark:bg-yellow-950/50 dark:border-l-yellow-500',
  info: 'border-l-4 border-l-blue-400 bg-blue-50 dark:bg-blue-950/50 dark:border-l-blue-500',
};

const ICON_COLORS: Record<string, string> = {
  success: 'text-green-500',
  error: 'text-red-500',
  warning: 'text-yellow-500',
  info: 'text-blue-500',
};

function ToastContainer({ toasts, onRemove }: { toasts: Toast[]; onRemove: (id: string) => void }) {
  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-[9999] flex flex-col gap-2 max-w-sm w-full pointer-events-none">
      {toasts.map(toast => (
        <div
          key={toast.id}
          className={`pointer-events-auto glass animate-glass-in p-4 flex items-start gap-3 cursor-pointer ${STYLES[toast.type]}`}
          onClick={() => onRemove(toast.id)}
        >
          <span className={`text-lg font-bold mt-0.5 ${ICON_COLORS[toast.type]}`}>
            {ICONS[toast.type]}
          </span>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{toast.title}</p>
            {toast.message && (
              <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5 truncate">{toast.message}</p>
            )}
          </div>
          <button className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 text-sm" onClick={e => { e.stopPropagation(); onRemove(toast.id); }}>
            ✕
          </button>
        </div>
      ))}
    </div>
  );
}
