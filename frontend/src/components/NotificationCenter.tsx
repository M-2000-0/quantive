import { useState, useCallback } from 'react';

type NotificationType = 'info' | 'success' | 'warning' | 'error' | 'optimization' | 'alert';
type NotificationCategory = 'all' | 'optimization' | 'risk' | 'team' | 'system';

interface Notification {
  id: string;
  type: NotificationType;
  category: NotificationCategory;
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  actionable?: boolean;
  actionLabel?: string;
  actionRoute?: string;
}

const MOCK_NOTIFICATIONS: Notification[] = [
  { id: 'n1', type: 'optimization', category: 'optimization', title: 'Optimization Complete', message: 'Cost optimization reduced annual financing cost by 3.2% ($7.4M savings)', timestamp: '2 min ago', read: false, actionable: true, actionLabel: 'View Results', actionRoute: '/optimizations' },
  { id: 'n2', type: 'alert', category: 'risk', title: 'Duration Mismatch Detected', message: 'Portfolio duration (4.8yr) exceeds target (3.5yr) by 37%. Consider extending maturities.', timestamp: '15 min ago', read: false, actionable: true, actionLabel: 'Review Risk', actionRoute: '/risk' },
  { id: 'n3', type: 'info', category: 'team', title: 'Ana Torres approved optimization', message: 'The Q3 cost reduction proposal has been approved and is ready for execution.', timestamp: '1 hr ago', read: false },
  { id: 'n4', type: 'success', category: 'optimization', title: 'Consensus Alert', message: '73% of similar portfolios are extending duration. Your portfolio is aligned.', timestamp: '2 hr ago', read: true },
  { id: 'n5', type: 'warning', category: 'risk', title: 'Credit Downgrade Warning', message: '2 holdings in your portfolio have negative credit outlook. Review exposure.', timestamp: '3 hr ago', read: true, actionable: true, actionLabel: 'View Holdings', actionRoute: '/portfolios' },
  { id: 'n6', type: 'info', category: 'system', title: 'System Update', message: 'Quantive v2.1.0 deployed. New features: Adaptive Dashboard, Pipeline Orchestrator.', timestamp: '5 hr ago', read: true },
  { id: 'n7', type: 'info', category: 'team', title: 'New team member', message: 'Priya Nair has joined as Analyst. Say hello!', timestamp: '1 day ago', read: true },
  { id: 'n8', type: 'error', category: 'system', title: 'API Connection Failed', message: 'Bloomberg data feed timed out. Retrying in 60 seconds.', timestamp: '1 day ago', read: true },
  { id: 'n9', type: 'optimization', category: 'optimization', title: 'Refinance Opportunity', message: 'EUR/USD hedge rate is favorable. Consider refinancing $45M EUR exposure.', timestamp: '2 days ago', read: true, actionable: true, actionLabel: 'View Opportunity', actionRoute: '/opportunities' },
];

const TYPE_STYLES: Record<NotificationType, { bg: string; icon: string; color: string }> = {
  info: { bg: 'bg-blue-50', icon: 'Info', color: 'text-blue-600' },
  success: { bg: 'bg-emerald-50', icon: 'CheckCircle', color: 'text-emerald-600' },
  warning: { bg: 'bg-amber-50', icon: 'AlertTriangle', color: 'text-amber-600' },
  error: { bg: 'bg-red-50', icon: 'XCircle', color: 'text-red-600' },
  optimization: { bg: 'bg-purple-50', icon: 'Zap', color: 'text-purple-600' },
  alert: { bg: 'bg-orange-50', icon: '🔔', color: 'text-orange-600' } };

const CATEGORY_LABELS: Record<NotificationCategory, string> = {
  all: 'All',
  optimization: 'Optimization',
  risk: 'Risk',
  team: 'Team',
  system: 'System' };

export default function NotificationCenter() {
  const [notifications, setNotifications] = useState<Notification[]>(MOCK_NOTIFICATIONS);
  const [isOpen, setIsOpen] = useState(false);
  const [filter, setFilter] = useState<NotificationCategory>('all');
  const [showUnreadOnly, setShowUnreadOnly] = useState(false);

  const unreadCount = notifications.filter(n => !n.read).length;

  const filteredNotifications = notifications.filter(n => {
    if (filter !== 'all' && n.category !== filter) return false;
    if (showUnreadOnly && n.read) return false;
    return true;
  });

  const markAsRead = useCallback((id: string) => {
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
  }, []);

  const markAllAsRead = useCallback(() => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
  }, []);

  const clearNotification = useCallback((id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  }, []);

  const clearAll = useCallback(() => {
    setNotifications([]);
  }, []);

  return (
    <div className="relative">
      {/* Bell trigger */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative rounded-xl p-2 text-slate-500 hover:bg-white/70 hover:text-slate-700 border border-transparent hover:border-white/60 hover:shadow-md backdrop-blur-md transition-all"
        title="Notifications"
      >
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
        </svg>
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[9px] font-bold text-white ring-2 ring-white shadow-sm animate-pulse">
            {unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />

          <div className="fixed right-4 top-16 z-50 w-96 max-h-[80vh] glass-strong rounded-2xl shadow-2xl border border-white/30 overflow-hidden animate-glass-in">
            {/* Header */}
            <div className="px-5 py-4 border-b border-white/20">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-base font-bold text-slate-900">
                  Notifications
                  {unreadCount > 0 && (
                    <span className="ml-2 text-xs font-bold text-blue-600 bg-blue-50 rounded-full px-2 py-0.5">
                      {unreadCount} unread
                    </span>
                  )}
                </h2>
                <div className="flex items-center gap-1">
                  {unreadCount > 0 && (
                    <button
                      onClick={markAllAsRead}
                      className="text-xs font-medium text-blue-600 hover:text-blue-700 transition-colors"
                    >
                      Mark all read
                    </button>
                  )}
                  <button
                    onClick={() => setShowUnreadOnly(!showUnreadOnly)}
                    className={`text-xs px-2 py-1 rounded-lg transition-colors ${
                      showUnreadOnly ? 'bg-blue-50 text-blue-700' : 'text-slate-500 hover:text-slate-700'
                    }`}
                  >
                    {showUnreadOnly ? 'All' : 'Unread'}
                  </button>
                </div>
              </div>

              {/* Category tabs */}
              <div className="flex gap-1 overflow-x-auto">
                {(Object.keys(CATEGORY_LABELS) as NotificationCategory[]).map(cat => {
                  const count = cat === 'all'
                    ? notifications.length
                    : notifications.filter(n => n.category === cat).length;
                  return (
                    <button
                      key={cat}
                      onClick={() => setFilter(cat)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${
                        filter === cat
                          ? 'bg-white/80 text-slate-900 shadow-sm'
                          : 'text-slate-500 hover:text-slate-700 hover:bg-white/40'
                      }`}
                    >
                      {CATEGORY_LABELS[cat]}
                      {count > 0 && (
                        <span className="ml-1 text-[10px] opacity-60">({count})</span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Notification list */}
            <div className="overflow-y-auto max-h-[50vh]">
              {filteredNotifications.length === 0 ? (
                <div className="px-6 py-12 text-center">
                  <div className="text-3xl mb-2">🎉</div>
                  <p className="text-sm font-medium text-slate-700">All caught up!</p>
                  <p className="text-xs text-slate-500 mt-1">No notifications to show</p>
                </div>
              ) : (
                <div className="divide-y divide-white/15">
                  {filteredNotifications.map(n => {
                    const style = TYPE_STYLES[n.type];
                    return (
                      <div
                        key={n.id}
                        className={`px-5 py-4 hover:bg-white/30 transition-colors cursor-pointer ${
                          !n.read ? 'bg-blue-50/30' : ''
                        }`}
                        onClick={() => markAsRead(n.id)}
                      >
                        <div className="flex items-start gap-3">
                          {/* Icon */}
                          <div className={`w-8 h-8 rounded-xl ${style.bg} flex items-center justify-center text-sm shrink-0`}>
                            {style.icon}
                          </div>

                          {/* Content */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <h4 className={`text-sm font-semibold ${!n.read ? 'text-slate-900' : 'text-slate-700'}`}>
                                {n.title}
                              </h4>
                              {!n.read && <div className="w-2 h-2 rounded-full bg-blue-500 shrink-0" />}
                            </div>
                            <p className="text-xs text-slate-600 mt-0.5 line-clamp-2">{n.message}</p>
                            <div className="flex items-center gap-3 mt-2">
                              <span className="text-[11px] text-slate-400">{n.timestamp}</span>
                              {n.actionable && (
                                <button
                                  className="text-[11px] font-semibold text-blue-600 hover:text-blue-700 transition-colors"
                                  onClick={e => { e.stopPropagation(); }}
                                >
                                  {n.actionLabel} →
                                </button>
                              )}
                              <button
                                className="text-[11px] text-slate-400 hover:text-red-500 transition-colors ml-auto"
                                onClick={e => { e.stopPropagation(); clearNotification(n.id); }}
                              >
                                Dismiss
                              </button>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Footer */}
            {notifications.length > 0 && (
              <div className="px-5 py-3 border-t border-white/20 flex items-center justify-between">
                <button
                  onClick={clearAll}
                  className="text-xs font-medium text-slate-500 hover:text-red-600 transition-colors"
                >
                  Clear all
                </button>
                <span className="text-[11px] text-slate-400">
                  {notifications.length} notification{notifications.length !== 1 ? 's' : ''}
                </span>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
