import { useState } from 'react';
import { Card } from './ui';
import { Badge } from './ui';
import { Button } from './ui';
import { ProgressBar } from './ui';
import GlassBarChart from './charts/GlassBarChart';

interface APIKey {
  id: string;
  name: string;
  prefix: string;
  createdAt: string;
  lastUsed: string;
  requests: number;
  enabled: boolean;
}

const MOCK_KEYS: APIKey[] = [
  { id: '1', name: 'Production', prefix: 'q_live_', createdAt: '2026-01-15', lastUsed: '2 min ago', requests: 45230, enabled: true },
  { id: '2', name: 'Staging', prefix: 'q_test_', createdAt: '2026-03-20', lastUsed: '1h ago', requests: 12450, enabled: true },
  { id: '3', name: 'CI/CD Pipeline', prefix: 'q_ci_', createdAt: '2026-06-10', lastUsed: '6h ago', requests: 3200, enabled: false },
];

const USAGE_DATA = [
  { name: 'Mon', api_calls: 4500 },
  { name: 'Tue', api_calls: 5200 },
  { name: 'Wed', api_calls: 4800 },
  { name: 'Thu', api_calls: 6100 },
  { name: 'Fri', api_calls: 5500 },
  { name: 'Sat', api_calls: 1200 },
  { name: 'Sun', api_calls: 800 },
];

export default function APIDashboard() {
  const [keys, setKeys] = useState<APIKey[]>(MOCK_KEYS);
  const [showNewKey, setShowNewKey] = useState(false);

  const totalRequests = keys.reduce((sum, k) => sum + k.requests, 0);
  const limit = 50000;
  const usagePct = Math.min((totalRequests / limit) * 100, 100);

  const revokeKey = (id: string) => {
    setKeys((prev) => prev.map((k) => k.id === id ? { ...k, enabled: false } : k));
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-4">
          <p className="text-xs text-white/50 mb-1">Total API Calls (30d)</p>
          <p className="text-2xl font-bold text-white">{totalRequests.toLocaleString()}</p>
          <ProgressBar value={usagePct} className="mt-2" />
          <p className="text-[10px] text-white/30 mt-1">{(limit - totalRequests).toLocaleString()} remaining</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-white/50 mb-1">Active API Keys</p>
          <p className="text-2xl font-bold text-white">{keys.filter((k) => k.enabled).length}</p>
          <p className="text-[10px] text-white/30 mt-1">of {keys.length} total</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-white/50 mb-1">Rate Limit</p>
          <p className="text-2xl font-bold text-white">2,000</p>
          <p className="text-[10px] text-white/30 mt-1">requests / minute</p>
        </Card>
      </div>

      <GlassBarChart data={USAGE_DATA} xKey="name" yKeys={[{ key: 'api_calls', color: '#3b82f6', name: 'API Calls' }]} height={200} title="Weekly Usage" />

      <Card className="p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-white">API Keys</h3>
          <Button variant="primary" size="sm" onClick={() => setShowNewKey(!showNewKey)}>Generate New Key</Button>
        </div>
        {showNewKey && (
          <div className="p-4 rounded-xl bg-green-500/10 border border-green-500/20 mb-4">
            <p className="text-green-400 text-sm font-medium">New API key generated: q_live_a1b2c3d4e5f6...</p>
            <p className="text-white/50 text-xs mt-1">Copy this key now — it won't be shown again.</p>
          </div>
        )}
        <div className="space-y-2">
          {keys.map((k) => (
            <div key={k.id} className={`p-3 rounded-xl border ${k.enabled ? 'bg-white/[0.03] border-white/10' : 'bg-white/[0.01] border-white/5 opacity-50'}`}>
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-white">{k.name}</span>
                    <Badge variant={k.enabled ? 'success' : 'danger'}>{k.enabled ? 'active' : 'revoked'}</Badge>
                  </div>
                  <p className="text-xs text-white/40 font-mono mt-1">{k.prefix}{'•'.repeat(24)}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-white/60">{k.requests.toLocaleString()} requests</p>
                  <p className="text-[10px] text-white/30">Last used: {k.lastUsed}</p>
                  {k.enabled && (
                    <button onClick={() => revokeKey(k.id)} className="text-[10px] text-red-400/60 hover:text-red-400 mt-1">
                      Revoke
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
