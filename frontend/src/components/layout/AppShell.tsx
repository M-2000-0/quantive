import { useState, useMemo, useEffect, useCallback } from 'react';
import { useLocation, Link } from 'react-router-dom';
import { useAuth } from '../../stores/auth';
import Sidebar from './Sidebar';
import Breadcrumbs from '../ui/Breadcrumbs';
import ThemeTransition from '../ThemeTransition';
import { Settings } from 'lucide-react';
import NotificationCenter from '../NotificationCenter';
import CommandPalette from '../CommandPalette';
import KeyboardShortcutOverlay from '../KeyboardShortcutOverlay';
import PwaInstallBanner from '../PwaInstallBanner';
import PageTransition from '../PageTransition';
import OnboardingTour from '../OnboardingTour';
import GuidedTour from '../GuidedTour';
import { useOnboardingTour } from '../../hooks/useOnboardingTour';

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
  const tour = useOnboardingTour();

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
    <div className="flex h-screen overflow-hidden relative" style={{ background: 'var(--bg)' }}>

      <Sidebar
        collapsed={!sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        currentPath={pathname}
      />

      <div className="flex flex-1 flex-col overflow-hidden">
        <header style={{ height: 52, display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 22px', background: 'var(--topbar-bg)', backdropFilter: 'blur(16px) saturate(1.2)', WebkitBackdropFilter: 'blur(16px) saturate(1.2)', flexShrink: 0, position: 'relative', zIndex: 5, transition: 'background-color 0.3s ease', borderBottom: '1px solid var(--border)' }}>
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

          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <button
              type="button"
              onClick={openPalette}
              className="hidden md:inline-flex"
              style={{
                display: 'flex', alignItems: 'center', gap: 9,
                padding: '7px 12px', background: 'var(--field)',
                border: '1px solid var(--border)', borderRadius: 'var(--radius)',
                cursor: 'pointer', color: 'var(--text3)', fontSize: 13,
                transition: 'all 0.18s ease', flex: 1, maxWidth: 360,
              }}
              aria-label="Open command palette"
            >
              <svg style={{ width: 15, height: 15, flexShrink: 0 }} fill="none" viewBox="0 0 24 24" strokeWidth={1.7} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.2-5.2m0 0A7.5 7.5 0 105.2 5.2a7.5 7.5 0 0010.6 10.6z" />
              </svg>
              <span>Search everything...</span>
              <span style={{ marginLeft: 'auto', background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 4, padding: '2px 6px', fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--mono)' }}>
                Ctrl K
              </span>
            </button>

            <ThemeTransition />
            <NotificationCenter />
            {user && (
              <div className="flex h-8 w-8 items-center justify-center rounded-full" style={{ background: 'var(--surface-2)', border: '1px solid var(--border)', fontSize: 11, color: 'var(--accent)', fontWeight: 700, letterSpacing: '-0.02em' }}>
                {initials}
              </div>
            )}
            <Link
              to="/settings"
              style={{ width: 33, height: 33, display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: 9, cursor: 'pointer', color: 'var(--text2)', fontSize: 15, transition: 'all 0.14s ease', border: 'none', background: 'none' }}
              title="Settings"
            >
              <Settings style={{ width: 16, height: 16 }} />
            </Link>
            <button
              type="button"
              onClick={logout}
              style={{ width: 33, height: 33, display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: 9, cursor: 'pointer', color: 'var(--text2)', fontSize: 15, transition: 'all 0.14s ease', border: 'none', background: 'none' }}
              title="Sign out"
            >
              <svg style={{ width: 16, height: 16 }} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15m3 0l3-3m0 0l-3-3m3 3H9" />
              </svg>
            </button>
          </div>
        </header>

        <main id="main-content" tabIndex={-1} className="flex-1 overflow-y-auto p-4 lg:p-6 relative outline-none">
          <PageTransition>{children}</PageTransition>
        </main>
      </div>

      {/* Command palette — triggered via AppShell (Cmd+K) */}
      <CommandPalette isOpen={paletteOpen} onClose={closePalette} />
      {/* Keyboard shortcut overlay (triggered by ? key) */}
      <KeyboardShortcutOverlay />
      {/* PWA liquid glass install banner */}
      <PwaInstallBanner />
      {/* Guided product tour */}
      <GuidedTour />
      {/* Onboarding guided tour */}
      <OnboardingTour
        isActive={tour.isActive}
        currentStep={tour.currentStep}
        currentStepIndex={tour.currentStepIndex}
        totalSteps={tour.totalSteps}
        position={tour.position}
        isFirst={tour.isFirst}
        isLast={tour.isLast}
        onNext={tour.next}
        onPrev={tour.prev}
        onSkip={tour.skip}
      />
    </div>
  );
}
