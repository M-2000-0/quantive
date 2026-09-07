import { useState, useEffect, useMemo } from 'react';
import { Link, useLocation } from 'react-router-dom';
import Badge from './ui/Badge';
import { useAuth } from '../stores/auth';
import { Target } from 'lucide-react';

/* ── Types ─────────────────────────────────────────────────────────── */

interface NavItem {
  label: string;
  path: string;
  icon: React.ReactNode;
  group: string;
  essential?: boolean;   // shown in simplified mode
  advanced?: boolean;    // hidden in simplified mode
}

/* ── Navigation Data ───────────────────────────────────────────────── */

const ALL_ITEMS: NavItem[] = [
  // Core (essential)
  { label: 'Dashboard', path: '/dashboard', group: 'Core', essential: true, icon: <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6z" /></svg> },
  { label: 'Portfolio', path: '/portfolios', group: 'Core', essential: true, icon: <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M20.25 14.15v4.25c0 1.094-.787 2.036-1.872 2.18-2.087.277-4.216.42-6.378.42s-4.291-.143-6.378-.42c-1.085-.144-1.872-1.086-1.872-2.18v-4.25m16.5 0a2.18 2.18 0 00.75-1.661V8.706c0-1.081-.768-2.015-1.837-2.175a48.114 48.114 0 00-3.413-.387m4.5 8.006c-.194.165-.42.295-.673.38A23.978 23.978 0 0112 15.75c-2.648 0-5.195-.429-7.577-1.22a2.016 2.016 0 01-.673-.38m0 0A2.18 2.18 0 013 12.489V8.706c0-1.081.768-2.015 1.837-2.175a48.111 48.111 0 013.413-.387m7.5 0V5.25A2.25 2.25 0 0013.5 3h-3a2.25 2.25 0 00-2.25 2.25v.894m7.5 0a48.667 48.667 0 00-7.5 0" /></svg> },
  { label: 'Optimize', path: '/optimizations/new', group: 'Core', essential: true, icon: <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M10.5 6h9.75M10.5 6a1.5 1.5 0 11-3 0m3 0a1.5 1.5 0 10-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-9.75 0h9.75" /></svg> },

  // Market (essential)
  { label: 'Market Data', path: '/market', group: 'Market', essential: true, icon: <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18L9 11.25l4.306 4.307a11.95 11.95 0 015.814-5.519l2.74-1.22m0 0l-5.94-2.28m5.94 2.28l-2.28 5.941" /></svg> },
  { label: 'Risk', path: '/risk', group: 'Market', essential: true, icon: <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126z" /></svg> },
  { label: 'What-If', path: '/whatif', group: 'Market', essential: true, icon: <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25z" /></svg> },

  // Analytics (advanced)
  { label: 'AI Advisor', path: '/advisor', group: 'Analytics', advanced: true, icon: <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25z" /></svg> },
  { label: 'Peers', path: '/peers', group: 'Analytics', advanced: true, icon: <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747" /></svg> },
  { label: 'Maturity Ladder', path: '/maturity', group: 'Analytics', advanced: true, icon: <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75z" /></svg> },
  { label: 'Reports', path: '/reports', group: 'Analytics', advanced: true, icon: <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" /></svg> },

  // Government (advanced)
  { label: 'Approvals', path: '/approvals', group: 'Government', advanced: true, icon: <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg> },
  { label: 'Sovereign DSA', path: '/sovereign-dsa', group: 'Government', advanced: true, icon: <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12" /></svg> },
  { label: 'Minister View', path: '/minister', group: 'Government', advanced: true, icon: <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" /></svg> },

  // AI Intelligence (advanced)
  { label: 'AI Copilot', path: '/copilot', group: 'AI', advanced: true, icon: <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12z" /></svg> },
  { label: 'Digital Twin', path: '/digital-twin', group: 'AI', advanced: true, icon: <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M21 7.5l-2.25-1.313M21 7.5v2.25m0-2.25l-2.25 1.313M3 7.5l2.25-1.313M3 7.5l2.25 1.313M3 7.5v2.25m9 3l2.25-1.313M12 12.75l-2.25-1.313M12 12.75V15" /></svg> },
  { label: 'Knowledge Graph', path: '/knowledge-graph', group: 'AI', advanced: true, icon: <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" /></svg> },

  // Security (advanced)
  { label: 'Audit Log', path: '/audit', group: 'Security', advanced: true, icon: <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 01-1.043 3.296 3.745 3.745 0 01-3.296 1.043A3.745 3.745 0 0112 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 01-3.296-1.043 3.745 3.745 0 01-1.043-3.296A3.745 3.745 0 013 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 011.043-3.296 3.746 3.746 0 013.296-1.043A3.746 3.746 0 0112 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 013.296 1.043 3.746 3.746 0 011.043 3.296A3.745 3.745 0 0121 12z" /></svg> },
  { label: 'Settings', path: '/settings', group: 'Settings', advanced: true, icon: <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z" /><path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg> },
];

/* ── Component ─────────────────────────────────────────────────────── */

interface ProgressiveSidebarProps {
  collapsed: boolean;
}

export default function ProgressiveSidebar({ collapsed }: ProgressiveSidebarProps) {
  const location = useLocation();
  const { user } = useAuth();
  const userRole = (user as unknown as Record<string, unknown>)?.role as string || 'analyst';

  // Role-based view presets
  const ROLE_VIEWS: Record<string, string[]> = {
    minister: ['Dashboard', 'Minister View', 'Reports', 'ROI Engine'],
    director: ['Dashboard', 'Portfolio', 'Optimize', 'Approvals', 'Reports', 'Risk'],
    analyst: ['Dashboard', 'Portfolio', 'Optimize', 'Market Data', 'Risk', 'What-If'],
    senior_analyst: ['Dashboard', 'Portfolio', 'Optimize', 'Market Data', 'Risk', 'What-If', 'AI Advisor', 'Reports'],
    admin: ALL_ITEMS.map(i => i.label) };

  const [mode, setMode] = useState<'simplified' | 'full' | 'role'>(() => {
    return (localStorage.getItem('quantive_nav_mode') as 'simplified' | 'full' | 'role') || 'role';
  });

  useEffect(() => {
    localStorage.setItem('quantive_nav_mode', mode);
  }, [mode]);

  const filteredItems = useMemo(() => {
    if (mode === 'full') return ALL_ITEMS;
    if (mode === 'role') {
      const allowed = ROLE_VIEWS[userRole] || ROLE_VIEWS.analyst;
      return ALL_ITEMS.filter((item) => allowed.includes(item.label));
    }
    return ALL_ITEMS.filter((item) => item.essential);
  }, [mode, userRole]);

  const groups = useMemo(() => {
    const map = new Map<string, NavItem[]>();
    filteredItems.forEach((item) => {
      if (!map.has(item.group)) map.set(item.group, []);
      map.get(item.group)!.push(item);
    });
    return Array.from(map.entries());
  }, [filteredItems]);

  if (collapsed) return null;

  return (
    <nav className="w-64 h-full bg-white/30 backdrop-blur-xl border-r border-white/40 flex flex-col">
      {/* Role badge + Mode toggle */}
      <div className="px-4 py-3 border-b border-white/30">
        <div className="flex items-center gap-2 mb-2">
          <Badge variant="info" className="text-[10px] uppercase">{userRole}</Badge>
        </div>
        <div className="flex items-center gap-1">
          {(['role', 'simplified', 'full'] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`flex-1 px-2 py-1.5 rounded-lg text-[11px] font-semibold transition-all ${
                mode === m
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'bg-white/40 text-slate-500 hover:bg-white/60'
              }`}
            >
              {m === 'role' ? 'My View' : m === 'simplified' ? 'Simple' : 'Full'}
            </button>
          ))}
        </div>
        {mode === 'role' && (
          <p className="text-[10px] text-slate-400 mt-1.5 text-center">
            Showing features for {userRole} role
          </p>
        )}
      </div>

      {/* Navigation groups */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-4">
        {groups.map(([groupName, items]) => (
          <div key={groupName}>
            <p className="px-2 mb-1.5 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
              {groupName}
            </p>
            <div className="space-y-0.5">
              {items.map((item) => {
                const isActive = location.pathname === item.path;
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`flex items-center gap-2.5 px-2.5 py-2 rounded-xl text-sm font-medium transition-all ${
                      isActive
                        ? 'bg-blue-600/10 text-blue-700 shadow-sm'
                        : 'text-slate-600 hover:bg-white/50 hover:text-slate-900'
                    }`}
                  >
                    <span className={isActive ? 'text-blue-600' : 'text-slate-400'}>
                      {item.icon}
                    </span>
                    {item.label}
                    {item.advanced && mode === 'full' && (
                      <Badge variant="info" className="ml-auto text-[9px]">ADV</Badge>
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-white/30">
        <Link
          to="/onboarding"
          className="flex items-center gap-2 px-3 py-2 rounded-xl bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-100 text-xs font-semibold text-blue-700 hover:shadow-md transition-all"
        >
          <Target className="w-5 h-5" />
          Guided Setup
        </Link>
      </div>
    </nav>
  );
}
