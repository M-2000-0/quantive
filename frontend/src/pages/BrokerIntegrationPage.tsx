import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Users, FileCheck, AlertTriangle, Shield, Building2, ClipboardCheck,
  BarChart3, Clock, CheckCircle, XCircle, ChevronRight, Search,
  Upload, Eye, Plus, Filter, ArrowUpRight, ArrowDownRight, Activity,
  Wallet, FileText, TrendingUp, AlertCircle, Settings, RefreshCw
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface KYCRecord {
  id: string;
  client_name: string;
  client_type: string;
  jurisdiction: string;
  kyc_status: string;
  risk_level: string;
  risk_score: number;
  cip_verified: boolean;
  cdd_status: string;
  edd_required: boolean;
  next_review_date: string | null;
  created_at: string;
}

interface OnboardingRecord {
  id: string;
  client_name: string;
  client_type: string;
  jurisdiction: string;
  stage: string;
  documents_submitted: string[];
  documents_required: string[];
  account_type: string | null;
  target_completion: string | null;
  created_at: string;
}

interface TransactionAlert {
  id: string;
  transaction_type: string;
  instrument_identifier: string;
  total_value: number;
  currency: string;
  alert_severity: string | null;
  alert_reasons: string[];
  sar_filed: boolean;
  review_status: string;
  created_at: string;
}

interface Registration {
  id: string;
  registration_type: string;
  regulator: string;
  crd_number: string | null;
  status: string;
  filing_date: string | null;
  approval_date: string | null;
}

interface DashboardData {
  summary: {
    kyc_total: number;
    kyc_approved: number;
    kyc_pending: number;
    onboarding_active: number;
    onboarding_complete: number;
    transactions_total: number;
    transactions_suspicious: number;
    sar_filed: number;
    ctr_required: number;
    registrations: number;
  };
  risk_distribution: Record<string, number>;
  registration_status: Record<string, number>;
  compliance_score: number;
}

interface FeeQuote {
  trade_value: number;
  commission: number;
  commission_bps: number;
  custody_fee_annual: number;
  minimum_commission: number;
  schedule_name: string;
}

export default function BrokerIntegrationPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('dashboard');
  const [loading, setLoading] = useState(true);
  const [orgId, setOrgId] = useState('');
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [kycRecords, setKycRecords] = useState<KYCRecord[]>([]);
  const [onboardingRecords, setOnboardingRecords] = useState<OnboardingRecord[]>([]);
  const [transactionAlerts, setTransactionAlerts] = useState<TransactionAlert[]>([]);
  const [registrations, setRegistrations] = useState<Registration[]>([]);

  // Form states
  const [showNewKYC, setShowNewKYC] = useState(false);
  const [newKYC, setNewKYC] = useState({
    client_name: '',
    client_type: 'sovereign_wealth',
    jurisdiction: '',
    registration_number: '',
  });
  const [feeQuote, setFeeQuote] = useState<FeeQuote | null>(null);
  const [quoteForm, setQuoteForm] = useState({ client_type: 'sovereign_wealth', trade_value: '' });
  const [showKYCDetail, setShowKYCDetail] = useState<KYCRecord | null>(null);
  const [amlSummary, setAmlSummary] = useState<any>(null);

  useEffect(() => {
    const storedOrg = localStorage.getItem('quantive_org_id') || 'default';
    setOrgId(storedOrg);
    loadDashboard(storedOrg);
  }, []);

  const getHeaders = () => {
    const token = localStorage.getItem('access_token');
    const csrfMatch = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/);
    const csrf = csrfMatch ? decodeURIComponent(csrfMatch[1]) : '';
    return {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(csrf ? { 'X-CSRF-Token': csrf } : {}),
    };
  };

  const loadDashboard = async (oid: string) => {
    setLoading(true);
    try {
      const [dashRes, kycRes, onbRes, alertsRes, regRes] = await Promise.all([
        fetch(`${API_BASE}/api/broker/dashboard?org_id=${oid}`, { headers: getHeaders() }),
        fetch(`${API_BASE}/api/broker/kyc?org_id=${oid}`, { headers: getHeaders() }),
        fetch(`${API_BASE}/api/broker/onboarding?org_id=${oid}`, { headers: getHeaders() }),
        fetch(`${API_BASE}/api/broker/transactions/alerts?org_id=${oid}`, { headers: getHeaders() }),
        fetch(`${API_BASE}/api/broker/registration?org_id=${oid}`, { headers: getHeaders() }),
      ]);

      if (dashRes.ok) setDashboardData(await dashRes.json());
      if (kycRes.ok) setKycRecords((await kycRes.json()).records || []);
      if (onbRes.ok) setOnboardingRecords((await onbRes.json()).records || []);
      if (alertsRes.ok) setTransactionAlerts((await alertsRes.json()).alerts || []);
      if (regRes.ok) setRegistrations((await regRes.json()).registrations || []);
    } catch (err) {
      console.error('Failed to load broker dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  const createKYC = async () => {
    if (!newKYC.client_name || !newKYC.jurisdiction) return;
    try {
      const res = await fetch(`${API_BASE}/api/broker/kyc`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ org_id: orgId, ...newKYC }),
      });
      if (res.ok) {
        setShowNewKYC(false);
        setNewKYC({ client_name: '', client_type: 'sovereign_wealth', jurisdiction: '', registration_number: '' });
        loadDashboard(orgId);
      }
    } catch (err) {
      console.error('Failed to create KYC:', err);
    }
  };

  const loadAMLSummary = async (kycId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/broker/kyc/${kycId}/aml-summary`, { headers: getHeaders() });
      if (res.ok) setAmlSummary(await res.json());
    } catch (err) {
      console.error('Failed to load AML summary:', err);
    }
  };

  const getFeeQuote = async () => {
    if (!quoteForm.trade_value) return;
    try {
      const res = await fetch(
        `${API_BASE}/api/broker/fees/quote?org_id=${orgId}&client_type=${quoteForm.client_type}&trade_value=${quoteForm.trade_value}`,
        { headers: getHeaders() }
      );
      if (res.ok) setFeeQuote(await res.json());
    } catch (err) {
      console.error('Failed to get fee quote:', err);
    }
  };

  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },
    { id: 'kyc', label: 'KYC/AML', icon: Shield },
    { id: 'onboarding', label: 'Onboarding', icon: Users },
    { id: 'transactions', label: 'Transaction Monitoring', icon: Activity },
    { id: 'registration', label: 'Broker Registration', icon: Building2 },
    { id: 'fees', label: 'Fees & Commissions', icon: Wallet },
    { id: 'rules', label: 'Monitoring Rules', icon: Settings },
  ];

  const kycStatusColor = (status: string) => {
    switch (status) {
      case 'approved': return 'bg-green-500/20 text-green-400 border-green-500/30';
      case 'pending_documents': return 'bg-sky-500/20 text-sky-400 border-sky-500/30';
      case 'under_review': return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      case 'rejected': return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'escalated': return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
      default: return 'bg-zinc-500/20 text-zinc-400 border-zinc-500/30';
    }
  };

  const riskColor = (level: string) => {
    switch (level) {
      case 'high': return 'text-red-400';
      case 'medium': return 'text-sky-400';
      case 'low': return 'text-green-400';
      case 'prohibited': return 'text-red-600';
      default: return 'text-zinc-400';
    }
  };

  const severityColor = (severity: string | null) => {
    switch (severity) {
      case 'critical': return 'bg-red-600 text-white';
      case 'high': return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'medium': return 'bg-sky-500/20 text-sky-400 border-sky-500/30';
      case 'low': return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      default: return 'bg-zinc-500/20 text-zinc-400 border-zinc-500/30';
    }
  };

  const onboardingStageColor = (stage: string) => {
    switch (stage) {
      case 'active': return 'bg-green-500/20 text-green-400 border-green-500/30';
      case 'rejected': return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'funding': return 'bg-sky-500/20 text-sky-400 border-sky-500/30';
      default: return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
    }
  };

  return (
    <div className="min-h-screen bg-[#08090c]">
      {/* Header */}
      <div className="border-b border-white/5 px-6 py-4">
        <div className="max-w-[1600px] mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-sky-500/20 to-sky-600/10 border border-sky-500/20 flex items-center justify-center">
              <Building2 className="w-5 h-5 text-sky-400" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-white">Broker Integration</h1>
              <p className="text-xs text-zinc-500">KYC/AML · Client Onboarding · Transaction Monitoring · Registration</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => loadDashboard(orgId)}
              className="flex items-center gap-2 px-3 py-2 text-sm text-zinc-400 hover:text-white border border-white/5 rounded-lg hover:border-white/10 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
            <button
              onClick={() => setShowNewKYC(true)}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-black bg-sky-500 hover:bg-sky-400 rounded-lg transition-colors"
            >
              <Plus className="w-4 h-4" />
              New KYC
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-[1600px] mx-auto px-6 py-6">
        {/* Tabs */}
        <div className="flex items-center gap-1 mb-6 overflow-x-auto pb-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? 'bg-sky-500/10 text-sky-400 border border-sky-500/20'
                  : 'text-zinc-500 hover:text-zinc-300 hover:bg-white/5'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Dashboard Tab */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
              <div className="bg-white/[0.02] border border-white/5 rounded-xl p-4">
                <div className="text-xs text-zinc-500 mb-1">KYC Records</div>
                <div className="text-2xl font-bold text-white">{dashboardData?.summary.kyc_total || 0}</div>
                <div className="text-xs text-green-400 mt-1">{dashboardData?.summary.kyc_approved || 0} approved</div>
              </div>
              <div className="bg-white/[0.02] border border-white/5 rounded-xl p-4">
                <div className="text-xs text-zinc-500 mb-1">Pending KYC</div>
                <div className="text-2xl font-bold text-sky-400">{dashboardData?.summary.kyc_pending || 0}</div>
              </div>
              <div className="bg-white/[0.02] border border-white/5 rounded-xl p-4">
                <div className="text-xs text-zinc-500 mb-1">Active Onboarding</div>
                <div className="text-2xl font-bold text-blue-400">{dashboardData?.summary.onboarding_active || 0}</div>
              </div>
              <div className="bg-white/[0.02] border border-white/5 rounded-xl p-4">
                <div className="text-xs text-zinc-500 mb-1">Transactions</div>
                <div className="text-2xl font-bold text-white">{dashboardData?.summary.transactions_total || 0}</div>
                <div className="text-xs text-red-400 mt-1">{dashboardData?.summary.transactions_suspicious || 0} suspicious</div>
              </div>
              <div className="bg-white/[0.02] border border-white/5 rounded-xl p-4">
                <div className="text-xs text-zinc-500 mb-1">SARs Filed</div>
                <div className="text-2xl font-bold text-orange-400">{dashboardData?.summary.sar_filed || 0}</div>
              </div>
              <div className="bg-white/[0.02] border border-white/5 rounded-xl p-4">
                <div className="text-xs text-zinc-500 mb-1">Compliance Score</div>
                <div className="text-2xl font-bold text-sky-400">{dashboardData?.compliance_score || 0}%</div>
              </div>
            </div>

            {/* Risk Distribution & Registration Status */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-white/[0.02] border border-white/5 rounded-xl p-6">
                <h3 className="text-sm font-medium text-white mb-4">Risk Distribution</h3>
                {dashboardData?.risk_distribution && Object.keys(dashboardData.risk_distribution).length > 0 ? (
                  <div className="space-y-3">
                    {Object.entries(dashboardData.risk_distribution).map(([level, count]) => (
                      <div key={level} className="flex items-center justify-between">
                        <span className={`text-sm capitalize ${riskColor(level)}`}>{level}</span>
                        <div className="flex items-center gap-3">
                          <div className="w-32 h-2 bg-white/5 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full ${
                                level === 'high' ? 'bg-red-500' : level === 'medium' ? 'bg-sky-500' : 'bg-green-500'
                              }`}
                              style={{ width: `${(count / (dashboardData?.summary.kyc_total || 1)) * 100}%` }}
                            />
                          </div>
                          <span className="text-sm text-zinc-400 w-8 text-right">{count}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-zinc-500">No KYC records yet</p>
                )}
              </div>

              <div className="bg-white/[0.02] border border-white/5 rounded-xl p-6">
                <h3 className="text-sm font-medium text-white mb-4">Registration Status</h3>
                {dashboardData?.registration_status && Object.keys(dashboardData.registration_status).length > 0 ? (
                  <div className="space-y-3">
                    {Object.entries(dashboardData.registration_status).map(([status, count]) => (
                      <div key={status} className="flex items-center justify-between">
                        <span className="text-sm text-zinc-300 capitalize">{status.replace(/_/g, ' ')}</span>
                        <span className="text-sm text-zinc-400">{count}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-zinc-500">No registrations yet</p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* KYC/AML Tab */}
        {activeTab === 'kyc' && (
          <div className="space-y-4">
            {/* New KYC Form */}
            {showNewKYC && (
              <div className="bg-white/[0.02] border border-sky-500/20 rounded-xl p-6">
                <h3 className="text-sm font-medium text-white mb-4">New KYC Record</h3>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div>
                    <label className="block text-xs text-zinc-500 mb-1">Client Name</label>
                    <input
                      type="text"
                      value={newKYC.client_name}
                      onChange={(e) => setNewKYC({ ...newKYC, client_name: e.target.value })}
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-sky-500/50"
                      placeholder="e.g. Ministry of Finance"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-zinc-500 mb-1">Client Type</label>
                    <select
                      value={newKYC.client_type}
                      onChange={(e) => setNewKYC({ ...newKYC, client_type: e.target.value })}
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-sky-500/50"
                    >
                      <option value="sovereign_wealth">Sovereign Wealth Fund</option>
                      <option value="central_bank">Central Bank</option>
                      <option value="treasury">Treasury</option>
                      <option value="pension_fund">Pension Fund</option>
                      <option value="ministry">Ministry</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-zinc-500 mb-1">Jurisdiction</label>
                    <input
                      type="text"
                      value={newKYC.jurisdiction}
                      onChange={(e) => setNewKYC({ ...newKYC, jurisdiction: e.target.value })}
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-sky-500/50"
                      placeholder="e.g. US, GB, SG"
                    />
                  </div>
                  <div className="flex items-end gap-2">
                    <button
                      onClick={createKYC}
                      className="px-4 py-2 text-sm font-medium text-black bg-sky-500 hover:bg-sky-400 rounded-lg transition-colors"
                    >
                      Create
                    </button>
                    <button
                      onClick={() => setShowNewKYC(false)}
                      className="px-4 py-2 text-sm text-zinc-400 hover:text-white border border-white/10 rounded-lg transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* KYC Records */}
            <div className="bg-white/[0.02] border border-white/5 rounded-xl overflow-hidden">
              <div className="px-6 py-4 border-b border-white/5">
                <h3 className="text-sm font-medium text-white">KYC Records ({kycRecords.length})</h3>
              </div>
              {kycRecords.length === 0 ? (
                <div className="p-12 text-center">
                  <Shield className="w-12 h-12 text-zinc-700 mx-auto mb-3" />
                  <p className="text-sm text-zinc-500">No KYC records yet</p>
                  <p className="text-xs text-zinc-600 mt-1">Create a KYC record to start client onboarding</p>
                </div>
              ) : (
                <div className="divide-y divide-white/5">
                  {kycRecords.map((kyc) => (
                    <div
                      key={kyc.id}
                      className="px-6 py-4 hover:bg-white/[0.02] transition-colors cursor-pointer"
                      onClick={() => { setShowKYCDetail(kyc); loadAMLSummary(kyc.id); }}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <div className="w-10 h-10 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center">
                            <Building2 className="w-5 h-5 text-sky-400" />
                          </div>
                          <div>
                            <div className="text-sm font-medium text-white">{kyc.client_name}</div>
                            <div className="text-xs text-zinc-500">{kyc.client_type.replace(/_/g, ' ')} · {kyc.jurisdiction}</div>
                          </div>
                        </div>
                        <div className="flex items-center gap-4">
                          <div className="text-right">
                            <div className="text-xs text-zinc-500">Risk Score</div>
                            <div className={`text-sm font-medium ${riskColor(kyc.risk_level)}`}>{kyc.risk_score}</div>
                          </div>
                          <div className={`px-2 py-1 text-xs font-medium rounded border ${kycStatusColor(kyc.kyc_status)}`}>
                            {kyc.kyc_status.replace(/_/g, ' ')}
                          </div>
                          {kyc.cip_verified && <CheckCircle className="w-4 h-4 text-green-400" />}
                          {kyc.edd_required && !amlSummary?.edd_status && <AlertTriangle className="w-4 h-4 text-sky-400" />}
                          <ChevronRight className="w-4 h-4 text-zinc-600" />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* KYC Detail Modal */}
            {showKYCDetail && (
              <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                <div className="bg-[#0c0d10] border border-white/10 rounded-2xl w-full max-w-2xl max-h-[80vh] overflow-y-auto">
                  <div className="flex items-center justify-between p-6 border-b border-white/5">
                    <div>
                      <h2 className="text-lg font-semibold text-white">{showKYCDetail.client_name}</h2>
                      <p className="text-xs text-zinc-500">{showKYCDetail.client_type.replace(/_/g, ' ')} · {showKYCDetail.jurisdiction}</p>
                    </div>
                    <button onClick={() => { setShowKYCDetail(null); setAmlSummary(null); }} className="text-zinc-500 hover:text-white">
                      <XCircle className="w-5 h-5" />
                    </button>
                  </div>
                  <div className="p-6 space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-white/[0.02] border border-white/5 rounded-lg p-3">
                        <div className="text-xs text-zinc-500">KYC Status</div>
                        <div className={`text-sm font-medium mt-1 ${kycStatusColor(showKYCDetail.kyc_status).split(' ')[1]}`}>
                          {showKYCDetail.kyc_status.replace(/_/g, ' ')}
                        </div>
                      </div>
                      <div className="bg-white/[0.02] border border-white/5 rounded-lg p-3">
                        <div className="text-xs text-zinc-500">Risk Level</div>
                        <div className={`text-sm font-medium mt-1 ${riskColor(showKYCDetail.risk_level)}`}>
                          {showKYCDetail.risk_level} ({showKYCDetail.risk_score})
                        </div>
                      </div>
                      <div className="bg-white/[0.02] border border-white/5 rounded-lg p-3">
                        <div className="text-xs text-zinc-500">CIP Verified</div>
                        <div className="text-sm font-medium mt-1 text-white">
                          {showKYCDetail.cip_verified ? 'Yes' : 'No'}
                        </div>
                      </div>
                      <div className="bg-white/[0.02] border border-white/5 rounded-lg p-3">
                        <div className="text-xs text-zinc-500">CDD Status</div>
                        <div className="text-sm font-medium mt-1 text-white">
                          {showKYCDetail.cdd_status.replace(/_/g, ' ')}
                        </div>
                      </div>
                      <div className="bg-white/[0.02] border border-white/5 rounded-lg p-3">
                        <div className="text-xs text-zinc-500">EDD Required</div>
                        <div className="text-sm font-medium mt-1 text-white">
                          {showKYCDetail.edd_required ? 'Yes' : 'No'}
                        </div>
                      </div>
                      <div className="bg-white/[0.02] border border-white/5 rounded-lg p-3">
                        <div className="text-xs text-zinc-500">Next Review</div>
                        <div className="text-sm font-medium mt-1 text-white">
                          {showKYCDetail.next_review_date ? new Date(showKYCDetail.next_review_date).toLocaleDateString() : 'N/A'}
                        </div>
                      </div>
                    </div>

                    {amlSummary && (
                      <div className="bg-white/[0.02] border border-white/5 rounded-lg p-4">
                        <h4 className="text-sm font-medium text-white mb-3">AML Summary</h4>
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <div className="text-xs text-zinc-500">Total Transactions</div>
                            <div className="text-sm text-white">{amlSummary.transaction_summary?.total_transactions || 0}</div>
                          </div>
                          <div>
                            <div className="text-xs text-zinc-500">Suspicious Transactions</div>
                            <div className="text-sm text-red-400">{amlSummary.transaction_summary?.suspicious_transactions || 0}</div>
                          </div>
                          <div>
                            <div className="text-xs text-zinc-500">SARs Filed</div>
                            <div className="text-sm text-orange-400">{amlSummary.transaction_summary?.sar_filed || 0}</div>
                          </div>
                          <div>
                            <div className="text-xs text-zinc-500">Sanctions Status</div>
                            <div className="text-sm text-green-400">{amlSummary.sanctions_screening?.status || 'clear'}</div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Onboarding Tab */}
        {activeTab === 'onboarding' && (
          <div className="space-y-4">
            <div className="bg-white/[0.02] border border-white/5 rounded-xl overflow-hidden">
              <div className="px-6 py-4 border-b border-white/5">
                <h3 className="text-sm font-medium text-white">Client Onboarding ({onboardingRecords.length})</h3>
              </div>
              {onboardingRecords.length === 0 ? (
                <div className="p-12 text-center">
                  <Users className="w-12 h-12 text-zinc-700 mx-auto mb-3" />
                  <p className="text-sm text-zinc-500">No onboarding records yet</p>
                  <p className="text-xs text-zinc-600 mt-1">Complete KYC to start onboarding</p>
                </div>
              ) : (
                <div className="divide-y divide-white/5">
                  {onboardingRecords.map((onb) => (
                    <div key={onb.id} className="px-6 py-4 hover:bg-white/[0.02] transition-colors">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <div className="w-10 h-10 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
                            <Users className="w-5 h-5 text-blue-400" />
                          </div>
                          <div>
                            <div className="text-sm font-medium text-white">{onb.client_name}</div>
                            <div className="text-xs text-zinc-500">{onb.client_type.replace(/_/g, ' ')} · {onb.jurisdiction}</div>
                          </div>
                        </div>
                        <div className="flex items-center gap-4">
                          <div className="text-right">
                            <div className="text-xs text-zinc-500">Documents</div>
                            <div className="text-sm text-white">
                              {onb.documents_submitted?.length || 0}/{onb.documents_required.length}
                            </div>
                          </div>
                          <div className={`px-2 py-1 text-xs font-medium rounded border ${onboardingStageColor(onb.stage)}`}>
                            {onb.stage.replace(/_/g, ' ')}
                          </div>
                          <ChevronRight className="w-4 h-4 text-zinc-600" />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Transaction Monitoring Tab */}
        {activeTab === 'transactions' && (
          <div className="space-y-4">
            <div className="bg-white/[0.02] border border-white/5 rounded-xl overflow-hidden">
              <div className="px-6 py-4 border-b border-white/5 flex items-center justify-between">
                <h3 className="text-sm font-medium text-white">Transaction Alerts ({transactionAlerts.length})</h3>
                <div className="flex items-center gap-2">
                  <button className="px-3 py-1.5 text-xs text-zinc-400 hover:text-white border border-white/10 rounded-lg transition-colors">
                    Scan Rules
                  </button>
                </div>
              </div>
              {transactionAlerts.length === 0 ? (
                <div className="p-12 text-center">
                  <Activity className="w-12 h-12 text-zinc-700 mx-auto mb-3" />
                  <p className="text-sm text-zinc-500">No transaction alerts</p>
                  <p className="text-xs text-zinc-600 mt-1">Suspicious transactions will appear here</p>
                </div>
              ) : (
                <div className="divide-y divide-white/5">
                  {transactionAlerts.map((alert) => (
                    <div key={alert.id} className="px-6 py-4 hover:bg-white/[0.02] transition-colors">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                            alert.alert_severity === 'high' ? 'bg-red-500/10 border border-red-500/20' :
                            alert.alert_severity === 'medium' ? 'bg-sky-500/10 border border-sky-500/20' :
                            'bg-blue-500/10 border border-blue-500/20'
                          }`}>
                            <AlertTriangle className={`w-5 h-5 ${
                              alert.alert_severity === 'high' ? 'text-red-400' :
                              alert.alert_severity === 'medium' ? 'text-sky-400' :
                              'text-blue-400'
                            }`} />
                          </div>
                          <div>
                            <div className="text-sm font-medium text-white">{alert.instrument_identifier}</div>
                            <div className="text-xs text-zinc-500">{alert.transaction_type} · {alert.alert_reasons?.join(', ')}</div>
                          </div>
                        </div>
                        <div className="flex items-center gap-4">
                          <div className="text-right">
                            <div className="text-sm font-medium text-white">${alert.total_value.toLocaleString()}</div>
                            <div className="text-xs text-zinc-500">{alert.currency}</div>
                          </div>
                          <div className={`px-2 py-1 text-xs font-medium rounded border ${severityColor(alert.alert_severity)}`}>
                            {alert.alert_severity || 'info'}
                          </div>
                          {alert.sar_filed && (
                            <div className="px-2 py-1 text-xs font-medium rounded border bg-orange-500/20 text-orange-400 border-orange-500/30">
                              SAR Filed
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Registration Tab */}
        {activeTab === 'registration' && (
          <div className="space-y-4">
            <div className="bg-white/[0.02] border border-white/5 rounded-xl overflow-hidden">
              <div className="px-6 py-4 border-b border-white/5">
                <h3 className="text-sm font-medium text-white">Broker Registrations ({registrations.length})</h3>
              </div>
              {registrations.length === 0 ? (
                <div className="p-12 text-center">
                  <Building2 className="w-12 h-12 text-zinc-700 mx-auto mb-3" />
                  <p className="text-sm text-zinc-500">No registrations yet</p>
                  <p className="text-xs text-zinc-600 mt-1">Register with SEC, FINRA, or state regulators</p>
                </div>
              ) : (
                <div className="divide-y divide-white/5">
                  {registrations.map((reg) => (
                    <div key={reg.id} className="px-6 py-4 hover:bg-white/[0.02] transition-colors">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <div className="w-10 h-10 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center">
                            <FileCheck className="w-5 h-5 text-purple-400" />
                          </div>
                          <div>
                            <div className="text-sm font-medium text-white">{reg.regulator}</div>
                            <div className="text-xs text-zinc-500">{reg.registration_type.replace(/_/g, ' ')}</div>
                          </div>
                        </div>
                        <div className="flex items-center gap-4">
                          {reg.crd_number && (
                            <div className="text-right">
                              <div className="text-xs text-zinc-500">CRD#</div>
                              <div className="text-sm text-white">{reg.crd_number}</div>
                            </div>
                          )}
                          <div className={`px-2 py-1 text-xs font-medium rounded border ${
                            reg.status === 'approved' ? 'bg-green-500/20 text-green-400 border-green-500/30' :
                            reg.status === 'pending' ? 'bg-sky-500/20 text-sky-400 border-sky-500/30' :
                            'bg-zinc-500/20 text-zinc-400 border-zinc-500/30'
                          }`}>
                            {reg.status}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Fees Tab */}
        {activeTab === 'fees' && (
          <div className="space-y-6">
            <div className="bg-white/[0.02] border border-white/5 rounded-xl p-6">
              <h3 className="text-sm font-medium text-white mb-4">Commission Quote Calculator</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs text-zinc-500 mb-1">Client Type</label>
                  <select
                    value={quoteForm.client_type}
                    onChange={(e) => setQuoteForm({ ...quoteForm, client_type: e.target.value })}
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-sky-500/50"
                  >
                    <option value="sovereign_wealth">Sovereign Wealth Fund</option>
                    <option value="central_bank">Central Bank</option>
                    <option value="treasury">Treasury</option>
                    <option value="pension_fund">Pension Fund</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-zinc-500 mb-1">Trade Value (USD)</label>
                  <input
                    type="number"
                    value={quoteForm.trade_value}
                    onChange={(e) => setQuoteForm({ ...quoteForm, trade_value: e.target.value })}
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-sky-500/50"
                    placeholder="e.g. 10000000"
                  />
                </div>
                <div className="flex items-end">
                  <button
                    onClick={getFeeQuote}
                    className="px-4 py-2 text-sm font-medium text-black bg-sky-500 hover:bg-sky-400 rounded-lg transition-colors"
                  >
                    Get Quote
                  </button>
                </div>
              </div>
              {feeQuote && (
                <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-white/[0.02] border border-white/5 rounded-lg p-3">
                    <div className="text-xs text-zinc-500">Commission</div>
                    <div className="text-lg font-bold text-sky-400">${feeQuote.commission.toLocaleString()}</div>
                  </div>
                  <div className="bg-white/[0.02] border border-white/5 rounded-lg p-3">
                    <div className="text-xs text-zinc-500">Commission (bps)</div>
                    <div className="text-lg font-bold text-white">{feeQuote.commission_bps}</div>
                  </div>
                  <div className="bg-white/[0.02] border border-white/5 rounded-lg p-3">
                    <div className="text-xs text-zinc-500">Annual Custody</div>
                    <div className="text-lg font-bold text-white">${feeQuote.custody_fee_annual.toLocaleString()}</div>
                  </div>
                  <div className="bg-white/[0.02] border border-white/5 rounded-lg p-3">
                    <div className="text-xs text-zinc-500">Schedule</div>
                    <div className="text-sm text-white">{feeQuote.schedule_name}</div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Monitoring Rules Tab */}
        {activeTab === 'rules' && (
          <div className="space-y-4">
            <div className="bg-white/[0.02] border border-white/5 rounded-xl p-6">
              <h3 className="text-sm font-medium text-white mb-4">Transaction Monitoring Rules</h3>
              <div className="space-y-3">
                {[
                  { name: 'Large Transaction Alert', type: 'threshold', threshold: '$10,000', severity: 'medium', status: 'active' },
                  { name: 'Very Large Transaction Alert', type: 'threshold', threshold: '$50,000', severity: 'high', status: 'active' },
                  { name: 'Daily Volume Limit', type: 'velocity', threshold: '$100,000/day', severity: 'high', status: 'active' },
                  { name: 'Structuring Detection', type: 'pattern', threshold: 'Multiple sub-threshold', severity: 'high', status: 'active' },
                  { name: 'Sanctions Screening', type: 'sanctions', threshold: 'OFAC/EU/UN lists', severity: 'critical', status: 'active' },
                ].map((rule, i) => (
                  <div key={i} className="flex items-center justify-between bg-white/[0.02] border border-white/5 rounded-lg p-4">
                    <div className="flex items-center gap-3">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                        rule.severity === 'critical' ? 'bg-red-500/10 border border-red-500/20' :
                        rule.severity === 'high' ? 'bg-orange-500/10 border border-orange-500/20' :
                        'bg-blue-500/10 border border-blue-500/20'
                      }`}>
                        <AlertCircle className={`w-4 h-4 ${
                          rule.severity === 'critical' ? 'text-red-400' :
                          rule.severity === 'high' ? 'text-orange-400' :
                          'text-blue-400'
                        }`} />
                      </div>
                      <div>
                        <div className="text-sm font-medium text-white">{rule.name}</div>
                        <div className="text-xs text-zinc-500">{rule.type} · {rule.threshold}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className={`px-2 py-1 text-xs font-medium rounded border ${severityColor(rule.severity)}`}>
                        {rule.severity}
                      </div>
                      <div className="w-2 h-2 rounded-full bg-green-500" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
