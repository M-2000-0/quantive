import { useCallback, useEffect, useState } from 'react';
import {
  Shield, Lock, Eye, Server, Database, Key, CheckCircle,
  AlertTriangle, Globe, Cpu, HardDrive
} from 'lucide-react';
import { api } from '../api';

interface SovereignModeConfig {
  mode: string;
  data_residency: {
    allowed_regions: string[];
    max_latency_ms: number;
    encryption_in_transit: boolean;
    encryption_at_rest: boolean;
  };
  ai_safeguards: {
    model_validation_required: boolean;
    backtesting_required: boolean;
    human_approval_required: boolean;
    explainability_required: boolean;
    max_automation_level: string;
  };
  audit: {
    immutable_logging: boolean;
    log_retention_years: number;
    external_audit_required: boolean;
    real_time_monitoring: boolean;
  };
  access_control: {
    mfa_required: boolean;
    ip_whitelist: string[];
    session_timeout_minutes: number;
    role_based_access: boolean;
  };
}

interface SecurityChecklist {
  category: string;
  items: Array<{
    item: string;
    status: string;
    description: string;
  }>;
}

export default function SovereignModePage() {
  const [config, setConfig] = useState<SovereignModeConfig | null>(null);
  const [checklist, setChecklist] = useState<SecurityChecklist[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'checklist' | 'settings'>('overview');

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [configData, checklistData] = await Promise.all([
        api.sovereignMode.status().catch(() => null),
        api.sovereignMode.securityChecklist().catch(() => null),
      ]);

      if (configData?.config) setConfig(configData.config);
      if (checklistData?.checklist) setChecklist(checklistData.checklist);
    } catch (e) {
      console.error('Failed to load sovereign mode:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="animate-pulse space-y-6">
            <div className="h-8 bg-slate-200 rounded w-1/3"></div>
            <div className="h-64 bg-slate-200 rounded-lg"></div>
          </div>
        </div>
      </div>
    );
  }

  const totalItems = checklist.reduce((acc, cat) => acc + cat.items.length, 0);
  const metItems = checklist.reduce(
    (acc, cat) => acc + cat.items.filter(i => i.status === 'met' || i.status === 'required').length,
    0
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
            <Shield className="w-8 h-8 text-blue-600" />
            Zero Trust Sovereign Mode
          </h1>
          <p className="text-slate-600 mt-2">
            Government-grade security configuration for data sovereignty and AI governance.
          </p>
        </div>

        {/* Status Banner */}
        <div className={`rounded-xl p-6 mb-8 ${
          config?.mode === 'sovereign'
            ? 'bg-gradient-to-r from-emerald-600 to-emerald-700 text-white'
            : 'bg-gradient-to-r from-amber-500 to-amber-600 text-white'
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {config?.mode === 'sovereign' ? (
                <CheckCircle className="w-10 h-10" />
              ) : (
                <AlertTriangle className="w-10 h-10" />
              )}
              <div>
                <div className="text-2xl font-bold">
                  Mode: {config?.mode === 'sovereign' ? 'Sovereign (Full)' : config?.mode || 'Standard'}
                </div>
                <div className="text-emerald-100">
                  {metItems}/{totalItems} security requirements met
                </div>
              </div>
            </div>
            <div className="text-right">
              <div className="text-4xl font-bold">
                {Math.round((metItems / totalItems) * 100)}%
              </div>
              <div className="text-emerald-100">Compliance Score</div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          {[
            { key: 'overview', label: 'Overview', icon: Eye },
            { key: 'checklist', label: 'Security Checklist', icon: CheckCircle },
            { key: 'settings', label: 'Configuration', icon: Lock },
          ].map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as any)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-slate-600 hover:bg-slate-50 border border-slate-200'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                  <Database className="w-5 h-5 text-blue-600" />
                </div>
                <h3 className="font-medium text-slate-900">Data Residency</h3>
              </div>
              <ul className="space-y-2 text-sm">
                <li className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-500" />
                  <span>Encryption in transit: {config?.data_residency.encryption_in_transit ? 'Yes' : 'No'}</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-500" />
                  <span>Encryption at rest: {config?.data_residency.encryption_at_rest ? 'Yes' : 'No'}</span>
                </li>
                <li className="flex items-center gap-2">
                  <Globe className="w-4 h-4 text-slate-400" />
                  <span>Regions: {config?.data_residency.allowed_regions?.length || 0}</span>
                </li>
              </ul>
            </div>

            <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-amber-100 rounded-lg flex items-center justify-center">
                  <Cpu className="w-5 h-5 text-amber-600" />
                </div>
                <h3 className="font-medium text-slate-900">AI Safeguards</h3>
              </div>
              <ul className="space-y-2 text-sm">
                <li className="flex items-center gap-2">
                  {config?.ai_safeguards.model_validation_required ? (
                    <CheckCircle className="w-4 h-4 text-emerald-500" />
                  ) : (
                    <AlertTriangle className="w-4 h-4 text-red-500" />
                  )}
                  <span>Model validation required</span>
                </li>
                <li className="flex items-center gap-2">
                  {config?.ai_safeguards.human_approval_required ? (
                    <CheckCircle className="w-4 h-4 text-emerald-500" />
                  ) : (
                    <AlertTriangle className="w-4 h-4 text-red-500" />
                  )}
                  <span>Human approval for trades</span>
                </li>
                <li className="flex items-center gap-2">
                  {config?.ai_safeguards.explainability_required ? (
                    <CheckCircle className="w-4 h-4 text-emerald-500" />
                  ) : (
                    <AlertTriangle className="w-4 h-4 text-red-500" />
                  )}
                  <span>Explainability required</span>
                </li>
              </ul>
            </div>

            <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center">
                  <HardDrive className="w-5 h-5 text-emerald-600" />
                </div>
                <h3 className="font-medium text-slate-900">Audit & Compliance</h3>
              </div>
              <ul className="space-y-2 text-sm">
                <li className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-500" />
                  <span>Immutable logging: {config?.audit.immutable_logging ? 'Yes' : 'No'}</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-500" />
                  <span>Retention: {config?.audit.log_retention_years} years</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-500" />
                  <span>Real-time monitoring: {config?.audit.real_time_monitoring ? 'Yes' : 'No'}</span>
                </li>
              </ul>
            </div>

            <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                  <Key className="w-5 h-5 text-purple-600" />
                </div>
                <h3 className="font-medium text-slate-900">Access Control</h3>
              </div>
              <ul className="space-y-2 text-sm">
                <li className="flex items-center gap-2">
                  {config?.access_control.mfa_required ? (
                    <CheckCircle className="w-4 h-4 text-emerald-500" />
                  ) : (
                    <AlertTriangle className="w-4 h-4 text-red-500" />
                  )}
                  <span>MFA required: {config?.access_control.mfa_required ? 'Yes' : 'No'}</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-500" />
                  <span>Session timeout: {config?.access_control.session_timeout_minutes} min</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-500" />
                  <span>RBAC: {config?.access_control.role_based_access ? 'Enabled' : 'Disabled'}</span>
                </li>
              </ul>
            </div>
          </div>
        )}

        {activeTab === 'checklist' && (
          <div className="space-y-4">
            {checklist.map((category, catIdx) => {
              const met = category.items.filter(i => i.status === 'met' || i.status === 'required').length;
              const total = category.items.length;
              return (
                <div key={catIdx} className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold text-slate-900">{category.category}</h3>
                    <span className="text-sm text-slate-500">{met}/{total} items</span>
                  </div>
                  <div className="space-y-2">
                    {category.items.map((item, itemIdx) => (
                      <div
                        key={itemIdx}
                        className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg"
                      >
                        <CheckCircle className="w-4 h-4 text-emerald-500 mt-0.5" />
                        <div>
                          <div className="font-medium text-slate-900 text-sm">{item.item}</div>
                          <div className="text-xs text-slate-500">{item.description}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
            <h3 className="font-semibold text-slate-900 mb-4">Sovereign Mode Configuration</h3>
            <p className="text-slate-500 text-sm mb-6">
              Contact sales to enable or modify sovereign mode settings for your government deployment.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="p-4 bg-slate-50 rounded-lg">
                <h4 className="font-medium text-slate-900 mb-2">Data Residency</h4>
                <ul className="text-sm text-slate-600 space-y-1">
                  <li>Allowed regions: {config?.data_residency.allowed_regions?.join(', ') || 'Not configured'}</li>
                  <li>Max latency: {config?.data_residency.max_latency_ms}ms</li>
                </ul>
              </div>
              <div className="p-4 bg-slate-50 rounded-lg">
                <h4 className="font-medium text-slate-900 mb-2">AI Automation</h4>
                <ul className="text-sm text-slate-600 space-y-1">
                  <li>Max automation level: {config?.ai_safeguards.max_automation_level}</li>
                  <li>Backtesting required: {config?.ai_safeguards.backtesting_required ? 'Yes' : 'No'}</li>
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
