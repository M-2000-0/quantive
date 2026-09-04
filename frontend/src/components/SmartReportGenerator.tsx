// ── Smart Report Generator ────────────────────────────────────────────
// Auto-generates investment committee memos from optimization results.
// Produces structured, actionable reports ready for committee review.

import { useState } from 'react';
import type { DecisionEntry } from '../lib/decisionJournal';
import { CircleCheck as CheckCircle, TriangleAlert as AlertTriangle } from 'lucide-react';

interface ReportSection {
 id: string;
 title: string;
 content: string;
 type: 'text' | 'metrics' | 'table' | 'chart' | 'recommendation';
 data?: Record<string, unknown>;
}

interface GeneratedReport {
 id: string;
 title: string;
 subtitle: string;
 generatedAt: number;
 author: string;
 classification: 'confidential' | 'internal' | 'public';
 sections: ReportSection[];
 executiveSummary: string;
 keyRecommendations: string[];
 riskDisclosure: string;
}

interface SmartReportGeneratorProps {
 decision: DecisionEntry;
 onGenerate?: (report: GeneratedReport) => void;
}

function generateReportFromDecision(decision: DecisionEntry): GeneratedReport {
 const { recommendation, marketSnapshot, outcome } = decision;

 const sections: ReportSection[] = [
 {
 id: 'market_context',
 title: 'Market Context',
 type: 'metrics',
 content: `As of the recommendation date, the federal funds rate stood at ${marketSnapshot.fedFundsRate}%, with the 10-year Treasury at ${marketSnapshot.treasury10Y}%. Credit spreads were at ${marketSnapshot.igSpread}bps (IG) and ${marketSnapshot.hySpread}bps (HY). The yield curve slope of ${marketSnapshot.yieldCurveSlope}bps indicated a ${marketSnapshot.yieldCurveSlope > 0 ? 'normal' : 'inverted'} term structure.`,
 data: {
 fedFundsRate: marketSnapshot.fedFundsRate,
 treasury10Y: marketSnapshot.treasury10Y,
 igSpread: marketSnapshot.igSpread,
 hySpread: marketSnapshot.hySpread,
 yieldCurveSlope: marketSnapshot.yieldCurveSlope,
 vix: marketSnapshot.vix } },
 {
 id: 'recommendation_detail',
 title: 'Recommendation Detail',
 type: 'recommendation',
 content: recommendation.description,
 data: {
 type: recommendation.type,
 instruments: recommendation.instruments,
 estimatedSavings: recommendation.estimatedSavings,
 riskImpact: recommendation.riskImpact,
 confidence: recommendation.confidence } },
 {
 id: 'financial_impact',
 title: 'Financial Impact Analysis',
 type: 'table',
 content: 'Projected financial impact of the recommended action.',
 data: {
 headers: ['Metric', 'Current', 'Projected', 'Change'],
 rows: [
 ['Estimated Annual Savings', '$0', `$${recommendation.estimatedSavings.toLocaleString()}`, `+$${recommendation.estimatedSavings.toLocaleString()}`],
 ['Risk Impact', 'Baseline', recommendation.riskImpact, recommendation.riskImpact],
 ['Confidence Level', '—', `${recommendation.confidence}%`, `${recommendation.confidence > 70 ? 'High' : recommendation.impactScore > 50 ? 'Medium' : 'Low'}`],
 ] } },
 ];

 // Add outcome section if available
 if (outcome) {
 sections.push({
 id: 'outcome',
 title: 'Outcome',
 type: 'metrics',
 content: `The decision was ${decision.decision.status}. ${outcome.notes}`,
 data: {
 actualSavings: outcome.actualSavings,
 actualRiskChange: outcome.actualRiskChange,
 rating: outcome.rating } });
 }

 // Add learnings section if available
 if (decision.learnings) {
 sections.push({
 id: 'learnings',
 title: 'Key Learnings',
 type: 'text',
 content: `Market regime: ${decision.learnings.marketRegime}. Confidence calibration: ${decision.learnings.confidenceCalibration.toFixed(2)}x.`,
 data: {
 whatWorked: decision.learnings.whatWorked,
 whatFailed: decision.learnings.whatFailed,
 marketRegime: decision.learnings.marketRegime,
 confidenceCalibration: decision.learnings.confidenceCalibration } });
 }

 const keyRecommendations = [
 `Execute ${recommendation.type.replace(/_/g, ' ')} for ${recommendation.instruments.join(', ')}`,
 `Target completion within: ${recommendation.timeframe || '30 days'}`,
 `Review with credit analyst before execution`,
 ];

 return {
 id: `report-${decision.id}`,
 title: `Investment Committee Memo: ${recommendation.title}`,
 subtitle: `Prepared ${new Date().toLocaleDateString()} | Classification: Confidential`,
 generatedAt: Date.now(),
 author: decision.decision.decidedBy || 'System Generated',
 classification: 'confidential',
 sections,
 executiveSummary: `This memo recommends ${recommendation.type.replace(/_/g, ' ')} for ${recommendation.instruments.join(', ')}. ${recommendation.description}. Estimated savings: $${recommendation.estimatedSavings.toLocaleString()}. Risk impact: ${recommendation.riskImpact}. Confidence: ${recommendation.confidence}%.`,
 keyRecommendations,
 riskDisclosure: 'This analysis is based on current market conditions and historical patterns. Past performance does not guarantee future results. All recommendations should be reviewed by qualified investment professionals before execution.' };
}

export default function SmartReportGenerator({ decision, onGenerate }: SmartReportGeneratorProps) {
 const [report, setReport] = useState<GeneratedReport | null>(null);
 const [isGenerating, setIsGenerating] = useState(false);

 const handleGenerate = () => {
 setIsGenerating(true);
 // Simulate generation time
 setTimeout(() => {
 const generated = generateReportFromDecision(decision);
 setReport(generated);
 setIsGenerating(false);
 onGenerate?.(generated);
 }, 800);
 };

 const handleExport = (format: 'pdf' | 'html' | 'markdown') => {
 if (!report) return;

 if (format === 'markdown') {
 let md = `# ${report.title}\n\n`;
 md += `*${report.subtitle}*\n\n`;
 md += `**Author:** ${report.author}\n\n`;
 md += `---\n\n`;
 md += `## Executive Summary\n\n${report.executiveSummary}\n\n`;
 report.sections.forEach((section) => {
 md += `## ${section.title}\n\n${section.content}\n\n`;
 });
 md += `## Key Recommendations\n\n`;
 report.keyRecommendations.forEach((rec, i) => {
 md += `${i + 1}. ${rec}\n`;
 });
 md += `\n---\n\n*${report.riskDisclosure}*\n`;

 const blob = new Blob([md], { type: 'text/markdown' });
 const url = URL.createObjectURL(blob);
 const a = document.createElement('a');
 a.href = url;
 a.download = `${report.id}.md`;
 a.click();
 URL.revokeObjectURL(url);
 }
 };

 return (
 <div className="space-y-4">
 <div className="flex items-center justify-between">
 <h3 className="text-lg font-bold text-slate-900">📄 Smart Report Generator</h3>
 <div className="flex items-center gap-2">
 {!report ? (
 <button
 onClick={handleGenerate}
 disabled={isGenerating}
 className="px-4 py-2 text-sm font-semibold rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-md hover:shadow-lg transition-all disabled:opacity-50"
 >
 {isGenerating ? (
 <span className="flex items-center gap-2">
 <span className="animate-spin">⏳</span> Generating...
 </span>
 ) : (
 ' <PencilLine className="w-4 h-4 inline" /> Generate Committee Memo'
 )}
 </button>
 ) : (
 <>
 <button
 onClick={() => handleExport('markdown')}
 className="px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200 transition-all"
 >
 Export MD
 </button>
 <button
 onClick={() => handleExport('pdf')}
 className="px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200 transition-all"
 >
 Export PDF
 </button>
 <button
 onClick={() => setReport(null)}
 className="px-3 py-1.5 text-xs font-medium rounded-lg text-slate-500 hover:text-slate-700"
 >
 Regenerate
 </button>
 </>
 )}
 </div>
 </div>

 {/* Report Preview */}
 {report && (
 <div className="glass rounded-2xl overflow-hidden animate-glass-in">
 {/* Report Header */}
 <div className="bg-gradient-to-r from-slate-800 to-slate-900 p-6 text-white">
 <div className="flex items-start justify-between">
 <div>
 <h2 className="text-xl font-bold">{report.title}</h2>
 <p className="text-sm text-white/70 mt-1">{report.subtitle}</p>
 </div>
 <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest bg-red-500/20 text-red-300 rounded border border-red-500/30">
 {report.classification}
 </span>
 </div>
 </div>

 {/* Executive Summary */}
 <div className="p-6 border-b border-white/20">
 <h3 className="text-sm font-bold text-slate-700 uppercase tracking-widest mb-2">Executive Summary</h3>
 <p className="text-sm text-slate-600 leading-relaxed">{report.executiveSummary}</p>
 </div>

 {/* Sections */}
 <div className="divide-y divide-white/20">
 {report.sections.map((section) => (
 <div key={section.id} className="p-6">
 <h3 className="text-sm font-bold text-slate-700 uppercase tracking-widest mb-3">{section.title}</h3>
 <p className="text-sm text-slate-600 mb-3">{section.content}</p>

 {/* Table */}
 {section.type === 'table' && section.data && (
 <div className="overflow-x-auto">
 <table className="w-full text-sm">
 <thead>
 <tr className="border-b border-slate-200">
 {(section.data.headers as string[]).map((h: string) => (
 <th key={h} className="text-left py-2 px-3 text-xs font-semibold text-slate-500">{h}</th>
 ))}
 </tr>
 </thead>
 <tbody>
 {(section.data.rows as string[][]).map((row: string[], i: number) => (
 <tr key={i} className="border-b border-white/10">
 {row.map((cell: string, j: number) => (
 <td key={j} className="py-2 px-3 text-slate-700">{cell}</td>
 ))}
 </tr>
 ))}
 </tbody>
 </table>
 </div>
 )}

 {/* Metrics */}
 {section.type === 'metrics' && section.data && (
 <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
 {Object.entries(section.data).map(([key, value]) => (
 <div key={key} className="p-3 rounded-xl bg-white/50">
 <div className="text-[10px] font-semibold text-slate-500 uppercase">{key.replace(/([A-Z])/g, ' $1')}</div>
 <div className="text-sm font-bold text-slate-900 mt-1">
 {typeof value === 'number' ? (key.includes('Rate') || key.includes('Spread') || key.includes('Slope') || key.includes('Vix') ? `${value}%` : value.toLocaleString()) : String(value)}
 </div>
 </div>
 ))}
 </div>
 )}

 {/* Learnings */}
 {section.id === 'learnings' && section.data && (
 <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
 <div className="p-3 rounded-xl bg-emerald-50">
 <div className="text-xs font-semibold text-emerald-700 mb-1"> <CheckCircle className="w-4 h-4 inline" /> What Worked</div>
 {(section.data.whatWorked as string[]).map((item: string, i: number) => (
 <div key={i} className="text-xs text-emerald-600">• {item}</div>
 ))}
 </div>
 <div className="p-3 rounded-xl bg-amber-50">
 <div className="text-xs font-semibold text-amber-700 mb-1"> <AlertTriangle className="w-4 h-4 inline" /> What Failed</div>
 {(section.data.whatFailed as string[]).length > 0
 ? (section.data.whatFailed as string[]).map((item: string, i: number) => (
 <div key={i} className="text-xs text-amber-600">• {item}</div>
 ))
 : <div className="text-xs text-amber-600">No failures identified</div>
 }
 </div>
 </div>
 )}
 </div>
 ))}
 </div>

 {/* Key Recommendations */}
 <div className="p-6 bg-blue-50/50 border-t border-blue-200/50">
 <h3 className="text-sm font-bold text-blue-800 uppercase tracking-widest mb-3">Key Recommendations</h3>
 <ol className="space-y-2">
 {report.keyRecommendations.map((rec, i) => (
 <li key={i} className="flex items-start gap-2 text-sm text-blue-700">
 <span className="font-bold text-blue-500">{i + 1}.</span>
 {rec}
 </li>
 ))}
 </ol>
 </div>

 {/* Risk Disclosure */}
 <div className="p-4 bg-slate-50 border-t border-slate-200">
 <p className="text-[10px] text-slate-500 leading-relaxed">{report.riskDisclosure}</p>
 </div>
 </div>
 )}
 </div>
 );
}
