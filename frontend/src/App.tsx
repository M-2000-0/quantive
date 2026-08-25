import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useState, Suspense, lazy } from 'react';
import ErrorBoundary from './components/ErrorBoundary';
import { I18nProvider } from './i18n';
import { ThemeProvider } from './stores/theme';
import { ToastProvider } from './stores/toast';
import { AuthProvider, useAuth } from './stores/auth';
import CommandPalette from './components/CommandPalette';
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts';

// ── Code-split pages (each becomes its own chunk) ─────────────────────
const LoginPage = lazy(() => import('./pages/LoginPage'));
const RegisterPage = lazy(() => import('./pages/RegisterPage'));
const ForgotPasswordPage = lazy(() => import('./pages/ForgotPasswordPage'));
const ResetPasswordPage = lazy(() => import('./pages/ResetPasswordPage'));
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const PortfolioListPage = lazy(() => import('./pages/PortfolioListPage'));
const PortfolioDetailPage = lazy(() => import('./pages/PortfolioDetailPage'));
const NewPortfolioPage = lazy(() => import('./pages/NewPortfolioPage'));
const OptimizationWizardPage = lazy(() => import('./pages/OptimizationWizardPage'));
const OptimizationDetailPage = lazy(() => import('./pages/OptimizationDetailPage'));
const BenchmarkPage = lazy(() => import('./pages/BenchmarkPage'));
const ReportsPage = lazy(() => import('./pages/ReportsPage'));
const AuditPage = lazy(() => import('./pages/AuditPage'));
const SystemStatusPage = lazy(() => import('./pages/SystemStatusPage'));
const MarketDataPage = lazy(() => import('./pages/MarketDataPage'));
const RiskDashboardPage = lazy(() => import('./pages/RiskDashboardPage'));
const SecurityDashboardPage = lazy(() => import('./pages/SecurityDashboardPage'));
const WhatIfPage = lazy(() => import('./pages/WhatIfPage'));
const AdvisorPage = lazy(() => import('./pages/AdvisorPage'));
const PeerComparisonPage = lazy(() => import('./pages/PeerComparisonPage'));
const CompliancePage = lazy(() => import('./pages/CompliancePage'));
const ExplainabilityPage = lazy(() => import('./pages/ExplainabilityPage'));
const RiskIntelPage = lazy(() => import('./pages/RiskIntelPage'));
const MaturityLadderPage = lazy(() => import('./pages/MaturityLadderPage'));
const ESGPage = lazy(() => import('./pages/ESGPage'));
const RatingSimulatorPage = lazy(() => import('./pages/RatingSimulatorPage'));
const SettingsPage = lazy(() => import('./pages/SettingsPage'));

// ── Glass loading skeleton ─────────────────────────────────────────────
function PageLoader() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="glass p-8 text-center animate-glass-in">
        <div className="flex justify-center mb-4">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-500 animate-pulse" />
        </div>
        <div className="skeleton h-4 w-32 mx-auto mb-2" />
        <div className="skeleton h-3 w-24 mx-auto" />
      </div>
    </div>
  );
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);

  useKeyboardShortcuts(() => setCommandPaletteOpen(true));

  if (loading) return <PageLoader />;
  if (!user) return <Navigate to="/login" />;
  return (
    <>
      {children}
      <CommandPalette isOpen={commandPaletteOpen} onClose={() => setCommandPaletteOpen(false)} />
    </>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <I18nProvider>
          <ToastProvider>
            <AuthProvider>
              <BrowserRouter>
                <Suspense fallback={<PageLoader />}>
                  <Routes>
                    <Route path="/login" element={<LoginPage />} />
                    <Route path="/register" element={<RegisterPage />} />
                    <Route path="/forgot-password" element={<ForgotPasswordPage />} />
                    <Route path="/reset-password" element={<ResetPasswordPage />} />
                    <Route path="/" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
                    <Route path="/portfolios" element={<ProtectedRoute><PortfolioListPage /></ProtectedRoute>} />
                    <Route path="/portfolios/new" element={<ProtectedRoute><NewPortfolioPage /></ProtectedRoute>} />
                    <Route path="/portfolios/:id" element={<ProtectedRoute><PortfolioDetailPage /></ProtectedRoute>} />
                    <Route path="/optimizations/new" element={<ProtectedRoute><OptimizationWizardPage /></ProtectedRoute>} />
                    <Route path="/optimizations/:id" element={<ProtectedRoute><OptimizationDetailPage /></ProtectedRoute>} />
                    <Route path="/benchmarks/:id" element={<ProtectedRoute><BenchmarkPage /></ProtectedRoute>} />
                    <Route path="/benchmarks" element={<ProtectedRoute><BenchmarkPage /></ProtectedRoute>} />
                    <Route path="/reports" element={<ProtectedRoute><ReportsPage /></ProtectedRoute>} />
                    <Route path="/audit" element={<ProtectedRoute><AuditPage /></ProtectedRoute>} />
                    <Route path="/market" element={<ProtectedRoute><MarketDataPage /></ProtectedRoute>} />
                    <Route path="/risk" element={<ProtectedRoute><RiskDashboardPage /></ProtectedRoute>} />
                    <Route path="/whatif" element={<ProtectedRoute><WhatIfPage /></ProtectedRoute>} />
                    <Route path="/advisor" element={<ProtectedRoute><AdvisorPage /></ProtectedRoute>} />
                    <Route path="/peers" element={<ProtectedRoute><PeerComparisonPage /></ProtectedRoute>} />
                    <Route path="/compliance" element={<ProtectedRoute><CompliancePage /></ProtectedRoute>} />
                    <Route path="/explain" element={<ProtectedRoute><ExplainabilityPage /></ProtectedRoute>} />
                    <Route path="/risk-intel" element={<ProtectedRoute><RiskIntelPage /></ProtectedRoute>} />
                    <Route path="/maturity" element={<ProtectedRoute><MaturityLadderPage /></ProtectedRoute>} />
                    <Route path="/esg" element={<ProtectedRoute><ESGPage /></ProtectedRoute>} />
                    <Route path="/ratings" element={<ProtectedRoute><RatingSimulatorPage /></ProtectedRoute>} />
                    <Route path="/security" element={<ProtectedRoute><SecurityDashboardPage /></ProtectedRoute>} />
                    <Route path="/status" element={<ProtectedRoute><SystemStatusPage /></ProtectedRoute>} />
                    <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
                    <Route path="*" element={<Navigate to="/" />} />
                  </Routes>
                </Suspense>
              </BrowserRouter>
            </AuthProvider>
          </ToastProvider>
        </I18nProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}
