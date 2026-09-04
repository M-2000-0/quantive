import React, { useState } from 'react';
import { Search } from 'lucide-react';

interface Dependency {
  name: string;
  version: string;
  license: string;
  category: 'core' | 'ui' | 'data' | 'security' | 'utility';
  vulnerabilities: number;
  status: 'clean' | 'advisory' | 'vulnerable';
}

const DEPENDENCIES: Dependency[] = [
  { name: 'react', version: '18.3.1', license: 'MIT', category: 'ui', vulnerabilities: 0, status: 'clean' },
  { name: 'react-router-dom', version: '6.26.0', license: 'MIT', category: 'ui', vulnerabilities: 0, status: 'clean' },
  { name: 'zustand', version: '4.5.4', license: 'MIT', category: 'core', vulnerabilities: 0, status: 'clean' },
  { name: 'recharts', version: '2.12.7', license: 'MIT', category: 'ui', vulnerabilities: 0, status: 'clean' },
  { name: 'vitest', version: '4.1.11', license: 'MIT', category: 'utility', vulnerabilities: 0, status: 'clean' },
  { name: 'typescript', version: '5.5.3', license: 'Apache-2.0', category: 'utility', vulnerabilities: 0, status: 'clean' },
  { name: 'tailwindcss', version: '3.4.7', license: 'MIT', category: 'ui', vulnerabilities: 0, status: 'clean' },
  { name: '@sentry/react', version: '8.24.0', license: 'BSD-3-Clause', category: 'security', vulnerabilities: 0, status: 'clean' },
  { name: 'i18next', version: '23.14.0', license: 'MIT', category: 'utility', vulnerabilities: 0, status: 'clean' },
  { name: 'date-fns', version: '3.6.0', license: 'MIT', category: 'utility', vulnerabilities: 0, status: 'clean' },
];

const CATEGORY_COLORS: Record<string, string> = {
  core: 'bg-blue-500/20 text-blue-400',
  ui: 'bg-purple-500/20 text-purple-400',
  data: 'bg-green-500/20 text-green-400',
  security: 'bg-red-500/20 text-red-400',
  utility: 'bg-slate-500/20 text-slate-400' };

export default function SourceCodeInspection() {
  const [selected, setSelected] = useState<Dependency | null>(null);
  const [filter, setFilter] = useState<string>('all');

  const filtered = filter === 'all' ? DEPENDENCIES : DEPENDENCIES.filter(d => d.category === filter);
  const totalVulns = DEPENDENCIES.reduce((sum, d) => sum + d.vulnerabilities, 0);

  return (
    <div className="space-y-6 animate-glass-in">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-gradient-to-br from-slate-500 to-gray-600 rounded-xl flex items-center justify-center">
          <Search className="w-5 h-5" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">Source Code Inspection</h2>
          <p className="text-sm text-slate-400">SBOM, dependency audit, and license inventory for government review</p>
        </div>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-4 gap-4">
        <div className="glass rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-white">{DEPENDENCIES.length}</p>
          <p className="text-xs text-slate-400">Dependencies</p>
        </div>
        <div className="glass rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-green-400">{DEPENDENCIES.filter(d => d.status === 'clean').length}</p>
          <p className="text-xs text-slate-400">Clean</p>
        </div>
        <div className="glass rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-red-400">{totalVulns}</p>
          <p className="text-xs text-slate-400">Vulnerabilities</p>
        </div>
        <div className="glass rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-white">MIT/Apache</p>
          <p className="text-xs text-slate-400">All Licenses</p>
        </div>
      </div>

      {/* Escrow & Review */}
      <div className="glass rounded-2xl p-5">
        <h3 className="text-sm font-medium text-slate-400 mb-4">SOURCE CODE ACCESS OPTIONS</h3>
        <div className="grid grid-cols-3 gap-4">
          {[
            { icon: '💾', title: 'Source Code Escrow', desc: 'Full source deposited with Iron Mountain. Released on company dissolution.' },
            { icon: 'FileText', title: 'SBOM Export', desc: 'Machine-readable SBOM (CycloneDX format) with every release.' },
            { icon: 'Search', title: 'Code Review Access', desc: 'Read-only access to repository for authorized government auditors.' },
          ].map((opt, i) => (
            <div key={i} className="bg-white/5 rounded-xl p-4">
              <span className="text-2xl mb-2 block">{opt.icon}</span>
              <h4 className="text-white text-sm font-medium mb-1">{opt.title}</h4>
              <p className="text-xs text-slate-500">{opt.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Dependencies */}
      <div className="glass rounded-2xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium text-slate-400">DEPENDENCY INVENTORY</h3>
          <div className="flex gap-2">
            <button onClick={() => setFilter('all')} className={`px-2 py-1 rounded text-xs ${filter === 'all' ? 'bg-white/20 text-white' : 'bg-white/5 text-slate-400'}`}>All</button>
            {Object.keys(CATEGORY_COLORS).map(c => (
              <button key={c} onClick={() => setFilter(c)} className={`px-2 py-1 rounded text-xs ${filter === c ? 'bg-white/20 text-white' : 'bg-white/5 text-slate-400'}`}>{c}</button>
            ))}
          </div>
        </div>
        <div className="space-y-1">
          {filtered.map((d, i) => (
            <button key={i} onClick={() => setSelected(d)} className={`w-full text-left flex items-center gap-4 p-2 rounded-lg transition-all ${selected?.name === d.name ? 'bg-white/10' : 'hover:bg-white/5'}`}>
              <span className={`px-1.5 py-0.5 rounded text-xs ${CATEGORY_COLORS[d.category]}`}>{d.category}</span>
              <span className="text-white text-sm flex-1 font-mono">{d.name}@{d.version}</span>
              <span className="text-xs text-slate-400">{d.license}</span>
              <span className={`text-xs ${d.status === 'clean' ? 'text-green-400' : 'text-red-400'}`}>
                {d.vulnerabilities === 0 ? '✓ Clean' : `${d.vulnerabilities} CVE`}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
