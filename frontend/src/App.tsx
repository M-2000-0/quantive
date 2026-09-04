import { useEffect, useRef, useState } from 'react';
import {
  Bell,
  BriefcaseBusiness,
  Gauge,
  LayoutGrid,
  Plus,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  X,
} from 'lucide-react';
import {
  Link,
  Navigate,
  NavLink,
  Outlet,
  Route,
  Routes,
  useNavigate,
  useSearchParams,
} from 'react-router-dom';
import { useAuth } from './stores/auth';
import { useDemoMode } from './stores/demoMode';
import DemoModeBanner from './components/DemoModeBanner';
import DashboardPage from './pages/DashboardPage';
import SettingsPage from './pages/SettingsPage';
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import EventImpactDashboard from './pages/EventImpactDashboard';
import OptimizationsPage from './pages/OptimizationsPage';
import NewOptimizationPage from './pages/NewOptimizationPage';

function isAuthenticated(): boolean {
  try {
    return (
      localStorage.getItem('user') !== null || localStorage.getItem('demo_mode') === 'true'
    );
  } catch {
    return false;
  }
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  if (!isAuthenticated()) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function readStoredUser(): { name: string; role: string } | null {
  try {
    const raw = localStorage.getItem('user');
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { name?: string; role?: string; email?: string };
    return {
      name: parsed.name || parsed.email || 'User',
      role: parsed.role || 'Member',
    };
  } catch {
    return null;
  }
}

const NAV_ITEMS = [
  { label: 'Overview', to: '/dashboard', icon: LayoutGrid },
  { label: 'Portfolio', to: '/dashboard', icon: BriefcaseBusiness },
  { label: 'Insights', to: '/events', icon: Gauge },
  { label: 'Security', to: '/settings', icon: ShieldCheck },
  { label: 'Settings', to: '/settings', icon: Settings },
];

function AppLayout() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [search, setSearch] = useState(params.get('q') ?? '');
  const [notifOpen, setNotifOpen] = useState(false);
  const [actionsOpen, setActionsOpen] = useState(false);
  const actionsRef = useRef<HTMLDivElement | null>(null);
  const { user } = useAuth();
  const { isDemoMode } = useDemoMode();
  const [storedUser, setStoredUser] = useState(readStoredUser);

  useEffect(() => {
    setStoredUser(readStoredUser());
  }, [user, isDemoMode]);

  useEffect(() => {
    setSearch(params.get('q') ?? '');
  }, [params]);

  useEffect(() => {
    if (!actionsOpen) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setActionsOpen(false);
    }
    function onClick(e: MouseEvent) {
      if (actionsRef.current && !actionsRef.current.contains(e.target as Node)) {
        setActionsOpen(false);
      }
    }
    document.addEventListener('keydown', onKey);
    document.addEventListener('mousedown', onClick);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('mousedown', onClick);
    };
  }, [actionsOpen]);

  function submitSearch(e: React.FormEvent) {
    e.preventDefault();
    const next = new URLSearchParams(params);
    if (search.trim()) next.set('q', search.trim());
    else next.delete('q');
    setParams(next);
    navigate(`/dashboard?${next.toString()}`);
  }

  const displayName = user?.name || storedUser?.name || (isDemoMode ? 'Demo User' : 'Guest');
  const displayRole = user?.role || storedUser?.role || (isDemoMode ? 'admin' : 'Sign in to personalize');
  const initial = (displayName || 'G').charAt(0).toUpperCase();

  return (
    <div className="apple-shell">
      <DemoModeBanner />
      <aside className="sidebar">
        <Link to="/dashboard" className="brand-row" style={{ textDecoration: 'none', color: 'inherit' }}>
          <div className="brand-mark">Q</div>
          <div>
            <div className="brand-name">Quantive</div>
            <div className="brand-subtitle">workspace</div>
          </div>
        </Link>

        <nav className="nav" aria-label="Main navigation">
          {NAV_ITEMS.map(({ label, to, icon: Icon }) => (
            <NavLink
              key={label}
              to={to}
              className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
            >
              <Icon size={16} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="mini-card">
          <div className="mini-card-header">
            <span className="dot green" />
            <span>System healthy</span>
          </div>
          <p>Data loads live from your workspace.</p>
        </div>

        <div className="profile-box">
          <div className="profile-avatar" aria-hidden="true">{initial}</div>
          <div>
            <strong>{displayName}</strong>
            <span>{displayRole}</span>
          </div>
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <form className="search-box" role="search" onSubmit={submitSearch}>
            <Search size={16} aria-hidden="true" />
            <input
              type="search"
              aria-label="Search tasks"
              placeholder="Search tasks..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ background: 'transparent', border: 'none', outline: 'none', flex: 1, fontSize: 13 }}
            />
            {search && (
              <button
                type="button"
                aria-label="Clear search"
                onClick={() => {
                  setSearch('');
                  const next = new URLSearchParams(params);
                  next.delete('q');
                  setParams(next);
                  navigate('/dashboard');
                }}
                style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex' }}
              >
                <X size={14} />
              </button>
            )}
          </form>

          <div className="topbar-actions">
            <button
              className="icon-button"
              type="button"
              aria-label="Notifications"
              aria-expanded={notifOpen}
              onClick={() => {
                setNotifOpen((v) => !v);
                setActionsOpen(false);
              }}
            >
              <Bell size={16} />
            </button>
            <div style={{ position: 'relative' }} ref={actionsRef}>
              <button
                className="icon-button"
                type="button"
                aria-label="Quick actions"
                aria-expanded={actionsOpen}
                aria-haspopup="menu"
                onClick={() => {
                  setActionsOpen((v) => !v);
                  setNotifOpen(false);
                }}
              >
                <Sparkles size={16} />
              </button>
              {actionsOpen && (
                <div role="menu" aria-label="Quick actions" className="qa-menu">
                  <Link role="menuitem" to="/optimizations/new" onClick={() => setActionsOpen(false)}>
                    Run new optimization
                  </Link>
                  <Link role="menuitem" to="/optimizations" onClick={() => setActionsOpen(false)}>
                    View optimizations
                  </Link>
                  <Link role="menuitem" to="/settings" onClick={() => setActionsOpen(false)}>
                    Open settings
                  </Link>
                </div>
              )}
            </div>
            <button className="primary-button" type="button" onClick={() => navigate('/optimizations/new')}>
              <Plus size={16} />
              New report
            </button>
          </div>
        </header>

        {notifOpen && (
          <section aria-label="Notifications" className="panel" style={{ marginBottom: 16 }}>
            <div className="panel-header">
              <h2>Notifications</h2>
              <button type="button" className="soft-button" onClick={() => setNotifOpen(false)}>
                Close
              </button>
            </div>
            <p style={{ fontSize: 13, color: '#6b7280' }}>
              Task alerts and briefing updates appear in the Daily Briefing below.{' '}
              <a href="#briefing">Jump to briefing</a>
            </p>
          </section>
        )}

        <Outlet />
      </main>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
      </Route>
      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<SettingsPage />} />
      </Route>
      <Route
        path="/events"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<EventImpactDashboard />} />
      </Route>
      <Route
        path="/optimizations"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<OptimizationsPage />} />
        <Route path="new" element={<NewOptimizationPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
