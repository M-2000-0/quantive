import { Routes, Route, Navigate } from "react-router-dom";
import { api } from "./api/client";
import { Layout } from "./components/Layout";
import { LoginPage } from "./pages/Login";
import { DashboardPage } from "./pages/Dashboard";
import { TransactionsPage } from "./pages/Transactions";
import { AlertsPage } from "./pages/Alerts";
import { CasesPage } from "./pages/Cases";
import { SettingsPage } from "./pages/Settings";
import { AutomationsPage } from "./pages/Automations";
import { BlockchainPage } from "./pages/Blockchain";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  if (!api.isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={<ProtectedRoute><Layout /></ProtectedRoute>}
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="transactions" element={<TransactionsPage />} />
        <Route path="alerts" element={<AlertsPage />} />
        <Route path="cases" element={<CasesPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="automations" element={<AutomationsPage />} />
        <Route path="blockchain" element={<BlockchainPage />} />
      </Route>
    </Routes>
  );
}
