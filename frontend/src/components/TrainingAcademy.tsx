import React, { useState } from 'react';

interface Course {
  id: string;
  title: string;
  category: 'user' | 'admin' | 'developer' | 'analyst';
  duration: string;
  level: 'beginner' | 'intermediate' | 'advanced';
  modules: number;
  status: 'available' | 'coming_soon';
}

const COURSES: Course[] = [
  { id: 'c1', title: 'Quantive Fundamentals', category: 'user', duration: '8 hours', level: 'beginner', modules: 12, status: 'available' },
  { id: 'c2', title: 'Portfolio Optimization', category: 'analyst', duration: '16 hours', level: 'intermediate', modules: 20, status: 'available' },
  { id: 'c3', title: 'Advanced Risk Modeling', category: 'analyst', duration: '24 hours', level: 'advanced', modules: 18, status: 'available' },
  { id: 'c4', title: 'System Administration', category: 'admin', duration: '20 hours', level: 'advanced', modules: 15, status: 'available' },
  { id: 'c5', title: 'API Integration', category: 'developer', duration: '12 hours', level: 'intermediate', modules: 10, status: 'available' },
  { id: 'c6', title: 'Compliance Reporting', category: 'user', duration: '10 hours', level: 'beginner', modules: 8, status: 'available' },
  { id: 'c7', title: 'Crisis Management', category: 'admin', duration: '8 hours', level: 'advanced', modules: 6, status: 'coming_soon' },
  { id: 'c8', title: 'Model Governance', category: 'admin', duration: '6 hours', level: 'intermediate', modules: 8, status: 'coming_soon' },
];

const CATEGORY_INFO: Record<string, { icon: string; color: string }> = {
  user: { icon: '👤', color: 'blue' },
  admin: { icon: 'Settings', color: 'purple' },
  developer: { icon: '💻', color: 'green' },
  analyst: { icon: 'BarChart3', color: 'amber' } };

export default function TrainingAcademy() {
  const [filter, setFilter] = useState<string>('all');
  const filtered = filter === 'all' ? COURSES : COURSES.filter(c => c.category === filter);

  return (
    <div className="space-y-6 animate-glass-in">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center">
          <span className="text-lg">🎓</span>
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">Quantive Academy</h2>
          <p className="text-sm text-slate-400">Training materials, certifications, and documentation</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="glass rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-white">{COURSES.length}</p>
          <p className="text-xs text-slate-400">Total Courses</p>
        </div>
        <div className="glass rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-green-400">{COURSES.filter(c => c.status === 'available').length}</p>
          <p className="text-xs text-slate-400">Available Now</p>
        </div>
        <div className="glass rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-white">97</p>
          <p className="text-xs text-slate-400">Total Modules</p>
        </div>
        <div className="glass rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-white">104h</p>
          <p className="text-xs text-slate-400">Total Hours</p>
        </div>
      </div>

      {/* Filter */}
      <div className="flex gap-2">
        <button onClick={() => setFilter('all')} className={`px-3 py-1.5 rounded-lg text-xs font-medium ${filter === 'all' ? 'bg-white/20 text-white' : 'bg-white/5 text-slate-400'}`}>All</button>
        {Object.entries(CATEGORY_INFO).map(([key, info]) => (
          <button key={key} onClick={() => setFilter(key)} className={`px-3 py-1.5 rounded-lg text-xs font-medium ${filter === key ? 'bg-white/20 text-white' : 'bg-white/5 text-slate-400'}`}>
            {info.icon} {key}
          </button>
        ))}
      </div>

      {/* Courses */}
      <div className="grid grid-cols-2 gap-4">
        {filtered.map(c => (
          <div key={c.id} className={`glass rounded-xl p-5 ${c.status === 'coming_soon' ? 'opacity-60' : ''}`}>
            <div className="flex items-center justify-between mb-3">
              <span className={`px-2 py-0.5 rounded text-xs bg-${CATEGORY_INFO[c.category]?.color}-500/20 text-${CATEGORY_INFO[c.category]?.color}-400`}>
                {CATEGORY_INFO[c.category]?.icon} {c.category}
              </span>
              <span className={`px-2 py-0.5 rounded text-xs ${
                c.level === 'beginner' ? 'bg-green-500/20 text-green-400' :
                c.level === 'intermediate' ? 'bg-yellow-500/20 text-yellow-400' :
                'bg-red-500/20 text-red-400'
              }`}>
                {c.level}
              </span>
            </div>
            <h4 className="text-white font-medium mb-2">{c.title}</h4>
            <div className="flex items-center gap-4 text-xs text-slate-500">
              <span>⏱️ {c.duration}</span>
              <span>📚 {c.modules} modules</span>
            </div>
            {c.status === 'coming_soon' && (
              <span className="mt-2 inline-block px-2 py-0.5 bg-slate-500/20 text-slate-400 rounded text-xs">Coming Soon</span>
            )}
          </div>
        ))}
      </div>

      {/* Documentation */}
      <div className="glass rounded-2xl p-6">
        <h3 className="text-sm font-medium text-slate-400 mb-4">DOCUMENTATION</h3>
        <div className="grid grid-cols-3 gap-4">
          {[
            { icon: '📖', title: 'User Manual', desc: 'Complete user guide (PDF)' },
            { icon: 'Settings', title: 'Admin Guide', desc: 'System administration manual' },
            { icon: '💻', title: 'API Reference', desc: 'REST API documentation' },
          ].map((d, i) => (
            <button key={i} className="p-4 bg-white/5 rounded-xl text-left hover:bg-white/10 transition-colors">
              <span className="text-2xl mb-2 block">{d.icon}</span>
              <h4 className="text-white text-sm font-medium">{d.title}</h4>
              <p className="text-xs text-slate-500">{d.desc}</p>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
