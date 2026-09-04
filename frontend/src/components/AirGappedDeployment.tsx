import React, { useState } from 'react';
import { Lock } from 'lucide-react';

interface DeploymentOption {
  id: string;
  name: string;
  icon: string;
  description: string;
  status: 'available' | 'beta' | 'planned';
  features: string[];
  securityLevel: string;
  estimatedCost: string;
  timeline: string;
}

const DEPLOYMENT_OPTIONS: DeploymentOption[] = [
  {
    id: 'airgapped',
    name: 'Air-Gapped Deployment',
    icon: 'Lock',
    description: 'Fully isolated network with zero internet connectivity. Hardware security modules for key management.',
    status: 'available',
    features: ['Zero internet connectivity', 'HSM key storage', 'Smart card authentication', 'Manual data import/export', 'Physical security controls', 'Dedicated hardware'],
    securityLevel: 'Top Secret',
    estimatedCost: '$2.5M - $5M',
    timeline: '8-12 weeks' },
  {
    id: 'onprem',
    name: 'On-Premise Private Cloud',
    icon: 'Building2',
    description: 'Deployed within government datacenter. Full control over infrastructure, data, and network.',
    status: 'available',
    features: ['Government-controlled network', 'Local data storage', 'Custom security policies', 'VPN/专线 access', 'On-site support option', 'Custom integrations'],
    securityLevel: 'Classified',
    estimatedCost: '$1.5M - $3M',
    timeline: '6-10 weeks' },
  {
    id: 'sovereign',
    name: 'Sovereign Cloud',
    icon: 'Building2',
    description: 'Dedicated cloud environment in-country. AWS GovCloud, Azure Government, or sovereign datacenter.',
    status: 'available',
    features: ['In-country data residency', 'Government cloud providers', 'FIPS 140-2 compliance', 'Dedicated tenancy', 'Government-controlled encryption', 'Audit logging'],
    securityLevel: 'Confidential',
    estimatedCost: '$800K - $1.5M',
    timeline: '4-6 weeks' },
  {
    id: 'hybrid',
    name: 'Hybrid Deployment',
    icon: '🔗',
    description: 'Sensitive data on-premise, analytics in cloud. Balances security with functionality.',
    status: 'available',
    features: ['Data classification controls', 'Secure data bridge', 'Cloud analytics on anonymized data', 'On-premise key management', 'Selective sync', 'Fallback to local mode'],
    securityLevel: 'Confidential',
    estimatedCost: '$600K - $1.2M',
    timeline: '4-8 weeks' },
  {
    id: 'selfhosted',
    name: 'Self-Hosted Container',
    icon: 'Package',
    description: 'Docker/Kubernetes deployment for government DevOps teams. Full source code access.',
    status: 'beta',
    features: ['Full source code access', 'Docker/K8s native', 'Custom CI/CD pipelines', 'Government DevOps integration', 'Container security scanning', 'Custom monitoring'],
    securityLevel: 'Varies',
    estimatedCost: '$400K - $800K',
    timeline: '2-4 weeks' },
  {
    id: 'classified',
    name: 'Classified Network Deployment',
    icon: 'Shield',
    description: 'Deployed on classified government networks (SIPRNet, JWICS, equivalent). Maximum security.',
    status: 'planned',
    features: ['Cross-domain guards', 'Data diodes', 'Hardware isolation', 'Air-gap verification', 'Tamper-evident hardware', 'Physical security compliance'],
    securityLevel: 'Top Secret/SCI',
    estimatedCost: 'Custom',
    timeline: '12-16 weeks' },
];

const STATUS_COLORS: Record<string, string> = {
  available: 'bg-green-500/20 text-green-400',
  beta: 'bg-yellow-500/20 text-yellow-400',
  planned: 'bg-slate-500/20 text-slate-400' };

export default function AirGappedDeployment() {
  const [selected, setSelected] = useState<DeploymentOption | null>(null);

  return (
    <div className="space-y-6 animate-glass-in">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-gradient-to-br from-slate-600 to-gray-700 rounded-xl flex items-center justify-center">
          <Lock className="w-5 h-5" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">Deployment Options</h2>
          <p className="text-sm text-slate-400">Air-gapped, on-premise, sovereign cloud, and classified network support</p>
        </div>
      </div>

      {/* Deployment Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        {DEPLOYMENT_OPTIONS.map(opt => (
          <button
            key={opt.id}
            onClick={() => setSelected(opt)}
            className={`text-left p-5 rounded-2xl border transition-all ${
              selected?.id === opt.id
                ? 'bg-slate-500/10 border-slate-500/30'
                : 'bg-white/5 border-white/10 hover:bg-white/10'
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-3xl">{opt.icon}</span>
              <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[opt.status]}`}>
                {opt.status}
              </span>
            </div>
            <h4 className="text-white font-medium mb-1">{opt.name}</h4>
            <p className="text-xs text-slate-400 mb-3">{opt.description}</p>
            <div className="space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-slate-500">Security Level</span>
                <span className="text-white">{opt.securityLevel}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-500">Cost</span>
                <span className="text-white">{opt.estimatedCost}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-500">Timeline</span>
                <span className="text-white">{opt.timeline}</span>
              </div>
            </div>
          </button>
        ))}
      </div>

      {/* Detail */}
      {selected && (
        <div className="glass rounded-2xl p-6 space-y-4">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <span className="text-4xl">{selected.icon}</span>
              <div>
                <h3 className="text-lg font-bold text-white">{selected.name}</h3>
                <p className="text-sm text-slate-400">{selected.description}</p>
              </div>
            </div>
            <span className={`px-3 py-1 rounded-lg text-xs font-medium ${STATUS_COLORS[selected.status]}`}>
              {selected.status.toUpperCase()}
            </span>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="bg-white/5 rounded-xl p-3 text-center">
              <p className="text-xs text-slate-500">Security Level</p>
              <p className="text-lg font-bold text-white">{selected.securityLevel}</p>
            </div>
            <div className="bg-white/5 rounded-xl p-3 text-center">
              <p className="text-xs text-slate-500">Estimated Cost</p>
              <p className="text-lg font-bold text-white">{selected.estimatedCost}</p>
            </div>
            <div className="bg-white/5 rounded-xl p-3 text-center">
              <p className="text-xs text-slate-500">Deployment Timeline</p>
              <p className="text-lg font-bold text-white">{selected.timeline}</p>
            </div>
          </div>

          <div>
            <h4 className="text-xs font-medium text-slate-500 mb-3">FEATURES</h4>
            <div className="grid grid-cols-2 gap-2">
              {selected.features.map((f, i) => (
                <div key={i} className="flex items-center gap-2 text-sm text-slate-300">
                  <span className="text-green-400">✓</span>
                  {f}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
