// ── UpgradeModal Component ────────────────────────────────────────────
// Full-screen modal that shows tier comparison and upgrade flow.
// Triggered when users hit plan limits or click upgrade CTAs.

import { useState } from 'react';
import { PLANS, FEATURES, hasFeature, getAnnualSavings, getFeatureMatrix, type PlanTier } from '../lib/featureFlags';

interface UpgradeModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentPlan: PlanTier;
  highlightedFeature?: string;
}

const TIER_GRADIENTS: Record<PlanTier, string> = {
  demo: 'from-slate-400 to-slate-600',
  starter: 'from-blue-500 to-cyan-500',
  professional: 'from-purple-500 to-indigo-500',
  enterprise: 'from-amber-500 to-orange-500' };

const TIER_CHECK: Record<PlanTier, string> = {
  demo: 'bg-slate-100 text-slate-400',
  starter: 'bg-blue-100 text-blue-600',
  professional: 'bg-purple-100 text-purple-600',
  enterprise: 'bg-amber-100 text-amber-600' };

export default function UpgradeModal({
  isOpen,
  onClose,
  currentPlan,
  highlightedFeature }: UpgradeModalProps) {
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'annual'>('monthly');
  const [selectedPlan, setSelectedPlan] = useState<PlanTier | null>(null);
  const featureMatrix = getFeatureMatrix();

  if (!isOpen) return null;

  const tierPlans: PlanTier[] = ['starter', 'professional', 'enterprise'];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={onClose}>
      <div
        className="glass rounded-3xl w-full max-w-6xl max-h-[90vh] overflow-hidden animate-glass-in"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-white/20">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-slate-900">Choose Your Plan</h2>
              <p className="text-sm text-slate-600 mt-1">
                Unlock the full power of Quantive debt optimization
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-slate-600 text-2xl"
            >
              ✕
            </button>
          </div>

          {/* Billing Toggle */}
          <div className="flex items-center gap-3 mt-4">
            <span className={`text-sm font-medium ${billingCycle === 'monthly' ? 'text-slate-900' : 'text-slate-500'}`}>
              Monthly
            </span>
            <button
              onClick={() => setBillingCycle(billingCycle === 'monthly' ? 'annual' : 'monthly')}
              className={`relative w-12 h-6 rounded-full transition-colors ${
                billingCycle === 'annual' ? 'bg-emerald-600' : 'bg-slate-300'
              }`}
            >
              <div
                className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform ${
                  billingCycle === 'annual' ? 'translate-x-6' : 'translate-x-0.5'
                }`}
              />
            </button>
            <span className={`text-sm font-medium ${billingCycle === 'annual' ? 'text-slate-900' : 'text-slate-500'}`}>
              Annual
            </span>
            {billingCycle === 'annual' && (
              <span className="text-xs font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-lg">
                Save up to 20%
              </span>
            )}
          </div>
        </div>

        {/* Tier Cards */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            {tierPlans.map((tier) => {
              const plan = PLANS[tier];
              const price = billingCycle === 'annual' ? plan.priceAnnual : plan.price;
              const savings = billingCycle === 'annual' ? getAnnualSavings(tier) : 0;
              const isCurrent = tier === currentPlan;
              const isLocked = tierPlans.indexOf(tier) > tierPlans.indexOf(currentPlan as PlanTier);
              const isSelected = selectedPlan === tier;

              return (
                <div
                  key={tier}
                  className={`relative rounded-2xl border-2 transition-all cursor-pointer ${
                    isSelected
                      ? 'border-blue-500 shadow-lg scale-105'
                      : isCurrent
                      ? 'border-emerald-400'
                      : 'border-white/40 hover:border-slate-200'
                  } ${isLocked ? 'opacity-90' : ''}`}
                  onClick={() => setSelectedPlan(tier)}
                >
                  {tier === 'professional' && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 text-[10px] font-bold uppercase tracking-widest bg-gradient-to-r from-purple-500 to-indigo-500 text-white rounded-full">
                      Most Popular
                    </div>
                  )}
                  {isCurrent && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 text-[10px] font-bold uppercase tracking-widest bg-emerald-500 text-white rounded-full">
                      Current Plan
                    </div>
                  )}

                  <div className={`bg-gradient-to-r ${TIER_GRADIENTS[tier]} p-4 text-white rounded-t-xl`}>
                    <h3 className="text-lg font-bold">{plan.name}</h3>
                    <p className="text-xs text-white/80 mt-1">{plan.description}</p>
                  </div>

                  <div className="p-4">
                    <div className="flex items-baseline gap-1 mb-3">
                      <span className="text-3xl font-bold text-slate-900">${price}</span>
                      <span className="text-sm text-slate-500">/month</span>
                    </div>
                    {savings > 0 && (
                      <div className="text-xs text-emerald-600 font-medium mb-3">
                        Save ${savings}/year with annual billing
                      </div>
                    )}

                    <div className="space-y-2 mb-4">
                      <div className="flex items-center gap-2 text-sm text-slate-700">
                        <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${TIER_CHECK[tier]}`}>✓</span>
                        {plan.maxPortfolios >= 999 ? 'Unlimited' : plan.maxPortfolios} Portfolios
                      </div>
                      <div className="flex items-center gap-2 text-sm text-slate-700">
                        <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${TIER_CHECK[tier]}`}>✓</span>
                        {plan.maxUsers >= 999 ? 'Unlimited' : plan.maxUsers} Users
                      </div>
                      <div className="flex items-center gap-2 text-sm text-slate-700">
                        <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${TIER_CHECK[tier]}`}>✓</span>
                        {plan.supportLevel === 'dedicated' ? 'Dedicated CSM' : plan.supportLevel === 'priority' ? 'Priority Support' : 'Email Support'}
                      </div>
                    </div>

                    {isCurrent ? (
                      <button
                        disabled
                        className="w-full py-2.5 text-sm font-semibold rounded-xl bg-slate-100 text-slate-400 cursor-not-allowed"
                      >
                        Current Plan
                      </button>
                    ) : (
                      <button
                        className={`w-full py-2.5 text-sm font-semibold rounded-xl transition-all ${
                          isSelected
                            ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg'
                            : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                        }`}
                      >
                        {isSelected ? 'Selected — Click to Checkout' : 'Select Plan'}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Feature Matrix */}
          <div className="mb-6">
            <h3 className="text-lg font-bold text-slate-900 mb-4">Feature Comparison</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/20">
                    <th className="text-left py-2 px-3 text-slate-700 font-semibold">Feature</th>
                    {tierPlans.map((tier) => (
                      <th key={tier} className="text-center py-2 px-3 text-slate-700 font-semibold">
                        {PLANS[tier].name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {featureMatrix.map((group) => (
                    <>
                      <tr key={group.category}>
                        <td
                          colSpan={4}
                          className="py-2 px-3 text-xs font-bold uppercase tracking-widest text-slate-500 bg-slate-50/50"
                        >
                          {group.category}
                        </td>
                      </tr>
                      {group.features.map((row) => (
                        <tr
                          key={row.feature.id}
                          className={`border-b border-white/10 ${
                            highlightedFeature === row.feature.id ? 'bg-blue-50/50' : ''
                          }`}
                        >
                          <td className="py-2 px-3 text-slate-700">
                            {row.feature.name}
                            {row.feature.isBeta && (
                              <span className="ml-1 text-[9px] font-bold text-amber-600 bg-amber-50 px-1 rounded">BETA</span>
                            )}
                          </td>
                          {(['starter', 'professional', 'enterprise'] as PlanTier[]).map((tier) => (
                            <td key={tier} className="text-center py-2 px-3">
                              {row[tier as keyof typeof row] ? (
                                <span className="text-emerald-600 font-bold">✓</span>
                              ) : (
                                <span className="text-slate-300">—</span>
                              )}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between pt-4 border-t border-white/20">
            <p className="text-xs text-slate-500">
              All plans include: 2FA, audit logging, GDPR compliance, Terms of Service
            </p>
            {selectedPlan && selectedPlan !== currentPlan && (
              <button className="px-6 py-3 text-sm font-bold rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg hover:shadow-xl transition-all">
                Checkout with {PLANS[selectedPlan].name} →
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
