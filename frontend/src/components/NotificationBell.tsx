import { useState, useEffect, useRef } from 'react';
import { api } from '../api';

interface Notification {
  id: string;
  title: string;
  message: string;
  type: string;
  read: boolean;
  created_at: string;
}

export default function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadUnreadCount();
    const interval = setInterval(loadUnreadCount, 30000); // poll every 30s
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const loadUnreadCount = async () => {
    try {
      const res = await api.notifications.unreadCount() as { count: number };
      setUnreadCount(res.count);
    } catch {
      // silently fail
    }
  };

  const loadNotifications = async () => {
    setLoading(true);
    try {
      const res = await api.notifications.list({ limit: 10 }) as unknown as { data: Notification[] };
      setNotifications(res.data || []);
    } catch {
      // silently fail
    }
    setLoading(false);
  };

  const handleOpen = () => {
    setOpen(!open);
    if (!open) loadNotifications();
  };

  const markRead = async (id: string) => {
    try {
      await api.notifications.markRead(id);
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch {
      // silently fail
    }
  };

  const markAllRead = async () => {
    try {
      await api.notifications.markAllRead();
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
      setUnreadCount(0);
    } catch {
      // silently fail
    }
  };

  const typeIcons: Record<string, string> = {
    optimization_complete: '✅',
    rate_alert: '📈',
    risk_change: '⚠️',
    report_ready: '📄',
    system: '🔧',
    default: '🔔',
  };

  return (
    <div ref={ref} className="relative">
      <button
        onClick={handleOpen}
        className="relative w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-200 hover:bg-white/10"
      >
        <svg className="h-5 w-5 text-slate-300" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
        </svg>
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] flex items-center justify-center rounded-full bg-red-500 text-white text-[10px] font-bold px-1 animate-pulse">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute top-full right-0 mt-2 w-80 glass-float p-0 overflow-hidden animate-glass-in">
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 dark:border-white/5">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              Notifications
              {unreadCount > 0 && (
                <span className="ml-2 text-xs font-medium text-blue-400">({unreadCount} new)</span>
              )}
            </h3>
            {unreadCount > 0 && (
              <button onClick={markAllRead} className="text-xs text-blue-400 hover:text-blue-300">
                Mark all read
              </button>
            )}
          </div>

          <div className="max-h-80 overflow-y-auto">
            {loading ? (
              <div className="p-4 space-y-3">
                {[1, 2, 3].map(i => (
                  <div key={i} className="skeleton h-12 w-full" />
                ))}
              </div>
            ) : notifications.length === 0 ? (
              <div className="p-8 text-center text-gray-400 text-sm">
                No notifications yet
              </div>
            ) : (
              notifications.map(n => (
                <div
                  key={n.id}
                  onClick={() => !n.read && markRead(n.id)}
                  className={`px-4 py-3 border-b border-white/5 cursor-pointer transition-colors hover:bg-white/5 ${
                    !n.read ? 'bg-blue-500/5' : ''
                  }`}
                >
                  <div className="flex items-start gap-2">
                    <span className="text-sm mt-0.5">{typeIcons[n.type] || typeIcons.default}</span>
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm ${!n.read ? 'font-semibold text-gray-900 dark:text-gray-100' : 'text-gray-700 dark:text-gray-300'}`}>
                        {n.title}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">{n.message}</p>
                      <p className="text-[10px] text-gray-400 mt-1">{new Date(n.created_at).toLocaleString()}</p>
                    </div>
                    {!n.read && <div className="w-2 h-2 rounded-full bg-blue-400 mt-1.5" />}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
