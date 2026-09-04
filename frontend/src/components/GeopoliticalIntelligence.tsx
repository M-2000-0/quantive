import React, { useState } from 'react';
import { ChartColumn as BarChart3, Globe } from 'lucide-react';

interface GeopoliticalEvent {
 id: string;
 title: string;
 category: 'sanctions' | 'trade_war' | 'commodity_shock' | 'military' | 'supply_chain' | 'energy' | 'cyber';
 severity: 'critical' | 'high' | 'medium' | 'low';
 region: string;
 date: string;
 description: string;
 portfolioImpact: number;
 affectedSectors: string[];
 affectedCurrencies: string[];
 recommendedActions: string[];
 status: 'active' | 'monitoring' | 'resolved';
}

const EVENTS: GeopoliticalEvent[] = [
 {
 id: 'geo-001',
 title: 'Expanded Sanctions on Energy Sector',
 category: 'sanctions',
 severity: 'critical',
 region: 'Eastern Europe',
 date: '2026-08-24',
 description: 'New sanctions targeting energy imports from major supplier. Direct impact on sovereign bonds denominated in affected currency.',
 portfolioImpact: -2.8,
 affectedSectors: ['Energy', 'Banking', 'Transportation'],
 affectedCurrencies: ['RUB', 'CNY'],
 recommendedActions: ['Reduce exposure to affected sovereign bonds', 'Hedge currency risk', 'Review counterparty exposure'],
 status: 'active' },
 {
 id: 'geo-002',
 title: 'Trade War Tariff Escalation',
 category: 'trade_war',
 severity: 'high',
 region: 'Asia-Pacific',
 date: '2026-08-23',
 description: '25% tariffs imposed on $200B of bilateral trade. Export-dependent economies face growth headwinds.',
 portfolioImpact: -1.5,
 affectedSectors: ['Manufacturing', 'Technology', 'Agriculture'],
 affectedCurrencies: ['CNY', 'KRW', 'TWD'],
 recommendedActions: ['Diversify regional exposure', 'Monitor export-dependent sovereigns', 'Consider defensive positioning'],
 status: 'active' },
 {
 id: 'geo-003',
 title: 'OPEC+ Production Cut',
 category: 'commodity_shock',
 severity: 'medium',
 region: 'Middle East',
 date: '2026-08-22',
 description: '2M bpd production cut announced. Oil prices expected to rise 15-20% over next quarter.',
 portfolioImpact: -0.8,
 affectedSectors: ['Energy', 'Transportation', 'Chemicals'],
 affectedCurrencies: ['SAR', 'AED', 'NOK'],
 recommendedActions: ['Review commodity-linked bonds', 'Assess inflation hedging needs', 'Monitor emerging market oil importers'],
 status: 'monitoring' },
 {
 id: 'geo-004',
 title: 'Strait of Taiwan Tensions',
 category: 'military',
 severity: 'high',
 region: 'East Asia',
 date: '2026-08-21',
 description: 'Increased military exercises near strait. Risk premium on regional assets elevated.',
 portfolioImpact: -1.2,
 affectedSectors: ['Technology', 'Semiconductors', 'Shipping'],
 affectedCurrencies: ['TWD', 'JPY', 'CNY'],
 recommendedActions: ['Reduce TWD exposure', 'Increase JPY safe-haven allocation', 'Review supply chain dependencies'],
 status: 'monitoring' },
 {
 id: 'geo-005',
 title: 'Red Sea Shipping Disruption',
 category: 'supply_chain',
 severity: 'medium',
 region: 'Middle East / Africa',
 date: '2026-08-20',
 description: 'Continued attacks on commercial shipping. Transit times increased 2-3 weeks. Freight costs up 300%.',
 portfolioImpact: -0.6,
 affectedSectors: ['Shipping', 'Retail', 'Manufacturing'],
 affectedCurrencies: ['EUR', 'GBP'],
 recommendedActions: ['Monitor European trade exposure', 'Assess inflation impact from supply disruption', 'Review logistics-linked holdings'],
 status: 'active' },
 {
 id: 'geo-006',
 title: 'European Gas Supply Crisis',
 category: 'energy',
 severity: 'critical',
 region: 'Europe',
 date: '2026-08-19',
 description: 'Pipeline flows reduced 40%. Winter storage at 55% vs 75% target. Energy security at risk.',
 portfolioImpact: -2.1,
 affectedSectors: ['Energy', 'Utilities', 'Manufacturing'],
 affectedCurrencies: ['EUR', 'CHF'],
 recommendedActions: ['Review European sovereign exposure', 'Assess utility bond risk', 'Consider energy hedge positions'],
 status: 'active' },
];

const CATEGORY_INFO: Record<string, { icon: string; color: string; label: string }> = {
 sanctions: { icon: '🚫', color: 'red', label: 'Sanctions' },
 trade_war: { icon: '⚔️', color: 'orange', label: 'Trade War' },
 commodity_shock: { icon: 'BarChart3', color: 'yellow', label: 'Commodity' },
 military: { icon: '🎖️', color: 'red', label: 'Military' },
 supply_chain: { icon: '🔗', color: 'blue', label: 'Supply Chain' },
 energy: { icon: 'Zap', color: 'purple', label: 'Energy' },
 cyber: { icon: '💻', color: 'cyan', label: 'Cyber' } };

const SEVERITY_COLORS: Record<string, string> = {
 critical: 'bg-red-500/20 text-red-400',
 high: 'bg-orange-500/20 text-orange-400',
 medium: 'bg-yellow-500/20 text-yellow-400',
 low: 'bg-green-500/20 text-green-400' };

export default function GeopoliticalIntelligence() {
 const [events, setEvents] = useState(EVENTS);
 const [selectedEvent, setSelectedEvent] = useState<GeopoliticalEvent | null>(null);
 const [filterCategory, setFilterCategory] = useState<string>('all');
 const [filterSeverity, setFilterSeverity] = useState<string>('all');

 const filteredEvents = events.filter(e => {
 if (filterCategory !== 'all' && e.category !== filterCategory) return false;
 if (filterSeverity !== 'all' && e.severity !== filterSeverity) return false;
 return true;
 });

 const totalImpact = events.filter(e => e.status === 'active').reduce((sum, e) => sum + e.portfolioImpact, 0);

 return (
 <div className="space-y-6 animate-glass-in">
 <div className="flex items-center justify-between">
 <div className="flex items-center gap-3">
 <div className="w-10 h-10 bg-gradient-to-br from-red-500 to-rose-600 rounded-xl flex items-center justify-center">
 <Globe className="w-5 h-5" />
 </div>
 <div>
 <h2 className="text-xl font-bold text-white">Geopolitical Intelligence</h2>
 <p className="text-sm text-slate-400">Real-time monitoring of geopolitical risks to sovereign debt</p>
 </div>
 </div>
 <div className="glass px-4 py-2 rounded-xl text-center">
 <p className={`text-2xl font-bold ${totalImpact < 0 ? 'text-red-400' : 'text-green-400'}`}>
 {totalImpact > 0 ? '+' : ''}{totalImpact.toFixed(1)}%
 </p>
 <p className="text-xs text-slate-400">Net Portfolio Impact</p>
 </div>
 </div>

 {/* Filters */}
 <div className="flex gap-2 flex-wrap">
 <select
 value={filterCategory}
 onChange={(e) => setFilterCategory(e.target.value)}
 className="px-3 py-2 bg-white/5 border border-white/10 rounded-xl text-sm text-white focus:outline-none focus:border-red-500/50"
 >
 <option value="all">All Categories</option>
 {Object.entries(CATEGORY_INFO).map(([key, info]) => (
 <option key={key} value={key}>{info.icon} {info.label}</option>
 ))}
 </select>
 <select
 value={filterSeverity}
 onChange={(e) => setFilterSeverity(e.target.value)}
 className="px-3 py-2 bg-white/5 border border-white/10 rounded-xl text-sm text-white focus:outline-none focus:border-red-500/50"
 >
 <option value="all">All Severity</option>
 <option value="critical">🔴 Critical</option>
 <option value="high">🟠 High</option>
 <option value="medium">🟡 Medium</option>
 <option value="low">🟢 Low</option>
 </select>
 </div>

 <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
 {/* Event List */}
 <div className="space-y-3">
 {filteredEvents.map(event => (
 <button
 key={event.id}
 onClick={() => setSelectedEvent(event)}
 className={`w-full text-left glass rounded-xl p-4 transition-all ${
 selectedEvent?.id === event.id ? 'ring-2 ring-red-500/50' : 'hover:bg-white/5'
 }`}
 >
 <div className="flex items-start justify-between mb-2">
 <div className="flex items-center gap-2">
 <span className="text-lg">{CATEGORY_INFO[event.category]?.icon}</span>
 <span className={`px-2 py-0.5 rounded text-xs font-medium ${SEVERITY_COLORS[event.severity]}`}>
 {event.severity.toUpperCase()}
 </span>
 </div>
 <span className={`text-sm font-bold ${event.portfolioImpact < 0 ? 'text-red-400' : 'text-green-400'}`}>
 {event.portfolioImpact > 0 ? '+' : ''}{event.portfolioImpact}%
 </span>
 </div>
 <h4 className="text-white text-sm font-medium mb-1">{event.title}</h4>
 <p className="text-xs text-slate-400 mb-2">{event.region} • {event.date}</p>
 <div className="flex gap-1 flex-wrap">
 {event.affectedCurrencies.slice(0, 3).map(c => (
 <span key={c} className="px-1.5 py-0.5 bg-white/10 rounded text-xs text-slate-400">{c}</span>
 ))}
 </div>
 </button>
 ))}
 </div>

 {/* Detail Panel */}
 <div className="lg:col-span-2">
 {selectedEvent ? (
 <div className="glass rounded-2xl p-6 space-y-5">
 <div className="flex items-start justify-between">
 <div>
 <div className="flex items-center gap-2 mb-2">
 <span className="text-2xl">{CATEGORY_INFO[selectedEvent.category]?.icon}</span>
 <span className={`px-3 py-1 rounded-lg text-xs font-medium ${SEVERITY_COLORS[selectedEvent.severity]}`}>
 {selectedEvent.severity.toUpperCase()}
 </span>
 <span className={`px-3 py-1 rounded-lg text-xs font-medium ${
 selectedEvent.status === 'active' ? 'bg-red-500/20 text-red-400' :
 selectedEvent.status === 'monitoring' ? 'bg-yellow-500/20 text-yellow-400' :
 'bg-green-500/20 text-green-400'
 }`}>
 {selectedEvent.status.toUpperCase()}
 </span>
 </div>
 <h3 className="text-lg font-bold text-white">{selectedEvent.title}</h3>
 <p className="text-sm text-slate-400 mt-1">{selectedEvent.region} • {selectedEvent.date}</p>
 </div>
 <div className="text-right">
 <p className={`text-3xl font-bold ${selectedEvent.portfolioImpact < 0 ? 'text-red-400' : 'text-green-400'}`}>
 {selectedEvent.portfolioImpact > 0 ? '+' : ''}{selectedEvent.portfolioImpact}%
 </p>
 <p className="text-xs text-slate-500">Portfolio Impact</p>
 </div>
 </div>

 <p className="text-sm text-slate-300">{selectedEvent.description}</p>

 {/* Affected Sectors */}
 <div>
 <h4 className="text-xs font-medium text-slate-500 mb-2">AFFECTED SECTORS</h4>
 <div className="flex gap-2 flex-wrap">
 {selectedEvent.affectedSectors.map(s => (
 <span key={s} className="px-3 py-1 bg-white/5 border border-white/10 rounded-lg text-xs text-slate-300">
 {s}
 </span>
 ))}
 </div>
 </div>

 {/* Affected Currencies */}
 <div>
 <h4 className="text-xs font-medium text-slate-500 mb-2">AFFECTED CURRENCIES</h4>
 <div className="flex gap-2 flex-wrap">
 {selectedEvent.affectedCurrencies.map(c => (
 <span key={c} className="px-3 py-1 bg-purple-500/10 border border-purple-500/20 rounded-lg text-xs text-purple-300 font-mono">
 {c}
 </span>
 ))}
 </div>
 </div>

 {/* Recommended Actions */}
 <div>
 <h4 className="text-xs font-medium text-slate-500 mb-2">RECOMMENDED ACTIONS</h4>
 <div className="space-y-2">
 {selectedEvent.recommendedActions.map((action, i) => (
 <div key={i} className="flex items-start gap-3 p-3 bg-white/5 rounded-xl">
 <span className="text-red-400 mt-0.5">{i + 1}.</span>
 <p className="text-sm text-slate-300">{action}</p>
 </div>
 ))}
 </div>
 </div>

 {/* Impact Assessment */}
 <div className="p-4 bg-white/5 rounded-xl border-l-2 border-red-500">
 <h4 className="text-xs font-medium text-red-400 mb-2"> <BarChart3 className="w-4 h-4 inline" /> IMPACT ASSESSMENT</h4>
 <div className="grid grid-cols-3 gap-4 text-center">
 <div>
 <p className="text-lg font-bold text-white">{selectedEvent.affectedSectors.length}</p>
 <p className="text-xs text-slate-500">Sectors</p>
 </div>
 <div>
 <p className="text-lg font-bold text-white">{selectedEvent.affectedCurrencies.length}</p>
 <p className="text-xs text-slate-500">Currencies</p>
 </div>
 <div>
 <p className={`text-lg font-bold ${selectedEvent.portfolioImpact < 0 ? 'text-red-400' : 'text-green-400'}`}>
 {selectedEvent.portfolioImpact > 0 ? '+' : ''}{selectedEvent.portfolioImpact}%
 </p>
 <p className="text-xs text-slate-500">Est. Impact</p>
 </div>
 </div>
 </div>
 </div>
 ) : (
 <div className="glass rounded-2xl p-12 text-center">
 <div className="text-4xl mb-4"> <Globe className="w-4 h-4 inline" /> </div>
 <h3 className="text-white font-bold mb-2">Select an Event</h3>
 <p className="text-sm text-slate-400">Click a geopolitical event to see its portfolio impact and recommended actions</p>
 </div>
 )}
 </div>
 </div>
 </div>
 );
}
