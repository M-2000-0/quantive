import { Suspense, lazy, useEffect, useRef, useState } from 'react';
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
import ErrorBoundary from './components/ErrorBoundary';

const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const SettingsPage = lazy(() => import('./pages/SettingsPage'));
const LandingPage = lazy(() => import('./pages/LandingPage'));
const QuboPage = lazy(() => import('./pages/QuboPage'));
const TermsPage = lazy(() => import('./pages/TermsPage'));
const GovernmentPage = lazy(() => import('./pages/GovernmentPage'));
const BusinessPage = lazy(() => import('./pages/BusinessPage'));
const BankingPage = lazy(() => import('./pages/BankingPage'));
const BankingDashboardPage = lazy(() => import('./pages/BankingDashboardPage'));
const BankingTransfersPage = lazy(() => import('./pages/BankingTransfersPage'));
const BankingOnboardingPage = lazy(() => import('./pages/BankingOnboardingPage'));
const QuboWorkspacePage = lazy(() => import('./pages/QuboWorkspacePage'));
const LoginPage = lazy(() => import('./pages/LoginPage'));
const RegisterPage = lazy(() => import('./pages/RegisterPage'));
const EventImpactDashboard = lazy(() => import('./pages/EventImpactDashboard'));
const OptimizationsPage = lazy(() => import('./pages/OptimizationsPage'));
const NewOptimizationPage = lazy(() => import('./pages/NewOptimizationPage'));
const TransparencyIndexPage = lazy(() => import('./pages/TransparencyIndexPage'));
const OutcomePricingPage = lazy(() => import('./pages/OutcomePricingPage'));
const CaseStudyGeneratorPage = lazy(() => import('./pages/CaseStudyGeneratorPage'));
const PortfolioDetailPage = lazy(() => import('./pages/PortfolioDetailPage'));
const RiskDashboardPage = lazy(() => import('./pages/RiskDashboardPage'));
const SolverTournamentPage = lazy(() => import('./pages/SolverTournamentPage'));
const ProcurementDashboardPage = lazy(() => import('./pages/ProcurementDashboardPage'));
const GovernmentPilotPage = lazy(() => import('./pages/GovernmentPilotPage'));
const SovereignModePage = lazy(() => import('./pages/SovereignModePage'));
const AuditTrailPage = lazy(() => import('./pages/AuditTrailPage'));
const ApprovalWorkflowPage = lazy(() => import('./pages/ApprovalWorkflowPage'));
const AgentRunsPage = lazy(() => import('./pages/AgentRunsPage'));
const ModelValidationPage = lazy(() => import('./pages/ModelValidationPage'));
const InteroperabilityPage = lazy(() => import('./pages/InteroperabilityPage'));
const DisasterRecoveryPage = lazy(() => import('./pages/DisasterRecoveryPage'));
const SLAMonitoringPage = lazy(() => import('./pages/SLAMonitoringPage'));
const EscrowPage = lazy(() => import('./pages/EscrowPage'));
const PersonalLayout = lazy(() => import('./personal/PersonalLayout'));
const PersonalDashboard = lazy(() => import('./personal/pages/DashboardPage'));
const PersonalOnboarding = lazy(() => import('./personal/pages/OnboardingPage'));
const PersonalProfile = lazy(() => import('./personal/pages/ProfilePage'));
const PersonalOpportunities = lazy(() => import('./personal/pages/OpportunitiesPage'));
const PersonalDocuments = lazy(() => import('./personal/pages/DocumentsPage'));
const PersonalIntelligence = lazy(() => import('./personal/pages/IntelligencePage'));
const PersonalReports = lazy(() => import('./personal/pages/ReportsPage'));
const PersonalPricing = lazy(() => import('./personal/pages/PricingPage'));
const PersonalGov = lazy(() => import('./personal/pages/GovInsightsPage'));

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
  // ── MVP core loop: Overview -> Optimize -> Risk -> Solvers ──
  { label: 'Overview', to: '/dashboard', icon: LayoutGrid },
  { label: 'Optimizations', to: '/optimizations', icon: BriefcaseBusiness },
  { label: 'Insights', to: '/events', icon: Gauge },
  { label: 'Risk', to: '/risk-dashboard', icon: ShieldCheck },
  { label: 'Solvers', to: '/solver-tournament', icon: Sparkles },
  // ── Extended (defer for MVP, kept for deep-link compat) ──
  { label: 'Transparency Index', to: '/transparency-index', icon: LayoutGrid },
  { label: 'Pricing', to: '/pricing', icon: LayoutGrid },
  { label: 'Case Studies', to: '/case-studies', icon: LayoutGrid },
  { label: 'Pilots', to: '/pilots', icon: BriefcaseBusiness },
  { label: 'Procurement', to: '/procurement', icon: BriefcaseBusiness },
  { label: 'Sovereign Mode', to: '/sovereign-mode', icon: ShieldCheck },
  { label: 'Audit Trail', to: '/audit-trail', icon: ShieldCheck },
  { label: 'Approvals', to: '/approvals', icon: ShieldCheck },
  { label: 'Agent Runs', to: '/agent-runs', icon: Sparkles },
  { label: 'Model Validation', to: '/model-validation', icon: ShieldCheck },
  { label: 'Interoperability', to: '/interoperability', icon: BriefcaseBusiness },
  { label: 'DR', to: '/disaster-recovery', icon: ShieldCheck },
  { label: 'SLA', to: '/sla', icon: ShieldCheck },
  { label: 'Escrow', to: '/escrow', icon: BriefcaseBusiness },
  { label: 'Security', to: '/settings', icon: ShieldCheck },
  { label: 'Settings', to: '/settings', icon: Settings },
  { label: 'Personal ★', to: '/personal', icon: Sparkles },
  { label: 'Banking', to: '/banking/app', icon: BriefcaseBusiness },
  { label: 'Qubo Tax', to: '/qubo/workspace', icon: Sparkles },
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
      <a href="#main-content" className="skip-to-content" style={{
        position: 'absolute', left: '-9999px', top: 'auto', width: 1, height: 1,
        overflow: 'hidden', zIndex: 9999,
      }}>
        Skip to main content
      </a>
      <DemoModeBanner />
      <aside className="sidebar">
        <Link to="/dashboard" className="brand-row" style={{ textDecoration: 'none', color: 'inherit' }}>
          <img className="brand-mark" src="/quantive-logo.png" alt="Quantive" />
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

        <main id="main-content" tabIndex={-1} className="main-panel">
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

function PageWrapper({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary>
      {children}
    </ErrorBoundary>
  );
}

export default function App() {
  return (
    <Suspense fallback={
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', color: '#6b7280' }}>
        Loading...
      </div>
    }>
    <Routes>
      <Route path="/" element={<PageWrapper><LandingPage /></PageWrapper>} />
      <Route path="/qubo" element={<PageWrapper><QuboPage /></PageWrapper>} />
      <Route
        path="/qubo/workspace"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<PageWrapper><QuboWorkspacePage /></PageWrapper>} />
      </Route>
      <Route path="/terms" element={<PageWrapper><TermsPage /></PageWrapper>} />
      <Route path="/government" element={<PageWrapper><GovernmentPage /></PageWrapper>} />
      <Route path="/business" element={<PageWrapper><BusinessPage /></PageWrapper>} />
      <Route path="/banking" element={<PageWrapper><BankingPage /></PageWrapper>} />
      <Route
        path="/banking/app"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<PageWrapper><BankingDashboardPage /></PageWrapper>} />
      </Route>
      <Route
        path="/banking/transfers"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<PageWrapper><BankingTransfersPage /></PageWrapper>} />
      </Route>
      <Route
        path="/banking/onboarding"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<PageWrapper><BankingOnboardingPage /></PageWrapper>} />
      </Route>
      <Route path="/login" element={<PageWrapper><LoginPage /></PageWrapper>} />
      <Route path="/register" element={<PageWrapper><RegisterPage /></PageWrapper>} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<PageWrapper><DashboardPage /></PageWrapper>} />
        <Route path="portfolios/:id" element={<PageWrapper><PortfolioDetailPage /></PageWrapper>} />
      </Route>
      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<PageWrapper><SettingsPage /></PageWrapper>} />
      </Route>
      <Route
        path="/events"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<PageWrapper><EventImpactDashboard /></PageWrapper>} />
      </Route>
      <Route
        path="/risk-dashboard"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<PageWrapper><RiskDashboardPage /></PageWrapper>} />
      </Route>
      <Route
        path="/solver-tournament"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<PageWrapper><SolverTournamentPage /></PageWrapper>} />
      </Route>
      <Route
        path="/optimizations"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<PageWrapper><OptimizationsPage /></PageWrapper>} />
        <Route path="new" element={<PageWrapper><NewOptimizationPage /></PageWrapper>} />
      </Route>
      <Route
        path="/transparency-index"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<PageWrapper><TransparencyIndexPage /></PageWrapper>} />
      </Route>
      <Route
        path="/pricing"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<PageWrapper><OutcomePricingPage /></PageWrapper>} />
      </Route>
      <Route
        path="/case-studies"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<PageWrapper><CaseStudyGeneratorPage /></PageWrapper>} />
      </Route>
      <Route
        path="/procurement"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<PageWrapper><ProcurementDashboardPage /></PageWrapper>} />
      </Route>
      <Route
        path="/pilots"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<PageWrapper><GovernmentPilotPage /></PageWrapper>} />
      </Route>
      <Route
        path="/sovereign-mode"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<PageWrapper><SovereignModePage /></PageWrapper>} />
      </Route>
      <Route
        path="/audit-trail"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<PageWrapper><AuditTrailPage /></PageWrapper>} />
      </Route>
      <Route
        path="/approvals"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<PageWrapper><ApprovalWorkflowPage /></PageWrapper>} />
      </Route>
      <Route
        path="/agent-runs"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<PageWrapper><AgentRunsPage /></PageWrapper>} />
      </Route>
      <Route
        path="/model-validation"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<PageWrapper><ModelValidationPage /></PageWrapper>} />
      </Route>
      <Route
        path="/interoperability"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<PageWrapper><InteroperabilityPage /></PageWrapper>} />
      </Route>
      <Route
        path="/disaster-recovery"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<PageWrapper><DisasterRecoveryPage /></PageWrapper>} />
      </Route>
      <Route
        path="/sla"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<PageWrapper><SLAMonitoringPage /></PageWrapper>} />
      </Route>
      <Route
        path="/escrow"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<PageWrapper><EscrowPage /></PageWrapper>} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
      <Route
        path="/personal"
        element={
          <ProtectedRoute>
            <PageWrapper><PersonalLayout /></PageWrapper>
          </ProtectedRoute>
        }
      >
        <Route index element={<PageWrapper><PersonalDashboard /></PageWrapper>} />
        <Route path="onboarding" element={<PageWrapper><PersonalOnboarding /></PageWrapper>} />
        <Route path="profile" element={<PageWrapper><PersonalProfile /></PageWrapper>} />
        <Route path="opportunities" element={<PageWrapper><PersonalOpportunities /></PageWrapper>} />
        <Route path="documents" element={<PageWrapper><PersonalDocuments /></PageWrapper>} />
        <Route path="intelligence" element={<PageWrapper><PersonalIntelligence /></PageWrapper>} />
        <Route path="gov" element={<PageWrapper><PersonalGov /></PageWrapper>} />
        <Route path="reports" element={<PageWrapper><PersonalReports /></PageWrapper>} />
        <Route path="pricing" element={<PageWrapper><PersonalPricing /></PageWrapper>} />
      </Route>
    </Routes>
    </Suspense>
  );
}
