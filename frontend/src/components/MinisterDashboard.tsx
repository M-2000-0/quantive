import React from 'react';
import { FileText } from 'lucide-react';

export default function MinisterDashboard() {
 return (
 <div className="space-y-6 animate-glass-in">
 <div className="flex items-center gap-3">
 <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-violet-600 rounded-xl flex items-center justify-center">
 <span className="text-lg">👤</span>
 </div>
 <div>
 <h2 className="text-xl font-bold text-white">Minister Dashboard</h2>
 <p className="text-sm text-slate-400">Executive view — no charts, just decisions</p>
 </div>
 </div>

 {/* Today */}
 <div className="glass rounded-2xl p-6">
 <h3 className="text-sm font-medium text-indigo-400 mb-4"> <FileText className="w-4 h-4 inline" /> TODAY</h3>
 <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
 <div className="bg-green-500/10 rounded-xl p-4 text-center">
 <p className="text-3xl font-bold text-green-400">$420M</p>
 <p className="text-xs text-slate-400 mt-1">Potential Savings</p>
 </div>
 <div className="bg-red-500/10 rounded-xl p-4 text-center">
 <p className="text-3xl font-bold text-red-400">2</p>
 <p className="text-xs text-slate-400 mt-1">Critical Risks</p>
 </div>
 <div className="bg-amber-500/10 rounded-xl p-4 text-center">
 <p className="text-3xl font-bold text-amber-400">$8.3B</p>
 <p className="text-xs text-slate-400 mt-1">Upcoming Maturities</p>
 </div>
 <div className="bg-blue-500/10 rounded-xl p-4 text-center">
 <p className="text-3xl font-bold text-blue-400">3</p>
 <p className="text-xs text-slate-400 mt-1">Recommended Actions</p>
 </div>
 </div>
 </div>

 {/* Recommended Actions */}
 <div className="glass rounded-2xl p-6">
 <h3 className="text-sm font-medium text-slate-400 mb-4">RECOMMENDED ACTIONS</h3>
 <div className="space-y-3">
 {[
 { priority: 'Critical', title: 'Approve $2.4B 2027 Refinancing Plan', impact: 'Saves $180M annually', deadline: 'Requires decision by Aug 28' },
 { priority: 'High', title: 'Authorize 60% FX Hedge on USD Exposure', impact: 'Reduces FX risk by $320M', deadline: 'Requires decision by Sep 1' },
 { priority: 'Medium', title: 'Update Green Bond Framework', impact: 'Meets ESG targets, attracts ESG investors', deadline: 'Decision by Sep 15' },
 ].map((action, i) => (
 <div key={i} className={`flex items-center gap-4 p-4 rounded-xl border ${
 action.priority === 'Critical' ? 'bg-red-500/5 border-red-500/20' :
 action.priority === 'High' ? 'bg-orange-500/5 border-orange-500/20' :
 'bg-white/5 border-white/10'
 }`}>
 <span className={`px-2 py-1 rounded text-xs font-bold ${
 action.priority === 'Critical' ? 'bg-red-500/20 text-red-400' :
 action.priority === 'High' ? 'bg-orange-500/20 text-orange-400' :
 'bg-yellow-500/20 text-yellow-400'
 }`}>
 {action.priority}
 </span>
 <div className="flex-1">
 <h4 className="text-white font-medium">{action.title}</h4>
 <p className="text-xs text-slate-400">{action.impact}</p>
 </div>
 <span className="text-xs text-slate-500">{action.deadline}</span>
 </div>
 ))}
 </div>
 </div>

 {/* Next 12 Months */}
 <div className="glass rounded-2xl p-6">
 <h3 className="text-sm font-medium text-slate-400 mb-4">NEXT 12 MONTHS</h3>
 <div className="grid grid-cols-3 gap-4">
 <div className="bg-white/5 rounded-xl p-4">
 <h4 className="text-xs text-slate-500 mb-2">FUNDING NEED</h4>
 <p className="text-2xl font-bold text-white">$12.4B</p>
 <p className="text-xs text-slate-400 mt-1">Across 4 issuances</p>
 </div>
 <div className="bg-white/5 rounded-xl p-4">
 <h4 className="text-xs text-slate-500 mb-2">RISK FORECAST</h4>
 <p className="text-2xl font-bold text-yellow-400">Moderate</p>
 <p className="text-xs text-slate-400 mt-1">2 critical, 3 watch items</p>
 </div>
 <div className="bg-white/5 rounded-xl p-4">
 <h4 className="text-xs text-slate-500 mb-2">CONFIDENCE</h4>
 <p className="text-2xl font-bold text-green-400">91%</p>
 <p className="text-xs text-slate-400 mt-1">High confidence in projections</p>
 </div>
 </div>
 </div>

 {/* One-Click Reports */}
 <div className="glass rounded-2xl p-6">
 <h3 className="text-sm font-medium text-slate-400 mb-4">ONE-CLICK REPORTS</h3>
 <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
 {[
 { icon: 'FileText', label: 'Executive Brief', desc: '2-page summary' },
 { icon: 'BarChart3', label: 'Board Presentation', desc: '15-slide deck' },
 { icon: 'FileText', label: 'IMF Compliance', desc: 'DSA report' },
 { icon: 'TrendingUp', label: 'Investor Update', desc: 'Market-facing' },
 ].map((report, i) => (
 <button key={i} className="p-4 bg-white/5 rounded-xl text-left hover:bg-white/10 transition-colors">
 <span className="text-2xl mb-2 block">{report.icon}</span>
 <h4 className="text-white text-sm font-medium">{report.label}</h4>
 <p className="text-xs text-slate-500">{report.desc}</p>
 </button>
 ))}
 </div>
 </div>
 </div>
 );
}
