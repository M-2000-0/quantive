// ── Peer Intelligence Component ───────────────────────────────────────
// Aggregates anonymized optimization patterns across users and displays
// consensus indicators, peer benchmarks, market sentiment, and actions.

import { useState } from 'react';
import {
  MOCK_CONSENSUS_INDICATORS,
  getTopConsensus,
  getPercentileLabel,
  getPercentileColor,
  getSentimentColor,
  getSentimentIcon,
  getCategoryIcon,
  type ConsensusIndicator,
  type PeerBenchmark,
  type MarketSentiment,
  type PeerAction } from '../lib/peerIntelligence';
import { ChartColumn as BarChart3, RefreshCw, Target } from 'lucide-react';

type Tab = 'consensus' | 'benchmarks' | 'sentiment' | 'actions';

const CATEGORY_COLORS: Record<string, string> = {
 duration: 'from-blue-500 to-cyan-500',
 allocation: 'from-purple-500 to-pink-500',
 hedging: 'from-emerald-500 to-teal-500',
 credit: 'from-amber-500 to-orange-500',
 refinancing: 'from-indigo-500 to-blue-500',
 risk: 'from-red-500 to-rose-500' };

function ConsensusCard({ indicator }: { indicator: ConsensusIndicator }) {
 return (
 <div className="glass rounded-2xl p-5 hover:shadow-lg transition-all">
 <div className="flex items-start justify-between mb-3">
 <div className="flex items-center gap-2">
 <span className="text-lg">{getCategoryIcon(indicator.category)}</span>
 <div>
 <h3 className="font-semibold text-slate-900 text-sm">{indicator.title}</h3>
 <span className="text-[10px] font-medium text-slate-500 capitalize">{indicator.category}</span>
 </div>
 </div>
 <div className="text-right">
 <div className="text-2xl font-bold text-slate-900">{indicator.consensusPercentage}%</div>
 <div className="flex items-center gap-1">
 <span className={`text-[10px] font-bold ${indicator.trend === 'increasing' ? 'text-emerald-600' : indicator.trend === 'decreasing' ? 'text-red-600' : 'text-slate-500'}`}>
 {indicator.trend === 'increasing' ? '↑' : indicator.trend === 'decreasing' ? '↓' : '→'}
 {indicator.trendDelta > 0 ? '+' : ''}{indicator.trendDelta}%
 </span>
 <span className="text-[9px] text-slate-400">30d</span>
 </div>
 </div>
 </div>

 <p className="text-xs text-slate-600 mb-3 leading-relaxed">{indicator.description}</p>

 <div className="flex items-center justify-between">
 <div className="flex items-center gap-3 text-[10px] text-slate-500">
 <span> <BarChart3 className="w-4 h-4 inline" /> {indicator.sampleSize.toLocaleString()} portfolios</span>
 <span> <Target className="w-4 h-4 inline" /> {indicator.confidence}% confidence</span>
 </div>
 {indicator.actionable && (
 <span className="px-2 py-0.5 text-[9px] font-bold uppercase bg-blue-50 text-blue-600 rounded-full ring-1 ring-blue-200">
 Actionable
 </span>
 )}
 </div>

 {/* Consensus bar */}
 <div className="mt-3">
 <div className="h-2 rounded-full bg-slate-200 overflow-hidden">
 <div
 className={`h-full rounded-full bg-gradient-to-r ${CATEGORY_COLORS[indicator.category] || 'from-slate-400 to-slate-500'}`}
 style={{ width: `${indicator.consensusPercentage}%` }}
 />
 </div>
 <div className="flex justify-between text-[9px] text-slate-400 mt-1">
 <span>0%</span>
 <span>{indicator.consensusPercentage}% of peers</span>
 <span>100%</span>
 </div>
 </div>
 </div>
 );
}

function BenchmarkRow({ benchmark }: { benchmark: PeerBenchmark }) {
 const percentile = benchmark.percentile;
 const userPosition = ((benchmark.userValue - benchmark.peerP10) / (benchmark.peerP90 - benchmark.peerP10)) * 100;

 return (
 <div className="glass rounded-xl p-4">
 <div className="flex items-center justify-between mb-2">
 <div>
 <h4 className="text-sm font-semibold text-slate-900">{benchmark.metric}</h4>
 <span className="text-[10px] text-slate-500">{benchmark.category}</span>
 </div>
 <div className="text-right">
 <div className="text-lg font-bold text-slate-900">
 {benchmark.userValue}{benchmark.unit === '%' ? '%' : ` ${benchmark.unit}`}
 </div>
 <div className={`text-xs font-bold ${getPercentileColor(percentile)}`}>
 {getPercentileLabel(percentile)}
 </div>
 </div>
 </div>

 {/* Peer range visualization */}
 <div className="relative h-8 bg-slate-100 rounded-lg overflow-hidden mb-2">
 {/* Peer range */}
 <div
 className="absolute top-1 bottom-1 bg-slate-200 rounded"
 style={{
 left: '10%',
 right: '10%' }}
 />
 {/* P25-P75 range */}
 <div
 className="absolute top-0 bottom-0 bg-blue-100 rounded"
 style={{
 left: `${25}%`,
 right: `${25}%` }}
 />
 {/* Median line */}
 <div
 className="absolute top-0 bottom-0 w-0.5 bg-slate-400"
 style={{ left: '50%' }}
 />
 {/* User position */}
 <div
 className="absolute top-0 bottom-0 w-1 rounded-full bg-blue-600 shadow-md"
 style={{ left: `${Math.min(95, Math.max(5, userPosition))}%` }}
 />
 </div>

 <div className="flex justify-between text-[9px] text-slate-400 mb-2">
 <span>P10: {benchmark.peerP10}{benchmark.unit}</span>
 <span>Median: {benchmark.peerMedian}{benchmark.unit}</span>
 <span>P90: {benchmark.peerP90}{benchmark.unit}</span>
 </div>

 <p className="text-xs text-slate-600 italic">{benchmark.insight}</p>
 </div>
 );
}

function SentimentCard({ sentiment }: { sentiment: MarketSentiment }) {
 return (
 <div className="glass rounded-xl p-4">
 <div className="flex items-center justify-between mb-2">
 <div className="flex items-center gap-2">
 <span className="text-lg">{getSentimentIcon(sentiment.sentiment)}</span>
 <h4 className="text-sm font-semibold text-slate-900">{sentiment.indicator}</h4>
 </div>
 <div className="flex items-center gap-2">
 <span className={`text-sm font-bold ${getSentimentColor(sentiment.sentiment)}`}>
 {sentiment.sentiment}
 </span>
 <span className={`px-2 py-0.5 text-[10px] font-bold rounded-full ${
 sentiment.score > 0 ? 'bg-emerald-50 text-emerald-600' :
 sentiment.score < 0 ? 'bg-red-50 text-red-600' :
 'bg-slate-50 text-slate-600'
 }`}>
 {sentiment.score > 0 ? '+' : ''}{sentiment.score}
 </span>
 </div>
 </div>

 <div className="flex items-center gap-3 text-[10px] text-slate-500 mb-2">
 <span> <BarChart3 className="w-4 h-4 inline" /> {sentiment.dataPoints} portfolios</span>
 <span> <Target className="w-4 h-4 inline" /> {sentiment.consensus}% consensus</span>
 <span>⏱️ {sentiment.timeframe}</span>
 </div>

 {/* Sentiment bar */}
 <div className="relative h-2 rounded-full bg-gradient-to-r from-red-200 via-slate-200 to-emerald-200 mb-2">
 <div
 className="absolute top-0 w-3 h-3 rounded-full bg-white border-2 border-slate-600 shadow -mt-0.5"
 style={{ left: `${((sentiment.score + 100) / 200) * 100}%`, transform: 'translateX(-50%)' }}
 />
 </div>

 <div className="flex flex-wrap gap-1">
 {sentiment.sources.map((source) => (
 <span key={source} className="px-1.5 py-0.5 text-[9px] font-medium bg-slate-100 text-slate-600 rounded">
 {source}
 </span>
 ))}
 </div>
 </div>
 );
}

export default function PeerIntelligence() {
 const [activeTab, setActiveTab] = useState<Tab>('consensus');
 const [selectedCategory, setSelectedCategory] = useState<string>('all');

 const tabs: { key: Tab; label: string; icon: string; count?: number }[] = [
 { key: 'consensus', label: 'Consensus', icon: 'Target', count: 0 },
 { key: 'benchmarks', label: 'Benchmarks', icon: 'BarChart3', count: 0 },
 { key: 'sentiment', label: 'Sentiment', icon: '💭', count: 0 },
 { key: 'actions', label: 'Peer Actions', icon: 'Zap', count: 0 },
 ];

 const filteredConsensus = selectedCategory === 'all'
 ? MOCK_CONSENSUS_INDICATORS
 : MOCK_CONSENSUS_INDICATORS.filter((c) => c.category === selectedCategory);

 const categories = ['all', ...new Set(MOCK_CONSENSUS_INDICATORS.map((c) => c.category))];

 return (
 <div className="space-y-6 animate-glass-in">
 {/* Header */}
 <div className="flex items-center justify-between">
 <div>
 <h2 className="text-2xl font-bold tracking-tight text-slate-900">Peer Intelligence</h2>
 <p className="text-sm text-slate-600 mt-1">
 Anonymized patterns from {MOCK_CONSENSUS_INDICATORS[0]?.sampleSize.toLocaleString()}+ portfolios
 </p>
 </div>
 <div className="glass px-3 py-1.5 rounded-xl text-xs font-medium text-slate-600">
 <RefreshCw className="w-4 h-4 inline" /> Updated daily · Last: {new Date().toLocaleDateString()}
 </div>
 </div>

 {/* Quick Stats */}
 <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
 <div className="glass p-3 rounded-xl text-center">
 <div className="text-lg font-bold text-blue-600">{getTopConsensus(1)[0]?.consensusPercentage || 0}%</div>
 <div className="text-[10px] text-slate-500">Top Consensus</div>
 </div>
 <div className="glass p-3 rounded-xl text-center">
 <div className="text-lg font-bold text-emerald-600">{([] as MarketSentiment[]).filter((s) => s.sentiment === 'bullish').length}</div>
 <div className="text-[10px] text-slate-500">Bullish Signals</div>
 </div>
 <div className="glass p-3 rounded-xl text-center">
 <div className="text-lg font-bold text-amber-600">{([] as PeerBenchmark[]).filter((b) => b.percentile >= 50).length}/{MOCK_CONSENSUS_INDICATORS.length}</div>
 <div className="text-[10px] text-slate-500">Above Median</div>
 </div>
 <div className="glass p-3 rounded-xl text-center">
 <div className="text-lg font-bold text-purple-600">{0}</div>
 <div className="text-[10px] text-slate-500">Popular Actions</div>
 </div>
 </div>

 {/* Tabs */}
 <div className="flex gap-1 bg-white/40 backdrop-blur rounded-xl p-1 w-fit border border-white/30">
 {tabs.map((tab) => (
 <button
 key={tab.key}
 onClick={() => setActiveTab(tab.key)}
 className={`px-4 py-2 text-sm font-medium rounded-lg transition-all ${
 activeTab === tab.key
 ? 'bg-white text-slate-900 shadow-sm border border-white/60'
 : 'text-slate-500 hover:text-slate-700'
 }`}
 >
 {tab.icon} {tab.label}
 {tab.count && (
 <span className="ml-1.5 text-[10px] font-bold text-slate-400">{tab.count}</span>
 )}
 </button>
 ))}
 </div>

 {/* Consensus Tab */}
 {activeTab === 'consensus' && (
 <div className="space-y-4">
 {/* Category Filter */}
 <div className="flex gap-1 flex-wrap">
 {categories.map((cat) => (
 <button
 key={cat}
 onClick={() => setSelectedCategory(cat)}
 className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${
 selectedCategory === cat
 ? 'bg-blue-600/14 text-blue-700 ring-1 ring-blue-400/20'
 : 'text-slate-600 hover:bg-white/60'
 }`}
 >
 {cat === 'all' ? 'All' : `${getCategoryIcon(cat as ConsensusIndicator['category'])} ${cat.charAt(0).toUpperCase() + cat.slice(1)}`}
 </button>
 ))}
 </div>

 <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
 {filteredConsensus.map((indicator) => (
 <ConsensusCard key={indicator.id} indicator={indicator} />
 ))}
 </div>
 </div>
 )}

 {/* Benchmarks Tab */}
 {activeTab === 'benchmarks' && (
 <div className="space-y-4">
 {([] as PeerBenchmark[]).map((benchmark) => (
 <BenchmarkRow key={benchmark.id} benchmark={benchmark} />
 ))}
 </div>
 )}

 {/* Sentiment Tab */}
 {activeTab === 'sentiment' && (
 <div className="space-y-4">
 {([] as MarketSentiment[]).map((sentiment) => (
 <SentimentCard key={sentiment.id} sentiment={sentiment} />
 ))}
 </div>
 )}

 {/* Peer Actions Tab */}
 {activeTab === 'actions' && (
 <div className="space-y-3">
 <div className="glass rounded-2xl overflow-hidden">
 <table className="w-full text-sm">
 <thead>
 <tr className="border-b border-white/20">
 <th className="px-4 py-3 text-left font-semibold text-slate-700">Action</th>
 <th className="px-4 py-3 text-left font-semibold text-slate-700">Type</th>
 <th className="px-4 py-3 text-right font-semibold text-slate-700">Peers</th>
 <th className="px-4 py-3 text-right font-semibold text-slate-700">Avg Savings</th>
 <th className="px-4 py-3 text-right font-semibold text-slate-700">Risk Change</th>
 <th className="px-4 py-3 text-right font-semibold text-slate-700">Timeframe</th>
 </tr>
 </thead>
 <tbody>
 {([] as PeerAction[]).map((action) => (
 <tr key={action.id} className="border-b border-white/10 hover:bg-white/30 transition-colors">
 <td className="px-4 py-3">
 <div className="font-medium text-slate-900">{action.action}</div>
 </td>
 <td className="px-4 py-3">
 <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium bg-slate-100 text-slate-600">
 {action.instrumentType}
 </span>
 </td>
 <td className="px-4 py-3 text-right">
 <div className="text-sm font-bold text-slate-900">{action.percentage}%</div>
  <div className="text-[10px] text-slate-500">{action.peerCount!.toLocaleString()}</div>
  </td>
  <td className="px-4 py-3 text-right">
  {action.avgSavings! > 0 ? (
  <span className="text-sm font-bold text-emerald-600">
  +${action.avgSavings!.toLocaleString()}
 </span>
 ) : (
 <span className="text-sm text-slate-400">—</span>
 )}
 </td>
 <td className="px-4 py-3 text-right">
 <span className="text-xs text-slate-600">{action.riskChange}</span>
 </td>
 <td className="px-4 py-3 text-right">
 <span className="text-xs text-slate-500">{action.timeframe}</span>
 </td>
 </tr>
 ))}
 </tbody>
 </table>
 </div>
 </div>
 )}
 </div>
 );
}
