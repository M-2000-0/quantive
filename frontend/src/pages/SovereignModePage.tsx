import { useCallback, useEffect, useState } from 'react';
import {
  Shield, Lock, Eye, Server, Database, Key, CheckCircle,
  AlertTriangle, Globe, Cpu, HardDrive
} from 'lucide-react';
import { api } from '../api';

interface SovereignModeStatus {
  enabled: boolean;
  activated_at: string | null;
  security_level: string;
  features: string[];
}

interface SecurityChecklistItem {
  id: string;
  name: string;
  description: string;
  status: string;
  last_verified: string | null;
}

export default function SovereignModePage() {
  const [config, setConfig] = useState<SovereignModeStatus | null>(null);
  const [checklist, setChecklist] = useState<SecurityChecklistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'checklist' | 'settings'>('overview');

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [configData, checklistData] = await Promise.all([
        api.sovereignMode.status().catch(() => null),
        api.sovereignMode.securityChecklist().catch(() => null),
      ]);

      if (configData) setConfig(configData);
      if (checklistData?.checklist) {
        const allItems = checklistData.checklist.flatMap((cat: any) => cat.items || []);
        setChecklist(allItems);
      }
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

  const totalItems = checklist.length;
  const metItems = checklist.filter(i => i.status === 'met' || i.status === 'passed').length;

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
          config?.enabled
            ? 'bg-gradient-to-r from-emerald-600 to-emerald-700 text-white'
            : 'bg-gradient-to-r from-amber-500 to-amber-600 text-white'
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {config?.enabled ? (
                <CheckCircle className="w-10 h-10" />
              ) : (
                <AlertTriangle className="w-10 h-10" />
              )}
              <div>
                <div className="text-2xl font-bold">
                  Mode: {config?.enabled ? `Sovereign (${config.security_level})` : 'Standard'}
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
                  <Shield className="w-5 h-5 text-blue-600" />
                </div>
                <h3 className="font-medium text-slate-900">Status</h3>
              </div>
              <ul className="space-y-2 text-sm">
                <li className="flex items-center gap-2">
                  {config?.enabled ? (
                    <CheckCircle className="w-4 h-4 text-emerald-500" />
                  ) : (
                    <AlertTriangle className="w-4 h-4 text-red-500" />
                  )}
                  <span>Enabled: {config?.enabled ? 'Yes' : 'No'}</span>
                </li>
                <li className="flex items-center gap-2">
                  <Globe className="w-4 h-4 text-slate-400" />
                  <span>Security Level: {config?.security_level || 'Standard'}</span>
                </li>
                <li className="flex items-center gap-2">
                  <Lock className="w-4 h-4 text-slate-400" />
                  <span>Activated: {config?.activated_at ? new Date(config.activated_at).toLocaleDateString() : 'Never'}</span>
                </li>
              </ul>
            </div>

            <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center">
                  <CheckCircle className="w-5 h-5 text-emerald-600" />
                </div>
                <h3 className="font-medium text-slate-900">Features</h3>
              </div>
              <ul className="space-y-2 text-sm">
                {config?.features?.map((feature, idx) => (
                  <li key={idx} className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-emerald-500" />
                    <span>{feature}</span>
                  </li>
                )) || (
                  <li className="text-slate-500">No features configured</li>
                )}
              </ul>
            </div>

            <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-amber-100 rounded-lg flex items-center justify-center">
                  <Lock className="w-5 h-5 text-amber-600" />
                </div>
                <h3 className="font-medium text-slate-900">Compliance</h3>
              </div>
              <ul className="space-y-2 text-sm">
                <li className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-500" />
                  <span>Security Score: {Math.round((metItems / totalItems) * 100)}%</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-500" />
                  <span>{metItems}/{totalItems} items passed</span>
                </li>
              </ul>
            </div>

            <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                  <Database className="w-5 h-5 text-purple-600" />
                </div>
                <h3 className="font-medium text-slate-900">Checklist</h3>
              </div>
              <ul className="space-y-2 text-sm">
                {checklist.slice(0, 4).map((item, idx) => (
                  <li key={idx} className="flex items-center gap-2">
                    {item.status === 'passed' || item.status === 'met' ? (
                      <CheckCircle className="w-4 h-4 text-emerald-500" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-amber-500" />
                    )}
                    <span>{item.name}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {activeTab === 'checklist' && (
          <div className="space-y-4">
            <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-200">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-slate-900">Security Checklist</h3>
                <span className="text-sm text-slate-500">{metItems}/{totalItems} items passed</span>
              </div>
              <div className="space-y-2">
                {checklist.map((item, idx) => (
                  <div
                    key={idx}
                    className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg"
                  >
                    {item.status === 'passed' || item.status === 'met' ? (
                      <CheckCircle className="w-4 h-4 text-emerald-500 mt-0.5" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-amber-500 mt-0.5" />
                    )}
                    <div>
                      <div className="font-medium text-slate-900 text-sm">{item.name}</div>
                      <div className="text-xs text-slate-500">{item.description}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
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
                <h4 className="font-medium text-slate-900 mb-2">Status</h4>
                <ul className="text-sm text-slate-600 space-y-1">
                  <li>Enabled: {config?.enabled ? 'Yes' : 'No'}</li>
                  <li>Security Level: {config?.security_level || 'Standard'}</li>
                  <li>Activated: {config?.activated_at ? new Date(config.activated_at).toLocaleDateString() : 'Never'}</li>
                </ul>
              </div>
              <div className="p-4 bg-slate-50 rounded-lg">
                <h4 className="font-medium text-slate-900 mb-2">Features</h4>
                <ul className="text-sm text-slate-600 space-y-1">
                  {config?.features?.map((feature, idx) => (
                    <li key={idx}>{feature}</li>
                  )) || <li>No features configured</li>}
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
