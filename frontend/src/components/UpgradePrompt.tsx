// ── UpgradePrompt Component ───────────────────────────────────────────
// Inline upgrade prompt shown within a page when a feature is locked.
// Displays a preview of what the locked feature offers and a CTA to upgrade.

import { Lock } from 'lucide-react';
import { PLANS, getRequiredPlan, getAnnualSavings, type PlanTier, type FeatureDefinition } from '../lib/featureFlags';

interface UpgradePromptProps {
 currentPlan: PlanTier;
 requiredPlan: PlanTier;
 feature?: FeatureDefinition;
 compact?: boolean;
}

const TIER_COLORS: Record<PlanTier, string> = {
 demo: 'from-slate-400 to-slate-500',
 starter: 'from-blue-500 to-cyan-500',
 professional: 'from-purple-500 to-indigo-500',
 enterprise: 'from-amber-500 to-orange-500' };

const TIER_BG: Record<PlanTier, string> = {
 demo: 'bg-slate-50 border-slate-200',
 starter: 'bg-blue-50 border-blue-200',
 professional: 'bg-purple-50 border-purple-200',
 enterprise: 'bg-amber-50 border-amber-200' };

export default function UpgradePrompt({
 currentPlan,
 requiredPlan,
 feature,
 compact = false }: UpgradePromptProps) {
 const requiredDef = PLANS[requiredPlan];
 const savings = getAnnualSavings(requiredPlan);

 if (compact) {
 return (
 <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border ${TIER_BG[requiredPlan]}`}>
 <span className="text-xs font-medium text-slate-700">
 <Lock className="w-4 h-4 inline" /> {feature?.name || 'This feature'} requires{' '}
 <span className={`font-bold bg-gradient-to-r ${TIER_COLORS[requiredPlan]} bg-clip-text text-transparent`}>
 {requiredDef.name}
 </span>
 </span>
 <a
 href="/billing"
 className="text-xs font-bold text-blue-600 hover:text-blue-700 underline"
 >
 Upgrade →
 </a>
 </div>
 );
 }

 return (
 <div className="glass rounded-2xl border border-white/40 overflow-hidden">
 {/* Header with gradient */}
 <div className={`bg-gradient-to-r ${TIER_COLORS[requiredPlan]} p-6 text-white`}>
 <div className="flex items-start justify-between">
 <div>
 <div className="flex items-center gap-2 mb-1">
 <Lock className="w-5 h-5" />
 <span className="text-xs font-bold uppercase tracking-widest opacity-80">
 {requiredDef.name} Feature
 </span>
 </div>
 <h3 className="text-xl font-bold">
 {feature?.name || 'Unlock This Feature'}
 </h3>
 <p className="text-sm text-white/80 mt-1">
 {feature?.description || `Available on the ${requiredDef.name} plan and above`}
 </p>
 </div>
 <div className="text-right">
 <div className="text-3xl font-bold">${requiredDef.price}</div>
 <div className="text-xs text-white/70">/month</div>
 {savings > 0 && (
 <div className="text-xs text-white/60 mt-1">
 Save ${savings}/yr with annual billing
 </div>
 )}
 </div>
 </div>
 </div>

 {/* Body */}
 <div className="p-6">
 <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
 <div className="text-center p-3 rounded-xl bg-white/50">
 <div className="text-2xl mb-1">
 {requiredPlan === 'enterprise' ? 'Building2' : requiredPlan === 'professional' ? 'Zap' : 'BarChart3'}
 </div>
 <div className="text-xs font-medium text-slate-700">
 {requiredDef.maxPortfolios >= 999 ? 'Unlimited' : requiredDef.maxPortfolios} Portfolios
 </div>
 </div>
 <div className="text-center p-3 rounded-xl bg-white/50">
 <div className="text-2xl mb-1">
 {requiredPlan === 'enterprise' ? 'Users' : requiredPlan === 'professional' ? '🤖' : '👤'}
 </div>
 <div className="text-xs font-medium text-slate-700">
 {requiredDef.maxUsers >= 999 ? 'Unlimited' : requiredDef.maxUsers} Users
 </div>
 </div>
 <div className="text-center p-3 rounded-xl bg-white/50">
 <div className="text-2xl mb-1">
 {requiredPlan === 'enterprise' ? 'Target' : requiredPlan === 'professional' ? '📞' : '📧'}
 </div>
 <div className="text-xs font-medium text-slate-700">
 {requiredDef.supportLevel === 'dedicated' ? 'Dedicated CSM' : requiredDef.supportLevel === 'priority' ? 'Priority Support' : 'Email Support'}
 </div>
 </div>
 </div>

 <div className="flex items-center justify-between">
 <div className="text-sm text-slate-600">
 Current plan: <span className="font-semibold capitalize">{currentPlan}</span>
 </div>
 <div className="flex items-center gap-3">
 <a
 href="/billing"
 className="px-4 py-2 text-sm font-semibold rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-md hover:shadow-lg transition-all"
 >
 Upgrade to {requiredDef.name} →
 </a>
 <a
 href="/billing"
 className="text-xs text-slate-500 hover:text-slate-700"
 >
 Compare plans
 </a>
 </div>
 </div>
 </div>
 </div>
 );
}
