import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useState } from 'react';
import { AuthProvider, useAuth } from './stores/auth';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import PortfolioListPage from './pages/PortfolioListPage';
import PortfolioDetailPage from './pages/PortfolioDetailPage';
import NewPortfolioPage from './pages/NewPortfolioPage';
import OptimizationWizardPage from './pages/OptimizationWizardPage';
import OptimizationDetailPage from './pages/OptimizationDetailPage';
import BenchmarkPage from './pages/BenchmarkPage';
import ReportsPage from './pages/ReportsPage';
import AuditPage from './pages/AuditPage';
import SystemStatusPage from './pages/SystemStatusPage';
import MarketDataPage from './pages/MarketDataPage';
import RiskDashboardPage from './pages/RiskDashboardPage';
import CommandPalette from './components/CommandPalette';
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);

  useKeyboardShortcuts(() => setCommandPaletteOpen(true));

  if (loading) return <div className="flex items-center justify-center min-h-screen text-slate-500">Loading...</div>;
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
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
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
          <Route path="/status" element={<ProtectedRoute><SystemStatusPage /></ProtectedRoute>} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
