import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Suspense, lazy, useEffect, useState } from 'react';
import ErrorBoundary from './components/ErrorBoundary';
import PageTransition from './components/PageTransition';
import FeedbackWidget from './components/FeedbackWidget';
import { I18nProvider } from './i18n';
import { ThemeProvider } from './stores/theme';
import { ToastProvider } from './stores/toast';
import { AuthProvider, useAuth } from './stores/auth';
import { DemoModeProvider, useDemoMode } from './stores/demoMode';
import { PortfolioProvider } from './stores/portfolio';
import DemoModeBanner from './components/DemoModeBanner';
import DisclaimerBanner from './components/DisclaimerBanner';
import { initSentry, captureError, setUser, clearUser } from './lib/sentry';
import { initAnalytics, identify, resetIdentity, events } from './lib/analytics';
import { GlassRefractionEngine, LiquidGlassFilter } from './components/glass';
import LiquidScene from './components/glass/LiquidScene';

// Initialize error monitoring & analytics at module load time
initSentry();
initAnalytics();

// ── Code-split pages (each becomes its own chunk) ─────────────────────
const LandingPage = lazy(() => import('./pages/LandingPage'));
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
const AdminDashboardPage = lazy(() => import('./pages/AdminDashboardPage'));
const BillingPage = lazy(() => import('./pages/BillingPage'));
const LegalPage = lazy(() => import('./pages/LegalPage'));
const PurchaseTrackerPage = lazy(() => import('./pages/PurchaseTrackerPage'));
const OpportunityFeedPage = lazy(() => import('./pages/OpportunityFeedPage'));
const EventImpactDashboard = lazy(() => import('./pages/EventImpactDashboard'));
const NotificationPreferencesPage = lazy(() => import('./pages/NotificationPreferencesPage'));
const AdaptiveDashboardPage = lazy(() => import('./pages/AdaptiveDashboardPage'));
const ExecutionDashboardPage = lazy(() => import('./pages/ExecutionDashboardPage'));
const DecisionCopilotPage = lazy(() => import('./pages/DecisionCopilotPage'));
const ExplainabilityEnginePage = lazy(() => import('./pages/ExplainabilityEnginePage'));
const DigitalTwinPage = lazy(() => import('./pages/DigitalTwinPage'));
const ConstraintBuilderPage = lazy(() => import('./pages/ConstraintBuilderPage'));
const SolverTournamentPage = lazy(() => import('./pages/SolverTournamentPage'));
const KnowledgeGraphPage = lazy(() => import('./pages/KnowledgeGraphPage'));
const ApprovalWorkflowPage = lazy(() => import('./pages/ApprovalWorkflowPage'));
const PolicyImpactPage = lazy(() => import('./pages/PolicyImpactPage'));
const SovereignDSAPage = lazy(() => import('./pages/SovereignDSAPage'));
const CrisisCommandPage = lazy(() => import('./pages/CrisisCommandPage'));
const GeopoliticalPage = lazy(() => import('./pages/GeopoliticalPage'));
const NationalDigitalTwinPage = lazy(() => import('./pages/NationalDigitalTwinPage'));
const SovereignAdvisorPage = lazy(() => import('./pages/SovereignAdvisorPage'));
const EarlyWarningPage = lazy(() => import('./pages/EarlyWarningPage'));
const IssuancePlannerPage = lazy(() => import('./pages/IssuancePlannerPage'));
const CrossCountryPage = lazy(() => import('./pages/CrossCountryPage'));
const ROIEnginePage = lazy(() => import('./pages/ROIEnginePage'));
const RatingAgencyPage = lazy(() => import('./pages/RatingAgencyPage'));
const SovereignHealthPage = lazy(() => import('./pages/SovereignHealthPage'));
const MinisterDashboardPage = lazy(() => import('./pages/MinisterDashboardPage'));
const FiscalImpactPage = lazy(() => import('./pages/FiscalImpactPage'));
const ImmutableAuditPage = lazy(() => import('./pages/ImmutableAuditPage'));
const MultiEyesPage = lazy(() => import('./pages/MultiEyesPage'));
const FraudDetectionPage = lazy(() => import('./pages/FraudDetectionPage'));
const InsiderRiskPage = lazy(() => import('./pages/InsiderRiskPage'));
const DecisionVaultPage = lazy(() => import('./pages/DecisionVaultPage'));
const DLPPage = lazy(() => import('./pages/DLPPage'));
const AirGappedPage = lazy(() => import('./pages/AirGappedPage'));
const CompliancePageDashboard = lazy(() => import('./pages/CompliancePageDashboard'));
const DisasterRecoveryPage = lazy(() => import('./pages/DisasterRecoveryPage'));
const DataResidencyPage = lazy(() => import('./pages/DataResidencyPage'));
const VendorRiskPage = lazy(() => import('./pages/VendorRiskPage'));
const SecurityAssessmentPage = lazy(() => import('./pages/SecurityAssessmentPage'));
const LegalEvidencePage = lazy(() => import('./pages/LegalEvidencePage'));
const SystemAvailabilityPage = lazy(() => import('./pages/SystemAvailabilityPage'));
const OfflineModePage = lazy(() => import('./pages/OfflineModePage'));
const SourceInspectionPage = lazy(() => import('./pages/SourceInspectionPage'));
const AIGovernancePage = lazy(() => import('./pages/AIGovernancePage'));
const SavingsTracePage = lazy(() => import('./pages/SavingsTracePage'));
const TrainingAcademyPage = lazy(() => import('./pages/TrainingAcademyPage'));
const ModelValidationPage = lazy(() => import('./pages/ModelValidationPage'));
const RedTeamPage = lazy(() => import('./pages/RedTeamPage'));
const InstitutionalMemoryPage = lazy(() => import('./pages/InstitutionalMemoryPage'));
const PoliticalFeasibilityPage = lazy(() => import('./pages/PoliticalFeasibilityPage'));
const CorruptionOpportunityPage = lazy(() => import('./pages/CorruptionOpportunityPage'));
const NationalResiliencePage = lazy(() => import('./pages/NationalResiliencePage'));
const MinisterHandoverPage = lazy(() => import('./pages/MinisterHandoverPage'));
const BlackSwanPage = lazy(() => import('./pages/BlackSwanPage'));
const DataSourceTrustPage = lazy(() => import('./pages/DataSourceTrustPage'));
const OnboardingPage = lazy(() => import('./pages/OnboardingPage'));
const GovernmentPricingPage = lazy(() => import('./pages/GovernmentPricingPage'));
const KnowledgeNetworkPage = lazy(() => import('./pages/KnowledgeNetworkPage'));
const RiskRadarPage = lazy(() => import('./pages/RiskRadarPage'));
// DigitalTwinPage already imported above
const DecisionArchivePage = lazy(() => import('./pages/DecisionArchivePage'));
const WarRoomPage = lazy(() => import('./pages/WarRoomPage'));
const AIChallengerPage = lazy(() => import('./pages/AIChallengerPage'));
const InstitutionalIQPage = lazy(() => import('./pages/InstitutionalIQPage'));
// EarlyWarningPage already imported above
const AntiCorruptionPage = lazy(() => import('./pages/AntiCorruptionPage'));
const FlightRecorderPage = lazy(() => import('./pages/DecisionHistoryPage'));
const TrustDashboardPage = lazy(() => import('./pages/TrustDashboardPage'));
const MaturityAssessmentPage = lazy(() => import('./pages/MaturityAssessmentPage'));
const AssumptionTrackerPage = lazy(() => import('./pages/AssumptionTrackerPage'));
const ExcelImportWizardPage = lazy(() => import('./pages/ExcelImportWizardPage'));
const StockMonitorPage = lazy(() => import('./pages/StockMonitorPage'));
const SOCDashboardPage = lazy(() => import('./pages/SOCDashboardPage'));
const QuantumReadinessPage = lazy(() => import('./pages/QuantumReadinessPage'));
const OpenQASM3Page = lazy(() => import('./pages/OpenQASM3Page'));
const ZKPolicyPage = lazy(() => import('./pages/ZKPolicyPage'));
const QAEPage = lazy(() => import('./pages/QAEPage'));
const ParetoFrontierPage = lazy(() => import('./pages/ParetoFrontierPage'));
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
  const { isDemoMode } = useDemoMode();
  const [disclaimerAccepted, setDisclaimerAccepted] = useState(() => {
    if (!user) return true; // not logged in, skip
    const key = `quantive_disclaimer_accepted_${user.id || user.email}`;
    const versionKey = `${key}_version`;
    return localStorage.getItem(key) === 'true' && localStorage.getItem(versionKey) === '1.0.0';
  });
  const [showDisclaimer, setShowDisclaimer] = useState(!disclaimerAccepted);

  const handleDisclaimerAccept = () => {
    setDisclaimerAccepted(true);
    setShowDisclaimer(false);
  };

  if (loading) return <PageLoader />;
  // In demo mode, skip auth check
  if (!user && !isDemoMode) return <Navigate to="/login" />;
  return (
    <>
      {showDisclaimer && !isDemoMode && <DisclaimerBanner onAccept={handleDisclaimerAccept} />}
      {children}
    </>
  );
}

/** Syncs auth state to Sentry and analytics for error context. */
function AuthTracker() {
  const { user } = useAuth();
  useEffect(() => {
    if (user) {
      setUser({ id: user.id, email: user.email, role: user.role });
      identify(user.id, { role: user.role, org_id: user.org_id });
    } else {
      clearUser();
      resetIdentity();
    }
  }, [user]);
  return null;
}

export default function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <I18nProvider>
          <ToastProvider>
            <AuthProvider>
              <DemoModeProvider>
              <PortfolioProvider>
              <BrowserRouter>
                {/* Skip navigation link for screen readers */}
                <a href="#main-content" className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-[10000] focus:px-4 focus:py-2 focus:bg-blue-600 focus:text-white focus:rounded-xl focus:shadow-lg focus:outline-none focus:ring-2 focus:ring-blue-400">
                  Skip to main content
                </a>
              <GlassRefractionEngine />
              <LiquidGlassFilter />
              <LiquidScene>
              <FeedbackWidget />
              <DemoModeBanner />
              <AuthTracker />
                <Suspense fallback={<PageLoader />}>
                  <Routes>
                    <Route path="/" element={<LandingPage />} />
                    <Route path="/onboarding" element={<ProtectedRoute><OnboardingPage /></ProtectedRoute>} />
                    <Route path="/pricing" element={<GovernmentPricingPage />} />
                    <Route path="/login" element={<LoginPage />} />
                    <Route path="/register" element={<RegisterPage />} />
                    <Route path="/forgot-password" element={<ForgotPasswordPage />} />
                    <Route path="/reset-password" element={<ResetPasswordPage />} />
                    <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
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
                    <Route path="/purchases" element={<ProtectedRoute><PurchaseTrackerPage /></ProtectedRoute>} />
                    <Route path="/opportunities" element={<ProtectedRoute><OpportunityFeedPage /></ProtectedRoute>} />
                    <Route path="/events" element={<ProtectedRoute><EventImpactDashboard /></ProtectedRoute>} />
                    <Route path="/adaptive" element={<ProtectedRoute><AdaptiveDashboardPage /></ProtectedRoute>} />
                    <Route path="/executions" element={<ProtectedRoute><ExecutionDashboardPage /></ProtectedRoute>} />
                    <Route path="/copilot" element={<ProtectedRoute><DecisionCopilotPage /></ProtectedRoute>} />
                    <Route path="/explain-engine" element={<ProtectedRoute><ExplainabilityEnginePage /></ProtectedRoute>} />
                    <Route path="/digital-twin" element={<ProtectedRoute><DigitalTwinPage /></ProtectedRoute>} />
                    <Route path="/constraint-builder" element={<ProtectedRoute><ConstraintBuilderPage /></ProtectedRoute>} />
                    <Route path="/solver-tournament" element={<ProtectedRoute><SolverTournamentPage /></ProtectedRoute>} />
                    <Route path="/knowledge-graph" element={<ProtectedRoute><KnowledgeGraphPage /></ProtectedRoute>} />
                    <Route path="/approvals" element={<ProtectedRoute><ApprovalWorkflowPage /></ProtectedRoute>} />
                    <Route path="/policy-impact" element={<ProtectedRoute><PolicyImpactPage /></ProtectedRoute>} />
                    <Route path="/sovereign-dsa" element={<ProtectedRoute><SovereignDSAPage /></ProtectedRoute>} />
                    <Route path="/crisis" element={<ProtectedRoute><CrisisCommandPage /></ProtectedRoute>} />
                    <Route path="/geopolitical" element={<ProtectedRoute><GeopoliticalPage /></ProtectedRoute>} />
                    <Route path="/national-twin" element={<ProtectedRoute><NationalDigitalTwinPage /></ProtectedRoute>} />
                    <Route path="/sovereign-advisor" element={<ProtectedRoute><SovereignAdvisorPage /></ProtectedRoute>} />
                    <Route path="/early-warning" element={<ProtectedRoute><EarlyWarningPage /></ProtectedRoute>} />
                    <Route path="/issuance-planner" element={<ProtectedRoute><IssuancePlannerPage /></ProtectedRoute>} />
                    <Route path="/cross-country" element={<ProtectedRoute><CrossCountryPage /></ProtectedRoute>} />
                    <Route path="/roi-engine" element={<ProtectedRoute><ROIEnginePage /></ProtectedRoute>} />
                    <Route path="/rating-agency" element={<ProtectedRoute><RatingAgencyPage /></ProtectedRoute>} />
                    <Route path="/sovereign-health" element={<ProtectedRoute><SovereignHealthPage /></ProtectedRoute>} />
                    <Route path="/minister" element={<ProtectedRoute><MinisterDashboardPage /></ProtectedRoute>} />
                    <Route path="/fiscal-impact" element={<ProtectedRoute><FiscalImpactPage /></ProtectedRoute>} />
                    <Route path="/immutable-audit" element={<ProtectedRoute><ImmutableAuditPage /></ProtectedRoute>} />
                    <Route path="/multi-eyes" element={<ProtectedRoute><MultiEyesPage /></ProtectedRoute>} />
                    <Route path="/fraud-detection" element={<ProtectedRoute><FraudDetectionPage /></ProtectedRoute>} />
                    <Route path="/insider-risk" element={<ProtectedRoute><InsiderRiskPage /></ProtectedRoute>} />
                    <Route path="/decision-vault" element={<ProtectedRoute><DecisionVaultPage /></ProtectedRoute>} />
                    <Route path="/dlp" element={<ProtectedRoute><DLPPage /></ProtectedRoute>} />
                    <Route path="/airgapped" element={<ProtectedRoute><AirGappedPage /></ProtectedRoute>} />
                    <Route path="/compliance-dash" element={<ProtectedRoute><CompliancePageDashboard /></ProtectedRoute>} />
                    <Route path="/disaster-recovery" element={<ProtectedRoute><DisasterRecoveryPage /></ProtectedRoute>} />
                    <Route path="/data-residency" element={<ProtectedRoute><DataResidencyPage /></ProtectedRoute>} />
                    <Route path="/vendor-risk" element={<ProtectedRoute><VendorRiskPage /></ProtectedRoute>} />
                    <Route path="/security-assessment" element={<ProtectedRoute><SecurityAssessmentPage /></ProtectedRoute>} />
                    <Route path="/legal-evidence" element={<ProtectedRoute><LegalEvidencePage /></ProtectedRoute>} />
                    <Route path="/system-availability" element={<ProtectedRoute><SystemAvailabilityPage /></ProtectedRoute>} />
                    <Route path="/offline-mode" element={<ProtectedRoute><OfflineModePage /></ProtectedRoute>} />
                    <Route path="/source-inspection" element={<ProtectedRoute><SourceInspectionPage /></ProtectedRoute>} />
                    <Route path="/ai-governance" element={<ProtectedRoute><AIGovernancePage /></ProtectedRoute>} />
                    <Route path="/savings-trace" element={<ProtectedRoute><SavingsTracePage /></ProtectedRoute>} />
                    <Route path="/training" element={<ProtectedRoute><TrainingAcademyPage /></ProtectedRoute>} />
                    <Route path="/model-validation" element={<ProtectedRoute><ModelValidationPage /></ProtectedRoute>} />
                    <Route path="/red-team" element={<ProtectedRoute><RedTeamPage /></ProtectedRoute>} />
                    <Route path="/institutional-memory" element={<ProtectedRoute><InstitutionalMemoryPage /></ProtectedRoute>} />
                    <Route path="/political-feasibility" element={<ProtectedRoute><PoliticalFeasibilityPage /></ProtectedRoute>} />
                    <Route path="/corruption-opportunity" element={<ProtectedRoute><CorruptionOpportunityPage /></ProtectedRoute>} />
                    <Route path="/national-resilience" element={<ProtectedRoute><NationalResiliencePage /></ProtectedRoute>} />
                    <Route path="/minister-handover" element={<ProtectedRoute><MinisterHandoverPage /></ProtectedRoute>} />
                    <Route path="/black-swan" element={<ProtectedRoute><BlackSwanPage /></ProtectedRoute>} />
                    <Route path="/data-source-trust" element={<ProtectedRoute><DataSourceTrustPage /></ProtectedRoute>} />
                    <Route path="/knowledge-network" element={<ProtectedRoute><KnowledgeNetworkPage /></ProtectedRoute>} />
                    <Route path="/risk-radar" element={<ProtectedRoute><RiskRadarPage /></ProtectedRoute>} />
                    <Route path="/decision-archive" element={<ProtectedRoute><DecisionArchivePage /></ProtectedRoute>} />
                    <Route path="/war-room" element={<ProtectedRoute><WarRoomPage /></ProtectedRoute>} />
                    <Route path="/ai-challenger" element={<ProtectedRoute><AIChallengerPage /></ProtectedRoute>} />
                    <Route path="/institutional-iq" element={<ProtectedRoute><InstitutionalIQPage /></ProtectedRoute>} />
                    <Route path="/anti-corruption" element={<ProtectedRoute><AntiCorruptionPage /></ProtectedRoute>} />
                    <Route path="/flight-recorder" element={<ProtectedRoute><FlightRecorderPage /></ProtectedRoute>} />
                    <Route path="/trust-dashboard" element={<ProtectedRoute><TrustDashboardPage /></ProtectedRoute>} />
                    <Route path="/maturity-assessment" element={<ProtectedRoute><MaturityAssessmentPage /></ProtectedRoute>} />
                    <Route path="/assumption-tracker" element={<ProtectedRoute><AssumptionTrackerPage /></ProtectedRoute>} />
                    <Route path="/excel-import" element={<ProtectedRoute><ExcelImportWizardPage /></ProtectedRoute>} />
                    <Route path="/stock-monitor" element={<ProtectedRoute><StockMonitorPage /></ProtectedRoute>} />
                    <Route path="/soc-dashboard" element={<ProtectedRoute><SOCDashboardPage /></ProtectedRoute>} />
                    <Route path="/quantum-readiness" element={<ProtectedRoute><QuantumReadinessPage /></ProtectedRoute>} />
                    <Route path="/openqasm3" element={<ProtectedRoute><OpenQASM3Page /></ProtectedRoute>} />
                    <Route path="/zk-policy" element={<ProtectedRoute><ZKPolicyPage /></ProtectedRoute>} />
                    <Route path="/qae" element={<ProtectedRoute><QAEPage /></ProtectedRoute>} />
                    <Route path="/pareto" element={<ProtectedRoute><ParetoFrontierPage /></ProtectedRoute>} />
                    <Route path="/notifications" element={<ProtectedRoute><NotificationPreferencesPage /></ProtectedRoute>} />
                    <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
                    <Route path="/admin" element={<ProtectedRoute><AdminDashboardPage /></ProtectedRoute>} />
                    <Route path="/billing" element={<ProtectedRoute><BillingPage /></ProtectedRoute>} />
                    <Route path="/legal/:page" element={<LegalPage />} />
                    <Route path="*" element={<Navigate to="/" />} />
                  </Routes>
                </Suspense>
              </LiquidScene>
              </BrowserRouter>
              </PortfolioProvider>
              </DemoModeProvider>
            </AuthProvider>
          </ToastProvider>
        </I18nProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}
