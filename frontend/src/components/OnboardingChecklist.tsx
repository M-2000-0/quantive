// ── Onboarding Checklist Component ─────────────────────────────────────
// Guides new users through setting up their first portfolio, running
// an optimization, and connecting data providers.

import { useState, useEffect } from 'react';
import { Rocket } from 'lucide-react';

interface ChecklistStep {
 id: string;
 title: string;
 description: string;
 icon: string;
 category: 'setup' | 'data' | 'optimize' | 'explore';
 actionLabel: string;
 actionUrl: string;
 estimatedTime: string;
}

const CHECKLIST_STEPS: ChecklistStep[] = [
 {
 id: 'create_portfolio',
 title: 'Create Your First Portfolio',
 description: 'Import or manually create a debt portfolio with your instruments',
 icon: '📁',
 category: 'setup',
 actionLabel: 'Create Portfolio',
 actionUrl: '/portfolios/new',
 estimatedTime: '5 min' },
 {
 id: 'add_instruments',
 title: 'Add Instruments',
 description: 'Add bonds, loans, notes, or commercial paper to your portfolio',
 icon: 'PencilLine',
 category: 'setup',
 actionLabel: 'Add Instruments',
 actionUrl: '/portfolios/new',
 estimatedTime: '10 min' },
 {
 id: 'import_csv',
 title: 'Import from CSV',
 description: 'Bulk import instruments from a spreadsheet for faster setup',
 icon: 'BarChart3',
 category: 'setup',
 actionLabel: 'Import CSV',
 actionUrl: '/portfolios/new',
 estimatedTime: '3 min' },
 {
 id: 'connect_fred',
 title: 'Connect FRED API',
 description: 'Get live yield curves and economic data from the Federal Reserve',
 icon: 'Landmark',
 category: 'data',
 actionLabel: 'Connect FRED',
 actionUrl: '/settings',
 estimatedTime: '2 min' },
 {
 id: 'connect_bloomberg',
 title: 'Connect Bloomberg',
 description: 'Access real-time market data and bond pricing from Bloomberg',
 icon: 'Building2',
 category: 'data',
 actionLabel: 'Connect Bloomberg',
 actionUrl: '/settings',
 estimatedTime: '5 min' },
 {
 id: 'run_optimization',
 title: 'Run First Optimization',
 description: 'Configure objectives and constraints, then run the solver',
 icon: 'Zap',
 category: 'optimize',
 actionLabel: 'Run Optimization',
 actionUrl: '/optimizations/new',
 estimatedTime: '10 min' },
 {
 id: 'review_results',
 title: 'Review Optimization Results',
 description: 'Analyze the recommendations and compare strategies',
 icon: 'FileText',
 category: 'optimize',
 actionLabel: 'View Results',
 actionUrl: '/reports',
 estimatedTime: '5 min' },
 {
 id: 'set_alerts',
 title: 'Set Up Alerts',
 description: 'Configure notifications for price changes, maturities, and credit events',
 icon: '🔔',
 category: 'explore',
 actionLabel: 'Configure Alerts',
 actionUrl: '/notifications',
 estimatedTime: '3 min' },
 {
 id: 'view_peers',
 title: 'View Peer Intelligence',
 description: 'See how your portfolio compares to similar institutional portfolios',
 icon: 'Users',
 category: 'explore',
 actionLabel: 'View Peers',
 actionUrl: '/peers',
 estimatedTime: '5 min' },
 {
 id: 'explore_market',
 title: 'Explore Market Data',
 description: 'Check live yield curves, FX rates, and credit spreads',
 icon: 'TrendingUp',
 category: 'explore',
 actionLabel: 'View Market Data',
 actionUrl: '/market',
 estimatedTime: '5 min' },
];

const CATEGORY_CONFIG = {
 setup: { label: 'Getting Started', color: 'from-blue-500 to-cyan-500' },
 data: { label: 'Connect Data', color: 'from-purple-500 to-pink-500' },
 optimize: { label: 'Run Optimization', color: 'from-emerald-500 to-teal-500' },
 explore: { label: 'Explore Features', color: 'from-amber-500 to-orange-500' } };

interface OnboardingChecklistProps {
 /** Completed step IDs */
 completedSteps?: string[];
 /** Callback when a step is completed */
 onStepComplete?: (stepId: string) => void;
 /** Callback when checklist is dismissed */
 onDismiss?: () => void;
 /** Whether to show the checklist */
 visible?: boolean;
}

export default function OnboardingChecklist({
 completedSteps = [],
 onStepComplete,
 onDismiss,
 visible = true }: OnboardingChecklistProps) {
 const [completed, setCompleted] = useState<Set<string>>(new Set(completedSteps));
 const [expandedStep, setExpandedStep] = useState<string | null>(null);

 useEffect(() => {
 setCompleted(new Set(completedSteps));
 }, [completedSteps]);

 const progress = (completed.size / CHECKLIST_STEPS.length) * 100;
 const isComplete = completed.size === CHECKLIST_STEPS.length;

 const handleComplete = (stepId: string) => {
 setCompleted((prev) => {
 const next = new Set(prev);
 next.add(stepId);
 return next;
 });
 onStepComplete?.(stepId);
 };

 const categories = Object.keys(CATEGORY_CONFIG) as Array<keyof typeof CATEGORY_CONFIG>;

 if (!visible) return null;

 if (isComplete) {
 return (
 <div className="glass rounded-2xl p-6 text-center animate-glass-in">
 <div className="text-4xl mb-3">🎉</div>
 <h3 className="text-lg font-bold text-slate-900 mb-1">Onboarding Complete!</h3>
 <p className="text-sm text-slate-600 mb-4">You've set up everything you need to get started with Quantive.</p>
 <button
 onClick={onDismiss}
 className="px-4 py-2 text-sm font-semibold rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-md hover:shadow-lg transition-all"
 >
 Start Using Quantive
 </button>
 </div>
 );
 }

 return (
 <div className="glass rounded-2xl overflow-hidden animate-glass-in">
 {/* Header */}
 <div className="bg-gradient-to-r from-blue-600 to-purple-600 p-6 text-white">
 <div className="flex items-center justify-between mb-3">
 <div>
 <h3 className="text-lg font-bold"> <Rocket className="w-4 h-4 inline" /> Quick Start Guide</h3>
 <p className="text-sm text-white/80">Get up and running in ~45 minutes</p>
 </div>
 <button
 onClick={onDismiss}
 className="text-white/60 hover:text-white text-sm"
 >
 Skip for now →
 </button>
 </div>

 {/* Progress bar */}
 <div className="flex items-center gap-3">
 <div className="flex-1 h-2 rounded-full bg-white/20 overflow-hidden">
 <div
 className="h-full rounded-full bg-white transition-all duration-500"
 style={{ width: `${progress}%` }}
 />
 </div>
 <span className="text-sm font-bold">{completed.size}/{CHECKLIST_STEPS.length}</span>
 </div>
 </div>

 {/* Steps by Category */}
 <div className="p-6 space-y-6">
 {categories.map((category) => {
 const steps = CHECKLIST_STEPS.filter((s) => s.category === category);
 const completedInCategory = steps.filter((s) => completed.has(s.id)).length;
 const config = CATEGORY_CONFIG[category];

 return (
 <div key={category}>
 <div className="flex items-center gap-2 mb-3">
 <div className={`w-2 h-2 rounded-full bg-gradient-to-r ${config.color}`} />
 <h4 className="text-xs font-bold uppercase tracking-widest text-slate-500">{config.label}</h4>
 <span className="text-[10px] text-slate-400">
 {completedInCategory}/{steps.length}
 </span>
 </div>

 <div className="space-y-2">
 {steps.map((step) => {
 const isCompleted = completed.has(step.id);
 const isExpanded = expandedStep === step.id;

 return (
 <div
 key={step.id}
 className={`rounded-xl transition-all ${
 isCompleted
 ? 'bg-emerald-50/50 border border-emerald-200/50'
 : 'bg-white/30 border border-white/40 hover:border-slate-200'
 }`}
 >
 <div
 className="flex items-center gap-3 p-3 cursor-pointer"
 onClick={() => setExpandedStep(isExpanded ? null : step.id)}
 >
 {/* Checkbox */}
 <button
 onClick={(e) => {
 e.stopPropagation();
 handleComplete(step.id);
 }}
 className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 transition-all ${
 isCompleted
 ? 'bg-emerald-500 text-white'
 : 'bg-slate-200 text-slate-500 hover:bg-slate-300'
 }`}
 >
 {isCompleted ? '✓' : ''}
 </button>

 {/* Content */}
 <div className="flex-1 min-w-0">
 <div className="flex items-center gap-2">
 <span className="text-sm">{step.icon}</span>
 <span className={`text-sm font-medium ${isCompleted ? 'text-emerald-700 line-through' : 'text-slate-900'}`}>
 {step.title}
 </span>
 </div>
 </div>

 {/* Time estimate */}
 <span className="text-[10px] text-slate-400 flex-shrink-0">
 {step.estimatedTime}
 </span>
 </div>

 {/* Expanded content */}
 {isExpanded && !isCompleted && (
 <div className="px-3 pb-3 pt-0 animate-glass-in">
 <p className="text-xs text-slate-600 mb-3">{step.description}</p>
 <a
 href={step.actionUrl}
 className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold rounded-lg bg-blue-600/14 text-blue-700 hover:bg-blue-600/20 transition-all"
 >
 {step.actionLabel} →
 </a>
 </div>
 )}
 </div>
 );
 })}
 </div>
 </div>
 );
 })}
 </div>
 </div>
 );
}
