import { useState, useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../../stores/auth';
import Sidebar from './Sidebar';
import Breadcrumbs from '../ui/Breadcrumbs';

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
  admin: 'bg-amber-500/10 text-amber-400 ring-1 ring-amber-500/20',
  analyst: 'bg-blue-500/10 text-blue-400 ring-1 ring-blue-500/20',
  viewer: 'bg-slate-500/10 text-slate-400 ring-1 ring-slate-500/20',
};

export default function AppShell({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { pathname } = useLocation();
  const { user, logout } = useAuth();

  const breadcrumbs = useMemo(() => getBreadcrumbs(pathname), [pathname]);
  const pageTitle = PATH_LABELS[pathname] || breadcrumbs[breadcrumbs.length - 1]?.label || '';
  const initials = user ? getUserInitials(user.name) : '??';
  const roleBadge = user ? ROLE_BADGES[user.role] || ROLE_BADGES.viewer : '';

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      <Sidebar
        collapsed={!sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        currentPath={pathname}
      />

      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-4 lg:px-6">
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-700 lg:hidden"
              onClick={() => setSidebarOpen(true)}
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
              </svg>
            </button>

            <div>
              <h1 className="text-base font-semibold text-slate-900">{pageTitle}</h1>
              <Breadcrumbs items={breadcrumbs} />
            </div>
          </div>

          <div className="flex items-center gap-3">
            {user && (
              <>
                <div className="hidden text-right sm:block">
                  <p className="text-sm font-medium text-slate-900">{user.name}</p>
                  <span className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${roleBadge}`}>
                    {user.role}
                  </span>
                </div>

                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-900 text-xs font-bold text-white">
                  {initials}
                </div>
              </>
            )}

            <button
              type="button"
              onClick={logout}
              className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
              title="Sign out"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15m3 0l3-3m0 0l-3-3m3 3H9" />
              </svg>
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
