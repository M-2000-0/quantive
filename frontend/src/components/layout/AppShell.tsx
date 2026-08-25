import { useState, useMemo, useEffect, useCallback } from 'react';
import { useLocation, Link } from 'react-router-dom';
import { useAuth } from '../../stores/auth';
import Sidebar from './Sidebar';
import Breadcrumbs from '../ui/Breadcrumbs';
import ThemeToggle from '../ThemeToggle';
import NotificationBell from '../NotificationBell';
import CommandPalette from '../CommandPalette';
import PwaInstallBanner from '../PwaInstallBanner';

const PATH_LABELS: Record<string, string> = {
  '/': 'Overview',
  '/portfolios': 'Debt Portfolio',
  '/portfolios/new': 'New Portfolio',
  '/optimizations': 'Optimization',
  '/optimizations/new': 'New Optimization',
  '/results': 'Results',
  '/benchmarks': 'Benchmarks',
  '/reports': 'Reports',
  '/audit': 'Audit Log',
  '/status': 'System Status',
};

function getBreadcrumbs(pathname: string) {
  if (pathname === '/') return [{ label: 'Overview' }];

  const segments = pathname.split('/').filter(Boolean);
  const crumbs: Array<{ label: string; path?: string }> = [{ label: 'Home', path: '/' }];

  let accumulated = '';
  for (const segment of segments) {
    accumulated += '/' + segment;
    const label = PATH_LABELS[accumulated] || segment.charAt(0).toUpperCase() + segment.slice(1);
    if (accumulated === pathname) {
      crumbs.push({ label });
    } else {
      crumbs.push({ label, path: accumulated });
    }
  }

  return crumbs;
}

function getUserInitials(name: string): string {
  return name
    .split(' ')
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

const ROLE_BADGES: Record<string, string> = {
  admin: 'bg-amber-400/14 text-amber-700 ring-1 ring-amber-400/20 shadow-sm',
  analyst: 'bg-blue-500/14 text-blue-700 ring-1 ring-blue-500/18 shadow-sm',
  viewer: 'bg-slate-500/12 text-slate-600 ring-1 ring-slate-400/15 shadow-sm',
};

export default function AppShell({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const { pathname } = useLocation();
  const { user, logout } = useAuth();

  const breadcrumbs = useMemo(() => getBreadcrumbs(pathname), [pathname]);
  const pageTitle = PATH_LABELS[pathname] || breadcrumbs[breadcrumbs.length - 1]?.label || '';
  const initials = user ? getUserInitials(user.name) : '??';
  const roleBadge = user ? ROLE_BADGES[user.role] || ROLE_BADGES.viewer : '';

  // Global Cmd+K / Ctrl+K handler — AppShell owns the palette trigger
  const openPalette = useCallback(() => setPaletteOpen(true), []);
  const closePalette = useCallback(() => setPaletteOpen(false), []);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        // avoid triggering when already in palette input? still allow close/reopen
        e.preventDefault();
        setPaletteOpen(v => !v);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  return (
    <div className="flex h-screen overflow-hidden relative">
      {/* liquid depth backdrop for content area */}
      <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
        <div className="liquid-orb w-[720px] h-[520px] -top-40 -right-40 bg-gradient-to-br from-blue-400/20 via-violet-400/14 to-cyan-400/16" />
        <div className="liquid-orb w-[560px] h-[560px] top-[42%] -left-40 bg-gradient-to-br from-sky-400/14 via-blue-400/10 to-indigo-400/12" />
        <div className="liquid-orb w-[640px] h-[420px] bottom-0 right-[18%] bg-gradient-to-br from-violet-400/10 via-fuchsia-400/8 to-blue-400/12" />
      </div>

      <Sidebar
        collapsed={!sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        currentPath={pathname}
      />

      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-16 items-center justify-between glass-header sticky top-0 z-30 px-4 lg:px-6">
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="rounded-xl p-2 text-slate-600 hover:bg-white/60 hover:text-slate-900 border border-transparent hover:border-white/60 hover:shadow-sm transition-all lg:hidden backdrop-blur-md"
              onClick={() => setSidebarOpen(true)}
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
              </svg>
            </button>

            <div>
              <h1 className="text-[15px] font-semibold tracking-tight text-slate-900">{pageTitle}</h1>
              <Breadcrumbs items={breadcrumbs} />
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Global search trigger — opens CommandPalette via AppShell */}
            <button
              type="button"
              onClick={openPalette}
              className="hidden md:inline-flex items-center gap-2 rounded-xl border border-white/50 bg-white/60 px-3 py-1.5 text-sm text-slate-600 hover:bg-white/80 hover:text-slate-900 shadow-sm backdrop-blur-md transition-all"
              aria-label="Open command palette"
            >
              <svg className="h-4 w-4 text-slate-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.7} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.2-5.2m0 0A7.5 7.5 0 105.2 5.2a7.5 7.5 0 0010.6 10.6z" />
              </svg>
              <span className="text-xs font-medium">Search</span>
              <span className="ml-1 inline-flex items-center gap-1 rounded-md border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-[10px] font-semibold tracking-wide text-slate-500">
                <span>⌘</span>K
              </span>
            </button>
            <button
              type="button"
              onClick={openPalette}
              className="md:hidden rounded-xl p-2 text-slate-500 hover:bg-white/70 hover:text-slate-700 border border-transparent hover:border-white/60 hover:shadow-md backdrop-blur-md transition-all"
              aria-label="Search"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.7} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.2-5.2m0 0A7.5 7.5 0 105.2 5.2a7.5 7.5 0 0010.6 10.6z" />
              </svg>
            </button>

            <ThemeToggle />
            <NotificationBell />
            {user && (
              <>
                <div className="hidden text-right sm:block">
                  <p className="text-sm font-semibold tracking-tight text-slate-900">{user.name}</p>
                  <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest backdrop-blur-md border border-white/40 shadow-sm ${roleBadge}`}>
                    {user.role}
                  </span>
                </div>

                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-slate-900 to-slate-700 text-xs font-bold text-white shadow-lg ring-1 ring-white/20">
                  {initials}
                </div>
              </>
            )}

            <Link
              to="/settings"
              className="rounded-xl p-2 text-slate-500 hover:bg-white/70 hover:text-slate-700 border border-transparent hover:border-white/60 hover:shadow-md backdrop-blur-md transition-all"
              title="Settings"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </Link>

            <button
              type="button"
              onClick={logout}
              className="rounded-xl p-2 text-slate-500 hover:bg-white/70 hover:text-slate-700 border border-transparent hover:border-white/60 hover:shadow-md backdrop-blur-md transition-all"
              title="Sign out"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15m3 0l3-3m0 0l-3-3m3 3H9" />
              </svg>
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-4 lg:p-6 relative">
          {children}
        </main>
      </div>

      {/* Command palette — triggered via AppShell (Cmd+K) */}
      <CommandPalette isOpen={paletteOpen} onClose={closePalette} />
      {/* PWA liquid glass install banner */}
      <PwaInstallBanner />
    </div>
  );
}
