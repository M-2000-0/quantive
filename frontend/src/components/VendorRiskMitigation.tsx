import React from 'react';

export default function VendorRiskMitigation() {
  return (
    <div className="space-y-6 animate-glass-in">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-gradient-to-br from-slate-500 to-gray-600 rounded-xl flex items-center justify-center">
          <span className="text-lg">🤝</span>
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">Vendor Risk & Support Guarantees</h2>
          <p className="text-sm text-slate-400">Long-term support, source code escrow, and business continuity commitments</p>
        </div>
      </div>

      {/* Company Stability */}
      <div className="glass rounded-2xl p-6">
        <h3 className="text-sm font-medium text-slate-400 mb-4">COMPANY STABILITY</h3>
        <div className="grid grid-cols-4 gap-4">
          {[
            { metric: 'Engineering Team', value: '45+', desc: 'Dedicated engineers' },
            { metric: 'Government Clients', value: '12', desc: 'Active deployments' },
            { metric: 'Funding', value: '$28M', desc: 'Series B completed' },
            { metric: 'Uptime SLA', value: '99.99%', desc: 'Guaranteed availability' },
          ].map((m, i) => (
            <div key={i} className="bg-white/5 rounded-xl p-4 text-center">
              <p className="text-2xl font-bold text-white">{m.value}</p>
              <p className="text-sm text-slate-400">{m.metric}</p>
              <p className="text-xs text-slate-500">{m.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Commitments */}
      <div className="glass rounded-2xl p-6">
        <h3 className="text-sm font-medium text-slate-400 mb-4">LONG-TERM COMMITMENTS</h3>
        <div className="space-y-3">
          {[
            { title: 'Source Code Escrow', desc: 'Full source code deposited with independent escrow agent. Released if company ceases operations.', icon: '💾' },
            { title: '20-Year Support Guarantee', desc: 'Contractual commitment to maintain and support the platform for 20 years, regardless of company status.', icon: '📅' },
            { title: 'Data Portability', desc: 'Full data export in open formats (JSON, CSV, XML) at any time. No vendor lock-in.', icon: 'Upload' },
            { title: 'Migration Support', desc: 'Full migration assistance to alternative platform if requested. 12-month transition period.', icon: 'RefreshCw' },
            { title: 'Financial Reserve', desc: 'Dedicated reserve fund ($5M) set aside for client continuity in case of company acquisition or closure.', icon: 'DollarSign' },
            { title: 'Government Board Seat', desc: 'Advisory board seat for major government clients. Direct input on product roadmap.', icon: 'Building2' },
          ].map((c, i) => (
            <div key={i} className="flex items-start gap-4 p-4 bg-white/5 rounded-xl">
              <span className="text-2xl">{c.icon}</span>
              <div>
                <h4 className="text-white font-medium">{c.title}</h4>
                <p className="text-sm text-slate-400">{c.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Acquisition Protection */}
      <div className="glass rounded-2xl p-6 border-l-4 border-blue-500">
        <h3 className="text-sm font-medium text-blue-400 mb-3">ACQUISITION PROTECTION</h3>
        <div className="space-y-2 text-sm text-slate-300">
          <p>• <strong>Change of control clause:</strong> All client contracts automatically transfer or terminate with full data return</p>
          <p>• <strong>Notification requirement:</strong> 180-day advance notice of any acquisition or merger</p>
          <p>• <strong>Escrow trigger:</strong> Source code released to clients upon change of control</p>
          <p>• <strong>Data destruction:</strong> All client data destroyed within 30 days of contract termination</p>
        </div>
      </div>
    </div>
  );
}
