import { useState } from 'react';
import { MOCK_API_KEYS, type ApiKeyConfig } from '../lib/purchaseData';
import { TriangleAlert as AlertTriangle } from 'lucide-react';

const STATUS_CONFIG: Record<string, { color: string; icon: string; label: string }> = {
 connected: { color: 'text-emerald-600', icon: 'CheckCircle', label: 'Connected' },
 expiring: { color: 'text-amber-600', icon: 'AlertTriangle', label: 'Expiring Soon' },
 failed: { color: 'text-red-600', icon: 'XCircle', label: 'Failed' },
 not_configured: { color: 'text-slate-400', icon: '○', label: 'Not Configured' } };

export default function ApiKeyManager() {
  const [apiKeys, setApiKeys] = useState<ApiKeyConfig[]>(MOCK_API_KEYS);
 const [testingId, setTestingId] = useState<string | null>(null);
 const [showAddModal, setShowAddModal] = useState(false);

 const handleTestConnection = async (id: string) => {
 setTestingId(id);
 // Simulate connection test
 await new Promise((r) => setTimeout(r, 1500));
 setTestingId(null);
 };

 const handleRevoke = (id: string) => {
 setApiKeys((prev) =>
 prev.map((k) => (k.id === id ? { ...k, status: 'not_configured' as const, keyPrefix: undefined, lastSync: undefined, expiresAt: undefined } : k))
 );
 };

 return (
 <div className="space-y-4">
 <div className="flex items-center justify-between">
 <div>
 <h3 className="text-lg font-bold text-slate-900">API Connections</h3>
 <p className="text-sm text-slate-500">Manage your data provider integrations</p>
 </div>
 <button
 onClick={() => setShowAddModal(true)}
 className="px-3 py-1.5 text-xs font-medium rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-md hover:shadow-lg transition-all"
 >
 + Connect Service
 </button>
 </div>

 <div className="grid grid-cols-1 gap-3">
 {apiKeys.map((apiKey) => {
 const status = STATUS_CONFIG[apiKey.status];
 const isExpiring = apiKey.status === 'expiring' && apiKey.expiresAt;
 const daysUntilExpiry = isExpiring
 ? Math.max(0, Math.ceil((new Date(apiKey.expiresAt!).getTime() - Date.now()) / (1000 * 60 * 60 * 24)))
 : null;

 return (
 <div key={apiKey.id} className="glass rounded-2xl p-4 hover:shadow-md transition-all">
 <div className="flex items-start justify-between">
 <div className="flex items-start gap-3">
 <div className="text-2xl">{apiKey.icon}</div>
 <div>
 <div className="flex items-center gap-2">
 <span className="font-semibold text-slate-900">{apiKey.displayName}</span>
 <span className={`text-xs font-medium ${status.color}`}>
 {status.icon} {status.label}
 </span>
 </div>
 <p className="text-sm text-slate-500 mt-0.5">{apiKey.description}</p>
 <div className="flex flex-wrap gap-1 mt-2">
  {(apiKey.services || []).map((svc) => (
 <span key={svc} className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium bg-slate-100 text-slate-600">
 {svc}
 </span>
 ))}
 </div>
 {apiKey.keyPrefix && (
 <div className="text-xs text-slate-400 mt-2 font-mono">Key: {apiKey.keyPrefix}</div>
 )}
 <div className="flex items-center gap-3 mt-2 text-xs text-slate-500">
 {apiKey.lastSync && (
 <span>Last sync: {new Date(apiKey.lastSync).toLocaleDateString()}</span>
 )}
 {daysUntilExpiry !== null && daysUntilExpiry <= 7 && (
 <span className="text-amber-600 font-medium">
 <AlertTriangle className="w-4 h-4 inline" /> Expires in {daysUntilExpiry} days
 </span>
 )}
 </div>
 </div>
 </div>

 <div className="flex items-center gap-2">
 {apiKey.status !== 'not_configured' && (
 <button
 onClick={() => handleTestConnection(apiKey.id)}
 disabled={testingId === apiKey.id}
 className="glass-button px-3 py-1.5 text-xs font-medium disabled:opacity-50"
 >
 {testingId === apiKey.id ? (
 <span className="flex items-center gap-1">
 <span className="animate-spin">⏳</span> Testing...
 </span>
 ) : (
 'Test Connection'
 )}
 </button>
 )}
 {apiKey.status === 'not_configured' ? (
 <button className="px-3 py-1.5 text-xs font-medium rounded-xl bg-blue-600/14 text-blue-700 hover:bg-blue-600/20 transition-all">
 Configure
 </button>
 ) : (
 <button
 onClick={() => handleRevoke(apiKey.id)}
 className="px-3 py-1.5 text-xs font-medium rounded-xl bg-red-600/14 text-red-700 hover:bg-red-600/20 transition-all"
 >
 Revoke
 </button>
 )}
 </div>
 </div>
 </div>
 );
 })}
 </div>

 {/* Add Modal Placeholder */}
 {showAddModal && (
 <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm" onClick={() => setShowAddModal(false)}>
 <div className="glass rounded-2xl p-6 w-full max-w-md animate-glass-in" onClick={(e) => e.stopPropagation()}>
 <h3 className="text-lg font-bold text-slate-900 mb-4">Connect a Data Provider</h3>
 <p className="text-sm text-slate-600 mb-4">
 Select a provider below and enter your API key. Keys are encrypted at rest with AES-256.
 </p>
 <div className="space-y-2">
 {['Bloomberg', 'Refinitiv', 'FRED', 'Morningstar', 'ICE Data', 'FactSet', 'S&P Capital IQ'].map((name) => (
 <button
 key={name}
 className="w-full glass p-3 rounded-xl text-left text-sm font-medium text-slate-700 hover:bg-white/60 transition-all"
 >
 + {name}
 </button>
 ))}
 </div>
 <button
 onClick={() => setShowAddModal(false)}
 className="mt-4 w-full glass-button py-2 text-sm font-medium"
 >
 Cancel
 </button>
 </div>
 </div>
 )}
 </div>
 );
}
