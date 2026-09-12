import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Shield, FileText, Globe, TrendingUp, Users, CheckCircle,
  Clock, AlertTriangle, ArrowRight, BarChart3
} from 'lucide-react';
import { api } from '../api';

interface ComplianceStatus {
  standard: string;
  score: number;
  status: string;
}

interface PilotSummary {
  total_programs: number;
  active: number;
  completed: number;
  metrics: Record<string, number>;
}

interface TransparencyStats {
  total_countries: number;
  average_score: number;
  leaders_count: number;
}

interface SecurityChecklist {
  category: string;
  items: Array<{ item: string; status: string }>;
}

export default function ProcurementDashboardPage() {
  const [compliance, setCompliance] = useState<ComplianceStatus[]>([]);
  const [pilots, setPilots] = useState<PilotSummary | null>(null);
  const [transparency, setTransparency] = useState<TransparencyStats | null>(null);
  const [securityChecklist, setSecurityChecklist] = useState<SecurityChecklist[]>([]);
  const [slaStatus, setSlaStatus] = useState<any>(null);
  const [drStatus, setDrStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    try {
      const [complianceData, pilotData, transparencyData, securityData, slaData, drData] = await Promise.all([
        api.transparencyIndex.globalStats().catch(() => null),
        api.pilotProgram.dashboard().catch(() => null),
        api.transparencyIndex.globalStats().catch(() => null),
        api.sovereignMode.securityChecklist().catch(() => null),
        api.sla.documentation().catch(() => null),
        api.disasterRecovery.status().catch(() => null),
      ]);

      if (pilotData) setPilots({
        total_programs: pilotData.total_programs || 0,
        active: pilotData.active || 0,
        completed: pilotData.completed || 0,
        metrics: pilotData.metrics || {},
      });
      if (transparencyData) setTransparency({
        total_countries: transparencyData.total_countries || 0,
        average_score: transparencyData.avg_score || 0,
        leaders_count: transparencyData.top_performers?.length || 0,
      });
      if (securityData) setSecurityChecklist(Array.isArray(securityData.items) ? [{ category: 'Security', items: securityData.items.map((i: any) => ({ item: i.name || i.id, status: i.status })) }] : []);
      if (slaData) setSlaStatus(slaData);
      if (drData) setDrStatus(drData);
    } catch (e) {
      console.error('Failed to load dashboard:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="animate-pulse space-y-6">
            <div className="h-8 bg-slate-200 rounded w-1/3"></div>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-32 bg-slate-200 rounded-lg"></div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
            <Shield className="w-8 h-8 text-blue-600" />
            Government Procurement Dashboard
          </h1>
          <p className="text-slate-600 mt-2">
            Track procurement readiness, compliance status, and government pilot programs.
          </p>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                <Globe className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <div className="text-sm text-slate-500">Countries Ranked</div>
                <div className="text-2xl font-bold text-slate-900">{transparency?.total_countries || 0}</div>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-emerald-100 rounded-lg flex items-center justify-center">
                <Users className="w-6 h-6 text-emerald-600" />
              </div>
              <div>
                <div className="text-sm text-slate-500">Active Pilots</div>
                <div className="text-2xl font-bold text-slate-900">{pilots?.active || 0}</div>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-amber-100 rounded-lg flex items-center justify-center">
                <TrendingUp className="w-6 h-6 text-amber-600" />
              </div>
              <div>
                <div className="text-sm text-slate-500">Conversion Rate</div>
                <div className="text-2xl font-bold text-slate-900">{pilots?.completed || 0}</div>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                <BarChart3 className="w-6 h-6 text-purple-600" />
              </div>
              <div>
                <div className="text-sm text-slate-500">Metrics</div>
                <div className="text-2xl font-bold text-slate-900">
                  {Object.keys(pilots?.metrics || {}).length}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Procurement Readiness */}
          <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
            <h2 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-emerald-600" />
              Procurement Readiness
            </h2>
            <div className="space-y-3">
              <Link to="/transparency-index" className="flex items-center justify-between p-3 bg-slate-50 rounded-lg hover:bg-slate-100">
                <div className="flex items-center gap-3">
                  <Globe className="w-5 h-5 text-blue-600" />
                  <span className="font-medium text-slate-900">Transparency Index</span>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-400" />
              </Link>
              <Link to="/pricing" className="flex items-center justify-between p-3 bg-slate-50 rounded-lg hover:bg-slate-100">
                <div className="flex items-center gap-3">
                  <TrendingUp className="w-5 h-5 text-emerald-600" />
                  <span className="font-medium text-slate-900">Outcome-Based Pricing</span>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-400" />
              </Link>
              <Link to="/case-studies" className="flex items-center justify-between p-3 bg-slate-50 rounded-lg hover:bg-slate-100">
                <div className="flex items-center gap-3">
                  <FileText className="w-5 h-5 text-amber-600" />
                  <span className="font-medium text-slate-900">Case Studies</span>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-400" />
              </Link>
            </div>
          </div>

          {/* Security Status */}
          <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
            <h2 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <Shield className="w-5 h-5 text-blue-600" />
              Security & Compliance
            </h2>
            <div className="space-y-3">
              {securityChecklist.length > 0 ? (
                securityChecklist.slice(0, 4).map((category, idx) => {
                  const metCount = category.items.filter(i => i.status === 'met' || i.status === 'passed').length;
                  const total = category.items.length;
                  return (
                    <div key={idx} className="p-3 bg-slate-50 rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium text-slate-900">{category.category}</span>
                        <span className="text-sm text-slate-500">{metCount}/{total}</span>
                      </div>
                      <div className="w-full bg-slate-200 rounded-full h-2">
                        <div
                          className="bg-emerald-500 h-2 rounded-full"
                          style={{ width: `${total > 0 ? (metCount / total) * 100 : 0}%` }}
                        ></div>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="p-3 bg-slate-50 rounded-lg text-center text-slate-500 text-sm">
                  No security checklist data available
                </div>
              )}
            </div>
          </div>

          {/* SLA Status */}
          <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
            <h2 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <Clock className="w-5 h-5 text-amber-600" />
              SLA Commitments
            </h2>
            {slaStatus ? (
              <div className="space-y-3">
                <div className="flex justify-between p-3 bg-slate-50 rounded-lg">
                  <span className="text-slate-600">Monthly Uptime</span>
                  <span className="font-bold text-emerald-600">≥ 99.95%</span>
                </div>
                <div className="flex justify-between p-3 bg-slate-50 rounded-lg">
                  <span className="text-slate-600">RTO</span>
                  <span className="font-bold text-emerald-600">≤ 4 hours</span>
                </div>
                <div className="flex justify-between p-3 bg-slate-50 rounded-lg">
                  <span className="text-slate-600">RPO</span>
                  <span className="font-bold text-emerald-600">≤ 15 minutes</span>
                </div>
                <div className="flex justify-between p-3 bg-slate-50 rounded-lg">
                  <span className="text-slate-600">API P95</span>
                  <span className="font-bold text-emerald-600">≤ 500ms</span>
                </div>
              </div>
            ) : (
              <div className="text-center py-4 text-slate-500">Loading SLA data...</div>
            )}
          </div>

          {/* DR Status */}
          <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
            <h2 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-red-600" />
              Disaster Recovery
            </h2>
            {drStatus ? (
              <div className="space-y-3">
                <div className="flex justify-between p-3 bg-slate-50 rounded-lg">
                  <span className="text-slate-600">Status</span>
                  <span className="font-bold text-emerald-600 capitalize">{drStatus.status}</span>
                </div>
                <div className="flex justify-between p-3 bg-slate-50 rounded-lg">
                  <span className="text-slate-600">Total Backups</span>
                  <span className="font-bold text-slate-900">{drStatus.total_backups}</span>
                </div>
                <div className="flex justify-between p-3 bg-slate-50 rounded-lg">
                  <span className="text-slate-600">Verified Backups</span>
                  <span className="font-bold text-emerald-600">{drStatus.verified_backups}</span>
                </div>
                <div className="flex justify-between p-3 bg-slate-50 rounded-lg">
                  <span className="text-slate-600">DR Tests</span>
                  <span className="font-bold text-slate-900">{drStatus.total_tests}</span>
                </div>
              </div>
            ) : (
              <div className="text-center py-4 text-slate-500">Loading DR data...</div>
            )}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="mt-8 bg-gradient-to-r from-blue-600 to-blue-700 rounded-xl shadow-lg p-6 text-white">
          <h2 className="text-xl font-semibold mb-4">Quick Actions</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Link to="/transparency-index" className="p-4 bg-white/10 rounded-lg hover:bg-white/20 flex items-center gap-3">
              <Globe className="w-6 h-6" />
              <div>
                <div className="font-medium">View Rankings</div>
                <div className="text-sm text-blue-100">See country transparency scores</div>
              </div>
            </Link>
            <Link to="/pricing" className="p-4 bg-white/10 rounded-lg hover:bg-white/20 flex items-center gap-3">
              <TrendingUp className="w-6 h-6" />
              <div>
                <div className="font-medium">Calculate Pricing</div>
                <div className="text-sm text-blue-100">Outcome-based pricing for governments</div>
              </div>
            </Link>
            <Link to="/case-studies" className="p-4 bg-white/10 rounded-lg hover:bg-white/20 flex items-center gap-3">
              <FileText className="w-6 h-6" />
              <div>
                <div className="font-medium">Generate Case Study</div>
                <div className="text-sm text-blue-100">Create pilot program case studies</div>
              </div>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
