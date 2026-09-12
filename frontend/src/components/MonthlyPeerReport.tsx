// ── Monthly Peer Report Component ─────────────────────────────────────
// Generates a monthly summary of consensus shifts, benchmark changes,
// sentiment evolution, and actionable recommendations.

import { useState } from 'react';
import {
  MOCK_CONSENSUS_INDICATORS,
  getTopConsensus,
  getIncreasingTrends,
  getPercentileLabel,
  getSentimentColor,
  getSentimentIcon,
  getCategoryIcon,
  type ConsensusIndicator,
  type PeerBenchmark,
  type MarketSentiment,
  type PeerAction } from '../lib/peerIntelligence';
import { ChartColumn as BarChart3, Target, Zap } from 'lucide-react';

interface MonthlyPeerReportProps {
 /** Report month (default: current) */
 month?: string;
}

export default function MonthlyPeerReport({ month }: MonthlyPeerReportProps) {
 const [expandedSection, setExpandedSection] = useState<string | null>('summary');

 const reportMonth = month || new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

 const topConsensus = getTopConsensus(3);
 const increasingTrends = getIncreasingTrends();
 const benchmarksAboveMedian = ([] as PeerBenchmark[]).filter((b) => b.percentile >= 50);

 const toggleSection = (section: string) => {
 setExpandedSection(expandedSection === section ? null : section);
 };

 return (
 <div className="space-y-4 animate-glass-in">
 {/* Report Header */}
 <div className="glass rounded-2xl overflow-hidden">
 <div className="bg-gradient-to-r from-slate-800 to-slate-900 p-6 text-white">
 <div className="flex items-center justify-between">
 <div>
 <h2 className="text-xl font-bold"> <BarChart3 className="w-4 h-4 inline" /> Monthly Peer Intelligence Report</h2>
 <p className="text-sm text-white/70 mt-1">{reportMonth} • Institutional Investor Peer Group</p>
 </div>
 <div className="text-right">
 <div className="text-xs text-white/50">Report Generated</div>
 <div className="text-sm font-medium">{new Date().toLocaleDateString()}</div>
 </div>
 </div>
 </div>

 {/* Executive Summary */}
 <div className="p-6 border-b border-white/20">
 <h3 className="text-sm font-bold text-slate-700 uppercase tracking-widest mb-3">Executive Summary</h3>
 <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
 <div className="p-3 rounded-xl bg-blue-50/50">
 <div className="text-2xl font-bold text-blue-600">{0}</div>
 <div className="text-xs text-slate-600">Consensus trends tracked</div>
 </div>
 <div className="p-3 rounded-xl bg-emerald-50/50">
 <div className="text-2xl font-bold text-emerald-600">{increasingTrends.length}</div>
 <div className="text-xs text-slate-600">Trends increasing this month</div>
 </div>
 <div className="p-3 rounded-xl bg-purple-50/50">
 <div className="text-2xl font-bold text-purple-600">{benchmarksAboveMedian.length}/{0}</div>
 <div className="text-xs text-slate-600">Your metrics above median</div>
 </div>
 </div>

 <p className="text-sm text-slate-600 mt-4 leading-relaxed">
 This month saw continued momentum in duration extension ({topConsensus[0]?.consensusPercentage}% of peers),
 with {increasingTrends.length} of {0} tracked trends showing upward movement.
 Credit concerns remain elevated as {([] as ConsensusIndicator[]).find((c) => c.category === 'credit')?.consensusPercentage}% of peers
 reduce high-yield exposure. Green bond allocation continues to grow, reflecting the secular shift toward ESG integration.
 </p>
 </div>
 </div>

 {/* Consensus Shifts */}
 <div className="glass rounded-2xl overflow-hidden">
 <button
 onClick={() => toggleSection('consensus')}
 className="w-full p-4 flex items-center justify-between hover:bg-white/30 transition-colors"
 >
 <div className="flex items-center gap-2">
 <Target className="w-5 h-5" />
 <h3 className="text-sm font-bold text-slate-900">Consensus Shifts</h3>
 <span className="text-[10px] text-slate-500">• {0} trends</span>
 </div>
 <span className="text-slate-400">{expandedSection === 'consensus' ? '▲' : '▼'}</span>
 </button>

 {expandedSection === 'consensus' && (
 <div className="p-4 pt-0 space-y-3">
 {([] as ConsensusIndicator[]).map((indicator) => (
 <div key={indicator.id} className="flex items-center gap-3 p-3 rounded-xl bg-white/30">
 <span className="text-lg">{getCategoryIcon(indicator.category)}</span>
 <div className="flex-1">
 <div className="flex items-center gap-2">
 <span className="text-sm font-semibold text-slate-900">{indicator.title}</span>
 <span className={`text-[10px] font-bold ${indicator.trend === 'increasing' ? 'text-emerald-600' : indicator.trend === 'decreasing' ? 'text-red-600' : 'text-slate-500'}`}>
 {indicator.trend === 'increasing' ? '↑' : indicator.trend === 'decreasing' ? '↓' : '→'}
 {indicator.trendDelta > 0 ? '+' : ''}{indicator.trendDelta}%
 </span>
 </div>
 <p className="text-xs text-slate-500 line-clamp-1">{indicator.description}</p>
 </div>
 <div className="text-right">
 <div className="text-lg font-bold text-slate-900">{indicator.consensusPercentage}%</div>
 <div className="text-[10px] text-slate-400">{indicator.sampleSize.toLocaleString()} peers</div>
 </div>
 </div>
 ))}
 </div>
 )}
 </div>

 {/* Benchmark Changes */}
 <div className="glass rounded-2xl overflow-hidden">
 <button
 onClick={() => toggleSection('benchmarks')}
 className="w-full p-4 flex items-center justify-between hover:bg-white/30 transition-colors"
 >
 <div className="flex items-center gap-2">
 <BarChart3 className="w-5 h-5" />
 <h3 className="text-sm font-bold text-slate-900">Benchmark Changes</h3>
 <span className="text-[10px] text-slate-500">• Your percentile rankings</span>
 </div>
 <span className="text-slate-400">{expandedSection === 'benchmarks' ? '▲' : '▼'}</span>
 </button>

 {expandedSection === 'benchmarks' && (
 <div className="p-4 pt-0">
 <div className="overflow-x-auto">
 <table className="w-full text-sm">
 <thead>
 <tr className="border-b border-white/20">
 <th className="text-left py-2 px-3 text-xs font-semibold text-slate-500">Metric</th>
 <th className="text-right py-2 px-3 text-xs font-semibold text-slate-500">You</th>
 <th className="text-right py-2 px-3 text-xs font-semibold text-slate-500">Median</th>
 <th className="text-right py-2 px-3 text-xs font-semibold text-slate-500">Range (P25-P75)</th>
 <th className="text-right py-2 px-3 text-xs font-semibold text-slate-500">Percentile</th>
 </tr>
 </thead>
 <tbody>
 {([] as PeerBenchmark[]).map((b) => (
 <tr key={b.id} className="border-b border-white/10">
 <td className="py-2 px-3 text-slate-700">{b.metric}</td>
 <td className="py-2 px-3 text-right font-medium text-slate-900">{b.userValue}{b.unit}</td>
 <td className="py-2 px-3 text-right text-slate-600">{b.peerMedian}{b.unit}</td>
 <td className="py-2 px-3 text-right text-slate-500">{b.peerP25}{b.unit} - {b.peerP75}{b.unit}</td>
 <td className="py-2 px-3 text-right">
 <span className={`font-bold ${b.percentile >= 75 ? 'text-emerald-600' : b.percentile >= 50 ? 'text-blue-600' : 'text-amber-600'}`}>
 {getPercentileLabel(b.percentile)}
 </span>
 </td>
 </tr>
 ))}
 </tbody>
 </table>
 </div>
 </div>
 )}
 </div>

 {/* Sentiment Evolution */}
 <div className="glass rounded-2xl overflow-hidden">
 <button
 onClick={() => toggleSection('sentiment')}
 className="w-full p-4 flex items-center justify-between hover:bg-white/30 transition-colors"
 >
 <div className="flex items-center gap-2">
 <span>💭</span>
 <h3 className="text-sm font-bold text-slate-900">Sentiment Evolution</h3>
 <span className="text-[10px] text-slate-500">• {0} indicators</span>
 </div>
 <span className="text-slate-400">{expandedSection === 'sentiment' ? '▲' : '▼'}</span>
 </button>

 {expandedSection === 'sentiment' && (
 <div className="p-4 pt-0 space-y-3">
 {([] as MarketSentiment[]).map((sentiment) => (
 <div key={sentiment.id} className="flex items-center gap-3 p-3 rounded-xl bg-white/30">
 <span className="text-lg">{getSentimentIcon(sentiment.sentiment)}</span>
 <div className="flex-1">
 <div className="flex items-center gap-2">
 <span className="text-sm font-semibold text-slate-900">{sentiment.indicator}</span>
 <span className={`text-xs font-bold ${getSentimentColor(sentiment.sentiment)}`}>
 {sentiment.sentiment}
 </span>
 </div>
 <div className="flex items-center gap-2 mt-1">
 <div className="flex-1 h-1.5 rounded-full bg-gradient-to-r from-red-200 via-slate-200 to-emerald-200">
 <div
 className="w-2.5 h-2.5 rounded-full bg-white border-2 border-slate-600 shadow -mt-0.5"
 style={{ left: `${((sentiment.score + 100) / 200) * 100}%`, position: 'relative' }}
 />
 </div>
 <span className="text-[10px] text-slate-500">{sentiment.consensus}% agree</span>
 </div>
 </div>
 <div className="text-right">
 <div className={`text-lg font-bold ${sentiment.score > 0 ? 'text-emerald-600' : sentiment.score < 0 ? 'text-red-600' : 'text-slate-500'}`}>
 {sentiment.score > 0 ? '+' : ''}{sentiment.score}
 </div>
 <div className="text-[10px] text-slate-400">{sentiment.timeframe}</div>
 </div>
 </div>
 ))}
 </div>
 )}
 </div>

 {/* Top Peer Actions */}
 <div className="glass rounded-2xl overflow-hidden">
 <button
 onClick={() => toggleSection('actions')}
 className="w-full p-4 flex items-center justify-between hover:bg-white/30 transition-colors"
 >
 <div className="flex items-center gap-2">
 <Zap className="w-5 h-5" />
 <h3 className="text-sm font-bold text-slate-900">Top Peer Actions</h3>
 <span className="text-[10px] text-slate-500">• Last 30 days</span>
 </div>
 <span className="text-slate-400">{expandedSection === 'actions' ? '▲' : '▼'}</span>
 </button>

 {expandedSection === 'actions' && (
 <div className="p-4 pt-0 space-y-2">
 {([] as PeerAction[]).map((action) => (
 <div key={action.id} className="flex items-center gap-3 p-3 rounded-xl bg-white/30">
 <div className="text-lg font-bold text-blue-600">{action.percentage}%</div>
 <div className="flex-1">
 <div className="text-sm font-medium text-slate-900">{action.action}</div>
  <div className="text-xs text-slate-500">{action.instrumentType} • {action.peerCount!.toLocaleString()} peers</div>
  </div>
  <div className="text-right">
  {action.avgSavings! > 0 && (
  <div className="text-sm font-bold text-emerald-600">+${action.avgSavings!.toLocaleString()}</div>
 )}
 <div className="text-[10px] text-slate-500">{action.riskChange}</div>
 </div>
 </div>
 ))}
 </div>
 )}
 </div>

 {/* Disclaimer */}
 <div className="glass rounded-xl p-4">
 <p className="text-[10px] text-slate-500 leading-relaxed">
 This report is generated from anonymized peer data and does not constitute investment advice.
 Peer consensus does not guarantee future performance. All data reflects aggregated patterns from {MOCK_CONSENSUS_INDICATORS[0]?.sampleSize.toLocaleString()}+ institutional portfolios.
 Consult your investment committee before making allocation changes.
 </p>
 </div>
 </div>
 );
}
